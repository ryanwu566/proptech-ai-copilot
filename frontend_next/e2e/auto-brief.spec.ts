import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { buildDemoCases } from "../lib/workspace/demo-cases";
import { DEMO_CASE_A_ID } from "../lib/workspace/demo-case-ids";
import { captureNearbyFacilities } from "../lib/workspace/nearby-facilities";
import { captureVillageDemographics } from "../lib/workspace/village-demographics";
import { autoBriefCopy } from "../lib/workspace/auto-brief-copy";
import { plotNearby } from "../lib/workspace/auto-brief-presentation";
import { isNearbyRequest } from "./helpers/nearby-route";
import type { SavedCase } from "../lib/case-storage";

/**
 * Gates A1-1 / A1-2: one explicit "One-click analysis" walks Market → Location → Risk → Money → Brief,
 * and the cinematic stage only visualises that real run. Saved Nearby and demographics are reused,
 * the location is never geocoded again, and the presentation (scenes, pause, skip, reduced motion,
 * reopening, Brief, Compare, Report, locale) adds zero acquisitions.
 */
const KEY = "proptech.savedCases.v1";
const RUNS_KEY = "proptech.autoBrief.v1";
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const POINT = { latitude: 24.16525, longitude: 120.64555 };
const ANCHOR_ID = "journey-browser-11111111-2222-4333-8444-555555555555";
const CHECKED_AT = "2026-10-20T03:00:00.000Z";
const STEPS = ["market", "location", "risk", "money", "brief"] as const;

const AVAILABLE_DEMOGRAPHICS = { status: "available", reason: null, statistic_yyymm: "11508", statistic_month: "2026-08-01", total_population: 12345, household_count: 4567, average_household_size: 2.7,
  child_ratio: 0.121, working_age_ratio: 0.702, elderly_ratio: 0.177, first_month: "11408", last_month: "11508", observed_month_count: 13, population_change: 120, population_change_ratio: 0.0098,
  household_change: 45, has_month_gaps: false, trend_status: "increasing", source_provider: "RIS", source_dataset: "ODRP014" };

function v2Case(id = "case-a", patch: (row: SavedCase) => void = () => undefined, demographics: "no_data" | "available" = "no_data"): SavedCase {
  const row = e9Case(id);
  const origin = { lat: POINT.latitude, lng: POINT.longitude };
  row.data.nearbyFacilities = captureNearbyFacilities({ center: origin, radius_m: 800, source: "google_places", checked_at: CHECKED_AT,
    categories: ["transport", "shopping", "food", "school", "medical", "park"].map((category, index) => ({ category, source: "google_places",
      places: [{ place_id: `${category}-1`, name: `Fixture ${category}`, lat: origin.lat + 0.001 * (index + 1), lng: origin.lng, types: [category === "transport" ? "subway_station" : category], source: "google_places" }] })) }, origin);
  row.data.villageDemographics = captureVillageDemographics({ ...POINT, checked_at: CHECKED_AT,
    village_resolution: { status: "resolved", county: "臺中市", town: "西屯區", village: "潮洋里", village_code: "66000060020", district_code: "66000060", source: "nlsc_village_boundary", source_vintage: "ROC-1150817", reason: "unique_intersection" },
    demographics: demographics === "available" ? AVAILABLE_DEMOGRAPHICS : { status: "no_data", reason: "not_available" } }, POINT);
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
type Options = { market?: Promise<void>; risk?: Promise<void>; marketBody?: unknown; riskStatus?: number; runs?: unknown; reducedMotion?: boolean };
const ONCE = { market: 1, risk: 1, resolve: 0, nearby: 0, demographics: 0 };
const NONE = { market: 0, risk: 0, resolve: 0, nearby: 0, demographics: 0 };

async function prepare(page: Page, rows: SavedCase[], locale: (typeof LOCALES)[number] = "zh-TW", options: Options = {}) {
  if (options.reducedMotion) await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(({ key, rows, locale, runsKey, runs }) => {
    if (sessionStorage.getItem("auto-brief-seeded")) return;
    sessionStorage.setItem("auto-brief-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    if (runs) localStorage.setItem(runsKey, JSON.stringify(runs));
  }, { key: KEY, rows, locale, runsKey: RUNS_KEY, runs: options.runs ?? null });
  const calls: Calls = { ...NONE };
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
    await options.market;
    await route.fulfill({ json: options.marketBody ?? e9Case().data.marketInsight }).catch(() => {});
  });
  await page.route("**/terrain-risk/analyze", async (route) => {
    await options.risk;
    await (options.riskStatus ? route.fulfill({ status: options.riskStatus, json: { detail: "unavailable" } }) : route.fulfill({ json: riskResult() })).catch(() => {});
  });
  return calls;
}

