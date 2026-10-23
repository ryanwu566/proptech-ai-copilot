import { expect, test } from "./fixtures";
import type { Page, Request } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";
import { locationConfirmationCopy } from "../lib/workspace/location-confirmation-copy";
import { buildAddressDraftCase } from "../lib/workspace/case-draft";

/**
 * In-case location confirmation: Find = one geocode-only /location/resolve; Confirm = identity only.
 * Rendering a case, finding or confirming never runs nearby, commute, market, valuation or risk providers.
 */
const KEY = "proptech.savedCases.v1";
const ADDRESS = "臺北市信義區市府路1號";
const RESOLVED = { status: "resolved", source: "tgos", formatted_address: "臺北市信義區市府路1號", latitude: 25.0375, longitude: 121.5637, confidence: "high", message: "ok", county: "臺北市", district: "信義區" };
// Free basemap tiles render once a confirmed map is shown; they are not provider enrichment.
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");

type Calls = { provider: string[]; resolve: number; basemap: number };

async function prepare(page: Page, rows: unknown[] = [], resolve: (route: import("@playwright/test").Route) => Promise<void> = (route) => route.fulfill({ json: RESOLVED })) {
  await page.addInitScript(({ key, rows }) => {
    if (sessionStorage.getItem("location-confirmation-seeded")) return;
    sessionStorage.setItem("location-confirmation-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, rows });
  const calls: Calls = { provider: [], resolve: 0, basemap: 0 };
  await page.route("**/location/resolve", async (route) => { calls.resolve++; await resolve(route); });
  await page.route((url) => BASEMAP.test(url.hostname), (route) => { calls.basemap++; return route.fulfill({ status: 200, contentType: "image/png", body: PNG }); });
  return calls;
}

function record(page: Page, calls: Calls) {
  const origin = new URL(page.url()).origin;
  page.on("request", (request: Request) => {
    const url = new URL(request.url());
    if (BASEMAP.test(url.hostname) || url.pathname.endsWith("/location/resolve")) return;
    if (isProviderRequest(request, origin)) calls.provider.push(`${request.method()} ${url.host}${url.pathname}`);
  });
}

const stored = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "[]") as Array<{ id: string; updatedAt: string; data: Record<string, unknown> }>, KEY);

test("in-case lookup deadline ends loading and an explicit retry remains usable", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let attempt = 0;
  const calls = await prepare(page, [], async (route) => {
    if (++attempt === 1) await gate;
    await route.fulfill({ json: RESOLVED }).catch(() => {});
  });
  const caseId = await startCase(page);
  record(page, calls);
  await page.clock.install();
  const before = await stored(page);
  await page.getByTestId("location-find").click();
  await expect.poll(() => calls.resolve).toBe(1);
  await page.clock.fastForward(10_001);
  await expect(page.getByTestId("location-confirmation-failure")).toHaveAttribute("data-reason", "unavailable");
  await expect(page.getByTestId("location-find")).toHaveCount(0);
  expect(await stored(page)).toEqual(before);
  expect(before[0].id).toBe(caseId);
  release();
  await page.clock.fastForward(30_000);
  await expect(page.getByTestId("location-candidate")).toHaveCount(0);
  expect(calls.resolve).toBe(1);
  await page.getByRole("button", { name: locationConfirmationCopy["zh-TW"].retry, exact: true }).click();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  expect(calls.resolve).toBe(2);
  expect(await stored(page)).toEqual(before);
  expect(calls.provider).toEqual([]);
});

test("a contradictory district response is never presented as a trusted candidate", async ({ page }) => {
  const calls = await prepare(page, [], (route) => route.fulfill({ json: { ...RESOLVED, district: "大安區", formatted_address: "臺北市大安區市府路1號" } }));
  await startCase(page);
  await page.getByTestId("location-find").click();
  await expect(page.getByTestId("location-confirmation-failure")).toHaveAttribute("data-reason", "invalid");
  await expect(page.getByTestId("location-candidate")).toHaveCount(0);
  expect((await stored(page))[0].data.propertyIdentityAnchor).toBeUndefined();
  expect(calls.resolve).toBe(1);
});

