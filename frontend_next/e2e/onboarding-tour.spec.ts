import { expect, test } from './fixtures';
import type { Page } from '@playwright/test';
import { isProviderRequest } from './helpers/provider-request';
import { e9Case } from '../lib/workspace/e9-test-fixtures';

const STEPS = ['createCase', 'confirmLocation', 'knownUnknown', 'marketRisk', 'questionsReport'];
const LAST = STEPS.length - 1;

/** Home exposes a visible "Start tour" entry; it never opens by itself. */
async function openTour(page: Page) {
  await page.locator('.commercial-home').getByTestId('tour-start').click();
  return page.getByRole('dialog');
}
function watchProviders(page: Page) {
  const requests: string[] = [];
  page.on('request', (request) => { if (isProviderRequest(request, page.url())) requests.push(request.url()); });
  return requests;
}
const record = (page: Page) => page.evaluate(() => JSON.parse(localStorage.getItem('proptech_onboarding_state') ?? 'null'));

test('Home exposes 開始導覽 in every locale and never auto-opens the tour for first-time or returning users', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  for (const [locale, label] of [['zh-TW', '開始導覽'], ['en', 'Start tour'], ['ja', 'ガイドを開始'], ['ko', '안내 시작']]) {
    await page.getByTestId('locale-switcher').first().selectOption(locale);
    await expect(page.locator('.commercial-home').getByTestId('tour-start')).toHaveText(label);
  }
  await page.reload();
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('live zh-TW → English → Japanese → Korean switches all tour copy and preserves first, middle, final steps', async ({ page }) => {
  await page.goto('/');
  const dialog = await openTour(page);
  const locale = dialog.getByTestId('locale-switcher');
  await expect(dialog).toHaveAttribute('data-step-id', 'createCase');
  await expect(dialog.getByRole('heading', { level: 2 })).toHaveText('從物件地址建立案件');
  await expect(dialog.locator('.onboarding-path li')).toHaveText(['1建立案件', '2確認位置', '3已知與未知', '4市場與風險', '5問題、比較與報告']);
  await locale.selectOption('en');
  await expect(dialog.getByRole('heading', { level: 2 })).toHaveText('Start a case from the property address');
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'knownUnknown');
  for (const [value, title, safe, next, previous, skip] of [
    ['zh-TW', '分開已知證據與未解決缺口', '未知不等於安全', '下一步', '上一步', '略過導覽'],
    ['en', 'Separate known evidence from open gaps', 'Unknown does not mean safe', 'Next', 'Back', 'Skip tour'],
    ['ja', '既知の資料と未解決の不足を分ける', '不明は安全を意味しません', '次へ', '前へ', 'ガイドをスキップ'],
    ['ko', '확보한 근거와 남은 공백 구분', '알 수 없음은 안전을 뜻하지 않습니다', '다음', '이전', '안내 건너뛰기'],
  ]) {
    await locale.focus();
    await locale.selectOption(value);
    await expect(locale).toBeFocused();
    await expect(dialog).toHaveAttribute('data-step-id', 'knownUnknown');
    await expect(dialog.getByRole('heading', { level: 2 })).toHaveText(title);
    await expect(dialog.locator('#tour-description')).toContainText(safe);
    await expect(dialog.getByTestId('tour-next')).toHaveText(next);
    await expect(dialog.getByTestId('tour-back')).toHaveText(previous);
    await expect(dialog.getByTestId('tour-skip')).toHaveText(skip);
    // Language option names deliberately retain their native spelling.
    if (value === 'en') for (const region of ['.onboarding-title', '.onboarding-path', '.onboarding-context', '.onboarding-footer']) {
      await expect(dialog.locator(region)).not.toContainText(/[㐀-鿿぀-ヿ가-힣]/);
    }
  }
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'marketRisk');
  await locale.selectOption('en');
  await expect(dialog.locator('#tour-description')).toContainText('not a formal appraisal');
  await expect(dialog.locator('#tour-description')).toContainText('no matching record does not mean no risk');
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'questionsReport');
  await expect(dialog.getByTestId('tour-next')).toHaveText('Start a case');
  await locale.selectOption('zh-TW');
  await expect(dialog.getByTestId('tour-next')).toHaveText('開始建立案件');
  await dialog.getByTestId('tour-back').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'marketRisk');
});

test('skip, Escape, finish CTA, restart and browser reopen keep completion state with zero provider calls', async ({ page, context, browser }) => {
  await page.goto('/');
  await page.getByTestId('locale-switcher').selectOption('en');
  const requests = watchProviders(page);
  let dialog = await openTour(page);
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('locale-switcher').selectOption('ja');
  await expect(dialog).toHaveAttribute('data-step-id', 'confirmLocation');
  await dialog.getByTestId('tour-back').click();
  await dialog.getByTestId('tour-skip').click();
  expect(await record(page)).toEqual({ version: '4', status: 'skipped' });
  dialog = await openTour(page);
  await expect(dialog).toHaveAttribute('data-step-id', 'createCase');
  await dialog.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(page.locator('.commercial-home').getByTestId('tour-start')).toBeFocused();
  // The accessibility panel keeps its restart entry.
  await page.locator('.commercial-methods > summary').click();
  await page.getByTestId('tour-restart').click();
  for (let i = 0; i < LAST; i++) await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).not.toBeVisible();
  expect(await record(page)).toEqual({ version: '4', status: 'completed' });
  dialog = await openTour(page);
  for (let i = 0; i < LAST; i++) await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).not.toBeVisible();
  // Home's CTA ends on the address field instead of creating anything.
  await expect(page.locator('#commercial-address')).toBeFocused();
  await expect(page).toHaveURL(/\/$/);
  expect(requests).toEqual([]);
  const restoredContext = await browser.newContext({ storageState: await context.storageState() });
  const reopened = await restoredContext.newPage();
  await reopened.goto('/');
  await expect(reopened.getByRole('dialog')).not.toBeVisible();
  expect(await record(reopened)).toEqual({ version: '4', status: 'completed' });
  const restarted = await openTour(reopened);
  await expect(restarted).toHaveAttribute('data-step-id', 'createCase');
  await restoredContext.close();
});

