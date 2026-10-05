import { expect, test, type Page } from "@playwright/test";

const NOW = "2026-09-27T08:00:00.000Z";

function savedCase() {
  return {
    id: "market-price-case",
    title: "市府路案件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "report",
    progress: 80,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號", propertyPrice: 2480, areaPing: 30 },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      journeyContext: {
        version: 1,
        propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 2480 },
        priceBasis: "asking",
        activePriceWan: 2480,
      },
      marketInsight: {
        city: "臺北市",
        county: "臺北市",
        district: "信義區",
        period: "2025-01–2026-07",
        average_unit_price: 53.1,
        avg_price_per_ping: 53.1,
        transaction_count: 18,
        transaction_volume: 18,
        record_count: 18,
        summary: "近期成交單價集中於每坪 50 至 55 萬元。",
        source_name: "內政部不動產實價登錄",
        source_updated_at: "2026-08-31",
        coverage_status: "covered",
        data_status: "available",
        caveat: "樣本僅供初步比較。",
        disclaimer: "成交資料不等同正式估價。",
        history: [
          { period: "2026-07", average_unit_price: 53.1, transaction_count: 8 },
          { period: "2026-06", average_unit_price: 51.8, transaction_count: 10 },
        ],
        sample_status: "sufficient",
        freshness_status: "fresh",
        period_min: "2025-01",
        period_max: "2026-07",
        newest_effective_period: "2026-07",
        median_unit_price_per_ping: 52.4,
        p25_unit_price_per_ping: 49.8,
        p75_unit_price_per_ping: 55.6,
        median_total_price: 1850,
        effective_scope_label: "臺北市信義區",
        effective_analysis_level: "DISTRICT",
        effective_sample_count: 18,
        fallback_applied: true,
      },
    },
  };
}

function identityAnchor(address = "臺北市信義區市府路1號", road = "市府路1號") {
  return {
    version: 1,
    scope: "journey_browser_anchor",
    journey_anchor_id: `journey-browser-${road === "市府路1號" ? "11111111-2222-4333-8444-555555555555" : "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"}`,
    address_input: address,
    normalized_address: address,
    coordinates: road === "市府路1號"
      ? { latitude: 25.0375, longitude: 121.5637 }
      : { latitude: 25.033, longitude: 121.5654 },
    administrative_location: { city: "臺北市", district: "信義區", village: "西村里", village_code: "63000020-014" },
    location_status: "candidate",
    parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
    building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: ["no_approved_building_identity_evidence"], confirmation: null },
    confidence: { level: "medium", domain: "address_spatial_correlation", basis: ["normalized_address", "trusted_geocoding_coordinates"], limitations: ["not_legal_identity"] },
    evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding", checked_at: NOW }], checked_at: NOW, limitations: ["journey_browser_correlation_only"] },
    revalidation: { status: "current", conflicts: [] },
  };
}

function confirmedCase(options: { withMarket?: boolean } = {}) {
  const row = structuredClone(savedCase());
  (row.data as typeof row.data & { propertyIdentityAnchor: ReturnType<typeof identityAnchor> }).propertyIdentityAnchor = identityAnchor();
  if (options.withMarket === false) delete (row.data as Partial<typeof row.data>).marketInsight;
  return row;
}

function refreshedMarket(overrides: Record<string, unknown> = {}) {
  return {
    ...savedCase().data.marketInsight,
    period: "2026-08",
    average_unit_price: 58.2,
    avg_price_per_ping: 58.2,
    transaction_count: 24,
    transaction_volume: 24,
    record_count: 24,
    source_updated_at: "2026-09-30",
    history: [{ period: "2026-08", average_unit_price: 58.2, transaction_count: 24 }],
    median_unit_price_per_ping: 57.8,
    p25_unit_price_per_ping: 55.2,
    p75_unit_price_per_ping: 60.4,
    median_total_price: 2050,
    effective_sample_count: 24,
    source_file_hash: "provider-secret-hash",
    source_release_id: "provider-release-42",
    support_reference: "provider-support-reference",
    provider_debug_payload: { raw_rows: [1, 2, 3] },
    ...overrides,
  };
}

