/**
 * Market Insight / Location Insight — East/West Road Identity Guard
 *
 * RELEASE-BLOCKING: 忠孝東路 must NOT resolve to 忠孝西路 for analysis.
 *
 * Tests the REAL UI flow through:
 *   Location Insight → geocoder → acceptance → downstream block
 *   Map Insight → geocoder → acceptance gate → blocked
 */

import { expect, test } from "./fixtures";

// ─── Controlled geocoding responses ─────────────────────────────────────────

function makeLocationInsightResponse(options: {
  query: string;
  resolvedRoad: string;
  resolvedDistrict?: string;
  accepted: boolean;
  matchQuality: string;
  mismatchReasons: string[];
}) {
  const { query, resolvedRoad, resolvedDistrict = "大安區", accepted, matchQuality, mismatchReasons } = options;
  const acceptance = {
    original_query: query,
    normalized_address: `臺北市${resolvedDistrict}${resolvedRoad}`,
    resolved_lat: 25.04,
    resolved_lng: 121.52,
    geocoding_source: "google_geocoding",
    match_quality: matchQuality,
    accepted_for_analysis: accepted,
    requires_confirmation: !accepted,
    mismatch_reasons: mismatchReasons,
    message: accepted ? "定位結果與輸入條件相符。" : "定位結果與輸入的重要地址欄位不一致，已停止後續分析。",
  };

  if (!accepted) {
    // Backend returns unavailable when acceptance fails
    return {
      input: { address: query, city: "臺北市", district: "大安區", road: "", radius_m: 800 },
      resolved_location: null,
      geocoding_acceptance: acceptance,
      radius_m: 800,
      location_score: null,
      category_scores: { transit_score: 0, convenience_score: 0, education_score: 0, green_space_score: 0, medical_score: 0, risk_score: 0 },
      poi_summary: { transit_count: 0, convenience_count: 0, school_count: 0, park_count: 0, medical_count: 0, risk_facility_count: 0 },
      nearest_pois: [],
      strengths: [],
      weaknesses: [],
      buyer_fit: {},
      valuation_context: { supports_price_reasonableness: "unknown", explanation: "" },
      data_quality: { status: "unavailable", missing_sources: [], warnings: ["定位結果與輸入的路街不一致。"] },
      scoring_method: { weights: {}, explanation: "" },
      disclaimer: "定位結果與輸入不一致，後續分析已停止。",
    };
  }

  return {
    input: { address: query, city: "臺北市", district: resolvedDistrict, road: resolvedRoad, radius_m: 800 },
    resolved_location: { address_label: `臺北市${resolvedDistrict}${resolvedRoad}`, latitude: 25.04, longitude: 121.55, geocoding_confidence: "high" },
    geocoding_acceptance: acceptance,
    radius_m: 800,
    location_score: 72,
    category_scores: { transit_score: 80, convenience_score: 75, education_score: 70, green_space_score: 60, medical_score: 65, risk_score: 50 },
    poi_summary: { transit_count: 4, convenience_count: 6, school_count: 2, park_count: 1, medical_count: 3, risk_facility_count: 0 },
    nearest_pois: [{ category: "transit", name: "忠孝復興站", distance_m: 300, source: "fixture" }],
    strengths: ["交通便利"],
    weaknesses: [],
    buyer_fit: { self_use_family: "適合", commuter: "適合", investor: "參考", elderly: "參考" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "區位分析不決定價格合理性。" },
    data_quality: { status: "good", missing_sources: [], warnings: [] },
    scoring_method: { weights: {}, explanation: "Fixture." },
    disclaimer: "僅供參考。",
  };
}

