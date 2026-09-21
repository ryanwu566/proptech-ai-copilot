import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import {
  buildMarketTrendStats,
  formatMarketPeriodChange,
  type MarketHistoryPoint,
} from "../lib/market-insight-visualization";
import { formatMarketCopy, getMarketInsightCopy } from "../lib/market-insight-copy";
import { buildMarketInsightSnapshot } from "../lib/market-insight-snapshot";
import { createClosedLoopJourneyState, selectJourneyPrice, updateJourneyMarketLocation } from "../lib/closed-loop-journey";
import type { MarketResult } from "../lib/api";

const COUNTY = "臺中市";
const DISTRICT = "北屯區";
const HISTORY: MarketHistoryPoint[] = [
  { period: "2026-05", average_unit_price: 33.21, transaction_count: 4 },
  { period: "2026-04", average_unit_price: 34.09, transaction_count: 27 },
  { period: "2026-03", average_unit_price: 34.85, transaction_count: 49 },
  { period: "2026-02", average_unit_price: 26.69, transaction_count: 13 },
  { period: "2026-01", average_unit_price: 33.39, transaction_count: 87 },
  { period: "2025-12", average_unit_price: 32.54, transaction_count: 169 },
];

const AVAILABLE_RESULT = {
  city: COUNTY,
  county: COUNTY,
  district: DISTRICT,
  period: "2026-05",
  average_unit_price: 33.21,
  avg_price_per_ping: 33.21,
  transaction_count: 4,
  transaction_volume: 4,
  record_count: 4,
  summary: "Market data is available for reference.",
  source_name: "Official PLVR OpenData aggregate",
  source_updated_at: "2026-06-07",
  coverage_status: "covered",
  data_status: "available",
  caveat: "Regional transaction reference only.",
  disclaimer: "市場資料只供區域交易參考，不是估價、核貸或購買建議。",
  median_unit_price_ntd_sqm: null,
  median_total_price_ntd: null,
  inclusion_count: 0,
  exclusion_count: 0,
  sample_status: null,
  freshness_status: null,
  price_distribution: [],
  building_type_distribution: [],
  age_band_distribution: [],
  history: HISTORY,
};

function roadAnalysisResult(level: "ROAD" | "DISTRICT", requestedRoad: string) {
  const normalizedRoad = requestedRoad.replace("4段", "四段");
  const roadCount = level === "ROAD" ? 12 : 6;
  const effectiveCount = level === "ROAD" ? 12 : 20;
  return {
    ...AVAILABLE_RESULT,
    transaction_count: effectiveCount,
    transaction_volume: effectiveCount,
    record_count: effectiveCount,
    sample_status: "sufficient",
    freshness_status: "fresh",
    requested_scope: "ROAD",
    requested_city: COUNTY,
    requested_district: DISTRICT,
    requested_road: requestedRoad,
    normalized_road: normalizedRoad,
    road_minimum_sample: 10,
    analysis_level: level,
    effective_analysis_level: level,
    effective_scope_label: level === "ROAD" ? `${COUNTY} / ${DISTRICT} / ${normalizedRoad}` : `${COUNTY} / ${DISTRICT}`,
    effective_sample_count: effectiveCount,
    road_sample_count: roadCount,
    district_sample_count: 20,
    fallback_applied: level === "DISTRICT",
    fallback_reason: level === "DISTRICT" ? "road_sample_below_threshold" : null,
    period_min: "2025-01",
    period_max: "2026-05",
    median_unit_price_per_ping: 35.5,
    p25_unit_price_per_ping: 32.1,
    p75_unit_price_per_ping: 38.9,
    median_total_price: 1680,
    median_area_ping: 31.5,
    volatility: 0.042,
    monthly_series: [],
    yearly_series: [],
  };
}

function unavailableRoadResult(requestedRoad: string) {
  return {
    ...roadAnalysisResult("DISTRICT", requestedRoad),
    data_status: "no_data",
    sample_status: "insufficient",
    analysis_level: "NOT_AVAILABLE",
    effective_analysis_level: "NOT_AVAILABLE",
    effective_scope_label: "",
    effective_sample_count: 0,
    road_sample_count: 3,
    district_sample_count: 8,
    fallback_reason: "district_sample_below_threshold",
    period: null,
    period_min: null,
    period_max: null,
    average_unit_price: null,
    avg_price_per_ping: null,
    transaction_count: null,
    transaction_volume: null,
    record_count: null,
    median_unit_price_per_ping: null,
    p25_unit_price_per_ping: null,
    p75_unit_price_per_ping: null,
    median_total_price: null,
    median_area_ping: null,
    volatility: null,
    history: [],
    monthly_series: [],
    yearly_series: [],
  };
}

