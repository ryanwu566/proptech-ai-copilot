import { expect, test, type Page } from '@playwright/test';
import { e9Case } from '../lib/workspace/e9-test-fixtures';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

const stages = ['propertyCase', 'marketEvidence', 'locationCommute', 'terrainRisk', 'finance', 'verificationChecklist', 'saveCompareReport'];
async function start(page: Page) {
  await page.getByTestId('demo-start').click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toHaveAttribute('data-demo', 'true');
  return dialog;
}
async function snapshot(page: Page) {
  return page.evaluate(() => {
    const read = (storage: Storage) => Object.fromEntries(Object.keys(storage).filter(k => k !== 'proptech_onboarding_state').sort().map(k => [k, storage.getItem(k)]));
    return { local: read(localStorage), session: read(sessionStorage) };
  });
}
async function seed(page: Page) {
  await page.addInitScript((cases) => {
    localStorage.setItem('proptech.savedCases.v1', JSON.stringify(cases));
    sessionStorage.setItem('proptech:holding-cost-result', JSON.stringify({ monthly_total_holding_cost: 45678 }));
    localStorage.setItem('demo-test:compare-selection', 'case-a,case-b');
    localStorage.setItem('proptech_onboarding_state', JSON.stringify({ version: '3', status: 'completed' }));
  }, [e9Case(), e9Case('case-b')]);
}

test('synthetic full journey, Back, locale, Restart, Exit and Finish make zero provider requests and preserve real storage', async ({ page, baseURL }) => {
  await seed(page);
  const providers: string[] = [];
  const diagnostics: string[] = [];
  page.on('pageerror', error => diagnostics.push(error.message));
  // Observe before navigation; never fulfill analysis/provider requests with fake results.
  page.on('request', request => {
    const url = new URL(request.url());
    const sameOrigin = url.origin === new URL(baseURL!).origin;
    const routePayload = sameOrigin && request.method() === 'GET' && request.headers().rsc === '1' && url.searchParams.has('_rsc') &&
      (['/', '/cases', '/vnext/property-identity'].includes(url.pathname) || /^\/cases\/[^/]+\/overview$/.test(url.pathname));
    if (!sameOrigin || (!routePayload && ['fetch', 'xhr'].includes(request.resourceType()))) providers.push(request.url());
  });
  await page.goto('/');
  await page.locator('#commercial-address').fill('Preserve my real property draft');
  const before = await snapshot(page);
  await page.evaluate(() => {
    const writes: string[] = [];
    const events: string[] = [];
    Object.assign(window, { demoStorageWrites: writes, demoCaseEvents: events });
    for (const name of ['proptech:saved-case-loaded', 'proptech:saved-case-updated', 'proptech:current-case-cleared']) window.addEventListener(name, () => events.push(name));
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function(key, value) { if (key !== 'proptech_onboarding_state') writes.push(key); return original.call(this, key, value); };
  });
  let dialog = await start(page);
  await expect(dialog.getByTestId('demo-address')).toHaveValue('臺灣示範市虛構區示例巷18號');
  await expect(dialog.getByTestId('demo-created')).toBeVisible();
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('tour-back').click();
  await expect(dialog.getByTestId('demo-created')).toBeVisible();
  for (let i = 0; i < 4; i++) await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('demo-down').fill('45');
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('demo-review').check();
  await expect(dialog).toContainText('個人核對不代表官方查證');
  await expect(dialog).toContainText('未知');
  await dialog.getByTestId('locale-switcher').selectOption('en');
  await expect(dialog).toHaveAttribute('data-step-id', 'verificationChecklist');
  await expect(dialog.getByTestId('demo-review')).toBeChecked();
  expect(await snapshot(page)).toEqual(before);
  await expect(page.locator('#commercial-address')).toHaveValue('Preserve my real property draft');
  await dialog.getByTestId('demo-restart').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'propertyCase');
  for (let i = 0; i < 4; i++) await dialog.getByTestId('tour-next').click();
  await expect(dialog.getByTestId('demo-down')).toHaveValue('30');
  await dialog.getByTestId('tour-next').click();
  await expect(dialog.getByTestId('demo-review')).not.toBeChecked();
  await dialog.getByTestId('demo-exit').click();
  await expect(page.getByTestId('demo-start')).toBeFocused();
  expect(await snapshot(page)).toEqual(before);
  dialog = await start(page);
  for (let i = 0; i < 6; i++) await dialog.getByTestId('tour-next').click();
  await expect(dialog).toContainText('Example report preview');
  await expect(dialog).toContainText('Unknown · not queried');
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).not.toBeVisible();
  expect(await snapshot(page)).toEqual(before);
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('proptech_onboarding_state')!))).toEqual({ version: '3', status: 'completed' });
  expect(providers).toEqual([]);
  expect(await page.evaluate(() => (window as unknown as { demoStorageWrites: string[] }).demoStorageWrites)).toEqual([]);
  expect(await page.evaluate(() => (window as unknown as { demoCaseEvents: string[] }).demoCaseEvents)).toEqual([]);
  expect(diagnostics).toEqual([]);
});

