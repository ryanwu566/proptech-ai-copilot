/**
 * Trust Closure Regression — Hard Browser Proof
 *
 * RULES:
 * - Zero conditional passes (no if-isVisible)
 * - Zero window test helpers
 * - Zero test.skip
 * - Every expect is a hard fail if the condition is not met
 *
 * Tests:
 * 1. Property → Valuation identity (real UI, no wrong road)
 * 2. A → B → A real UI property cycle
 * 3. Valuation partial messaging (visible UI contract)
 * 4. Aegis trust label (scenario risk indicator)
 * 5. Parcel point reference (real terrain UI)
 * 6. Locale zh → ja → zh accessibility round-trip
 * 7. Async property race (late response must not overwrite)
 */

import { expect, test } from "./fixtures";

// ─── Shared valuation response factory ──────────────────────────────────────

function makeValuationResponse(road: string, district = "大安區") {
  return {
    valuation_status: "available",
    result_origin: "official",
    is_actionable: true,
    source: "postgres",
    data_status: { active_source: "postgres", is_demo_data: false, is_full_taiwan: true, data_composition: "official", official_records_count: 50, sample_records_count: 0, coverage: { cities: ["臺北市"], districts: [district], roads_count: 1, records_count: 50 }, last_updated: "2026-08-01", update_frequency_note: "", source_note: "", user_message: "", freshness_status: "fresh", freshness_reason_code: "CURRENT", freshness_as_of: "2026-08-01", latest_import_at: "2026-08-01T00:00:00Z", latest_import_age_days: 1, newest_effective_period_lag_months: 1, operator_attention_required: false, freshness_user_message: "" },
    data_composition: "official",
    estimate_data_composition: "official",
    estimate_source_label: "Official PLVR",
    candidate_pool_size: 10,
    official_same_road_count: 10,
    official_same_district_count: 10,
    sample_same_road_count: 0,
    sample_same_district_count: 0,
    estimate_level: "road",
    matched_community: null,
    confidence_reason: "Controlled fixture.",
    source_details: { file: "fixture", nature: "official", complete_real_price_registry: true, formal_appraisal: false, bank_appraisal: false, future_adapter: "none" },
    estimate_total_price: 2500,
    estimate_unit_price_per_ping: 83,
    price_range: { low: 2350, mid: 2500, high: 2650 },
    unit_price_distribution: { weighted_mean: 83, weighted_median: 83, p25: 78, p75: 88 },
    confidence: "high",
    confidence_score: 85,
    comparables: [
      { transaction_period: "2026-06", city: "臺北市", district, road, building_type: "住宅大樓", area_ping: 30, unit_price_per_ping: 83, total_price: 2500, building_age_years: 15, distance_m: 0, similarity_score: 0.9, weight: 1, note: "Official", source: "official_plvr_opendata", source_label: "Official" },
      { transaction_period: "2026-05", city: "臺北市", district, road, building_type: "住宅大樓", area_ping: 31, unit_price_per_ping: 82, total_price: 2540, building_age_years: 16, distance_m: 50, similarity_score: 0.88, weight: 1, note: "Official", source: "official_plvr_opendata", source_label: "Official" },
      { transaction_period: "2026-04", city: "臺北市", district, road, building_type: "住宅大樓", area_ping: 29, unit_price_per_ping: 84, total_price: 2436, building_age_years: 14, distance_m: 100, similarity_score: 0.85, weight: 1, note: "Official", source: "official_plvr_opendata", source_label: "Official" },
    ],
    valuation_explanation: { sample_count: 3, same_road_count: 3, same_district_count: 3, same_city_count: 3, same_building_type_count: 3, nearest_distance_m: 0, average_area_difference_ping: 1, average_age_difference_years: 1, average_similarity_score: 0.88, method: "Official" },
    methodology: ["Official"],
    disclaimer: "Reference only.",
  };
}

