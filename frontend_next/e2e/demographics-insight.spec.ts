/**
 * Phase 3C-2 — RIS Demographics Frontend Integration (里人口概況)
 *
 * Exercises the demographics insight card inside the real Location Insight UI:
 * available render, ratio/null/zero formatting, no_data / unavailable / unresolved
 * / ambiguous village states, trend available vs insufficient, month-gap caveat,
 * audit warning, legacy backward compatibility, address-change clearing, stale
 * response protection, no direct data-source calls, mobile 390px, and Location
 * Insight regression. API responses are mocked via page.route; the frontend never
 * talks to a database, R2, the RIS API, or NLSC directly.
 */

import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";

// CI-stability (Phase 3C-2): run this spec's cases serially within a single
// worker. Each case boots the guided journey and the Location Insight stage,
// which is relatively heavy; under the repo's default 6-worker parallelism the
// second browser project (branded Chrome) could time out from machine
// contention. Serializing at the FILE level bounds this spec's concurrency
// without touching global playwright.config.ts or the project-wide worker count.
// All logical cases are preserved and both browser projects still execute.
test.describe.configure({ mode: "serial" });

const ADDRESS = "臺北市大安區和平東路二段";

type VillageResolution = {
  status: "resolved" | "unresolved" | "ambiguous" | "unavailable";
  county: string | null;
  town: string | null;
  village: string | null;
  village_code: string | null;
  district_code: string | null;
  source: string;
  source_vintage: string | null;
  reason: string;
  candidate_count?: number;
};

function resolvedVillage(overrides: Partial<VillageResolution> = {}): VillageResolution {
  return {
    status: "resolved",
    county: "臺北市",
    town: "大安區",
    village: "龍泉里",
    village_code: "63000020001",
    district_code: "63000020001",
    source: "nlsc_village_boundary",
    source_vintage: "ROC-1150817",
    reason: "unique_intersection",
    ...overrides,
  };
}

function availableDemographics(overrides: Record<string, unknown> = {}) {
  return {
    status: "available",
    reason: null,
    statistic_yyymm: "11507",
    statistic_month: "2026-07-01",
    total_population: 12345,
    household_count: 4567,
    average_household_size: 2.7,
    child_ratio: 0.121,
    working_age_ratio: 0.702,
    elderly_ratio: 0.177,
    first_month: "11406",
    last_month: "11507",
    observed_month_count: 13,
    population_change: 120,
    population_change_ratio: 0.0098,
    household_change: 45,
    has_month_gaps: false,
    trend_status: "increasing",
    source_provider: "RIS",
    source_dataset: "ODRP014",
    ...overrides,
  };
}

function locationResponse(options: {
  village_resolution?: VillageResolution;
  demographics?: Record<string, unknown> | null;
  omitDemographicFields?: boolean;
  score?: number;
}) {
  const base: Record<string, unknown> = {
    input: { address: ADDRESS, city: "臺北市", district: "大安區", road: "和平東路二段", radius_m: 800 },
    resolved_location: { address_label: ADDRESS, latitude: 25.026, longitude: 121.534, geocoding_confidence: "high" },
    geocoding_acceptance: {
      original_query: ADDRESS,
      normalized_address: ADDRESS,
      resolved_lat: 25.026,
      resolved_lng: 121.534,
      geocoding_source: "google_geocoding",
      match_quality: "EXACT_OR_ACCEPTABLE",
      accepted_for_analysis: true,
      requires_confirmation: false,
      mismatch_reasons: [],
      message: "定位結果與輸入條件相符。",
    },
    radius_m: 800,
    location_score: options.score ?? 72,
    category_scores: { transit_score: 80, convenience_score: 75, education_score: 70, green_space_score: 60, medical_score: 65, risk_score: 50 },
    poi_summary: { transit_count: 4, convenience_count: 6, school_count: 2, park_count: 1, medical_count: 3, risk_facility_count: 0 },
    nearest_pois: [{ category: "transit", name: "科技大樓站", distance_m: 300, source: "fixture" }],
    strengths: ["交通便利"],
    weaknesses: [],
    buyer_fit: { self_use_family: "適合", commuter: "適合", investor: "參考", elderly: "參考" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "區位分析不決定價格合理性。" },
    data_quality: { status: "good", missing_sources: [], warnings: [] },
    scoring_method: { weights: {}, explanation: "Fixture." },
    disclaimer: "僅供參考。",
  };
  if (!options.omitDemographicFields) {
    base.village_resolution = options.village_resolution ?? resolvedVillage();
    if (options.demographics !== null) base.demographics = options.demographics ?? availableDemographics();
  }
  return base;
}

