import { test, expect } from "./fixtures";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { navigationCopy } from "../lib/navigation/copy";
import { workspaceNavigationCopy } from "../lib/workspace/workspace-navigation-copy";
import { openMethod } from "./helpers/commercial-navigation";

for (const width of [390, 430, 1024, 1440]) {
  test(`first-time navigation is minimal, unclipped and keyboard complete at ${width}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    const expensive: string[] = [];
    page.on("request", (request) => { if (/\/(map\/search|map\/nearby|valuation\/estimate|terrain\/analyze|market\/insight|commute\/route)/.test(request.url())) expensive.push(request.url()); });
    await page.goto("/");
    await expect(page.locator(".commercial-home [data-page-heading]")).toBeFocused();
    await expect(page.locator(".commercial-global-nav").getByRole("link", { name: "已儲存案件", exact: true })).toBeVisible();
    await expect(page.getByRole("searchbox")).toHaveCount(0);
    const summary = page.locator(".commercial-methods > summary");
    await summary.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("tour-restart")).toBeVisible();
    const panel = await page.locator(".commercial-methods__panel").boundingBox();
    expect(panel!.x).toBeGreaterThanOrEqual(0);
    expect(panel!.x + panel!.width).toBeLessThanOrEqual(width);
    await page.screenshot({ path: testInfo.outputPath("header-menu.png") });
    await page.keyboard.press("Escape");
    await expect(summary).toBeFocused();
    expect(await summary.evaluate((node) => getComputedStyle(node).outlineStyle)).not.toBe("none");
    await expect(page.locator(".commercial-methods")).not.toHaveAttribute("open", "");
    await summary.press("Shift+Tab");
    await expect(page.getByTestId("locale-switcher")).toBeFocused();
    await page.locator(".commercial-skip-link").focus();
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
  for (const locale of ["en", "ja", "ko", "zh-TW"] as const) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    const nav = page.locator(".commercial-global-nav");
    await expect(nav.getByRole("link", { name: navigationCopy[locale].cases, exact: true })).toHaveAttribute("href", "/cases");
    await expect(nav.getByRole("link", { name: navigationCopy[locale].compare, exact: true })).toHaveAttribute("href", "/compare");
    await expect(page.locator(".commercial-methods")).toHaveCount(0);
    const caseNav = page.locator(".workspace-navigation");
    await expect(caseNav.getByRole("link", { name: workspaceNavigationCopy[locale].decisionRoom, exact: true })).toHaveAttribute("href", "/cases/case-a/decision-room");
    await expect(caseNav.locator('[aria-current="page"]')).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
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
    await expect(page.locator(".workspace-navigation")).toHaveCount(1);
    await expect(page.locator(".workspace-navigation a[href='/cases/case-a/scenarios']")).toBeAttached();
    await expect(page.locator(".workspace-navigation a[href$='/planning']")).toHaveCount(0);
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
  await expect(page.getByRole("link", { name: "從地址建立案件", exact: true }).last()).toHaveAttribute("href", "/");
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
  await expect(page.locator("main").getByRole("link", { name: "從地址建立案件", exact: true })).toHaveAttribute("href", "/");
  await expect(page.locator("main").getByRole("link", { name: /^開啟/ })).toHaveCount(0);
});

test("tool deep links and browser history restore the selected tool", async ({ page }) => {
  await page.goto("/?tool=Market%20Insight%20Lite");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await openMethod(page, "房價估算");
  await expect(page).toHaveURL(/tool=.*%E6%88%BF/);
  await page.goBack();
  await expect(page).toHaveURL(/tool=Market/);
  await expect(page.getByTestId("market-insight-search-form")).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/tool=.*%E6%88%BF/);
  await expect(page.locator("#valuation-calculator")).toBeVisible();
});

test("retained legacy tool and journey URLs react to query-only navigation without a public entry", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".commercial-home .product-capabilities")).toHaveCount(0);
  await openMethod(page, "Market Insight");
  await expect(page).toHaveURL(/\?tool=Market/);
  await expect(page.getByTestId("market-insight-search-form")).toBeVisible();
  await page.locator(".commercial-global-nav").getByRole("button", { name: "首頁", exact: true }).click();
  await expect(page.locator(".commercial-home")).toBeVisible();
  await page.evaluate(() => { history.pushState(null, "", "/?workflow=property"); });
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

test("keyboard property start moves focus to the new case's Location heading", async ({ page }) => {
  await page.goto("/");
  const address = page.getByRole("textbox", { name: "物件地址", exact: true });
  await address.fill("臺中市西屯區臺灣大道三段100號");
  await address.press("Enter");
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  await expect(page.getByRole("heading", { level: 1, name: "區位與通勤" })).toBeFocused();
  await expect(page.locator(":focus")).toBeInViewport();
});

test("keyboard legacy entry moves focus into the active workflow stage", async ({ page }) => {
  await page.goto("/");
  const finder = page.locator(".commercial-home").getByRole("button", { name: /搜尋官方成交資料/ });
  await finder.focus();
  await finder.press("Enter");
  await expect(page.locator("#journey-stage-property")).toBeVisible();
  await expect.poll(() => page.evaluate(() => Boolean(document.querySelector("#journey-stage-property")?.contains(document.activeElement)))).toBe(true);
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
  const finder = page.locator(".commercial-home").getByRole("button", { name: /搜尋官方成交資料/ });
  await finder.focus();
  await finder.press("Enter");
  await expect(page).toHaveURL(/\/\?source=closure&workflow=property$/);
  await expect(page.locator("#journey-stage-heading-property")).toBeFocused();
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
    await expect(page.locator(".commercial-methods")).toHaveAttribute("open", "");
    await page.locator(".commercial-global-nav").getByRole("link", { name: "已儲存案件", exact: true }).tap();
    await expect(page).toHaveURL(/\/cases$/);
    await expect(page.locator(".commercial-methods")).toHaveCount(0);
    await page.locator("main").getByRole("link", { name: "從地址建立案件", exact: true }).tap();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator("#commercial-address")).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(requests).toEqual([]);
  });
});
