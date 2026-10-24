import fixtures from "../../tests/fixtures/location_market_google.json";
import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { isProviderRequest } from "./helpers/provider-request";
import { buildAddressDraftCase } from "../lib/workspace/case-draft";
import { buildConfirmedLocationAnchor, interpretLocationResolution } from "../lib/workspace/location-confirmation";
import { locationConfirmationCopy } from "../lib/workspace/location-confirmation-copy";
import type { SavedCase } from "../lib/case-storage";

const KEY = "proptech.savedCases.v1";
const START = { "zh-TW": "開始物件評估", en: "Start property review", ja: "物件の検討を開始", ko: "부동산 검토 시작" };
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const stored = (page: Page): Promise<SavedCase[]> => page.evaluate(key => JSON.parse(localStorage.getItem(key) ?? "[]"), KEY);

function oldCase(index = 0) {
  const fixture = fixtures[index];
  const row = buildAddressDraftCase(fixture.address, { id: "old-admin-case", now: "2026-10-20T08:00:00Z" })!;
  const result = interpretLocationResolution({ ...fixture.response, county: null, district: null }, fixture.address);
  if (result.kind !== "candidate") throw new Error("Invalid test fixture");
  row.data.propertyIdentityAnchor = buildConfirmedLocationAnchor(result.candidate, {
    now: () => "2026-10-20T08:00:00Z", idFactory: () => "11111111-2222-4333-8444-555555555555",
  })!;
  return row;
}

