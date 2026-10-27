import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { buildDemoCases } from "../lib/workspace/demo-cases";
import { DEMO_CASE_A_ID } from "../lib/workspace/demo-case-ids";
import { captureNearbyFacilities } from "../lib/workspace/nearby-facilities";
import { captureVillageDemographics } from "../lib/workspace/village-demographics";
import { autoBriefCopy } from "../lib/workspace/auto-brief-copy";
import { isNearbyRequest } from "./helpers/nearby-route";
import type { SavedCase } from "../lib/case-storage";

/**
 * Gate A1-1: one explicit "One-click analysis" walks Market → Location → Risk → Money → Brief.
 * Saved Nearby and demographics are reused, the location is never geocoded again, and opening the
 * Brief, Compare, Report, reloading or switching locale add zero acquisitions.
 */
const KEY = "proptech.savedCases.v1";
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const POINT = { latitude: 24.16525, longitude: 120.64555 };
const CHECKED_AT = "2026-10-20T03:00:00.000Z";

function v2Case(id = "case-a", patch: (row: SavedCase) => void = () => undefined): SavedCase {
  const row = e9Case(id);
  const origin = { lat: POINT.latitude, lng: POINT.longitude };
  row.data.nearbyFacilities = captureNearbyFacilities({ center: origin, radius_m: 800, source: "google_places", checked_at: CHECKED_AT,
    categories: ["transport", "shopping", "food", "school", "medical", "park"].map((category, index) => ({ category, source: "google_places",
      places: [{ place_id: `${category}-1`, name: `Fixture ${category}`, lat: origin.lat + 0.001 * (index + 1), lng: origin.lng, types: [category === "transport" ? "subway_station" : category], source: "google_places" }] })) }, origin);
  row.data.villageDemographics = captureVillageDemographics({ ...POINT, checked_at: CHECKED_AT,
    village_resolution: { status: "resolved", county: "臺中市", town: "西屯區", village: "潮洋里", village_code: "66000060020", district_code: "66000060", source: "nlsc_village_boundary", source_vintage: "ROC-1150817", reason: "unique_intersection" },
    demographics: { status: "no_data", reason: "not_available" } }, POINT);
  patch(row);
  return row;
}

function riskResult() {
  const source = (name: string, status = "available") => ({ name, agency: "經濟部水利署", source_url: "https://example.gov.tw/evidence", status, data_updated_at: "2026-06-30", data_vintage: "2026" });
  const hazards = {
    flood: { key: "flood", label: "淹水潛勢", status: "available", level: "unknown", matched: false, distance_m: null, value: null, explanation: "查詢完成且未比對到圖層。", source: source("淹水潛勢圖") },
    landslide: { key: "landslide", label: "大規模崩塌潛勢", status: "available", level: "unknown", matched: false, distance_m: null, value: null, explanation: "查詢完成且未比對到圖層。", source: source("崩塌潛勢圖") },
    debris_flow: { key: "debris_flow", label: "土石流潛勢溪流", status: "error", level: "unknown", matched: false, distance_m: null, value: null, explanation: "來源目前無法查詢。", source: source("土石流", "error") },
    liquefaction: { key: "liquefaction", label: "土壤液化潛勢", status: "available", level: "unknown", matched: false, distance_m: null, value: null, explanation: "查詢完成且未比對到圖層。", source: source("液化") },
    geological_sensitivity: { key: "geological_sensitivity", label: "地質敏感區", status: "available", level: "unknown", matched: false, distance_m: null, value: { dataset_version: "2024-06-27", matched_count: 0, matches: [] }, explanation: "未交集。", source: source("地質敏感區") },
    active_fault: { key: "active_fault", label: "活動斷層", status: "unavailable", level: "unknown", matched: false, distance_m: null, value: null, explanation: "目前未設定官方圖資查詢。", source: source("活動斷層", "unavailable") },
  };
  return {
    input: { ...POINT, radius_m: 500 }, resolved_location: { ...POINT, geocoding_source: "provided_coordinates" },
    overall: { level: "unknown", label: "", summary: "", confidence: "low" },
    terrain: { status: "available", slope_value: 3.2, slope_class: "平緩", explanation: "坡度圖資僅供參考。", source: source("坡度") },
    hazards, risk_factors: [], missing_sources: [], recommended_checks: [], map_layers: [],
    source_transparency: { notice: "逐項判讀。", layers: [] }, official_data_sources: [],
    data_quality: { status: "limited", warnings: [], checked_at: CHECKED_AT }, disclaimer: "證據導向查證。",
  };
}

type Calls = { market: number; risk: number; resolve: number; nearby: number; demographics: number };
type Hold = { market?: Promise<void>; risk?: Promise<void> };

