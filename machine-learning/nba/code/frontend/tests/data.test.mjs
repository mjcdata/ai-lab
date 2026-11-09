import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { prepareSnapshot } from '../scripts/prepare-snapshot.mjs';
const id='a'.repeat(32), base=`/snapshots/releases/${id}`;
const players=[{player_id:'1',name:'Stephen Curry'},{player_id:'2',name:'Seth Curry'}];
let serial=0;
async function loader() { return import(`../lib/data.js?test=${++serial}`); }
function fixtureFetch(url) {
 const values={'/snapshots/current.json':{snapshot_id:id},[`${base}/manifest.json`]:{schema_version:2,snapshot_id:id,season:'2026-27',player_count:2},[`${base}/players.json`]:players};
 if (url.includes('/results/')) {const parts=url.split('/');return Response.json({reference:{PLAYER_ID:parts.at(-1).replace('.json','')},mode:parts.at(-2),season:'2026-27',comparisons:[]});}
 return Response.json(values[url]);
}
test('search and per36 use one immutable generation without an API',async()=>{
 const original=globalThis.fetch;const urls=[];globalThis.fetch=async url=>{urls.push(url);return fixtureFetch(url);};
 try {const data=await loader();assert.equal((await data.searchPlayers('CURRY')).total,2);assert.equal((await data.searchPlayers('Stephen')).players[0].player_id,'1');assert.equal((await data.searchPlayers('no match')).total,0);assert.equal((await data.loadComparisons('1','per36')).mode,'per36');await assert.rejects(data.loadComparisons('1','per_game'),/Invalid/);assert.equal(urls.filter(u=>u.endsWith('current.json')).length,1);assert.ok(urls.every(u=>u.startsWith('/snapshots/')));}finally{globalThis.fetch=original;}
});
test('failed index retries, aborts and invalid selections reject',async()=>{
 const original=globalThis.fetch;let fail=true;globalThis.fetch=async url=>fail&&url===`${base}/players.json`?new Response('',{status:503}):fixtureFetch(url);
 try{const data=await loader();await assert.rejects(data.searchPlayers('Curry'),/unavailable/);fail=false;assert.equal((await data.searchPlayers('1')).total,1);await assert.rejects(data.loadComparisons('bad','per36'),/Invalid/);await assert.rejects(data.loadComparisons('1','bad'),/Invalid/);await assert.rejects(data.loadComparisons('999','per36'),/not found/);await assert.rejects(data.searchPlayers('',AbortSignal.abort()));}finally{globalThis.fetch=original;}
});
test('mismatched result identity is rejected',async()=>{
 const original=globalThis.fetch;globalThis.fetch=async url=>url.includes('/results/')?Response.json({reference:{PLAYER_ID:'2'},mode:'per36',season:'2026-27'}):fixtureFetch(url);
 try{await assert.rejects((await loader()).loadComparisons('1','per36'),/identity/);}finally{globalThis.fetch=original;}
});
test('build staging checks every asset and preserves previous assets on validation failure',async()=>{
 const root=await mkdtemp(join(tmpdir(),'nba-static-test-')),source=join(root,'source'),publicDir=join(root,'public');
 try{const release=join(source,'releases',id);await mkdir(release,{recursive:true});const files={};
 for(const [path,value] of [['players.json',[players[0]]],['results/per36/1.json',{}]]){const bytes=Buffer.from(JSON.stringify(value));await mkdir(join(release,path,'..'),{recursive:true});await writeFile(join(release,path),bytes);files[path]={bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')};}
 const manifest=Buffer.from(JSON.stringify({schema_version:2,snapshot_id:id,season:'2026-27',modes:['per36'],player_count:1,result_count:1,files}));await writeFile(join(release,'manifest.json'),manifest);await writeFile(join(source,'current.json'),JSON.stringify({snapshot_id:id,manifest_sha256:createHash('sha256').update(manifest).digest('hex')}));
 await prepareSnapshot(source,publicDir);const before=await readFile(join(publicDir,'snapshots/current.json'));await writeFile(join(release,'results/per36/1.json'),'corrupt');await assert.rejects(prepareSnapshot(source,publicDir),/checksum/);assert.deepEqual(await readFile(join(publicDir,'snapshots/current.json')),before);assert.equal((await readFile(join(publicDir,'snapshots/releases',id,'results/per36/1.json'))).toString(),'{}');
 }finally{await rm(root,{recursive:true,force:true});}
});
