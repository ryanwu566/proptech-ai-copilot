import { expect, test } from './fixtures';
import type { Page } from '@playwright/test';

async function openTour(page: Page) {
  await page.locator('.commercial-methods > summary').click();
  await page.locator('.ds-disclosure > summary').click();
  await page.locator('.commercial-accessibility-controls button').last().click();
  return page.getByRole('dialog');
}

test('live zh-TW → English → Japanese → Korean switches all tour copy and preserves first, middle, final steps', async ({ page }) => {
  await page.goto('/');
  const documentToken = await page.evaluate(() => {
    document.documentElement.dataset.tourDocument = crypto.randomUUID();
    return document.documentElement.dataset.tourDocument;
  });
  const dialog = await openTour(page);
  const locale = dialog.getByTestId('locale-switcher');
  await expect(locale).toBeVisible();
  await expect(dialog).toHaveAttribute('data-step-id', 'propertyCase');
  await locale.selectOption('en');
  await expect(dialog.getByRole('heading', { level: 2 })).toHaveText('Establish the property case');
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('tour-next').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'locationCommute');
  for (const [value, title, next, previous, skip] of [
    ['zh-TW', '確認生活圈與通勤', '下一步', '上一步', '略過導覽'],
    ['en', 'Check location and commute', 'Next', 'Back', 'Skip tour'],
    ['ja', '生活圏と通勤を確認', '次へ', '前へ', 'ガイドをスキップ'],
    ['ko', '입지와 통근 확인', '다음', '이전', '안내 건너뛰기'],
  ]) {
    await locale.focus();
    await locale.selectOption(value);
    await expect(locale).toBeFocused();
    await expect(dialog).toHaveAttribute('data-step-id', 'locationCommute');
    await expect(dialog.getByRole('heading', { level: 2 })).toHaveText(title);
    await expect(dialog.getByTestId('tour-next')).toHaveText(next);
    await expect(dialog.getByTestId('tour-back')).toHaveText(previous);
    await expect(dialog.getByTestId('tour-skip')).toHaveText(skip);
    // Language option names deliberately retain their native spelling.
    if (value === 'en') for (const region of ['.onboarding-title', '.onboarding-path', '.onboarding-context', '.onboarding-footer']) {
      await expect(dialog.locator(region)).not.toContainText(/[\u3400-\u9fff\u3040-\u30ff가-힣]/);
    }
  }
  for (let i = 0; i < 4; i++) await dialog.getByTestId('tour-next').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'saveCompareReport');
  await locale.selectOption('en');
  await expect(dialog.getByTestId('tour-next')).toHaveText('Finish');
  await dialog.getByTestId('tour-back').click();
  await expect(dialog).toHaveAttribute('data-step-id', 'verificationChecklist');
  // Next startup history.replaceState also emits framenavigated; document identity tests reloads directly.
  expect(await page.evaluate(() => document.documentElement.dataset.tourDocument)).toBe(documentToken);
});