async function prepare(page: Page, rows: SavedCase[] = [], respond?: (address: string) => unknown) {
  await page.addInitScript(({ key, rows }) => {
    if (sessionStorage.getItem("admin-contract-seeded")) return;
    sessionStorage.setItem("admin-contract-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, rows });
  const calls = { resolve: [] as string[], other: [] as string[] };
  page.on("request", request => {
    const url = new URL(request.url());
    if (BASEMAP.test(url.hostname) || url.pathname.endsWith("/location/resolve")) return;
    if (isProviderRequest(request, url.hostname === "127.0.0.1" ? url.origin : "http://127.0.0.1")) calls.other.push(url.pathname);
  });
  await page.route(url => BASEMAP.test(url.hostname), route => route.fulfill({ contentType: "image/png", body: PNG }));
  await page.route("**/location/resolve", async route => {
    const address = route.request().postDataJSON().address;
    calls.resolve.push(address);
    const response = respond ? await respond(address) : fixtures.find((fixture: { address: string }) => fixture.address === address)?.response;
    await route.fulfill({ json: response }).catch(() => {});
  });
  return calls;
}

async function ordinaryViews(page: Page, id: string) {
  for (const view of ["overview", "market", "location", "report"]) {
    await page.goto(`/cases/${id}/${view}`);
    await page.waitForLoadState("networkidle");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.goto(`/compare?cases=${id}`);
  await page.waitForLoadState("networkidle");
}

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const width of [390, 430, 720, 1024, 1440]) {
  const index = width === 390 ? 0 : 1;
  const fixture = fixtures[index];
  test(`Home confirmation preserves ${fixture.name} administrative context in ${locale} at ${width}px`, async ({ page }) => {
    const calls = await prepare(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await page.getByTestId("locale-switcher").selectOption(locale);
    await page.locator("#commercial-address").fill(fixture.address);
    expect(calls).toEqual({ resolve: [], other: [] });
    await page.getByRole("button", { name: START[locale], exact: true }).click();
    await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
    const id = new URL(page.url()).pathname.split("/")[2];
    await expect(page.getByTestId("location-candidate")).toBeVisible();
    expect((await stored(page))[0].data.propertyIdentityAnchor).toBeUndefined();
    await page.getByTestId("location-confirm").click();
    await expect(page.getByTestId("location-confirmation")).toHaveCount(0);
    const [confirmed] = await stored(page);
    expect(confirmed.data.propertyIdentityAnchor?.administrative_location).toEqual({ city: "臺北市", district: fixture.response.district, village: null, village_code: null });
    await page.goto(`/cases/${id}/market`);
    await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
    await expect(page.getByTestId("market-administrative-unavailable")).toHaveCount(0);
    // Address-only Start has no real building facts. Preserve the separate valuation gate.
    await expect(page.getByTestId("valuation-refresh-button")).toBeDisabled();
    await page.reload();
    await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
    await page.goto("/cases");
    await page.goto(`/cases/${id}/location`);
    await ordinaryViews(page, id);
    expect((await stored(page))[0].data.propertyIdentityAnchor).toEqual(confirmed.data.propertyIdentityAnchor);
    expect(calls).toEqual({ resolve: [fixture.address], other: [] });
    // Explicitly supply facts as a saved-case update; never derive them from the geocoder.
    await page.evaluate(({ key, road }) => {
      const rows = JSON.parse(localStorage.getItem(key)!);
      rows[0].data.inputs = { ...rows[0].data.inputs, road, building_type: "住宅大樓", area_ping: 30, building_age_years: 10, floor: 5 };
      localStorage.setItem(key, JSON.stringify(rows));
    }, { key: KEY, road: index === 0 ? "市府路" : "中山南路" });
    await page.goto(`/cases/${id}/market`);
    await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
    await expect(page.getByTestId("valuation-refresh-button")).toBeEnabled();
    expect(calls).toEqual({ resolve: [fixture.address], other: [] });
  });

  test(`saved missing-admin repair requires recheck and confirmation in ${locale} at ${width}px`, async ({ page }) => {
    const original = oldCase(index);
    const calls = await prepare(page, [original]);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await page.getByTestId("locale-switcher").selectOption(locale);
    await ordinaryViews(page, original.id);
    expect(calls).toEqual({ resolve: [], other: [] });
    expect((await stored(page))[0]).toEqual(original);
    await page.goto(`/cases/${original.id}/market`);
    await expect(page.getByTestId("market-refresh-button")).toBeDisabled();
    await page.getByTestId("market-admin-repair-link").click();
    const button = page.getByTestId("administrative-area-recheck");
    await expect(button).toBeVisible();
    await expect(button).toHaveText(locationConfirmationCopy[locale].adminRecheck);
    await button.click();
    await expect(page.getByTestId("administrative-area-candidate")).toContainText(fixture.response.district);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.getByTestId("administrative-area-candidate")).toBeFocused();
    for (const control of await page.getByTestId("administrative-area-candidate").getByRole("button").all()) {
      const box = await control.boundingBox();
      expect(box && box.x >= 0 && box.x + box.width <= width && box.height >= 44).toBeTruthy();
    }
    expect((await stored(page))[0]).toEqual(original);
    expect(calls.resolve).toEqual([fixture.address]);
    // Reload discards transient repair intent and must never re-acquire or auto-save it.
    await page.reload();
    await expect(page.getByTestId("administrative-area-recheck")).toBeVisible();
    await expect(page.getByTestId("administrative-area-confirm")).toHaveCount(0);
    expect(calls.resolve).toEqual([fixture.address]);
    expect((await stored(page))[0]).toEqual(original);
    await page.getByTestId("administrative-area-recheck").click();
    await page.getByTestId("administrative-area-confirm").click();
    await expect(page.getByTestId("location-administrative-incomplete")).toHaveCount(0);
    const [repaired] = await stored(page);
    expect(repaired.data.propertyIdentityAnchor?.coordinates).toEqual(original.data.propertyIdentityAnchor!.coordinates);
    expect(repaired.data.propertyIdentityAnchor?.journey_anchor_id).toBe(original.data.propertyIdentityAnchor!.journey_anchor_id);
    expect(repaired.data.propertyIdentityAnchor?.normalized_address).toBe(original.data.propertyIdentityAnchor!.normalized_address);
    expect(repaired.data.propertyIdentityAnchor?.administrative_location).toEqual({ city: "臺北市", district: fixture.response.district, village: null, village_code: null });
    await ordinaryViews(page, original.id);
    await page.goto(`/cases/${original.id}/market`);
    await page.reload();
    await expect(page.getByTestId("market-refresh-button")).toBeEnabled();
    expect((await stored(page))[0]).toEqual(repaired);
    expect(calls).toEqual({ resolve: [fixture.address, fixture.address], other: [] });
  });
}

test("old backend, mismatched address and changed coordinates cannot repair saved identity", async ({ page }) => {
  const original = oldCase();
  const responses = [
    { ...fixtures[0].response, county: undefined, district: undefined },
    { ...fixtures[0].response, district: "中正區" },
    { ...fixtures[0].response, latitude: 25.04 },
    { ...fixtures[0].response, formatted_address: "臺北市信義區市府路2號" },
  ];
  const calls = await prepare(page, [original], () => responses.shift());
  await page.goto(`/cases/${original.id}/location`);
  for (let attempt = 0; attempt < 4; attempt++) {
    await page.getByTestId("administrative-area-recheck").click();
    await expect(page.getByTestId("administrative-area-repair-failure")).toBeVisible();
    await expect(page.getByTestId("administrative-area-confirm")).toHaveCount(0);
    expect((await stored(page))[0]).toEqual(original);
  }
  expect(calls).toEqual({ resolve: Array(4).fill(fixtures[0].address), other: [] });
});

test("concurrent saved-case changes prevent a previously reviewed administrative repair", async ({ page }) => {
  const original = oldCase();
  const calls = await prepare(page, [original]);
  await page.goto(`/cases/${original.id}/location`);
  await page.getByTestId("administrative-area-recheck").click();
  await expect(page.getByTestId("administrative-area-confirm")).toBeVisible();
  await page.evaluate(key => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].title = "Changed in another view";
    localStorage.setItem(key, JSON.stringify(rows));
  }, KEY);
  const before = await stored(page);
  await page.getByTestId("administrative-area-confirm").click();
  await expect(page.getByTestId("administrative-area-repair-failure")).toBeVisible();
  expect(await stored(page)).toEqual(before);
  expect(calls).toEqual({ resolve: [fixtures[0].address], other: [] });
});

test("repair double-click and deadline make one lookup; late success cannot save or auto-retry", async ({ page }) => {
  const original = oldCase();
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const calls = await prepare(page, [original], async () => { await gate; return fixtures[0].response; });
  await page.goto(`/cases/${original.id}/location`);
  await page.clock.install();
  await page.getByTestId("administrative-area-recheck").dblclick();
  await expect.poll(() => calls.resolve.length).toBe(1);
  await page.clock.fastForward(10_001);
  await expect(page.getByTestId("administrative-area-repair-failure")).toBeVisible();
  release();
  await page.clock.fastForward(30_000);
  await expect(page.getByTestId("administrative-area-confirm")).toHaveCount(0);
  expect((await stored(page))[0]).toEqual(original);
  await page.goto(`/cases/${original.id}/market`);
  await expect(page.getByTestId("market-refresh-button")).toBeDisabled();
  expect(calls).toEqual({ resolve: [fixtures[0].address], other: [] });
});

test("leaving Location cancels a repair confirmation queued behind a storage lock", async ({ page }) => {
  const original = oldCase();
  const calls = await prepare(page, [original]);
  await page.goto(`/cases/${original.id}/location`);
  await page.getByTestId("administrative-area-recheck").click();
  await expect(page.getByTestId("administrative-area-confirm")).toBeVisible();
  // Another tab owns the lock, so ordinary document navigation cannot release it.
  const holder = await page.context().newPage();
  await holder.route("**/__admin-lock-holder", route => route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Test lock holder</title>" }));
  await holder.goto(new URL("/__admin-lock-holder", page.url()).href);
  try {
    await holder.evaluate(key => new Promise<void>(acquired => {
      void navigator.locks.request(key, { mode: "exclusive" }, () => new Promise<void>(release => {
        (window as unknown as { releaseAdminLock: () => void }).releaseAdminLock = release;
        acquired();
      }));
    }), KEY);
    await page.getByTestId("administrative-area-confirm").click();
    await page.locator(`a[href="/cases/${original.id}/overview"]`).first().click();
    await expect(page).toHaveURL(new RegExp(`/cases/${original.id}/overview$`));
    await expect(page.getByTestId("case-pulse")).toBeVisible();
    await holder.evaluate(() => (window as unknown as { releaseAdminLock: () => void }).releaseAdminLock());
  } finally { await holder.close(); }
  await page.waitForLoadState("networkidle");
  expect((await stored(page))[0]).toEqual(original);
  await page.goto(`/cases/${original.id}/market`);
  await expect(page.getByTestId("market-refresh-button")).toBeDisabled();
  expect(calls).toEqual({ resolve: [fixtures[0].address], other: [] });
});
