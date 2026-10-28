import { expect, test } from "./fixtures";
import type { Page, Route } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { buildAddressDraftCase } from "../lib/workspace/case-draft";
import { captureVillageDemographics } from "../lib/workspace/village-demographics";
import { villageDemographicsCopy } from "../lib/workspace/village-demographics-copy";
import { isNearbyRequest, routeNearby, type NearbyCall } from "./helpers/nearby-route";
import { isProviderRequest } from "./helpers/provider-request";

/**
 * Location V2 village demographics in the case workspace. The frontend only calls the backend's
 * /demographics/location; it never reaches RIS, NLSC or R2. Saved results are read without acquisition,
 * and a result for one location identity can never land on another.
 */
const KEY = "proptech.savedCases.v1";
const POINT = { latitude: 24.16525, longitude: 120.64555 };
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const FORBIDDEN = /r2\.|cloudflarestorage|ris\.gov|\/ris\/|nlsc\.gov|wms\.nlsc|village_boundary/i;

const VILLAGE = { status: "resolved", county: "臺中市", town: "西屯區", village: "潮洋里", village_code: "66000060020", district_code: "66000060020", source: "nlsc_village_boundary", source_vintage: "ROC-1150817", reason: "unique_intersection" };
function available(population: number, overrides: Record<string, unknown> = {}) {
  return { status: "available", reason: null, statistic_yyymm: "11508", statistic_month: "2026-08-01", total_population: population, household_count: 4567, average_household_size: 2.7, child_ratio: 0.121, working_age_ratio: 0.702, elderly_ratio: 0.177, first_month: "11408", last_month: "11508", observed_month_count: 13, population_change: 120, population_change_ratio: 0.0098, household_change: 45, has_month_gaps: false, trend_status: "increasing", source_provider: "RIS", source_dataset: "ODRP014", ...overrides };
}
function payload(point: { latitude: number; longitude: number }, village: Record<string, unknown>, demographics: Record<string, unknown>) {
  return { ...point, checked_at: "2026-10-20T08:00:00+00:00", village_resolution: village, demographics };
}
const UNRESOLVED = { ...VILLAGE, status: "unresolved", county: null, town: null, village: null, village_code: null, district_code: null, reason: "zero_polygon" };
const STATES = {
  available: payload(POINT, VILLAGE, available(12345)),
  zero: payload(POINT, VILLAGE, available(0, { household_count: 0, child_ratio: 0, working_age_ratio: null, elderly_ratio: null, average_household_size: null, observed_month_count: 1, first_month: "11508", population_change: 0, household_change: 0, population_change_ratio: null })),
  no_data: payload(POINT, VILLAGE, { status: "no_data", reason: "demographics_not_available_for_village_code" }),
  unavailable: payload(POINT, VILLAGE, { status: "no_data", reason: "demographics_unavailable" }),
  unresolved: payload(POINT, UNRESOLVED, { status: "no_data", reason: "village_identity_not_resolved" }),
  ambiguous: payload(POINT, { ...UNRESOLVED, status: "ambiguous", reason: "multiple_intersecting_polygons", candidate_count: 2 }, { status: "no_data", reason: "village_identity_not_resolved" }),
} as const;
const STATE_TEST_IDS: Record<keyof typeof STATES, string> = {
  available: "demographics-available", zero: "demographics-available", no_data: "demographics-no-data",
  unavailable: "demographics-unavailable", unresolved: "demographics-village-unresolved", ambiguous: "demographics-village-ambiguous",
};

type Calls = { demographics: string[]; nearby: NearbyCall[]; provider: string[]; forbidden: string[] };