function propertyFinderResult() {
  return {
    search_status: "available",
    search_reason_code: "official_result_available",
    is_actionable: true,
    summary: { matched_count: 1, city_count: 1, district_count: 1, road_count: 1, budget_min: null, budget_max: 2500, period_min: "2026-05", period_max: "2026-05", data_source_label: "官方 PLVR 實價登錄", message: "找到歷史成交方向。", disclaimer: "僅供歷史成交參考。" },
    district_suggestions: [],
    road_suggestions: [],
    matched_transactions: [{ transaction_period: "2026-05", city: COUNTY, district: DISTRICT, road: "文心路四段", building_type: "住宅大樓", area_ping: 31.5, total_price: 1680, unit_price_per_ping: 53.33, building_age_years: 12, floor: 8, source_label: "官方 PLVR" }],
    methodology: "Official historical transactions only.",
    disclaimer: "僅供歷史成交參考。",
  };
}

async function openMarketInsight(page: Page) {
  await page.goto("/");
  const menuButton = page.getByRole("button", { name: /開啟選單|Open menu|メニューを開く|메뉴 열기/ });
  if (await menuButton.isVisible()) await menuButton.click();
  await page.getByRole("button", { name: /Market Insight/ }).first().click();
  await expect(page.getByRole("heading", { name: "Market Insight" })).toBeVisible();
}

async function selectRegion(page: Page) {
  const form = page.getByTestId("market-insight-search-form");
  await form.locator("select").nth(0).selectOption(COUNTY);
  await form.locator("select").nth(1).selectOption(DISTRICT);
}

test.describe("buildMarketTrendStats", () => {
  test("handles six valid points", () => {
    expect(buildMarketTrendStats(HISTORY).periodCount).toBe(6);
  });

  test("handles two valid points", () => {
    const stats = buildMarketTrendStats(HISTORY.slice(0, 2));
    expect(stats.latest?.period).toBe("2026-05");
    expect(stats.previous?.period).toBe("2026-04");
  });

  test("handles one valid point without a comparison", () => {
    const stats = buildMarketTrendStats(HISTORY.slice(0, 1));
    expect(stats.periodCount).toBe(1);
    expect(stats.previous).toBeNull();
    expect(stats.periodChange).toBeNull();
  });

  test("handles zero points", () => {
    expect(buildMarketTrendStats([])).toEqual({
      periodCount: 0,
      latest: null,
      previous: null,
      periodChange: null,
      averageUnitPrice: null,
      maxPoint: null,
      minPoint: null,
      totalTransactions: null,
    });
  });

  test("filters structurally invalid points and caps the window at six", () => {
    const invalid = { period: "", average_unit_price: Number.NaN, transaction_count: -1 };
    const stats = buildMarketTrendStats([invalid, ...HISTORY, { period: "2025-11", average_unit_price: 31, transaction_count: 2 }]);
    expect(stats.periodCount).toBe(6);
    expect(stats.latest?.period).toBe("2026-05");
  });

  test("calculates a positive period change", () => {
    expect(buildMarketTrendStats([
      { period: "B", average_unit_price: 12, transaction_count: 1 },
      { period: "A", average_unit_price: 10, transaction_count: 1 },
    ]).periodChange).toBeCloseTo(0.2);
  });

  test("calculates the production-shaped negative period change", () => {
    const change = buildMarketTrendStats(HISTORY).periodChange;
    expect(change).toBeCloseTo(-0.0258140188);
    expect(formatMarketPeriodChange(change)).toBe("-2.6%");
  });

  test("formats zero period change without a directional label", () => {
    const change = buildMarketTrendStats([
      { period: "B", average_unit_price: 10, transaction_count: 1 },
      { period: "A", average_unit_price: 10, transaction_count: 1 },
    ]).periodChange;
    expect(change).toBe(0);
    expect(formatMarketPeriodChange(change)).toBe("0.0%");
  });

  test("returns null when the previous price is zero", () => {
    const stats = buildMarketTrendStats([
      { period: "B", average_unit_price: 10, transaction_count: 1 },
      { period: "A", average_unit_price: 0, transaction_count: 1 },
    ]);
    expect(stats.periodChange).toBeNull();
  });

  test("calculates the arithmetic mean", () => {
    expect(buildMarketTrendStats(HISTORY).averageUnitPrice).toBeCloseTo(32.4616666667);
  });

  test("selects the maximum point", () => {
    expect(buildMarketTrendStats(HISTORY).maxPoint).toEqual(HISTORY[2]);
  });

  test("selects the minimum point", () => {
    expect(buildMarketTrendStats(HISTORY).minPoint).toEqual(HISTORY[3]);
  });

  test("sums recent transactions", () => {
    expect(buildMarketTrendStats(HISTORY).totalTransactions).toBe(349);
  });

  test("does not mutate its input", () => {
    const input = HISTORY.map((point) => ({ ...point }));
    const before = JSON.stringify(input);
    buildMarketTrendStats(input);
    expect(JSON.stringify(input)).toBe(before);
  });

  test("uses an N-period label when fewer than six periods exist", () => {
    const labels = getMarketInsightCopy("zh-TW");
    expect(formatMarketCopy(labels.recentAverageN, { count: 4 })).toBe("近 4 期平均單價");
  });

  test("provides the complete analysis contract in all four locales", () => {
    for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
      const labels = getMarketInsightCopy(locale);
      for (const key of ["summary", "periodComparison", "recentAverageN", "highestAverage", "lowestAverage", "recentTransactionsN", "priceTrend", "volumeTrend", "history", "initial", "loading", "noData", "unavailable", "networkError", "supportReference", "boundary"] as const) {
        expect(labels[key].trim(), `${locale}.${key}`).not.toBe("");
      }
    }
  });
});

