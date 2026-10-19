import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

// Physical A4 acceptance for the three-page core report: Chromium's own print-to-PDF
// path, CSS @page size and margins. Pages 2, 3 and the appendix force new sheets, so a
// cumulative page count of 1/2/3 proves no core page spills and the appendix starts on 4.
const KEY = "proptech.savedCases.v1";
function cases() {
  const a = e9Case(); const b = e9Case("case-b"); const c = e9Case("case-c"); const d = e9Case("case-d"); const e = e9Case("case-e");
  delete b.data.marketInsight; delete b.data.financeEvidence; delete b.data.commuteRoute;
  c.data.marketInsight!.freshness_status = "stale";
  d.data.commuteRoute!.status = "unavailable"; d.data.commuteRoute!.duration_min = null;
  d.data.propertyIdentityAnchor!.normalized_address = d.data.propertyIdentityAnchor!.address_input;
  const long = `臺中市西屯區臺灣大道三段100號${"長地址建物附註".repeat(8)}`;
  e.title = "長地址案件 E"; e.data.propertyIdentityAnchor!.address_input = long; e.data.propertyIdentityAnchor!.normalized_address = long; e.data.journeyContext!.propertyContext.addressSummary = long;
  return [a, b, c, d, e];
}
async function seed(page: Page, locale: string) {
  await page.addInitScript(({ rows, key, locale }) => {
    if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(rows));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
  }, { rows: cases(), key: KEY, locale });
}
async function watchProviders(page: Page, baseURL: string) {
  const requests: string[] = [];
  await page.route("**/*", async (route) => {
    const request = route.request();
    if (isProviderRequest(request, baseURL)) { requests.push(`${request.method()} ${new URL(request.url()).pathname}`); return route.abort(); }
    await route.continue();
  });
  return requests;
}
/** Chromium writes one uncompressed `/Type /Page` dictionary per physical sheet. */
const pages = (pdf: Buffer) => (pdf.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) ?? []).length;
const pdf = (page: Page, path?: string) => page.pdf({ path, preferCSSPageSize: true, printBackground: true });
async function only(page: Page, hidden: string[]) {
  await page.evaluate((selectors) => {
    document.getElementById("core-measure")?.remove();
    const style = document.createElement("style"); style.id = "core-measure";
    style.textContent = selectors.map((selector) => `${selector} { display: none !important; }`).join("\n");
    document.head.append(style);
  }, hidden);
}
const PAGE2 = '[data-testid="report-core-page-2"]'; const PAGE3 = '[data-testid="report-core-page-3"]';
const APPENDIX = '[data-testid="report-appendix"]'; const REFERENCES = '[data-testid="report-citation-references"]';

const runs: Array<[string, string]> = [["case-a", "zh-TW"], ["case-b", "zh-TW"], ["case-c", "zh-TW"], ["case-d", "zh-TW"], ["case-e", "zh-TW"], ["case-a", "en"], ["case-a", "ja"], ["case-a", "ko"]];
for (const [caseId, locale] of runs) {
  test(`A4 core is exactly three physical pages and the appendix starts on page four (${caseId}, ${locale})`, async ({ page, baseURL }, testInfo) => {
    // Four full A4 renders per run; observed 8–35s locally and a 30s-default timeout inside
    // page.pdf() late in a long serial suite. Assertions keep their defaults; only the
    // four-PDF orchestration receives a bounded budget.
    test.setTimeout(90_000);
    await seed(page, locale); const requests = await watchProviders(page, baseURL!);
    await page.goto(`/cases/${caseId}/report`);
    await expect(page.getByTestId("report-core-page-3")).toBeVisible();
    await page.emulateMedia({ media: "print" });
    const full = await pdf(page, testInfo.outputPath(`${caseId}-${locale}-a4.pdf`));
    await only(page, [PAGE2, PAGE3, APPENDIX, REFERENCES]); const one = pages(await pdf(page, testInfo.outputPath("only-page1.pdf")));
    await only(page, [PAGE3, APPENDIX, REFERENCES]); const two = pages(await pdf(page));
    await only(page, [APPENDIX, REFERENCES]); const three = pages(await pdf(page));
    const total = pages(full);
    await testInfo.attach("a4-pages", { body: JSON.stringify({ caseId, locale, page1: one, through2: two, through3: three, total, appendixStartsOn: three + 1 }), contentType: "application/json" });
    expect([one, two, three], "cumulative core pages: no core page spills").toEqual([1, 2, 3]);
    expect(total, "appendix follows on its own sheets").toBeGreaterThan(3);
    // Every core [n] resolves to the one citation register.
    await only(page, []);
    for (const href of await page.locator(`${PAGE2} [data-citation-id] a, ${PAGE3} [data-citation-id] a`).evaluateAll((nodes) => nodes.map((node) => node.getAttribute("href")!))) {
      await expect(page.locator(REFERENCES).locator(`[id="${href.slice(1)}"]`)).toHaveCount(1);
    }
    expect(requests, "report open, print and PDF generation make no provider call").toEqual([]);
  });
}

test("core report copy follows the locale and keeps unknown, stale and not-a-valuation states visible", async ({ page, baseURL }) => {
  await seed(page, "en"); const requests = await watchProviders(page, baseURL!);
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-core-page-2").getByRole("heading", { level: 2 })).toHaveText("Market, location and risk");
  await expect(page.getByTestId("report-core-page-3").getByRole("heading", { level: 2 })).toHaveText("Finance and next verification steps");
  await expect(page.getByTestId("report-appendix").getByRole("heading", { level: 2 })).toHaveText("Appendix: detailed evidence and methods");
  await expect(page.getByTestId("core-group-risk")).toContainText("never means safe");
  await expect(page.getByTestId("core-market-marker")).toContainText("not a valuation");
  await expect(page.getByTestId("core-next-steps")).toContainText("no purchase recommendation");
  // New interface copy never falls back to zh-TW in another locale.
  for (const zh of ["市場、區位與風險", "資金與下一步查證", "顧問查證清單", "附錄：詳細證據與方法", "推導位置示意", "製作顧問", "提供對象", "已儲存證據", "尚未查詢"]) {
    for (const id of ["report-core-page-2", "report-core-page-3", "report-prepared-by"]) await expect(page.getByTestId(id)).not.toContainText(zh);
  }
  await page.goto("/cases/case-b/report");
  // No saved market band: no marker is drawn and market facts stay listed as missing.
  await expect(page.getByTestId("core-market-marker")).toHaveCount(0);
  await expect(page.getByTestId("core-fact-market-p25")).toContainText("Not queried");
  await page.goto("/cases/case-c/report");
  await expect(page.getByTestId("core-fact-market-unit")).toHaveAttribute("data-evidence-status", "stale");
  await expect(page.getByTestId("core-fact-market-unit")).toContainText("Stale");
  expect(requests).toEqual([]);
});

for (const width of [390, 1024, 1440]) {
  test(`${width}px print layout has no horizontal overflow in any locale`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const locale of ["zh-TW", "en", "ja", "ko"]) {
      await page.addInitScript((locale) => localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale })), locale);
      await seed(page, locale);
      for (const caseId of ["case-a", "case-c"]) {
        await page.emulateMedia({ media: "screen" });
        await page.goto(`/cases/${caseId}/report`);
        await expect(page.getByTestId("report-core-page-3")).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${locale} ${caseId} screen`).toBe(true);
        await page.emulateMedia({ media: "print" });
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${locale} ${caseId} print`).toBe(true);
      }
    }
  });
}
