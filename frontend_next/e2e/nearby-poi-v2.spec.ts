import { expect, test } from "./fixtures";
import type { Page, Route } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { captureNearbyFacilities } from "../lib/workspace/nearby-facilities";
import { nearbyFacilitiesCopy } from "../lib/workspace/nearby-facilities-copy";
import { NEARBY_POI_KINDS } from "../lib/workspace/nearby-poi-category";
import { isProviderRequest } from "./helpers/provider-request";

/**
 * Nearby POI V2: provider types[] → product category → localized label → marker glyph/colour → legend/filter.
 * Viewing, filtering, selecting, switching locale, Compare and Report read saved evidence only.
 */
const KEY = "proptech.savedCases.v1";
const PATH = "/cases/case-a/location";
const origin = { lat: 24.16525, lng: 120.64555 };
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const place = (id: string, name: string, types: string[], step: number, at = origin) => ({ place_id: id, name, types, lat: at.lat + (0.0012 + step * 0.0005) * Math.sin(step * 0.7), lng: at.lng + (0.0012 + step * 0.0005) * Math.cos(step * 0.7), source: "google_places" });
// Provider display names stay as returned; nothing is translated by the product.
const response = (at = origin, prefix = "") => ({
  center: at, radius_m: 800, source: "google_places", checked_at: "2026-10-20T03:00:00Z", partial: false,
  categories: [
    { category: "transport", source: "google_places", places: [place("mrt", `${prefix}捷運市政府站`, ["subway_station", "transit_station"], 1, at), place("bus", `${prefix}Bus Stop Wenhua Rd`, ["bus_stop", "transit_station"], 2, at), place("hub", `${prefix}転運站`, ["transit_station"], 3, at)] },
    { category: "shopping", source: "google_places", places: [place("store", `${prefix}7-ELEVEN 市府門市`, ["convenience_store", "store"], 4, at)] },
    { category: "food", source: "google_places", places: [place("food", `${prefix}Noodle House`, ["restaurant", "food"], 5, at), place("bakery", `${prefix}Corner Bakery`, ["bakery", "store"], 6, at)] },
    { category: "school", source: "google_places", places: [place("school", `${prefix}Civic Primary School`, ["primary_school", "school"], 7, at)] },
    { category: "medical", source: "google_places", places: [place("clinic", `${prefix}家庭醫學科診所`, ["doctor", "health"], 8, at)] },
    { category: "park", source: "google_places", places: [place("park", `${prefix}市民廣場公園`, ["park"], 9, at)] },
  ],
});
const RAW = /[a-z]+_[a-z]+/;
const RAW_IDS = ["rail", "bus", "transit", "education", "medical", "park", "shopping", "food", "other", "healthcare", "parks", "transport", "school"];

async function prepare(page: Page, options: { persisted?: boolean; respond?: (route: Route) => Promise<void> } = {}) {
  const saved = e9Case();
  if (options.persisted !== false) saved.data.nearbyFacilities = captureNearbyFacilities(response(), origin);
  await page.addInitScript(({ key, rows }) => {
    if (sessionStorage.getItem("poi-v2-seeded")) return;
    sessionStorage.setItem("poi-v2-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, rows: [saved, e9Case("case-b")] });
  const calls = { nearby: [] as Array<{ lat: number; lng: number }>, other: [] as string[] };
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (BASEMAP.test(url.hostname)) return;
    if (url.pathname.endsWith("/map/nearby")) calls.nearby.push(request.postDataJSON());
    else if (isProviderRequest(request, url.hostname === "127.0.0.1" ? url.origin : "http://127.0.0.1")) calls.other.push(url.pathname);
  });
  await page.route((url) => BASEMAP.test(url.hostname), (route) => route.fulfill({ contentType: "image/png", body: PNG }));
  await page.route("**/map/nearby", options.respond ?? ((route) => route.fulfill({ json: response() })));
  return calls;
}
const panel = (page: Page) => page.getByTestId("nearby-facilities");
const markers = (page: Page) => page.locator('[data-testid="nearby-marker"]');
const stored = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).find((row: { id: string }) => row.id === "case-a"), KEY);
const copy = nearbyFacilitiesCopy["zh-TW"];

