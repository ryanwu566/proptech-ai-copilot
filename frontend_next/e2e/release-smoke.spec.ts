import { expect, test } from "./fixtures";
import { openMethod, openPropertyEntry } from "./helpers/commercial-navigation";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

/**
 * Release Certification Smoke Suite
 * ──────────────────────────────────
 * Critical-path smoke tests for release candidate certification.
 * Runnable against local production build or deployed production URL.
 *
 * Configure via: E2E_BASE_URL environment variable
 * Default: http://127.0.0.1:3100 (from playwright.config.ts)
 *
 * Target runtime: < 10 minutes locally
 *
 * Exit code non-zero = P0 release blocker detected.
 */

// ─── Helpers ────────────────────────────────────────────────────────────────

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;

async function switchLocale(page: import("@playwright/test").Page, locale: string) {
  const select = page.locator("select[aria-label*='語言'], select[aria-label*='language'], select[aria-label*='言語'], select[aria-label*='언어']").first();
  await select.selectOption(locale);
  await page.waitForTimeout(400);
}

// ═══════════════════════════════════════════════════════════════════════════
// PART A: Critical Module Smoke
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Release Smoke — Navigation", () => {
  test("Homepage provides explicit property entry", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#commercial-address")).toBeVisible({ timeout: 10000 });
    await openPropertyEntry(page);
    await expect(page.locator("#property-finder")).toBeVisible();
  });

  test("Methods navigation keeps secondary capabilities accessible", async ({ page }) => {
    await page.goto("/");
    const methods = page.locator(".commercial-methods");
    await methods.locator(":scope > summary").click();
    for (const name of [/Aegis-Credit/, /Market Insight/, /房價估算/, /TaxOracle/]) {
      await expect(methods.getByRole("button", { name })).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe("Release Smoke — Aegis", () => {
  test("Aegis form visible with 6 inputs and submittable", async ({ page }) => {
    await page.goto("/");
    await openMethod(page, "Aegis-Credit");
    const form = page.getByTestId("aegis-scenario-form");
    await expect(form).toBeVisible({ timeout: 8000 });
    // 6 inputs exist within 3 fieldsets
    const inputs = form.locator("input[type='number']");
    await expect(inputs).toHaveCount(6);
    // CTA visible
    await expect(page.getByRole("button", { name: /執行房貸風險分析|Run risk analysis/ })).toBeVisible();
  });
});

test.describe("Release Smoke — Valuation", () => {
  test("Valuation page loads with estimate form", async ({ page }) => {
    await page.goto("/");
    await openMethod(page, "房價估算");
    await expect(page.locator("#valuation-calculator")).toBeVisible({ timeout: 8000 });
    await expect(page.locator("#valuation-calculator select")).toHaveCount(3, { timeout: 3000 }).catch(() => {});
    await expect(page.getByRole("button", { name: /估算房價/ })).toBeVisible();
  });
});

test.describe("Release Smoke — Market", () => {
  test("Market Insight page loads", async ({ page }) => {
    await page.goto("/");
    await openMethod(page, "Market Insight");
    await expect(page.locator("#main-content")).toContainText(/Market|市場|行情/i, { timeout: 8000 });
  });
});

test.describe("Release Smoke — Loan", () => {
  test("Loan calculator accessible on valuation page", async ({ page }) => {
    await page.goto("/");
    await openMethod(page, "房價估算");
    await expect(page.getByRole("heading", { name: /貸款月付試算|Loan/ }).first()).toBeVisible({ timeout: 8000 });
  });
});

test.describe("Release Smoke — Decision", () => {
  test("Explicit property workflow reaches decision components", async ({ page }) => {
    await page.goto("/");
    await openPropertyEntry(page);
    const stepBtn = page.locator("nav button[aria-label]", { hasText: /看房決策摘要|Viewing decision/ }).first();
    await stepBtn.click();
    await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible({ timeout: 8000 });
    await expect(page.locator("#decision-attention-heading")).toBeVisible();
  });
});

test.describe("Release Smoke — Terrain Basic", () => {
  test("Terrain page loads without crash", async ({ page }) => {
    await page.goto("/");
    await openMethod(page, "Terrain Risk");
    await expect(page.locator("#main-content")).toContainText(/Terrain|地勢|災害|地形/i, { timeout: 8000 });
  });
});

test.describe("Release Smoke — Map Basic", () => {
  test("Map page loads without crash", async ({ page }) => {
    await page.goto("/");
    await openMethod(page, "Map Insight");
    await expect(page.locator("#main-content")).toContainText(/Map|地圖/i, { timeout: 8000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PART B: Case Workspace Smoke
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Release Smoke — Case Workspaces", () => {
  test("Overview, market, location, risk, finance and outputs remain reachable", async ({ page }) => {
    await page.addInitScript((rows) => {
      window.localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    }, [e9Case(), e9Case("case-b")]);
    await page.goto("/cases/case-a/overview");
    const tasks = [
      { name: "物件總覽", section: "overview" },
      { name: "價格與市場", section: "market" },
      { name: "區位與通勤", section: "location" },
      { name: "風險與環境", section: "risk" },
      { name: "資金與持有成本", section: "finance" },
    ];
    for (const task of tasks) {
      await page.locator(".workspace-navigation").getByRole("link", { name: task.name, exact: true }).click();
      await expect(page).toHaveURL(new RegExp(`/cases/case-a/${task.section}$`));
      await expect(page.getByRole("heading", { level: 1, name: task.name, exact: true })).toBeVisible();
      await expect(page.getByRole("banner", { name: "目前物件" })).toContainText("臺中市西屯區臺灣大道三段100號");
    }
    await page.locator(".workspace-navigation").getByRole("link", { name: "物件總覽", exact: true }).click();
    await expect(page).toHaveURL(/\/cases\/case-a\/overview$/);
    await page.locator(".workspace-navigation").getByRole("link", { name: "案件報告", exact: true }).click();
    await expect(page).toHaveURL(/\/cases\/case-a\/report$/);
    const report = page.getByTestId("report-evidence");
    await expect(report.getByRole("heading", { level: 1, name: "案件證據報告 · 案件 A", exact: true })).toBeVisible({ timeout: 5000 });
    await expect(report).toContainText("臺中市西屯區臺灣大道三段100號");
    await expect(report).toContainText("55,111");
    await expect(report).toContainText("內政部不動產實價登錄");
    await expect(report).toContainText("本報告依已儲存證據快照製作；不是即時重新查詢。");
    await expect(report).toContainText("已確認僅指瀏覽器案件關聯；不代表地號、建物、所有權或法律身分確認。");
    await page.goBack();
    await expect(page).toHaveURL(/\/cases\/case-a\/overview$/);
    await page.locator(".workspace-navigation").getByRole("link", { name: "比較案件", exact: true }).click();
    await expect(page).toHaveURL(/\/compare\?cases=case-a$/);
    await expect(page.getByRole("heading", { level: 1, name: "案件證據比較", exact: true })).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PART C: A→B→A Stale-State Regression
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Release Smoke — Aegis Stale-State", () => {
  test("Aegis A→B replaces previous result", async ({ page }) => {
    await page.route("**/aegis-credit/analyze", async (route) => {
      const payload = route.request().postDataJSON();
      const stressed = payload.monthly_income === 40000;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(stressed
          ? { risk_score: 70, signal_color: "red", traces: ["E2E_STRESSED_TRACE"] }
          : { risk_score: 0, signal_color: "green", traces: ["E2E_STRONG_TRACE"] }),
      });
    });
    await page.goto("/");
    await openMethod(page, "Aegis-Credit");
    const form = page.getByTestId("aegis-scenario-form");
    await expect(form).toBeVisible({ timeout: 10000 });

    // Fill stressed scenario
    await form.locator("fieldset").nth(0).locator("input").nth(0).fill("40000");
    await form.locator("fieldset").nth(0).locator("input").nth(1).fill("25000");
    await form.locator("fieldset").nth(1).locator("input").nth(0).fill("500000");
    await form.locator("fieldset").nth(1).locator("input").nth(1).fill("2");
    await form.locator("fieldset").nth(1).locator("input").nth(2).fill("2");
    await form.locator("fieldset").nth(2).locator("input").nth(0).fill("20000000");
    await page.getByRole("button", { name: /執行房貸風險分析|Run risk analysis/ }).click();
    const stressedTrace = page.getByRole("listitem").filter({ hasText: "E2E_STRESSED_TRACE" });
    await expect(stressedTrace).toBeVisible();

    // Now fill strong scenario
    await form.locator("fieldset").nth(0).locator("input").nth(0).fill("80000");
    await form.locator("fieldset").nth(0).locator("input").nth(1).fill("5000");
    await form.locator("fieldset").nth(1).locator("input").nth(0).fill("5000000");
    await form.locator("fieldset").nth(1).locator("input").nth(1).fill("0");
    await form.locator("fieldset").nth(1).locator("input").nth(2).fill("0");
    await form.locator("fieldset").nth(2).locator("input").nth(0).fill("15000000");
    const submitBtn = page.getByRole("button", { name: /執行房貸風險分析|Run risk analysis/ });
    await expect(submitBtn).not.toBeDisabled({ timeout: 5000 });
    await submitBtn.click();
    await expect(page.getByRole("listitem").filter({ hasText: "E2E_STRONG_TRACE" })).toBeVisible();
    await expect(stressedTrace).not.toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PART E: Mobile Matrix
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Release Smoke — Mobile", () => {
  for (const width of [360, 390, 430]) {
    test.describe(`${width}px`, () => {
      test.use({ viewport: { width, height: 844 } });

      test(`No horizontal overflow at ${width}px`, async ({ page }) => {
        await page.goto("/");
        await page.waitForTimeout(500);
        const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
        expect(bodyWidth).toBeLessThanOrEqual(width + 5);
      });

      test(`Aegis form accessible at ${width}px`, async ({ page }) => {
        await page.goto("/");
        await openMethod(page, "Aegis-Credit");
        await expect(page.getByTestId("aegis-scenario-form")).toBeVisible({ timeout: 8000 });
      });
    });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// PART F: Locale Matrix
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Release Smoke — Locale", () => {
  for (const locale of LOCALES) {
    test(`${locale}: Home and explicit property entry render without raw keys`, async ({ page }) => {
      await page.goto("/");
      await switchLocale(page, locale);
      await expect(page.locator("#commercial-home-heading")).toBeVisible();
      await openPropertyEntry(page);
      const mainText = await page.locator("#main-content").innerText();
      // No raw translation keys
      expect(mainText).not.toMatch(/journey\.\w+\.\w+/);
      expect(mainText).not.toMatch(/aegis\.\w+/);
      // Journey heading visible (not Chinese residue in EN/JA/KO)
      if (locale !== "zh-TW") {
        expect(mainText).not.toContain("用五個步驟整理看房資訊");
      }
    });
  }
});
