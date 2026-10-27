import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { captureNearbyFacilities } from "../lib/workspace/nearby-facilities";
import { captureVillageDemographics } from "../lib/workspace/village-demographics";
import { buildAddressDraftCase } from "../lib/workspace/case-draft";
import { locationViewCopy } from "../lib/workspace/location-view-copy";
import { commuteRouteCopy } from "../lib/commute-route-copy";
import { nearbyFacilitiesCopy } from "../lib/workspace/nearby-facilities-copy";
import { villageDemographicsCopy } from "../lib/workspace/village-demographics-copy";
import { locationConfirmationCopy } from "../lib/workspace/location-confirmation-copy";
import { isNearbyRequest } from "./helpers/nearby-route";
import { isProviderRequest } from "./helpers/provider-request";

/**
 * Gate L1-4: the Location workspace renders product copy in the active locale only. Saved addresses,
 * village and place names, destinations and provider/source proper names are data and stay as stored.
 * Rendering and switching locale never geocode, acquire demographics or query Nearby.
 */
const KEY = "proptech.savedCases.v1";
const CHECKED_AT = "2026-09-27T08:00:00.000Z";
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
type Locale = typeof LOCALES[number];
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const POINT = { latitude: 25.0375, longitude: 121.5637 };

/** Data rendered as stored: addresses, administrative and place names, destinations, source proper names. */
const DATA = ["臺北市信義區市府路1號", "臺北市", "信義區", "西村里", "台北車站", "市政府站", "戶政司", "戸政司", "Taipei City Hall MRT"];
const HAN = /[㐀-鿿]/;
const KANA = /[぀-ヿ]/;
const HANGUL = /[가-힯]/;
/** Traditional Chinese forms that modern Japanese writes differently; any of them in ja means leaked zh-TW copy. */
const ZH_ONLY = /[區與證據這們說查詢邊擇條圖鄰關價號臺灣從將麼嗎]/;

function anchor() {
  return {
    version: 1, scope: "journey_browser_anchor", journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
    address_input: "臺北市信義區市府路1號", normalized_address: "臺北市信義區市府路1號", coordinates: POINT,
    administrative_location: { city: "臺北市", district: "信義區", village: "西村里", village_code: "63000020-014" }, location_status: "candidate",
    parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
    building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
    confidence: { level: "high", domain: "address_spatial_correlation", basis: ["normalized_address", "trusted_geocoding_coordinates", "resolved_village"], limitations: [] },
    evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding", checked_at: CHECKED_AT }, { source_id: "nlsc_village_boundary", kind: "administrative_boundary", checked_at: CHECKED_AT }], checked_at: CHECKED_AT, limitations: ["journey_browser_correlation_only"] },
    revalidation: { status: "current", conflicts: [] },
  };
}

/** An older saved case: legacy insight summary, risk-facility evidence and zh-only data-quality warnings, no Nearby details. */
function legacyCase(id = "legacy-case") {
  return {
    id, title: "市府路案件", createdAt: CHECKED_AT, updatedAt: CHECKED_AT, version: 1, workflowMode: "buying_wizard", activeWizardStep: "location", progress: 60,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號" },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      propertyIdentityAnchor: anchor(),
      journeyContext: { version: 1, propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected" }, priceBasis: "asking" },
      locationInsight: {
        input: {}, resolved_location: { address_label: "臺北市信義區市府路1號", ...POINT, geocoding_confidence: "high" },
        village_resolution: { status: "resolved", county: "臺北市", town: "信義區", village: "西村里", village_code: "63000020-014", district_code: "63000020", source: "nlsc_village_boundary", source_vintage: "2026-08", reason: "resolved" },
        demographics: { status: "no_data", reason: "not_available" }, geocoding_acceptance: null, radius_m: 800, location_score: 91,
        category_scores: { transit_score: 80, convenience_score: 70, education_score: 60, green_space_score: 50, medical_score: 40, risk_score: 30 },
        poi_summary: { transit_count: 4, convenience_count: 8, school_count: 3, park_count: 2, medical_count: 4, risk_facility_count: 1 },
        nearest_pois: [], strengths: [], weaknesses: [],
        buyer_fit: { self_use_family: "", commuter: "", investor: "", elderly: "" }, valuation_context: { supports_price_reasonableness: "unknown", explanation: "" },
        data_quality: { status: "limited", missing_sources: [], warnings: ["部分地點明細未隨案件保存"] }, scoring_method: { weights: {}, explanation: "" }, disclaimer: "僅供區位參考",
        risk_facility_evidence: { status: "unavailable", count: null, source: null, checked_at: null, reason: "risk_facilities_source_unavailable", limitation: "未知涵蓋不代表零處設施或安全。" },
      },
      commuteRoute: { status: "resolved", source: "google_routes", mode: "transit", duration_min: 23, duration_seconds: 1380, distance_m: 8100, partial: false, fallback: false, reason_code: "success", checked_at: CHECKED_AT, origin: POINT, destination: { address: "台北車站" } },
      commuteTransit: { status: "unavailable", source: "none", station_name: null, line_ids: [], distance_meters: null, source_updated_at: null, snapshot_generated_at: CHECKED_AT, message: "unavailable" },
    },
  };
}