const panel = (page: Page) => page.getByTestId("auto-brief-panel");
const stage = (page: Page) => page.getByTestId("auto-brief-stage");
const step = (page: Page, id: string) => page.getByTestId(`auto-brief-step-${id}`);
const finished = async (page: Page, status = "completed_with_gaps") => {
  await expect(panel(page)).toHaveAttribute("data-run-status", status);
  await expect(page.getByTestId("auto-brief-completion")).toBeVisible({ timeout: 10_000 });
};
const review = async (page: Page, id: string) => {
  await page.getByTestId(`auto-brief-review-${id}`).click();
  await expect(stage(page)).toHaveAttribute("data-scene", id === "brief" ? "converge" : id);
};

test("confirmed case: the cinematic run follows real state, reuses Location V2 evidence and never geocodes", async ({ page }) => {
  const calls = await prepare(page, [v2Case("case-a", () => undefined, "available"), v2Case("case-b")]);
  await page.goto("/cases/case-a/location");
  await expect(panel(page)).toBeVisible();
  expect(calls).toEqual(NONE);
  const c = autoBriefCopy["zh-TW"];
  // Manual exploration is offered beside the one-click path, not as a fallback.
  await expect(page.getByTestId("auto-brief-manual")).toHaveText(c.manual);
  await page.getByTestId("auto-brief-start").click();
  await expect(stage(page)).toBeVisible();
  await finished(page);
  expect(calls).toEqual(ONCE);
  await expect(page.getByTestId("auto-brief-status")).toContainText(c.run_completed_with_gaps);
  await expect(page.getByTestId("auto-brief-rail-lockin")).toHaveAttribute("data-status", "available");
  await expect(step(page, "market")).toHaveAttribute("data-status", "available");
  // Nearby and available demographics were both saved, so Location is reused in full.
  await expect(step(page, "location")).toHaveAttribute("data-status", "available");
  await expect(step(page, "location")).toContainText(c.reused);
  await expect(step(page, "risk")).toHaveAttribute("data-status", "partial");
  await expect(step(page, "money")).toHaveAttribute("data-status", "partial");
  await expect(step(page, "brief")).toHaveAttribute("data-status", "available");
  await expect(page.getByTestId("auto-brief-completion")).toHaveAttribute("data-ending", "completed_with_gaps");
  await expect(page.getByTestId("auto-brief-gaps")).toBeVisible();

  // Scene 0: the confirmed identity, never a new lookup.
  await review(page, "lockin");
  await expect(page.getByTestId("auto-brief-scene-lockin")).toContainText("臺中市西屯區臺灣大道三段100號");
  await expect(page.getByTestId("auto-brief-scene-lockin")).toContainText("潮洋里");
  // Scene 1: Market shows the state the run recorded.
  await review(page, "market");
  await expect(page.getByTestId("auto-brief-market-state")).toHaveText(c.market_available);
  await expect(page.getByTestId("auto-brief-scene-market")).toContainText("內政部不動產實價登錄");
  // Scene 2: saved Nearby categories and village demographics, drawn from evidence only.
  await review(page, "location");
  const expected = plotNearby(v2Case("case-a").data.nearbyFacilities).groups.map((row) => row.group);
  await expect(page.getByTestId("auto-brief-poi-legend").locator("li")).toHaveCount(expected.length);
  expect(await page.getByTestId("auto-brief-poi-legend").locator("li").evaluateAll((items) => items.map((item) => item.getAttribute("data-group")))).toEqual(expected);
  await expect(page.getByTestId("auto-brief-demographics")).toContainText("12,345");
  // Scene 3: partial Risk stays partial; unavailable layers are listed, never cleared.
  await review(page, "risk");
  await expect(page.getByTestId("auto-brief-scene-risk")).toContainText(c.status_partial);
  await expect(page.getByTestId("auto-brief-risk-layers").locator('[data-layer="active_fault"]')).toHaveAttribute("data-usability", /unavailable|unverified|unsupported|limited/);
  await expect(page.getByTestId("auto-brief-scene-risk")).toContainText(c.riskNote);
  await expect(page.getByTestId("auto-brief-risk-layers").locator(".ds-role-success")).toHaveCount(0);
  await page.getByTestId("auto-brief-back").click();
  await expect(stage(page)).toHaveAttribute("data-scene", "complete");
  // The stage draws a schematic: no map tiles, iframes or images of its own.
  await expect(stage(page).locator("img, iframe, canvas, .leaflet-container")).toHaveCount(0);
  expect(await panel(page).innerText()).not.toMatch(/completed_with_gaps|needs_input|no_data|provider_unavailable|partial_evidence|reused_saved|money_partial|lockin/);

  // View Brief, reopen, Compare, Report and reload add zero acquisitions, and nothing replays.
  await page.getByTestId("auto-brief-view-brief").click();
  await expect(page.getByTestId("commercial-overview-workspace")).toBeVisible();
  await page.goto("/cases/case-a/location");
  await expect(stage(page)).toHaveAttribute("data-scene", "complete");
  await page.reload();
  await expect(stage(page)).toHaveAttribute("data-scene", "complete");
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeVisible();
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-evidence")).toBeVisible();
  expect(calls).toEqual(ONCE);
});

