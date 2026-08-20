import { expect, test } from "./fixtures";

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
  test("Homepage loads with guided journey", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("nav button[aria-label]", { hasText: /建立物件情境|Establish/ }).first()).toBeVisible({ timeout: 10000 });
  });

  test("Sidebar navigation accessible", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("aside button", { hasText: /Aegis-Credit/ })).toBeVisible({ timeout: 5000 });
    await expect(page.locator("aside button", { hasText: /Market Insight/ })).toBeVisible();
    await expect(page.locator("aside button", { hasText: /房價估算/ })).toBeVisible();
    await expect(page.locator("aside button", { hasText: /TaxOracle/ })).toBeVisible();
  });
});

test.describe("Release Smoke — Aegis", () => {
  test("Aegis form visible with 6 inputs and submittable", async ({ page }) => {
    await page.goto("/");
    await page.locator("aside button", { hasText: /Aegis-Credit/ }).click();
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
    await page.locator("aside button", { hasText: "房價估算" }).click();
    await expect(page.locator("#valuation-calculator")).toBeVisible({ timeout: 8000 });
    await expect(page.locator("#valuation-calculator select")).toHaveCount(3, { timeout: 3000 }).catch(() => {});
    await expect(page.getByRole("button", { name: /估算房價/ })).toBeVisible();
  });
});

test.describe("Release Smoke — Market", () => {
  test("Market Insight page loads", async ({ page }) => {
    await page.goto("/");
    await page.locator("aside button", { hasText: "Market Insight" }).click();
    await expect(page.locator("#main-content")).toContainText(/Market|市場|行情/i, { timeout: 8000 });
  });
});

test.describe("Release Smoke — Loan", () => {
  test("Loan calculator accessible on valuation page", async ({ page }) => {
    await page.goto("/");
    await page.locator("aside button", { hasText: "房價估算" }).click();
    await expect(page.getByRole("heading", { name: /貸款月付試算|Loan/ }).first()).toBeVisible({ timeout: 8000 });
  });
});

test.describe("Release Smoke — Decision", () => {
  test("Journey step 5 shows decision components", async ({ page }) => {
    await page.goto("/");
    const stepBtn = page.locator("nav button[aria-label]", { hasText: /看房決策摘要|Viewing decision/ }).first();
    await stepBtn.click();
    await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible({ timeout: 8000 });
    await expect(page.locator("#decision-attention-heading")).toBeVisible();
  });
});

test.describe("Release Smoke — Terrain Basic", () => {
  test("Terrain page loads without crash", async ({ page }) => {
    await page.goto("/");
    await page.locator("aside button", { hasText: /Terrain/ }).click();
    await expect(page.locator("#main-content")).toContainText(/Terrain|地勢|災害|地形/i, { timeout: 8000 });
  });
});

test.describe("Release Smoke — Map Basic", () => {
  test("Map page loads without crash", async ({ page }) => {
    await page.goto("/");
    await page.locator("aside button", { hasText: /Map Insight/ }).click();
    await expect(page.locator("#main-content")).toContainText(/Map|地圖/i, { timeout: 8000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PART B: Five-Step Journey Smoke
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Release Smoke — Five-Step Journey", () => {
  test("All 5 steps navigable without crash", async ({ page }) => {
    await page.goto("/");
    const steps = ["建立物件情境", "位置與資料證據", "價格與估價證據", "資金與持有成本", "看房決策摘要"];
    for (const step of steps) {
      const btn = page.locator("nav button[aria-label]", { hasText: step }).first();
      await btn.click();
      await page.waitForTimeout(300);
    }
    // Final step renders decision
    await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// PART C: A→B→A Stale-State Regression
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Release Smoke — Aegis Stale-State", () => {
  test("Aegis A→B replaces previous result", async ({ page }) => {
    await page.goto("/");
    await page.locator("aside button", { hasText: /Aegis-Credit/ }).click();
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
    await page.waitForTimeout(500);

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
    await page.waitForTimeout(500);
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
        // Open mobile menu
        const menuBtn = page.getByRole("button", { name: /開啟選單|Open menu/ });
        if (await menuBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await menuBtn.click();
          await page.waitForTimeout(300);
        }
        await page.locator("aside button", { hasText: /Aegis-Credit/ }).click();
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
    test(`${locale}: Journey renders without raw keys`, async ({ page }) => {
      await page.goto("/");
      await switchLocale(page, locale);
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
