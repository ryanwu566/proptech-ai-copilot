import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

/** Home Start saves a local case and explicitly acquires one location candidate, without analysis. */
const KEY = "proptech.savedCases.v1";
const ADDRESS = "臺北市信義區市府路1號";
const START = { "zh-TW": "開始物件評估", en: "Start property review", ja: "物件の検討を開始", ko: "부동산 검토 시작" } as const;
const ADDRESS_LABEL = { "zh-TW": "物件地址", en: "Property address", ja: "物件住所", ko: "부동산 주소" } as const;
const FAILED = { "zh-TW": "未建立案件", en: "Case not created", ja: "案件は作成されていません", ko: "사례가 생성되지 않았습니다" } as const;

async function seed(page: Page, rows: unknown[] | string | null) {
  await page.route("**/location/resolve", (route) => route.fulfill({ status: 503, json: { detail: "unavailable" } }));
  await page.addInitScript(({ key, rows }) => {
    if (sessionStorage.getItem("home-start-seeded")) return;
    sessionStorage.setItem("home-start-seeded", "1");
    if (rows === null) localStorage.removeItem(key);
    else localStorage.setItem(key, typeof rows === "string" ? rows : JSON.stringify(rows));
  }, { key: KEY, rows });
}

/** Cross-origin requests (API origin, Maps, tiles, Earth Engine) and same-origin fetch/XHR outside route payloads are provider calls. */
function recordProviders(page: Page) {
  const calls: string[] = [];
  const origin = new URL(page.url()).origin;
  page.on("request", (request) => { if (isProviderRequest(request, origin)) calls.push(`${request.method()} ${request.url()}`); });
  return calls;
}

const stored = (page: Page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "[]") as Array<{ id: string; title: string; data: Record<string, unknown>; inputSummary: Record<string, unknown> }>, KEY);
const rawStored = (page: Page) => page.evaluate((key) => localStorage.getItem(key), KEY);
const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

async function openHome(page: Page) {
  await page.goto("/");
  await expect(page.locator(".commercial-home [data-page-heading]")).toBeFocused();
}

test("address start creates one unconfirmed case, acquires one location and runs no analysis", async ({ page }) => {
  await seed(page, [e9Case(), e9Case("case-b")]);
  await openHome(page);
  const calls = recordProviders(page);
  await page.getByRole("textbox", { name: "物件地址", exact: true }).fill(ADDRESS);
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/[A-Za-z0-9_-]+\/location$/);
  const caseId = decodeURIComponent(new URL(page.url()).pathname.split("/")[2]);
  await expect(page.getByRole("heading", { level: 1, name: "區位與通勤" })).toBeFocused();
  const banner = page.getByRole("banner", { name: "目前物件" });
  await expect(banner).toContainText(ADDRESS);
  await expect(banner).toContainText("物件尚待確認");
  await expect(page.getByTestId("location-not-yet-confirmed")).toContainText("確認物件位置");
  await expect(page.getByTestId("location-not-yet-confirmed")).not.toContainText("已變更");
  await expect(page.locator("#guided-property-journey")).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  const rows = await stored(page);
  expect(rows.map((row) => row.id)).toEqual([caseId, "case-a", "case-b"]);
  const created = rows[0];
  expect(created.title).toBe(ADDRESS);
  expect(created.inputSummary).toEqual({});
  // No fabricated identity, coordinates, parcel, building, price, area or evidence.
  for (const field of ["propertyIdentityAnchor", "valuation", "marketInsight", "locationInsight", "terrainReference", "commuteRoute", "loan", "financeEvidence"]) expect(created.data[field]).toBeUndefined();
  expect(created.data.journeyContext).toMatchObject({ propertyContext: { addressSummary: ADDRESS, selectionStatus: "partial" }, priceBasis: "asking" });
  expect(JSON.stringify(created)).not.toMatch(/latitude|longitude|parcel|confirmed/);
  // No automatic analysis anywhere in the new case.
  await page.locator(".workspace-navigation").getByRole("link", { name: "物件總覽", exact: true }).click();
  await expect(page.getByTestId("commercial-overview-workspace")).toContainText("尚未查詢");
  await page.locator(".workspace-navigation").getByRole("link", { name: "價格與市場", exact: true }).click();
  await expect(page.getByTestId("market-price-workspace")).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(calls).toEqual(["POST http://e2e.test/location/resolve"]);
});