function makeMapSearchResponse(options: {
  query: string;
  resolvedRoad: string;
  resolvedDistrict?: string;
  accepted: boolean;
  matchQuality: string;
  mismatchReasons: string[];
}) {
  const { query, resolvedRoad, resolvedDistrict = "大安區", accepted, matchQuality, mismatchReasons } = options;
  const acceptance = {
    original_query: query,
    normalized_address: `臺北市${resolvedDistrict}${resolvedRoad}`,
    resolved_lat: 25.04,
    resolved_lng: 121.52,
    geocoding_source: "google_geocoding",
    match_quality: matchQuality,
    accepted_for_analysis: accepted,
    requires_confirmation: !accepted,
    mismatch_reasons: mismatchReasons,
    message: accepted ? "定位結果與輸入條件相符。" : "定位結果與輸入的重要地址欄位不一致，已停止後續分析。",
  };

  return {
    query,
    matched: true,
    center: { lat: 25.04, lng: accepted ? 121.55 : 121.52 },
    city: "臺北市",
    district: resolvedDistrict,
    road: resolvedRoad,
    source: "google_geocoding",
    source_chain: ["google_geocoding"],
    formatted_address: `臺北市${resolvedDistrict}${resolvedRoad}`,
    place_id: "test",
    confidence: accepted ? "high" : "low",
    location_note: acceptance.message,
    geocoding_ms: 50,
    disclaimer: "定位參考。",
    ...acceptance,
    geocoding_acceptance: acceptance,
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// CASE 1: query=忠孝東路四段45號 resolved=忠孝西路一段 → REJECT
// ═══════════════════════════════════════════════════════════════════════════

test.describe("East/West road identity: Location Insight", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("CASE 1: 忠孝東路四段 resolved as 忠孝西路一段 shows acceptance gate and blocks analysis", async ({ page }) => {
    test.setTimeout(25000);

    await page.route("**/location/insight", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeLocationInsightResponse({
          query: "臺北市大安區忠孝東路四段45號",
          resolvedRoad: "忠孝西路一段",
          resolvedDistrict: "中正區",
          accepted: false,
          matchQuality: "MISMATCH",
          mismatchReasons: ["street_mismatch", "district_mismatch"],
        })),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Navigate to journey step 2 (Location)
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });
    const locationStepBtn = page.getByLabel(/位置與資料證據/).first();
    await expect(locationStepBtn).toBeVisible({ timeout: 5000 });
    await locationStepBtn.click();
    await expect(page.locator("section[id='journey-stage-location']")).toBeVisible({ timeout: 8000 });

    // Fill address and trigger analysis
    const addressInput = page.locator("#location-insight-calculator input").first();
    await expect(addressInput).toBeVisible({ timeout: 5000 });
    await addressInput.fill("臺北市大安區忠孝東路四段45號");
    await page.locator("#location-insight-calculator button", { hasText: /開始位置分析|Start location/ }).click();

    // HARD ASSERT: geocoding acceptance gate is visible
    const gate = page.getByTestId("geocoding-acceptance-gate");
    await expect(gate).toBeVisible({ timeout: 8000 });

    // HARD ASSERT: the gate shows the mismatch
    await expect(gate).toContainText("忠孝西路一段");
    await expect(gate).toContainText("MISMATCH");

    // HARD ASSERT: street_mismatch reason is shown
    await expect(gate).toContainText(/路街不一致|Street differs/);

    // HARD ASSERT: no location score is shown (analysis was blocked)
    await expect(page.locator("[data-testid='location-result']")).not.toContainText("72");
  });

  test("CASE 3: 忠孝東路四段45號 resolved correctly shows results without gate", async ({ page }) => {
    test.setTimeout(25000);

    await page.route("**/location/insight", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeLocationInsightResponse({
          query: "臺北市大安區忠孝東路四段45號",
          resolvedRoad: "忠孝東路四段",
          resolvedDistrict: "大安區",
          accepted: true,
          matchQuality: "EXACT_OR_ACCEPTABLE",
          mismatchReasons: [],
        })),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Navigate to journey step 2
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });
    await page.getByLabel(/位置與資料證據/).first().click();
    await expect(page.locator("section[id='journey-stage-location']")).toBeVisible({ timeout: 8000 });

    // Fill address and trigger
    const addressInput = page.locator("#location-insight-calculator input").first();
    await expect(addressInput).toBeVisible({ timeout: 5000 });
    await addressInput.fill("臺北市大安區忠孝東路四段45號");
    await page.locator("#location-insight-calculator button", { hasText: /開始位置分析|Start location/ }).click();

    // HARD ASSERT: NO acceptance gate
    await expect(page.getByTestId("geocoding-acceptance-gate")).not.toBeVisible({ timeout: 5000 });

    // HARD ASSERT: location score IS visible
    await expect(page.locator("[data-testid='location-result']")).toContainText("72", { timeout: 8000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// CASE 4: Map Insight — 忠孝東路 must not analyze as 忠孝西路
// ═══════════════════════════════════════════════════════════════════════════

test.describe("East/West road identity: Map Insight", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("CASE 4: Map search resolving 忠孝東路 to 忠孝西路 shows acceptance gate, blocks nearby", async ({ page }) => {
    test.setTimeout(25000);

    let nearbyCallCount = 0;

    await page.route("**/map/search**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeMapSearchResponse({
          query: "臺北市大安區忠孝東路四段",
          resolvedRoad: "忠孝西路一段",
          resolvedDistrict: "中正區",
          accepted: false,
          matchQuality: "MISMATCH",
          mismatchReasons: ["street_mismatch", "district_mismatch"],
        })),
      });
    });

    await page.route("**/map/nearby**", async (route) => {
      nearbyCallCount++;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ categories: [], nearest_places: [], center: { lat: 25.04, lng: 121.52 }, radius_m: 800, source: "mock", livability_score: 0, livability_level: "不足", score_summary: "", category_scores: [], scoring_criteria: [], recommendation_text: "", disclaimer: "" }) });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Navigate to Map Insight
    await page.locator("aside button", { hasText: /Map Insight/ }).click();

    // Fill address in the manual search input and submit
    const searchInput = page.getByRole("textbox", { name: /輸入地址|地標|路段/ }).first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill("臺北市大安區忠孝東路四段");
    await page.getByRole("button", { name: /搜尋位置/ }).click();

    // HARD ASSERT: geocoding acceptance gate is visible
    const gate = page.getByTestId("geocoding-acceptance-gate");
    await expect(gate).toBeVisible({ timeout: 8000 });

    // HARD ASSERT: gate shows the mismatched road
    await expect(gate).toContainText("忠孝西路一段");

    // HARD ASSERT: nearby was NOT called (analysis blocked)
    expect(nearbyCallCount).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// CASE 5: A → B stale location test
