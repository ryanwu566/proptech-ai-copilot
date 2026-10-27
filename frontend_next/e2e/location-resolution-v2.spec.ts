import { expect, test } from "./fixtures";
import type { Page, Route } from "@playwright/test";
import { buildAddressDraftCase } from "../lib/workspace/case-draft";
import { isNearbyRequest, routeNearby, type NearbyCall } from "./helpers/nearby-route";
import { isProviderRequest } from "./helpers/provider-request";

/**
 * Gate L1-1: Google-first resolution. A candidate contradicting the typed district is shown but blocked;
 * several plausible candidates require an explicit choice; only explicit Find/Search again geocodes. Only a confirmed
 * candidate acquires village demographics and Nearby, once each, for its own coordinates.
 */
const KEY = "proptech.savedCases.v1";
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");

async function prepare(page: Page, resolve: (route: Route) => Promise<void>) {
  await page.addInitScript(({ key }) => {
    if (sessionStorage.getItem("lxv2-resolve-seeded")) return;
    sessionStorage.setItem("lxv2-resolve-seeded", "1");
    localStorage.setItem(key, "[]");
  }, { key: KEY });
  const calls = { resolve: 0, other: [] as string[], demographics: [] as string[], nearby: [] as NearbyCall[] };
  await routeNearby(page, calls.nearby);
  await page.route("**/demographics/location?*", async (route) => {
    const url = new URL(route.request().url());
    calls.demographics.push(`${url.searchParams.get("latitude")},${url.searchParams.get("longitude")}`);
    await route.fulfill({ json: { latitude: Number(url.searchParams.get("latitude")), longitude: Number(url.searchParams.get("longitude")), checked_at: "2026-10-20T08:00:00+00:00", village_resolution: { status: "unresolved", reason: "no_intersection" }, demographics: { status: "unavailable", reason: "village_unresolved" } } });
  });
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (BASEMAP.test(url.hostname) || url.pathname.endsWith("/demographics/location") || isNearbyRequest(url)) return;
    if (url.pathname.endsWith("/location/resolve")) calls.resolve++;
    else if (isProviderRequest(request, url.hostname === "127.0.0.1" ? url.origin : "http://127.0.0.1")) calls.other.push(url.pathname);
  });
  await page.route((url) => BASEMAP.test(url.hostname), (route) => route.fulfill({ contentType: "image/png", body: PNG }));
  await page.route("**/location/resolve", resolve);
  return calls;
}
const stored = (page: Page, id: string) => page.evaluate(([key, id]) => JSON.parse(localStorage.getItem(key)!).find((row: { id: string }) => row.id === id), [KEY, id] as const);

const ADDRESS = "新北市新莊區中正路191號";
const blocked = { status: "unresolved", source: "none", formatted_address: null, latitude: null, longitude: null, confidence: "unknown", message: "x", county: null, district: null, postal_code: null, place_id: null, resolution_reason: "administrative_mismatch",
  candidates: [{ source: "google", formatted_address: "238台灣新北市樹林區金寮里中正路191號", latitude: 24.99, longitude: 121.42, county: "新北市", district: "樹林區", postal_code: "238", place_id: "wrong", admin_check: "district_mismatch", confirmable: false, block_reason: "administrative_mismatch" }] };
const accepted = { status: "resolved", source: "google", formatted_address: "242台灣新北市新莊區中正路191號", latitude: 25.0359, longitude: 121.4326, confidence: "high", message: "x", county: "新北市", district: "新莊區", postal_code: "242", place_id: "right", resolution_reason: "accepted",
  candidates: [{ source: "google", formatted_address: "242台灣新北市新莊區中正路191號", latitude: 25.0359, longitude: 121.4326, county: "新北市", district: "新莊區", postal_code: "242", place_id: "right", admin_check: "consistent", confirmable: true, block_reason: null }] };

async function draftCase(page: Page, address = ADDRESS) {
  await page.goto("/");
  const draft = buildAddressDraftCase(address, { id: "lxv2-draft", now: "2026-10-26T08:00:00Z" })!;
  await page.evaluate(({ key, draft }) => localStorage.setItem(key, JSON.stringify([draft, ...JSON.parse(localStorage.getItem(key) ?? "[]")])), { key: KEY, draft });
  await page.goto(`/cases/${draft.id}/location`);
}