test("Back returns Home with the new case first in Recent Cases and Forward reopens it", async ({ page }) => {
  await seed(page, [e9Case()]);
  await openHome(page);
  const address = page.getByRole("textbox", { name: "物件地址", exact: true });
  await address.fill(ADDRESS);
  await address.press("Enter");
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  const casePath = new URL(page.url()).pathname;
  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  const recent = page.locator(".commercial-recent-cases li");
  await expect(recent.first()).toContainText(ADDRESS);
  await expect(recent.first()).toContainText("物件尚待確認");
  await expect(recent.nth(1)).toContainText("案件 A");
  await expect(page.locator("#guided-property-journey")).toBeHidden();
  await page.goForward();
  await expect(page).toHaveURL(new RegExp(`${casePath}$`));
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(ADDRESS);
  await page.goBack();
  await recent.first().getByRole("link").click();
  await expect(page).toHaveURL(new RegExp(`${casePath.replace(/location$/, "overview")}$`));
});

test("double click, repeated Enter and a repeat start reuse one case", async ({ page }) => {
  await seed(page, null);
  await openHome(page);
  const address = page.getByRole("textbox", { name: "物件地址", exact: true });
  await address.fill(ADDRESS);
  await page.getByRole("button", { name: "開始物件評估", exact: true }).dblclick();
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  const first = new URL(page.url()).pathname;
  expect((await stored(page)).length).toBe(1);
  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await address.fill(`  ${ADDRESS} `);
  await address.press("Enter");
  // The repeat goes to the focused field; a locator press would wait out the test once Home unmounts.
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`${first}$`));
  expect((await stored(page)).length).toBe(1);
  await page.goBack();
  await address.fill("臺中市西屯區臺灣大道三段100號");
  await address.press("Enter");
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  expect(new URL(page.url()).pathname).not.toBe(first);
  expect((await stored(page)).length).toBe(2);
});

test("storage write failure is announced, keeps existing cases and never falls back to the legacy journey", async ({ page }) => {
  await seed(page, [e9Case()]);
  await page.addInitScript(() => {
    const setItem = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key: string, value: string) {
      if (key === "proptech.savedCases.v1" && sessionStorage.getItem("home-start-seeded")) throw new DOMException("Quota exceeded", "QuotaExceededError");
      return setItem.call(this, key, value);
    };
  });
  await openHome(page);
  const before = await rawStored(page);
  const calls = recordProviders(page);
  await page.getByRole("textbox", { name: "物件地址", exact: true }).fill(ADDRESS);
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  const alert = page.getByTestId("home-start-status").getByRole("alert");
  await expect(alert).toContainText("未建立案件");
  await expect(alert).toContainText("儲存空間不足");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("#guided-property-journey")).toBeHidden();
  await expect(page.getByRole("button", { name: "開始物件評估", exact: true })).toBeEnabled();
  await expect(page.getByRole("textbox", { name: "物件地址", exact: true })).toHaveValue(ADDRESS);
  expect(await rawStored(page)).toBe(before);
  expect(calls).toEqual([]);
});

test("malformed saved storage is protected and reported instead of overwritten", async ({ page }) => {
  await seed(page, "{not-json");
  await openHome(page);
  await page.getByRole("textbox", { name: "物件地址", exact: true }).fill(ADDRESS);
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  const alert = page.getByTestId("home-start-status").getByRole("alert");
  await expect(alert).toContainText("需要修復");
  await expect(alert.getByRole("link", { name: "管理已儲存案件" })).toHaveAttribute("href", "/cases");
  expect(await rawStored(page)).toBe("{not-json");
  await expect(page).toHaveURL(/\/$/);
});

test("unavailable storage lock blocks creation explicitly", async ({ page }) => {
  await seed(page, null);
  await page.addInitScript(() => { Object.defineProperty(Navigator.prototype, "locks", { configurable: true, get: () => undefined }); });
  await openHome(page);
  await page.getByRole("textbox", { name: "物件地址", exact: true }).fill(ADDRESS);
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  await expect(page.getByTestId("home-start-status").getByRole("alert")).toContainText("無法安全協調案件儲存");
  expect(await rawStored(page)).toBeNull();
  await expect(page).toHaveURL(/\/$/);
});

test("the saved-case limit blocks a new case without evicting any existing case", async ({ page }) => {
  const full = Array.from({ length: 10 }, (_, index) => e9Case(`case-${index}`));
  await seed(page, full);
  await openHome(page);
  const before = await rawStored(page);
  await page.getByRole("textbox", { name: "物件地址", exact: true }).fill(ADDRESS);
  await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
  const alert = page.getByTestId("home-start-status").getByRole("alert");
  await expect(alert).toContainText("10 件案件上限");
  await expect(alert.getByRole("link", { name: "管理已儲存案件" })).toBeVisible();
  expect(await rawStored(page)).toBe(before);
  await expect(page).toHaveURL(/\/$/);
});

