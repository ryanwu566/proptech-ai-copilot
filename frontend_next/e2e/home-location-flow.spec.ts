import { expect, test } from "./fixtures";
import type { Page, Route } from "@playwright/test";
import { isProviderRequest } from "./helpers/provider-request";
import { isNearbyRequest, routeNearby, type NearbyCall } from "./helpers/nearby-route";
import { locationConfirmationCopy } from "../lib/workspace/location-confirmation-copy";
import { identityConfirmationCopy } from "../lib/workspace/identity-confirmation-copy";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

const ADDRESS = "臺北市信義區市府路1號";
const KEY = "proptech.savedCases.v1";
const SPATIAL = { status: "resolved", source: "google", confidence: "high", latitude: 25.0375, longitude: 121.5637, formatted_address: ADDRESS };
const START = { "zh-TW": "開始物件評估", en: "Start property review", ja: "物件の検討を開始", ko: "부동산 검토 시작" };
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const stored = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "[]"), KEY);

test("Home lookup deadline preserves the case and address, ignores late success and retries only explicitly", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let attempt = 0;
  const calls = await prepare(page, async (route) => {
    if (++attempt === 1) await gate;
    await route.fulfill({ json: SPATIAL }).catch(() => {});
  });
  await page.goto("/");
  await page.clock.install();
  await page.locator("#commercial-address").fill(ADDRESS);
  const caseId = await clickStart(page);
  await expect.poll(() => calls.resolve.length).toBe(1);
  const before = await stored(page);
  await expect(page.getByTestId("location-find")).toBeDisabled();
  await page.clock.fastForward(10_001);
  const failure = page.getByTestId("location-confirmation-failure");
  await expect(failure).toHaveAttribute("data-reason", "unavailable");
  await expect(failure).toHaveText(locationConfirmationCopy["zh-TW"].unavailable);
  await expect(page.getByTestId("location-find")).toHaveCount(0);
  await expect(page.getByTestId("location-candidate")).toHaveCount(0);
  expect(await stored(page)).toEqual(before);
  expect(before[0].data.journeyContext.propertyContext.addressSummary).toBe(ADDRESS);
  expect(before[0].data.propertyIdentityAnchor).toBeUndefined();
  release();
  await page.clock.fastForward(30_000);
  await expect(failure).toBeVisible();
  expect(calls.resolve).toHaveLength(1);
  await page.getByRole("button", { name: locationConfirmationCopy["zh-TW"].retry, exact: true }).click();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  expect(calls.resolve).toHaveLength(2);
  // Only the fresh explicit retry result is saved, and only as unconfirmed UI data.
  const pending = (await stored(page))[0];
  expect(pending.data.pendingLocationCandidate).toMatchObject({ state: "unconfirmed", caseId, candidate: { addressInput: ADDRESS } });
  expect(pending.data.propertyIdentityAnchor).toBeUndefined();
  for (const path of [`/cases/${caseId}/overview`, `/cases/${caseId}/risk`, `/cases/${caseId}/report`, "/compare", `/cases/${caseId}/location`]) {
    await page.goto(path);
  }
  await page.reload();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  await expect(page.getByTestId("location-find")).toHaveCount(0);
  expect(await stored(page)).toEqual([pending]);
  expect(calls.resolve).toHaveLength(2);
  expect(calls.other).toEqual([]);
});

async function prepare(page: Page, respond: (route: Route) => Promise<void> = (route) => route.fulfill({ json: SPATIAL })) {
  await page.addInitScript((key) => {
    if (!sessionStorage.getItem("home-location-seeded")) {
      sessionStorage.setItem("home-location-seeded", "1");
      localStorage.setItem(key, "[]");
    }
  }, KEY);
  const calls = { resolve: [] as unknown[], other: [] as string[], demographics: [] as string[], nearby: [] as NearbyCall[] };
  await routeNearby(page, calls.nearby);
  page.on("request", (request) => {
    const url = new URL(request.url());
    // The internal village demographics read and the Nearby read are counted on their own; `other` stays the Google/Places/provider boundary.
    if (BASEMAP.test(url.hostname) || url.pathname.endsWith("/location/resolve") || url.pathname.endsWith("/demographics/location") || isNearbyRequest(url)) return;
    if (isProviderRequest(request, url.hostname === "127.0.0.1" ? url.origin : "http://127.0.0.1")) calls.other.push(url.pathname);
  });
  await page.route((url) => BASEMAP.test(url.hostname), (route) => route.fulfill({ contentType: "image/png", body: PNG }));
  await page.route("**/location/resolve", async (route) => { calls.resolve.push(route.request().postDataJSON()); await respond(route); });
  await page.route("**/demographics/location?*", async (route) => {
    const url = new URL(route.request().url());
    const [latitude, longitude] = [Number(url.searchParams.get("latitude")), Number(url.searchParams.get("longitude"))];
    calls.demographics.push(`${latitude},${longitude}`);
    await route.fulfill({ json: { latitude, longitude, checked_at: "2026-10-20T08:00:00+00:00", village_resolution: { status: "unresolved", county: null, town: null, village: null, village_code: null, district_code: null, source: "nlsc_village_boundary", source_vintage: null, reason: "zero_polygon" }, demographics: { status: "no_data", reason: "village_identity_not_resolved" } } });
  });
  return calls;
}