test("limited-sample path sends one POST and renders cautious analysis, charts, and history", async ({ page }) => {
  await openMarketInsight(page);
  await expect(page.getByTestId("market-insight-initial")).toHaveText("請選擇縣市與行政區後查詢市場資料。");
  await expect(page.getByTestId("market-insight-unavailable")).toHaveCount(0);
  await selectRegion(page);

  let requestCount = 0;
  let requestPayload: unknown;
  let releaseResponse!: () => void;
  const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve; });
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    requestPayload = route.request().postDataJSON();
    await responseGate;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(AVAILABLE_RESULT) });
  });

  const form = page.getByTestId("market-insight-search-form");
  const button = page.getByTestId("market-insight-search-button");
  await button.click();
  await expect.poll(() => requestCount).toBe(1);
  expect(requestPayload).toEqual({ county: COUNTY, district: DISTRICT });
  await expect(button).toBeDisabled();
  await expect(button).toHaveText("查詢中…");
  await expect(form).toHaveAttribute("aria-busy", "true");
  await expect(page.getByTestId("market-insight-loading")).toBeVisible();
  await button.click({ force: true });
  expect(requestCount).toBe(1);

  releaseResponse();
  await expect(page.getByTestId("market-insight-low_sample")).toBeVisible();
  await expect(page.getByTestId("market-state-guidance")).toContainText("樣本有限");
  await expect(button).toBeEnabled();
  const primary = page.getByTestId("market-primary-metrics");
  await expect(primary).toContainText("33.21");
  await expect(primary).toContainText("4 筆");
  await expect(primary).toContainText("2026-05");
  const derived = page.getByTestId("market-derived-stats");
  await expect(derived).toContainText("-2.6%");
  await expect(derived).toContainText("32.46 萬元／坪");
  await expect(derived).toContainText("34.85 萬元／坪 · 2026-03");
  await expect(derived).toContainText("26.69 萬元／坪 · 2026-02");
  await expect(derived).toContainText("349 筆");
  await expect(page.getByTestId("market-price-trend")).toBeVisible();
  await expect(page.getByTestId("market-volume-trend")).toBeVisible();
  await expect(page.getByTestId("market-price-trend").getByRole("img", { name: "平均單價趨勢" })).toBeVisible();
  await page.getByTestId("market-price-trend").locator("g[tabindex='0']").first().focus();
  await expect(page.getByTestId("market-price-trend").locator("g[tabindex='0']").first()).toBeFocused();
  await expect(page.getByRole("table", { name: "最近期別市場資料" })).toBeVisible();
  await expect(page.getByTestId("market-source-metadata")).toContainText("Official PLVR OpenData aggregate");
  expect(requestCount).toBe(1);
});

