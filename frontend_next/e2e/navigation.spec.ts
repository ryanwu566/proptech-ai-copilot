import { expect, test } from "./fixtures";

test("sidebar tools navigate without replacing the main shell", async ({ page }) => {
  await page.goto("/");
  const destinations = [/Map|地圖|地図|지도/i, /Terrain|地勢|地形|재해/i, /TaxOracle/i, /Aegis|貸款|ローン|대출/i, /Market|市場|시장/i];
  for (const destination of destinations) {
    const button = page.getByRole("button", { name: destination }).first();
    await expect(button).toBeVisible();
    await button.click();
    await expect(page.locator("[data-page-heading]")).toBeVisible();
    await expect(page.locator("main")).toBeVisible();
  }
});

test("navigation moves focus to the new page heading", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Map|地圖|地図|지도/i }).first().click();
  await expect.poll(() => page.evaluate(() => document.activeElement?.hasAttribute("data-page-heading"))).toBe(true);
});