async function startCase(page: Page) {
  await page.goto("/");
  // Existing address-only cases have no automatic acquisition. Home Start is covered in home-location-flow.spec.ts.
  const draft = buildAddressDraftCase(ADDRESS, { id: "fallback-location-case", now: "2026-10-20T08:00:00Z" })!;
  await page.evaluate(({ key, draft }) => localStorage.setItem(key, JSON.stringify([draft, ...JSON.parse(localStorage.getItem(key) ?? "[]")])), { key: KEY, draft });
  await page.goto(`/cases/${draft.id}/location`);
  return draft.id;
}

test("existing address-only case → lookup → confirm unlocks actions with one explicit lookup and no enrichment", async ({ page }) => {
  const calls = await prepare(page, [e9Case()]);
  await page.goto("/");
  record(page, calls);
  const caseId = await startCase(page);
  const panel = page.getByTestId("location-confirmation");
  await expect(panel).toBeVisible();
  await page.waitForLoadState("networkidle");
  // A + B + C: Home start, opening the case and rendering Location run nothing.
  expect(calls).toEqual({ provider: [], resolve: 0, basemap: 0 });

  // D + E: Find runs exactly one geocode-only resolve and saves only unconfirmed UI data.
  const before = JSON.stringify(await stored(page));
  const find = panel.getByRole("button", { name: "確認物件位置", exact: true });
  await find.dblclick();
  const candidate = page.getByTestId("location-candidate");
  await expect(candidate).toBeFocused();
  await expect(candidate).toContainText("臺北市信義區市府路1號");
  await page.getByTestId("location-candidate-details").getByText(locationConfirmationCopy["zh-TW"].details, { exact: true }).click();
  await expect(candidate).toContainText("臺北市 · 信義區");
  await expect(candidate).toContainText("25.037500, 121.563700");
  await expect(candidate).toContainText("TGOS 地址解析");
  await page.waitForLoadState("networkidle");
  expect(calls.resolve).toBe(1);
  expect(calls.provider).toEqual([]);
  expect(JSON.stringify(await stored(page))).not.toBe(before);
  const pending = (await stored(page)).find((row) => row.id === caseId)!;
  expect(pending.data.propertyIdentityAnchor).toBeUndefined();
  expect(pending.data.pendingLocationCandidate).toMatchObject({ state: "unconfirmed", caseId });

  // F: Confirm persists identity only and runs no provider.
  await candidate.getByRole("button", { name: "確認位置", exact: true }).click();
  await expect(page.getByTestId("location-confirmation-status")).toContainText("已確認物件位置");
  await expect(panel).toHaveCount(0);
  await expect(page.getByRole("banner", { name: "目前物件" })).not.toContainText("物件尚待確認");
  await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(calls.resolve).toBe(1);
  expect(calls.provider).toEqual([]);
  const rows = await stored(page);
  expect(rows).toHaveLength(2);
  const created = rows.find((row) => row.id === caseId)!;
  expect(created.data.propertyIdentityAnchor).toMatchObject({ address_input: ADDRESS, coordinates: { latitude: 25.0375, longitude: 121.5637 }, administrative_location: { city: "臺北市", district: "信義區", village: null }, parcel: { status: "unavailable" }, building: { status: "unavailable" }, revalidation: { status: "current" } });
  for (const field of ["marketInsight", "valuation", "locationInsight", "terrainReference", "commuteRoute", "commuteTransit", "financeEvidence"]) expect(created.data[field]).toBeUndefined();

  // Downstream unlock matrix — every action stays explicit; nothing auto-runs.
  const nav = page.locator(".workspace-navigation");
  await nav.getByRole("link", { name: "物件總覽", exact: true }).click();
  await expect(page.getByTestId("commercial-overview-workspace")).not.toContainText("確認物件位置");
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(ADDRESS);
  await nav.getByRole("link", { name: "價格與市場", exact: true }).click();
  await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
  await nav.getByRole("link", { name: "風險與環境", exact: true }).click();
  await expect(page.getByRole("button", { name: "查詢目前物件風險證據", exact: true })).toBeEnabled();
  await nav.getByRole("link", { name: "區位與通勤", exact: true }).click();
  await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toContainText(ADDRESS);
  // Finance / snapshot: identity-dependent save now succeeds.
  await page.getByRole("button", { name: "保存目前案件快照", exact: true }).click();
  await expect(page.getByTestId("context-save-status")).toContainText("已保存");
  await page.waitForLoadState("networkidle");
  expect(calls.provider).toEqual([]);

  await page.goto(`/cases/${encodeURIComponent(caseId)}/report`);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("案件證據報告");
  await page.goto(`/compare?cases=${encodeURIComponent(caseId)},case-a`);
  await expect(page.locator("#main-content")).not.toContainText("身分需要重新確認");
  await expect(page.getByTestId("compare-desktop")).toContainText(ADDRESS);

  // G: reopening reuses the persisted identity without resolving again.
  await page.goto(`/cases/${encodeURIComponent(caseId)}/location`);
  await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toBeVisible();
  await expect(page.getByTestId("location-confirmation")).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  expect(calls.resolve).toBe(1);
  expect(calls.provider).toEqual([]);
});