function actionableValuation(overrides: Record<string, unknown> = {}) {
  const comparable = (period: string, price: number) => ({
    transaction_period: period, city: "臺北市", district: "信義區", road: "市府路1號",
    building_type: "住宅大樓", area_ping: 30, unit_price_per_ping: price / 30, total_price: price,
    building_age_years: 5, distance_m: 100, similarity_score: 90, weight: 1,
    note: "官方成交", source: "official_plvr_opendata", source_label: "實價登錄",
  });
  return {
    valuation_status: "available", valuation_reason_code: "official_result_available",
    result_origin: "official", is_actionable: true, source: "postgres",
    data_status: { provider_debug_payload: { raw_rows: [1, 2, 3] } },
    data_composition: "official", estimate_data_composition: "official", estimate_source_label: "實價登錄",
    candidate_pool_size: 3, official_same_road_count: 3, official_same_district_count: 3,
    sample_same_road_count: 0, sample_same_district_count: 0, estimate_level: "road", matched_community: null,
    confidence_reason: "三筆官方成交通過檢查。", source_details: { file: "provider.csv", db_rows_returned: 300 },
    estimate_total_price: 2500, estimate_unit_price_per_ping: 83.3,
    price_range: { low: 2350, mid: 2500, high: 2650 },
    unit_price_distribution: { weighted_mean: 83.3, weighted_median: 83.3, p25: 80, p75: 86 },
    confidence: "high", confidence_score: 90,
    comparables: [comparable("2026-06", 2500), comparable("2026-05", 2460), comparable("2026-04", 2540)],
    valuation_explanation: { sample_count: 3, same_road_count: 3, same_district_count: 3, same_city_count: 3, same_building_type_count: 3, nearest_distance_m: 100, average_area_difference_ping: 0, average_age_difference_years: 0, average_similarity_score: 90, method: "官方成交加權" },
    methodology: ["官方成交"], disclaimer: "僅供市場判讀，不是正式估價。",
    provider_debug_payload: { raw_candidates: [1, 2, 3] },
    ...overrides,
  };
}

function actionableTrend() {
  return {
    trend_status: "available", trend_reason_code: "official_trend_available", is_actionable: true,
    source: "official_plvr_opendata", data_scope: "road", raw_period_min: "2026-01", raw_period_max: "2026-08",
    effective_period_min: "2026-01", effective_period_max: "2026-08", excluded_future_period_count: 0,
    excluded_out_of_window_count: 0, period_min: "2026-01", period_max: "2026-08", sample_count: 12,
    road_sample_count: 12, district_sample_count: 24,
    monthly_series: [
      { period: "2026-07", median_unit_price_per_ping: 81, p25_unit_price_per_ping: 78, p75_unit_price_per_ping: 84, transaction_count: 6 },
      { period: "2026-08", median_unit_price_per_ping: 83, p25_unit_price_per_ping: 80, p75_unit_price_per_ping: 86, transaction_count: 6 },
    ],
    yearly_series: [], recent_median_unit_price: 83, trend_annualized_rate: 2.4, volatility: 1.2,
    confidence_level: "high", confidence_reason: "官方成交期間足夠。",
    scenario_forecast: { conservative: [], base: [], optimistic: [] }, methodology: ["官方成交"], disclaimer: "僅供參考。",
  };
}