/** Wait for cities to load into a select by checking option count > 1 */
async function waitForCityOptions(page: import("@playwright/test").Page, calcSection: import("@playwright/test").Locator) {
  const citySelect = calcSection.locator("select").nth(0);
  await expect(citySelect.locator("option")).not.toHaveCount(0, { timeout: 5000 });
  // Ensure at least one city option contains 北 (台北/臺北)
  await expect.poll(async () => {
    const opts = await citySelect.locator("option").allTextContents();
    return opts.some((o) => o.includes("北"));
  }, { timeout: 5000 }).toBeTruthy();
}

// ═══════════════════════════════════════════════════════════════════════════
// TEST 1 — REAL PROPERTY → VALUATION IDENTITY
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TEST 1: Property → Valuation identity", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Valuation page uses selected road, not hardcoded default", async ({ page }) => {
    test.setTimeout(45000);
    const capturedRequests: Array<{ city: string; district: string; road: string }> = [];

    // Route client-errors to avoid fixture assertion
    await page.route("**/client-errors", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));

    await page.route("**/valuation/estimate", async (route) => {
      const payload = route.request().postDataJSON();
      capturedRequests.push({ city: payload.city, district: payload.district, road: payload.road });
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(makeValuationResponse(payload.road, payload.district)) });
    });

    await page.route("**/roads/roads?*", async (route) => {
      const url = new URL(route.request().url());
      const district = url.searchParams.get("district") ?? "";
      const roads = district === "大安區" ? ["忠孝東路四段", "和平東路二段", "復興南路一段"] : district === "信義區" ? ["信義路五段", "松仁路"] : ["中山路", "中正路"];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: url.searchParams.get("city") ?? "", district, roads, message: "OK" }) });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Navigate to standalone valuation via sidebar
    await page.locator("aside button", { hasText: "房價估算" }).click();
    await expect(page.locator("#valuation-calculator")).toBeVisible({ timeout: 10000 });

    const calcSection = page.locator("#valuation-calculator");
    await waitForCityOptions(page, calcSection);

    // Select city — use 臺北市 which is what the fixture route returns
    await calcSection.locator("select").nth(0).selectOption("臺北市");
    await page.waitForTimeout(400);
    await calcSection.locator("select").nth(1).selectOption("大安區");
    await page.waitForTimeout(400);
    await calcSection.locator("select").nth(2).selectOption("忠孝東路四段");

    // Hard assert: road is 忠孝東路四段
    await expect(calcSection.locator("select").nth(2)).toHaveValue("忠孝東路四段");

    // Click estimate
    await calcSection.getByRole("button", { name: /估算房價/ }).click();

    // Wait for the request to be captured (the valuation route handler will fire)
    await expect.poll(() => capturedRequests.length, { timeout: 8000 }).toBeGreaterThan(0);

    // Hard assert on request payload
    const lastReq = capturedRequests[capturedRequests.length - 1];
    expect(lastReq.road).toBe("忠孝東路四段");
    expect(lastReq.district).toBe("大安區");
    expect(lastReq.road).not.toBe("和平東路二段");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TEST 2 — REAL A → B → A
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TEST 2: A → B → A property cycle", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Switching district clears result and final request matches return trip", async ({ page }) => {
    test.setTimeout(60000);
    const capturedRequests: Array<{ city: string; district: string; road: string }> = [];

    // Route client-errors
    await page.route("**/client-errors", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));

    // Unroute the fixture's broad valuation catch-all to prevent trend crash
    await page.unroute("**/valuation/**");

    await page.route("**/valuation/estimate", async (route) => {
      const payload = route.request().postDataJSON();
      capturedRequests.push({ city: payload.city, district: payload.district, road: payload.road });
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(makeValuationResponse(payload.road, payload.district)) });
    });

    await page.route("**/valuation/trend", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ trend_status: "no_data", is_actionable: false }) });
    });

    await page.route("**/valuation/data-status", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ active_source: "unknown", is_demo_data: false, is_full_taiwan: false, data_composition: "official", official_records_count: 0, sample_records_count: 0, coverage: { cities: [], districts: [], roads_count: 0, records_count: 0 }, last_updated: null, update_frequency_note: "", source_note: "", user_message: "", freshness_status: "unavailable", freshness_reason_code: "UNAVAILABLE", freshness_as_of: null, latest_import_at: null, latest_import_age_days: null, newest_effective_period_lag_months: null, operator_attention_required: false, freshness_user_message: "" }) });
    });

    await page.route("**/roads/roads?*", async (route) => {
      const url = new URL(route.request().url());
      const district = url.searchParams.get("district") ?? "";
      const roads = district === "大安區" ? ["忠孝東路四段", "和平東路二段"] : district === "信義區" ? ["信義路五段", "松仁路"] : ["中山路"];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: url.searchParams.get("city") ?? "", district, roads, message: "OK" }) });
    });

    await page.route("**/roads/districts?*", async (route) => {
      const city = new URL(route.request().url()).searchParams.get("city") ?? "";
      const districts = city.includes("北") ? ["大安區", "信義區", "中正區"] : ["板橋區"];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city, districts, message: "OK" }) });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.locator("aside button", { hasText: "房價估算" }).click();
    await expect(page.locator("#valuation-calculator")).toBeVisible({ timeout: 10000 });

    const calcSection = page.locator("#valuation-calculator");
    await waitForCityOptions(page, calcSection);

    // === A: 大安區/忠孝東路四段 ===
    await calcSection.locator("select").nth(0).selectOption("臺北市");
    await page.waitForTimeout(400);
    await calcSection.locator("select").nth(1).selectOption("大安區");
    await page.waitForTimeout(400);
    await calcSection.locator("select").nth(2).selectOption("忠孝東路四段");
    await calcSection.getByRole("button", { name: /估算房價/ }).click();
    await expect.poll(() => capturedRequests.length, { timeout: 8000 }).toBeGreaterThan(0);

    const reqA = capturedRequests[capturedRequests.length - 1];
    expect(reqA.road).toBe("忠孝東路四段");

    // === B: Switch to 信義區/信義路五段 ===
    await calcSection.locator("select").nth(1).selectOption("信義區");
    await page.waitForTimeout(500);

    await calcSection.locator("select").nth(2).selectOption("信義路五段");
    await calcSection.getByRole("button", { name: /估算房價/ }).click();
    await expect.poll(() => capturedRequests.length, { timeout: 8000 }).toBeGreaterThan(1);

    const reqB = capturedRequests[capturedRequests.length - 1];
    expect(reqB.road).toBe("信義路五段");
    expect(reqB.district).toBe("信義區");

    // === Back to A ===
    await calcSection.locator("select").nth(1).selectOption("大安區");
    await page.waitForTimeout(500);

    await calcSection.locator("select").nth(2).selectOption("忠孝東路四段");
    await calcSection.getByRole("button", { name: /估算房價/ }).click();
    await expect.poll(() => capturedRequests.length, { timeout: 8000 }).toBeGreaterThan(2);

    const reqAReturn = capturedRequests[capturedRequests.length - 1];
    expect(reqAReturn.road).toBe("忠孝東路四段");
    expect(reqAReturn.district).toBe("大安區");

    // Final assertions
    expect(reqA.road).not.toBe(reqB.road);
    expect(reqAReturn.road).toBe(reqA.road);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TEST 3 — VALUATION PARTIAL UI
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TEST 3: Valuation partial visible UI", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Comparables with unavailable status show partial message not full unavailable", async ({ page }) => {
    test.setTimeout(30000);

    // Route client-errors to avoid unhandled request assertion failure
    await page.route("**/client-errors", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));

    // Unroute the fixture's broad valuation catch-all to prevent trend crash
    await page.unroute("**/valuation/**");

    await page.route("**/valuation/trend", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ trend_status: "no_data", is_actionable: false }) });
    });

    await page.route("**/valuation/data-status", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ active_source: "unknown", is_demo_data: false, is_full_taiwan: false, data_composition: "official", official_records_count: 0, sample_records_count: 0, coverage: { cities: [], districts: [], roads_count: 0, records_count: 0 }, last_updated: null, update_frequency_note: "", source_note: "", user_message: "", freshness_status: "unavailable", freshness_reason_code: "UNAVAILABLE", freshness_as_of: null, latest_import_at: null, latest_import_age_days: null, newest_effective_period_lag_months: null, operator_attention_required: false, freshness_user_message: "" }) });
    });

    // Override BOTH the catch-all valuation route AND the specific estimate route
    // Routes registered later take priority in Playwright
    await page.route("**/valuation/estimate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          valuation_status: "unavailable",
          result_origin: "none",
          is_actionable: false,
          source: "postgres",
          data_status: { active_source: "postgres", is_demo_data: false, is_full_taiwan: true, data_composition: "official", official_records_count: 50, sample_records_count: 0, coverage: { cities: ["臺北市"], districts: ["大安區"], roads_count: 1, records_count: 50 }, last_updated: "2026-08-01", update_frequency_note: "", source_note: "", user_message: "", freshness_status: "fresh", freshness_reason_code: "CURRENT", freshness_as_of: null, latest_import_at: null, latest_import_age_days: null, newest_effective_period_lag_months: null, operator_attention_required: false, freshness_user_message: "" },
          data_composition: "official",
          estimate_data_composition: "official",
          estimate_source_label: "Official",
          candidate_pool_size: 5,
          official_same_road_count: 5,
          official_same_district_count: 5,
          sample_same_road_count: 0,
          sample_same_district_count: 0,
          estimate_level: "road",
          matched_community: null,
          confidence_reason: "Quality insufficient.",
          source_details: { file: "fixture", nature: "official", complete_real_price_registry: true, formal_appraisal: false, bank_appraisal: false, future_adapter: "none" },
          estimate_total_price: 2000,
          estimate_unit_price_per_ping: 67,
          price_range: { low: 1800, mid: 2000, high: 2200 },
          unit_price_distribution: { weighted_mean: 67, weighted_median: 67, p25: 60, p75: 73 },
          confidence: "low",
          confidence_score: 30,
          comparables: [
            { transaction_period: "2026-06", city: "臺北市", district: "大安區", road: "和平東路二段", building_type: "住宅大樓", area_ping: 30, unit_price_per_ping: 67, total_price: 2000, building_age_years: 15, distance_m: 0, similarity_score: 0.7, weight: 1, note: "Official", source: "official_plvr_opendata", source_label: "Official" },
            { transaction_period: "2026-05", city: "臺北市", district: "大安區", road: "和平東路二段", building_type: "住宅大樓", area_ping: 28, unit_price_per_ping: 65, total_price: 1820, building_age_years: 20, distance_m: 200, similarity_score: 0.6, weight: 1, note: "Official", source: "official_plvr_opendata", source_label: "Official" },
          ],
          valuation_explanation: { sample_count: 2, same_road_count: 2, same_district_count: 2, same_city_count: 2, same_building_type_count: 2, nearest_distance_m: 0, average_area_difference_ping: 2, average_age_difference_years: 3, average_similarity_score: 0.65, method: "Official" },
          methodology: ["Official"],
          disclaimer: "Reference only.",
        }),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Navigate to journey price step where the trust status strip shows the partial text
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });
    const priceStepBtn = page.getByLabel(/價格與估價證據/).first();
    await expect(priceStepBtn).toBeVisible({ timeout: 5000 });
    await priceStepBtn.click();
    await expect(page.locator("section[id='journey-stage-price']")).toBeVisible({ timeout: 8000 });

    // Wait for the embedded valuation calc
    const calcSection = page.locator("#valuation-calculator");
    await expect(calcSection).toBeVisible({ timeout: 8000 });

    // Trigger estimation
    await calcSection.getByRole("button", { name: /估算房價/ }).click();

    // Wait for the partial trust status text to appear in the journey strip
    // The text is "可比成交可查閱，估價信心不足" from buildPriceTrustStatusItems
    await expect(page.locator("text=可比成交可查閱")).toBeVisible({ timeout: 8000 });

    // Hard assert: the contradictory "unavailable" full-block message is NOT shown
    await expect(page.locator("text=資料暫時無法取得")).not.toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TEST 4 — AEGIS TRUST UI
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TEST 4: Aegis trust label", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Aegis shows scenario risk indicator label, not risk score", async ({ page }) => {
    test.setTimeout(30000);

    await page.route("**/aegis-credit/analyze", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ risk_score: 35, signal_color: "yellow", traces: ["負債比偏高", "名下已有房貸"] }),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.locator("aside button", { hasText: /Aegis-Credit/ }).click();
    await expect(page.getByRole("heading", { name: "房貸風險展示" })).toBeVisible({ timeout: 10000 });

    // Hard assert: form is visible
    await expect(page.getByTestId("aegis-scenario-form")).toBeVisible({ timeout: 5000 });

    // Hard assert: heuristic disclaimer visible (use .first() to avoid strict mode)
    await expect(page.locator("text=heuristic").first()).toBeVisible();

    // Submit
    await page.getByRole("button", { name: /執行房貸風險分析/ }).click();

    // Wait for result label
    await expect(page.locator("text=情境風險指標")).toBeVisible({ timeout: 10000 });

    // Hard assert: OLD labels NOT present
    await expect(page.locator("text=風險分數")).not.toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TEST 5 — PARCEL POINT REFERENCE
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TEST 5: Parcel point reference", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Terrain shows POINT_REFERENCE_ONLY without parcel geometry", async ({ page }) => {
    test.setTimeout(30000);

    await page.route("**/terrain-risk/analyze", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          input: { address: "臺北市大安區忠孝東路四段45號" },
          resolved_location: { address_label: "臺北市大安區忠孝東路四段45號", latitude: 25.04, longitude: 121.55, geocoding_confidence: "high", geocoding_source: "mock" },
          overall: { level: "low", label: "Reference", summary: "Available.", confidence: "medium" },
          terrain: { status: "available", slope_value: 2, slope_class: "gentle", elevation_m: 15, explanation: "Fixture." },
          hazards: {
            landslide: { key: "landslide", label: "大規模崩塌潛勢", status: "available", level: "low", matched: false, distance_m: 1000, value: null, explanation: "No match." },
            debris_flow: { key: "debris_flow", label: "土石流", status: "available", level: "low", matched: false, distance_m: 800, value: null, explanation: "No match." },
            flood: { key: "flood", label: "淹水潛勢", status: "available", level: "low", matched: false, distance_m: 900, value: null, explanation: "No match." },
            geological_sensitivity: { key: "geological_sensitivity", label: "地質敏感區", status: "available", level: "low", matched: false, distance_m: 1500, value: null, explanation: "No match." },
            liquefaction: { key: "liquefaction", label: "土壤液化", status: "available", level: "low", matched: false, distance_m: 500, value: null, explanation: "No match." },
            active_fault: { key: "active_fault", label: "活動斷層", status: "available", level: "low", matched: false, distance_m: 2000, value: null, explanation: "No match." },
          },
          risk_factors: [],
          missing_sources: [],
          recommended_checks: ["Confirm official layers."],
          map_layers: [],
          data_quality: { status: "good", warnings: [], checked_at: "2026-08-20T00:00:00Z" },
          cadastral: {
            provider: "mock",
            provider_name: "Mock cadastral",
            center: { lat: 25.04, lng: 121.55 },
            tile_url_template: "",
            checked_at: "2026-08-20T00:00:00Z",
          },
          disclaimer: "Reference only.",
        }),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.locator("aside").getByRole("button", { name: "Terrain Risk", exact: true }).click();

    // Fill address and trigger analysis
    const addressInput = page.getByRole("textbox", { name: "物件地址" });
    await expect(addressInput).toBeVisible({ timeout: 10000 });
    await addressInput.fill("臺北市大安區忠孝東路四段45號");
    await page.getByRole("button", { name: "開始地勢／災害檢查" }).click();

    // Wait for cadastral evidence section
    const cadastral = page.getByTestId("terrain-cadastral-evidence");
    await expect(cadastral).toBeVisible({ timeout: 20000 });

    // Hard assert: parcel status
    await expect(cadastral).toHaveAttribute("data-parcel-status", "point_reference_only");

    // Hard assert: POINT_REFERENCE_ONLY text visible
    const limitation = page.getByTestId("cadastral-point-reference-limitation");
    await expect(limitation).toBeVisible();
    await expect(limitation).toContainText("POINT_REFERENCE_ONLY");

    // Hard assert: LANDSECT semantics
    const landsect = page.getByTestId("landsect-semantics");
    await expect(landsect).toBeVisible();
    await expect(landsect).toContainText("LANDSECT");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TEST 6 — LOCALE ACCESSIBILITY ROUNDTRIP
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TEST 6: Locale zh → ja → zh accessibility", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("No Japanese kana in aria-labels after returning to zh-TW", async ({ page }) => {
    test.setTimeout(20000);
    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Use first select (locale switcher per i18n-smoke pattern)
    const localeSwitcher = page.locator("select").first();
    await expect(localeSwitcher).toBeVisible({ timeout: 5000 });

    // zh-TW → ja
    await localeSwitcher.selectOption("ja");
    await expect.poll(() => page.locator("html").getAttribute("lang"), { timeout: 5000 }).toBe("ja");

    // ja → zh-TW
    await localeSwitcher.selectOption("zh-TW");
    await expect.poll(() => page.locator("html").getAttribute("lang"), { timeout: 5000 }).toBe("zh-TW");

    // Hard assert: no Japanese kana in aria-labels
    const ariaLabels = await page.evaluate(() => {
      const elements = document.querySelectorAll("[aria-label]");
      return Array.from(elements).map((el) => el.getAttribute("aria-label") ?? "");
    });

    const japaneseKana = /[ぁ-ゖァ-ヶ]/;
    const staleJapanese = ariaLabels.filter((label) => japaneseKana.test(label));
    expect(staleJapanese, `Stale Japanese aria-labels: ${JSON.stringify(staleJapanese)}`).toEqual([]);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TEST 7 — ASYNC PROPERTY RACE
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TEST 7: Async context race", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Late road response for district A does not overwrite district B", async ({ page }) => {
    test.setTimeout(45000);

    let resolveDelayedA: (() => void) | undefined;
    const delayedAGate = new Promise<void>((resolve) => { resolveDelayedA = resolve; });

    await page.route("**/roads/roads?*", async (route) => {
      const url = new URL(route.request().url());
      const district = url.searchParams.get("district") ?? "";

      if (district === "大安區") {
        // DELAY response for A
        await delayedAGate;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: "臺北市", district: "大安區", roads: ["忠孝東路四段", "和平東路二段"], message: "OK" }) });
      } else if (district === "信義區") {
        // B responds immediately
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: "臺北市", district: "信義區", roads: ["信義路五段", "松仁路"], message: "OK" }) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: "臺北市", district, roads: ["中山路"], message: "OK" }) });
      }
    });

    await page.route("**/roads/districts?*", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: "臺北市", districts: ["大安區", "信義區"], message: "OK" }) });
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.locator("aside button", { hasText: "房價估算" }).click();
    await expect(page.locator("#valuation-calculator")).toBeVisible({ timeout: 10000 });

    const calcSection = page.locator("#valuation-calculator");
    await waitForCityOptions(page, calcSection);

    // Select city first
    await calcSection.locator("select").nth(0).selectOption("臺北市");
    await page.waitForTimeout(400);

    // Select 大安區 — this triggers the DELAYED road request
    await calcSection.locator("select").nth(1).selectOption("大安區");
    await page.waitForTimeout(200);

    // Immediately switch to 信義區 (B responds instantly)
    await calcSection.locator("select").nth(1).selectOption("信義區");
    await page.waitForTimeout(500);

    // B roads should be visible now
    const roadOptionsB = await calcSection.locator("select").nth(2).locator("option").allTextContents();
    expect(roadOptionsB).toContain("信義路五段");

    // Now release the delayed A response
    resolveDelayedA!();
    await page.waitForTimeout(800);

    // Hard assert: district selector still shows 信義區
    await expect(calcSection.locator("select").nth(1)).toHaveValue("信義區");

    // Hard assert: road options are still B's roads, not A's
    const finalRoads = await calcSection.locator("select").nth(2).locator("option").allTextContents();
    expect(finalRoads).toContain("信義路五段");
    expect(finalRoads).not.toContain("忠孝東路四段");
    expect(finalRoads).not.toContain("和平東路二段");
  });
});
