import { expect, test } from "./fixtures";

test("four locale runtime changes document language and visible navigation", async ({ page }) => {
  await page.goto("/");
  const locale = page.getByRole("combobox", { name: /language|語言|言語|언어/i });
  for (const [value, lang] of [["zh-TW", "zh-TW"], ["en", "en"], ["ja", "ja"], ["ko", "ko"]] as const) {
    await locale.selectOption(value);
    await expect.poll(() => page.locator("html").getAttribute("lang")).toBe(lang);
    await expect(page.locator("aside[aria-label]").first()).toBeVisible();
    await expect(page.locator("#main-content")).toBeVisible();
  }
});

test("map labels keep canonical option values while changing display locale", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Map|地圖|地図|지도/i }).first().click();
  await page.getByRole("combobox", { name: /市|県|county|city/i }).first().selectOption("臺北市");
  await page.getByRole("combobox", { name: /區|郡|district/i }).first().selectOption("信義區");
  const roads = page.getByRole("combobox", { name: /道路|路段|road|도로/i }).first();
  await expect(roads.locator("option[value='市府路']")).toHaveCount(1);
  await expect(roads.locator("option[value='市府路']")).toHaveAttribute("value", "市府路");
});
