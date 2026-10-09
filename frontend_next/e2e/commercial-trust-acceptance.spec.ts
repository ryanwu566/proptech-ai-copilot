import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import type { LocationInsightResult } from "../lib/api";

function manualCase() {
  const saved = e9Case();
  delete saved.data.journeyContext!.propertyContext.askingPriceWan;
  delete saved.data.journeyContext!.activePriceWan;
  delete saved.inputSummary.propertyPrice;
  saved.data.financeEvidence!.assumptions.price_basis = "manual";
  saved.data.financeEvidence!.input_fingerprint = saved.data.financeEvidence!.input_fingerprint.replace("asking|", "manual|");
  saved.data.locationInsight = {
    radius_m: 800, poi_summary: { transit_count: 3, convenience_count: 4, school_count: 2, park_count: 1, medical_count: 3, risk_facility_count: 0 },
    category_scores: { risk_score: 50 }, location_score: 70, nearest_pois: [],
    data_quality: { status: "good", missing_sources: ["risk_facilities"], warnings: [] },
  } as unknown as LocationInsightResult;
  return saved;
}

test("a delayed calculator response from property A cannot reach property B", async ({ page }) => {
  await seed(page);
  let release: () => void = () => {};
  const pending = new Promise<void>(resolve => { release = resolve; });
  let started = false;
  await page.route("**/loan/calculate", async route => {
    started = true;
    await pending;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ property_price_wan: 2480, down_payment_ratio: .2, down_payment_wan: 496, loan_amount_wan: 1984, annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0, monthly_income_wan: null, monthly_payment: 123456, total_payment: 44444160, total_interest: 24604160, sensitivity: [], income_burden_ratio: null }) }).catch(() => {});
  });
  await page.goto("/cases/case-b/finance");
  await page.getByTestId("calculate-loan").click();
  await expect.poll(() => started).toBe(true);
  // A storage update replaces the property anchor while Finance stays mounted.
  await page.evaluate(() => {
    const rows = JSON.parse(localStorage.getItem("proptech.savedCases.v1")!);
    const row = rows[1];
    row.updatedAt = "2026-10-09T01:00:00Z"; delete row.data.financeEvidence;
    row.data.propertyIdentityAnchor.journey_anchor_id = "journey-browser-88888888-2222-4333-8444-555555555555";
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    window.dispatchEvent(new StorageEvent("storage", { key: "proptech.savedCases.v1" }));
  });
  await expect(page.getByTestId("loan-summary")).not.toContainText("55,111");
  const completed = page.waitForResponse("**/loan/calculate");
  release();
  await completed;
  await expect(page.getByTestId("loan-summary")).not.toContainText("123,456");
  const rows = await page.evaluate(() => JSON.parse(localStorage.getItem("proptech.savedCases.v1")!));
  expect(rows.find((r: {id: string}) => r.id === "case-b").data.financeEvidence).toBeUndefined();
});
async function seed(page: Page) {
  await page.addInitScript((rows) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
    sessionStorage.setItem("proptech:holding-cost-result", JSON.stringify({ monthly_total_holding_cost: 999999999 }));
  }, [manualCase(), e9Case("case-b")]);
}
const address = "臺北市信義區市府路1號";
function liveLocation() {
  return {
    input: { address, city: "臺北市", district: "信義區", radius_m: 800 },
    resolved_location: { address_label: address, latitude: 25.0375, longitude: 121.5637, geocoding_confidence: "high" },
    geocoding_acceptance: { original_query: address, normalized_address: address, resolved_lat: 25.0375, resolved_lng: 121.5637, geocoding_source: "google_geocoding", match_quality: "EXACT_OR_ACCEPTABLE", accepted_for_analysis: true, requires_confirmation: false, mismatch_reasons: [], message: "accepted" },
    village_resolution: { status: "resolved", county: "臺北市", town: "信義區", village: "西村里", village_code: "63000020-014", source: "nlsc_village_boundary", candidate_count: 1 },
    demographics: { status: "no_data", reason: "not_requested" }, radius_m: 800,
    poi_summary: { transit_count: 3, convenience_count: 4, school_count: 2, park_count: 1, medical_count: 3, risk_facility_count: null },
    risk_facility_evidence: { status: "unavailable", count: null, source: null, checked_at: null, reason: "risk_facilities_source_unavailable", limitation: "No approved coverage" },
    category_scores: { transit_score: 50, convenience_score: 80, education_score: 50, green_space_score: 25, medical_score: 60, risk_score: null },
    location_score: null, nearest_pois: [], strengths: [], weaknesses: [], buyer_fit: { self_use_family: "資料不足", commuter: "資料不足", investor: "資料不足", elderly: "資料不足" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "資料不足" },
    data_quality: { status: "good", missing_sources: ["risk_facilities"], warnings: [], source: "google_places", checked_at: "2026-10-09T01:00:00Z" }, scoring_method: { weights: {}, explanation: "資料不足" }, disclaimer: "Location reference",
  };
}
for (const width of [1440, 1024, 390]) {
  test(`${width}px address to unavailable valuation to manual 3000 mortgage Save Cases Reopen all projections`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(row => {
      if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row]));
    }, e9Case("case-b"));
    const calls: string[] = [];
    page.on("request", request => {
      if (request.method() === "POST" && /\/(location|valuation|loan|holding-cost|terrain|commute)/.test(new URL(request.url()).pathname)) calls.push(new URL(request.url()).pathname);
    });
    await page.route("**/location/insight", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(liveLocation()) }));
    await page.route("**/valuation/estimate", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Valuation unavailable" }) }));
    await page.route("**/loan/calculate", async route => {
      expect(route.request().postDataJSON().property_price).toBe(3000);
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ property_price_wan: 3000, down_payment_ratio: .2, down_payment_wan: 600, loan_amount_wan: 2400, annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0, monthly_income_wan: null, monthly_payment: 91117, total_payment: 32802120, total_interest: 8802120, sensitivity: [], income_burden_ratio: null, affordability_level: "unknown", disclaimer: "Scenario" }) });
    });
    await page.goto("/");
    await page.locator("#commercial-address").fill(address);
    await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
    await page.getByRole("button", { name: "開始位置分析", exact: true }).click();
    await expect(page.getByTestId("journey-property-identity-card")).toContainText(address);
    const nav = page.getByRole("navigation", { name: "選擇流程步驟" });
    async function goTo(label: RegExp) {
      const disclosure = nav.locator("details");
      if (await disclosure.isVisible() && !await disclosure.evaluate(el => (el as HTMLDetailsElement).open)) await disclosure.locator("summary").click();
      await nav.getByRole("button", { name: label }).click();
    }
    await goTo(/價格與估價證據/);
    const valuation = page.locator("#valuation-calculator");
    for (const label of ["選擇縣市", "選擇鄉鎮市區", "選擇路段"]) await expect(valuation.getByRole("combobox", { name: label })).toHaveCount(1);
    await valuation.getByRole("button", { name: "估算房價", exact: true }).click();
    await expect(page.locator("#journey-stage-price")).toContainText("估價資料暫時無法取得");
    await goTo(/資金與持有成本/);
    await page.getByRole("spinbutton", { name: "房屋總價（萬元）", exact: true }).fill("3000");
    await page.getByRole("button", { name: "計算貸款月付", exact: true }).click();
    await expect(page.getByTestId("affordability-price-context")).toContainText("3,000");
    await expect(page.getByTestId("affordability-price-context")).toContainText(/手動/);
    await goTo(/看房決策摘要/);
    await page.getByRole("button", { name: /^新增案件/ }).click();
    await page.getByRole("button", { name: "儲存案件", exact: true }).click();
    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("proptech.savedCases.v1")!)[0]);
    expect(stored.data.financeEvidence.assumptions.price_source).toBe("MANUAL_SCENARIO");
    expect(stored.data.financeEvidence.assumptions.price_twd).toBe(30000000);
    expect(stored.data.journeyContext.propertyContext.askingPriceWan).toBeUndefined();
    expect(stored.progress).toBeLessThan(100);
    const count = calls.length;
    await page.goto("/cases");
    await page.getByRole("link", { name: `開啟${address}`, exact: true }).click();
    await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("地址與座標已關聯");
    await expect(page.locator("main")).toContainText("手動試算情境");
    await page.goto(`/cases/${stored.id}/finance`);
    await expect(page.getByTestId("loan-summary")).toContainText("91,117");
    await expect(page.getByTestId("saved-finance-assumptions")).toContainText("3,000 萬元");
    await expect(page.getByTestId("calculate-loan")).toHaveCount(0);
    await page.goto(`/cases/${stored.id}/market`);
    await expect(page.locator("main")).toContainText(/無法取得|尚未取得/);
    await page.goto(`/compare?cases=${stored.id},case-b`);
    await expect(page.locator("main")).toContainText("手動試算情境");
    await page.goto(`/cases/${stored.id}/report`);
    const report = page.getByTestId("report-evidence");
    await expect(report).toContainText("91,117");
    await expect(report).toContainText("手動試算情境");
    await expect(report.getByRole("row", { name: /需留意設施/ })).toContainText("未知／未取得");
    await expect(report.getByRole("row", { name: /^開價 / })).not.toContainText("3,000");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(calls.length).toBe(count);
    expect(calls).toEqual(["/location/insight", "/valuation/estimate", "/loan/calculate"]);
  });
}