test("wrong-district candidate is visibly blocked, cannot be confirmed, and search again geocodes explicitly", async ({ page }) => {
  let attempt = 0;
  const calls = await prepare(page, (route) => route.fulfill({ json: ++attempt === 1 ? blocked : accepted }));
  await draftCase(page);
  await page.getByTestId("location-find").click();
  await expect(page.getByTestId("location-confirmation-failure")).toHaveAttribute("data-reason", "administrative_mismatch");
  const rejected = page.getByTestId("location-rejected-option");
  await expect(rejected).toContainText("樹林區");
  await expect(rejected).toContainText("行政區不一致 · 不可確認");
  await expect(rejected).toHaveAttribute("aria-disabled", "true");
  await expect(page.getByTestId("location-confirm")).toHaveCount(0);
  expect((await stored(page, "lxv2-draft")).data.pendingLocationCandidate).toBeUndefined();
  // Downstream analysis cannot start from a blocked candidate.
  await expect(page.getByTestId("nearby-facilities").getByRole("button").first()).toBeDisabled();
  expect(calls.resolve).toBe(1);
  expect(calls.demographics).toEqual([]);
  expect(calls.nearby).toEqual([]);
  await page.getByTestId("location-confirmation").getByRole("button", { name: "重新尋找", exact: true }).click();
  await expect(page.getByTestId("location-candidate")).toContainText("242台灣新北市新莊區中正路191號");
  await page.getByTestId("location-candidate-details").locator("summary").click();
  await expect(page.getByTestId("location-candidate-details")).toContainText("242");
  await expect(page.getByTestId("location-not-legal")).toBeVisible();
  await page.getByTestId("location-confirm").click();
  await expect(page.getByTestId("location-confirmation-status")).not.toBeEmpty();
  const anchor = (await stored(page, "lxv2-draft")).data.propertyIdentityAnchor;
  expect(anchor.coordinates).toEqual({ latitude: 25.0359, longitude: 121.4326 });
  expect(calls.resolve).toBe(2);
  // Confirming the accepted candidate acquires demographics and Nearby once each, for its coordinates only.
  await expect(page.getByTestId("nearby-facilities")).toContainText("Confirmed fixture station");
  await expect.poll(() => calls.demographics).toEqual(["25.0359,121.4326"]);
  expect(calls.nearby).toEqual([expect.objectContaining({ lat: 25.0359, lng: 121.4326 })]);
  await page.reload();
  await page.waitForLoadState("networkidle");
  expect(calls.resolve).toBe(2);
  expect(calls.demographics).toHaveLength(1);
  expect(calls.nearby).toHaveLength(1);
  expect(calls.other).toEqual([]);
});

test("several plausible Google candidates require an explicit choice before confirmation", async ({ page }) => {
  const base = { source: "google", admin_check: "county_unverified", confirmable: true, block_reason: null, place_id: null };
  const ambiguous = { status: "ambiguous", source: "google", formatted_address: null, latitude: null, longitude: null, confidence: "unknown", message: "x", county: null, district: null, postal_code: null, place_id: null, resolution_reason: "multiple_candidates", candidates: [
    { ...base, formatted_address: "110台灣臺北市信義區市府路1號", latitude: 25.0375, longitude: 121.5637, county: "臺北市", district: "信義區", postal_code: "110" },
    { ...base, formatted_address: "201台灣基隆市信義區市府路1號", latitude: 25.13, longitude: 121.75, county: "基隆市", district: "信義區", postal_code: "201" },
  ] };
  const calls = await prepare(page, (route) => route.fulfill({ json: ambiguous }));
  await draftCase(page, "信義區市府路1號");
  await page.getByTestId("location-find").click();
  await expect(page.getByTestId("location-choice-option")).toHaveCount(2);
  await expect(page.getByTestId("location-confirm")).toHaveCount(0);
  await page.getByTestId("location-choice-option").nth(1).getByRole("button", { name: "選擇此位置", exact: true }).click();
  await expect(page.getByTestId("location-candidate")).toContainText("基隆市信義區市府路1號");
  await expect(page.getByTestId("location-county-unverified")).toBeVisible();
  await page.getByTestId("location-confirm").click();
  await expect.poll(async () => (await stored(page, "lxv2-draft")).data.propertyIdentityAnchor?.coordinates).toEqual({ latitude: 25.13, longitude: 121.75 });
  expect(calls.resolve).toBe(1);
  // Only the chosen candidate is enriched; the other plausible candidate never is.
  await expect.poll(() => calls.demographics).toEqual(["25.13,121.75"]);
  await expect.poll(() => calls.nearby.length).toBe(1);
  expect(calls.nearby).toEqual([expect.objectContaining({ lat: 25.13, lng: 121.75 })]);
  expect(calls.other).toEqual([]);
});
