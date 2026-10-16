import { test, expect } from "./fixtures";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

for (const width of [390, 430, 1024, 1440]) {
  test(`product navigation is searchable and keyboard complete at ${width}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    const expensive: string[] = [];
    page.on("request", (request) => { if (/\/(map\/search|map\/nearby|valuation\/estimate|terrain\/analyze|market\/insight|commute\/route)/.test(request.url())) expensive.push(request.url()); });
    await page.goto("/");
    await expect(page.locator(".commercial-home [data-page-heading]")).toBeFocused();
    await expect(page.locator(".commercial-global-nav").getByRole("link", { name: "已儲存案件", exact: true })).toBeVisible();
    const summary = page.locator(".commercial-methods > summary");
    await summary.focus();
    await page.keyboard.press("Enter");
    const search = page.getByRole("searchbox", { name: "搜尋產品功能" });
    await expect(search).toBeVisible();
    await expect(page.locator(".commercial-methods").getByRole("button", { name: "Market Insight", exact: true })).toHaveAccessibleDescription("市場");
    await page.screenshot({ path: testInfo.outputPath("product-menu.png") });
    await search.fill("情境");
    await expect(page.locator(".commercial-methods").getByRole("link", { name: "情境實驗室", exact: true })).toHaveAttribute("href", "/cases?next=scenarios");
    await search.fill("區位");
    await expect(page.locator(".commercial-methods").getByRole("button", { name: /Map Insight/ })).toBeVisible();
    await search.fill("zzzz");
    await expect(page.getByRole("status").filter({ hasText: "找不到相符功能" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(summary).toBeFocused();
    expect(await summary.evaluate((node) => getComputedStyle(node).outlineStyle)).not.toBe("none");
    await expect(page.locator(".commercial-methods")).not.toHaveAttribute("open", "");
    await summary.press("Enter");
    await expect(search).toHaveValue("");
    await summary.press("Tab");
    await expect(search).toBeFocused();
    await search.press("Shift+Tab");
    await expect(summary).toBeFocused();
    await summary.press("Shift+Tab");
    await expect(page.getByTestId("locale-switcher")).toBeFocused();
    await expect(page.locator(".commercial-methods")).not.toHaveAttribute("open", "");
    await page.locator(".commercial-skip-link").focus();
    await expect(page.locator(".commercial-methods")).not.toHaveAttribute("open", "");
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(expensive).toEqual([]);
  });
}

for (const width of [390, 430, 1024, 1440]) test(`all locales retain destinations and case context at ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  await page.addInitScript((row) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row])), e9Case());
  await page.goto("/cases/case-a/scenarios?source=deep-link#main-content");
  for (const [locale, label, preferences, places] of [
    ["en", "Search product features", "Preference profile", "My Places"],
    ["ja", "製品の機能を検索", "希望条件プロフィール", "マイプレイス"],
    ["ko", "제품 기능 검색", "선호 프로필", "내 장소"],
    ["zh-TW", "搜尋產品功能", "偏好檔案", "我的地點"],
  ]) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await page.locator(".commercial-methods > summary").click();
    await expect(page.getByRole("searchbox", { name: label })).toBeVisible();
    await page.getByRole("searchbox", { name: label }).fill(preferences);
    await expect(page.locator(".commercial-methods a[href='/preferences']")).toBeVisible();
    await page.getByRole("searchbox", { name: label }).fill(places);
    await expect(page.locator(".commercial-methods a[href='/places']")).toBeVisible();
    await page.getByRole("searchbox", { name: label }).fill("");
    await expect(page.locator(".commercial-methods a[href='/cases/case-a/decision-room']")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(page).toHaveURL(/\/cases\/case-a\/scenarios\?source=deep-link#main-content$/);
  }
});

test("major case routes remain discoverable without provider requests", async ({ page }) => {
  await page.addInitScript((row) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row])), e9Case());
  const requests: string[] = [];
  await page.route("http://e2e.test/**", async (route) => { requests.push(new URL(route.request().url()).pathname); await route.abort(); });
  for (const section of ["overview", "market", "location", "risk", "finance", "scenarios", "decision-room", "commute-planner", "report"]) {
    await page.goto(`/cases/case-a/${section}`);
    await expect(page.locator("#main-content")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
    await page.locator(".commercial-methods > summary").click();
    await expect(page.locator(".commercial-methods a[href='/cases/case-a/scenarios']")).toBeVisible();
    await page.keyboard.press("Escape");
  }
  expect(requests).toEqual([]);
});