test("market no_data and Risk unavailable are presented exactly as recorded", async ({ page }) => {
  const calls = await prepare(page, [v2Case()], "en", { marketBody: { ...e9Case().data.marketInsight, data_status: "no_data" }, riskStatus: 503 });
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await finished(page);
  const c = autoBriefCopy.en;
  await expect(step(page, "market")).toHaveAttribute("data-status", "no_data");
  await expect(step(page, "risk")).toHaveAttribute("data-status", "unavailable");
  await review(page, "market");
  await expect(page.getByTestId("auto-brief-market-state")).toHaveText(c.market_no_data);
  await review(page, "risk");
  await expect(page.getByTestId("auto-brief-scene-risk")).toContainText(c.status_unavailable);
  await expect(page.getByTestId("auto-brief-risk-layers")).toHaveCount(0);
  // Retry is offered for the unavailable domain only, and only on request.
  await page.getByTestId("auto-brief-back").click();
  await expect(page.getByTestId("auto-brief-retry-risk")).toBeVisible();
  await expect(page.getByTestId("auto-brief-retry-market")).toHaveCount(0);
  expect(calls).toEqual(ONCE);
});

test("unconfirmed location blocks one-click analysis with a localized action and no acquisition", async ({ page }) => {
  const calls = await prepare(page, [v2Case("case-a", (row) => { delete row.data.propertyIdentityAnchor; })], "en");
  await page.goto("/cases/case-a/location");
  await expect(page.getByTestId("auto-brief-needs-location")).toContainText(autoBriefCopy.en.run_needs_location);
  await expect(page.getByTestId("auto-brief-start")).toBeDisabled();
  await expect(page.getByTestId("auto-brief-manual")).toHaveText(autoBriefCopy.en.manual);
  expect(calls).toEqual(NONE);
});

test("missing Money inputs stay visible as Needs input while the Brief is still built", async ({ page }) => {
  const calls = await prepare(page, [v2Case("case-a", (row) => { delete row.data.financeEvidence; })], "en");
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await finished(page);
  await expect(step(page, "money")).toHaveAttribute("data-status", "needs_input");
  await expect(step(page, "money")).toContainText(autoBriefCopy.en.status_needs_input);
  await expect(step(page, "brief")).toHaveAttribute("data-status", "available");
  await expect(page.getByTestId("auto-brief-go-money")).toHaveAttribute("href", "/cases/case-a/finance");
  await review(page, "money");
  await expect(page.getByTestId("auto-brief-money-missing")).toContainText(autoBriefCopy.en.moneyMissingTitle);
  expect(calls).toEqual(ONCE);
});