async function prepare(page: Page, rows: SavedCase[], locale: (typeof LOCALES)[number] = "zh-TW", hold: Hold = {}) {
  await page.addInitScript(({ key, rows, locale }) => {
    if (sessionStorage.getItem("auto-brief-seeded")) return;
    sessionStorage.setItem("auto-brief-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
  }, { key: KEY, rows, locale });
  const calls: Calls = { market: 0, risk: 0, resolve: 0, nearby: 0, demographics: 0 };
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.endsWith("/market-insights/query")) calls.market++;
    else if (url.pathname.endsWith("/terrain-risk/analyze")) calls.risk++;
    else if (url.pathname.endsWith("/location/resolve")) calls.resolve++;
    else if (url.pathname.endsWith("/demographics/location")) calls.demographics++;
    else if (isNearbyRequest(url)) calls.nearby++;
  });
  await page.route((url) => /tile\.openstreetmap\.org|basemaps\.cartocdn\.com|arcgisonline\.com/.test(url.hostname), (route) => route.fulfill({ status: 204, body: "" }));
  await page.route("**/market-insights/query", async (route) => {
    await hold.market;
    await route.fulfill({ json: e9Case().data.marketInsight }).catch(() => {});
  });
  await page.route("**/terrain-risk/analyze", async (route) => {
    await hold.risk;
    await route.fulfill({ json: riskResult() }).catch(() => {});
  });
  return calls;
}

const panel = (page: Page) => page.getByTestId("auto-brief-panel");
const step = (page: Page, id: string) => page.getByTestId(`auto-brief-step-${id}`);

test("confirmed case: one click runs Market and Risk once, reuses Location V2 evidence and never geocodes", async ({ page }) => {
  const calls = await prepare(page, [v2Case(), v2Case("case-b")]);
  await page.goto("/cases/case-a/location");
  await expect(panel(page)).toBeVisible();
  // Opening the workspace acquires nothing.
  expect(calls).toEqual({ market: 0, risk: 0, resolve: 0, nearby: 0, demographics: 0 });
  await page.getByTestId("auto-brief-start").click();
  await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
  expect(calls).toEqual({ market: 1, risk: 1, resolve: 0, nearby: 0, demographics: 0 });
  const c = autoBriefCopy["zh-TW"];
  await expect(page.getByTestId("auto-brief-status")).toContainText(c.run_completed_with_gaps);
  await expect(step(page, "market")).toHaveAttribute("data-status", "available");
  await expect(step(page, "location")).toHaveAttribute("data-status", "partial");
  await expect(step(page, "location")).toContainText(c.reused);
  await expect(step(page, "risk")).toHaveAttribute("data-status", "partial");
  await expect(step(page, "money")).toHaveAttribute("data-status", "partial");
  await expect(step(page, "brief")).toHaveAttribute("data-status", "available");
  await expect(page.getByTestId("auto-brief-gaps")).toBeVisible();
  // Raw ids and reason codes never render.
  expect(await panel(page).innerText()).not.toMatch(/completed_with_gaps|needs_input|no_data|provider_unavailable|partial_evidence|reused_saved|money_partial/);

  // View Brief, reopen, Compare, Report and reload add zero acquisitions.
  await page.getByTestId("auto-brief-view-brief").click();
  await expect(page.getByTestId("commercial-overview-workspace")).toBeVisible();
  await page.goto("/cases/case-a/location");
  await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
  await page.reload();
  await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeVisible();
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-evidence")).toBeVisible();
  expect(calls).toEqual({ market: 1, risk: 1, resolve: 0, nearby: 0, demographics: 0 });
});

test("unconfirmed location blocks one-click analysis with a localized action and no acquisition", async ({ page }) => {
  const calls = await prepare(page, [v2Case("case-a", (row) => { delete row.data.propertyIdentityAnchor; })], "en");
  await page.goto("/cases/case-a/location");
  await expect(page.getByTestId("auto-brief-needs-location")).toContainText(autoBriefCopy.en.run_needs_location);
  await expect(page.getByTestId("auto-brief-start")).toBeDisabled();
  await expect(page.getByTestId("auto-brief-manual")).toHaveText(autoBriefCopy.en.manual);
  expect(calls).toEqual({ market: 0, risk: 0, resolve: 0, nearby: 0, demographics: 0 });
});

test("missing Money inputs end as Needs input while the Brief is still built", async ({ page }) => {
  const calls = await prepare(page, [v2Case("case-a", (row) => { delete row.data.financeEvidence; })], "en");
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
  await expect(step(page, "money")).toHaveAttribute("data-status", "needs_input");
  await expect(step(page, "money")).toContainText(autoBriefCopy.en.status_needs_input);
  await expect(step(page, "brief")).toHaveAttribute("data-status", "available");
  await expect(page.getByTestId("auto-brief-go-money")).toHaveAttribute("href", "/cases/case-a/finance");
  expect(calls.market + calls.risk).toBe(2);
});

