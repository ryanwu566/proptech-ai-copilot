import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
const KEY = "proptech.savedCases.v1";
async function seed(page: Page) {
  await page.addInitScript(({ key, rows }) => {
    if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(rows));
  }, { key: KEY, rows: [e9Case(), e9Case("case-b")] });
}
async function openChecklist(page: Page, caseId = "case-a") {
  await page.goto(`/cases/${caseId}/overview`);
  await expect(page.getByRole("heading", { name: "證據查證清單", exact: true })).toBeVisible();
  await page.getByText("開啟完整查證清單", { exact: true }).click();
}
function item(page: Page, id = "risk-active_fault") { return page.getByTestId(`checklist-${id}`); }
async function markAndSave(page: Page) {
  await item(page).getByRole("checkbox", { name: "已由使用者核對：活動斷層／人工查證" }).check();
  await expect(page.getByRole("status").filter({ hasText: "尚未保存人工核對變更" })).toBeVisible();
  await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "人工核對狀態已保存" })).toBeVisible();
}

async function watchProviders(page: Page) {
  const requests: string[] = [];
  await page.route("**/*", async (route) => {
    const req = route.request(); const url = new URL(req.url());
    if (/googleapis|maps\.google|gstatic|earthengine|tdx\.transportdata/.test(url.hostname)
      || (["fetch", "xhr"].includes(req.resourceType()) && /\/(market|valuation|commute|location|terrain|satellite|geocod|places|routes|loan|holding-cost|tax)/.test(url.pathname) && !url.pathname.startsWith("/cases/"))) {
      requests.push(url.hostname + url.pathname); return route.abort();
    }
    await route.continue();
  });
  return requests;
}

for (const width of [1440, 1024, 390]) {
  test(`${width}px overview/check/uncheck/save/reopen/isolation and labels`, async ({ page }) => {
    await seed(page); await page.setViewportSize({ width, height: 900 }); await openChecklist(page);
    await expect(item(page)).toContainText("目前不支援");
    await expect(item(page)).toContainText("來源摘要未保存");
    await markAndSave(page); await page.reload();
    await page.getByText("開啟完整查證清單", { exact: true }).click();
    await expect(item(page).getByRole("checkbox")).toBeChecked();
    await expect(item(page)).toContainText("目前不支援");
    await openChecklist(page, "case-b"); await expect(item(page).getByRole("checkbox")).not.toBeChecked();
    await openChecklist(page); await expect(item(page).getByRole("checkbox")).toBeChecked();
    await item(page).getByRole("checkbox").focus(); await page.keyboard.press("Space");
    await expect(item(page).getByRole("checkbox")).not.toBeChecked();
    await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
    await page.reload(); await page.getByText("開啟完整查證清單", { exact: true }).click();
    await expect(item(page).getByRole("checkbox")).not.toBeChecked();
    await expect(item(page).getByLabel("人工核對狀態：活動斷層／人工查證")).toHaveValue("not_checked");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test("evidence changes preserve historical review and identity changes require recheck", async ({ page }) => {
  await seed(page); await openChecklist(page); await markAndSave(page);
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].data.riskEvidenceCheckedAt = "2026-10-09T03:00:00Z";
    rows[0].updatedAt = "2026-10-09T03:00:00Z";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  await expect(item(page)).toContainText("需再次核對");
  await expect(item(page).getByRole("checkbox")).not.toBeChecked();
  await expect(item(page)).toContainText("先前人工核對");
  await item(page).getByRole("checkbox").check();
  await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].data.propertyIdentityAnchor.revalidation.status = "needs_revalidation";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  await expect(item(page)).toContainText("需再次核對");
  await expect(item(page).getByRole("checkbox")).toBeDisabled();
});

test("storage failure is visible and preserves persisted state", async ({ page }) => {
  await seed(page); await openChecklist(page);
  await item(page).getByRole("checkbox").check();
  const before = await page.evaluate((key) => localStorage.getItem(key), KEY);
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException("full", "QuotaExceededError"); }; });
  await page.getByRole("button", { name: "保存人工核對", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "人工核對狀態未保存" })).toBeVisible();
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBe(before);
});

