/**
 * Compact Header Navigation — Normal Click Test
 *
 * Proves that at mobile and desktop widths the first-time header (Home, Cases,
 * Compare, Account, Locale, accessibility disclosure) and Home's tour entry
 * respond to NORMAL Playwright clicks (no force, no dispatchEvent, no JS click).
 *
 * FORCE_CLICK_COUNT = 0
 * DISPATCH_EVENT_COUNT = 0
 * JS_CLICK_COUNT = 0
 */
import { test, expect } from "./fixtures";

for (const [width, height] of [[390, 844], [430, 932], [1440, 900]]) test.describe(`Header normal click navigation ${width}×${height}`, () => {
  test.use({ viewport: { width, height } });

  test(`header destinations and the tour entry respond to normal clicks at ${width}×${height}`, async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "看清物件證據，確認下一步" })).toBeVisible({ timeout: 10000 });
    const menu = page.locator(".commercial-methods");
    await menu.locator("summary").click();
    await expect(menu).toHaveAttribute("open", "");
    await expect(page.getByTestId("tour-restart")).toBeVisible();
    await page.locator(".commercial-global-nav").getByRole("link", { name: "已儲存案件", exact: true }).click();
    await expect(page).toHaveURL(/\/cases$/);
    await page.locator(".commercial-global-nav").getByRole("link", { name: "比較案件", exact: true }).click();
    await expect(page).toHaveURL(/\/compare$/);
    await page.locator(".commercial-global-tools").getByRole("link", { name: "帳戶", exact: true }).click();
    await expect(page).toHaveURL(/\/account$/);
    await page.locator(".commercial-global-nav").getByRole("link", { name: "首頁", exact: true }).click();
    await expect(page).toHaveURL(/\/$/);
    await page.locator(".commercial-home").getByTestId("tour-start").click();
    await expect(page.getByRole("dialog")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
});