test("keyboard cancel during Market stops later steps and ignores the late response", async ({ page }) => {
  let release!: () => void;
  const market = new Promise<void>((done) => { release = done; });
  const calls = await prepare(page, [v2Case()], "en", { market });
  await page.goto("/cases/case-a/location");
  const start = page.getByTestId("auto-brief-start");
  await start.focus();
  await page.keyboard.press("Enter");
  await expect(step(page, "market")).toHaveAttribute("data-status", "running");
  const cancel = page.getByTestId("auto-brief-cancel");
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(panel(page)).toHaveAttribute("data-run-status", "cancelled");
  release();
  await page.waitForTimeout(300);
  await expect(panel(page)).toHaveAttribute("data-run-status", "cancelled");
  await expect(step(page, "risk")).toHaveAttribute("data-status", "skipped");
  expect(calls.risk).toBe(0);
  // Continue and Restart are explicit, keyboard-reachable decisions.
  await expect(page.getByTestId("auto-brief-continue")).toBeVisible();
  await page.getByTestId("auto-brief-restart").focus();
  await page.keyboard.press("Enter");
  await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
  expect(calls).toEqual({ market: 2, risk: 1, resolve: 0, nearby: 0, demographics: 0 });
});

test("reload during Risk shows interrupted and never resumes provider calls by itself", async ({ page }) => {
  const risk = new Promise<void>(() => undefined);
  const calls = await prepare(page, [v2Case()], "zh-TW", { risk });
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await expect(step(page, "risk")).toHaveAttribute("data-status", "running");
  await page.reload();
  await expect(panel(page)).toHaveAttribute("data-run-status", "interrupted");
  await expect(page.getByTestId("auto-brief-status")).toContainText(autoBriefCopy["zh-TW"].run_interrupted);
  await expect(step(page, "market")).toHaveAttribute("data-status", "available");
  await expect(step(page, "risk")).toHaveAttribute("data-status", "pending");
  await page.waitForTimeout(300);
  expect(calls).toEqual({ market: 1, risk: 1, resolve: 0, nearby: 0, demographics: 0 });
  await expect(page.getByTestId("auto-brief-continue")).toBeVisible();
});

test("demo fixture runs the same steps with zero provider calls", async ({ page }) => {
  const calls = await prepare(page, buildDemoCases("en"), "en");
  await page.goto(`/cases/${DEMO_CASE_A_ID}/location`);
  await expect(page.getByTestId("auto-brief-demo-note")).toHaveText(autoBriefCopy.en.demoNote);
  await page.getByTestId("auto-brief-start").click();
  await expect(panel(page)).toHaveAttribute("data-run-status", /completed/);
  for (const id of ["market", "location", "risk", "money", "brief"]) await expect(step(page, id)).not.toHaveAttribute("data-status", /pending|running/);
  expect(calls).toEqual({ market: 0, risk: 0, resolve: 0, nearby: 0, demographics: 0 });
});

for (const locale of LOCALES) {
  test(`${locale}: localized progress at 390 / 430 / 1024 / 1440 without horizontal overflow; locale switch acquires nothing`, async ({ page }) => {
    const calls = await prepare(page, [v2Case()], locale);
    const c = autoBriefCopy[locale];
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/cases/case-a/location");
    await expect(page.getByTestId("auto-brief-start")).toHaveText(c.start);
    await page.getByTestId("auto-brief-start").click();
    await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
    await expect(page.getByTestId("auto-brief-status")).toContainText(c.run_completed_with_gaps);
    for (const id of ["market", "location", "risk", "money", "brief"] as const) await expect(step(page, id)).toContainText(c[`step_${id}`]);
    await expect(page.getByTestId("auto-brief-view-brief")).toHaveText(c.viewBrief);
    for (const width of [390, 430, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(panel(page)).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${locale} ${width}`).toBeLessThanOrEqual(0);
      const box = await panel(page).boundingBox();
      expect(box!.x + box!.width, `${locale} ${width} panel`).toBeLessThanOrEqual(width + 0.5);
    }
    const before = { ...calls };
    const other = locale === "en" ? "ko" : "en";
    await page.getByTestId("locale-switcher").selectOption(other).catch(async () => {
      await page.evaluate((next) => localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale: next })), other);
      await page.reload();
    });
    await expect(page.getByTestId("auto-brief-status")).toContainText(autoBriefCopy[other].run_completed_with_gaps);
    expect(calls).toEqual(before);
    expect(calls).toEqual({ market: 1, risk: 1, resolve: 0, nearby: 0, demographics: 0 });
  });
}
