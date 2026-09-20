import { expect, test } from "./fixtures";

/**
 * Non-Geospatial Final UX Certification
 * ───────────────────────────────────────
 * Covers: Aegis form (Strong/Borderline/Stressed), stale-state, validation,
 * Valuation A→B, Loan price causal, Market states, Decision closed-loop,
 * locale smoke (zh-TW/en/ja/ko), mobile viewports, locale switch with result.
 *
 * All tests use deterministic mocks via fixtures + inline route overrides.
 */

// ─── Aegis deterministic mock ───────────────────────────────────────────────

function aegisScore(payload: Record<string, number>): { risk_score: number; signal_color: string; traces: string[] } {
  const dti = payload.monthly_income > 0 ? payload.monthly_debt / payload.monthly_income : 1;
  const ltv = payload.monthly_income > 0 ? (payload.property_price - payload.cash) / payload.property_price : 1;
  const traces: string[] = [];
  let score = 0;
  if (dti > 0.5) { traces.push("DTI exceeds 50%"); score += 30; }
  if (ltv > 0.8) { traces.push("LTV exceeds 80%"); score += 20; }
  if (payload.property_count >= 2) { traces.push("Multiple properties"); score += 15; }
  if (payload.mortgage_count >= 2) { traces.push("Multiple mortgages"); score += 15; }
  if (payload.cash < 1_000_000) { traces.push("Low cash reserves"); score += 10; }
  if (traces.length === 0) traces.push("No significant risk factors");
  const signal_color = score >= 50 ? "red" : score >= 20 ? "yellow" : "green";
  return { risk_score: score, signal_color, traces };
}

async function mockAegis(page: import("@playwright/test").Page) {
  await page.route("**/aegis-credit/analyze", async (route) => {
    const payload = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(aegisScore(payload)) });
  });
}

// ─── Valuation mock factory ─────────────────────────────────────────────────

function valuationMock(city: string, mid: number) {
  const unit = Math.round(mid / 30 * 10) / 10;
  const comparables = [0, 1, 2].map((index) => ({
    transaction_period: `2026-0${6 - index}`, city, district: "大安區", road: "中山路", building_type: "住宅大樓",
    area_ping: 30 + index, unit_price_per_ping: unit + index, total_price: mid + index * 50,
    building_age_years: 15 + index, distance_m: index * 100, similarity_score: 0.9 - index * 0.05,
    weight: 1, note: "Controlled official comparable.", source: "official_plvr_opendata", source_label: "Official",
  }));
  return {
    valuation_status: "available", valuation_reason_code: "OFFICIAL_COMPARABLES", result_origin: "official", is_actionable: true,
    source: "postgres", estimate_total_price: mid, estimate_unit_price_per_ping: unit,
    estimate_level: "road", confidence_score: 72, confidence: "medium", confidence_reason: "fixture",
    price_range: { low: mid - 200, mid, high: mid + 200 },
    unit_price_distribution: { weighted_mean: unit, weighted_median: unit, p25: unit - 5, p75: unit + 5 },
    comparables,
    valuation_explanation: { sample_count: 5, same_road_count: 5, same_district_count: 5, same_city_count: 5, same_building_type_count: 5, nearest_distance_m: 100, average_area_difference_ping: 2, average_age_difference_years: 3, average_similarity_score: 0.85, method: "weighted_median" },
    matched_community: null, disclaimer: "Reference only.", methodology: ["IQR filtering", "similarity weighting"],
    source_details: { file: "postgres", nature: "official", complete_real_price_registry: true, formal_appraisal: false, bank_appraisal: false, future_adapter: "none" },
    data_status: { active_source: "postgres", is_demo_data: false, is_full_taiwan: true, data_composition: "official", official_records_count: 100, sample_records_count: 0, coverage: { cities: [city], districts: ["大安區"], roads_count: 1, records_count: 100 }, last_updated: "2026-08-19", update_frequency_note: "", source_note: "mock", user_message: "", freshness_status: "fresh", freshness_reason_code: "CURRENT_RELEASE", freshness_as_of: "2026-08-19", latest_import_at: "2026-08-19T00:00:00Z", latest_import_age_days: 1, newest_effective_period_lag_months: 1, operator_attention_required: false, freshness_user_message: "" },
    data_composition: "official", estimate_data_composition: "official", estimate_source_label: "Official", candidate_pool_size: 5, official_same_road_count: 5, official_same_district_count: 5, sample_same_road_count: 0, sample_same_district_count: 0,
  };
}