test('skip, Escape, finish, restart and browser reopen preserve locale-independent completion without provider calls', async ({ page, context, browser }) => {
  await page.goto('/');
  await page.getByTestId('locale-switcher').selectOption('en');
  const requests: string[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    const sameOrigin = url.origin === new URL(page.url()).origin;
    // Known shell Link prefetches are frontend route payloads, not provider requests.
    const frontendRoutePayload = sameOrigin && request.method() === 'GET' && request.headers().rsc === '1' &&
      url.searchParams.has('_rsc') && ['/', '/cases', '/vnext/property-identity'].includes(url.pathname);
    if (!frontendRoutePayload && (['fetch', 'xhr'].includes(request.resourceType()) || !sameOrigin)) requests.push(request.url());
  });
  let dialog = await openTour(page);
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('locale-switcher').selectOption('ja');
  await expect(dialog).toHaveAttribute('data-step-id', 'marketEvidence');
  await dialog.getByTestId('tour-back').click();
  await dialog.getByTestId('tour-skip').click();
  const record = () => page.evaluate(() => JSON.parse(localStorage.getItem('proptech_onboarding_state') ?? 'null'));
  expect(await record()).toEqual({ version: '3', status: 'skipped' });
  await page.getByTestId('locale-switcher').selectOption('ko');
  expect(await record()).toEqual({ version: '3', status: 'skipped' });
  await page.getByTestId('tour-restart').click();
  dialog = page.getByRole('dialog');
  await expect(dialog).toHaveAttribute('data-step-id', 'propertyCase');
  await dialog.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(page.getByTestId('tour-restart')).toBeFocused();
  await page.getByTestId('tour-restart').click();
  for (let i = 0; i < 6; i++) await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('tour-next').click();
  expect(await record()).toEqual({ version: '3', status: 'completed' });
  await page.getByTestId('locale-switcher').selectOption('ja');
  expect(await record()).toEqual({ version: '3', status: 'completed' });
  expect(requests).toEqual([]);
  const restoredContext = await browser.newContext({ storageState: await context.storageState() });
  const reopened = await restoredContext.newPage();
  await reopened.goto('/');
  await reopened.getByTestId('locale-switcher').selectOption('en');
  await expect(reopened.getByRole('dialog')).not.toBeVisible();
  expect(await reopened.evaluate(() => JSON.parse(localStorage.getItem('proptech_onboarding_state') ?? 'null'))).toEqual({ version: '3', status: 'completed' });
  const restarted = await openTour(reopened);
  await expect(restarted).toHaveAttribute('data-step-id', 'propertyCase');
  await expect(restarted.getByRole('heading', { level: 2 })).toHaveText('Establish the property case');
  await restoredContext.close();
});

for (const width of [390, 1024, 1440]) {
  test(`${width}px card has reachable controls and readable copy through every locale and step without a DOM target`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    const dialog = await openTour(page);
    for (const locale of ['zh-TW', 'en', 'ja', 'ko']) {
      await dialog.getByTestId('locale-switcher').selectOption(locale);
      for (let step = 0; step < 7; step++) {
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
        if (step < 6) await dialog.getByTestId('tour-next').click();
      }
      if (locale === 'en') {
        const screenshot = testInfo.outputPath(`tour-${width}.png`);
        await page.screenshot({ path: screenshot });
        await testInfo.attach(`tour-${width}`, { path: screenshot, contentType: 'image/png' });
      }
      for (let step = 0; step < 6; step++) await dialog.getByTestId('tour-back').click();
    }
    await expect(page.locator('[data-tour-target]')).toHaveCount(0);
    await expect(dialog.getByTestId('tour-context-note')).toBeVisible();
  });
}

test('keyboard-only completion transfers focus and Escape releases the modal', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('locale-switcher').selectOption('en');
  await page.locator('.commercial-methods > summary').focus();
  await page.keyboard.press('Enter');
  await page.locator('.ds-disclosure > summary').focus();
  await page.keyboard.press('Enter');
  await page.locator('.commercial-accessibility-controls button').last().focus();
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
  for (let i = 0; i < 7; i++) {
    for (let tab = 0; tab < 5 && !await dialog.getByTestId('tour-next').evaluate((element) => document.activeElement === element); tab++) await page.keyboard.press('Tab');
    await expect(dialog.getByTestId('tour-next')).toBeFocused();
    await page.keyboard.press('Enter');
  }
  await expect(dialog).not.toBeVisible();
  await expect(page.getByTestId('tour-restart')).toBeFocused();
  await page.keyboard.press('Enter');
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(page.getByTestId('tour-restart')).toBeFocused();
});

test('reduced motion removes tour animation while preserving navigation and live language switching', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const dialog = await openTour(page);
  await dialog.getByTestId('tour-next').click();
  await dialog.getByTestId('locale-switcher').selectOption('en');
  await expect(dialog).toHaveAttribute('data-step-id', 'marketEvidence');
  expect(await dialog.evaluate((element) => [element, ...element.querySelectorAll('*')].every((node) => getComputedStyle(node).animationName === 'none'))).toBe(true);
  await dialog.getByTestId('tour-skip').click();
  await expect(dialog).not.toBeVisible();
});
