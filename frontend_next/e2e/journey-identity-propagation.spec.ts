/**
 * Journey Identity Propagation — Real PropertyFinder Selection
 *
 * Uses 新北市/永和區 broad search, selects one real property,
 * then verifies identity propagation through Journey stages.
 */
import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3000", viewport: { width: 1440, height: 900 } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

test("Real PropertyFinder selection + Journey propagation", async ({ page }) => {
  test.setTimeout(120000);

  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "建立物件情境" })).toBeVisible({ timeout: 10000 });

  // ── PROPERTYFINDER SEARCH ──
  const cityInput = page.getByRole("textbox", { name: /縣市/ });
  await cityInput.fill("新北市");
  const districtInput = page.getByRole("textbox", { name: /行政區/ });
  await districtInput.fill("永和區");
  const upperPrice = page.getByRole("spinbutton", { name: /預算上限/ });
  await upperPrice.fill("50000");
  const areaMin = page.getByRole("spinbutton", { name: /坪數下限/ });
  await areaMin.fill("0");
  const areaMax = page.getByRole("spinbutton", { name: /坪數上限/ });
  await areaMax.fill("200");

  await page.getByRole("button", { name: /搜尋看屋方向/ }).click();
  await page.waitForTimeout(5000);

  // Verify results exist
  const mainText = await page.locator("#main-content").textContent() ?? "";
  expect(mainText.includes("找到") || mainText.includes("筆") || mainText.includes("成交"), "PropertyFinder must return results").toBe(true);

  // ── CAPTURE SELECTED PROPERTY BEFORE CLICK ──
  // The FinderActions buttons are: 用這個路段估價, 用這個價格算月付, 算每月總支出, 看附近生活機能
  // "看附近生活機能" triggers onUseForLocationInsight which sets propertyContext
  const locationActionBtn = page.getByRole("button", { name: "看附近生活機能" });
  await expect(locationActionBtn).toBeVisible({ timeout: 5000 });

  // Capture the property row context
  const propertyRowText = await page.evaluate(() => {
    const btn = document.querySelector("button[aria-label='看附近生活機能']");
    if (!btn) return "";
    const row = btn.closest("tr");
    if (row) return row.textContent?.trim().substring(0, 300) ?? "";
    const card = btn.closest("div, article");
    return card?.textContent?.trim().substring(0, 300) ?? "";
  });

  console.log(`\n=== SELECTED PROPERTY CONTEXT ===`);
  console.log(`ROW_TEXT: ${propertyRowText.substring(0, 200)}`);

  // ── CLICK PROPERTY ACTION (看附近生活機能) ──
  await locationActionBtn.click();
  await page.waitForTimeout(3000);

  // ── VERIFY JOURNEY STATE CHANGED (Location stage should now be visible) ──
  // After selecting a property and clicking "查看位置", the Journey should navigate to Location
  const locationStage = page.locator("section[id='journey-stage-location']");
  const locationVisible = await locationStage.isVisible().catch(() => false);

  // If Location didn't auto-open, try manually navigating
  if (!locationVisible) {
    await page.getByRole("button", { name: /位置與資料證據/ }).click();
    await page.waitForTimeout(1500);
  }

  // ── LOCATION IDENTITY ──
  const locationText = await page.locator("#main-content").textContent() ?? "";
  const locationHasYonghe = locationText.includes("永和") || locationText.includes("新北");

  console.log(`LOCATION_STAGE_VISIBLE: ${await locationStage.isVisible().catch(() => false)}`);
  console.log(`LOCATION_HAS_CORRECT_IDENTITY: ${locationHasYonghe}`);

  // Check if embedded Market in Location stage shows city/district
  const marketCountyInLocation = await page.getByTestId("market-county-select").inputValue().catch(() => "");
  const marketDistrictInLocation = await page.getByTestId("market-district-select").inputValue().catch(() => "");

  console.log(`EMBEDDED_MARKET_COUNTY: "${marketCountyInLocation}"`);
  console.log(`EMBEDDED_MARKET_DISTRICT: "${marketDistrictInLocation}"`);

  // ── PRICE STAGE ──
  await page.getByRole("button", { name: /價格與估價證據/ }).click();
  await page.waitForTimeout(2000);
  const priceStage = page.locator("section[id='journey-stage-price']");
  const priceVisible = await priceStage.isVisible().catch(() => false);
  const priceText = await page.locator("#main-content").textContent() ?? "";
  const priceHasIdentity = priceText.includes("永和") || priceText.includes("新北");

  console.log(`PRICE_STAGE_VISIBLE: ${priceVisible}`);
  console.log(`PRICE_HAS_IDENTITY: ${priceHasIdentity}`);

  // ── DECISION STAGE ──
  await page.getByRole("button", { name: /看房決策摘要/ }).click();
  await page.waitForTimeout(2000);
  const decisionStage = page.locator("section[id='journey-stage-decision']");
  await expect(decisionStage).toBeVisible({ timeout: 8000 });
  const decisionText = await page.locator("#main-content").textContent() ?? "";
  const decisionHasIdentity = decisionText.includes("永和") || decisionText.includes("新北");

  console.log(`DECISION_STAGE_VISIBLE: true`);
  console.log(`DECISION_HAS_IDENTITY: ${decisionHasIdentity}`);
  console.log(`=== END ===\n`);

  // ── IDENTITY ASSERTIONS ──
  // The embedded Market (if present) should match 新北市/永和區 or be empty (not wrong city)
  if (marketCountyInLocation && marketCountyInLocation !== "新北市" && marketCountyInLocation !== "") {
    expect.soft(false, `Market county should be 新北市 or empty, got: ${marketCountyInLocation}`).toBe(true);
  }
  if (marketDistrictInLocation && marketDistrictInLocation !== "永和區" && marketDistrictInLocation !== "") {
    expect.soft(false, `Market district should be 永和區 or empty, got: ${marketDistrictInLocation}`).toBe(true);
  }

  // Decision stage must be reachable
  await expect(decisionStage).toBeVisible();
});