/** A Location V2 case: saved Nearby details and village demographics bound to the confirmed coordinates. */
function v2Case(id = "v2-case") {
  const row = legacyCase(id);
  const origin = { lat: POINT.latitude, lng: POINT.longitude };
  const nearby = captureNearbyFacilities({ center: origin, radius_m: 800, source: "google_places", checked_at: CHECKED_AT, categories: [
    { category: "transport", source: "google_places", places: [{ place_id: "mrt", name: "Taipei City Hall MRT", lat: origin.lat + 0.001, lng: origin.lng, types: ["subway_station", "transit_station"], source: "google_places" }] },
    { category: "park", source: "google_places", places: [{ place_id: "park", name: "Zhongshan Park", lat: origin.lat, lng: origin.lng + 0.001, types: ["park"], source: "google_places" }] },
  ] }, origin);
  const demographics = captureVillageDemographics({ ...POINT, checked_at: "2026-10-20T08:00:00+00:00",
    village_resolution: { status: "resolved", county: "臺北市", town: "信義區", village: "西村里", village_code: "63000020032", district_code: "63000020032", source: "nlsc_village_boundary", source_vintage: "ROC-1150817", reason: "unique_intersection" },
    demographics: { status: "available", reason: null, statistic_yyymm: "11508", statistic_month: "2026-08-01", total_population: 12345, household_count: 4567, average_household_size: 2.7, child_ratio: 0.121, working_age_ratio: 0.702, elderly_ratio: 0.177, first_month: "11408", last_month: "11508", observed_month_count: 13, population_change: 120, population_change_ratio: 0.0098, household_change: 45, has_month_gaps: true, trend_status: "increasing", source_provider: "RIS", source_dataset: "ODRP014" },
  }, POINT);
  return { ...row, data: { ...row.data, nearbyFacilities: nearby, villageDemographics: demographics } };
}

type Calls = { resolve: number; demographics: number; nearby: number; provider: string[] };