async function clickStart(page: Page, locale: keyof typeof START = "zh-TW") {
  const button = page.getByRole("button", { name: START[locale], exact: true });
  await button.scrollIntoViewIfNeeded();
  const box = (await button.boundingBox())!;
  const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  expect(await button.evaluate((element, point) => element.contains(document.elementFromPoint(point.x, point.y)), center)).toBe(true);
  await page.mouse.click(center.x, center.y);
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  return new URL(page.url()).pathname.split("/")[2];
}

for (const width of [1280, 390]) test(`real pointer and keyboard keep Home address editable at ${width}px`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  let revealPhoto!: () => void;
  const photoGate = new Promise<void>((resolve) => { revealPhoto = resolve; });
  await page.route(/\/brand\/home\/home-hero-taipei-/, async (route) => { await photoGate; await route.continue(); });
  const calls = await prepare(page);
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const input = page.locator("#commercial-address");
  await input.scrollIntoViewIfNeeded();
  const box = (await input.boundingBox())!;
  const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  expect(await page.evaluate(({ x, y }) => document.elementFromPoint(x, y)?.id, center)).toBe("commercial-address");
  await input.evaluate((element) => {
    const field = element as HTMLInputElement & { focusDuringInput?: boolean[] };
    field.focusDuringInput = [];
    field.addEventListener("input", () => field.focusDuringInput!.push(document.activeElement === field));
  });
  await page.mouse.click(center.x, center.y);
  await expect(input).toBeFocused();
  for (const character of ADDRESS) {
    await page.keyboard.type(character);
    await expect(input).toBeFocused();
  }
  await expect(input).toHaveValue(ADDRESS);
  // Exercise ordinary edits too, without programmatically setting the field's value.
  await page.keyboard.press("Backspace");
  await page.keyboard.type("號");
  revealPhoto();
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[data-ambient-scene="home"]')).toHaveAttribute("data-phase", "resolve", { timeout: 15_000 });
  await expect(input).toHaveValue(ADDRESS);
  await expect(input).toBeFocused();
  expect(await input.evaluate((element) => (element as HTMLInputElement & { focusDuringInput: boolean[] }).focusDuringInput.every(Boolean))).toBe(true);
  expect(await input.evaluate((element) => getComputedStyle(element).pointerEvents)).toBe("auto");
  const decorations = page.locator('[data-ambient-scene]');
  await expect(decorations.first()).toBeAttached();
  for (const layer of await decorations.all()) expect(await layer.evaluate((element) => getComputedStyle(element).pointerEvents)).toBe("none");
  expect(calls).toEqual({ resolve: [], other: [], demographics: [], nearby: [] });
  await clickStart(page);
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  expect(calls.resolve).toEqual([{ address: ADDRESS }]);
  expect((await stored(page))[0].data.propertyIdentityAnchor).toBeUndefined();
});

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const width of [390, 430]) {
  test(`Start delivers a spatial candidate and keeps all analysis explicit in ${locale} at ${width}px`, async ({ page }) => {
    const calls = await prepare(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await page.getByTestId("locale-switcher").selectOption(locale);
    await page.waitForLoadState("networkidle");
    expect(calls).toEqual({ resolve: [], other: [], demographics: [], nearby: [] });
    await page.locator("#commercial-address").fill(ADDRESS);
    expect(calls.resolve).toHaveLength(0);
    const caseId = await clickStart(page, locale);
    const copy = locationConfirmationCopy[locale];
    const candidate = page.getByTestId("location-candidate");
    await expect(candidate).toBeVisible();
    await expect(candidate.getByRole("heading")).toHaveText(copy.candidateTitle);
    await expect(candidate.getByText(ADDRESS, { exact: true }).first()).toBeVisible();
    await expect(page.getByTestId("location-find")).toHaveCount(0);
    await expect(page.getByRole("button", { name: copy.confirm, exact: true })).toBeEnabled();
    await expect(page.getByRole("button", { name: copy.reject, exact: true })).toBeEnabled();
    expect(await candidate.innerText()).not.toMatch(/25\.037500|121\.563700|Google|TGOS/);
    const details = page.getByTestId("location-candidate-details");
    await expect(details).not.toHaveAttribute("open", "");
    await expect(details.getByText("25.037500, 121.563700", { exact: true })).toBeHidden();
    await details.getByText(copy.details, { exact: true }).click();
    await expect(details.getByText("25.037500, 121.563700", { exact: true })).toBeVisible();
    await expect(details).toContainText(copy.sourceGoogle);
    await expect(details).toContainText(copy.adminUnknown);
    await details.getByText(copy.details, { exact: true }).click();
    expect((await stored(page))[0].data.propertyIdentityAnchor).toBeUndefined();
    expect(calls.resolve).toEqual([{ address: ADDRESS }]);
    expect(calls.other).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    // A full reload clears the Home handoff. Saved pending UI must restore with no acquisition.
    await page.reload();
    await expect(page.getByTestId("location-candidate-map")).toBeVisible();
    await expect(page.getByTestId("location-confirm")).toBeEnabled();
    const pendingRow = (await stored(page))[0];
    expect(pendingRow.data.pendingLocationCandidate).toMatchObject({ state: "unconfirmed", caseId, candidate: { addressInput: ADDRESS } });
    expect(pendingRow.data.propertyIdentityAnchor).toBeUndefined();
    await page.goto("/");
    await page.locator("#commercial-address").fill(ADDRESS);
    expect(await clickStart(page, locale)).toBe(caseId);
    await expect(page.getByTestId("location-candidate")).toBeVisible();
    expect(await stored(page)).toHaveLength(1);
    const gates = identityConfirmationCopy[locale];
    await page.goto(`/cases/${caseId}/risk`);
    await expect(page.getByTestId("risk-identity-gate")).toHaveText(gates.pendingRisk);
    await expect(page.getByTestId("risk-buyer-summary").getByRole("button")).toBeDisabled();
    await page.goto(`/cases/${caseId}/report`);
    await expect(page.getByTestId("report-identity-gate")).toContainText(gates.pendingReport);
    await expect(page.getByTestId("report-controls")).toHaveCount(0);
    await page.goto(`/compare?cases=${caseId}`);
    await page.goto(`/cases/${caseId}/overview`);
    await expect(page.getByTestId("case-pulse")).toBeVisible();
    await page.getByTestId("command-palette-trigger").click();
    await expect(page.getByTestId("command-palette")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("command-palette")).toHaveCount(0);
    await page.goto(`/cases/${caseId}/location`);
    await expect(page.getByTestId("location-candidate")).toContainText(ADDRESS);
    await expect(page.getByTestId("location-confirm")).toHaveText(copy.confirm);
    await page.waitForLoadState("networkidle");
    expect(calls.resolve).toHaveLength(1);
    expect(calls.other).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole("button", { name: copy.confirm, exact: true }).click();
    await expect(page.getByTestId("location-administrative-incomplete")).toContainText(copy.adminIncomplete);
    // Confirm reads village demographics exactly once for the new anchor; an unresolved village stays explicit.
    await expect(page.getByTestId("demographics-village-unresolved")).toBeVisible();
    expect(calls.demographics).toEqual([`${SPATIAL.latitude},${SPATIAL.longitude}`]);
    const row = (await stored(page))[0];
    expect(row.data.pendingLocationCandidate).toBeUndefined();
    expect(row.data.propertyIdentityAnchor).toMatchObject({
      coordinates: { latitude: SPATIAL.latitude, longitude: SPATIAL.longitude },
      administrative_location: { city: null, district: null },
      parcel: { status: "unavailable" }, building: { status: "unavailable" },
    });
    await expect(page.getByTestId("nearby-facilities").getByRole("button").first()).toBeEnabled();
    await expect(page.getByTestId("commute-route-card").getByRole("button").first()).toBeEnabled();
    await page.goto(`/cases/${caseId}/market`);
    await expect(page.getByTestId("market-refresh-button")).toBeDisabled();
    await expect(page.getByTestId("market-administrative-unavailable")).toContainText(copy.adminIncomplete);
    await page.goto(`/cases/${caseId}/location`);
    await page.reload();
    await expect(page.getByTestId("location-confirmation")).toHaveCount(0);
    await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(calls.resolve).toHaveLength(1);
    expect(calls.other).toEqual([]);
    // Market detour, reopen and reload read the saved state only.
    expect(calls.demographics).toHaveLength(1);
    await expect(page.getByTestId("demographics-village-unresolved")).toBeVisible();
    expect(calls.nearby).toEqual([expect.objectContaining({ lat: SPATIAL.latitude, lng: SPATIAL.longitude })]);
    expect((await stored(page))[0].data.propertyIdentityAnchor).toEqual(row.data.propertyIdentityAnchor);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const status of [429, 503]) {
  test(`Start ${status} keeps the case and offers one friendly retry in ${locale}`, async ({ page }) => {
    let attempts = 0;
    const calls = await prepare(page, (route) => ++attempts === 1 ? route.fulfill({ status, json: { detail: "unavailable" } }) : route.fulfill({ json: SPATIAL }));
    await page.setViewportSize({ width: status === 429 ? 390 : 430, height: 900 });
    await page.goto("/");
    await page.getByTestId("locale-switcher").selectOption(locale);
    await page.locator("#commercial-address").fill(ADDRESS);
    const caseId = await clickStart(page, locale);
    const copy = locationConfirmationCopy[locale];
    const reason = status === 429 ? "capacity_unavailable" : "provider_unavailable";
    await expect(page.getByTestId("location-confirmation-failure")).toHaveAttribute("data-reason", reason);
    await expect(page.getByTestId("location-confirmation-failure")).toHaveText(copy[reason]);
    await expect(page.getByTestId("location-confirmation").getByRole("button")).toHaveCount(1);
    expect(await page.getByTestId("location-confirmation").innerText()).not.toMatch(/沒有可用容量|available capacity|処理容量|처리 용량/);
    expect((await stored(page))[0].id).toBe(caseId);
    expect((await stored(page))[0].data.propertyIdentityAnchor).toBeUndefined();
    expect(calls.resolve).toHaveLength(1);
    await page.getByRole("button", { name: copy.retry, exact: true }).click();
    await expect(page.getByTestId("location-candidate")).toBeVisible();
    expect(calls.resolve).toHaveLength(2);
    expect((await stored(page))).toHaveLength(1);
    expect(calls.other).toEqual([]);
    await page.goto(`/cases/${caseId}/overview`);
    await page.goto(`/cases/${caseId}/location`);
    await expect(page.getByTestId("location-candidate")).toBeVisible();
    expect(calls.resolve).toHaveLength(2);
    await page.reload();
    await expect(page.getByTestId("location-candidate")).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(calls.resolve).toHaveLength(2);
  });
}

for (const mode of ["double click", "repeated submit"]) test(`${mode} and slow lookup create one case and one acquisition`, async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const calls = await prepare(page, async (route) => { await gate; await route.fulfill({ json: { ...SPATIAL, county: "臺北市", district: "信義區" } }); });
  await page.goto("/");
  await page.locator("#commercial-address").fill(ADDRESS);
  if (mode === "double click") {
    const button = page.getByRole("button", { name: START["zh-TW"], exact: true });
    const box = (await button.boundingBox())!;
    await page.mouse.dblclick(box.x + box.width / 2, box.y + box.height / 2);
  } else await page.locator(".commercial-home__form").evaluate((form: HTMLFormElement) => { form.requestSubmit(); form.requestSubmit(); });
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  await expect.poll(() => calls.resolve.length).toBe(1);
  await expect(page.getByTestId("location-find")).toBeDisabled();
  expect((await stored(page))).toHaveLength(1);
  expect((await stored(page))[0].data.propertyIdentityAnchor).toBeUndefined();
  release();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  await page.getByRole("button", { name: "確認位置", exact: true }).click();
  await expect(page.getByTestId("location-confirmation")).toHaveCount(0);
  await expect.poll(() => calls.nearby.length).toBe(1);
  expect(calls.resolve).toHaveLength(1);
  expect(calls.other).toEqual([]);
});

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) test(`changed confirmed identity uses reconfirmation copy in ${locale}`, async ({ page }) => {
  const calls = await prepare(page);
  await page.goto("/");
  await page.getByTestId("locale-switcher").selectOption(locale);
  const changed = e9Case("changed-case");
  changed.data.journeyContext!.propertyContext.addressSummary = ADDRESS;
  await page.evaluate(({ key, changed }) => localStorage.setItem(key, JSON.stringify([changed])), { key: KEY, changed });
  const copy = identityConfirmationCopy[locale];
  await page.goto("/cases/changed-case/location");
  await expect(page.getByTestId("commercial-location-workspace")).toContainText(copy.reconfirmationTitle);
  await expect(page.getByTestId("location-confirm")).toHaveCount(0);
  await page.goto("/cases/changed-case/risk");
  await expect(page.getByTestId("risk-identity-gate")).toHaveText(copy.reconfirmationRisk);
  await page.goto("/cases/changed-case/report");
  await expect(page.getByTestId("report-identity-gate")).toContainText(copy.reconfirmationReport);
  await expect(page.getByTestId("report-controls")).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  expect(calls).toEqual({ resolve: [], other: [], demographics: [], nearby: [] });
});

test("pending candidate is invalidated by address edit and cannot leak into another case", async ({ page }) => {
  const calls = await prepare(page);
  await page.goto("/");
  await page.locator("#commercial-address").fill(ADDRESS);
  const caseId = await clickStart(page);
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].inputSummary.road = "已編輯的地址";
    localStorage.setItem(key, JSON.stringify(rows));
    window.dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  // The displayed journey summary did not change; the hidden address edit still invalidates local UI.
  await expect(page.getByTestId("location-candidate")).toHaveCount(0);
  await expect(page.getByTestId("location-find")).toBeVisible();
  const changedAddress = "臺中市西屯區臺灣大道三段100號";
  await page.evaluate(({ key, changedAddress }) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    const foreign = structuredClone(rows[0]); foreign.id = "foreign-case"; delete foreign.inputSummary.road;
    rows.push(foreign);
    rows[0].data.journeyContext.propertyContext.addressSummary = changedAddress;
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, changedAddress });
  await page.reload();
  await expect(page.getByTestId("location-confirmation")).toContainText(changedAddress);
  await expect(page.getByTestId("location-candidate")).toHaveCount(0);
  await page.goto("/cases/foreign-case/location");
  await expect(page.getByTestId("location-find")).toBeVisible();
  await expect(page.getByTestId("location-candidate")).toHaveCount(0);
  await page.goto(`/cases/${caseId}/location`);
  await page.waitForLoadState("networkidle");
  expect(calls.resolve).toHaveLength(1);
  expect(calls.other).toEqual([]);
});

