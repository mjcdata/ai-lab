import { test, expect } from '@playwright/test';
const label='Search the 2026–27 roster';
async function select(page,name='Curry') {
 await page.getByLabel(label).fill(name);
 await page.getByRole('button',{name:name==='Curry'?/Stephen Curry/:/Bronny James/}).click();
}
test('current-to-historical per36 search, seasonal matches and six-stat explanations',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',r=>{errors.push('Unexpected API request');return r.abort();});
 await page.goto('/');await expect(page).toHaveTitle('NBA Player Similarity');
 await expect(page.getByRole('heading',{level:1})).toHaveText('NBA Player Similarity');
 await expect(page.locator('.season')).toContainText('2026–27');
 await select(page);await expect(page.locator('.comparison')).toHaveCount(5);
 await expect(page.getByRole('button',{name:'Per game',exact:true})).toHaveCount(0);
 await expect(page.locator('.comparison').first().locator('h3')).toContainText(/20\d{2}-\d{2}/);
 await expect(page.locator('caption').first()).toContainText('Per-36');
 await expect(page.locator('.comparison').first().locator('tbody tr')).toHaveCount(6);
 await page.locator('summary').first().click();
 await expect(page.locator('.contributions').first().locator('meter')).toHaveCount(6);
 await expect(page.locator('.warnings')).toContainText('Limited playing time');
 await expect(page.locator('.warnings')).toContainText('player-seasons excluded');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 expect(errors).toEqual([]);
});
test('index failure retries and empty search',async({page})=>{
 await page.route('**/snapshots/**/players.json',r=>r.fulfill({status:503,body:'{}'}));
 await page.goto('/');await expect(page.locator('main [role=alert]')).toContainText('Snapshot data unavailable');
 await page.unroute('**/snapshots/**/players.json');await page.getByRole('button',{name:'Retry search'}).click();
 await expect(page.locator('.player-option').first()).toBeVisible();
 await page.getByLabel(label).fill('nobody-matches-this');
 await expect(page.getByText('No players found. Try a different name.')).toBeVisible();
 await page.getByLabel(label).fill('Curry');await expect(page.getByRole('button',{name:/Stephen Curry/})).toBeVisible();
});
test('comparison loading, retry and empty candidate states',async({page})=>{
 await page.goto('/');
 await page.route('**/snapshots/**/results/*/*.json',async r=>{await new Promise(resolve=>setTimeout(resolve,500));await r.fulfill({status:503,body:'{}'});});
 await select(page,'Bronny');await expect(page.getByRole('heading',{name:'Finding statistical neighbors…'})).toBeVisible();
 await expect(page.locator('main [role=alert]')).toContainText('Snapshot data unavailable');
 await page.unroute('**/snapshots/**/results/*/*.json');await page.getByRole('button',{name:'Retry comparisons'}).click();
 await expect(page.locator('.comparison')).toHaveCount(5);
 await page.route('**/snapshots/**/results/*/*.json',async r=>{const response=await r.fetch();const data=await response.json();data.comparisons=[];data.candidate_count=0;await r.fulfill({response,json:data});});
 await select(page);await expect(page.getByRole('heading',{name:'No eligible comparisons'})).toBeVisible();
});
test('reference and explanation values exactly match immutable snapshot on desktop/mobile',async({page})=>{
 await page.goto('/');await select(page);
 await expect(page.locator('.comparison')).toHaveCount(5);
 const current=await (await page.request.get('/snapshots/current.json')).json();
 const result=await (await page.request.get(`/snapshots/releases/${current.snapshot_id}/results/per36/201939.json`)).json();
 const cells=page.locator('.reference-stats > div');await expect(cells).toHaveCount(6);
 for(const [i,stat] of ['PTS','AST','REB','STL','BLK','TOV'].entries()) {
  await expect(cells.nth(i).locator('dt')).toHaveText(stat);
  await expect(cells.nth(i).locator('dd')).toHaveText(result.reference.per36[stat].toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}));
  expect(result.comparisons[0].features[stat].reference).toBe(result.reference.per36[stat]);
 }
 expect(result.comparisons.every(c=>c.player_id!=='201939'&&c.season<'2026-27')).toBeTruthy();
 expect(await page.locator('.reference-stats').evaluate(grid=>{const b=grid.getBoundingClientRect();return b.left>=0&&b.right<=window.innerWidth&&[...grid.children].every(c=>c.scrollWidth<=c.clientWidth);})).toBeTruthy();
});
