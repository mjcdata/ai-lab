import { test, expect } from '@playwright/test';

test('live search, comparisons, explanations and both modes', async ({ page }) => {
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await expect(page).toHaveTitle('NBA Player Similarity');
  await expect(page.getByRole('heading', {level:1})).toHaveText('NBA Player Similarity');
  await expect(page.locator('.brand')).toContainText('NBA Player Similarity');
  await expect(page.getByRole('heading', {name:'Every player has a neighborhood.'})).toBeVisible();
  await page.getByLabel('Search the 2024–25 roster').fill('Curry');
  await page.getByRole('button',{name:/Stephen Curry/}).click();
  await expect(page.getByRole('heading',{name:'Stephen Curry',exact:true})).toBeVisible();
  await expect(page.locator('.comparison')).toHaveCount(5);
  await expect(page.locator('.comparison').first()).toContainText('Damian Lillard');
  await expect(page.locator('.comparison').first().locator('.score')).toContainText('0.809');
  await expect(page.locator('.comparison').first().locator('tbody tr')).toHaveCount(6);
  await page.locator('summary').first().click();
  await expect(page.locator('.contributions').first().locator('meter')).toHaveCount(6);
  await page.getByRole('button',{name:'Per game',exact:true}).click();
  await expect(page.getByRole('button',{name:'Per game',exact:true})).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('caption').first()).toContainText('Per-game');
  await expect(page.locator('.warnings')).toContainText('Limited playing time');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  expect(errors).toEqual([]);
});

test('no search results and a recoverable search failure', async ({page})=>{
 await page.goto('/');
 await page.getByLabel('Search the 2024–25 roster').fill('nobody-matches-this');
 await expect(page.getByText('No players found. Try a different name.')).toBeVisible();
 await page.route('**/api/players?**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Test API unavailable'})}));
 await page.getByLabel('Search the 2024–25 roster').fill('Curry');
 await expect(page.locator('main [role=alert]')).toContainText('Test API unavailable');
 await page.unroute('**/api/players?**');
 await page.getByRole('button',{name:'Retry search'}).click();
 await expect(page.getByRole('button',{name:/Stephen Curry/})).toBeVisible();
});

test('comparison loading, failure, recovery and empty candidates',async({page})=>{
 await page.goto('/');
 await page.getByLabel('Search the 2024–25 roster').fill('Bronny');
 await page.route('**/api/players/*/comparisons?**',async route=>{await new Promise(resolve=>setTimeout(resolve,500));await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Test comparison failure'})});});
 await page.getByRole('button',{name:/Bronny James/}).click();
 await expect(page.getByRole('heading',{name:'Finding statistical neighbors…'})).toBeVisible();
 await expect(page.locator('main [role=alert]')).toContainText('Test comparison failure');
 await page.unroute('**/api/players/*/comparisons?**');
 await page.getByRole('button',{name:'Retry comparisons'}).click();
 await expect(page.locator('.comparison')).toHaveCount(5);
 await page.route('**/api/players/*/comparisons?**',async route=>{
  const response=await route.fetch(); const data=await response.json();data.comparisons=[];data.candidate_count=0;
  await route.fulfill({response,json:data});
 });
 await page.getByRole('button',{name:'Per game',exact:true}).click();
 await expect(page.getByRole('heading',{name:'No eligible comparisons'})).toBeVisible();
});


test('reference statistics match API values in both modes and fit the viewport', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Search the 2024–25 roster').fill('Curry');
  await page.getByRole('button', { name: /Stephen Curry/ }).click();
  for (const [mode, button, label] of [
    ['per36', 'Per 36 min', 'Per-36 statistics'],
    ['per_game', 'Per game', 'Per-game statistics'],
  ]) {
    await page.getByRole('button', { name: button, exact: true }).click();
    await expect(page.locator('.reference-stats-label')).toHaveText(label);
    const response = await page.request.get(`/api/players/201939/comparisons?mode=${mode}`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    const cells = page.locator('.reference-stats > div');
    await expect(cells).toHaveCount(6);
    for (const [index, stat] of ['PTS', 'AST', 'REB', 'STL', 'BLK', 'TOV'].entries()) {
      await expect(cells.nth(index).locator('dt')).toHaveText(stat);
      const expected = data.reference[mode][stat].toLocaleString('en-US', {
        maximumFractionDigits: 2, minimumFractionDigits: 2,
      });
      await expect(cells.nth(index).locator('dd')).toHaveText(expected);
      // Reference values must also agree with comparison explanations.
      expect(data.comparisons[0].features[stat].reference).toBe(data.reference[mode][stat]);
    }
    expect(await page.locator('.reference-stats').evaluate(grid => {
      const bounds = grid.getBoundingClientRect();
      return bounds.left >= 0 && bounds.right <= window.innerWidth &&
        [...grid.children].every(cell => cell.scrollWidth <= cell.clientWidth);
    })).toBeTruthy();
  }
});
