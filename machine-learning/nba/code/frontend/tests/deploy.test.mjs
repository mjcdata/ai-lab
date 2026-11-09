import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, readdir, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { prepareVercel } from '../scripts/prepare-vercel.mjs';
const id='b'.repeat(32);
const hash=b=>createHash('sha256').update(b).digest('hex');
async function fixture(root) {
 const source=join(root,'out'),release=join(source,'snapshots/releases',id);await mkdir(release,{recursive:true});
 const files={};
 for(const [path,value] of [['players.json',[{player_id:'1',name:'Player'}]],['results/per36/1.json',{}]]) {
  const b=Buffer.from(JSON.stringify(value));await mkdir(join(release,path,'..'),{recursive:true});await writeFile(join(release,path),b);files[path]={bytes:b.length,sha256:hash(b)};
 }
 const manifest=Buffer.from(JSON.stringify({schema_version:2,snapshot_id:id,season:'2026-27',modes:['per36'],player_count:1,result_count:1,files}));
 await writeFile(join(release,'manifest.json'),manifest);await writeFile(join(source,'snapshots/current.json'),JSON.stringify({snapshot_id:id,manifest_sha256:hash(manifest)}));
 await writeFile(join(source,'index.html'),'<html>Static NBA app</html>');await writeFile(join(source,'404.html'),'<html>Not found</html>');
 return source;
}
test('isolated Vercel output contains only static export and v3 routing, without functions or source files',async()=>{
 const root=await mkdtemp(join(tmpdir(),'nba-upload-'));
 try {
  const source=await fixture(root);const dest=join(root,'bundle');const result=await prepareVercel(source,dest);
  assert.equal(result.players,1);assert.equal(result.files,6);
  assert.deepEqual(await readdir(dest),['.vercel']);
  const output=join(dest,'.vercel/output');assert.deepEqual((await readdir(output)).sort(),['config.json','static']);
  const config=JSON.parse(await readFile(join(output,'config.json')));assert.equal(config.version,3);assert.equal(config.routes.at(-1).status,404);
  assert.equal((await readFile(join(output,'static/index.html'))).toString(),'<html>Static NBA app</html>');
  await assert.rejects(prepareVercel(source,dest));assert.equal((await readFile(join(output,'static/index.html'))).toString(),'<html>Static NBA app</html>');
 }finally{await rm(root,{recursive:true,force:true});}
});
test('unexpected private files, embedded keys and symlinks cannot enter upload bundle',async()=>{
 const root=await mkdtemp(join(tmpdir(),'nba-upload-private-'));
 try {
  const source=await fixture(root);const dest=join(root,'bundle');
  await writeFile(join(source,'.env'),'DO_NOT_UPLOAD=fixture');await assert.rejects(prepareVercel(source,dest),/Unexpected/);await rm(join(source,'.env'));
  await writeFile(join(source,'index.html'),'-----BEGIN PRIVATE KEY-----');await assert.rejects(prepareVercel(source,dest),/Private material/);await writeFile(join(source,'index.html'),'<html>safe</html>');
  await symlink(join(source,'index.html'),join(source,'leak.html'));await assert.rejects(prepareVercel(source,dest),/Symlink/);
  assert.deepEqual((await readdir(root)).sort(),['out']);
 }finally{await rm(root,{recursive:true,force:true});}
});
test('corrupt snapshots and nested output paths fail before any upload bundle is produced',async()=>{
 const root=await mkdtemp(join(tmpdir(),'nba-upload-corrupt-'));
 try {
  const source=await fixture(root);await assert.rejects(prepareVercel(source,join(source,'nested')),/separate/);
  await writeFile(join(source,'snapshots/releases',id,'results/per36/1.json'),'changed');
  await assert.rejects(prepareVercel(source,join(root,'bundle')),/checksum/);assert.deepEqual(await readdir(root),['out']);
 }finally{await rm(root,{recursive:true,force:true});}
});