test("each major category, the fallback and the property marker are distinct; no raw ids or types are visible", async ({ page }) => {
  const calls = await prepare(page);
  await page.goto(PATH);
  const legend = page.getByTestId("nearby-legend");
  await expect(legend.getByRole("listitem")).toHaveCount(1 + NEARBY_POI_KINDS.length);
  for (const label of [copy.property, copy.kindRail, copy.kindBus, copy.kindTransit, copy.education, copy.healthcare, copy.parks, copy.shopping, copy.food, copy.other]) await expect(legend).toContainText(label);
  for (const [group, names] of [["transit", ["捷運市政府站", "Bus Stop Wenhua Rd", "転運站"]], ["shopping", ["7-ELEVEN 市府門市"]], ["food", ["Noodle House"]], ["other", ["Corner Bakery"]], ["education", ["Civic Primary School"]], ["healthcare", ["家庭醫學科診所"]], ["parks", ["市民廣場公園"]]] as const) {
    for (const name of names) await expect(page.getByTestId(`nearby-group-${group}`)).toContainText(name);
  }
  await expect(panel(page).locator('li[data-kind="rail"][data-selected]')).toContainText(copy.kindRail);
  await expect(panel(page).locator('li[data-kind="bus"][data-selected]')).toContainText(copy.kindBus);
  const text = await panel(page).innerText();
  expect(text).not.toMatch(RAW);
  for (const id of RAW_IDS) await expect(panel(page).getByText(id, { exact: true })).toHaveCount(0);
  expect(JSON.stringify((await stored(page)).data.nearbyFacilities)).not.toMatch(/subway_station|bus_stop|convenience_store/);

  await panel(page).getByRole("button", { name: "顯示附近設施地圖", exact: true }).click();
  await expect(markers(page)).toHaveCount(9);
  await expect(page.locator('[data-testid="property-marker"]')).toHaveCount(1);
  const icons = await markers(page).evaluateAll((nodes) => nodes.map((node) => ({ kind: node.getAttribute("data-kind"), svg: node.innerHTML, fill: node.querySelector("circle")?.getAttribute("fill") })));
  expect(new Set(icons.map((icon) => icon.kind)).size).toBe(NEARBY_POI_KINDS.length);
  expect(new Set(icons.map((icon) => icon.fill)).size).toBe(NEARBY_POI_KINDS.length);
  // Glyphs differ too, so colour is never the only cue.
  expect(new Set(icons.map((icon) => icon.svg.replace(/fill="#[0-9a-f]{6}"/g, ""))).size).toBe(NEARBY_POI_KINDS.length);
  const property = await page.locator('[data-testid="property-marker"]').evaluate((node) => ({ html: node.innerHTML, width: node.getBoundingClientRect().width }));
  expect(property.html).toContain('rx="6"');
  expect(property.width).toBeGreaterThan((await markers(page).first().boundingBox())!.width);
  expect(icons.every((icon) => !icon.svg.includes('rx="6"'))).toBe(true);
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
  expect(calls.other).toEqual([]);
});

