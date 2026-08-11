import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";

const COUNTY = String.fromCodePoint(0x6843, 0x5712, 0x5e02);
const DISTRICT = String.fromCodePoint(0x4e2d, 0x58e2, 0x5340);
const UNAVAILABLE_CAVEAT = String.fromCodePoint(
  0x76ee, 0x524d, 0x6c92, 0x6709, 0x53ef, 0x5b89, 0x5168, 0x5448, 0x73fe, 0x7684, 0x5e02, 0x5834, 0x8cc7, 0x6599, 0x3002,
);

const availableResult = {
  city: COUNTY,
  county: COUNTY,
  district: DISTRICT,
  period: "2025-02",
  average_unit_price: 90000,
  avg_price_per_ping: 90000,
  transaction_count: 12,
  transaction_volume: 12,
  record_count: 12,
  summary: "Market data is available for reference.",
  source_name: "Test fixture",
  source_updated_at: "2025-02-01",
  coverage_status: "covered",
  data_status: "available",
  caveat: "Reference only.",
  disclaimer: "Reference only.",
  history: [{ period: "2025-02", average_unit_price: 90000, transaction_count: 12 }],
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

test("search button submits one market query and renders available data", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);

  let requestCount = 0;
  let requestPayload: unknown;
  let releaseResponse!: () => void;
  const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve; });
  await page.route("**/market-insights/query", async (route) => {
    requestCount += 1;
    requestPayload = route.request().postDataJSON();
    await responseGate;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(availableResult) });
  });

  const searchButton = page.getByTestId("market-insight-search-button");
  await searchButton.click();
  await expect(searchButton).toBeDisabled();
  expect(requestCount).toBe(1);
  expect(requestPayload).toEqual({ county: COUNTY, district: DISTRICT });

  releaseResponse();
  await expect(searchButton).toBeEnabled();
  await expect(page.getByTestId("market-primary-metrics").getByText("90,000", { exact: true })).toBeVisible();
  const priceTrend = page.getByTestId("market-price-trend");
  await expect(priceTrend).toContainText("目前只有 1 個有效期別，暫無足夠資料形成趨勢。");
  await expect(priceTrend.locator("polyline")).toHaveCount(0);
  await expect(priceTrend.locator("circle")).toHaveCount(1);
  expect(requestCount).toBe(1);
});

test("safe unavailable and network failures are visible", async ({ page }) => {
  await openMarketInsight(page);
  await selectRegion(page);
  const searchButton = page.getByTestId("market-insight-search-button");

  await page.route("**/market-insights/query", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...availableResult, data_status: "unavailable", coverage_status: "coverage_unknown", caveat: UNAVAILABLE_CAVEAT }),
    });
  });
  await searchButton.click();
  await expect(page.getByText(UNAVAILABLE_CAVEAT).first()).toBeVisible();

  await page.unroute("**/market-insights/query");
  await page.route("**/market-insights/query", (route) => route.abort("failed").catch(() => undefined));
  await searchButton.click();
  await expect(page.locator("[data-market-failure-reason]")).toBeVisible();
});