test("Enter on the submit button sends exactly one POST", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  let requestCount = 0;
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(AVAILABLE_RESULT) });
  });
  const button = page.getByTestId("market-insight-search-button");
  await button.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("market-insight-low_sample")).toBeVisible();
  expect(requestCount).toBe(1);
});

test("district-only serialized null scope fields do not render a road scope summary", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await page.route("**/market-insights/query", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      ...AVAILABLE_RESULT,
      requested_scope: null,
      analysis_level: null,
      effective_analysis_level: null,
      effective_scope_label: null,
      road_minimum_sample: null,
      road_sample_count: null,
      district_sample_count: null,
    }),
  }));

  await page.getByTestId("market-insight-search-button").click();

  await expect(page.getByTestId("market-insight-low_sample")).toBeVisible();
  await expect(page.getByTestId("market-scope-summary")).toHaveCount(0);
});

test("market handoff changes only geography and preserves a manual price assumption", () => {
  const initial = createClosedLoopJourneyState({
    city: "臺北市",
    district: "大安區",
    road: "和平東路二段",
    addressSummary: "臺北市大安區和平東路二段",
    buildingType: "住宅大樓",
    areaPing: 35,
    buildingAgeYears: 12,
    floor: 8,
    askingPriceWan: 2200,
    selectionStatus: "selected",
  });
  const manual = selectJourneyPrice(initial, "manual", 1888);

  const next = updateJourneyMarketLocation(manual, { city: COUNTY, district: DISTRICT, road: "文心路四段" });

  expect(next.propertyContext.city).toBe(COUNTY);
  expect(next.propertyContext.district).toBe(DISTRICT);
  expect(next.propertyContext.road).toBe("文心路四段");
  expect(next.propertyContext.buildingType).toBe("住宅大樓");
  expect(next.propertyContext.areaPing).toBe(35);
  expect(next.propertyContext.askingPriceWan).toBe(2200);
  expect(next.priceBasis).toBe("manual");
  expect(next.manualPriceWan).toBe(1888);
  expect(next.activePriceWan).toBe(1888);
});

test("explicit same-location market handoff clears stale market evidence", () => {
  const initial = createClosedLoopJourneyState({
    city: COUNTY,
    district: DISTRICT,
    road: "文心路四段",
    addressSummary: `${COUNTY}${DISTRICT}文心路四段`,
    selectionStatus: "selected",
  });
  const withStaleMarket = {
    ...initial,
    marketResult: roadAnalysisResult("ROAD", "崇德路二段") as MarketResult,
    marketStatus: "available" as const,
  };

  const next = updateJourneyMarketLocation(withStaleMarket, {
    city: COUNTY,
    district: DISTRICT,
    road: "文心路四段",
  });

  expect(next.marketResult).toBeUndefined();
  expect(next.marketStatus).toBe("not_started");
});

test("road-aware results do not emit a district-semantic safe snapshot", () => {
  const snapshot = buildMarketInsightSnapshot(
    roadAnalysisResult("ROAD", "文心路四段") as MarketResult,
    "2026-09-21T00:00:00.000Z",
  );

  expect(snapshot).toBeNull();
});

