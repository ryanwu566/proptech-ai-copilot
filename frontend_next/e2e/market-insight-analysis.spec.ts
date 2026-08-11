import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import {
  buildMarketTrendStats,
  formatMarketPeriodChange,
  type MarketHistoryPoint,
} from "../lib/market-insight-visualization";
import { formatMarketCopy, getMarketInsightCopy } from "../lib/market-insight-copy";

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

test("happy path sends one POST and renders loading, analysis, charts, and history", async ({ page }) => {
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
  await expect(page.getByTestId("market-insight-available")).toBeVisible();
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
  await expect(page.getByTestId("market-insight-available")).toBeVisible();
  expect(requestCount).toBe(1);
});

test("network failure has a distinct safe state and one request", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  let requestCount = 0;
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    await route.abort("failed").catch(() => undefined);
  });
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-network-error")).toContainText("目前無法連線至市場資料服務，請稍後重試。");
  expect(requestCount).toBe(1);
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

test("mobile analysis remains readable without page-level horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openMarketInsight(page);
  await selectRegion(page);
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
