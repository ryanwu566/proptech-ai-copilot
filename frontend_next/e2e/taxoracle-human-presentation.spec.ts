import { test, expect } from "./fixtures";
import type { Page } from "@playwright/test";

const locales = ["zh-TW", "en", "ja", "ko"];
const widths = [360, 390, 430];

async function openDemo(page: Page) {
  await page.goto("/");
  await page.getByTestId("competition-demo-start").getByRole("button").click();
  await expect(page.getByTestId("competition-demo")).toBeVisible();
}

test("TaxOracle demo is human-readable in every locale", async ({ page }) => {
  for (const locale of locales) {
    await page.goto("/");
    await page.getByRole("combobox", { name: /language|語言|言語|언어/i }).selectOption(locale);
    await page.getByTestId("competition-demo-start").getByRole("button").click();
    await page.getByTestId("demo-property-price").fill("2500");
    await page.locator("button.demo-calculate-button").click();
    await expect(page.getByTestId("human-tax-outcome")).toBeVisible();
    const body = await page.getByTestId("competition-demo").innerText();
    expect(body).not.toMatch(/sold_self_occupied|residency_condition_met|purchase_within_reasonable_period|compatibility-screening-v1|Risk score:|=true|=false/);
    await expect(page.getByTestId("human-holding-cost")).toContainText(/NT\$|NTD|新台幣|ニュー台湾|신대만/);
  }
});

for (const width of widths) {
  test(`TaxOracle demo has no horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openDemo(page);
    await page.getByTestId("demo-property-price").fill("2500");
    await page.locator("button.demo-calculate-button").click();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });
}
