import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
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
async function watchProviders(page: Page) {
  const requests: string[] = [];
  const telemetry: string[] = [];
  const staticAssets: string[] = [];
  await page.route("**/*", async (route) => {
    const request = route.request(); const url = new URL(request.url());
    if (/\/_next\/static\//.test(url.pathname) || ["stylesheet", "script", "font"].includes(request.resourceType())) { staticAssets.push(url.pathname); return route.continue(); }
    if (/telemetry|client-error|web-vitals/.test(url.pathname)) { telemetry.push(url.pathname); return route.continue(); }
    const providerHost = /googleapis|maps\.google|gstatic|openstreetmap|mapbox|earthengine|tdx\.transportdata/.test(url.hostname);
    const analysisPath = /\/(?:market(?:-insights)?|valuation(?:-trend)?|commute(?:-route)?|location(?:\/insight)?|terrain(?:-risk)?|satellite|geocod\w*|places|routes|loan|finance|holding-cost|taxoracle|tax)(?:\/|\?|$)/i.test(url.pathname);
    if (providerHost || (["xhr", "fetch"].includes(request.resourceType()) && analysisPath && !url.pathname.startsWith("/cases/"))) { requests.push(`${request.method()} ${url.hostname}${url.pathname}`); return route.abort(); }
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
test("opening, navigation, selection, disclosure, storage changes and print cause zero provider requests", async ({ page }) => {
  await seed(page); const observed = await watchProviders(page);
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
