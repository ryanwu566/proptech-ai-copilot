import { expect, test } from "@playwright/test";

const PREVIEW = "/dev/decision-report-preview/";

test("existing decision output, header identity, and source times remain explicit", async ({ page }) => {
  await page.goto(`${PREVIEW}?scenario=sufficient`);

  await expect(page.getByRole("heading", { level: 1, name: "合成物件｜河岸生活圈 33 坪" })).toBeVisible();
  await expect(page.getByTestId("synthetic-notice")).toContainText("非真實物件");
  await expect(page.getByTestId("decision-overview")).toHaveAttribute("data-engine-status", "ready_to_view");
  await expect(page.getByTestId("decision-overview")).toContainText("可安排看屋，仍需現場查核");
  await expect(page.getByTestId("identity-status")).toHaveAttribute("data-identity-status", "confirmed");
  await expect(page.getByText("報告產生時間：", { exact: false }).first()).toBeVisible();

  const detail = page.getByTestId("evidence-detail-0");
  await detail.getByText("合成估價可比資料").click();
  await expect(detail).toHaveAttribute("open", "");
  await expect(detail.getByText("來源取得時間")).toBeVisible();
  await expect(detail.getByText("資料生效時間")).toBeVisible();
  await expect(detail).toContainText("合成固定資料（test environment）");
  await expect(detail).toContainText("ev-synth-valuation-0001");
});

test("known high risk survives other missing evidence", async ({ page }) => {
  await page.goto(`${PREVIEW}?scenario=known-high-missing`);

  const decision = page.getByTestId("decision-overview");
  await expect(decision).toHaveAttribute("data-engine-status", "clarify_risk_first");
  await expect(decision).toContainText("已知風險，建議先釐清");
  await expect(decision).toContainText("地勢／災害證據已顯示高風險");
  await expect(decision).toContainText("持有成本資料尚未提供或不可用");
  await expect(page.getByTestId("report-section-terrain")).toContainText("已知高風險");
});

test("unknown, unavailable, partial, stale, conflicting, and unverified states are not upgraded", async ({ page }) => {
  await page.goto(`${PREVIEW}?scenario=terrain-unavailable`);
  await expect(page.getByTestId("decision-overview")).toHaveAttribute("data-engine-status", "needs_more_data");
  await expect(page.getByTestId("report-section-terrain")).toContainText("暫時不可用");
  await expect(page.getByTestId("report-section-terrain")).toContainText("不代表沒有風險");

  await page.goto(`${PREVIEW}?scenario=mixed-quality`);
  await expect(page.getByTestId("report-section-valuation")).toContainText("已過時");
  await expect(page.getByTestId("report-section-terrain")).toContainText("部分可用");
  await expect(page.getByTestId("report-section-tax")).toContainText("資料衝突");
  await expect(page.getByTestId("evidence-register")).toContainText("未驗證");
});

test("missing numeric values are not shown as zero and identity remains unconfirmed", async ({ page }) => {
  await page.goto(`${PREVIEW}?scenario=missing-valuation-identity`);

  const valuation = page.getByTestId("report-section-valuation");
  await expect(valuation).toContainText("未評估");
  await expect(valuation.getByText("未提供（不等於 0）")).toHaveCount(4);
  await expect(valuation).not.toContainText("0 萬");
  await expect(page.getByTestId("identity-status")).toHaveAttribute("data-identity-status", "unverified");
  await expect(page.getByTestId("identity-status")).toContainText("尚未驗證");
});

test("checklist is local review only and does not make provider or customer-data requests", async ({ page }) => {
  const outsideRequests: string[] = [];
  const dataRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.origin !== "http://127.0.0.1:3103") outsideRequests.push(request.url());
    if (["fetch", "xhr"].includes(request.resourceType()) && !url.pathname.startsWith("/__nextjs")) dataRequests.push(request.url());
  });
  await page.goto(`${PREVIEW}?scenario=sufficient`);

  const identity = page.getByTestId("identity-status");
  const identityState = await identity.getAttribute("data-identity-status");
  const evidenceState = await page.locator("[data-report-status]").nth(4).getAttribute("data-report-status");
  await page.getByRole("checkbox").first().check();
  await expect(page.getByTestId("checklist-progress")).toContainText("1／3");
  await expect(identity).toHaveAttribute("data-identity-status", identityState ?? "");
  await expect(page.locator("[data-report-status]").nth(4)).toHaveAttribute("data-report-status", evidenceState ?? "");
  expect(outsideRequests).toEqual([]);
  expect(dataRequests).toEqual([]);

  await page.reload();
  await expect(page.getByTestId("checklist-progress")).toContainText("0／3");
});

test("mobile, keyboard disclosure, long content, and print media preserve report safeguards", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "print", { value: () => { document.documentElement.dataset.printCalled = "true"; } });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${PREVIEW}?scenario=long-text`);

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const summary = page.getByTestId("evidence-detail-0").locator("summary");
  await summary.focus();
  await summary.press("Enter");
  await expect(page.getByTestId("evidence-detail-0")).toHaveAttribute("open", "");
  await summary.press("Enter");
  await expect(page.getByTestId("evidence-detail-0")).not.toHaveAttribute("open", "");
  await page.getByTestId("print-report").click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.printCalled)).toBe("true");

  await page.emulateMedia({ media: "print" });
  await expect(page.getByTestId("print-report")).toBeHidden();
  await expect(page.getByTestId("synthetic-notice")).toBeVisible();
  await expect(page.getByRole("heading", { name: "證據、來源與限制" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "報告限制" })).toBeVisible();
  await expect(page.getByTestId("print-evidence-detail-0").getByText("來源標籤")).toBeVisible();
});

test("all-data-missing case keeps sections and missing provenance visible", async ({ page }) => {
  await page.goto(`${PREVIEW}?scenario=all-missing`);

  await expect(page.getByTestId("decision-overview")).toHaveAttribute("data-engine-status", "needs_more_data");
  for (const section of ["valuation", "affordability", "terrain", "tax"]) {
    await expect(page.getByTestId(`report-section-${section}`)).toContainText("未評估");
  }
  await expect(page.getByTestId("evidence-register")).toContainText("證據來源與溯源資料未提供");
  await expect(page.getByTestId("identity-status")).toHaveAttribute("data-identity-status", "unknown");
});

test("inconsistent supplied decision fails closed without hiding known risk", async ({ page }) => {
  await page.goto(`${PREVIEW}?scenario=inconsistent-input`);

  const decision = page.getByTestId("decision-overview");
  await expect(decision).toHaveAttribute("data-engine-status", "ready_to_view");
  await expect(decision).toContainText("無法判定：決策輸入與結果不一致");
  await expect(decision).toContainText("既有規則重新判定（clarify_risk_first）不一致");
  await expect(decision).toContainText("地勢／災害證據已顯示高風險");
});
