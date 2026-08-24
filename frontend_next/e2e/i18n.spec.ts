import { expect, test } from "./fixtures";

async function openMap(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Map Insight", exact: true }).click();
  await expect(page.getByTestId("map-search-form")).toBeVisible();
  const advanced = page.getByTestId("map-advanced-settings");
  await advanced.locator("summary").click();
  await expect(advanced).toHaveAttribute("open", "");
}

test("four locale runtime changes document language and visible navigation", async ({ page }) => {
  await page.goto("/");
  const locale = page.locator("select").first();
  for (const [value, lang] of [["zh-TW", "zh-TW"], ["en", "en"], ["ja", "ja"], ["ko", "ko"]] as const) {
    await locale.selectOption(value);
    await expect.poll(() => page.locator("html").getAttribute("lang")).toBe(lang);
    await expect(page.locator("aside[aria-label]").first()).toBeVisible();
    await expect(page.locator("#main-content")).toBeVisible();
  }
});

test("Daxi road options render meaningful names in every locale and preserve canonical values", async ({ page }) => {
  await openMap(page);
  const locale = page.getByTestId("locale-switcher");
  const advanced = page.getByTestId("map-advanced-settings");
  const county = advanced.locator('select:has(option[value="桃園市"])');
  await county.selectOption("桃園市");
  const district = advanced.locator('select:has(option[value="大溪區"])');
  await district.selectOption("大溪區");
  const roads = advanced.locator('select:has(option[value="三元二街"])');
  await expect(roads.locator("option")).toHaveCount(31);
  const canonical = "三元二街";
  await roads.selectOption(canonical);
  for (const [value, pattern] of [["zh-TW", /三元二街/], ["en", /Sanyuan 2nd Street/], ["ja", /[ァ-ヶ]/], ["ko", /[가-힣]/]] as const) {
    await locale.selectOption(value);
    await expect(roads.locator(`option[value="${canonical}"]`)).toHaveCount(1);
    await expect(roads).toHaveValue(canonical);
    await expect(roads.locator(`option[value="${canonical}"]`)).toContainText(pattern);
    await expect(roads.locator("option").evaluateAll((options) => options.slice(1).every((option) => !option.textContent?.startsWith("Official road name")))).toBeTruthy();
  }
});

test("localized map open action is rendered and remains responsive", async ({ page }) => {
  await openMap(page);
  const locale = page.getByTestId("locale-switcher");
  const advanced = page.getByTestId("map-advanced-settings");
  for (const [value, label] of [["en", "Open"], ["ja", "開く"], ["ko", "열기"]] as const) {
    await locale.selectOption(value);
    await expect(advanced.getByRole("button", { name: label, exact: true })).toBeVisible();
  }
});
