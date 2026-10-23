import { expect, test } from "./fixtures";
import type { Page, Route } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { captureNearbyFacilities, NEARBY_CATEGORIES } from "../lib/workspace/nearby-facilities";
import { isProviderRequest } from "./helpers/provider-request";

const KEY = "proptech.savedCases.v1";
const origin = { lat: 24.16525, lng: 120.64555 };
const PATH = "/cases/case-a/location";
const response = {
  center: origin, radius_m: 800, source: "google_places", checked_at: "2026-10-20T03:00:00Z", partial: false,
  categories: NEARBY_CATEGORIES.map((category, i) => ({ category, source: "google_places", places: [{ place_id: category, name: `Facility ${category}`, lat: origin.lat + (i + 1) * 0.0001, lng: origin.lng, source: "google_places", distance_m: 99999, rating: 4.9 }] })),
};
const BASEMAP = /(^|\.)tile\.openstreetmap\.org$|(^|\.)basemaps\.cartocdn\.com$|(^|\.)arcgisonline\.com$/;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");

async function prepare(page: Page, options: { persisted?: boolean; respond?: (route: Route) => Promise<void>; mutate?: (saved: ReturnType<typeof e9Case>) => void } = {}) {
  const saved = e9Case();
  if (options.persisted) saved.data.nearbyFacilities = captureNearbyFacilities(response, origin);
  options.mutate?.(saved);
  await page.addInitScript(({ key, rows }) => {
    if (sessionStorage.getItem("nearby-seeded")) return;
    sessionStorage.setItem("nearby-seeded", "1");
    localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, rows: [saved, e9Case("case-b")] });
  const calls: { nearby: unknown[]; other: string[] } = { nearby: [], other: [] };
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (BASEMAP.test(url.hostname)) return;
    if (url.pathname.endsWith("/map/nearby")) calls.nearby.push(request.postDataJSON());
    else if (isProviderRequest(request, url.hostname === "127.0.0.1" ? url.origin : "http://127.0.0.1")) calls.other.push(url.pathname);
  });
  await page.route((url) => BASEMAP.test(url.hostname), (route) => route.fulfill({ contentType: "image/png", body: PNG }));
  await page.route("**/map/nearby", options.respond ?? ((route) => route.fulfill({ json: response })));
  return calls;
}
const panel = (page: Page) => page.getByTestId("nearby-facilities");
const stored = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).find((row: { id: string }) => row.id === "case-a"), KEY);

test("open and pre-CTA are zero calls; double click acquires once, persists, and all later reads are free", async ({ page }) => {
  let release!: () => void;
  const deferred = new Promise<void>((resolve) => { release = resolve; });
  const calls = await prepare(page, { respond: async (route) => { await deferred; await route.fulfill({ json: response }); } });
  await page.goto(PATH);
  await expect(page.getByText("需要時再查詢附近設施；不會在開啟案件時自動呼叫外部服務。", { exact: true })).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
  const cta = panel(page).getByRole("button", { name: "查附近生活機能", exact: true });
  await cta.evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await expect(panel(page).getByRole("button", { name: "正在查詢附近設施…", exact: true })).toBeDisabled();
  await expect.poll(() => calls.nearby.length).toBe(1);
  release();
  await expect(panel(page)).toContainText("已保存設施證據");
  expect(calls.nearby).toEqual([{ ...origin, radius_m: 800, categories: [...NEARBY_CATEGORIES], language_code: "zh-TW" }]);
  await expect(page.getByTestId("nearby-group-convenience")).toContainText("Facility shopping");
  await expect(page.getByTestId("nearby-group-convenience")).toContainText("Facility food");
  for (const group of ["transit", "education", "healthcare", "parks"]) await expect(page.getByTestId(`nearby-group-${group}`)).toBeVisible();
  await expect(panel(page)).toContainText("11 m（直線）");
  await expect(panel(page)).not.toContainText("99999");
  const before = (await stored(page)).data.nearbyFacilities;
  expect(before.places).toHaveLength(6);
  expect(JSON.stringify(before)).not.toContain("rating");
  // Snapshot save must preserve the bounded details as well as the original identity.
  await page.getByRole("button", { name: "保存目前案件快照", exact: true }).click();
  await expect(page.getByTestId("context-save-status")).toContainText("已保存");
  expect((await stored(page)).data.nearbyFacilities).toEqual(before);
  for (const section of ["overview", "market", "risk", "finance", "report", "location"]) {
    await page.goto(`/cases/case-a/${section}`);
    await expect(page.locator("h1").first()).toBeVisible();
  }
  await expect(panel(page)).toContainText("Facility school");
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeAttached();
  await page.goto(PATH);
  await page.reload();
  await expect(panel(page)).toContainText("Facility medical");
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toHaveLength(1);
  expect(calls.other).toEqual([]);
});