test("road query sends only after submit and distinguishes ROAD from DISTRICT fallback", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  let requestCount = 0;
  const payloads: Array<Record<string, unknown>> = [];
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    payloads.push(payload);
    const road = String(payload.road || "");
    const level = road === "文心路4段" ? "ROAD" : "DISTRICT";
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(roadAnalysisResult(level, road)) });
  });

  const roadInput = page.getByTestId("market-road-input");
  await roadInput.fill("文心路4段");
  expect(requestCount).toBe(0);
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-available")).toBeVisible();
  await expect(page.getByTestId("market-scope-summary")).toContainText(`${COUNTY} / ${DISTRICT} / 文心路四段`);
  await expect(page.getByTestId("market-scope-summary")).toContainText("2025-01 – 2026-05");
  await expect(page.getByTestId("market-scope-summary")).toContainText("路段");
  await expect(page.getByTestId("market-fallback-notice")).toHaveCount(0);
  await expect(page.getByTestId("market-primary-metrics")).toContainText("有效期間交易筆數");
  await expect(page.getByTestId("market-primary-metrics")).not.toContainText("本期交易筆數");
  expect(payloads[0]).toEqual({ county: COUNTY, district: DISTRICT, road: "文心路4段" });

  await roadInput.fill("崇德路二段");
  await expect(page.getByTestId("market-insight-available")).toHaveCount(0);
  expect(requestCount).toBe(1);
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-scope-summary")).toContainText("崇德路二段");
  await expect(page.getByTestId("market-scope-summary")).toContainText(`${COUNTY} / ${DISTRICT}`);
  await expect(page.getByTestId("market-fallback-notice")).toContainText("6 筆有效交易");
  await expect(page.getByTestId("market-fallback-notice")).toContainText("10 筆門檻");
  expect(payloads[1]).toEqual({ county: COUNTY, district: DISTRICT, road: "崇德路二段" });
});

test("Property Finder hands city district and road to Market Insight without auto-querying", async ({ page }) => {
  let marketRequestCount = 0;
  let marketPayload: Record<string, unknown> | undefined;
  await page.route("**/valuation/property-search", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(propertyFinderResult()) }));
  await page.route("**/market-insights/query", async (route) => {
    marketRequestCount += 1;
    marketPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(roadAnalysisResult("ROAD", "文心路四段")) });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "搜尋看屋方向" }).click();
  const transactions = page.locator("#property-finder details").filter({ hasText: "查看完整成交樣本" });
  await transactions.locator("summary").click();
  await transactions.getByRole("button", { name: "查看此路段歷史行情" }).click();

  await expect(page.locator("#journey-stage-location")).toBeVisible();
  await expect(page.locator("#location-market-market-heading")).toBeVisible();
  await expect(page.getByTestId("market-county-select")).toHaveValue(COUNTY);
  await expect(page.getByTestId("market-district-select")).toHaveValue(DISTRICT);
  await expect(page.getByTestId("market-road-input")).toHaveValue("文心路四段");
  expect(marketRequestCount).toBe(0);

  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-scope-summary")).toContainText("文心路四段");
  expect(marketRequestCount).toBe(1);
  expect(marketPayload).toEqual({ county: COUNTY, district: DISTRICT, road: "文心路四段" });
});

test("NOT_AVAILABLE keeps scope explanation but renders no charts or fake metrics", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await page.getByTestId("market-road-input").fill("文心路四段");
  await page.route("**/market-insights/query", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(unavailableRoadResult("文心路四段")) }));
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-no-data")).toBeVisible();
  await expect(page.getByTestId("market-scope-summary")).toContainText("資料不足");
  await expect(page.getByTestId("market-fallback-notice")).toContainText("8 筆有效交易");
  await expect(page.getByTestId("market-primary-metrics")).toHaveCount(0);
  await expect(page.getByTestId("market-price-trend")).toHaveCount(0);
  await expect(page.getByTestId("market-volume-trend")).toHaveCount(0);
});

test("normal official sample renders the available state with provenance", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await page.route("**/market-insights/query", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ ...AVAILABLE_RESULT, transaction_count: 20, transaction_volume: 20, record_count: 20, sample_status: "sufficient", freshness_status: "current" }),
  }));
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-available")).toBeVisible();
  await expect(page.getByTestId("market-primary-metrics")).toContainText("20 筆");
  await expect(page.getByTestId("market-source-metadata")).toContainText("Official PLVR OpenData aggregate");
});

test("stale official evidence remains visible with an explicit vintage warning", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await page.route("**/market-insights/query", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ ...AVAILABLE_RESULT, transaction_count: 20, transaction_volume: 20, record_count: 20, sample_status: "sufficient", freshness_status: "stale" }),
  }));
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-stale")).toBeVisible();
  await expect(page.getByTestId("market-state-guidance")).toContainText("資料期別較早");
  await expect(page.getByTestId("market-primary-metrics")).toContainText("33.21");
  await expect(page.getByTestId("market-source-metadata")).toContainText("2026-06-07");
});

