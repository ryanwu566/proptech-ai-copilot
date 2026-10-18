import { expect, test } from "./fixtures";
import type { Page, Request } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

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

async function startCase(page: Page) {
  await page.goto("/");
  await expect(page.locator(".commercial-home [data-page-heading]")).toBeFocused();
  await page.getByRole("textbox", { name: "物件地址", exact: true }).fill(ADDRESS);
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  return decodeURIComponent(new URL(page.url()).pathname.split("/")[2]);
}

test("Home → Find → Confirm unlocks identity-gated actions with exactly one geocode and no enrichment", async ({ page }) => {
  const calls = await prepare(page, [e9Case()]);
  await page.goto("/");
  record(page, calls);
  const caseId = await startCase(page);
  const panel = page.getByTestId("location-confirmation");
  await expect(panel).toBeVisible();
  await page.waitForLoadState("networkidle");
  // A + B + C: Home start, opening the case and rendering Location run nothing.
  expect(calls).toEqual({ provider: [], resolve: 0, basemap: 0 });

  // D + E: Find runs exactly one geocode-only resolve and persists nothing.
  const before = JSON.stringify(await stored(page));
  const find = panel.getByRole("button", { name: "尋找這個地址", exact: true });
  await find.dblclick();
  const candidate = page.getByTestId("location-candidate");
  await expect(candidate).toBeFocused();
  await expect(candidate).toContainText("臺北市信義區市府路1號");
  await expect(candidate).toContainText("臺北市 · 信義區");
  await expect(candidate).toContainText("25.037500, 121.563700");
  await expect(candidate).toContainText("TGOS 地址解析");
  await page.waitForLoadState("networkidle");
  expect(calls.resolve).toBe(1);
  expect(calls.provider).toEqual([]);
  expect(JSON.stringify(await stored(page))).toBe(before);

  // F: Confirm persists identity only and runs no provider.
  await candidate.getByRole("button", { name: "確認這是此物件", exact: true }).click();
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
  await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toContainText("25.037500, 121.563700");
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
  ["provider unavailable", (route) => route.fulfill({ status: 503, json: { detail: "unavailable" } }), "unavailable", "暫時無法使用"],
  ["missing district", (route) => route.fulfill({ json: { ...RESOLVED, district: null } }), "missing_area", "缺少縣市或行政區"],
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
    await page.getByRole("button", { name: "尋找這個地址", exact: true }).click();
    const failure = page.getByTestId("location-confirmation-failure");
    await expect(failure).toHaveAttribute("data-reason", reason);
    await expect(failure).toContainText(text);
    await expect(page.getByRole("button", { name: "確認這是此物件", exact: true })).toHaveCount(0);
    expect(JSON.stringify(await stored(page))).toBe(before);
    expect((await stored(page)).find((row) => row.id === caseId)!.data.propertyIdentityAnchor).toBeUndefined();
    expect(calls.resolve).toBe(1);
    expect(calls.provider).toEqual([]);
  });
}

test("rejecting the interpreted location returns to Find without saving", async ({ page }) => {
  const calls = await prepare(page);
  await page.goto("/");
  await startCase(page);
  const before = JSON.stringify(await stored(page));
  await page.getByRole("button", { name: "尋找這個地址", exact: true }).click();
  await page.getByRole("button", { name: "不是這個位置", exact: true }).click();
  await expect(page.getByRole("button", { name: "尋找這個地址", exact: true })).toBeVisible();
  expect(JSON.stringify(await stored(page))).toBe(before);
  expect(calls.resolve).toBe(1);
});

test("a case changed elsewhere after Find is not overwritten by Confirm", async ({ page }) => {
  await prepare(page);
  await page.goto("/");
  const caseId = await startCase(page);
  await page.getByRole("button", { name: "尋找這個地址", exact: true }).click();
  await expect(page.getByTestId("location-candidate")).toBeVisible();
  // Another tab edits the case without firing an event in this tab.
  const changed = await page.evaluate(({ key, caseId }) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows.find((row: { id: string }) => row.id === caseId).updatedAt = "2026-10-18T09:59:59.000Z";
    localStorage.setItem(key, JSON.stringify(rows));
    return localStorage.getItem(key);
  }, { key: KEY, caseId });
  await page.getByRole("button", { name: "確認這是此物件", exact: true }).click();
  await expect(page.getByTestId("location-confirmation-failure")).toHaveAttribute("data-reason", "case_changed");
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBe(changed);
});

for (const [locale, find, confirm] of [["en", "Find this address", "Confirm this is the property"], ["ja", "この住所を検索", "この物件で確定する"], ["ko", "이 주소 찾기", "이 부동산이 맞습니다"]] as const) {
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
    await page.getByRole("button", { name: "尋找這個地址", exact: true }).click();
    const confirm = page.getByRole("button", { name: "確認這是此物件", exact: true });
    await confirm.scrollIntoViewIfNeeded();
    expect((await confirm.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