test("existing saved results render without fetch; refresh requires another explicit click", async ({ page }) => {
  const calls = await prepare(page, { persisted: true });
  await page.goto(PATH);
  await expect(panel(page)).toContainText("Facility transport");
  expect(await panel(page).getAttribute("data-evidence-key")).toBeNull();
  await expect(page.getByText("完整設施明細未隨案件保存", { exact: true })).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
  await panel(page).getByRole("button", { name: "重新查詢附近設施", exact: true }).click();
  await expect(panel(page)).toContainText("已保存設施證據");
  expect(calls.nearby).toHaveLength(1);
});

for (const nearest of [undefined, []]) test(`legacy snapshot with ${nearest ? "empty" : "missing"} nearest POIs keeps its caveat without acquiring facilities`, async ({ page }) => {
  const calls = await prepare(page, { mutate: (saved) => {
    saved.data.locationInsight = {
      input: { address: saved.data.propertyIdentityAnchor!.normalized_address },
      poi_summary: { transit_count: 2, convenience_count: 3, school_count: null, park_count: 1, medical_count: null, risk_facility_count: null },
      nearest_pois: nearest,
      data_quality: { status: "limited", missing_sources: [], warnings: [] },
    } as never;
  } });
  await page.goto(PATH);
  const evidence = page.locator('[data-evidence-key="location"]');
  await expect(evidence).toHaveCount(1);
  await expect(evidence).toContainText("完整設施明細未隨案件保存");
  await expect(evidence).toContainText("請勿由摘要重建或推測個別設施");
  await expect(panel(page).getByRole("listitem")).toHaveCount(0);
  await expect(panel(page).getByRole("button", { name: "查附近生活機能", exact: true })).toBeEnabled();
  const before = await stored(page);
  await page.reload();
  await expect(evidence).toHaveCount(1);
  await expect(evidence).toContainText("完整設施明細未隨案件保存");
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
  expect(await stored(page)).toEqual(before);
});

test("leaving during an unfinished request never auto-retries on reopening", async ({ page }) => {
  let release!: () => void;
  const deferred = new Promise<void>((resolve) => { release = resolve; });
  const calls = await prepare(page, { respond: async (route) => { await deferred; await route.fulfill({ json: response }); } });
  await page.goto(PATH);
  await panel(page).getByRole("button", { name: "查附近生活機能", exact: true }).click();
  await expect.poll(() => calls.nearby.length).toBe(1);
  await page.locator(".workspace-navigation").getByRole("link", { name: "物件總覽", exact: true }).click();
  await expect(page).toHaveURL(/\/overview$/);
  await expect(panel(page)).toHaveCount(0);
  release();
  // The explicit acquisition owns persistence even after its panel unmounts.
  // Its successful saved result changes the manual action from Explore to Refresh.
  await expect.poll(async () => (await stored(page)).data.nearbyFacilities?.places.length).toBe(6);
  await page.locator(".workspace-navigation").getByRole("link", { name: "區位與通勤", exact: true }).click();
  const refresh = panel(page).getByRole("button", { name: "重新查詢附近設施", exact: true });
  await expect(panel(page)).toContainText("Facility school");
  await expect(refresh).toBeVisible();
  await expect(refresh).toBeEnabled();
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toHaveLength(1);
  expect(calls.other).toEqual([]);
  await refresh.click();
  await expect(panel(page)).toContainText("Facility school");
  await expect.poll(() => calls.nearby.length).toBe(2);
  expect(calls.other).toEqual([]);
});