test("a saved completed run reopens on the Completed ending with no acquisition and no replay", async ({ page }) => {
  const at = "2026-10-27T00:00:00.000Z";
  const runs = { "case-a": { runId: "auto-brief-saved", caseId: "case-a", mode: "real_case", status: "completed", anchorId: ANCHOR_ID, startedAt: at, updatedAt: at, currentStep: null, reason: null, gapCount: 0,
    steps: STEPS.map((id) => ({ id, status: "available", startedAt: at, completedAt: at, reason: null, retryable: false, ...(id === "location" ? { parts: { nearby: "available", demographics: "available" }, reused: true } : {}) })) } };
  const calls = await prepare(page, [v2Case()], "en", { runs });
  await page.goto("/cases/case-a/location");
  await expect(page.getByTestId("auto-brief-completion")).toHaveAttribute("data-ending", "completed");
  await expect(page.getByTestId("auto-brief-completion")).toContainText(autoBriefCopy.en.leadCompleted);
  await expect(page.getByTestId("auto-brief-gaps")).toHaveText(autoBriefCopy.en.noGaps);
  await expect(page.getByTestId("auto-brief-view-brief")).toHaveText(autoBriefCopy.en.viewBrief);
  await expect(page.getByTestId("auto-brief-retry-risk")).toHaveCount(0);
  expect(calls).toEqual(NONE);
});

test("keyboard: cancel during Market stops later steps; restart and chapter review are keyboard reachable", async ({ page }) => {
  let release!: () => void;
  const market = new Promise<void>((done) => { release = done; });
  const calls = await prepare(page, [v2Case()], "en", { market });
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").focus();
  await page.keyboard.press("Enter");
  await expect(step(page, "market")).toHaveAttribute("data-status", "running");
  await expect(step(page, "market")).toHaveAttribute("aria-current", "step");
  const cancel = page.getByTestId("auto-brief-cancel");
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(panel(page)).toHaveAttribute("data-run-status", "cancelled");
  release();
  await page.waitForTimeout(300);
  await expect(panel(page)).toHaveAttribute("data-run-status", "cancelled");
  await expect(stage(page)).toHaveAttribute("data-scene", "halted");
  await expect(step(page, "risk")).toHaveAttribute("data-status", "skipped");
  expect(calls.risk).toBe(0);
  await expect(page.getByTestId("auto-brief-continue")).toBeVisible();
  await page.getByTestId("auto-brief-restart").focus();
  await page.keyboard.press("Enter");
  await finished(page);
  await page.getByTestId("auto-brief-review-risk").focus();
  await page.keyboard.press("Enter");
  await expect(stage(page)).toHaveAttribute("data-scene", "risk");
  await expect(page.getByTestId("auto-brief-review-risk")).toHaveAttribute("aria-pressed", "true");
  expect(calls).toEqual({ ...ONCE, market: 2 });
});

test("pause holds the presentation while the real run keeps going", async ({ page }) => {
  let release!: () => void;
  const market = new Promise<void>((done) => { release = done; });
  const calls = await prepare(page, [v2Case()], "en", { market });
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await expect(stage(page)).toHaveAttribute("data-scene", "market");
  await page.getByTestId("auto-brief-pause").click();
  await expect(page.getByTestId("auto-brief-pause")).toHaveAttribute("aria-pressed", "true");
  release();
  // The run finishes while the presentation stays held on Market; acquisition never waits for the view.
  await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
  await expect(step(page, "risk")).toHaveAttribute("data-status", "partial");
  await expect(stage(page)).toHaveAttribute("data-scene", "market");
  await page.getByTestId("auto-brief-pause").click();
  await finished(page);
  expect(calls).toEqual(ONCE);
});

test("skip animation skips presentation only: every acquisition still runs once", async ({ page }) => {
  let release!: () => void;
  const market = new Promise<void>((done) => { release = done; });
  const calls = await prepare(page, [v2Case()], "en", { market });
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await expect(stage(page)).toHaveAttribute("data-motion", "on");
  await page.getByTestId("auto-brief-skip").click();
  await expect(stage(page)).toHaveAttribute("data-motion", "off");
  release();
  await finished(page);
  for (const id of STEPS) await expect(step(page, id)).not.toHaveAttribute("data-status", /pending|running|skipped/);
  expect(calls).toEqual(ONCE);
});

test("reduced motion: the same workflow as a fast state interface without animation", async ({ page }) => {
  const calls = await prepare(page, [v2Case()], "ja", { reducedMotion: true });
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await expect(stage(page)).toHaveAttribute("data-motion", "off");
  await finished(page);
  await expect(page.getByTestId("auto-brief-status")).toContainText(autoBriefCopy.ja.run_completed_with_gaps);
  expect(await stage(page).evaluate((root) => root.getAnimations({ subtree: true }).filter((animation) => animation.playState === "running").length)).toBe(0);
  await review(page, "location");
  expect(await stage(page).evaluate((root) => root.getAnimations({ subtree: true }).filter((animation) => animation.playState === "running").length)).toBe(0);
  expect(calls).toEqual(ONCE);
});