test("hung Home lookup exits pending, preserves address and retries only on explicit intent", async ({ page }) => {
  let attempts = 0;
  const calls = await prepare(page, async (route) => {
    if (++attempts === 1) return; // Deliberately leave the first transport unresolved.
    await route.fulfill({ json: SPATIAL });
  });
  await page.goto("/");
  await page.locator("#commercial-address").fill(ADDRESS);
  const caseId = await clickStart(page);
  await expect(page.getByTestId("location-confirmation-failure")).toHaveAttribute("data-reason", "unavailable", { timeout: 15_000 });
  await expect(page.getByRole("button", { name: locationConfirmationCopy["zh-TW"].retry, exact: true })).toBeEnabled();
  expect(calls.resolve).toHaveLength(1);
  expect((await stored(page))[0].data.journeyContext.propertyContext.addressSummary).toBe(ADDRESS);
  await page.goto(`/cases/${caseId}/overview`);
  await page.goto(`/cases/${caseId}/location`);
  // A full document navigation clears the transient error; the saved address still offers an explicit lookup.
  await expect(page.getByTestId("location-find")).toBeVisible();
  expect(calls.resolve).toHaveLength(1);
  await page.getByTestId("location-find").click();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  expect(calls.resolve).toHaveLength(2);
  expect((await stored(page))[0].id).toBe(caseId);
  expect(calls.other).toEqual([]);
});