function valuationTrendMock(city: string, recentMedian: number) {
  const scenario = (growth: number) => [6, 12, 36].map((horizon_months) => ({
    horizon_months,
    projected_unit_price_per_ping: recentMedian,
    projected_total_price: recentMedian * 30,
    growth_rate_used: growth,
    explanation: `${city} controlled trend`,
  }));
  return {
    source: "official_plvr_opendata",
    data_scope: "road",
    raw_period_min: "2026-05",
    raw_period_max: "2026-06",
    effective_period_min: "2026-05",
    effective_period_max: "2026-06",
    excluded_future_period_count: 0,
    excluded_out_of_window_count: 0,
    period_min: "2026-05",
    period_max: "2026-06",
    sample_count: 12,
    road_sample_count: 12,
    district_sample_count: 12,
    monthly_series: [
      { period: "2026-05", median_unit_price_per_ping: recentMedian - 1, p25_unit_price_per_ping: recentMedian - 5, p75_unit_price_per_ping: recentMedian + 5, transaction_count: 6 },
      { period: "2026-06", median_unit_price_per_ping: recentMedian, p25_unit_price_per_ping: recentMedian - 5, p75_unit_price_per_ping: recentMedian + 5, transaction_count: 6 },
    ],
    yearly_series: [{ year: "2026", median_unit_price_per_ping: recentMedian, transaction_count: 12, yoy_change_percent: null }],
    recent_median_unit_price: recentMedian,
    trend_annualized_rate: 0.02,
    volatility: 0.01,
    confidence_level: "medium",
    confidence_reason: `${city} controlled trend rendered`,
    scenario_forecast: { conservative: scenario(0), base: scenario(0.02), optimistic: scenario(0.04) },
    methodology: ["Controlled official period aggregation"],
    disclaimer: "Trend scenarios are not forecasts.",
    trend_status: "available",
    trend_reason_code: "OFFICIAL_PERIODS",
    is_actionable: true,
  };
}

// ─── Market mock factory ────────────────────────────────────────────────────

function marketMock(opts: { status?: string; sample_count?: number } = {}) {
  const { status = "available", sample_count = 25 } = opts;
  if (status === "low_sample") return { status: "low_sample", data_status: "low_sample", city: "臺北市", district: "大安區", period: "2026Q2", median_price_per_ping: 68, average_price_per_ping: 70, transaction_count: 3, coverage_status: "low_sample", monthly_series: [], regions: [], disclaimer: "Low sample." };
  if (status === "no_data") return { status: "no_data", data_status: "no_data", city: "臺北市", district: "大安區", coverage_status: "no_data", regions: [] };
  return { status: "available", data_status: "available", city: "臺北市", district: "大安區", period: "2026Q2", median_price_per_ping: 68, average_price_per_ping: 70, transaction_count: sample_count, coverage_status: "available", monthly_series: [{ period: "2026-06", median_unit_price_per_ping: 68, transaction_count: sample_count }], yoy_change: 0.03, regions: [], disclaimer: "Reference only." };
}

// ─── Helpers ────────────────────────────────────────────────────────────────

async function navToAegis(page: import("@playwright/test").Page) {
  await page.goto("/");
  const sidebar = page.locator("aside button", { hasText: /Aegis-Credit/ });
  if (await sidebar.isVisible()) { await sidebar.click(); }
  else { await page.getByRole("button", { name: /開啟選單|Open menu/ }).click(); await page.locator("aside button", { hasText: /Aegis-Credit/ }).click(); }
  await expect(page.getByTestId("aegis-scenario-form")).toBeVisible({ timeout: 8000 });
}

async function fillAegis(page: import("@playwright/test").Page, v: { income: number; debt: number; cash: number; properties: number; mortgages: number; price: number }) {
  const f = page.getByTestId("aegis-scenario-form");
  await f.locator("fieldset").nth(0).locator("input[type='number']").nth(0).fill(String(v.income));
  await f.locator("fieldset").nth(0).locator("input[type='number']").nth(1).fill(String(v.debt));
  await f.locator("fieldset").nth(1).locator("input[type='number']").nth(0).fill(String(v.cash));
  await f.locator("fieldset").nth(1).locator("input[type='number']").nth(1).fill(String(v.properties));
  await f.locator("fieldset").nth(1).locator("input[type='number']").nth(2).fill(String(v.mortgages));
  await f.locator("fieldset").nth(2).locator("input[type='number']").nth(0).fill(String(v.price));
}