test("verified zero keeps source and timestamp in saved Location and Report", async ({ page }) => {
  const saved = manualCase();
  saved.data.locationInsight!.data_quality.missing_sources = [];
  saved.data.locationInsight!.risk_facility_evidence = { status: "no_match", count: 0, source: "Verified fixture register", checked_at: "2026-10-09T01:00:00Z", reason: "successful_query", limitation: "Observed radius only" };
  await page.addInitScript(row => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row])), saved);
  await page.goto("/cases/case-a/location");
  await expect(page.getByTestId("risk-facility-source")).toContainText("Verified fixture register");
  await expect(page.getByTestId("risk-facility-source")).toContainText("2026");
  await page.goto("/cases/case-a/overview");
  await page.getByRole("button", { name: "保存目前案件快照" }).click();
  await page.goto("/cases/case-a/report");
  const row = page.getByTestId("report-evidence").getByRole("row", { name: /需留意設施/ });
  await expect(row).toContainText("0 處");
  await expect(row).toContainText("Verified fixture register");
  await expect(row).not.toContainText("未知／未取得");
});
for (const [locale, label, unavailable] of [
  ["zh-TW", "地址與座標已關聯", "尚無可用證據"],
  ["en", "Address and coordinates associated", "No usable evidence"],
  ["ja", "住所と座標を関連付け済み", "利用可能な根拠なし"],
  ["ko", "주소와 좌표 연결됨", "사용 가능한 근거 없음"],
]) {
  test(`${locale} limits workspace and guided identity to address association`, async ({ page }) => {
    await seed(page);
    await page.goto("/cases/case-a/overview");
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(label);
    await page.goto("/");
    await page.getByTestId("locale-switcher").selectOption(locale);
    const card = page.getByTestId("journey-property-identity-card");
    await expect.poll(async () => {
      await page.evaluate(row => {
        window.dispatchEvent(new CustomEvent("proptech:saved-case-loaded", { detail: row }));
        window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" }));
      }, manualCase());
      return card.count();
    }).toBe(1);
    await expect(card).toContainText(locale === "ko" ? "주소와 좌표가 연결됨" : label);
    await expect(card).toContainText(unavailable);
    await expect(card).not.toContainText("manual_confirmed");
    await expect(card).not.toContainText("物件已確認");
  });
}
for (const width of [1440, 1024, 390]) {
  test(`${width}px saved manual scenario stays visible across Overview Finance Compare Report with zero automatic analysis`, async ({ page }) => {
    await seed(page); await page.setViewportSize({ width, height: 900 });
    const analysis: string[] = [];
    await page.route("**/*", async (route) => {
      const request = route.request(); const url = new URL(request.url());
      if (["xhr", "fetch"].includes(request.resourceType()) && /\/(loan|holding-cost|valuation|location|market|terrain|commute|places|routes)(\/|$)/.test(url.pathname) && !url.pathname.startsWith("/cases/")) { analysis.push(url.pathname); return route.abort(); }
      await route.continue();
    });
    await page.goto("/cases");
    await page.goto("/cases/case-a/overview");
    await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("地址與座標已關聯");
    await expect(page.locator("main")).toContainText("手動試算情境");
    await page.goto("/cases/case-a/finance");
    await expect(page.getByTestId("loan-summary")).toContainText("NT$55,111／月");
    await expect(page.getByTestId("saved-finance-assumptions")).toContainText("手動試算情境");
    await expect(page.getByTestId("saved-finance-assumptions")).toContainText("2,480 萬元");
    await expect(page.getByTestId("holding-summary")).toContainText("NT$55,111／月");
    await expect(page.getByTestId("calculate-loan")).toHaveCount(0);
    await expect(page.getByLabel("新試算情境價格（萬元）")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.goto("/cases/case-a/location");
    await expect(page.getByTestId("poi-summary")).toContainText("未知／未取得");
    await page.goto("/cases/case-a/report");
    const report = page.getByTestId("report-evidence");
    await expect(report).toContainText("手動試算情境");
    await expect(report).toContainText("55,111 元／月");
    await expect(report.getByRole("row", { name: /需留意設施/ })).toContainText("未知／未取得");
    await expect(report.getByRole("row", { name: /^開價 / })).not.toContainText("2,480");
    await expect(report).not.toContainText("999,999,999");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.emulateMedia({ media: "print" });
    await expect(report).toContainText("手動試算情境");
    await page.emulateMedia({ media: "screen" });
    await page.goto("/compare?cases=case-a,case-b");
    await expect(page.locator("main")).toContainText("手動試算情境");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(analysis).toEqual([]);
  });
}
