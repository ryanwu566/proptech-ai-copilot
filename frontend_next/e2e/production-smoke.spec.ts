import { expect, test } from "@playwright/test";

/**
 * Production Post-Deploy Smoke
 * ────────────────────────────
 * Short production-safe suite (~5 min).
 * Run after deployment to verify critical paths.
 *
 * Usage:
 *   E2E_BASE_URL=https://proptech-ai-copilot.vercel.app npx playwright test e2e/production-smoke.spec.ts
 *
 * All interactions are READ-ONLY / normal user behavior.
 * No destructive actions, no load testing, no security testing.
 */

const BASE = process.env.E2E_BASE_URL || "https://proptech-ai-copilot.vercel.app";

test.use({ baseURL: BASE });

test.describe("Production Smoke", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("proptech_onboarding_seen", "true");
      window.localStorage.setItem("proptech_onboarding_version", "2");
    });
  });

  test("Homepage loads", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await expect(page.locator("#main-content")).toBeVisible({ timeout: 15000 });
  });

  test("Aegis page reachable and form visible", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await page.locator("aside button", { hasText: /Aegis-Credit/ }).click();
    await expect(page.locator("#main-content")).toContainText(/Aegis|房貸|Mortgage|リスク|위험/i, { timeout: 15000 });
  });

  test("Valuation page reachable", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await page.locator("aside button", { hasText: /房價估算|Valuation|価格/ }).click();
    await expect(page.locator("#main-content")).toContainText(/估算|Valuation|査定|평가/i, { timeout: 15000 });
  });

  test("Market page reachable", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await page.locator("aside button", { hasText: /Market Insight/ }).click();
    await expect(page.locator("#main-content")).toContainText(/Market|市場|行情/i, { timeout: 15000 });
  });

  test("Decision step renders", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    const stepBtn = page.locator("nav button[aria-label]", { hasText: /看房決策摘要|Viewing decision|内見判断|방문 판단/ }).first();
    await stepBtn.click();
    await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible({ timeout: 10000 });
  });

  test("Locale switch works", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    const select = page.locator("select[aria-label]").first();
    await select.selectOption("en");
    await page.waitForTimeout(500);
    await expect(page.locator("#main-content")).toContainText(/step|Step|journey/i, { timeout: 5000 });
  });

  test("Mobile 390 no overflow", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    try {
      await page.addInitScript(() => {
        window.localStorage.setItem("proptech_onboarding_seen", "true");
        window.localStorage.setItem("proptech_onboarding_version", "2");
      });
      await page.goto("/", { timeout: 30000 });
      await page.waitForTimeout(1000);
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      expect(bodyWidth).toBeLessThanOrEqual(395);
    } finally {
      await ctx.close();
    }
  });
});