const FAILURES: Array<[string, (route: import("@playwright/test").Route) => Promise<void>, string, string]> = [
  ["unresolved", (route) => route.fulfill({ json: { ...RESOLVED, status: "unresolved", source: "none", latitude: null, longitude: null, confidence: "unknown", county: null, district: null } }), "unresolved", "找不到可信位置"],
  ["provider 503", (route) => route.fulfill({ status: 503, json: { detail: "unavailable" } }), "provider_unavailable", "暫時無法使用"],
  ["capacity 429", (route) => route.fulfill({ status: 429, headers: { "Retry-After": "1" }, json: { detail: "capacity unavailable" } }), "capacity_unavailable", "查詢較忙碌"],
  ["low confidence", (route) => route.fulfill({ json: { ...RESOLVED, confidence: "unknown" } }), "low_confidence", "可信度不足"],
  ["missing coordinates", (route) => route.fulfill({ json: { ...RESOLVED, latitude: null } }), "missing_coordinates", "缺少座標"],
  ["structurally invalid", (route) => route.fulfill({ json: ["resolved"] }), "invalid", "無法安全判讀"],
];
for (const [name, respond, reason, text] of FAILURES) {
  test(`${name} result cannot be confirmed and persists nothing`, async ({ page }) => {
    const calls = await prepare(page, [], respond);
    await page.goto("/");
    record(page, calls);
    const caseId = await startCase(page);
    const before = JSON.stringify(await stored(page));
    await page.getByRole("button", { name: "確認物件位置", exact: true }).click();
    const failure = page.getByTestId("location-confirmation-failure");
    await expect(failure).toHaveAttribute("data-reason", reason);
    await expect(failure).toContainText(text);
    await expect(page.getByRole("button", { name: "重新確認位置", exact: true })).toBeEnabled();
    await expect(page.getByRole("button", { name: "確認位置", exact: true })).toHaveCount(0);
    expect(JSON.stringify(await stored(page))).toBe(before);
    expect((await stored(page)).find((row) => row.id === caseId)!.data.propertyIdentityAnchor).toBeUndefined();
    expect(calls.resolve).toBe(1);
    expect(calls.provider).toEqual([]);
  });
}

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const width of [390, 430]) {
  test(`spatial confirmation without administrative area persists at ${width}px in ${locale}`, async ({ page }) => {
    // The deployed older response omits the fields entirely, rather than returning nulls.
    const spatial = Object.fromEntries(Object.entries(RESOLVED).filter(([key]) => key !== "county" && key !== "district"));
    const calls = await prepare(page, [], (route) => route.fulfill({ json: spatial }));
    await page.setViewportSize({ width, height: 850 });
    await page.goto("/");
    record(page, calls);
    const caseId = await startCase(page);
    await page.getByTestId("locale-switcher").selectOption(locale);
    const copy = locationConfirmationCopy[locale];
    await page.getByRole("button", { name: copy.find, exact: true }).click();
    await expect(page.getByTestId("location-candidate")).toContainText(copy.adminUnknown);
    const confirm = page.getByRole("button", { name: copy.confirm, exact: true });
    await confirm.scrollIntoViewIfNeeded();
    expect((await confirm.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await confirm.click();
    await expect(page.getByTestId("location-administrative-incomplete")).toContainText(copy.adminIncomplete);
    await expect(page.getByTestId("location-confirmation")).toHaveCount(0);
    await expect(page.getByTestId("nearby-facilities").getByRole("button").first()).toBeEnabled();
    await expect(page.getByTestId("commute-route-card").getByRole("button").first()).toBeEnabled();
    const row = (await stored(page)).find((item) => item.id === caseId)!;
    expect(row.data.propertyIdentityAnchor).toMatchObject({
      coordinates: { latitude: RESOLVED.latitude, longitude: RESOLVED.longitude },
      administrative_location: { city: null, district: null, village: null, village_code: null },
      confidence: { level: "medium", domain: "address_spatial_correlation" },
      parcel: { status: "unavailable", confirmation: null }, building: { status: "unavailable", confirmation: null },
    });
    await page.goto(`/cases/${caseId}/market`);
    await expect(page.getByTestId("market-refresh-button")).toBeDisabled();
    await expect(page.getByTestId("valuation-refresh-button")).toBeDisabled();
    await expect(page.getByTestId("market-administrative-unavailable")).toContainText(copy.adminIncomplete);
    await page.goto(`/cases/${caseId}/location`);
    await page.reload();
    await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toBeVisible();
    await expect(page.getByTestId("location-administrative-incomplete")).toContainText(copy.adminIncomplete);
    await expect(page.getByTestId("location-confirmation")).toHaveCount(0);
    await page.waitForLoadState("networkidle");
    expect(calls.resolve).toBe(1);
    expect(calls.provider).toEqual([]);
    expect((await stored(page)).find((item) => item.id === caseId)!.data.propertyIdentityAnchor).toEqual(row.data.propertyIdentityAnchor);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

test("spatial-only anchor supplies Nearby and Commute coordinates on explicit actions, never on reopen", async ({ page }) => {
  const calls = await prepare(page, [], (route) => route.fulfill({ json: { ...RESOLVED, county: null, district: null } }));
  const nearby: unknown[] = [];
  const commute: unknown[] = [];
  await page.route("**/map/nearby", async (route) => {
    const payload = route.request().postDataJSON();
    nearby.push(payload);
    await route.fulfill({ json: { center: { lat: RESOLVED.latitude, lng: RESOLVED.longitude }, radius_m: 800, source: "google_places", categories: [{ category: "shopping", source: "google_places", places: [{ place_id: "shop", name: "Spatial fixture shop", lat: RESOLVED.latitude + 0.001, lng: RESOLVED.longitude, source: "google_places" }] }] } });
  });
  await page.route("**/commute/route", async (route) => {
    const payload = route.request().postDataJSON();
    commute.push(payload);
    await route.fulfill({ json: { status: "resolved", source: "google_routes", mode: "transit", duration_min: 23, duration_seconds: 1380, distance_m: 8100, partial: false, fallback: false, reason_code: "success", checked_at: "2026-10-20T08:00:00Z", origin: { latitude: RESOLVED.latitude, longitude: RESOLVED.longitude }, destination: { address: "台北車站" } } });
  });
  const caseId = await startCase(page);
  await page.getByRole("button", { name: "確認物件位置", exact: true }).click();
  await page.getByRole("button", { name: "確認位置", exact: true }).click();
  await expect(page.getByTestId("location-administrative-incomplete")).toBeVisible();
  expect(nearby).toHaveLength(0);
  expect(commute).toHaveLength(0);
  await page.getByTestId("nearby-facilities").getByRole("button", { name: "查附近生活機能", exact: true }).click();
  await expect(page.getByTestId("nearby-facilities")).toContainText("Spatial fixture shop");
  expect(nearby).toHaveLength(1);
  expect(nearby[0]).toMatchObject({ lat: RESOLVED.latitude, lng: RESOLVED.longitude });
  await page.getByRole("textbox", { name: "目的地地址", exact: true }).fill("台北車站");
  await page.getByTestId("commute-route-card").getByRole("button").click();
  await expect(page.getByTestId("commute-route-state")).toHaveAttribute("data-status", "available");
  expect(commute).toEqual([{ origin_latitude: RESOLVED.latitude, origin_longitude: RESOLVED.longitude, destination_address: "台北車站", mode: "transit" }]);
  await page.reload();
  await expect(page.getByTestId("nearby-facilities")).toContainText("Spatial fixture shop");
  await expect(page.getByRole("textbox", { name: "目的地地址", exact: true })).toHaveValue("台北車站");
  await expect(page.getByTestId("commute-route-state")).toHaveAttribute("data-status", "available");
  await page.waitForLoadState("networkidle");
  expect(calls.resolve).toBe(1);
  expect(nearby).toHaveLength(1);
  expect(commute).toHaveLength(1);
  expect((await stored(page)).find((item) => item.id === caseId)!.data.propertyIdentityAnchor).toMatchObject({ administrative_location: { city: null, district: null } });
});

test("search again explicitly reacquires and saves only an unconfirmed candidate", async ({ page }) => {
  const calls = await prepare(page);
  await page.goto("/");
  await startCase(page);
  await page.getByRole("button", { name: "確認物件位置", exact: true }).click();
  await page.getByRole("button", { name: "重新尋找", exact: true }).click();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  const rows = await stored(page);
  expect(rows).toHaveLength(1);
  expect(rows[0].data.propertyIdentityAnchor).toBeUndefined();
  expect(rows[0].data.pendingLocationCandidate).toMatchObject({ state: "unconfirmed" });
  expect(calls.resolve).toBe(2);
});

test("a case changed elsewhere after Find is not overwritten by Confirm", async ({ page }) => {
  await prepare(page);
  await page.goto("/");
  const caseId = await startCase(page);
  await page.getByRole("button", { name: "確認物件位置", exact: true }).click();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  // Another tab edits the case without firing an event in this tab.
  const changed = await page.evaluate(({ key, caseId }) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows.find((row: { id: string }) => row.id === caseId).updatedAt = "2026-10-18T09:59:59.000Z";
    localStorage.setItem(key, JSON.stringify(rows));
    return localStorage.getItem(key);
  }, { key: KEY, caseId });
  await page.getByRole("button", { name: "確認位置", exact: true }).click();
  await expect(page.getByTestId("location-confirmation-failure")).toHaveAttribute("data-reason", "case_changed");
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBe(changed);
});

for (const [locale, find, confirm] of [["en", "Check property location", "Confirm location"], ["ja", "物件の位置を確認", "位置を確定"], ["ko", "부동산 위치 확인", "위치 확정"]] as const) {
  test(`${locale} confirmation controls are localized`, async ({ page }) => {
    await prepare(page);
    await page.goto("/");
    await startCase(page);
    await page.getByTestId("locale-switcher").selectOption(locale);
    await page.getByRole("button", { name: find, exact: true }).click();
    await expect(page.getByRole("button", { name: confirm, exact: true })).toBeVisible();
    const panel = await page.getByTestId("location-confirmation").innerText();
    if (locale !== "ja") expect(panel.replaceAll(ADDRESS, "").replace(/臺北市|信義區/g, "")).not.toMatch(/[一-鿿]/);
  });
}

for (const width of [360, 390, 430]) {
  test(`confirmation fits ${width}px without horizontal overflow`, async ({ page }) => {
    await prepare(page);
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    await startCase(page);
    await page.getByRole("button", { name: "確認物件位置", exact: true }).click();
    const confirm = page.getByRole("button", { name: "確認位置", exact: true });
    await confirm.scrollIntoViewIfNeeded();
    expect((await confirm.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