async function prepare(page: Page, rows: unknown[]) {
  await page.addInitScript(({ key, rows }) => {
    if (sessionStorage.getItem("location-four-locale-seeded")) return;
    sessionStorage.setItem("location-four-locale-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, rows });
  const calls: Calls = { resolve: 0, demographics: 0, nearby: 0, provider: [] };
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (BASEMAP.test(url.hostname)) return;
    if (url.pathname.endsWith("/location/resolve")) calls.resolve++;
    else if (url.pathname.endsWith("/demographics/location")) calls.demographics++;
    else if (isNearbyRequest(url)) calls.nearby++;
    else if (isProviderRequest(request, url.hostname === "127.0.0.1" ? url.origin : "http://127.0.0.1")) calls.provider.push(url.pathname);
  });
  await page.route((url) => BASEMAP.test(url.hostname), (route) => route.fulfill({ contentType: "image/png", body: PNG }));
  return calls;
}

async function openInLocale(page: Page, locale: Locale, id: string) {
  await page.goto("/");
  await page.getByTestId("locale-switcher").selectOption(locale);
  await page.goto(`/cases/${id}/location`);
  const view = page.getByTestId("commercial-location-workspace");
  await expect(view.getByRole("heading", { level: 1 })).toHaveText(locationViewCopy[locale].title);
  // Open the source details so their labels are part of the audited text.
  await view.getByText(locationViewCopy[locale].sourcesTitle, { exact: true }).click();
  return view;
}

/** Product copy in the active locale only: data strings are removed first, then each locale's script rules apply. */
async function expectLocaleOnly(view: import("@playwright/test").Locator, locale: Locale) {
  let text = await view.innerText();
  for (const value of DATA) text = text.replaceAll(value, "");
  if (locale === "en") expect(text.match(/[぀-ヿ㐀-鿿가-힯]+/g) ?? []).toEqual([]);
  if (locale === "ko") expect(text.match(/[぀-ヿ㐀-鿿]+/g) ?? []).toEqual([]);
  if (locale === "ja") {
    expect(text.match(new RegExp(ZH_ONLY.source, "g")) ?? []).toEqual([]);
    expect(HANGUL.test(text)).toBe(false);
  }
  if (locale === "zh-TW") {
    expect(text).not.toContain("・");
    expect(KANA.test(text) || HANGUL.test(text)).toBe(false);
  }
  if (locale === "en" || locale === "ko") for (const value of Object.values(locationViewCopy["zh-TW"])) if (HAN.test(value) && value.length > 3) expect(text).not.toContain(value);
  // Raw provider types, internal reason codes and identifiers never render.
  expect(text).not.toMatch(/subway_station|transit_station|google_places|google_routes|risk_facilities_|reason_code|63000020|ODRP014|VILLCODE/);
}

for (const locale of LOCALES) for (const width of [390, 430, 1024, 1440]) {
  test(`saved Location V2 case renders only ${locale} product copy at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const calls = await prepare(page, [v2Case()]);
    const view = await openInLocale(page, locale, "v2-case");
    const nearby = page.getByTestId("nearby-facilities");
    await expect(page.getByTestId("nearby-legend")).toHaveAttribute("aria-label", nearbyFacilitiesCopy[locale].legend);
    await expect(page.getByTestId("nearby-filter")).toHaveAttribute("aria-label", nearbyFacilitiesCopy[locale].filter);
    await expect(page.getByTestId("nearby-filter")).toContainText(nearbyFacilitiesCopy[locale].filterAll);
    await expect(nearby).toContainText(nearbyFacilitiesCopy[locale].kindRail);
    await expect(nearby).toContainText(nearbyFacilitiesCopy[locale].parks);
    await expect(page.getByTestId("demographics-available")).toContainText(villageDemographicsCopy[locale].population);
    await expect(page.getByTestId("demographics-available")).toContainText(villageDemographicsCopy[locale].monthGap);
    await expect(page.getByTestId("commute-route-card")).toContainText(commuteRouteCopy[locale].title);
    await expect(page.getByTestId("commute-route-card")).toContainText(commuteRouteCopy[locale].disclaimer);
    await expect(view).toContainText(locationViewCopy[locale].limitsTitle);
    await expect(view).toContainText(locationViewCopy[locale].next1);
    await expect(view).toContainText(locationViewCopy[locale].sourceGoogle);
    await expectLocaleOnly(view, locale);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.waitForLoadState("networkidle");
    expect(calls).toEqual({ resolve: 0, demographics: 0, nearby: 0, provider: [] });
  });
}

for (const locale of LOCALES) for (const width of [390, 1440]) {
  test(`legacy saved Location sections localize in ${locale} at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const calls = await prepare(page, [legacyCase()]);
    const view = await openInLocale(page, locale, "legacy-case");
    const copy = locationViewCopy[locale];
    await expect(view).toContainText(copy.legacyTitle);
    await expect(view).toContainText(copy.poiConvenience);
    await expect(page.getByTestId("risk-facility-source")).toContainText(copy.riskTitle);
    await expect(page.getByTestId("risk-facility-source")).toContainText(copy.riskUnavailable);
    await expect(page.getByTestId("risk-facility-source")).toContainText(copy.riskLimitation);
    await expect(page.getByTestId("risk-facility-source")).toContainText(copy.riskSourceMissing);
    // The saved route is summarized with localized mode, distance and duration.
    await expect(view).toContainText(copy.selectedRoute.split("{{")[0].trim());
    await expect(view).toContainText(copy.routeOnlyTransitUnavailable);
    // zh-only saved warnings stay verbatim in zh-TW and become a localized count elsewhere.
    if (locale === "zh-TW") await expect(view).toContainText("部分地點明細未隨案件保存");
    else await expect(view).toContainText(copy.savedWarnings.replace("{{count}}", "1"));
    await expectLocaleOnly(view, locale);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.waitForLoadState("networkidle");
    expect(calls).toEqual({ resolve: 0, demographics: 0, nearby: 0, provider: [] });
  });
}