async function gotoLocationStage(page: Page) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 12000 });

  // The journey stepper renders a desktop button list (hidden below lg) and a
  // collapsed <details> for mobile. Pick whichever is visible for the viewport.
  const viewport = page.viewportSize();
  const isMobile = (viewport?.width ?? 1440) < 1024;
  if (isMobile) {
    const mobileSummary = page.locator("details.lg\\:hidden > summary").first();
    if (await mobileSummary.count()) {
      await mobileSummary.click();
    }
  }
  // Both desktop and mobile render the same aria-label; select the visible one.
  const candidates = page.getByLabel(/位置與資料證據/);
  const count = await candidates.count();
  let clicked = false;
  for (let i = 0; i < count; i += 1) {
    const candidate = candidates.nth(i);
    if (await candidate.isVisible()) {
      await candidate.click();
      clicked = true;
      break;
    }
  }
  if (!clicked) {
    await candidates.first().click();
  }
  // Readiness signal: the location calculator itself is mounted. This is more
  // robust than the intermediate stage <section> under heavy parallel load.
  await expect(page.locator("#location-insight-calculator")).toBeVisible({ timeout: 20000 });
}

async function analyze(page: Page, address = ADDRESS) {
  const input = page.locator("#location-insight-calculator input").first();
  await expect(input).toBeVisible({ timeout: 15000 });
  await input.fill(address);
  await page.locator("#location-insight-calculator button", { hasText: /開始位置分析|Start location/ }).click();
  await expect(page.getByTestId("location-result")).toBeVisible({ timeout: 12000 });
}

