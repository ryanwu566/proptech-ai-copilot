import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";
const KEY = "proptech.savedCases.v1";
function cases() {
  const a = e9Case(); const b = e9Case("case-b"); const c = e9Case("case-c"); const d = e9Case("case-d"); const e = e9Case("case-e");
  delete b.data.marketInsight; delete b.data.financeEvidence; delete b.data.commuteRoute;
  c.data.marketInsight!.freshness_status = "stale";
  c.data.commuteRoute!.destination.address = "高鐵臺中站";
  c.data.financeEvidence!.loan.annual_interest_rate = 2.2;
  d.data.commuteRoute!.status = "unavailable"; d.data.commuteRoute!.duration_min = null;
  d.data.propertyIdentityAnchor!.normalized_address = d.data.propertyIdentityAnchor!.address_input;
  return [a, b, c, d, e];
}
async function seed(page: Page, rows = cases()) {
  await page.addInitScript(({ rows, key }) => {
    if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(rows));
    sessionStorage.setItem("proptech:holding-cost-result", JSON.stringify({ property_price_wan: 99999, monthly_total_holding_cost: 987654321 }));
    sessionStorage.setItem("proptech:location-insight-result", JSON.stringify({ secret: "CASE_B_PRIVATE_SESSION" }));
  }, { rows, key: KEY });
}
async function watchProviders(page: Page, baseURL: string) {
  const requests: string[] = [];
  const telemetry: string[] = [];
  const staticAssets: string[] = [];
  await page.route("**/*", async (route) => {
    const request = route.request(); const url = new URL(request.url());
    if (url.origin === new URL(baseURL).origin && (/\/_next\/static\//.test(url.pathname) || ["stylesheet", "script", "font"].includes(request.resourceType()))) { staticAssets.push(url.pathname); return route.continue(); }
    if (/telemetry|client-error|web-vitals/.test(url.pathname)) { telemetry.push(url.pathname); return route.continue(); }
    if (isProviderRequest(request, baseURL)) { requests.push(`${request.method()} ${url.hostname}${url.pathname}`); return route.abort(); }
    await route.continue();
  });
  return { requests, telemetry, staticAssets };
}
test("desktop compare preserves four-case order, descriptive rows and missing/zero/stale states", async ({ page }) => {
  await seed(page);
  await page.goto("/compare?cases=case-d,case-a,case-b,case-c");
  await expect(page.getByRole("heading", { level: 1, name: "案件證據比較" })).toBeVisible();
  const table = page.getByTestId("compare-desktop");
  await expect(table.getByRole("columnheader").nth(1)).toContainText("A · 案件 D");
  await expect(table.getByRole("row", { name: /市場成交總價中位數/ })).toContainText("1,850 萬元");
  await expect(table.getByRole("row", { name: /年利率/ })).toContainText("0 %");
  await expect(table.getByRole("row", { name: /市場成交總價中位數/ })).toContainText("已過期");
  // Same-state unresolved rows are collapsed by default but named, and remain one toggle away.
  await expect(page.getByTestId("hidden-unresolved").first()).toContainText("成交資料推估中點");
  await page.getByRole("button", { name: "顯示所有欄位" }).click();
  await expect(table.getByRole("row", { name: /成交資料推估中點/ })).toContainText("已嘗試，目前無法取得");
  await expect(page.getByTestId("comparability-warnings")).toContainText("假設不同");
  await expect(page.locator("main")).not.toContainText(/最佳物件|勝出物件|綜合分數|bestCaseId|topCandidate/);
});
test("selection rejects fifth and duplicates, never substitutes missing or invalid cases", async ({ page }) => {
  await seed(page); await page.goto("/compare");
  for (const label of ["案件 A", "案件 B", "案件 C", "案件 D"]) await page.getByRole("checkbox", { name: `選擇 ${label}`, exact: true }).check();
  await page.getByRole("checkbox", { name: "選擇 案件 E", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("最多選擇 4");
  await expect(page).toHaveURL(/cases=case-a,case-b,case-c,case-d/);
  await page.goto("/compare?cases=case-a,case-a"); await expect(page.locator("main").getByRole("alert")).toContainText("重複");
  await page.goto("/compare?cases=case-a,missing"); await expect(page.locator("main").getByRole("alert")).toContainText("找不到");
  await expect(page.getByTestId("compare-desktop")).toHaveCount(0);
});
test("390px shows two cases per field, switches pair/domain, wraps long content", async ({ page }) => {
  await seed(page); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/compare?cases=case-a,case-b,case-c,case-d");
  await expect(page.getByTestId("compare-mobile")).toBeVisible();
  await page.getByLabel("右側比較案件").selectOption("case-c");
  await page.getByLabel("比較領域").selectOption("market");
  const row = page.getByTestId("mobile-row-price-asking");
  await expect(row).toContainText("案件 A"); await expect(row).toContainText("案件 C");
  await expect(row).not.toContainText("案件 B");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page).toHaveURL(/cases=case-a,case-b,case-c,case-d/);
});
test("report prints the frozen snapshot until explicit newer-load, with no cross-case session fallback", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/report");
  await expect(page.getByRole("heading", { level: 1, name: "案件證據報告" })).toBeVisible();
  await expect(page.getByTestId("report-evidence")).toContainText("55,111 元／月");
  await page.evaluate((key) => { const rows = JSON.parse(localStorage.getItem(key)!); rows[0].title = "更新案件 A"; localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key })); }, KEY);
  await expect(page.getByTestId("snapshot-change")).toContainText("案件已有較新快照");
  await expect(page.getByTestId("report-evidence")).toContainText("案件 A");
  await expect(page.getByTestId("report-evidence")).not.toContainText("更新案件 A");
  await page.evaluate(() => { window.print = () => { document.body.dataset.printed = "yes"; }; });
  await page.getByRole("button", { name: "列印／另存 PDF" }).click();
  expect(await page.locator("body").getAttribute("data-printed")).toBe("yes");
  await page.getByRole("button", { name: "載入較新快照" }).click();
  await expect(page.getByTestId("report-evidence")).toContainText("更新案件 A");
  await expect(page.getByTestId("report-evidence")).not.toContainText(/987654321|CASE_B_PRIVATE_SESSION/);
});
test("deleted and identity-invalid reports stop formal print with recovery", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-evidence")).toBeVisible();
  await page.evaluate((key) => { localStorage.setItem(key, "[]"); dispatchEvent(new StorageEvent("storage", { key })); }, KEY);
  await expect(page.locator("main").getByRole("alert")).toContainText("找不到");
  await expect(page.getByRole("button", { name: "列印／另存 PDF" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "回到已儲存案件" })).toBeVisible();
});
test("invalid storage, duplicate records and identity conflicts are disclosed", async ({ page }) => {
  await seed(page); await page.goto("/compare?cases=case-a,case-b");
  await page.evaluate((key) => { localStorage.setItem(key, "{broken"); dispatchEvent(new StorageEvent("storage", { key })); }, KEY);
  await expect(page.locator("main").getByRole("alert")).toContainText("儲存資料無法解析");
  const rows = cases(); rows[0].data.propertyIdentityAnchor!.revalidation = { status: "needs_revalidation", conflicts: ["coordinates"] };
  await page.evaluate(({ key, rows }) => localStorage.setItem(key, JSON.stringify(rows)), { key: KEY, rows });
  await page.goto("/cases/case-a/report"); await expect(page.locator("main").getByRole("alert")).toContainText("重新確認");
});
test("opening, navigation, selection, disclosure, storage changes and print cause zero provider requests", async ({ page, baseURL }) => {
  await seed(page); const observed = await watchProviders(page, baseURL!);
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeVisible();
  await page.getByTestId("compare-desktop").getByRole("button", { name: "移除 案件 B" }).click();
  await page.getByRole("checkbox", { name: "選擇 案件 C", exact: true }).check();
  await page.reload(); await expect(page.getByTestId("compare-desktop")).toBeVisible();
  await page.goto("/cases/case-a/report"); await expect(page.getByTestId("report-evidence")).toBeVisible();
  await page.getByTestId("report-evidence").locator("summary").first().click();
  await page.evaluate((key) => dispatchEvent(new StorageEvent("storage", { key })), KEY);
  await page.evaluate(() => { window.print = () => { dispatchEvent(new Event("beforeprint")); dispatchEvent(new Event("afterprint")); }; });
  await page.getByRole("button", { name: "列印／另存 PDF" }).click();
  await page.goBack(); await page.goForward();
  await expect(page.getByTestId("report-evidence")).toBeVisible();
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!); rows[0].title = "已保存更新 A";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  await page.getByRole("button", { name: "載入較新快照" }).click();
  await expect(page.getByTestId("report-evidence")).toContainText("已保存更新 A");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/compare?cases=case-a,case-b,case-c,case-d");
  await page.getByLabel("右側比較案件").selectOption("case-c");
  await page.getByLabel("比較領域").selectOption("finance");
  await expect(page.getByTestId("compare-mobile")).toBeVisible();
  expect(observed.requests).toEqual([]);
});
test("A4 long print expands sources and limitations, without controls or horizontal clipping", async ({ page }, testInfo) => {
  const rows = cases();
  rows[0].title = "長報告案件 A";
  const longAddress = `臺中市西屯區臺灣大道三段100號${"長地址建物附註".repeat(20)}`;
  rows[0].data.propertyIdentityAnchor!.address_input = longAddress;
  rows[0].data.propertyIdentityAnchor!.normalized_address = longAddress;
  rows[0].data.journeyContext!.propertyContext.addressSummary = longAddress;
  rows[0].data.terrainReference!.layers[0].evidence_metadata = { version: 1, usability: "no_match", matched: false, source_url: `https://example.org/${"official-source-".repeat(50)}`, query_condition: "半徑 500 公尺；依來源條件" };
  await seed(page, rows); await page.goto("/cases/case-a/report"); await expect(page.getByTestId("report-evidence")).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(page.getByTestId("report-controls")).toBeHidden();
  await expect(page.getByTestId("report-evidence")).toContainText("快照未保存");
  await expect(page.getByTestId("report-evidence")).toContainText("不代表安全");
  await expect(page.locator("iframe, .leaflet-container")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const pdf = await page.pdf({ path: testInfo.outputPath("e9-report-a4.pdf"), format: "A4", printBackground: true });
  expect(pdf.byteLength).toBeGreaterThan(10000);
  await page.screenshot({ path: testInfo.outputPath("e9-report-print.png"), fullPage: true });
});
test("malformed domain updates block native printing before projection and cannot silently become unqueried", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/report"); await expect(page.getByTestId("report-evidence")).toBeVisible();
  const guarded = await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!); rows[0].data.financeEvidence.loan.monthly_payment_twd = "bad";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new Event("beforeprint"));
    return document.querySelector("main")?.getAttribute("data-print-blocked");
  }, KEY);
  expect(guarded).toBe("true"); await expect(page.locator("main").getByRole("alert")).toContainText("無效");
  await page.emulateMedia({ media: "print" }); await expect(page.getByTestId("report-evidence")).toHaveCount(0);
});
test("legacy failed valuation survives repeated repository compaction and reload", async ({ page }) => {
  const row = e9Case(); delete row.data.journeyContext; row.data.valuation = { valuation_status: "unavailable", result_origin: "none" } as never;
  await seed(page, [row]); await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-evidence").getByRole("row", { name: /成交資料推估中點/ })).toContainText("已嘗試，目前無法取得");
  await page.reload();
  await expect(page.getByTestId("report-evidence").getByRole("row", { name: /成交資料推估中點/ })).toContainText("已嘗試，目前無法取得");
});
test("cleared area and stored unusable finance stay suppressed in the report", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/report");
  for (const variant of ["missing-area", "stale", "unavailable"] as const) {
    const row = e9Case();
    if (variant === "missing-area") { delete row.inputSummary.areaPing; row.data.inputs.area_ping = 0; }
    else row.data.financeEvidence!.calculation.usability = variant;
    await page.evaluate(({ key, row }) => { localStorage.setItem(key, JSON.stringify([row])); }, { key: KEY, row });
    await page.reload();
    const payment = page.getByTestId("report-evidence").getByRole("row").filter({ has: page.getByRole("rowheader", { name: "房貸月付", exact: true }) });
    await expect(payment).toContainText(variant === "unavailable" ? "已嘗試，目前無法取得" : "已過期，需重新確認");
    await expect(payment).not.toContainText("已儲存摘要／受限");
  }
});
test("storage unavailable differs from empty and clear-all invalidates frozen report", async ({ page }) => {
  await seed(page); await page.goto("/cases/case-a/report"); await expect(page.getByTestId("report-evidence")).toBeVisible();
  await page.evaluate(() => { localStorage.clear(); dispatchEvent(new StorageEvent("storage", { key: null })); });
  await expect(page.locator("main").getByRole("alert")).toContainText("找不到");
  await page.addInitScript(() => { Storage.prototype.getItem = () => { throw new Error("denied"); }; });
  await page.goto("/compare"); await expect(page.locator("main").getByRole("alert")).toContainText("儲存目前無法讀取");
});
const RANKING = /最佳物件|勝出|綜合分數|推薦購買|較安全|整體較便宜|bestCaseId|topCandidate|winner|recommended/i;
test("standard pair leads with a difference brief, differences-only rows and one limitations area under 6000px", async ({ page, baseURL }) => {
  await seed(page); const observed = await watchProviders(page, baseURL!);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/compare?cases=case-a,case-b");
  const key = page.getByTestId("compare-difference-brief"); const table = page.getByTestId("compare-desktop");
  await expect(key).toBeVisible(); await expect(table).toBeVisible();
  expect((await key.boundingBox())!.y).toBeLessThan((await table.boundingBox())!.y);
  await expect(key.getByTestId("brief-price")).toContainText("52.4 萬元／坪");
  await expect(key.getByTestId("brief-price")).toContainText("尚未查詢");
  await expect(key.getByTestId("brief-risk")).toContainText("未知不等於安全");
  await expect(key.getByTestId("brief-location")).toContainText("臺中車站");
  await expect(key.getByTestId("brief-verification")).toBeVisible();
  await expect(page.locator("main")).not.toContainText(RANKING);
  await expect(table).toHaveAttribute("data-fields-view", "differences");
  await expect(table.getByTestId("compare-row-price-asking")).toBeHidden();
  await expect(table.getByTestId("compare-row-market-total")).toBeVisible();
  await expect(table.getByTestId("compare-row-market-total")).toContainText("尚未查詢");
  await expect(page.getByTestId("compare-fields-toolbar")).toContainText("各案件的保存數值、狀態與來源皆相同");
  await expect(page.getByTestId("hidden-unresolved").first()).toContainText("不代表數值相同");
  const limits = page.getByTestId("compare-limitations");
  await expect(limits.getByTestId("comparability-warnings")).toContainText("缺值不等於零");
  await expect(limits.getByTestId("compare-gap-counts")).toContainText("A · 案件 A");
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  expect(height).toBeLessThanOrEqual(6000);
  // Provenance remains reachable by keyboard in compact cells and in the limitations area.
  const row = table.getByTestId("compare-row-market-total");
  await row.locator("summary").first().focus();
  await page.keyboard.press("Enter");
  await expect(row.getByText(/^來源：/).first()).toBeVisible();
  await limits.getByTestId("compare-gaps").locator("summary").click();
  await expect(limits.getByRole("link", { name: "前往查證工作區" }).first()).toBeVisible();
  await limits.getByTestId("compare-sources").locator("summary").click();
  await expect(limits.getByTestId("compare-sources")).toContainText("沒有執行新查詢");
  expect(observed.requests).toEqual([]);
});
test("show all fields toggle is accessible, URL-backed and restores with Back/Forward", async ({ page, baseURL }) => {
  await seed(page); const observed = await watchProviders(page, baseURL!);
  await page.goto("/compare?cases=case-a,case-b");
  const table = page.getByTestId("compare-desktop"); const toggle = page.getByRole("button", { name: "顯示所有欄位" });
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect(table.getByTestId("compare-row-price-asking")).toBeHidden();
  await toggle.focus(); await page.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await expect(page).toHaveURL(/cases=case-a,case-b&fields=all$/);
  await expect(table.getByTestId("compare-row-price-asking")).toBeVisible();
  await expect(table.getByTestId("compare-row-valuation-estimate")).toContainText("已嘗試，目前無法取得");
  await page.goBack();
  await expect(page).toHaveURL(/cases=case-a,case-b$/);
  await expect(table.getByTestId("compare-row-price-asking")).toBeHidden();
  await page.goForward();
  await expect(table.getByTestId("compare-row-price-asking")).toBeVisible();
  // A new case selection starts again from differences only.
  await page.getByRole("checkbox", { name: "選擇 案件 C", exact: true }).check();
  await expect(page).toHaveURL(/cases=case-a,case-b,case-c$/);
  await expect(table).toHaveAttribute("data-fields-view", "differences");
  expect(observed.requests).toEqual([]);
});
test("stale, unknown and mismatched states stay visible in differences-only mode", async ({ page }) => {
  await seed(page); await page.goto("/compare?cases=case-a,case-c");
  const table = page.getByTestId("compare-desktop");
  await expect(table.getByTestId("compare-row-market-total")).toBeVisible();
  await expect(table.getByTestId("compare-row-market-total")).toContainText("已過期");
  await expect(page.getByTestId("brief-price")).toContainText("已過期");
  await expect(table.getByTestId("compare-row-commute-destination")).toBeVisible();
  await expect(table.getByTestId("compare-row-finance-rate")).toContainText("2.2 %");
  await page.goto("/compare?cases=case-a,case-d");
  await expect(table.getByTestId("compare-row-commute-duration")).toBeVisible();
  await expect(table.getByTestId("compare-row-commute-duration")).toContainText("已嘗試，目前無法取得");
  await expect(table.getByTestId("compare-row-commute-duration")).toHaveAttribute("data-row-relation", "differs");
  await page.goto("/compare?cases=case-a,case-b");
  await expect(table.getByTestId("compare-row-finance-payment")).toBeVisible();
  await expect(table.getByTestId("compare-row-finance-payment")).toContainText("尚未查詢");
});
for (const width of [390, 430]) {
  test(`${width}px keeps key differences before the pair matrix, collapses identical rows and keeps provenance reachable`, async ({ page, baseURL }) => {
    await seed(page); const observed = await watchProviders(page, baseURL!);
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/compare?cases=case-a,case-b");
    const key = page.getByTestId("compare-difference-brief"); const mobile = page.getByTestId("compare-mobile");
    await expect(key).toBeVisible(); await expect(mobile).toBeVisible();
    expect((await key.boundingBox())!.y).toBeLessThan((await mobile.boundingBox())!.y);
    await expect(page.getByLabel("比較領域")).toHaveValue("market");
    await expect(page.getByTestId("mobile-row-price-asking")).toBeHidden();
    await expect(page.getByTestId("mobile-row-market-total")).toBeVisible();
    const summary = page.getByTestId("mobile-row-market-total").locator("summary").first();
    expect((await summary.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await summary.click();
    await expect(page.getByTestId("mobile-row-market-total").getByText(/^來源：/).first()).toBeVisible();
    await page.getByLabel("比較領域").selectOption("risk");
    await expect(mobile).toContainText("這兩個案件在此領域沒有差異欄位");
    await expect(mobile.getByTestId("hidden-unresolved")).toContainText("活動斷層");
    const toggle = page.getByRole("button", { name: "顯示所有欄位" });
    expect((await toggle.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await toggle.click();
    await expect(page.getByTestId("mobile-row-risk-active_fault")).toBeVisible();
    await expect(page.locator("main")).not.toContainText(RANKING);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(observed.requests).toEqual([]);
  });
}
async function executiveCitationsResolve(page: Page) {
  const executive = page.getByTestId("report-executive");
  const links = executive.locator("[data-citation-id] a");
  expect(await links.count()).toBeGreaterThan(0);
  const references = page.getByTestId("report-citation-references");
  for (const href of await links.evaluateAll((nodes) => nodes.map((node) => node.getAttribute("href")!))) {
    expect(href).toMatch(/^#report-ec1\.case-/);
    await expect(references.locator(`[id="${href.slice(1)}"]`)).toHaveCount(1);
  }
}
test("report leads with a cited executive summary before domain detail, provider-free", async ({ page, baseURL }) => {
  await seed(page); const observed = await watchProviders(page, baseURL!);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/cases/case-a/report");
  const executive = page.getByTestId("report-executive");
  await expect(executive.getByRole("heading", { level: 2, name: "重點摘要" })).toBeVisible();
  const firstDomain = page.getByTestId("report-evidence").getByRole("heading", { level: 2, name: "市場、區位與風險" });
  expect((await executive.boundingBox())!.y).toBeLessThan((await firstDomain.boundingBox())!.y);
  await expect(executive.getByTestId("executive-snapshot")).toContainText("2026");
  await expect(executive.getByTestId("executive-snapshot")).toContainText("不會自動更新");
  await expect(executive.getByTestId("executive-property")).toContainText("不代表地號");
  await expect(executive.getByTestId("executive-key-asking")).toContainText("2,480 萬元");
  await expect(executive.getByTestId("executive-key-asking")).toContainText("使用者輸入");
  await expect(executive.getByTestId("executive-key-asking_unit")).toContainText("82.67");
  await expect(executive.getByTestId("executive-key-asking_unit")).toContainText("本報告推導");
  await expect(executive.getByTestId("executive-key-asking_unit")).toContainText("不是估價");
  await expect(executive.getByTestId("executive-key-asking_unit").locator("[data-citation-id]")).toHaveCount(4);
  await expect(executive.getByTestId("executive-key-housing")).toContainText("55,111");
  await expect(executive.getByTestId("executive-key-commute")).toContainText("臺中車站");
  await expect(executive.getByTestId("executive-key-state")).toContainText("未知");
  await expect(executive.getByTestId("executive-attention-risk_unresolved")).toContainText("不代表安全");
  await expect(executive.getByTestId("executive-attention-affordability_not_assessed")).toBeVisible();
  await expect(executive.getByTestId("executive-open")).toContainText("項缺口");
  await expect(executive.getByTestId("executive-open-risk")).toBeVisible();
  await expect(executive.getByTestId("executive-limitation")).toContainText("不是估價");
  await expect(executive).not.toContainText(RANKING);
  await executiveCitationsResolve(page);
  // Executive references reuse the report list: no second numbering system.
  const ids = await page.getByTestId("report-citation-references").locator("ol > li").evaluateAll((nodes) => nodes.map((node) => node.id));
  expect(new Set(ids).size).toBe(ids.length);
  const link = executive.getByTestId("executive-key-asking").locator("[data-citation-id] a").first();
  await link.focus(); await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#report-ec1\.case-a\..+price-asking$/);
  await expect(page.locator(`[id="${(await link.getAttribute("href"))!.slice(1)}"]`)).toBeInViewport();
  await executive.getByTestId("executive-open").getByRole("link", { name: "見未知與限制" }).click();
  await expect(page.locator("#report-limits")).toBeInViewport();
  expect(observed.requests).toEqual([]);
});
test("executive summary keeps stale, unknown and missing evidence unresolved", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-c/report");
  const executive = page.getByTestId("report-executive");
  await expect(executive.getByTestId("executive-key-market")).toHaveCount(0);
  await expect(executive.getByTestId("executive-attention-stale")).toContainText("市場成交總價中位數");
  await expect(executive.getByTestId("executive-attention-stale")).toContainText("不代表目前");
  await expect(executive.getByTestId("executive-attention-stale")).toContainText("已過期");
  await executiveCitationsResolve(page);
  await page.goto("/cases/case-b/report");
  await expect(executive.getByTestId("executive-key-housing")).toHaveCount(0);
  await expect(executive.getByTestId("executive-key-commute")).toHaveCount(0);
  await expect(executive.getByTestId("executive-key-market")).toHaveCount(0);
  await expect(executive.getByTestId("executive-open-finance")).toBeVisible();
  await expect(executive).not.toContainText(/55,111|1,850|52\.4/);
});
test("executive summary follows the selected locale", async ({ page }) => {
  await seed(page);
  await page.addInitScript(() => localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale: "en" })));
  await page.goto("/cases/case-a/report");
  const executive = page.getByTestId("report-executive");
  await expect(executive.getByRole("heading", { level: 2, name: "Executive summary" })).toBeVisible();
  await expect(executive.getByTestId("executive-key-asking_unit")).toContainText("Derived in this report");
  await expect(executive.getByTestId("executive-attention-risk_unresolved")).toContainText("None of these means safe");
});
for (const width of [390, 430]) {
  test(`${width}px report shows the executive summary first with reachable citations and no overflow`, async ({ page, baseURL }) => {
    await seed(page); const observed = await watchProviders(page, baseURL!);
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/cases/case-a/report");
    const executive = page.getByTestId("report-executive");
    await expect(executive).toBeVisible();
    const firstTable = page.getByTestId("report-evidence").locator("table").first();
    expect((await executive.boundingBox())!.y).toBeLessThan((await firstTable.boundingBox())!.y);
    // Key numbers stack in one column instead of a dense grid.
    const columns = await executive.getByTestId("executive-key-numbers").locator("li").evaluateAll((nodes) => nodes.map((node) => Math.round(node.getBoundingClientRect().x)));
    expect(new Set(columns).size).toBe(1);
    for (const target of [executive.locator("[data-citation-id] a").first(), executive.getByRole("link", { name: /工作區/ }).first()]) {
      const box = (await target.boundingBox())!;
      expect(box.height).toBeGreaterThanOrEqual(44); expect(box.width).toBeGreaterThanOrEqual(44);
    }
    await expect(executive.getByTestId("executive-open")).toBeVisible();
    await expect(executive.getByTestId("executive-limitation")).toBeVisible();
    await executiveCitationsResolve(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(observed.requests).toEqual([]);
  });
}
test("executive summary prints first with its citations and the full evidence, provider-free", async ({ page, baseURL }) => {
  await seed(page); const observed = await watchProviders(page, baseURL!);
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-executive")).toBeVisible();
  await page.evaluate(() => { window.print = () => { dispatchEvent(new Event("beforeprint")); document.body.dataset.printed = "yes"; dispatchEvent(new Event("afterprint")); }; });
  await page.getByRole("button", { name: "列印／另存 PDF" }).click();
  expect(await page.locator("body").getAttribute("data-printed")).toBe("yes");
  await page.emulateMedia({ media: "print" });
  const executive = page.getByTestId("report-executive");
  await expect(executive).toBeVisible();
  await expect(page.getByTestId("report-controls")).toBeHidden();
  for (const id of ["executive-snapshot", "executive-key-numbers", "executive-attention", "executive-open", "executive-limitation"]) await expect(executive.getByTestId(id)).toBeVisible();
  await expect(executive.locator("[data-citation-id] a").first()).toBeVisible();
  // Screen-only navigation is not evidence; the evidence rows and reference ledger still print.
  await expect(executive.getByRole("link", { name: /工作區/ }).first()).toBeHidden();
  await expect(page.getByTestId("report-citation-references")).toBeVisible();
  await expect(page.getByTestId("report-evidence").getByRole("row", { name: /成交資料推估中點/ })).toBeVisible();
  expect((await executive.boundingBox())!.y).toBeLessThan((await page.getByTestId("report-evidence").locator("table").first().boundingBox())!.y);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(observed.requests).toEqual([]);
});