test("the explicit legacy workflow deep link still opens the guided journey", async ({ page }) => {
  await seed(page, null);
  await page.goto("/?workflow=property");
  await expect(page.locator("#guided-property-journey")).toBeVisible();
  await expect(page.locator("#journey-stage-property")).toBeVisible();
  const home = page.locator(".commercial-home");
  await home.getByRole("textbox", { name: "物件地址", exact: true }).fill(ADDRESS);
  await home.getByRole("button", { name: "開始物件評估", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
});

test("Home is a start page, not an app launcher", async ({ page }) => {
  await seed(page, [e9Case()]);
  await openHome(page);
  const home = page.locator(".commercial-home");
  await expect(home.locator(".product-capabilities")).toHaveCount(0);
  await expect(home.getByRole("heading", { level: 1 })).toHaveCount(1);
  await expect(home.getByRole("button", { name: "查看範例", exact: true })).toHaveClass(/commercial-text-action/);
  await expect(home.getByRole("link", { name: "繼續已儲存案件", exact: true })).toHaveAttribute("href", "/cases");
  await expect(home.locator(".commercial-home__trust")).toContainText("未知不代表安全");
  await expect(home.locator(".commercial-home__trust")).toContainText("明確執行");
  // Value → start → recent cases → what you get, in document order.
  const order = await page.evaluate(() => ["#commercial-home-heading", "#commercial-address", ".commercial-recent-cases", "#commercial-home-what"].map((selector) => document.querySelector(selector)!.getBoundingClientRect().top));
  expect(order).toEqual([...order].sort((a, b) => a - b));
  // Global navigation lists no capability catalogue; Home's header keeps only accessibility controls.
  await page.locator(".commercial-methods > summary").click();
  await expect(page.locator(".commercial-methods")).toHaveAttribute("open", "");
  await expect(page.locator(".commercial-methods__panel a")).toHaveCount(0);
  await expect(home.getByTestId("tour-start")).toBeVisible();
});

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
  test(`${locale} Home start is localized and reaches the case`, async ({ page }) => {
    await seed(page, null);
    await openHome(page);
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    const home = page.locator(".commercial-home");
    if (locale === "en" || locale === "ko") expect(await home.innerText()).not.toMatch(/[一-鿿]/);
    expect(await home.innerText()).not.toMatch(/homeStart\.|commercial\.\w+/);
    const address = home.getByRole("textbox", { name: ADDRESS_LABEL[locale], exact: true });
    await address.fill(ADDRESS);
    await home.getByRole("button", { name: START[locale], exact: true }).click();
    await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
    await page.goBack();
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await page.evaluate((key) => localStorage.setItem(key, "{bad"), KEY);
    await home.getByRole("textbox", { name: ADDRESS_LABEL[locale], exact: true }).fill("臺中市西屯區臺灣大道三段100號");
    await home.getByRole("button", { name: START[locale], exact: true }).click();
    await expect(page.getByTestId("home-start-status").getByRole("alert")).toContainText(FAILED[locale]);
  });
}

for (const width of [360, 390, 430, 1024, 1440]) {
  test(`Home start fits ${width}px with an obvious primary action`, async ({ page }) => {
    await seed(page, [e9Case(), e9Case("case-b")]);
    await page.setViewportSize({ width, height: width < 600 ? 780 : 900 });
    await openHome(page);
    // Layout is measured at rest: the document-load opening scales Home's start content in until its layer unmounts.
    await expect(page.locator("[data-app-entrance]")).toHaveCount(0, { timeout: 5_000 });
    expect(await noOverflow(page)).toBe(true);
    const home = page.locator(".commercial-home");
    await expect(home.getByRole("heading", { level: 1 })).toBeInViewport();
    const address = home.getByRole("textbox", { name: "物件地址", exact: true });
    const cta = home.getByRole("button", { name: "開始物件評估", exact: true });
    await expect(address).toBeInViewport();
    await expect(cta).toBeInViewport();
    const box = await cta.boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(44);
    for (const link of await home.locator(".commercial-home__secondary > *").all()) expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await expect(page.locator(".commercial-recent-cases li").first()).toContainText("案件");
    await address.fill(ADDRESS);
    await cta.click();
    await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
    expect(await noOverflow(page)).toBe(true);
  });
}