test("reload during Risk shows interrupted and never resumes provider calls by itself", async ({ page }) => {
  const risk = new Promise<void>(() => undefined);
  const calls = await prepare(page, [v2Case()], "zh-TW", { risk });
  await page.goto("/cases/case-a/location");
  await page.getByTestId("auto-brief-start").click();
  await expect(step(page, "risk")).toHaveAttribute("data-status", "running");
  await page.reload();
  await expect(panel(page)).toHaveAttribute("data-run-status", "interrupted");
  await expect(stage(page)).toHaveAttribute("data-scene", "halted");
  await expect(page.getByTestId("auto-brief-status")).toContainText(autoBriefCopy["zh-TW"].run_interrupted);
  await expect(step(page, "market")).toHaveAttribute("data-status", "available");
  await expect(step(page, "risk")).toHaveAttribute("data-status", "pending");
  await page.waitForTimeout(300);
  expect(calls).toEqual(ONCE);
  await expect(page.getByTestId("auto-brief-continue")).toBeVisible();
});

test("demo fixture runs the same cinematic steps with zero provider calls", async ({ page }) => {
  const calls = await prepare(page, buildDemoCases("en"), "en");
  await page.goto(`/cases/${DEMO_CASE_A_ID}/location`);
  await expect(page.getByTestId("auto-brief-demo-note")).toHaveText(autoBriefCopy.en.demoNote);
  await page.getByTestId("auto-brief-start").click();
  await expect(panel(page)).toHaveAttribute("data-run-status", /completed/);
  // Demo cases use showcase pacing; skipping shortens the presentation only.
  await expect(stage(page)).toHaveAttribute("data-showcase", "on");
  await page.getByTestId("auto-brief-skip").click();
  await expect(page.getByTestId("auto-brief-completion")).toBeVisible({ timeout: 10_000 });
  for (const id of STEPS) await expect(step(page, id)).not.toHaveAttribute("data-status", /pending|running/);
  await review(page, "location");
  await expect(page.getByTestId("auto-brief-poi-legend").locator("li").first()).toBeVisible();
  expect(calls).toEqual(NONE);
});

for (const locale of LOCALES) {
  test(`${locale}: localized cinematic stage at 390 / 430 / 1024 / 1440 without overflow; locale switch acquires nothing`, async ({ page }) => {
    const calls = await prepare(page, [v2Case()], locale);
    const c = autoBriefCopy[locale];
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/cases/case-a/location");
    await expect(page.getByTestId("auto-brief-start")).toHaveText(c.start);
    await page.getByTestId("auto-brief-start").click();
    await finished(page);
    await expect(page.getByTestId("auto-brief-status")).toContainText(c.run_completed_with_gaps);
    await expect(page.getByTestId("auto-brief-rail-lockin")).toContainText(c.rail_lockin);
    for (const id of STEPS) await expect(step(page, id)).toContainText(c[`rail_${id}`]);
    await expect(page.getByTestId("auto-brief-view-brief")).toHaveText(c.viewBrief);
    for (const width of [390, 430, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const scene of ["complete", "location", "risk"] as const) {
        if (scene !== "complete") await review(page, scene);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        expect(overflow, `${locale} ${width} ${scene}`).toBeLessThanOrEqual(0);
        const box = await panel(page).boundingBox();
        expect(box!.x + box!.width, `${locale} ${width} ${scene} panel`).toBeLessThanOrEqual(width + 0.5);
      }
      await page.getByTestId("auto-brief-back").click();
      const screen = await page.getByTestId("auto-brief-screen").boundingBox();
      const rail = await stage(page).getByRole("list", { name: autoBriefCopy[locale].progress }).boundingBox();
      // Narrow: a vertical story with the scene above the rail. Wide: rail beside the stage.
      if (width < 1024) expect(rail!.y, `${locale} ${width} stacked`).toBeGreaterThan(screen!.y);
      else expect(rail!.x + rail!.width, `${locale} ${width} side by side`).toBeLessThanOrEqual(screen!.x + 1);
    }
    const other = locale === "en" ? "ko" : "en";
    await page.getByTestId("locale-switcher").selectOption(other).catch(async () => {
      await page.evaluate((next) => localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale: next })), other);
      await page.reload();
    });
    await expect(page.getByTestId("auto-brief-status")).toContainText(autoBriefCopy[other].run_completed_with_gaps);
    expect(calls).toEqual(ONCE);
  });
}
