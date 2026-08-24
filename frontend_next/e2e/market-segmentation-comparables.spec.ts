import type { Page, Route } from "@playwright/test";
import { expect, test } from "./fixtures";


const COUNTY = "新北市";
const DISTRICT = "永和區";
const OVERVIEW = {
  city: COUNTY, county: COUNTY, district: DISTRICT, period: "2026-07",
  average_unit_price: 62.4, avg_price_per_ping: 62.4,
  transaction_count: 30, transaction_volume: 30, record_count: 30,
  summary: "Official district market evidence is available.",
  source_name: "Official PLVR OpenData aggregate", source_updated_at: "2026-08-20",
  coverage_status: "covered", data_status: "available", sample_status: "sufficient", freshness_status: "current",
  caveat: "Regional transaction reference only.", disclaimer: "Reference only.",
  history: [{ period: "2026-07", average_unit_price: 62.4, transaction_count: 30 }],
};

function segmentResult(overrides: Record<string, unknown> = {}) {
  return {
    state: "available", data_status: "available", county: COUNTY, district: DISTRICT,
    segment_identity: `${COUNTY}${DISTRICT} · 住宅大樓 · 30–40 ping`,
    matching_transaction_count: 18, eligible_transaction_count: 120, base_transaction_count: 20,
    excluded_transaction_count: 102, known_age_count: 19, unknown_age_count: 1,
    known_floor_count: 18, unknown_floor_count: 2,
    average_unit_price_per_ping: 63.2, median_unit_price_per_ping: 62.5,
    p25_unit_price_per_ping: 58.4, p75_unit_price_per_ping: 68.1, average_total_price_wan: 2210,
    period_min: "2024-01", period_max: "2026-07",
    filters_applied: { county: COUNTY, district: DISTRICT, period_from: "2023-09", period_to: "2026-08", building_type: "住宅大樓", area_min_ping: 30, area_max_ping: 40, age_min_years: null, age_max_years: null, known_age_only: false, floor_position: "", high_value_only: false, high_value_threshold_wan: 3000 },
    building_type_distribution: [{ category: "住宅大樓", count: 80, raw_values: ["住宅大樓(11層含以上有電梯)"] }],
    floor_position_rule: "Known-only deterministic ratio bands.", source: "Official PLVR OpenData",
    source_updated_at: "2026-08-20", sample_state: "available", caveats: [], ...overrides,
  };
}