test('simulation JavaScript and CSS stay unloaded until the example is activated', async ({ page }) => {
  const chunks = path.resolve('.next/static/chunks');
  const demoFiles = readdirSync(chunks).filter(name => name.endsWith('.js') && readFileSync(path.join(chunks, name), 'utf8').includes('demo:guided-case:v1'));
  expect(demoFiles.length).toBeGreaterThan(0);
  const demoCss = readdirSync(chunks).filter(name => name.endsWith('.css') && readFileSync(path.join(chunks, name), 'utf8').includes('.simulation-dialog'));
  expect(demoCss.length).toBeGreaterThan(0);
  const loaded: string[] = [];
  page.on('request', request => loaded.push(new URL(request.url()).pathname));
  await page.goto('/');
  expect(loaded.some(url => demoFiles.some(file => url.endsWith(`/${file}`)))).toBe(false);
  expect(loaded.some(url => demoCss.some(file => url.endsWith(`/${file}`)))).toBe(false);
  await start(page);
  expect(loaded.some(url => demoFiles.some(file => url.endsWith(`/${file}`)))).toBe(true);
  expect(loaded.some(url => demoCss.some(file => url.endsWith(`/${file}`)))).toBe(true);
});

test('lazy loading preserves the initiating button for focus restoration', async ({ page }) => {
  const chunks = path.resolve('.next/static/chunks');
  const files = readdirSync(chunks).filter(name => name.endsWith('.js') && readFileSync(path.join(chunks, name), 'utf8').includes('demo:guided-case:v1'));
  let release: () => void = () => {};
  let requested = false;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/_next/static/chunks/*.js', async route => {
    if (files.some(file => route.request().url().endsWith(`/${file}`))) { requested = true; await pending; }
    await route.continue();
  });
  await page.goto('/');
  await page.getByTestId('demo-start').click();
  await expect.poll(() => requested).toBe(true);
  // Deliberately move focus before the lazy module mounts, rather than rely on timing.
  await page.locator('[data-page-heading]').focus();
  release();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await dialog.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(page.getByTestId('demo-start')).toBeFocused();
});

test('live locale switching during input and middle/final stages preserves semantic state and focus', async ({ page }) => {
  await page.goto('/');
  const dialog = await start(page);
  const locale = dialog.getByTestId('locale-switcher');
  await locale.focus();
  await locale.selectOption('en');
  await expect(locale).toBeFocused();
  await expect(dialog.getByTestId('demo-address')).toHaveValue('No. 18, Example Lane, Fictional District, Taiwan');
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('tour-next').click();
  for (const lang of ['en', 'ja', 'ko', 'zh-TW']) {
    await locale.focus(); await locale.selectOption(lang);
    await expect(locale).toBeFocused();
    await expect(dialog).toHaveAttribute('data-step-id', 'locationCommute');
    if (lang === 'en') expect(await dialog.locator('.onboarding-body, .simulation-disclosure, .onboarding-footer, .onboarding-title').allTextContents()).not.toEqual(expect.arrayContaining([expect.stringMatching(/[\u3400-\u9fff\u3040-\u30ff가-힣]/)]));
    expect(await page.evaluate(() => localStorage.getItem('proptech_onboarding_state'))).toBeNull();
  }
  for (let i = 0; i < 4; i++) await dialog.getByTestId('tour-next').click();
  await locale.selectOption('ja');
  await expect(dialog).toContainText('例のレポートプレビュー');
  await locale.selectOption('ko');
  await expect(dialog).toContainText('예시 보고서 미리보기');
  await expect(dialog).toHaveAttribute('data-step-id', 'saveCompareReport');
});

for (const width of [390, 1024, 1440]) test(`${width}px every stage and locale has visible disclosure, reachable actions and no overflow`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 844 });
  await page.goto('/');
  const dialog = await start(page);
  for (const locale of ['zh-TW', 'en', 'ja', 'ko']) {
    await dialog.getByTestId('locale-switcher').selectOption(locale);
    for (let index = 0; index < 7; index++) {
      await expect(dialog).toHaveAttribute('data-step-id', stages[index]);
      const geometry = await dialog.evaluate(element => {
        const controls = ['[data-testid="tour-next"]', '[data-testid="tour-back"]', '[data-testid="demo-exit"]', '[data-testid="demo-restart"]', '[data-testid="demo-disclosure"]', '[aria-current="step"]'];
        return { fits: element.scrollWidth <= element.clientWidth && document.documentElement.scrollWidth <= innerWidth,
          bounds: controls.map(selector => {
            const node = element.querySelector(selector)!; const rect = node.getBoundingClientRect();
            return { x: rect.x, y: rect.y, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height, visible: getComputedStyle(node).display !== 'none' };
          }) };
      });
      expect(geometry.fits).toBe(true);
      for (const rect of geometry.bounds) {
        expect(rect.visible).toBe(true); expect(rect.width).toBeGreaterThan(0); expect(rect.height).toBeGreaterThan(0);
        expect(rect.x).toBeGreaterThanOrEqual(0); expect(rect.y).toBeGreaterThanOrEqual(0);
        expect(rect.right).toBeLessThanOrEqual(width); expect(rect.bottom).toBeLessThanOrEqual(844);
      }
      if (index === 0) await expect(dialog.getByTestId('demo-address')).toBeVisible();
      if (locale === 'en') await page.screenshot({ path: info.outputPath(`demo-${width}-${stages[index]}.png`) });
      if (index < 6) await dialog.getByTestId('tour-next').click();
    }
    for (let index = 0; index < 6; index++) await dialog.getByTestId('tour-back').click();
  }
  await dialog.getByTestId('tour-next').click();
});

test('keyboard-only journey uses finance/review controls, finishes and restores focus; Escape exits', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('demo-start').focus(); await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { level: 2 })).toBeFocused();
  for (let index = 0; index < 7; index++) {
    if (index === 4) { await dialog.getByTestId('demo-down').focus(); await page.keyboard.press('ArrowRight'); await expect(dialog.getByTestId('demo-down')).toHaveValue('35'); }
    if (index === 5) { await dialog.getByTestId('demo-review').focus(); await page.keyboard.press('Space'); await expect(dialog.getByTestId('demo-review')).toBeChecked(); }
    // Use only keyboard to reach Next, including the native read-only address field.
    for (let tab = 0; tab < 12 && !await dialog.getByTestId('tour-next').evaluate(e => e === document.activeElement); tab++) await page.keyboard.press('Tab');
    await expect(dialog.getByTestId('tour-next')).toBeFocused(); await page.keyboard.press('Enter');
  }
  await expect(dialog).not.toBeVisible(); await expect(page.getByTestId('demo-start')).toBeFocused();
  await page.keyboard.press('Enter'); await expect(dialog).toBeVisible(); await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible(); await expect(page.getByTestId('demo-start')).toBeFocused();
});

test('reduced motion reveals final input immediately and removes all animated transitions through completion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' }); await page.goto('/');
  const dialog = await start(page);
  await expect(dialog.getByTestId('demo-address')).toHaveValue('臺灣示範市虛構區示例巷18號');
  await expect(dialog.getByTestId('demo-skip-typing')).toHaveCount(0);
  for (let index = 0; index < 7; index++) {
    expect(await dialog.evaluate(e => [e, ...e.querySelectorAll('*')].every(n => getComputedStyle(n).animationName === 'none' && getComputedStyle(n).transitionDuration.split(',').every(v => parseFloat(v) === 0)))).toBe(true);
    await dialog.getByTestId('tour-next').click();
  }
  await expect(dialog).not.toBeVisible();
});

test('Skip and Escape work with blocked storage; typing can be skipped and restart cancels its clock', async ({ page }) => {
  await page.addInitScript(() => { Storage.prototype.setItem = () => { throw new Error('blocked'); }; });
  await page.goto('/');
  let dialog = await start(page);
  if (await dialog.getByTestId('demo-skip-typing').isVisible()) await dialog.getByTestId('demo-skip-typing').click();
  await expect(dialog.getByTestId('demo-created')).toBeVisible();
  await dialog.getByTestId('demo-restart').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'propertyCase');
  await dialog.getByTestId('tour-skip').click(); await expect(dialog).not.toBeVisible();
  dialog = await start(page); await page.keyboard.press('Escape'); await expect(dialog).not.toBeVisible();
});