test('Case header exposes 開始導覽; its CTA opens the example case with zero provider calls and returns focus', async ({ page }) => {
  await page.addInitScript((cases) => localStorage.setItem('proptech.savedCases.v1', JSON.stringify(cases)), [e9Case()]);
  await page.goto('/cases/case-a/overview');
  const entry = page.locator('.workspace-property-header').getByTestId('tour-start');
  await expect(entry).toHaveText('開始導覽');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  const requests = watchProviders(page);
  await entry.click();
  const dialog = page.getByRole('dialog');
  for (let i = 0; i < LAST; i++) await dialog.getByTestId('tour-next').click();
  await expect(dialog.getByTestId('tour-next')).toHaveText('開啟示範案件');
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).toHaveAttribute('data-demo', 'true');
  await expect(dialog.getByTestId('demo-disclosure')).toBeVisible();
  for (let i = 0; i < LAST; i++) await dialog.getByTestId('tour-next').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'questionsReport');
  await dialog.getByTestId('demo-exit').click();
  await expect(dialog).not.toBeVisible();
  await expect(entry).toBeFocused();
  expect(requests).toEqual([]);
});

for (const width of [390, 430, 1024, 1440]) {
  test(`${width}px card has reachable controls and readable copy through every locale and step without a DOM target`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    const dialog = await openTour(page);
    for (const locale of ['zh-TW', 'en', 'ja', 'ko']) {
      await dialog.getByTestId('locale-switcher').selectOption(locale);
      for (let step = 0; step <= LAST; step++) {
        await expect(dialog).toHaveAttribute('data-step-id', STEPS[step]);
        // Measure the same four elements in one browser round trip for each step.
        const layout = await dialog.evaluate((element) => ({
          bounds: [element, element.querySelector('[data-testid="tour-skip"]'), element.querySelector('[data-testid="tour-next"]'), element.querySelector('[data-testid="locale-switcher"]')].map((control) => {
            if (!control) return null;
            const { x, y, width, height } = control.getBoundingClientRect();
            return { x, y, width, height, visible: getComputedStyle(control).visibility === 'visible' };
          }),
          dialogFits: element.scrollWidth <= element.clientWidth,
          documentFits: document.documentElement.scrollWidth <= innerWidth,
        }));
        for (const bounds of layout.bounds) {
          expect(bounds).not.toBeNull();
          expect(bounds!.visible).toBe(true);
          expect(bounds!.width).toBeGreaterThan(0);
          expect(bounds!.height).toBeGreaterThan(0);
          expect(bounds!.x).toBeGreaterThanOrEqual(0);
          expect(bounds!.y).toBeGreaterThanOrEqual(0);
          expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
          expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(844);
        }
        expect(layout.dialogFits).toBe(true);
        expect(layout.documentFits).toBe(true);
        if (step < LAST) await dialog.getByTestId('tour-next').click();
      }
      if (locale === 'en') {
        const screenshot = testInfo.outputPath(`tour-${width}.png`);
        await page.screenshot({ path: screenshot });
        await testInfo.attach(`tour-${width}`, { path: screenshot, contentType: 'image/png' });
      }
      for (let step = 0; step < LAST; step++) await dialog.getByTestId('tour-back').click();
    }
    await expect(page.locator('[data-tour-target]')).toHaveCount(0);
    await expect(dialog.getByTestId('tour-context-note')).toBeVisible();
  });
}

test('keyboard-only completion traps focus, Escape releases the modal and focus returns to the opener', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('locale-switcher').selectOption('en');
  const entry = page.locator('.commercial-home').getByTestId('tour-start');
  await entry.focus();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { level: 2 })).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(dialog.getByTestId('tour-next')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(dialog.getByTestId('locale-switcher')).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(dialog.getByTestId('tour-next')).toBeFocused();
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press('Tab');
    expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  }
  await dialog.getByRole('heading', { level: 2 }).focus();
  for (let i = 0; i <= LAST; i++) {
    for (let tab = 0; tab < 5 && !await dialog.getByTestId('tour-next').evaluate((element) => document.activeElement === element); tab++) await page.keyboard.press('Tab');
    await expect(dialog.getByTestId('tour-next')).toBeFocused();
    await page.keyboard.press('Enter');
  }
  await expect(dialog).not.toBeVisible();
  await expect(page.locator('#commercial-address')).toBeFocused();
  await entry.focus();
  await page.keyboard.press('Enter');
  await expect(dialog).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(entry).toBeFocused();
  await expect(entry).toBeInViewport();
});

test('reduced motion removes tour animation while preserving navigation and live language switching', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const dialog = await openTour(page);
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('locale-switcher').selectOption('en');
  await expect(dialog).toHaveAttribute('data-step-id', 'confirmLocation');
  expect(await dialog.evaluate((element) => [element, ...element.querySelectorAll('*')].every((node) => getComputedStyle(node).animationName === 'none'))).toBe(true);
  await dialog.getByTestId('tour-skip').click();
  await expect(dialog).not.toBeVisible();
});