function comparableResult(overrides: Record<string, unknown> = {}) {
  return {
    state: "low_sample", data_status: "low_sample", county: COUNTY, district: DISTRICT,
    filters_applied: segmentResult().filters_applied, comparable_count: 1,
    comparables: [{
      transaction_period: "2026-06", county: COUNTY, district: DISTRICT, road: "永和路一段", location_display: "永和路一段",
      building_type: "住宅大樓", raw_building_type: "住宅大樓(11層含以上有電梯)", area_ping: 34,
      floor: 9, total_floor: 12, floor_position: "high", approximate_building_age_years: 8,
      total_price_wan: 2312, unit_price_per_ping: 68, area_difference_ping: 1,
      age_difference_years: null, floor_position_relationship: "known", period_recency_months: 2,
      source: "Official PLVR OpenData",
    }],
    ordering_method: "Transparent evidence ordering", dedupe_method: "dedupe_key", opaque_similarity_score: false,
    coordinates_required: false, source: "Official PLVR OpenData", caveats: [], ...overrides,
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function openMarket(page: Page, mobile = false) {
  await page.goto("/");
  if (mobile) await page.getByRole("button", { name: /開啟選單|Open menu|メニューを開く|메뉴 열기/ }).click();
  await page.getByRole("navigation").getByRole("button", { name: /Market Insight/ }).click();
  await expect(page.getByRole("heading", { name: "Market Insight" })).toBeVisible();
}

async function loadOverview(page: Page) {
  await page.route("**/market-insights/query", (route) => fulfillJson(route, OVERVIEW));
  await page.getByTestId("market-county-select").selectOption(COUNTY);
  await page.getByTestId("market-district-select").selectOption(DISTRICT);
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-segmentation-engine")).toBeVisible();
}

async function installSuccessfulSegmentRoutes(page: Page) {
  await page.route("**/market-insights/segments", (route) => fulfillJson(route, segmentResult()));
  await page.route("**/market-insights/segment-comparables", (route) => fulfillJson(route, comparableResult()));
}

test("desktop 1440 completes the buyer-first segment and comparable workflow", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openMarket(page);
  await loadOverview(page);
  await installSuccessfulSegmentRoutes(page);

  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-segment-available")).toContainText("62.5");
  await expect(page.getByTestId("market-segment-metrics")).toContainText("18 筆");
  await expect(page.getByTestId("market-comparables-low_sample")).toContainText("永和路一段");
  await expect(page.getByTestId("market-comparables-low_sample")).toContainText("34 坪");
  await expect(page.getByTestId("market-comparables-low_sample")).not.toContainText("相似度");
  await expect(page.getByTestId("segment-active-filters")).toContainText("[30, 40) 坪");
});

test("mobile 390 completes the same workflow without page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openMarket(page, true);
  await loadOverview(page);
  await installSuccessfulSegmentRoutes(page);

  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-segment-available")).toBeVisible();
  await expect(page.getByTestId("market-comparables-low_sample")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("A to B switch while A is pending leaves only B evidence", async ({ page }) => {
  await openMarket(page);
  await loadOverview(page);
  let releaseA!: () => void;
  const gateA = new Promise<void>((resolve) => { releaseA = resolve; });
  await page.route("**/market-insights/segments", async (route) => {
    const body = route.request().postDataJSON() as { building_type: string };
    if (body.building_type === "住宅大樓") {
      await gateA;
      await fulfillJson(route, segmentResult({ median_unit_price_per_ping: 51.1, segment_identity: "A stale" })).catch(() => undefined);
      return;
    }
    await fulfillJson(route, segmentResult({ median_unit_price_per_ping: 72.2, segment_identity: "B current" }));
  });
  await page.route("**/market-insights/segment-comparables", (route) => fulfillJson(route, comparableResult()));

  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-segment-loading")).toBeVisible();
  await page.getByTestId("segment-building-type").selectOption("華廈");
  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-segment-available")).toContainText("72.2");
  releaseA();
  await expect(page.getByText("51.1", { exact: false })).toHaveCount(0);
  await expect(page.getByTestId("segment-active-filters")).toContainText("華廈");
});

test("B to A reverse switch leaves only the latest A evidence", async ({ page }) => {
  await openMarket(page);
  await loadOverview(page);
  await page.getByTestId("segment-building-type").selectOption("華廈");
  let releaseB!: () => void;
  const gateB = new Promise<void>((resolve) => { releaseB = resolve; });
  await page.route("**/market-insights/segments", async (route) => {
    const body = route.request().postDataJSON() as { building_type: string };
    if (body.building_type === "華廈") {
      await gateB;
      await fulfillJson(route, segmentResult({ median_unit_price_per_ping: 74.4, segment_identity: "B stale" })).catch(() => undefined);
      return;
    }
    await fulfillJson(route, segmentResult({ median_unit_price_per_ping: 59.9, segment_identity: "A current" }));
  });
  await page.route("**/market-insights/segment-comparables", (route) => fulfillJson(route, comparableResult()));

  await page.getByTestId("market-segment-submit").click();
  await page.getByTestId("segment-building-type").selectOption("住宅大樓");
  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-segment-available")).toContainText("59.9");
  releaseB();
  await expect(page.getByText("74.4", { exact: false })).toHaveCount(0);
});

test("filter and geography changes clear segment and comparable evidence", async ({ page }) => {
  await openMarket(page);
  await loadOverview(page);
  await installSuccessfulSegmentRoutes(page);
  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-comparables-low_sample")).toBeVisible();

  await page.getByTestId("segment-area-preset").selectOption("40-60");
  await expect(page.getByTestId("market-segment-available")).toHaveCount(0);
  await expect(page.getByTestId("market-comparables-low_sample")).toHaveCount(0);
  await page.getByTestId("market-county-select").selectOption("桃園市");
  await expect(page.getByTestId("market-district-select")).toHaveValue("");
  await expect(page.getByTestId("market-segmentation-engine")).toHaveCount(0);
});

test("error and no-data responses never retain a prior comparable", async ({ page }) => {
  await openMarket(page);
  await loadOverview(page);
  let mode: "success" | "error" | "no_data" = "success";
  await page.route("**/market-insights/segments", (route) => {
    if (mode === "error") return fulfillJson(route, { detail: "unavailable" }, 503);
    if (mode === "no_data") return fulfillJson(route, segmentResult({ state: "no_data", data_status: "no_data", matching_transaction_count: 0, median_unit_price_per_ping: null }));
    return fulfillJson(route, segmentResult());
  });
  await page.route("**/market-insights/segment-comparables", (route) => fulfillJson(route, comparableResult()));
  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-comparables-low_sample")).toBeVisible();

  mode = "error";
  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-segment-unavailable")).toBeVisible();
  await expect(page.getByTestId("market-comparables-low_sample")).toHaveCount(0);

  mode = "no_data";
  await page.getByTestId("market-segment-submit").click();
  await expect(page.getByTestId("market-segment-no_data")).toBeVisible();
  await expect(page.getByTestId("market-comparables-no-data")).toBeVisible();
  await expect(page.getByTestId("market-comparables-low_sample")).toHaveCount(0);
});

test("all four locales translate critical filters and CTA labels", async ({ page }) => {
  await openMarket(page);
  await loadOverview(page);
  const localeSwitcher = page.getByTestId("locale-switcher");
  const expectations = [
    ["zh-TW", "市場區隔分析", "分析此市場區隔"],
    ["en", "Segment analysis", "Analyze this segment"],
    ["ja", "市場セグメント分析", "このセグメントを分析"],
    ["ko", "시장 세그먼트 분석", "이 세그먼트 분석"],
  ] as const;
  for (const [locale, heading, cta] of expectations) {
    await localeSwitcher.selectOption(locale);
    await expect(page.getByTestId("market-segmentation-engine")).toContainText(heading);
    await expect(page.getByTestId("market-segment-submit")).toHaveText(cta);
    await expect(page.getByTestId("segment-building-type")).toBeVisible();
    await expect(page.getByTestId("segment-area-preset")).toBeVisible();
    await expect(page.getByTestId("segment-age-band")).toBeVisible();
    await expect(page.getByTestId("segment-floor-position")).toBeVisible();
  }
});