test("leaving before a failed request keeps an explicit Explore action on reopening", async ({ page }) => {
  let release!: () => void;
  const deferred = new Promise<void>(resolve => { release = resolve; });
  let attempt = 0;
  const calls = await prepare(page, { respond: async route => {
    if (++attempt === 1) { await deferred; await route.fulfill({ status: 503, json: {} }); }
    else await route.fulfill({ json: response });
  } });
  await page.goto(PATH);
  await panel(page).getByRole("button", { name: "查附近生活機能", exact: true }).click();
  await expect.poll(() => calls.nearby.length).toBe(1);
  await page.locator(".workspace-navigation").getByRole("link", { name: "物件總覽", exact: true }).click();
  await expect(page).toHaveURL(/\/overview$/);
  await expect(panel(page)).toHaveCount(0);
  release();
  await page.locator(".workspace-navigation").getByRole("link", { name: "區位與通勤", exact: true }).click();
  const explore = panel(page).getByRole("button", { name: "查附近生活機能", exact: true });
  await expect(explore).toBeEnabled();
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toHaveLength(1);
  expect((await stored(page)).data.nearbyFacilities).toBeUndefined();
  await explore.click();
  await expect(panel(page)).toContainText("Facility school");
  expect(calls.nearby).toHaveLength(2);
  expect(calls.other).toEqual([]);
});

test("a changed property hides saved facilities and blocks acquisition until confirmed", async ({ page }) => {
  const calls = await prepare(page, { persisted: true, mutate: (saved) => { saved.data.journeyContext!.propertyContext.addressSummary = "臺中市西屯區臺灣大道三段999號"; } });
  await page.goto(PATH);
  await expect(panel(page)).toContainText("請先確認物件位置");
  await expect(panel(page)).not.toContainText("Facility");
  await expect(panel(page).getByRole("button")).toBeDisabled();
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toEqual([]);
});

