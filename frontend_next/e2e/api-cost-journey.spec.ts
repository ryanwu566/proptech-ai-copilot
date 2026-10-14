import { expect, test } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

test("saved representative journey, Save, Reopen, Compare and Report add zero analysis calls", async ({ page, baseURL }) => {
  const rows = [e9Case(), e9Case("case-b")];
  await page.addInitScript((saved) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(saved));
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
  }, rows);
  const calls: string[] = [];
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname.endsWith(".tile.openstreetmap.org") && request.resourceType() === "image") { await route.fulfill({ status: 204, body: "" }); return; }
    if (isProviderRequest(request, baseURL!)) {
      calls.push(`${request.method()} ${url.pathname}`);
      await route.abort();
      return;
    }
    await route.continue();
  });
  // Property identity and saved Market/Valuation, Location/Commute, Risk and
  // Overview evidence are consumed through their real workspace routes.
  for (const [section, heading] of [["overview", "物件總覽"], ["market", "價格與市場"], ["location", "區位與通勤"], ["risk", "風險與環境"], ["overview", "物件總覽"]]) {
    await page.goto(`/cases/case-a/${section}`);
    await expect(page.getByRole("heading", { level: 1, name: heading, exact: true })).toBeVisible();
    await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("臺灣大道三段100號");
    expect(calls).toEqual([]);
  }
  await page.getByRole("button", { name: "保存目前案件快照" }).click();
  await expect(page.getByTestId("overview-save-status")).toContainText("已保存目前已知狀態");
  await page.goto("/cases");
  await page.getByRole("link", { name: "開啟案件 A", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "物件總覽" })).toBeVisible();
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-desktop")).toBeVisible();
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-evidence")).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("report-evidence")).toBeVisible();
  expect(calls).toEqual([]);
});