test("case chooser preserves intent and local case identity", async ({ page }) => {
  await page.addInitScript((rows) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows)), [e9Case(), e9Case("case-b")]);
  await page.goto("/cases?next=decision-room");
  await expect(page.getByTestId("case-destination-hint")).toContainText("購屋決策室");
  await expect(page.getByRole("link", { name: "開啟案件 A", exact: true })).toHaveAttribute("href", "/cases/case-a/decision-room");
  await page.getByRole("link", { name: "開啟案件 A", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/case-a\/decision-room$/);
  await expect(page.getByTestId("case-workflow-handoff").getByRole("link", { name: "比較案件", exact: true })).toHaveAttribute("href", "/compare?cases=case-a");
  await page.goto("/cases/case-a/scenarios");
  await page.getByTestId("case-workflow-handoff").getByRole("link", { name: "購屋決策室", exact: true }).click();
  await expect(page).toHaveURL(/case-a\/decision-room$/);
  await page.goto("/compare?cases=case-a%2Ccase-b");
  await expect(page.getByTestId("compare-report-handoff").getByRole("link")).toHaveCount(2);
  await page.getByTestId("compare-report-handoff").getByRole("link").first().click();
  await expect(page).toHaveURL(/case-a\/report$/);
});

test("empty chooser explains prerequisites and unsafe intent stays local", async ({ page }) => {
  await page.goto("/cases?next=scenarios");
  await expect(page.getByTestId("case-destination-hint")).toContainText("情境實驗室");
  await expect(page.getByRole("link", { name: "物件評估流程", exact: true }).last()).toHaveAttribute("href", "/?workflow=property");
  await expect(page.getByText("先開始物件評估，保存案件後即可進行情境、決策與報告。匿名探索不需登入。")).toBeVisible();
  await page.goto("/cases?next=https://evil.test");
  await expect(page.getByTestId("case-destination-hint")).toContainText("物件總覽");
});

for (const store of ["invalid", "blocked"]) test(`${store} local cases retain diagnostics and a workflow entry`, async ({ page }) => {
  await page.addInitScript((mode) => {
    if (mode === "invalid") localStorage.setItem("proptech.savedCases.v1", "broken-json");
    else {
      const read = Storage.prototype.getItem;
      Storage.prototype.getItem = function (key) { if (key === "proptech.savedCases.v1") throw new DOMException("Blocked", "SecurityError"); return read.call(this, key); };
    }
  }, store);
  await page.goto("/cases?next=scenarios");
  await expect(page.locator("main").getByRole("link", { name: "物件評估流程", exact: true })).toHaveAttribute("href", "/?workflow=property");
  await expect(page.locator("main").getByRole("link", { name: /^開啟/ })).toHaveCount(0);
});

test("tool deep links and browser history restore the selected tool", async ({ page }) => {
  await page.goto("/?tool=Market%20Insight%20Lite");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.locator(".commercial-methods > summary").click();
  await page.locator(".commercial-methods").getByRole("button", { name: "房價估算", exact: true }).click();
  await expect(page).toHaveURL(/tool=.*%E6%88%BF/);
  await page.goBack();
  await expect(page).toHaveURL(/tool=Market/);
  await expect(page.getByTestId("market-insight-search-form")).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/tool=.*%E6%88%BF/);
  await expect(page.locator("#valuation-calculator")).toBeVisible();
});

test("Home capability links and property entry react to query-only navigation", async ({ page }) => {
  await page.goto("/");
  await page.locator(".product-capabilities").getByRole("link", { name: "市場", exact: true }).click();
  await expect(page.getByTestId("market-insight-search-form")).toBeVisible();
  await page.locator(".commercial-global-nav").getByRole("button", { name: "首頁", exact: true }).click();
  await expect(page.locator(".commercial-home")).toBeVisible();
  await page.locator(".commercial-methods > summary").click();
  await page.locator(".commercial-methods").getByRole("link", { name: "物件評估流程", exact: true }).click();
  await expect(page.locator("#guided-property-journey")).toBeVisible();
  await expect(page.locator("#guided-property-journey h2").first()).toBeFocused();
  await expect(page.locator("#guided-property-journey h2").first()).toBeInViewport();
});