test("nearby acquisition preserves independently saved risk facility source and limitations", async ({ page }) => {
  const calls = await prepare(page, { mutate: (saved) => {
    saved.data.locationInsight = {
      input: { address: saved.data.propertyIdentityAnchor!.normalized_address },
      data_quality: { status: "limited", missing_sources: [], warnings: [] },
      risk_facility_evidence: { status: "no_match", count: 0, source: "Saved facility source", checked_at: "2026-10-19T01:00:00Z", reason: "successful_query", limitation: "Saved source limitation" },
    } as never;
  } });
  await page.goto(PATH);
  await expect(page.getByTestId("risk-facility-source")).toContainText("Saved facility source");
  await expect(page.locator('[data-evidence-key="location"]')).toHaveCount(1);
  await expect(page.getByText("完整設施明細未隨案件保存", { exact: true })).toBeVisible();
  await panel(page).getByRole("button", { name: "查附近生活機能", exact: true }).click();
  await expect(panel(page)).toContainText("Facility school");
  await expect(page.getByTestId("risk-facility-source")).toContainText("Saved source limitation");
  await expect(page.locator('[data-evidence-key="location"]')).toHaveCount(1);
  await expect(page.getByText("完整設施明細未隨案件保存", { exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId("risk-facility-source")).toContainText("Saved facility source");
  expect(calls.nearby).toHaveLength(1);
});

test("partial response shows only supported returned categories and retains missing context", async ({ page }) => {
  await prepare(page, { respond: (route) => route.fulfill({ json: { ...response, partial: true, failed_categories: ["medical"], categories: [response.categories[0], response.categories[4], { category: "park", places: [] }, { category: "invented", places: response.categories[0].places }] } }) });
  await page.goto(PATH);
  await panel(page).getByRole("button", { name: "查附近生活機能", exact: true }).click();
  await expect(panel(page)).toContainText("部分類別未取得完整資料");
  await expect(page.getByTestId("nearby-group-transit")).toBeVisible();
  for (const group of ["healthcare", "education", "convenience", "parks"]) await expect(page.getByTestId(`nearby-group-${group}`)).toHaveCount(0);
  await page.reload();
  await expect(panel(page)).toContainText("部分類別未取得完整資料");
});

for (const [name, result, status] of [
  ["empty", { ...response, categories: NEARBY_CATEGORIES.map((category) => ({ category, places: [] })) }, 200],
  ["malformed", {}, 200], ["unavailable", {}, 503],
  ["fallback", { ...response, source: "mock", fallback: true }, 200],
] as const) test(`${name} response is truthful and never auto-retries`, async ({ page }) => {
  const calls = await prepare(page, { respond: (route) => route.fulfill({ status, json: result }) });
  await page.goto(PATH);
  await panel(page).getByRole("button", { name: "查附近生活機能", exact: true }).click();
  await expect(panel(page)).toContainText(name === "empty" ? "這次查詢沒有可顯示" : "暫時無法取得可靠結果");
  await expect(panel(page).getByRole("listitem")).toHaveCount(0);
  await page.reload();
  await page.waitForLoadState("networkidle");
  expect(calls.nearby).toHaveLength(1);
});

test("failed explicit refresh retains the previously persisted facilities", async ({ page }) => {
  const calls = await prepare(page, { persisted: true, respond: (route) => route.fulfill({ status: 503, json: {} }) });
  await page.goto(PATH);
  const before = (await stored(page)).data.nearbyFacilities;
  await panel(page).getByRole("button", { name: "重新查詢附近設施", exact: true }).click();
  await expect(panel(page)).toContainText("暫時無法取得可靠結果");
  await expect(panel(page)).toContainText("Facility park");
  expect((await stored(page)).data.nearbyFacilities).toEqual(before);
  expect(calls.nearby).toHaveLength(1);
});

for (const [locale, title, cta] of [
  ["zh-TW", "生活機能", "查附近生活機能"], ["en", "Nearby facilities", "Explore nearby facilities"],
  ["ja", "周辺の生活施設", "周辺の生活施設を調べる"], ["ko", "주변 생활 편의시설", "주변 생활 편의시설 찾기"],
] as const) test(`${locale} nearby controls, results and limits are localized`, async ({ page }) => {
  const calls = await prepare(page);
  await page.goto(PATH);
  await page.getByTestId("locale-switcher").selectOption(locale);
  await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  await panel(page).getByRole("button", { name: cta, exact: true }).click();
  await expect(panel(page)).toContainText("Facility school");
  await expect(panel(page).getByRole("button")).toBeEnabled();
  if (locale === "en" || locale === "ko") expect(await panel(page).innerText()).not.toMatch(/[一-鿿]/);
  expect(calls.nearby).toHaveLength(1);
});

for (const [width, height] of [[390, 844], [430, 932]]) test(`${width}×${height} facility cards have no horizontal overflow`, async ({ page }) => {
  await prepare(page, { respond: (route) => route.fulfill({ json: { ...response, categories: response.categories.map((g) => ({ ...g, places: g.places.map((p) => ({ ...p, name: "LongFacilityName".repeat(20) })) })) } }) });
  await page.setViewportSize({ width, height });
  await page.goto(PATH);
  const cta = panel(page).getByRole("button", { name: "查附近生活機能", exact: true });
  await cta.scrollIntoViewIfNeeded();
  expect((await cta.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await cta.click();
  await expect(panel(page).getByRole("listitem")).toHaveCount(6);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(await panel(page).evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
});

test("case changed during acquisition is not overwritten; save retry makes no provider call", async ({ page }) => {
  let release!: () => void;
  const deferred = new Promise<void>((resolve) => { release = resolve; });
  const calls = await prepare(page, { respond: async (route) => { await deferred; await route.fulfill({ json: response }); } });
  await page.goto(PATH);
  await panel(page).getByRole("button", { name: "查附近生活機能", exact: true }).click();
  await expect.poll(() => calls.nearby.length).toBe(1);
  await page.evaluate((key) => { const rows = JSON.parse(localStorage.getItem(key)!); rows[0].title = "Changed elsewhere"; localStorage.setItem(key, JSON.stringify(rows)); }, KEY);
  release();
  await expect(panel(page)).toContainText("未能保存至案件");
  expect((await stored(page)).data.nearbyFacilities).toBeUndefined();
  await panel(page).getByRole("button", { name: "重試保存結果", exact: true }).click();
  await expect(panel(page)).toContainText("未能保存至案件");
  expect(calls.nearby).toHaveLength(1);
  expect((await stored(page)).title).toBe("Changed elsewhere");
});
