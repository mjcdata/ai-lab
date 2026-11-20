import { test, expect } from '@playwright/test';
const label='Search NBA players';
async function select(page,name='Curry') {
 await page.getByLabel(label).fill(name);
 await page.getByRole('button',{name:name==='Curry'?/Stephen Curry/:/Bronny James/}).click();
}
test('current-to-historical per36 search, seasonal matches and six-stat explanations',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',r=>{errors.push('Unexpected API request');return r.abort();});
 await page.goto('/');await expect(page).toHaveTitle('NBA Player Similarity');
 await expect(page.locator('.intro')).toHaveCount(0);
 await expect(page.getByText('THE PLAYER SIMILARITY LAB',{exact:true})).toHaveCount(0);
 await expect(page.locator('.brand')).toContainText('NBA Player Similarity');
 await expect(page.getByRole('heading',{level:1})).toHaveText('Every player has a statistical neighbor.');
 await expect(page.getByRole('link',{name:'View on GitHub'})).toHaveAttribute('href','https://github.com/mjcdata/ai-lab/tree/main/machine-learning/nba');
 await expect(page.locator('footer').getByRole('link',{name:'NBA.com'})).toHaveAttribute('href','https://www.nba.com/stats');
 await select(page);await expect(page.locator('.comparison')).toHaveCount(5);
 await expect(page.getByRole('button',{name:'Per game',exact:true})).toHaveCount(0);
 await expect(page.locator('.comparison').first().locator('h3')).toContainText(/20\d{2}-\d{2}/);
 await expect(page.locator('caption').first()).toContainText('Per-36');
 await expect(page.locator('.comparison').first().locator('tbody tr')).toHaveCount(6);
 await page.locator('summary').first().click();
 await expect(page.locator('.contributions').first().locator('meter')).toHaveCount(6);
 await expect(page.locator('.warnings')).toContainText('Limited playing time');
 await expect(page.locator('.warnings')).toContainText('player seasons excluded');
 await expect(page.locator('main')).not.toContainText('player-season');
 await expect(page.locator('main')).not.toContainText('season-relative');
 await expect(page.locator('.results-heading')).not.toContainText('02 /');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 expect(errors).toEqual([]);
});
test('index failure retries and empty search',async({page})=>{
 await page.route('**/snapshots/**/players.json',r=>r.fulfill({status:503,body:'{}'}));
 await page.goto('/');await page.getByLabel(label).fill('Curry');await expect(page.locator('main [role=alert]')).toContainText('Snapshot data unavailable');
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

test('search starts empty, reacts to input, clears, and handles whitespace and no matches',async({page})=>{
 await page.goto('/');
 await expect(page.locator('.player-option')).toHaveCount(0);
 await expect(page.getByText('No players found. Try a different name.')).toHaveCount(0);
 await expect(page.getByText(/Showing up to 25/)).toHaveCount(0);
 await expect(page.getByText('01 / SELECT A PLAYER')).toHaveCount(0);
 await page.getByLabel(label).fill('Stephen');
 await expect(page.getByRole('button',{name:/Stephen Curry/})).toBeVisible();
 await page.getByLabel(label).fill('');await expect(page.locator('.player-option')).toHaveCount(0);
 await page.getByLabel(label).fill('   ');await expect(page.locator('.player-option')).toHaveCount(0);
 await page.getByLabel(label).fill('nobody-matches-this');
 await expect(page.getByText('No players found. Try a different name.')).toBeVisible();
 await page.getByLabel(label).fill('Curry');await page.getByLabel(label).clear();
 await expect(page.locator('.player-option')).toHaveCount(0);
 await expect(page.locator('main')).not.toContainText(/[→↗➡➜←↑↓↔]/);
});

test('keyboard player selection focuses results and honors reduced motion',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.addInitScript(()=>{
  window.resultScrolls=[];
  const scroll=Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView=function(options){
   if(this.matches('.reference h2'))window.resultScrolls.push(options);
   return scroll.call(this,options);
  };
 });
 await page.goto('/');await page.getByLabel(label).fill('Stephen Curry');
 const player=page.getByRole('button',{name:/Stephen Curry/});await expect(player).toBeVisible();
 await page.getByLabel(label).press('Tab');await expect(player).toBeFocused();
 await page.keyboard.press('Enter');
 await expect(page.locator('.reference h2')).toHaveText('Stephen Curry');
 await expect(page.locator('.reference h2')).toBeFocused();
 await expect(page.locator('.comparison')).toHaveCount(5);
 if(page.viewportSize().width<=650){
  expect(await page.evaluate(()=>window.resultScrolls.at(-1)?.behavior)).toBe('instant');
  await expect.poll(()=>page.locator('.reference h2').evaluate(e=>e.getBoundingClientRect().top)).toBeLessThan(100);
 }
 await page.keyboard.press('Tab');await expect(page.locator('summary').first()).toBeFocused();
});

test('header link is keyboard accessible and fits a narrow mobile viewport',async({page})=>{
 await page.setViewportSize({width:320,height:740});await page.goto('/');
 const link=page.getByRole('link',{name:'View on GitHub'});
 await page.keyboard.press('Tab');await page.keyboard.press('Tab');await expect(link).toBeFocused();
 const style=await link.evaluate(e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return {color:s.color,background:s.backgroundColor,left:r.left,right:r.right,height:r.height};});
 expect(style.color).toBe('rgb(255, 255, 255)');expect(style.background).toBe('rgb(17, 17, 17)');expect(style.height).toBeGreaterThanOrEqual(44);
 expect(style.left).toBeGreaterThanOrEqual(0);expect(style.right).toBeLessThanOrEqual(320);
 await expect(link.locator('svg')).toHaveAttribute('fill','currentColor');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.route('https://github.com/mjcdata/ai-lab/tree/main/machine-learning/nba',r=>r.fulfill({body:'GitHub destination verified'}));
 await page.keyboard.press('Enter');await expect(page).toHaveURL('https://github.com/mjcdata/ai-lab/tree/main/machine-learning/nba');
});

test('a slow comparison response does not steal focus from a new search',async({page})=>{
 await page.route('**/snapshots/**/results/*/*.json',async route=>{
  await new Promise(resolve=>setTimeout(resolve,400));await route.continue();
 });
 await page.goto('/');await select(page);
 await expect(page.getByRole('heading',{name:'Finding statistical neighbors…'})).toBeVisible();
 await page.getByLabel(label).fill('Nikola');
 await expect(page.locator('.comparison')).toHaveCount(5);
 await expect(page.getByLabel(label)).toBeFocused();
 await expect(page.getByRole('button',{name:/Nikola Jokić/})).toBeVisible();
});