test("skip link reaches a missing-case recovery page", async ({ page }) => {
  await page.goto("/cases/not-saved/overview");
  await expect(page.getByRole("heading", { name: "找不到已儲存案件" })).toBeVisible();
  await page.locator(".commercial-skip-link").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
});

test("keyboard property start moves focus into the active workflow stage", async ({ page }) => {
  await page.goto("/");
  const address = page.getByRole("textbox", { name: "物件地址", exact: true });
  await address.fill("臺中市西屯區臺灣大道三段100號");
  await address.press("Enter");
  await expect(page.locator("#journey-stage-location")).toBeVisible();
  await expect.poll(() => page.evaluate(() => Boolean(document.querySelector("#journey-stage-location")?.contains(document.activeElement)))).toBe(true);
  await expect(page.locator(":focus")).toBeInViewport();
});

test("property workflow preserves history and keeps journey state out of storage", async ({ page }) => {
  const requests: string[] = [];
  await page.route("http://e2e.test/**", async (route) => { requests.push(new URL(route.request().url()).pathname); await route.abort(); });
  await page.goto("/?source=closure#original");
  await expect(page.locator(".commercial-home [data-page-heading]")).toBeFocused();
  const storage = () => page.evaluate(() => ({ local: { ...localStorage }, session: { ...sessionStorage } }));
  const beforeStorage = await storage();
  const beforeHistory = await page.evaluate(() => history.length);
  const address = page.getByRole("textbox", { name: "物件地址", exact: true });
  await address.fill("臺中市西屯區臺灣大道三段100號");
  await address.press("Enter");
  await expect(page).toHaveURL(/\/\?source=closure&workflow=property$/);
  await expect(page.locator("#journey-stage-heading-location")).toBeFocused();
  expect(await page.evaluate(() => history.length)).toBe(beforeHistory + 1);
  await page.goBack();
  await expect(page).toHaveURL(/\/\?source=closure#original$/);
  await expect(page.locator("#guided-property-journey")).not.toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/\/\?source=closure&workflow=property$/);
  await expect(page.locator("#guided-property-journey")).toBeVisible();
  await page.reload();
  await expect(page.locator("#guided-property-journey h2").first()).toBeFocused();
  await page.locator(".commercial-skip-link").focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/workflow=property#main-content$/);
  const activeHistory = await page.evaluate(() => history.length);
  await page.locator(".commercial-home").getByRole("button", { name: /搜尋官方成交資料/ }).click();
  await expect(page.locator("#journey-stage-heading-property")).toBeFocused();
  await expect(page).toHaveURL(/\/\?source=closure&workflow=property#main-content$/);
  expect(await page.evaluate(() => history.length)).toBe(activeHistory);
  expect(await storage()).toEqual(beforeStorage);
  expect(requests).toEqual([]);
});

test.describe("touch navigation", () => {
  test.use({ hasTouch: true });
  for (const width of [390, 430]) test(`tap handoffs remain usable at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const requests: string[] = [];
    await page.route("http://e2e.test/**", async (route) => { requests.push(new URL(route.request().url()).pathname); await route.abort(); });
    await page.goto("/");
    const summary = page.locator(".commercial-methods > summary");
    await summary.tap();
    await page.getByRole("searchbox", { name: "搜尋產品功能" }).fill("情境");
    await page.locator(".commercial-methods").getByRole("link", { name: "情境實驗室", exact: true }).tap();
    await expect(page).toHaveURL(/\/cases\?next=scenarios$/);
    await summary.tap();
    await expect(page.locator(".commercial-methods")).toHaveAttribute("open", "");
    await page.locator(".commercial-global-nav").getByRole("link", { name: "已儲存案件", exact: true }).tap();
    await expect(page).toHaveURL(/\/cases$/);
    await expect(page.locator(".commercial-methods")).not.toHaveAttribute("open", "");
    await page.locator("main").getByRole("link", { name: "物件評估流程", exact: true }).tap();
    await expect(page.locator("#guided-property-journey h2").first()).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(requests).toEqual([]);
  });
});