async function prepare(page: Page, rows: unknown[], respond: (route: Route, point: string) => Promise<void> = (route) => route.fulfill({ json: STATES.available })) {
  await page.addInitScript(({ key, rows }) => {
    if (sessionStorage.getItem("demographics-v2-seeded")) return;
    sessionStorage.setItem("demographics-v2-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, rows });
  const calls: Calls = { demographics: [], nearby: [], provider: [], forbidden: [] };
  // Confirm also refreshes Nearby once (Gate L1-2); it is counted on its own, never as an unrelated provider.
  await routeNearby(page, calls.nearby);
  page.on("request", (request) => {
    const url = new URL(request.url());
    // Content-hashed build chunks (e.g. "…cr2.js") are the app itself, never a direct provider call.
    if (FORBIDDEN.test(request.url()) && !url.pathname.startsWith("/_next/")) calls.forbidden.push(request.url());
    if (BASEMAP.test(url.hostname) || url.pathname.endsWith("/demographics/location") || url.pathname.endsWith("/location/resolve") || isNearbyRequest(url)) return;
    if (isProviderRequest(request, url.hostname === "127.0.0.1" ? url.origin : "http://127.0.0.1")) calls.provider.push(url.pathname);
  });
  await page.route((url) => BASEMAP.test(url.hostname), (route) => route.fulfill({ contentType: "image/png", body: PNG }));
  await page.route("**/demographics/location?*", async (route) => {
    const url = new URL(route.request().url());
    const point = `${url.searchParams.get("latitude")},${url.searchParams.get("longitude")}`;
    calls.demographics.push(point);
    await respond(route, point);
  });
  return calls;
}

function seeded(id: string, state: keyof typeof STATES) {
  const saved = e9Case(id);
  saved.data.villageDemographics = captureVillageDemographics(STATES[state], POINT);
  return saved;
}
const card = (page: Page) => page.getByTestId("demographics-insight");
const stored = (page: Page, id: string) => page.evaluate(({ key, id }) => JSON.parse(localStorage.getItem(key) ?? "[]").find((row: { id: string }) => row.id === id), { key: KEY, id });
const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);

for (const locale of LOCALES) for (const width of [390, 430, 1024, 1440]) {
  test(`saved demographics states render localized without acquisition in ${locale} at ${width}px`, async ({ page }) => {
    const states = Object.keys(STATES) as Array<keyof typeof STATES>;
    const calls = await prepare(page, states.map((state) => seeded(`case-${state}`, state)));
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await page.getByTestId("locale-switcher").selectOption(locale);
    const copy = villageDemographicsCopy[locale];
    for (const state of states) {
      await page.goto(`/cases/case-${state}/location`);
      await expect(page.getByTestId(STATE_TEST_IDS[state])).toBeVisible();
      await expect(page.getByTestId("village-demographics")).toContainText(copy.title);
      await expect(card(page)).toContainText(copy.sourceValue);
      // Raw village codes, RIS dataset keys and backend reason codes never reach the screen.
      for (const raw of ["66000060020", "ODRP014", "unique_intersection", "village_identity_not_resolved", "demographics_unavailable", "no_data"]) await expect(card(page)).not.toContainText(raw);
      if (locale !== "zh-TW") for (const zh of ["里人口概況", "資料不足", "統計月份", "總人口", "歷史資料不足"]) await expect(card(page)).not.toContainText(zh);
      if (state === "available") {
        await expect(card(page)).toContainText(copy.population);
        await expect(card(page)).toContainText(copy.age65plus);
        await expect(page.getByTestId("demographics-admin-county")).toContainText("臺中市");
        await expect(page.getByTestId("demographics-admin-district")).toContainText("西屯區");
        await expect(page.getByTestId("demographics-admin-village")).toContainText("潮洋里");
        await expect(page.getByTestId("demographics-trend-summary")).toContainText(copy.trendIncreasing);
        await expect(page.getByTestId("demographics-freshness")).toBeVisible();
      }
      if (state === "zero") {
        // A real zero stays 0 / 0.0%; a null ratio is "insufficient", never 0.
        await expect(card(page)).toContainText("0.0%");
        await expect(card(page)).toContainText(copy.insufficient);
        await expect(page.getByTestId("demographics-trend-insufficient")).toHaveText(copy.trendInsufficient);
      }
      if (state === "ambiguous") await expect(card(page)).toContainText("2");
      expect(await noOverflow(page)).toBe(true);
    }
    await page.waitForLoadState("networkidle");
    expect(calls).toEqual({ demographics: [], nearby: [], provider: [], forbidden: [] });
  });
}

test("locale switch, Report and Compare reuse saved demographics without refetching", async ({ page }) => {
  const calls = await prepare(page, [seeded("case-a", "available"), e9Case("case-b")]);
  await page.goto("/cases/case-a/location");
  await expect(page.getByTestId("demographics-available")).toContainText("12,345");
  for (const locale of LOCALES) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(card(page)).toContainText(villageDemographicsCopy[locale].population);
  }
  await page.goto("/cases/case-a/report");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeAttached();
  await page.goto("/cases/case-a/location");
  await page.reload();
  await expect(page.getByTestId("demographics-available")).toBeVisible();
  // case-b has no saved demographics: a visible, explicit "not checked" state with a manual action.
  await page.goto("/cases/case-b/location");
  await expect(page.getByTestId("demographics-not-run")).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(calls).toEqual({ demographics: [], nearby: [], provider: [], forbidden: [] });
});

test("explicit refresh re-runs once for the confirmed anchor and replaces the saved result", async ({ page }) => {
  let population = 20000;
  const calls = await prepare(page, [seeded("case-a", "available")], (route) => route.fulfill({ json: payload(POINT, VILLAGE, available(population)) }));
  await page.goto("/cases/case-a/location");
  await expect(page.getByTestId("demographics-available")).toContainText("12,345");
  await page.getByTestId("demographics-refresh").evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await expect(page.getByTestId("demographics-available")).toContainText("20,000");
  expect(calls.demographics).toEqual([`${POINT.latitude},${POINT.longitude}`]);
  expect((await stored(page, "case-a")).data.villageDemographics.demographics.total_population).toBe(20000);
  // A failed refresh keeps the saved result visible with an explicit note.
  population = 1;
  await page.unroute("**/demographics/location?*");
  await page.route("**/demographics/location?*", (route) => { calls.demographics.push("failed"); return route.fulfill({ status: 503, json: { detail: { code: "unavailable", message: "x" } } }); });
  await page.getByTestId("demographics-refresh").click();
  await expect(page.getByTestId("village-demographics")).toContainText(villageDemographicsCopy["zh-TW"].failedKept);
  await expect(page.getByTestId("demographics-available")).toContainText("20,000");
  expect(calls.provider).toEqual([]);
  expect(calls.forbidden).toEqual([]);
});

test("a failed first acquisition shows the unavailable state instead of hiding the section", async ({ page }) => {
  const calls = await prepare(page, [e9Case("case-a")], (route) => route.fulfill({ status: 503, json: { detail: { code: "unavailable", message: "x" } } }));
  await page.goto("/cases/case-a/location");
  await expect(page.getByTestId("demographics-not-run")).toBeVisible();
  await page.getByTestId("demographics-refresh").click();
  await expect(page.getByTestId("demographics-unavailable")).toBeVisible();
  expect(calls.demographics).toHaveLength(1);
  expect((await stored(page, "case-a")).data.villageDemographics).toBeUndefined();
});

async function startAddressCase(page: Page, id: string, address: string) {
  const draft = buildAddressDraftCase(address, { id, now: "2026-10-20T08:00:00Z" })!;
  await page.evaluate(({ key, draft }) => localStorage.setItem(key, JSON.stringify([draft, ...JSON.parse(localStorage.getItem(key) ?? "[]")])), { key: KEY, draft });
  await page.goto(`/cases/${id}/location`);
}

const RESOLVE_A = { status: "resolved", source: "google", formatted_address: "臺北市信義區市府路1號", latitude: 25.0375, longitude: 121.5637, confidence: "high", message: "ok", county: "臺北市", district: "信義區" };

test("stale A: a late result for case A lands only on case A, never on case B", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const calls = await prepare(page, [seeded("case-b", "available")], async (route, point) => {
    if (point === "25.0375,121.5637") await gate;
    await route.fulfill({ json: payload({ latitude: 25.0375, longitude: 121.5637 }, { ...VILLAGE, county: "臺北市", town: "信義區", village: "西村里" }, available(99999)) }).catch(() => {});
  });
  await page.route("**/location/resolve", (route) => route.fulfill({ json: RESOLVE_A }));
  await page.goto("/");
  await startAddressCase(page, "case-x", "臺北市信義區市府路1號");
  await page.getByTestId("location-find").click();
  await page.getByTestId("location-confirm").click();
  await expect(page.getByTestId("demographics-loading")).toBeVisible();
  await expect.poll(() => calls.demographics).toEqual(["25.0375,121.5637"]);
  const caseB = JSON.stringify((await stored(page, "case-b")).data.villageDemographics);
  // Leave the Location view in-document while A's request is in flight, then let A's response arrive.
  await page.locator(".workspace-navigation").getByRole("link", { name: "物件總覽", exact: true }).click();
  await expect(page).toHaveURL(/\/case-x\/overview$/);
  release();
  // The acquisition owns persistence for its own identity only.
  await expect.poll(async () => (await stored(page, "case-x")).data.villageDemographics?.demographics.total_population).toBe(99999);
  expect(JSON.stringify((await stored(page, "case-b")).data.villageDemographics)).toBe(caseB);
  await page.goto("/cases/case-b/location");
  await expect(page.getByTestId("demographics-available")).toContainText("12,345");
  await expect(page.getByTestId("demographics-available")).not.toContainText("99,999");
  // Reopening case X reads its own saved result; there is no second acquisition.
  await page.goto("/cases/case-x/location");
  await expect(page.getByTestId("demographics-available")).toContainText("99,999");
  await page.waitForLoadState("networkidle");
  expect(calls.demographics).toHaveLength(1);
  expect(calls.nearby).toEqual([expect.objectContaining({ lat: 25.0375, lng: 121.5637 })]);
  expect((await stored(page, "case-x")).data.nearbyFacilities?.origin).toEqual({ lat: 25.0375, lng: 121.5637 });
  expect((await stored(page, "case-b")).data.nearbyFacilities).toBeUndefined();
  expect(calls.provider).toEqual([]);
  expect(calls.forbidden).toEqual([]);
});