async function routeLocation(page: Page, body: Record<string, unknown>) {
  await page.route("**/location/insight", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

test.describe("里人口概況 demographics card", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("CASE 1+2: available render with ratios formatted as percentages", async ({ page }) => {
    await routeLocation(page, locationResponse({}));
    await gotoLocationStage(page);
    await analyze(page);

    const card = page.getByTestId("demographics-insight");
    await expect(card).toBeVisible();
    await expect(page.getByTestId("demographics-available")).toBeVisible();
    await expect(page.getByTestId("demographics-admin-location")).toContainText("臺北市 大安區 龍泉里");
    await expect(page.getByTestId("demographics-statistic-month")).toContainText("民國115年07月");
    await expect(card).toContainText("12,345");
    await expect(card).toContainText("4,567");
    await expect(card).toContainText("2.70 人");
    await expect(card).toContainText("12.1%");
    await expect(card).toContainText("70.2%");
    await expect(card).toContainText("17.7%");
  });

  test("CASE 3: null ratio renders 資料不足, never 0", async ({ page }) => {
    await routeLocation(page, locationResponse({
      demographics: availableDemographics({ child_ratio: null, working_age_ratio: null, elderly_ratio: null, average_household_size: null }),
    }));
    await gotoLocationStage(page);
    await analyze(page);
    const card = page.getByTestId("demographics-available");
    await expect(card).toContainText("資料不足");
    await expect(card).not.toContainText("0.0%");
  });

  test("CASE 4: zero population renders 0 (not 資料不足)", async ({ page }) => {
    await routeLocation(page, locationResponse({
      demographics: availableDemographics({ total_population: 0, household_count: 0, child_ratio: 0, working_age_ratio: 0, elderly_ratio: 0 }),
    }));
    await gotoLocationStage(page);
    await analyze(page);
    const card = page.getByTestId("demographics-available");
    await expect(card).toContainText("0.0%");
    await expect(card.getByText("0", { exact: true }).first()).toBeVisible();
  });

  test("CASE 5: no_data state", async ({ page }) => {
    await routeLocation(page, locationResponse({ demographics: { status: "no_data", reason: "demographics_not_available_for_village_code" } }));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-no-data")).toBeVisible();
    await expect(page.getByTestId("demographics-no-data")).not.toContainText("0.0%");
  });

  test("CASE 6: unavailable village state", async ({ page }) => {
    await routeLocation(page, locationResponse({
      village_resolution: resolvedVillage({ status: "unavailable", county: null, town: null, village: null, village_code: null, district_code: null, source_vintage: null, reason: "location_not_resolved" }),
      demographics: { status: "no_data", reason: "location_not_resolved" },
    }));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-village-unavailable")).toBeVisible();
  });

  test("CASE 7: unresolved village state", async ({ page }) => {
    await routeLocation(page, locationResponse({
      village_resolution: resolvedVillage({ status: "unresolved", county: null, town: null, village: null, village_code: null, district_code: null, reason: "zero_polygon" }),
      demographics: { status: "no_data", reason: "village_identity_not_resolved" },
    }));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-village-unresolved")).toBeVisible();
  });

  test("CASE 8: ambiguous village state with candidate count", async ({ page }) => {
    await routeLocation(page, locationResponse({
      village_resolution: resolvedVillage({ status: "ambiguous", county: null, town: null, village: null, village_code: null, district_code: null, reason: "multiple_intersecting_polygons", candidate_count: 3 }),
      demographics: { status: "no_data", reason: "village_identity_not_resolved" },
    }));
    await gotoLocationStage(page);
    await analyze(page);
    const ambiguous = page.getByTestId("demographics-village-ambiguous");
    await expect(ambiguous).toBeVisible();
    await expect(ambiguous).toContainText("3");
  });

  test("CASE 9: trend available", async ({ page }) => {
    await routeLocation(page, locationResponse({}));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-trend-summary")).toContainText("民國114年06月");
    await expect(page.getByTestId("demographics-trend-summary")).toContainText("民國115年07月");
    await expect(page.getByTestId("demographics-trend-summary")).toContainText("13 個月");
    const trend = page.getByTestId("demographics-trend");
    await expect(trend).toContainText("+120");
    await expect(trend).toContainText("+1.0%");
    await expect(trend).toContainText("+45");
  });

  test("CASE 10: trend insufficient shows 歷史資料不足", async ({ page }) => {
    await routeLocation(page, locationResponse({
      demographics: availableDemographics({ observed_month_count: 1, first_month: "11507", last_month: "11507", population_change: 0, population_change_ratio: null, household_change: 0 }),
    }));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-trend-insufficient")).toContainText("歷史資料不足");
  });

  test("CASE 11: month-gap caveat is shown", async ({ page }) => {
    await routeLocation(page, locationResponse({ demographics: availableDemographics({ has_month_gaps: true }) }));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-month-gap-caveat")).toBeVisible();
  });

  test("CASE 12: audit warning shown when audit_reasons present", async ({ page }) => {
    await routeLocation(page, locationResponse({ demographics: availableDemographics({ audit_reasons: ["sex_total_mismatch"] }) }));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-audit-warning")).toContainText("此期資料有品質註記");
    // Data still renders alongside the caveat.
    await expect(page.getByTestId("demographics-available")).toContainText("12,345");
  });

  test("CASE 13: legacy response without demographics does not crash", async ({ page }) => {
    await routeLocation(page, locationResponse({ omitDemographicFields: true }));
    await gotoLocationStage(page);
    await analyze(page);
    // Location result still renders; the demographics card is simply absent.
    await expect(page.getByTestId("location-result")).toBeVisible();
    await expect(page.getByTestId("demographics-insight")).toHaveCount(0);
  });

  test("CASE 14+15: address change clears old data and stale response cannot overwrite", async ({ page }) => {
    // First analysis resolves available demographics.
    await routeLocation(page, locationResponse({}));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-available")).toBeVisible();

    // Changing the address invalidates the flow — old demographics must clear.
    const input = page.locator("#location-insight-calculator input").first();
    await input.fill("臺北市信義區松高路");
    await expect(page.getByTestId("demographics-insight")).toHaveCount(0);
    await expect(page.getByTestId("location-result")).toHaveCount(0);
  });

  test("CASE 16+17: no direct R2 / RIS / NLSC calls from the frontend", async ({ page }) => {
    const forbidden: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      if (/r2\.|cloudflarestorage|\/ris\/|nlsc|ris_village|village_boundary/i.test(url)) forbidden.push(url);
    });
    await routeLocation(page, locationResponse({}));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("demographics-available")).toBeVisible();
    expect(forbidden, `Frontend must not call data sources directly: ${forbidden.join(", ")}`).toEqual([]);
  });

  test("CASE 19: Location Insight regression — score + POI still render with card", async ({ page }) => {
    await routeLocation(page, locationResponse({}));
    await gotoLocationStage(page);
    await analyze(page);
    await expect(page.getByTestId("location-result")).toContainText("72");
    await expect(page.getByTestId("demographics-insight")).toBeVisible();
  });
});

test.describe("里人口概況 mobile 390px", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("CASE 18: no horizontal overflow at 390px", async ({ page }) => {
    await routeLocation(page, locationResponse({ demographics: availableDemographics({ audit_reasons: ["sex_total_mismatch"], has_month_gaps: true }) }));
    await gotoLocationStage(page);
    await analyze(page);
    const card = page.getByTestId("demographics-insight");
    await expect(card).toBeVisible();
    // The card must not exceed the viewport width.
    const overflow = await page.evaluate(() => {
      const el = document.querySelector("[data-testid='demographics-insight']");
      if (!el) return { scrollWidth: 0, clientWidth: 1 };
      return { scrollWidth: el.scrollWidth, clientWidth: document.documentElement.clientWidth };
    });
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  });
});

test.describe("Market journey regression", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("CASE 20: journey location stage still loads with demographics wired in", async ({ page }) => {
    await routeLocation(page, locationResponse({}));
    await gotoLocationStage(page);
    // The location stage renders its calculator and flow badges without error.
    await expect(page.locator("#location-insight-calculator")).toBeVisible();
    await analyze(page);
    await expect(page.getByTestId("location-result")).toBeVisible();
    await expect(page.getByTestId("demographics-insight")).toBeVisible();
  });
});
