import { expect, test } from "./fixtures";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

const LEGACY_NAMES = /Market Insight|Map Insight|Terrain Risk|TaxOracle|Aegis|房價估算|物件身分方法|Property identity|進階案件規劃|Advanced case planning|競賽展示參考|Demo reference|探索功能|Explore features/;

test("Home has compact auth entry and global navigation exposes explicit account actions", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".commercial-global-header")).toHaveCount(0);
  await expect(page.locator(".commercial-home__auth").getByRole("link")).toHaveText(["登入", "建立帳戶"]);
  await expect(page.locator(".commercial-home__auth").getByTestId("locale-switcher")).toBeVisible();
  await page.goto("/cases");
  const header = page.locator(".commercial-global-header");
  await expect(header.locator(".commercial-global-nav").getByRole("link")).toHaveText(["首頁", "已儲存案件", "比較案件"]);
  await expect(header.locator(".commercial-global-tools").getByRole("link")).toHaveText(["登入", "建立帳戶"]);
  await expect(header.getByTestId("locale-switcher")).toBeVisible();
  await expect(header.getByRole("searchbox")).toHaveCount(0);
  await expect(header.locator(".commercial-methods")).toHaveCount(0);
  await expect(header).not.toContainText(LEGACY_NAMES);
  await expect(page.locator('a[href*="?tool="], a[href^="/vnext"], a[href$="/planning"]')).toHaveCount(0);
  await expect(header.locator('[aria-current="page"]')).toHaveCount(1);
});

test("case routes show no product catalogue and one active case destination", async ({ page }) => {
  await page.addInitScript((row) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row])), e9Case());
  await page.goto("/cases/case-a/risk");
  const header = page.locator(".commercial-global-header");
  await expect(header.locator(".commercial-methods")).toHaveCount(0);
  await expect(header).not.toContainText(LEGACY_NAMES);
  const nav = page.locator(".workspace-navigation");
  await expect(nav.locator("a")).toHaveText(["物件總覽", "價格與市場", "區位與通勤", "風險與環境", "資金與持有成本", "購屋決策室", "案件報告", "情境實驗室", /通勤/, /文件|證據/, "比較案件"]);
  await expect(nav.locator(".workspace-navigation__secondary")).toHaveCount(4);
  await expect(nav.locator('[aria-current="page"]')).toHaveText(["風險與環境"]);
  await expect(page.locator('a[href$="/planning"]')).toHaveCount(0);
  // Standalone case routes keep the same case navigation and tour entry, so none is a dead end.
  for (const [section, label] of [["report", "案件報告"], ["decision-room", "購屋決策室"], ["evidence", /證據/], ["commute-planner", /通勤/]] as const) {
    await page.goto(`/cases/case-a/${section}`);
    await expect(page.locator(".workspace-navigation")).toHaveCount(1);
    await expect(page.locator(".workspace-navigation [aria-current='page']")).toHaveText(label);
    await expect(page.locator(".workspace-navigation a[href='/cases/case-a/overview']")).toBeVisible();
    await expect(page.locator(".case-standalone-nav").getByTestId("tour-start")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});

test("retained legacy ?tool= URLs still open their page and move focus to its heading", async ({ page }) => {
  for (const tool of ["Map Insight Lite", "Terrain Risk", "TaxOracle", "Aegis-Credit Lite", "Market Insight Lite", "房價估算"]) {
    await page.goto(`/?tool=${encodeURIComponent(tool)}`);
    await expect(page.locator("[data-page-heading]")).toBeVisible();
    await expect(page.locator(".commercial-home")).toHaveCount(0);
  }
  await page.goto("/");
  await page.evaluate(() => { history.pushState(null, "", "/?tool=Map%20Insight%20Lite"); });
  await expect.poll(() => page.evaluate(() => document.activeElement?.hasAttribute("data-page-heading"))).toBe(true);
});