async function installCase(page: Page, row = savedCase()) {
  await page.addInitScript(({ storageKey, saved }) => {
    if (!window.localStorage.getItem(storageKey)) {
      window.localStorage.setItem(storageKey, JSON.stringify([saved]));
    }
  }, { storageKey: "proptech.savedCases.v1", saved: row });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

test("Market & Price route distinguishes price bases and presents saved evidence", async ({ page }) => {
  await installCase(page);
  await page.goto("/cases/market-price-case/market");

  await expect(page.getByRole("heading", { level: 1, name: "價格與市場" })).toBeVisible();
  await expect(page.getByText("可取得的市場證據對這個物件的價格提供了什麼訊息？")).toBeVisible();
  const context = page.getByTestId("market-price-context");
  const scope = page.getByTestId("market-scope-context");
  await expect(scope).toContainText("臺北市信義區");
  await expect(scope).toContainText("行政區（已回退）");
  await expect(scope).toContainText("18 筆");
  await expect(context).toContainText("開價");
  await expect(context).toContainText("2,480 萬元");
  await expect(context).toContainText("市場成交中位數");
  await expect(context).toContainText("1,850 萬元");
  await expect(context).toContainText("52.4 萬元／坪");

  await expect(page.getByTestId("market-primary-finding")).toContainText("物件身分尚未確認");
  await expect(page.getByTestId("market-primary-finding")).not.toContainText("開價高於");
  await expect(page.locator('[data-evidence-key="market"]')).toContainText("已恢復有限摘要");
  await expect(page.getByRole("heading", { name: "可比成交證據" })).toBeVisible();
  await expect(page.getByText("已儲存案件未保留逐筆可比成交")).toBeVisible();
  await expect(page.locator('[data-evidence-key="valuation"]')).toContainText("尚未查詢此區段");
  await expect(page.getByText("內政部不動產實價登錄")).toBeVisible();
  await expect(page.getByText("2025/01–2026/07")).toBeVisible();
  await expect(page.getByText("2026-08-31")).toBeVisible();
});

test("Market & Price route does not create document overflow at 390px", async ({ page }) => {
  await installCase(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/cases/market-price-case/market");

  await expect(page.getByTestId("market-price-context")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});

test("explicit Market refresh preserves visible evidence, saves a bounded summary, and reopens it", async ({ page }) => {
  let requestCount = 0;
  let releaseResponse: (() => void) | undefined;
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    await new Promise<void>((resolve) => { releaseResponse = resolve; });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(refreshedMarket()) });
  });
  await installCase(page, confirmedCase());
  await page.goto("/cases/market-price-case/market");

  expect(requestCount).toBe(0);
  await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
  await page.getByTestId("market-refresh-button").click();
  await expect.poll(() => requestCount).toBe(1);
  await expect(page.getByTestId("market-refresh-state")).toContainText("正在更新市場資料");
  await expect(page.getByTestId("market-price-context")).toContainText("1,850 萬元");
  releaseResponse?.();

  await expect(page.getByTestId("market-refresh-state")).toContainText("市場資料已更新");
  await expect(page.locator('[data-evidence-key="market"]')).toContainText("證據可供目前判讀");
  await expect(page.getByTestId("market-price-context")).toContainText("2,050 萬元");
  await expect(page.getByTestId("market-price-context")).toContainText("2,480 萬元");
  const stored = await page.evaluate(() => {
    const row = JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0];
    return {
      market: row.data.marketInsight,
      askingPrice: row.inputSummary.propertyPrice,
      activePrice: row.data.journeyContext.activePriceWan,
    };
  });
  expect(stored.market.median_total_price).toBe(2050);
  expect(stored.market.source_file_hash).toBeUndefined();
  expect(stored.market.source_release_id).toBeUndefined();
  expect(stored.market.support_reference).toBeUndefined();
  expect(stored.market.provider_debug_payload).toBeUndefined();
  expect(stored.askingPrice).toBe(2480);
  expect(stored.activePrice).toBe(2480);

  await page.reload();
  await expect(page.getByTestId("market-price-context")).toContainText("2,050 萬元");
  await expect(page.locator('[data-evidence-key="market"]')).toContainText("已恢復有限摘要");
  await expect(page.getByText("2026-09-30")).toBeVisible();
  expect(requestCount).toBe(1);
});

