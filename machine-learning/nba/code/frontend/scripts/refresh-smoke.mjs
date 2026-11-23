// Dynamic refresh smoke test: no hardcoded player names, scoring or NBA requests.
import { chromium, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
const [url, expectedSnapshot, expectedManifest] = process.argv.slice(2);
const base = new URL(url);
assert(base.protocol==='https:' || (base.protocol==='http:' && base.hostname==='127.0.0.1'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
async function get(path) {
 const response=await fetch(new URL(path,base));assert.equal(response.status,200);
 assert.equal(new URL(response.url).origin,base.origin,'Unexpected authentication/host redirect');
 return Buffer.from(await response.arrayBuffer());
}
const pointer=JSON.parse(await get('/snapshots/current.json'));assert.equal(pointer.snapshot_id,expectedSnapshot);
if(expectedManifest)assert.equal(pointer.manifest_sha256,expectedManifest,'Published manifest differs from the validated local release');
const missing=await fetch(new URL('/refresh-smoke-missing-asset.json',base));assert.equal(missing.status,404);
const release=`/snapshots/releases/${pointer.snapshot_id}`;
const manifestBytes=await get(`${release}/manifest.json`);assert.equal(hash(manifestBytes),pointer.manifest_sha256);
const manifest=JSON.parse(manifestBytes);const indexBytes=await get(`${release}/players.json`);
assert.equal(hash(indexBytes),manifest.files['players.json'].sha256);
const players=JSON.parse(indexBytes);assert(players.length>0);assert.equal(players.length,manifest.player_count);
// Verify EVERY snapshot asset, not just the selected browser example.
const paths=Object.keys(manifest.files);let next=0;
await Promise.all(Array.from({length:Math.min(6,paths.length)},async()=>{
 while(next<paths.length){const path=paths[next++];const bytes=await get(`${release}/${path}`);const info=manifest.files[path];assert.equal(bytes.length,info.bytes);assert.equal(hash(bytes),info.sha256);}
}));
const sample=players[0];const result=JSON.parse(await get(`${release}/results/per36/${sample.player_id}.json`));
const browser=await chromium.launch();const views=[];
try {
 for(const [name,viewport] of [['mobile',{width:390,height:844}],['desktop',{width:1440,height:1000}]]) {
  const page=await browser.newPage({viewport,reducedMotion:'reduce'});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('requestfailed',request=>errors.push(`Failed asset: ${request.url()}`));
  page.on('response',response=>{if(new URL(response.url()).origin===base.origin && response.status()>=400)errors.push(`HTTP ${response.status()}: ${response.url()}`);});
  await page.route('**/api/**',route=>{errors.push('Unexpected runtime API request');return route.abort();});
  const response=await page.goto(url);assert.equal(response.status(),200);
  const search=page.getByRole('searchbox');await expect(search).toBeVisible();
  await expect(page.locator('.player-option')).toHaveCount(0);
  await search.fill(sample.player_id);
  const match=page.getByRole('button').filter({has:page.locator('strong').filter({hasText:sample.name})}).first();
  await expect(match).toBeVisible();await match.click();
  await expect(page.locator('.reference h2')).toHaveText(sample.name);
  await expect(page.locator('.reference-stats > div')).toHaveCount(6);
  await expect(page.locator('.comparison')).toHaveCount(result.comparisons.length);
  assert.equal(await page.locator('.comparison tbody tr').count(),6*result.comparisons.length);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
  views.push({name,selected:sample.player_id,comparisons:result.comparisons.length});await page.close();
 }
}finally{await browser.close();}
console.log(JSON.stringify({passed:true,url:base.origin,snapshot:expectedSnapshot,assets:paths.length,players:players.length,views}));