test("a second query clears the first result until the replacement response arrives", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  let requestCount = 0;
  let releaseSecond!: () => void;
  const secondResponseGate = new Promise<void>((resolve) => { releaseSecond = resolve; });
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    if (requestCount === 2) await secondResponseGate;
    const average = requestCount === 1 ? 31.11 : 45.67;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...AVAILABLE_RESULT,
        average_unit_price: average,
        avg_price_per_ping: average,
        transaction_count: 20,
        transaction_volume: 20,
        record_count: 20,
        sample_status: "sufficient",
      }),
    });
  });
  const button = page.getByTestId("market-insight-search-button");
  await button.click();
  await expect(page.getByTestId("market-primary-metrics")).toContainText("31.11");
  await button.click();
  await expect(page.getByTestId("market-insight-loading")).toBeVisible();
  await expect(page.getByTestId("market-primary-metrics")).toHaveCount(0);
  await expect(page.getByText("31.11", { exact: false })).toHaveCount(0);
  releaseSecond();
  await expect(page.getByTestId("market-primary-metrics")).toContainText("45.67");
  await expect(page.getByText("31.11", { exact: false })).toHaveCount(0);
  expect(requestCount).toBe(2);
});

test("network failure has a distinct safe state and retry replaces it with real evidence", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  let requestCount = 0;
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    if (requestCount === 1) {
      await route.abort("failed").catch(() => undefined);
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...AVAILABLE_RESULT, transaction_count: 20, transaction_volume: 20, record_count: 20, sample_status: "sufficient" }) });
  });
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-network-error")).toContainText("目前無法連線至市場資料服務，請稍後重試。");
  await page.getByTestId("market-insight-retry").click();
  await expect(page.getByTestId("market-insight-available")).toContainText("33.21");
  await expect(page.getByTestId("market-insight-network-error")).toHaveCount(0);
  expect(requestCount).toBe(2);
});

test("backend unavailable shows the safe message and bounded support reference", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await page.route("**/market-insights/query", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...AVAILABLE_RESULT,
        data_status: "unavailable",
        coverage_status: "coverage_unknown",
        support_reference: "market-ref_123",
      }),
    });
  });
  await page.getByTestId("market-insight-search-button").click();
  const state = page.getByTestId("market-insight-unavailable");
  await expect(state).toContainText("市場資料暫時無法使用，請稍後再試。");
  await expect(state).toContainText("參考代碼: market-ref_123");
});

test("no-data response does not render fake zero metrics", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await page.route("**/market-insights/query", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...AVAILABLE_RESULT,
        data_status: "no_data",
        average_unit_price: null,
        avg_price_per_ping: null,
        transaction_count: null,
        transaction_volume: null,
        record_count: null,
        history: [],
      }),
    });
  });
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-no-data")).toContainText("目前此區域尚無足夠的官方市場資料。");
  await expect(page.getByTestId("market-primary-metrics")).toHaveCount(0);
});

test("partial response preserves real metrics and marks missing metrics honestly", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await page.route("**/market-insights/query", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...AVAILABLE_RESULT,
        data_status: "incomplete",
        coverage_status: "partial",
        transaction_count: null,
        transaction_volume: null,
        record_count: 4,
        sample_status: "limited",
        summary: "Some official aggregate fields are unavailable.",
      }),
    });
  });
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-partial")).toBeVisible();
  await expect(page.getByTestId("market-state-guidance")).toBeVisible();
  await expect(page.getByTestId("market-primary-metrics")).toContainText("33.21");
  await expect(page.getByTestId("market-primary-metrics")).not.toContainText("0 筆");
  await expect(page.getByTestId("market-source-metadata")).toContainText("Official PLVR OpenData aggregate");
});

test("mobile analysis remains readable without page-level horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openMarketInsight(page);
  await selectRegion(page);
  const roadInput = page.getByTestId("market-road-input");
  await roadInput.fill("文心路四段");
  await roadInput.focus();
  await expect(roadInput).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByTestId("market-insight-search-button")).toBeFocused();
  await page.route("**/market-insights/query", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(AVAILABLE_RESULT) });
  });
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-primary-metrics")).toBeVisible();
  await expect(page.getByTestId("market-price-trend")).toBeVisible();
  await expect(page.getByTestId("market-volume-trend")).toBeVisible();
  await expect(page.getByTestId("market-history-table")).toBeVisible();
  const hasPageOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(hasPageOverflow).toBe(false);
});