test("filter narrows list and map together; selected marker is marked on map and list", async ({ page }) => {
  const calls = await prepare(page);
  await page.goto(PATH);
  const filter = page.getByTestId("nearby-filter");
  await expect(filter.getByRole("button", { name: copy.filterAll, exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("nearby-filter-count")).toHaveText("顯示 9 / 9 個設施");
  // Selecting from the list is an explicit ask to see the map.
  await page.getByTestId("nearby-group-transit").locator('li[data-kind="bus"]').getByRole("button", { name: copy.locate, exact: true }).click();
  await expect(markers(page)).toHaveCount(9);
  await expect(page.locator('[data-testid="nearby-marker"][data-selected="true"]')).toHaveAttribute("data-kind", "bus");
  await expect(page.locator('li[data-selected="true"]')).toContainText("Bus Stop Wenhua Rd");
  await expect(page.locator('li[data-selected="true"]').getByRole("button")).toHaveAttribute("aria-pressed", "true");
  const sizes = await markers(page).evaluateAll((nodes) => nodes.map((node) => [node.getAttribute("data-selected"), node.getBoundingClientRect().width]));
  expect(Math.min(...sizes.filter(([s]) => s === "true").map(([, w]) => w as number))).toBeGreaterThan(Math.max(...sizes.filter(([s]) => s === "false").map(([, w]) => w as number)));

  await filter.getByRole("button", { name: `${copy.transit} · 3`, exact: true }).click();
  await expect(filter.getByRole("button", { name: `${copy.transit} · 3`, exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("nearby-filter-count")).toHaveText("顯示 3 / 9 個設施");
  await expect(markers(page)).toHaveCount(3);
  await expect(panel(page).locator("li[data-selected]")).toHaveCount(3);
  await expect(page.getByTestId("nearby-group-parks")).toHaveCount(0);
  // Selection survives a filter that still contains it, and moves when a marker is clicked.
  await expect(page.locator('[data-testid="nearby-marker"][data-selected="true"]')).toHaveAttribute("data-kind", "bus");
  await page.locator('[data-testid="nearby-marker"][data-kind="rail"]').click();
  await expect(page.locator('[data-testid="nearby-marker"][data-selected="true"]')).toHaveAttribute("data-kind", "rail");
  await expect(page.locator('li[data-selected="true"]')).toContainText("捷運市政府站");
  // A filter that excludes the selection clears it.
  await filter.getByRole("button", { name: `${copy.parks} · 1`, exact: true }).click();
  await expect(markers(page)).toHaveCount(1);
  await expect(page.locator('[data-testid="nearby-marker"][data-selected="true"]')).toHaveCount(0);
  await filter.getByRole("button", { name: copy.filterAll, exact: true }).click();
  await expect(markers(page)).toHaveCount(9);
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
  expect(calls.other).toEqual([]);
});

test("reopen, Report, Compare and locale switches never query Nearby", async ({ page }) => {
  const calls = await prepare(page);
  await page.goto(PATH);
  await expect(panel(page)).toContainText("捷運市政府站");
  for (const locale of ["en", "ja", "ko", "zh-TW"] as const) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByTestId("nearby-legend")).toContainText(nearbyFacilitiesCopy[locale].kindRail);
  }
  await page.goto("/cases/case-a/report");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeAttached();
  await page.goto(PATH);
  await page.reload();
  await expect(panel(page)).toContainText("Civic Primary School");
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
  expect(calls.other).toEqual([]);
});

for (const [width, height] of [[390, 844], [430, 932], [1024, 768], [1440, 900]] as const) test(`${width}px: legend, filter, list and map localize in four locales without overflow`, async ({ page }) => {
  const calls = await prepare(page);
  await page.setViewportSize({ width, height });
  await page.goto(PATH);
  await panel(page).getByRole("button", { name: "顯示附近設施地圖", exact: true }).click();
  await expect(markers(page)).toHaveCount(9);
  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    const c = nearbyFacilitiesCopy[locale];
    await page.getByTestId("locale-switcher").selectOption(locale);
    const legend = page.getByTestId("nearby-legend");
    for (const label of [c.property, c.kindRail, c.kindBus, c.kindTransit, c.education, c.healthcare, c.parks, c.shopping, c.food, c.other]) await expect(legend).toContainText(label);
    const filter = page.getByTestId("nearby-filter");
    await expect(filter.getByRole("button", { name: c.filterAll, exact: true })).toBeVisible();
    await expect(filter).toHaveAttribute("aria-label", c.filter);
    await expect(legend).toHaveAttribute("aria-label", c.legend);
    // Provider names are unchanged in every locale.
    await expect(panel(page)).toContainText("家庭醫學科診所");
    await expect(panel(page)).toContainText("Noodle House");
    for (const control of await filter.getByRole("button").all()) {
      const box = (await control.boundingBox())!;
      expect(box.height).toBeGreaterThanOrEqual(44);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await panel(page).evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    if (locale === "en" || locale === "ko") {
      const chrome = [await legend.innerText(), await filter.innerText(), await page.getByTestId("nearby-filter-count").innerText()].join(" ");
      expect(chrome).not.toMatch(/[一-鿿]/);
    }
  }
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
  expect(calls.other).toEqual([]);
});

test("a stale Address A response cannot overwrite Address B", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const B = { lat: 24.17, lng: 120.65 };
  const calls = await prepare(page, { persisted: false, respond: async (route) => {
    const body = route.request().postDataJSON();
    if (body.lat === origin.lat) { await gate; await route.fulfill({ json: response(origin, "A ") }); }
    else await route.fulfill({ json: response(B, "B ") });
  } });
  await page.goto(PATH);
  await panel(page).getByRole("button", { name: copy.explore, exact: true }).click();
  await expect.poll(() => calls.nearby.length).toBe(1);
  // Elsewhere the case is re-confirmed at Address B while A is still in flight.
  await page.evaluate(({ key, B }) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    const anchor = rows[0].data.propertyIdentityAnchor;
    rows[0].data.propertyIdentityAnchor = { ...anchor, journey_anchor_id: "journey-browser-bbbbbbbb-2222-4333-8444-555555555555", coordinates: { latitude: B.lat, longitude: B.lng } };
    rows[0].updatedAt = "2026-10-21T00:00:00.000Z";
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, B });
  release();
  await expect(panel(page)).toContainText(copy.unsaved);
  expect((await stored(page)).data.nearbyFacilities).toBeUndefined();
  await page.reload();
  await expect(panel(page)).not.toContainText("A 捷運市政府站");
  await panel(page).getByRole("button", { name: copy.explore, exact: true }).click();
  await expect(panel(page)).toContainText("B 捷運市政府站");
  expect(calls.nearby).toHaveLength(2);
  expect(calls.nearby[1]).toMatchObject(B);
  const saved = (await stored(page)).data.nearbyFacilities;
  expect(saved.origin).toEqual(B);
  expect(JSON.stringify(saved)).not.toContain("A 捷運");
  await page.reload();
  await expect(panel(page)).toContainText("B 捷運市政府站");
  await expect(panel(page)).not.toContainText("A 捷運市政府站");
  expect(calls.nearby).toHaveLength(2);
});
