import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { openPropertyEntry } from "./helpers/commercial-navigation";

/** E10 primary acceptance: task Home → saved case domains → Compare / Report.
 * Optional finder decision components retain their independent semantic coverage.
 * No primary five-step layout contract is assumed.
 */
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const ADDRESS = "臺中市西屯區臺灣大道三段100號";
const DOMAINS = [
  ["overview", "物件總覽"], ["market", "價格與市場"],
  ["location", "區位與通勤"], ["risk", "風險與環境"],
  ["finance", "資金與持有成本"],
] as const;
const HOME = {
  "zh-TW": ["看清物件證據，確認下一步", "首頁", "已儲存案件", "進階／方法", "開始物件評估"],
  en: ["Review property evidence. Know what to verify.", "Start", "Saved cases", "Methods", "Start property review"],
  ja: ["物件の根拠を整理し、次の確認へ", "ホーム", "保存済み案件", "手法", "物件の検討を開始"],
  ko: ["부동산 근거를 검토하고 다음을 확인하세요", "시작", "저장된 사례", "방법", "부동산 검토 시작"],
};
const DECISION = {
  "zh-TW": "看房決策摘要", en: "Viewing decision summary",
  ja: "内見判断の要約", ko: "내방 판단 요약",
};

async function seed(page: Page) {
  await page.addInitScript((rows) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) {
      localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    }
  }, [e9Case(), e9Case("case-b")]);
}
async function openCase(page: Page) {
  await seed(page);
  await page.goto("/");
  await page.locator(".commercial-recent-cases").getByRole("link", { name: "繼續案件 A", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/case-a\/overview$/);
}
async function domain(page: Page, section: typeof DOMAINS[number][0], label: string) {
  await page.locator(".workspace-navigation").getByRole("link", { name: label, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/cases/case-a/${section}$`));
  await expect(page.getByRole("heading", { level: 1, name: label, exact: true })).toBeVisible();
  await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(ADDRESS);
}
async function optionalDecision(page: Page, locale: keyof typeof HOME = "zh-TW") {
  await page.goto("/");
  await page.getByTestId("locale-switcher").selectOption(locale);
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
  await openPropertyEntry(page);
  const button = page.getByLabel(new RegExp(DECISION[locale])).filter({ visible: true });
  await button.click();
  await expect(page.locator("#journey-stage-decision")).toBeVisible();
}

test.describe("E10 commercial case capability acceptance", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Home resumes a case through Overview, Market, Location, Risk and Finance with one identity", async ({ page }) => {
    await openCase(page);
    for (const [section, label] of DOMAINS) await domain(page, section, label);
    await page.reload();
    await expect(page.getByRole("banner", { name: "目前物件" })).toContainText(ADDRESS);
    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("proptech.savedCases.v1")!)[0]);
    expect(stored.id).toBe("case-a");
    expect(stored.data.propertyIdentityAnchor.normalized_address).toBe(ADDRESS);
    expect(stored.data.journeyContext.activePriceWan).toBe(2480);
  });

  test("case outputs reach Report and Compare with the selected case evidence", async ({ page }) => {
    await openCase(page);
    const nav = page.locator(".workspace-navigation");
    await nav.getByRole("link", { name: "案件報告", exact: true }).click();
    await expect(page).toHaveURL(/\/cases\/case-a\/report$/);
    await expect(page.getByTestId("report-evidence")).toContainText(ADDRESS);
    await expect(page.getByTestId("report-evidence")).toContainText("55,111");
    await page.goBack();
    await nav.getByRole("link", { name: "比較案件", exact: true }).click();
    await expect(page).toHaveURL(/\/compare\?cases=case-a$/);
    await page.getByRole("checkbox", { name: "選擇 案件 B", exact: true }).check();
    await expect(page).toHaveURL(/cases=case-a,case-b/);
    await expect(page.getByTestId("compare-desktop")).toContainText("案件 A");
    await expect(page.getByTestId("compare-desktop")).toContainText("案件 B");
  });

  test("property entry starts from an address and the optional official finder remains reachable", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#commercial-address")).toBeVisible();
    await expect(page.locator("#journey-stage-property")).toBeHidden();
    await page.locator("#commercial-address").fill(ADDRESS);
    await page.getByRole("button", { name: "開始物件評估", exact: true }).click();
    await expect(page.locator("#journey-stage-location")).toBeVisible();
    await expect(page.getByTestId("journey-property-context")).toContainText(ADDRESS);
    await page.reload();
    await openPropertyEntry(page);
    const finder = page.locator("#property-finder");
    await expect(finder).toBeVisible();
    await expect(finder.getByRole("button", { name: "搜尋看屋方向" })).toBeVisible();
    await expect(page.locator("#journey-stage-location")).toHaveCount(0);
  });

  test("Location exposes the current property's map and bounded route evidence", async ({ page }) => {
    await openCase(page);
    await domain(page, "location", "區位與通勤");
    await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toBeVisible();
    await expect(page.getByTestId("commute-route-card").getByRole("textbox", { name: "目的地地址" })).toHaveValue("臺中車站");
    await expect(page.getByTestId("commute-route-card")).toContainText("24 分鐘");
  });

  test("Market exposes price bases, valuation availability and comparable evidence", async ({ page }) => {
    await openCase(page);
    await domain(page, "market", "價格與市場");
    await expect(page.getByTestId("market-price-context")).toContainText("2,480");
    await expect(page.getByTestId("market-price-context")).toContainText("1,850");
    await expect(page.getByRole("heading", { name: "可比成交證據" })).toBeVisible();
    await expect(page.locator("#main-content")).toContainText(/無法取得|尚未取得/);
  });

  test("Finance exposes loan, holding costs and tax with unassessed affordability preserved", async ({ page }) => {
    await openCase(page);
    await domain(page, "finance", "資金與持有成本");
    await expect(page.getByTestId("loan-summary")).toContainText("55,111");
    await expect(page.getByTestId("holding-summary")).toContainText("小計");
    await expect(page.getByTestId("affordability-status")).toContainText("未評估");
    await expect(page.locator("#main-content")).toContainText(/稅務|TaxOracle/);
  });

  test("Overview integrates decision, attention and unknown evidence without a safety claim", async ({ page }) => {
    await openCase(page);
    for (const title of ["決策摘要", "需要特別留意", "已掌握", "尚未確認", "下一步查證"]) {
      await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
    }
    for (const id of ["market", "location", "risk", "finance"]) {
      await expect(page.getByTestId(`overview-${id}-summary`)).toBeVisible();
    }
    await expect(page.getByTestId("overview-risk-summary")).toContainText(/目前無法取得|未知/);
    await expect(page.locator("#main-content")).not.toContainText(/已確認安全|保證核貸/);
  });

  test("optional decision readiness preserves known item count and price status", async ({ page }) => {
    await optionalDecision(page);
    const section = page.locator("section[aria-labelledby='decision-readiness-summary-heading']");
    await expect(section).toBeVisible();
    expect(await section.innerText()).toMatch(/\d/);
    await expect(section).toContainText(/價格|Price|가격|価格/);
  });

  test("optional decision attention preserves actionable items or explicit empty state", async ({ page }) => {
    await optionalDecision(page);
    const section = page.locator("section[aria-labelledby='decision-attention-heading']");
    await expect(section).toBeVisible();
    await expect(section).toContainText(/ATTENTION|待注意|注意/i);
  });

  for (const locale of LOCALES) {
    test(`${locale}: task Home and current navigation are localized without raw keys`, async ({ page }) => {
      await page.goto("/");
      await page.getByTestId("locale-switcher").selectOption(locale);
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      const [heading, home, cases, methods, start] = HOME[locale];
      await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
      const nav = page.locator(".commercial-global-nav");
      await expect(nav.getByRole("button", { name: home, exact: true })).toBeVisible();
      await expect(nav.getByRole("link", { name: cases, exact: true })).toBeVisible();
      await expect(page.locator(".commercial-methods > summary")).toHaveText(methods);
      await expect(page.getByRole("button", { name: start, exact: true })).toBeVisible();
      expect(await page.locator(".commercial-global-header").innerText()).not.toMatch(/commercial\.\w+|journey\.\w+\./);
      expect(await page.locator(".commercial-home").innerText()).not.toMatch(/commercial\.\w+/);
    });

    test(`${locale}: optional decision remains reachable with localized readiness and attention`, async ({ page }) => {
      await optionalDecision(page, locale);
      await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible();
      await expect(page.locator("#decision-attention-heading")).toBeVisible();
      const text = await page.locator("#journey-stage-decision").innerText();
      expect(text).not.toMatch(/journey\.\w+\./);
      expect(text).not.toMatch(/decision\.\w+/);
    });
  }
});

test.describe("E10 mobile case flow", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  test("390px case domains and outputs are reachable without page overflow", async ({ page }) => {
    await openCase(page);
    for (const [section, label] of DOMAINS) {
      await domain(page, section, label);
      expect(await page.evaluate(() => document.body.scrollWidth)).toBeLessThanOrEqual(395);
    }
    await page.locator(".workspace-navigation").getByRole("link", { name: "案件報告", exact: true }).click();
    await expect(page.getByTestId("report-evidence")).toContainText(ADDRESS);
    await page.goBack();
    await page.locator(".workspace-navigation").getByRole("link", { name: "比較案件", exact: true }).click();
    await page.getByRole("checkbox", { name: "選擇 案件 B", exact: true }).check();
    await expect(page.getByTestId("compare-mobile")).toBeVisible();
    expect(await page.evaluate(() => document.body.scrollWidth)).toBeLessThanOrEqual(395);
  });
});