// ═══════════════════════════════════════════════════════════════════════════

test.describe("East/West road identity: stale location guard", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("CASE 5: Switching from 忠孝東路 to another address clears old result", async ({ page }) => {
    test.setTimeout(30000);
    let requestCount = 0;

    await page.route("**/location/insight", async (route) => {
      requestCount++;
      const payload = route.request().postDataJSON();
      const address = payload.address || "";
      const isZhongxiao = address.includes("忠孝東路");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeLocationInsightResponse({
          query: address,
          resolvedRoad: isZhongxiao ? "忠孝東路四段" : "信義路五段",
          resolvedDistrict: isZhongxiao ? "大安區" : "信義區",
          accepted: true,
          matchQuality: "EXACT_OR_ACCEPTABLE",
          mismatchReasons: [],
        })),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Navigate to journey location step
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });
    await page.getByLabel(/位置與資料證據/).first().click();
    await expect(page.locator("section[id='journey-stage-location']")).toBeVisible({ timeout: 8000 });

    const addressInput = page.locator("#location-insight-calculator input").first();
    await expect(addressInput).toBeVisible({ timeout: 5000 });

    // First analysis: 忠孝東路
    await addressInput.fill("臺北市大安區忠孝東路四段45號");
    await page.locator("#location-insight-calculator button", { hasText: /開始位置分析|Start location/ }).click();
    await expect(page.locator("[data-testid='location-result']")).toContainText("忠孝東路", { timeout: 8000 });

    // Switch to different address — old result must be cleared
    await addressInput.fill("臺北市信義區信義路五段7號");

    // After changing the address, the old result should be invalidated
    // The LocationInsight component calls invalidateLocationFlow() on address change
    await expect(page.locator("[data-testid='location-result']")).not.toBeVisible({ timeout: 3000 });

    // Run new analysis
    await page.locator("#location-insight-calculator button", { hasText: /開始位置分析|Start location/ }).click();
    await expect(page.locator("[data-testid='location-result']")).toContainText("信義路", { timeout: 8000 });

    // HARD ASSERT: no 忠孝東路 stale text in current result
    await expect(page.locator("[data-testid='location-result']")).not.toContainText("忠孝東路");

    // Return to 忠孝東路
    await addressInput.fill("臺北市大安區忠孝東路四段45號");
    await expect(page.locator("[data-testid='location-result']")).not.toBeVisible({ timeout: 3000 });

    await page.locator("#location-insight-calculator button", { hasText: /開始位置分析|Start location/ }).click();
    await expect(page.locator("[data-testid='location-result']")).toContainText("忠孝東路", { timeout: 8000 });
    await expect(page.locator("[data-testid='location-result']")).not.toContainText("信義路");

    // Verify all 3 requests were made
    expect(requestCount).toBe(3);
  });
});