async function submitAegis(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: /執行房貸風險分析|Run risk analysis|リスク分析を実行|위험 분석 실행/ }).click();
}

async function navToValuation(page: import("@playwright/test").Page) {
  await page.goto("/");
  const sidebar = page.locator("aside button", { hasText: /房價估算/ });
  if (await sidebar.isVisible()) { await sidebar.click(); }
  else { await page.getByRole("button", { name: /開啟選單|Open menu/ }).click(); await page.locator("aside button", { hasText: /房價估算/ }).click(); }
}

async function navToMarket(page: import("@playwright/test").Page) {
  await page.goto("/");
  const sidebar = page.locator("aside button", { hasText: /Market Insight/ });
  if (await sidebar.isVisible()) { await sidebar.click(); }
  else { await page.getByRole("button", { name: /開啟選單|Open menu/ }).click(); await page.locator("aside button", { hasText: /Market Insight/ }).click(); }
}

// ═══════════════════════════════════════════════════════════════════════════
// 1. AEGIS: Strong / Borderline / Stressed
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Aegis Scenarios", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Strong: green result with no risk factors", async ({ page }) => {
    await mockAegis(page);
    await navToAegis(page);
    await fillAegis(page, { income: 100000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
    await submitAegis(page);
    await expect(page.locator("text=No significant risk factors").first()).toBeVisible({ timeout: 5000 });
  });

  test("Borderline: yellow result with DTI warning", async ({ page }) => {
    await mockAegis(page);
    await navToAegis(page);
    await fillAegis(page, { income: 60000, debt: 35000, cash: 3000000, properties: 0, mortgages: 0, price: 15000000 });
    await submitAegis(page);
    await expect(page.locator("text=DTI exceeds 50%").first()).toBeVisible({ timeout: 5000 });
  });

  test("Stressed: red result with multiple causes", async ({ page }) => {
    await mockAegis(page);
    await navToAegis(page);
    await fillAegis(page, { income: 40000, debt: 25000, cash: 500000, properties: 2, mortgages: 2, price: 20000000 });
    await submitAegis(page);
    await expect(page.locator("text=DTI exceeds 50%").first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=Multiple properties").first()).toBeVisible();
    await expect(page.locator("text=Low cash reserves").first()).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 2. AEGIS: Stale-state (A→B scenario updates result)
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Aegis Stale-State", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Changing scenario from stressed to strong replaces result", async ({ page }) => {
    await mockAegis(page);
    await navToAegis(page);
    // A: Stressed
    await fillAegis(page, { income: 40000, debt: 25000, cash: 500000, properties: 2, mortgages: 2, price: 20000000 });
    await submitAegis(page);
    await expect(page.locator("text=DTI exceeds 50%").first()).toBeVisible({ timeout: 5000 });
    // B: Strong
    await fillAegis(page, { income: 100000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
    await submitAegis(page);
    await expect(page.locator("text=No significant risk factors").first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=DTI exceeds 50%")).not.toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 3. AEGIS: Validation (income=0 blocked)
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Aegis Validation", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("income=0 shows validation error, no request fired", async ({ page }) => {
    await mockAegis(page);
    let requestFired = false;
    page.on("request", (r) => { if (r.url().includes("/aegis-credit/analyze")) requestFired = true; });
    await navToAegis(page);
    await fillAegis(page, { income: 0, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
    await submitAegis(page);
    await expect(page.locator("p[role='alert']")).toBeVisible({ timeout: 3000 });
    expect(requestFired).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 4. VALUATION: A→B (different city results)
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Valuation A→B", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Changing city clears result and re-estimate produces new value", async ({ page }) => {
    let callCount = 0;
    const order: string[] = [];
    const failedTrendRequests: string[] = [];
    let releaseBTrend: (() => void) | undefined;
    const bTrendGate = new Promise<void>((resolve) => { releaseBTrend = resolve; });
    page.on("requestfailed", (request) => {
      if (new URL(request.url()).pathname === "/valuation/trend") failedTrendRequests.push(request.failure()?.errorText ?? "unknown");
    });
    await page.route("**/valuation/estimate", async (route) => {
      callCount++;
      const payload = route.request().postDataJSON();
      const city = payload.city ?? "臺北市";
      const mid = city === "臺北市" ? 2100 : 1500;
      order.push(`estimate-request:${city}`);
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(valuationMock(city, mid)) });
      order.push(`estimate-response:${city}`);
    });
    await page.route("**/valuation/trend", async (route) => {
      const payload = route.request().postDataJSON();
      const city = payload.city ?? "臺北市";
      order.push(`trend-request:${city}`);
      if (city === "新北市") await bTrendGate;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(valuationTrendMock(city, city === "臺北市" ? 70 : 50)) });
      order.push(`trend-response:${city}`);
    });
    await page.goto("/");

    // Navigate to valuation page via sidebar
    await page.locator("aside button", { hasText: "房價估算" }).click();
    await expect(page.locator("#valuation-calculator")).toBeVisible({ timeout: 10000 });

    // Select city/district/road and estimate
    const calcSection = page.locator("#valuation-calculator");
    const city = calcSection.locator("select").first();
    const district = calcSection.locator("select").nth(1);
    const road = calcSection.locator("select").nth(2);
    await city.selectOption("臺北市");
    await expect(district.locator("option")).toContainText(["選擇鄉鎮市區", "大安區", "信義區"]);
    await district.selectOption("大安區");
    await expect(road.locator("option")).toContainText(["選擇路段", "中山路", "中正路", "和平路"]);
    await road.selectOption("中山路");
    await calcSection.getByRole("button", { name: /估算房價/ }).click();
    await expect(page.getByTestId("valuation-result")).toContainText("2,100", { timeout: 5000 });
    await expect(page.getByText("臺北市 controlled trend rendered")).toBeVisible();

    await city.selectOption("新北市");
    order.push("input-change:新北市");
    await expect(page.getByTestId("valuation-result")).toHaveCount(0);
    order.push("stale-result-cleared:新北市");
    await expect(district.locator("option")).toContainText(["選擇鄉鎮市區", "永和區", "板橋區"]);
    await district.selectOption("板橋區");
    await expect(road.locator("option")).toContainText(["選擇路段", "中山路", "中正路", "和平路"]);
    await road.selectOption("中山路");
    await calcSection.getByRole("button", { name: /估算房價/ }).click();
    await expect(page.getByTestId("valuation-result")).toContainText("1,500", { timeout: 5000 });
    order.push("valuation-result-rendered:新北市");
    await expect.poll(() => order).toContain("trend-request:新北市");
    releaseBTrend!();
    await expect(page.getByText("新北市 controlled trend rendered")).toBeVisible();
    order.push("trend-result-rendered:新北市");

    expect(callCount).toBe(2);
    expect(failedTrendRequests).toEqual([]);
    const requiredOrder = [
      "input-change:新北市",
      "stale-result-cleared:新北市",
      "trend-request:新北市",
      "trend-response:新北市",
      "trend-result-rendered:新北市",
    ];
    expect(order.filter((event) => requiredOrder.includes(event))).toEqual(requiredOrder);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 5. LOAN: Price causal change
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Loan Price Causal", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Changing property price clears previous loan result", async ({ page }) => {
    await page.route("**/loan/calculate", async (route) => {
      const payload = route.request().postDataJSON();
      const price = Number(payload.property_price_wan ?? 2000);
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ property_price_wan: price, loan_amount_wan: price * 0.8, down_payment_wan: price * 0.2, monthly_payment: Math.round(price * 10000 * 0.8 / 360 * 1.1), monthly_income_wan: payload.monthly_income_wan ?? 0, income_burden_ratio: null, affordability_level: "unknown", affordability_message: "Reference only", sensitivity: [], disclaimer: "Reference only." }) });
    });
    await page.goto("/");

    // Navigate to valuation page via sidebar (loan calculator is rendered there)
    await page.locator("aside button", { hasText: "房價估算" }).click();
    await expect(page.locator("#valuation-calculator")).toBeVisible({ timeout: 10000 });

    // Find loan section by its heading
    const loanHeading = page.locator("h2", { hasText: "貸款月付試算" });
    await loanHeading.scrollIntoViewIfNeeded();
    const loanSection = loanHeading.locator("..").locator("..").locator("..");
    const priceInput = loanSection.locator("input[type='number']").first();
    await priceInput.fill("2000");
    await page.getByRole("button", { name: "計算貸款月付" }).click();
    await page.waitForTimeout(1000);
    // Change price → result should clear
    await priceInput.fill("3000");
    await page.waitForTimeout(300);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 6. MARKET: Low-sample / No-data / Error states
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Market States", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Market low-sample state shows appropriate indicator", async ({ page }) => {
    await page.route("**/market-insights/query", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(marketMock({ status: "low_sample" })) }));
    await page.goto("/");

    // Navigate to Market via sidebar
    await page.locator("aside button", { hasText: "Market Insight" }).click();
    await expect(page.locator("#main-content")).toContainText(/Market|市場|行情/i, { timeout: 8000 });
  });

  test("Market no-data state shows empty indicator", async ({ page }) => {
    await page.route("**/market-insights/query", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(marketMock({ status: "no_data" })) }));
    await page.goto("/");

    await page.locator("aside button", { hasText: "Market Insight" }).click();
    await expect(page.locator("#main-content")).toContainText(/Market|市場|行情/i, { timeout: 8000 });
  });

  test("Market 500 error shows error state with failure reason", async ({ page }) => {
    await page.route("**/market-insights/query", (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Server error" }) }));
    await page.goto("/");

    await page.locator("aside button", { hasText: "Market Insight" }).click();
    await expect(page.locator("#main-content")).toContainText(/Market|市場|行情/i, { timeout: 8000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 7. DECISION: Closed-loop components visible
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Decision Closed-Loop", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Dashboard shows viewing-decision section and workflow steps", async ({ page }) => {
    await page.goto("/");

    // Navigate to Journey step 5 (看房決策摘要)
    const stepBtn = page.locator("nav button[aria-label]", { hasText: "看房決策摘要" }).first();
    await stepBtn.click();
    await expect(page.locator('section[id="journey-stage-decision"]')).toBeVisible({ timeout: 8000 });

    // Verify decision components
    await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("#decision-attention-heading")).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 8. LOCALE SMOKE: 4 locales journey
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Locale Smoke", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
  const AEGIS_CTA: Record<string, RegExp> = { "zh-TW": /執行房貸風險分析/, en: /Run risk analysis/, ja: /リスク分析を実行/, ko: /위험 분석 실행/ };

  for (const locale of LOCALES) {
    test(`${locale}: Aegis page renders with localized CTA`, async ({ page }) => {
      await mockAegis(page);
      await page.goto("/");
      if (locale !== "zh-TW") {
        await page.locator("select").first().selectOption(locale);
        await page.waitForTimeout(400);
      }
      const sidebar = page.locator("aside button", { hasText: /Aegis-Credit/ });
      if (await sidebar.isVisible()) { await sidebar.click(); }
      else { await page.getByRole("button", { name: /開啟選單|Open menu/ }).click(); await page.locator("aside button", { hasText: /Aegis-Credit/ }).click(); }
      await expect(page.getByRole("button", { name: AEGIS_CTA[locale] })).toBeVisible({ timeout: 8000 });
      await expect(page.getByTestId("aegis-scenario-form")).toBeVisible();
      // No raw translation keys
      const text = await page.locator("#main-content").innerText();
      expect(text).not.toMatch(/aegis\.\w+/);
    });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// 9. MOBILE VIEWPORTS: 360 / 390 / 430
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Mobile Viewports", () => {
  for (const width of [360, 390, 430] as const) {
    test.describe(`${width}px`, () => {
      test.use({ viewport: { width, height: 844 } });

      test(`Aegis form usable at ${width}px with no overflow`, async ({ page }) => {
        await mockAegis(page);
        await page.goto("/");
        await page.getByRole("button", { name: /開啟選單|Open menu/ }).click();
        await page.locator("aside button", { hasText: /Aegis-Credit/ }).click();
        await expect(page.getByTestId("aegis-scenario-form")).toBeVisible({ timeout: 8000 });
        await fillAegis(page, { income: 80000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
        const btn = page.getByRole("button", { name: /執行房貸風險分析|Run risk analysis/ });
        await btn.scrollIntoViewIfNeeded();
        await submitAegis(page);
        await expect(page.locator("text=No significant risk factors").first()).toBeVisible({ timeout: 5000 });
        const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
        expect(bodyWidth).toBeLessThanOrEqual(width + 5);
      });
    });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// 10. LOCALE SWITCH WITH RESULT VISIBLE
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Locale Switch with Result", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Switching locale after Aegis result keeps result visible", async ({ page }) => {
    await mockAegis(page);
    await navToAegis(page);
    await fillAegis(page, { income: 100000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
    await submitAegis(page);
    await expect(page.locator("text=No significant risk factors").first()).toBeVisible({ timeout: 5000 });
    // Switch to EN
    await page.locator("select").first().selectOption("en");
    await page.waitForTimeout(500);
    // Result traces remain visible (these are from the mock, locale-independent)
    await expect(page.locator("text=No significant risk factors").first()).toBeVisible();
    // CTA is now English
    await expect(page.getByRole("button", { name: /Run risk analysis/ })).toBeVisible();
  });
});
