import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import type { ValuationResult } from "../lib/api";

const result = JSON.parse(readFileSync("../tests/fixtures/comparable-explanation-result.json", "utf8")) as ValuationResult;
const KEY = "proptech.savedCases.v1";
function savedCase() {
  const saved = e9Case();
  const address = "台北市大安區和平東路二段100號";
  Object.assign(saved.inputSummary, { city: "台北市", district: "大安區", road: "和平東路二段100號" });
  Object.assign(saved.data.inputs!, { city: "台北市", district: "大安區", road: "和平東路二段100號", building_age_years: 15, floor: 8 });
  Object.assign(saved.data.journeyContext!.propertyContext, { city: "台北市", district: "大安區", road: "和平東路二段100號", addressSummary: address });
  Object.assign(saved.data.propertyIdentityAnchor!, { address_input: address, normalized_address: address });
  saved.data.propertyIdentityAnchor!.coordinates = { latitude: 25.0254, longitude: 121.5434 };
  saved.data.propertyIdentityAnchor!.administrative_location.city = "台北市";
  saved.data.propertyIdentityAnchor!.administrative_location.district = "大安區";
  saved.data.valuation = structuredClone(result);
  return saved;
}
async function install(page: Page) {
  await page.addInitScript(({ key, row, second }) => {
    if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify([row, second]));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
  }, { key: KEY, row: savedCase(), second: e9Case("case-b") });
  const providers: string[] = [];
  await page.route("**/*", async (route) => {
    const request = route.request(); const url = new URL(request.url());
    const analysis = /\/(?:valuation|market-insights|location|commute|terrain|geocode|loan|holding-cost|taxoracle)(?:\/|$)/.test(url.pathname);
    const host = /googleapis|maps\.google|gstatic|openstreetmap|mapbox|tdx\.transportdata/.test(url.hostname);
    if (host || (analysis && ["fetch", "xhr"].includes(request.resourceType()) && !url.pathname.startsWith("/cases/"))) { providers.push(url.pathname); return route.abort(); }
    return route.continue();
  });
  return providers;
}

for (const width of [390, 1024, 1440]) {
  test(`saved Market explanation and keyboard disclosures at ${width}px`, async ({ page }, testInfo) => {
    const providers = await install(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/cases/case-a/market");
    const details = page.getByTestId("comparable-explanation");
    const toggle = details.locator(":scope > summary");
    await expect(toggle).toHaveText("為何採用這些可比成交？");
    await toggle.focus(); await page.keyboard.press("Enter");
    await expect(details).toHaveAttribute("open", "");
    await expect(page.getByTestId("comparable-counts")).toContainText("已採用: 10");
    await expect(page.getByTestId("selected-comparable-explanations").locator("article")).toHaveCount(10);
    await expect(details).toContainText("停車處理 · 僅供背景參考");
    await page.getByTestId("excluded-comparable-explanations").locator(":scope > summary").click();
    await expect(page.getByTestId("excluded-comparable-explanations").locator("article")).toHaveCount(3);
    await expect(page.getByTestId("excluded-comparable-explanations")).toContainText("未進入前十筆");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByTestId("locale-switcher").selectOption("en");
    await expect(toggle).toHaveText("Why these comparables?");
    await expect(details).toContainText("Parking treatment · Context only");
    for (const [locale, included] of [["ja", "採用"], ["ko", "포함"]]) {
      await page.getByTestId("locale-switcher").selectOption(locale);
      await expect(page.getByTestId("comparable-counts")).toContainText(`${included}: 10`);
    }
    const before = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!)[0].data.valuation.comparable_decision_trace, KEY);
    await page.reload(); await page.getByTestId("comparable-explanation").locator(":scope > summary").click();
    await expect(page.getByTestId("selected-comparable-explanations").locator("article")).toHaveCount(10);
    const after = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!)[0].data.valuation.comparable_decision_trace, KEY);
    expect(after).toEqual(before); expect(providers).toEqual([]);
    await page.getByTestId("comparable-explanation").scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`explanation-${width}px.png`) });
  });
}

test("explicit valuation save, reopen, Compare and frozen A4 Report make no explanation provider requests", async ({ page }, testInfo) => {
  const providers = await install(page);
  let valuationCalls = 0;
  let trendCalls = 0;
  await page.route("**/valuation/estimate", async (route) => { valuationCalls++; await route.fulfill({ json: result }); });
  await page.route("**/valuation/trend", (route) => { trendCalls++; return route.fulfill({ status: 503, body: "unavailable" }); });
  await page.goto("/cases/case-a/market");
  await page.getByTestId("valuation-refresh-button").click();
  await expect(page.getByTestId("valuation-refresh-state")).toContainText("價格推估已更新");
  expect(valuationCalls).toBe(1);
  const saved = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!)[0].data.valuation.comparable_decision_trace, KEY);
  expect(saved).toEqual(result.comparable_decision_trace);
  await page.reload();
  await page.getByTestId("comparable-explanation").locator(":scope > summary").click();
  await expect(page.getByTestId("comparable-counts")).toContainText("已採用: 10");
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeVisible();
  await page.goto("/cases/case-a/report");
  const report = page.getByTestId("report-comparable-explanation");
  await expect(report).toContainText("已採用: 10");
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].data.valuation.comparable_decision_trace.reference_period = "2026-11";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  await expect(page.getByTestId("snapshot-change")).toBeVisible();
  await expect(report).toContainText("2026-10");
  await expect(report).not.toContainText("2026-11");
  await page.emulateMedia({ media: "print" });
  await page.pdf({ path: testInfo.outputPath("comparable-explanation-a4.pdf"), format: "A4", printBackground: true });
  await page.screenshot({ path: testInfo.outputPath("comparable-explanation-print.png"), fullPage: true });
  await page.emulateMedia({ media: "screen" });
  await page.getByRole("button", { name: "載入較新快照" }).click();
  await expect(report).toContainText("2026-11");
  expect(valuationCalls).toBe(1); expect(trendCalls).toBe(1); expect(providers).toEqual([]);
});

test("legacy saved valuation shows unavailable reasons without reconstructing them", async ({ page }) => {
  const row = savedCase(); delete row.data.valuation!.comparable_decision_trace;
  await page.addInitScript(({ row, key }) => localStorage.setItem(key, JSON.stringify([row])), { row, key: KEY });
  const providers = await install(page);
  await page.goto("/cases/case-a/market");
  await page.getByTestId("comparable-explanation").locator(":scope > summary").click();
  await expect(page.getByTestId("comparable-explanation")).toContainText("未保存有效決策軌跡");
  expect(providers).toEqual([]);
});
