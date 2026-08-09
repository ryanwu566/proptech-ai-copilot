import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";

const COUNTY = "臺中市";
const DISTRICT = "北屯區";

const directQueryResult = {
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
  source_name: "Official PLVR aggregate",
  source_updated_at: "2026-06-01",
  coverage_status: "covered",
  data_status: "available",
  caveat: "Regional transaction reference only.",
  disclaimer: "市場資料只供區域交易參考，不是估價、核貸或購買建議。",
  median_unit_price_ntd_sqm: null,
  mean_unit_price_ntd_sqm: null,
  median_total_price_ntd: null,
  inclusion_count: 0,
  exclusion_count: 0,
  sample_status: null,
  freshness_status: null,
  price_distribution: [],
  building_type_distribution: [],
  age_band_distribution: [],
  history: [
    { period: "2026-05", average_unit_price: 33.21, transaction_count: 4 },
    { period: "2026-04", average_unit_price: 34.09, transaction_count: 27 },
  ],
};

async function openMarketInsight(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: /Market Insight/ }).first().click();
  await expect(page.getByRole("heading", { name: "Market Insight" })).toBeVisible();
}

async function selectRegion(page: Page) {
  const selects = page.locator("select");
  await selects.nth(1).selectOption(COUNTY);
  await selects.nth(2).selectOption(DISTRICT);
}

async function submitResult(page: Page, result: Record<string, unknown> & { summary: string }) {
  await page.route("**/market-insights/query", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) });
  });
  const searchButton = page.getByTestId("market-insight-search-button");
  await searchButton.click();
  await expect(searchButton).toBeEnabled();
  await expect(page.getByTestId("market-primary-metrics")).toBeVisible();
}

test("direct-query metrics keep their real units and hide unsupported analysis", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await submitResult(page, directQueryResult);

  const metrics = page.getByTestId("market-primary-metrics");
  await expect(metrics.getByText("平均單價（萬元／坪）", { exact: true })).toBeVisible();
  await expect(metrics.getByText("33.21", { exact: true })).toBeVisible();
  await expect(metrics.getByText("本期交易筆數", { exact: true })).toBeVisible();
  await expect(metrics.getByText("4", { exact: true })).toBeVisible();

  const metadata = page.getByTestId("market-source-metadata");
  await expect(metadata).toContainText("資料期別: 2026-05");
  await expect(metadata).toContainText("資料來源: Official PLVR aggregate");
  await expect(metadata).toContainText("資料更新: 2026-06-01");
  await expect(metadata).toContainText("涵蓋狀態: 已有資料涵蓋");

  await expect(page.getByText("平均單價（元／平方公尺）", { exact: true })).toHaveCount(0);
  await expect(page.getByText("中位單價（元／平方公尺）", { exact: true })).toHaveCount(0);
  await expect(page.getByText("中位總價（元）", { exact: true })).toHaveCount(0);
  await expect(page.getByText("納入筆數", { exact: true })).toHaveCount(0);
  await expect(page.getByText("排除筆數", { exact: true })).toHaveCount(0);
  await expect(page.getByText("unknown", { exact: true })).toHaveCount(0);
  await expect(page.getByText("資料分布", { exact: true })).toHaveCount(0);

  const history = page.getByTestId("market-history-table");
  await expect(history.getByRole("columnheader", { name: "平均單價（萬元／坪）" })).toBeVisible();
  await expect(history.getByRole("columnheader", { name: "交易筆數（筆）" })).toBeVisible();
  await expect(history.getByRole("row").filter({ hasText: "2026-05" })).toContainText("33.21");
  await expect(history.getByRole("row").filter({ hasText: "2026-05" })).toContainText("4 筆");
  await expect(history.getByRole("row").filter({ hasText: "2026-04" })).toContainText("34.09");
  await expect(history.getByRole("row").filter({ hasText: "2026-04" })).toContainText("27 筆");
});

test("advanced metrics appear only when the response provides real values", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  await submitResult(page, {
    ...directQueryResult,
    median_unit_price_ntd_sqm: 123456,
    median_total_price_ntd: 12000000,
    inclusion_count: 8,
    exclusion_count: 1,
    sample_status: "limited",
    freshness_status: "current",
  });

  await expect(page.getByText("中位單價（元／平方公尺）", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("中位總價（元）", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("納入筆數", { exact: true })).toBeVisible();
  await expect(page.getByText("排除筆數", { exact: true })).toBeVisible();
  const metadata = page.getByTestId("market-source-metadata");
  await expect(metadata).toContainText("樣本狀態: limited");
  await expect(metadata).toContainText("資料新鮮度: current");
});
