/**
 * Journey Identity Propagation — Real PropertyFinder Selection
 *
 * Uses 新北市/永和區 broad search, selects one real property,
 * then verifies identity propagation through Journey stages.
 */
import { test, expect } from "@playwright/test";
import { realProviderUrl } from "./real-provider";

test.use({ viewport: { width: 1440, height: 900 } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

function propertySearchResult(district: string, road: string) {
  const transaction = {
    transaction_period: "2026-05", city: "新北市", district, road,
    building_type: "住宅大樓", area_ping: 35, total_price: 2200,
    unit_price_per_ping: 62.86, building_age_years: 10, floor: 8,
    source_label: "官方 PLVR",
  };
  return {
    search_status: "available", search_reason_code: "official_result_available", is_actionable: true,
    summary: { matched_count: 1, city_count: 1, district_count: 1, road_count: 1, budget_min: null, budget_max: 50000, period_min: "2026-05", period_max: "2026-05", data_source_label: "官方 PLVR 實價登錄", message: "找到符合條件的歷史成交方向。", disclaimer: "test" },
    district_suggestions: [], road_suggestions: [], matched_transactions: [transaction], methodology: "test", disclaimer: "test",
  };
}

test("PropertyFinder A to B race keeps only the latest row identity", async ({ page }) => {
  let requests = 0;
  await page.route("**/valuation/property-search", async (route) => {
    requests += 1;
    const district = String((route.request().postDataJSON().districts ?? [""])[0]);
    if (district === "永和區") {
      await new Promise((resolve) => setTimeout(resolve, 350));
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(propertySearchResult("永和區", "A_OLD_ROAD")) }).catch(() => undefined);
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(propertySearchResult("板橋區", "B_WINNER_ROAD")) });
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByRole("textbox", { name: /縣市/ }).fill("新北市");
  const districtInput = page.getByRole("textbox", { name: /行政區/ });
  await districtInput.fill("永和區");
  await page.getByRole("spinbutton", { name: /預算上限/ }).fill("50000");
  await page.getByRole("button", { name: /搜尋看屋方向/ }).click();
  await districtInput.fill("板橋區");
  await page.getByRole("button", { name: /搜尋看屋方向/ }).click();
  const transactionSummary = page.locator("summary").filter({ hasText: "查看完整成交樣本" });
  await expect(transactionSummary).toHaveCount(1);
  await transactionSummary.click();
  const disclosure = transactionSummary.locator("..");
  await expect(disclosure.getByText("B_WINNER_ROAD", { exact: true })).toBeVisible();
  await expect(disclosure.getByText("A_OLD_ROAD", { exact: true })).toHaveCount(0);
  await page.waitForTimeout(450);
  await expect(disclosure.getByText("B_WINNER_ROAD", { exact: true })).toBeVisible();
  await expect(disclosure.getByText("A_OLD_ROAD", { exact: true })).toHaveCount(0);
  expect(requests).toBe(2);
});

test("Real PropertyFinder selection + Journey propagation", { tag: "@real-provider" }, async ({ page }) => {
  test.setTimeout(120000);

  await page.route("**/valuation/property-search", async (route) => {
    const response = await route.fetch({ url: realProviderUrl("/valuation/property-search") });
    await route.fulfill({ response });
  });

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

  const [searchResponse] = await Promise.all([
    page.waitForResponse((response) => new URL(response.url()).pathname === "/valuation/property-search" && response.request().method() === "POST"),
    page.getByRole("button", { name: /搜尋看屋方向/ }).click(),
  ]);
  const searchResult = await searchResponse.json();
  expect(searchResult.search_status).toBe("available");
  expect(searchResult.matched_transactions.length).toBeGreaterThan(0);

  // Bind the proof to one uniquely identified real transaction row. Aggregate
  // words such as 「筆」 or 「成交」 are not accepted as row-level evidence.
  const identityCounts = new Map<string, number>();
  for (const item of searchResult.matched_transactions) {
    const key = [item.transaction_period, item.city, item.district, item.road, item.area_ping, item.total_price, item.unit_price_per_ping].join("|");
    identityCounts.set(key, (identityCounts.get(key) ?? 0) + 1);
  }
  const selected = searchResult.matched_transactions.find((item: Record<string, string | number>) => {
    const key = [item.transaction_period, item.city, item.district, item.road, item.area_ping, item.total_price, item.unit_price_per_ping].join("|");
    return Boolean(item.road) && identityCounts.get(key) === 1;
  });
  expect(selected, "PropertyFinder must return a uniquely identifiable real row").toBeTruthy();

  const transactionSummary = page.locator("summary").filter({ hasText: "查看完整成交樣本" });
  await expect(transactionSummary).toHaveCount(1);
  await transactionSummary.click();
  const transactionDisclosure = transactionSummary.locator("..");
  const selectedPrice = `${new Intl.NumberFormat("zh-TW").format(selected.total_price)} 萬`;
  const selectedRow = transactionDisclosure.locator("tbody tr")
    .filter({ hasText: selected.transaction_period })
    .filter({ hasText: selected.city })
    .filter({ hasText: selected.district })
    .filter({ hasText: selected.road })
    .filter({ hasText: String(selected.area_ping) })
    .filter({ hasText: selectedPrice });
  await expect(selectedRow).toHaveCount(1);
  const propertyRowText = await selectedRow.innerText();
  const locationActionBtn = selectedRow.getByRole("button", { name: "看附近生活機能" });
  await expect(locationActionBtn).toHaveCount(1);

  console.log(`\n=== SELECTED PROPERTY CONTEXT ===`);
  console.log(`ROW_TEXT: ${propertyRowText.substring(0, 200)}`);

  // ── CLICK PROPERTY ACTION (看附近生活機能) ──
  await locationActionBtn.click();

  // ── VERIFY JOURNEY STATE CHANGED (Location stage should now be visible) ──
  const locationStage = page.locator("section[id='journey-stage-location']");
  await expect(locationStage).toBeVisible({ timeout: 10000 });
  await expect(locationStage.getByTestId("journey-property-context")).toContainText(selected.road);

  // ── LOCATION IDENTITY ──
  const locationText = await page.locator("#main-content").textContent() ?? "";
  const locationHasYonghe = locationText.includes("永和") || locationText.includes("新北");

  console.log(`LOCATION_STAGE_VISIBLE: ${await locationStage.isVisible().catch(() => false)}`);
  console.log(`LOCATION_HAS_CORRECT_IDENTITY: ${locationHasYonghe}`);

  // Check if embedded Market in Location stage shows city/district
  const marketCountyControl = locationStage.getByTestId("market-county-select");
  const marketDistrictControl = locationStage.getByTestId("market-district-select");
  const marketCountyInLocation = await marketCountyControl.count() === 1 ? await marketCountyControl.inputValue() : "";
  const marketDistrictInLocation = await marketDistrictControl.count() === 1 ? await marketDistrictControl.inputValue() : "";

  console.log(`EMBEDDED_MARKET_COUNTY: "${marketCountyInLocation}"`);
  console.log(`EMBEDDED_MARKET_DISTRICT: "${marketDistrictInLocation}"`);

  // ── PRICE STAGE ──
  const journeyNavigation = page.getByRole("navigation", { name: "選擇流程步驟" });
  await expect(journeyNavigation).toHaveCount(1);
  await journeyNavigation.getByRole("button", { name: /價格與估價證據/ }).click();
  const priceStage = page.locator("section[id='journey-stage-price']");
  await expect(priceStage).toBeVisible({ timeout: 10000 });
  await expect(priceStage.getByTestId("journey-property-context")).toContainText(selected.road);
  const priceVisible = true;
  const priceText = await page.locator("#main-content").textContent() ?? "";
  const priceHasIdentity = priceText.includes("永和") || priceText.includes("新北");

  console.log(`PRICE_STAGE_VISIBLE: ${priceVisible}`);
  console.log(`PRICE_HAS_IDENTITY: ${priceHasIdentity}`);

  // ── DECISION STAGE ──
  await journeyNavigation.getByRole("button", { name: /看房決策摘要/ }).click();
  const decisionStage = page.locator("section[id='journey-stage-decision']");
  await expect(decisionStage).toBeVisible({ timeout: 8000 });
  await expect(decisionStage.getByTestId("decision-property-address")).toContainText(selected.road);
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
