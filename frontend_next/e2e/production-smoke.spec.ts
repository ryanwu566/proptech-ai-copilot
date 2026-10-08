import { expect, test } from "@playwright/test";
import { openMethod, openPropertyEntry } from "./helpers/commercial-navigation";

/**
 * Production Post-Deploy Smoke
 * ────────────────────────────
 * Short production-safe suite (~5 min).
 * Run after deployment to verify critical paths.
 *
 * Usage:
 *   HOSTED_FRONTEND_URL=https://proptech-ai-copilot.vercel.app npm run test:e2e:hosted
 *
 * All interactions are READ-ONLY / normal user behavior.
 * No destructive actions, no load testing, no security testing.
 */

test.describe("Production Smoke", { tag: "@hosted" }, () => {
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
    const home = page.locator(".commercial-home");
    await expect(home).toHaveCount(1);
    await expect(home.getByRole("heading", { level: 1 })).toHaveText("看清物件證據，確認下一步");
    await expect(home.getByRole("textbox", { name: "物件地址", exact: true })).toBeVisible();
    expect(await page.evaluate(() => {
      const entry = document.querySelector(".commercial-home__start");
      const cases = document.querySelector(".commercial-home > .ds-section");
      return Boolean(entry && cases && (entry.compareDocumentPosition(cases) & Node.DOCUMENT_POSITION_FOLLOWING));
    })).toBe(true);
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);

    await page.getByTestId("locale-switcher").selectOption("en");
    await expect(home.getByRole("heading", { level: 1 })).toHaveText("Review property evidence. Know what to verify.");
    const address = "臺中市西屯區臺灣大道三段100號";
    await home.getByRole("textbox", { name: "Property address", exact: true }).fill(address);
    const primaryCta = home.getByRole("button", { name: "Start property review", exact: true });
    await expect(primaryCta).toBeVisible();
    await primaryCta.click();
    await expect(page.locator("#journey-stage-location")).toBeVisible();
    await expect(page.locator("#location-insight-calculator").getByRole("textbox").first()).toHaveValue(address);
    await openPropertyEntry(page);
    await expect(page.locator("#journey-stage-property")).toBeVisible();
  });

  test("Aegis page reachable and form visible", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await openMethod(page, "Aegis-Credit");
    await expect(page.getByTestId("aegis-scenario-form")).toBeVisible();
    await expect(page.locator("#main-content")).toContainText(/Aegis|房貸|Mortgage|リスク|위험/i, { timeout: 15000 });
  });

  test("Valuation page reachable", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await openMethod(page, /房價估算|Valuation|価格/);
    await expect(page.locator("#main-content")).toContainText(/估算|Valuation|査定|평가/i, { timeout: 15000 });
  });

  test("Market page reachable", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await openMethod(page, "Market Insight");
    await expect(page.locator("#main-content")).toContainText(/Market|市場|行情/i, { timeout: 15000 });
  });

  test("Decision step renders", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    await openPropertyEntry(page);
    const stepBtn = page.locator("nav button[aria-label]", { hasText: /看房決策摘要|Viewing decision|内見判断|방문 판단/ }).first();
    await stepBtn.click();
    await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible({ timeout: 10000 });
  });

  test("Locale switch works", async ({ page }) => {
    await page.goto("/", { timeout: 30000 });
    const select = page.locator("select[aria-label]").first();
    await select.selectOption("en");
    await page.waitForTimeout(500);
    await expect(page.locator("#commercial-home-heading")).toHaveText("Review property evidence. Know what to verify.", { timeout: 5000 });
  });

  test("Mobile 390 no overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/", { timeout: 30000 });
    await page.waitForTimeout(1000);
    await expect(page.locator(".commercial-home")).toHaveCount(1);
    await expect(page.getByRole("textbox", { name: "物件地址", exact: true })).toBeVisible();
    await openPropertyEntry(page);
    await expect(page.locator("#journey-stage-property")).toBeVisible();
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(395);
  });
});
