import { expect, test } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

test("saved difference brief explains contrasts and sources without provider calls or session leakage", async ({ page, baseURL }, testInfo) => {
  const a = e9Case(); const b = e9Case("case-b");
  b.data.journeyContext!.propertyContext.askingPriceWan = 2180;
  b.data.commuteRoute!.destination.address = "高鐵臺中站";
  b.data.marketInsight!.freshness_status = "stale";
  delete b.data.financeEvidence;
  await page.addInitScript((rows) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    sessionStorage.setItem("proptech:holding-cost-result", JSON.stringify({ monthly_total_holding_cost: 987654321 }));
  }, [a, b]);
  const providers: string[] = [];
  await page.route("**/*", async (route) => {
    if (isProviderRequest(route.request(), baseURL!)) { providers.push(route.request().url()); return route.abort(); }
    await route.continue();
  });
  await page.goto("/compare?cases=case-a,case-b");
  const brief = page.getByTestId("compare-difference-brief");
  await expect(brief.getByRole("heading", { level: 2, name: "差異摘要" })).toBeVisible();
  await expect(brief.getByTestId("brief-price")).toContainText("300");
  await expect(brief.getByTestId("brief-price")).toContainText("已過期");
  await expect(brief.getByTestId("brief-location")).toContainText("目的地或交通方式不同");
  await expect(brief.getByTestId("brief-risk")).toContainText("未命中不代表零風險");
  await expect(brief.getByTestId("brief-money")).toContainText("55,111");
  await expect(brief.getByTestId("brief-money")).toContainText("無法直接比較");
  await expect(brief.getByTestId("brief-verification")).toContainText("證據缺口");
  await expect(brief).not.toContainText(/987654321|winner|recommended|最佳|勝出|較安全/i);
  expect((await brief.boundingBox())!.y).toBeLessThan((await page.getByTestId("compare-desktop").boundingBox())!.y);
  await brief.screenshot({ path: testInfo.outputPath("difference-brief-desktop.png") });
  await brief.getByTestId("brief-price").locator("summary").first().click();
  await brief.getByTestId("brief-price").locator("summary").filter({ hasText: "市場成交單價中位數" }).first().click();
  await expect(brief.getByTestId("brief-price").getByText("來源：內政部不動產實價登錄", { exact: true }).first()).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(brief).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await brief.getByTestId("brief-price").locator("summary").first().click();
  await brief.screenshot({ path: testInfo.outputPath("difference-brief-mobile.png") });
  await page.reload();
  await expect(brief).toContainText("300");
  expect(providers).toEqual([]);
});

test("brief follows selection order and saved updates, and stops when identity needs revalidation", async ({ page }) => {
  await page.addInitScript((rows) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
  }, [e9Case(), e9Case("case-b")]);
  await page.goto("/compare?cases=case-b,case-a");
  const brief = page.getByTestId("compare-difference-brief");
  await expect(brief.getByTestId("brief-price").locator("dt").first()).toHaveText("A · 案件 B");
  await page.evaluate(() => {
    const key = "proptech.savedCases.v1";
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].data.journeyContext.propertyContext.askingPriceWan = 2780;
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  });
  await expect(brief.getByTestId("brief-price")).toContainText("300");
  await page.reload();
  await expect(brief.getByTestId("brief-price")).toContainText("300");
  await page.evaluate(() => {
    const key = "proptech.savedCases.v1";
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].data.propertyIdentityAnchor.revalidation = { status: "needs_revalidation", conflicts: ["coordinates"] };
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  });
  await expect(brief).toHaveCount(0);
  await expect(page.locator("main").getByRole("alert")).toContainText("重新確認");
});