test("Market no-data is explicit and an unavailable retry cannot erase it", async ({ page }) => {
  let mode: "no_data" | "unavailable" = "no_data";
  await page.route("**/market-insights/query", (route) => {
    const body = mode === "no_data"
      ? refreshedMarket({
          data_status: "no_data", sample_status: "no_data", summary: "目前沒有符合資料。",
          average_unit_price: null, avg_price_per_ping: null, transaction_count: 0, transaction_volume: 0,
          record_count: 0, history: [], median_unit_price_per_ping: null, median_total_price: null,
          p25_unit_price_per_ping: null, p75_unit_price_per_ping: null, effective_sample_count: 0,
        })
      : refreshedMarket({ data_status: "unavailable", sample_status: "unavailable", history: [] });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await installCase(page, confirmedCase());
  await page.goto("/cases/market-price-case/market");

  await page.getByTestId("market-refresh-button").click();
  await expect(page.getByTestId("market-refresh-state")).toContainText("沒有可用成交資料");
  await expect(page.locator('[data-evidence-key="market"]')).toContainText("資料不足");
  await expect(page.getByTestId("market-price-context")).not.toContainText("1,850 萬元");

  mode = "unavailable";
  await page.getByTestId("market-refresh-button").click();
  await expect(page.getByTestId("market-refresh-state")).toContainText("目前無法更新");
  const persistedStatus = await page.evaluate(() => JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0].data.marketInsight.data_status);
  expect(persistedStatus).toBe("no_data");
});

test("Valuation refresh promotes only actionable evidence and keeps rows session-only", async ({ page }) => {
  let valuationMode: "actionable" | "malformed" | "unavailable" = "actionable";
  let valuationRequests = 0;
  let trendRequests = 0;
  await page.route("**/valuation/estimate", (route) => {
    valuationRequests += 1;
    const body = valuationMode === "actionable"
      ? actionableValuation()
      : valuationMode === "malformed"
        ? actionableValuation({ price_range: { low: null, mid: 2500, high: 2650 } })
        : actionableValuation({ valuation_status: "unavailable", result_origin: "none", is_actionable: false, comparables: [], estimate_total_price: null, estimate_unit_price_per_ping: null, price_range: { low: null, mid: null, high: null } });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.route("**/valuation/trend", (route) => {
    trendRequests += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(actionableTrend()) });
  });
  await page.route("**/market-insights/query", (route) => route.fulfill({ status: 503, body: "unavailable" }));
  await installCase(page, confirmedCase());
  await page.goto("/cases/market-price-case/market");

  expect(valuationRequests).toBe(0);
  expect(trendRequests).toBe(0);
  await page.getByTestId("valuation-refresh-button").click();
  await expect(page.getByTestId("valuation-refresh-state")).toContainText("價格推估已更新");
  await expect(page.locator('[data-evidence-key="valuation"]')).toContainText("證據可供目前判讀");
  await expect(page.getByTestId("market-price-context")).toContainText("2,350–2,650 萬元");
  await expect(page.getByRole("table", { name: "逐筆可比成交" })).toBeVisible();
  await expect(page.getByTestId("valuation-trend-summary")).toContainText("2.4%");
  const stored = await page.evaluate(() => {
    const row = JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0];
    return {
      valuation: row.data.valuation,
      trend: row.data.trend,
      askingPrice: row.inputSummary.propertyPrice,
      activePrice: row.data.journeyContext.activePriceWan,
      marketMedian: row.data.marketInsight.median_total_price,
    };
  });
  expect(stored.valuation.estimate_total_price).toBe(2500);
  expect(stored.valuation.comparables).toEqual([]);
  expect(stored.valuation.data_status).toBeUndefined();
  expect(stored.valuation.provider_debug_payload).toBeUndefined();
  expect(stored.trend).toBeUndefined();
  expect(stored.askingPrice).toBe(2480);
  expect(stored.activePrice).toBe(2480);
  expect(stored.marketMedian).toBe(1850);

  valuationMode = "malformed";
  await page.getByTestId("valuation-refresh-button").click();
  await expect(page.getByTestId("valuation-refresh-state")).toContainText("價格推估無法採用");
  await expect(page.getByTestId("market-price-context")).toContainText("2,350–2,650 萬元");
  await expect(page.getByTestId("market-price-context")).toContainText("1,850 萬元");
  valuationMode = "unavailable";
  await page.getByTestId("valuation-refresh-button").click();
  await expect(page.getByTestId("valuation-refresh-state")).toContainText("價格推估無法採用");

  await page.getByTestId("market-refresh-button").click();
  await expect(page.getByTestId("market-refresh-state")).toContainText("更新失敗");
  await expect(page.getByTestId("market-price-context")).toContainText("2,350–2,650 萬元");
  const persistedEstimate = await page.evaluate(() => JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0].data.valuation.estimate_total_price);
  expect(persistedEstimate).toBe(2500);

  await page.reload();
  await expect(page.getByTestId("market-price-context")).toContainText("2,350–2,650 萬元");
  await expect(page.locator('[data-evidence-key="valuation"]')).toContainText("已恢復有限摘要");
  await expect(page.getByText("已儲存案件未保留逐筆可比成交")).toBeVisible();
  await expect(page.getByTestId("valuation-trend-summary")).toHaveCount(0);
});