test("external updates block stale drafts and switching cases discards unsaved marks", async ({ page }) => {
  await seed(page); await openChecklist(page); await item(page).getByRole("checkbox").check();
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!); rows[0].updatedAt = "2026-10-09T04:00:00Z";
    rows[0].data.riskEvidenceCheckedAt = "2026-10-09T04:00:00Z";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  await expect(page.getByRole("button", { name: "保存人工核對", exact: true })).toBeDisabled();
  await expect(item(page)).toContainText("需再次核對");
  await page.getByRole("button", { name: "載入已保存核對狀態" }).click();
  await expect(item(page).getByRole("checkbox")).not.toBeChecked();
  await item(page).getByRole("checkbox").check();
  await openChecklist(page, "case-b"); await expect(item(page).getByRole("checkbox")).not.toBeChecked();
  await openChecklist(page); await expect(item(page).getByRole("checkbox")).not.toBeChecked();
});

test("frozen manual report and provider-free workflow", async ({ page }) => {
  await seed(page); const providerRequests = await watchProviders(page);
  await openChecklist(page); await markAndSave(page); await page.reload();
  await page.goto("/cases/case-a/report");
  const summary = page.getByTestId("report-manual-review");
  await expect(summary).toContainText("已由使用者核對");
  await expect(summary).toContainText("不代表官方查證");
  const frozen = await summary.innerText();
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!);
    rows[0].data.checklistReview.entries[0].state = "pending";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  await expect(page.getByTestId("snapshot-change")).toBeVisible(); expect(await summary.innerText()).toBe(frozen);
  const beforePrint = await page.evaluate((key) => localStorage.getItem(key), KEY);
  await page.evaluate(() => { window.print = () => { dispatchEvent(new Event("beforeprint")); dispatchEvent(new Event("afterprint")); }; });
  await page.getByRole("button", { name: "列印／另存 PDF" }).click();
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBe(beforePrint);
  expect(await summary.innerText()).toBe(frozen);
  await page.getByRole("button", { name: "載入較新快照" }).click();
  await expect(summary).toContainText("待人工核對");
  await page.goto("/compare?cases=case-a,case-b"); await expect(page.getByTestId("compare-desktop")).toBeVisible();
  expect(providerRequests).toEqual([]);
});

test("A4 PDF retains frozen manual actions without writing or provider requests", async ({ page }, testInfo) => {
  await seed(page); const requests = await watchProviders(page);
  await openChecklist(page); await markAndSave(page); await page.goto("/cases/case-a/report");
  const summary = page.getByTestId("report-manual-review"); await expect(summary).toContainText("已由使用者核對");
  const frozen = await summary.textContent();
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!); rows[0].data.checklistReview.entries[0].state = "pending";
    localStorage.setItem(key, JSON.stringify(rows)); dispatchEvent(new StorageEvent("storage", { key }));
  }, KEY);
  await expect(page.getByTestId("snapshot-change")).toBeVisible();
  const before = await page.evaluate((key) => localStorage.getItem(key), KEY);
  await page.emulateMedia({ media: "print" });
  await expect(summary).toBeVisible(); await expect(page.getByTestId("report-controls")).toBeHidden();
  const pdf = await page.pdf({ path: testInfo.outputPath("checklist-report-a4.pdf"), format: "A4", printBackground: true });
  expect(pdf.length).toBeGreaterThan(10000);
  expect(await summary.textContent()).toBe(frozen);
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBe(before);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await summary.screenshot({ path: testInfo.outputPath("checklist-print.png") });
  expect(requests).toEqual([]);
});

test("malformed checklist blocks report instead of claiming a successful manual review", async ({ page }) => {
  await seed(page); await openChecklist(page); await markAndSave(page);
  await page.evaluate((key) => {
    const rows = JSON.parse(localStorage.getItem(key)!); rows[0].data.checklistReview.version = 99;
    localStorage.setItem(key, JSON.stringify(rows));
  }, KEY);
  await page.goto("/cases/case-a/report");
  await expect(page.locator("main").getByRole("alert")).toContainText("無效");
  await expect(page.getByTestId("report-manual-review")).toHaveCount(0);
});