test("stale A: a response for the old coordinate cannot be saved once the identity moved to B", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const calls = await prepare(page, [], async (route) => {
    await gate;
    await route.fulfill({ json: payload({ latitude: 25.0375, longitude: 121.5637 }, VILLAGE, available(99999)) }).catch(() => {});
  });
  await page.route("**/location/resolve", (route) => route.fulfill({ json: RESOLVE_A }));
  await page.goto("/");
  await startAddressCase(page, "case-x", "臺北市信義區市府路1號");
  await page.getByTestId("location-find").click();
  await page.getByTestId("location-confirm").click();
  await expect.poll(() => calls.demographics).toHaveLength(1);
  // Another surface re-anchors case X at point B before A's response returns.
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    const anchor = rows[0].data.propertyIdentityAnchor;
    rows[0].data.propertyIdentityAnchor = { ...anchor, journey_anchor_id: "journey-browser-0b0b0b0b-0b0b-4b0b-8b0b-0b0b0b0b0b0b", coordinates: { latitude: 25.0418, longitude: 121.5654 } };
    localStorage.setItem(key, JSON.stringify(rows));
  }, KEY);
  release();
  await page.waitForLoadState("networkidle");
  await expect.poll(async () => (await stored(page, "case-x")).data.villageDemographics).toBeUndefined();
  await expect(page.getByTestId("village-demographics")).toContainText(villageDemographicsCopy["zh-TW"].unsaved);
  await page.reload();
  // B's identity shows no A figures; nothing was written or refetched on reopen.
  await expect(page.locator("#main-content")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("99,999");
  await page.waitForLoadState("networkidle");
  expect((await stored(page, "case-x")).data.villageDemographics).toBeUndefined();
  expect(calls.demographics).toHaveLength(1);
});