test("A to B context change rejects late Market, valuation, and trend responses", async ({ page }) => {
  let releaseMarket: (() => void) | undefined;
  let releaseValuation: (() => void) | undefined;
  let releaseTrend: (() => void) | undefined;
  let fulfilled = 0;
  await page.route("**/market-insights/query", async (route) => {
    await new Promise<void>((resolve) => { releaseMarket = resolve; });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(refreshedMarket()) });
    fulfilled += 1;
  });
  await page.route("**/valuation/estimate", async (route) => {
    await new Promise<void>((resolve) => { releaseValuation = resolve; });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(actionableValuation()) });
    fulfilled += 1;
  });
  await page.route("**/valuation/trend", async (route) => {
    await new Promise<void>((resolve) => { releaseTrend = resolve; });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(actionableTrend()) });
    fulfilled += 1;
  });
  await installCase(page, confirmedCase({ withMarket: false }));
  await page.goto("/cases/market-price-case/market");

  await page.getByTestId("market-refresh-button").click();
  await page.getByTestId("valuation-refresh-button").click();
  await expect.poll(() => Boolean(releaseMarket && releaseValuation && releaseTrend)).toBe(true);
  await page.evaluate(({ nextAnchor }) => {
    const key = "proptech.savedCases.v1";
    const row = JSON.parse(window.localStorage.getItem(key) ?? "[]")[0];
    row.updatedAt = "2026-10-05T09:00:00.000Z";
    row.inputSummary.road = "松仁路100號";
    row.data.inputs.road = "松仁路100號";
    row.data.journeyContext.propertyContext.road = "松仁路100號";
    row.data.journeyContext.propertyContext.addressSummary = "臺北市信義區松仁路100號";
    row.data.propertyIdentityAnchor = nextAnchor;
    window.localStorage.setItem(key, JSON.stringify([row]));
    window.dispatchEvent(new CustomEvent("proptech:saved-case-updated", { detail: row }));
  }, { nextAnchor: identityAnchor("臺北市信義區松仁路100號", "松仁路100號") });

  await expect(page.getByTestId("market-refresh-state")).toContainText("先前更新已作廢");
  await expect(page.getByTestId("valuation-refresh-state")).toContainText("先前更新已作廢");
  releaseMarket?.();
  releaseValuation?.();
  releaseTrend?.();
  await expect.poll(() => fulfilled).toBe(3);
  await page.waitForTimeout(100);

  const persisted = await page.evaluate(() => {
    const row = JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0];
    return { road: row.data.inputs.road, market: row.data.marketInsight, valuation: row.data.valuation, trend: row.data.trend };
  });
  expect(persisted.road).toBe("松仁路100號");
  expect(persisted.market).toBeUndefined();
  expect(persisted.valuation).toBeUndefined();
  expect(persisted.trend).toBeUndefined();
  await expect(page.getByTestId("market-price-context")).not.toContainText("2,050 萬元");
  await expect(page.getByTestId("market-price-context")).not.toContainText("2,350–2,650 萬元");
});
