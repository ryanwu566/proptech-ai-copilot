import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

// Test-only records in Playwright's fresh context, never an existing user profile.
function representativeCases() {
  const a = e9Case(); const b = e9Case("case-b");
  const address = "台北市大安區敦化南路二段100號";
  a.title = "Acceptance fixture A";
  a.inputSummary.city = "臺北市"; a.inputSummary.district = "大安區";
  a.data.propertyIdentityAnchor!.address_input = address;
  a.data.propertyIdentityAnchor!.normalized_address = address;
  a.data.propertyIdentityAnchor!.coordinates = { latitude: 25.028, longitude: 121.548 };
  a.data.propertyIdentityAnchor!.administrative_location = { city: "臺北市", district: "大安區", village: null, village_code: null };
  a.data.journeyContext!.propertyContext = { city: "臺北市", district: "大安區", road: "敦化南路二段", addressSummary: address, sourceLabel: "Acceptance fixture", selectionStatus: "selected" };
  a.data.journeyContext!.priceBasis = "manual";
  delete a.data.journeyContext!.activePriceWan; delete a.inputSummary.propertyPrice;
  a.data.financeEvidence!.assumptions.price_basis = "manual";
  a.data.financeEvidence!.input_fingerprint = a.data.financeEvidence!.input_fingerprint.replace("asking|", "manual|");
  a.data.commuteRoute!.origin = { latitude: 25.028, longitude: 121.548 };
  a.data.commuteRoute!.destination = { address: "台北車站" };
  a.data.commuteRoute!.mode = "transit";
  // Do not relabel Taichung market observations as Taipei observations.
  delete a.data.marketInsight;
  b.title = "Acceptance fixture B"; delete b.data.financeEvidence;
  b.data.marketInsight!.freshness_status = "stale";
  return [a, b];
}

async function setup(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(rows => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
  }, representativeCases());
  const calls: string[] = [];
  await page.route("**/*", async route => {
    const request = route.request(); const url = new URL(request.url());
    if (/googleapis|maps\.google|earthengine|tdx\.transportdata/.test(url.hostname)) { calls.push(url.hostname); return route.abort(); }
    if (url.hostname !== "127.0.0.1" && url.hostname !== "e2e.test") return route.fulfill({ status: 204, body: "" });
    if (["fetch", "xhr"].includes(request.resourceType()) && /\/(market(?:-insights)?|valuation(?:-trend)?|location|commute(?:-route)?|terrain(?:-risk)?|satellite|loan|holding-cost|places|routes)(\/|$)/.test(url.pathname) && !url.pathname.startsWith("/cases/")) {
      calls.push(url.pathname); return route.abort();
    }
    await route.continue();
  });
  return calls;
}
const views = ["/", "/cases/case-a/overview", "/cases/case-a/market", "/cases/case-a/location", "/cases/case-a/risk", "/cases/case-a/finance", "/compare?cases=case-a,case-b", "/cases/case-a/report"];
for (const width of [1440, 1024, 390]) {
  for (const view of views) {
    test(`${width}px ${view} overflow, labels, focus and reduced motion`, async ({ page }, testInfo) => {
      const calls = await setup(page, width);
      await page.goto(view);
      await expect(page.locator("main")).toBeVisible();
      if (view !== "/") await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const unlabeled = await page.locator("input:not([type=hidden]),select,textarea").evaluateAll(elements => elements.filter(element => {
        const input = element as HTMLInputElement;
        return input.getClientRects().length && !input.labels?.length && !input.getAttribute("aria-label") && !input.getAttribute("aria-labelledby") && !input.getAttribute("title");
      }).length);
      expect(unlabeled).toBe(0);
      await page.keyboard.press("Tab");
      expect(await page.evaluate(() => {
        const active = document.activeElement;
        if (!active || active === document.body) return false;
        const css = getComputedStyle(active);
        return css.outlineStyle !== "none" && parseFloat(css.outlineWidth) >= 2;
      })).toBe(true);
      expect(await page.evaluate(() => [...document.querySelectorAll("*")].filter(el => {
        const css = getComputedStyle(el);
        return css.animationName !== "none" && css.animationDuration.split(",").some(duration => parseFloat(duration) > .01);
      }).length)).toBe(0);
      const headingContrast = await page.locator("h1").first().evaluate(el => {
        const rgb = (color: string) => color.match(/[\d.]+/g)!.slice(0, 3).map(Number);
        const luminance = (color: number[]) => color.map(channel => { const c = channel / 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; }).reduce((sum, channel, i) => sum + channel * [.2126, .7152, .0722][i], 0);
        let ancestor: Element | null = el; let background = "rgb(255,255,255)";
        while (ancestor) { const value = getComputedStyle(ancestor).backgroundColor; if (value !== "rgba(0, 0, 0, 0)" && value !== "transparent") { background = value; break; } ancestor = ancestor.parentElement; }
        const a = luminance(rgb(getComputedStyle(el).color)); const b = luminance(rgb(background));
        return (Math.max(a,b) + .05) / (Math.min(a,b) + .05);
      });
      expect(headingContrast).toBeGreaterThanOrEqual(3);
      await page.screenshot({ path: testInfo.outputPath(`view-${width}.png`), fullPage: true });
      expect(calls).toEqual([]);
    });
  }
  test(`${width}px saved Taipei transit fixture, A4 PDF, Save and Reopen preserve provenance`, async ({ page }, testInfo) => {
    const calls = await setup(page, width);
    await page.goto("/cases/case-a/report");
    const report = page.getByTestId("report-evidence");
    await expect(report).toContainText("手動試算情境");
    await expect(report).toContainText("55,111");
    await expect(report).toContainText("台北車站");
    await expect(report).toContainText("不代表安全");
    await page.emulateMedia({ media: "print" });
    await expect(page.getByTestId("report-controls")).toBeHidden();
    await expect(page.getByRole("navigation").first()).toBeHidden();
    const pdf = await page.pdf({ path: testInfo.outputPath(`acceptance-${width}-a4.pdf`), preferCSSPageSize: true, format: "A4", printBackground: true });
    expect(pdf.byteLength).toBeGreaterThan(10000);
    // A standard saved fixture must remain readable without expanding to one
    // nearly empty page per provenance record. Chrome emits page objects here.
    expect((pdf.toString("latin1").match(/\/Type\s*\/Page\b/g) ?? []).length).toBeLessThanOrEqual(20);
    expect(calls).toEqual([]);
    await page.emulateMedia({ media: "screen" });
    await page.goto("/cases/case-a/overview");
    await page.getByRole("button", { name: "保存目前案件快照" }).click();
    await expect(page.getByTestId("overview-save-status")).toContainText("已保存目前已知狀態");
    await page.goto("/cases");
    await page.getByRole("link", { name: "開啟Acceptance fixture A", exact: true }).click();
    await page.goto("/cases/case-a/finance");
    await expect(page.getByTestId("loan-summary")).toContainText("55,111");
    expect(calls).toEqual([]);
  });
}