test("switching through all four locales on Location never geocodes, acquires demographics or queries Nearby", async ({ page }) => {
  const calls = await prepare(page, [v2Case(), legacyCase()]);
  await page.goto("/cases/v2-case/location");
  await expect(page.getByTestId("demographics-available")).toBeVisible();
  for (const locale of [...LOCALES, "zh-TW"] as const) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByTestId("commercial-location-workspace").getByRole("heading", { level: 1 })).toHaveText(locationViewCopy[locale].title);
    await expect(page.getByTestId("nearby-legend")).toHaveAttribute("aria-label", nearbyFacilitiesCopy[locale].legend);
  }
  await page.goto("/cases/legacy-case/location");
  for (const locale of LOCALES) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByTestId("risk-facility-source")).toContainText(locationViewCopy[locale].riskTitle);
  }
  await page.waitForLoadState("networkidle");
  expect(calls).toEqual({ resolve: 0, demographics: 0, nearby: 0, provider: [] });
});

for (const locale of LOCALES) test(`administrative mismatch and candidate copy is localized in ${locale}`, async ({ page }) => {
  const calls = await prepare(page, []);
  const blocked = { status: "unresolved", source: "none", formatted_address: null, latitude: null, longitude: null, confidence: "unknown", message: "x", county: null, district: null, postal_code: null, place_id: null, resolution_reason: "administrative_mismatch",
    candidates: [{ source: "google", formatted_address: "238台灣新北市樹林區金寮里中正路191號", latitude: 24.99, longitude: 121.42, county: "新北市", district: "樹林區", postal_code: "238", place_id: "wrong", admin_check: "district_mismatch", confirmable: false, block_reason: "administrative_mismatch" }] };
  await page.route("**/location/resolve", (route) => route.fulfill({ json: blocked }));
  await page.goto("/");
  await page.getByTestId("locale-switcher").selectOption(locale);
  const draft = buildAddressDraftCase("新北市新莊區中正路191號", { id: "mismatch-draft", now: "2026-10-26T08:00:00Z" })!;
  await page.evaluate(({ key, draft }) => localStorage.setItem(key, JSON.stringify([draft])), { key: KEY, draft });
  await page.goto(`/cases/${draft.id}/location`);
  await page.getByTestId("location-find").click();
  const rejected = page.getByTestId("location-rejected-option");
  await expect(rejected).toContainText(locationConfirmationCopy[locale].badge_administrative_mismatch);
  await expect(page.getByTestId("location-confirm")).toHaveCount(0);
  await expect(page.getByTestId("location-confirmation").getByRole("button", { name: locationConfirmationCopy[locale].reject, exact: true })).toBeVisible();
  if (locale === "zh-TW") await expect(rejected).not.toContainText("・");
  await page.waitForLoadState("networkidle");
  expect(calls).toEqual({ resolve: 1, demographics: 0, nearby: 0, provider: [] });
});
