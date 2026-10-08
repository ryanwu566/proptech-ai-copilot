/**
 * True Dynamic Runtime E2E — Deterministic state verification.
 * Uses Playwright route mocking to construct exact runtime states.
 * Verifies actual component rendering, not just absence of raw keys.
 */
import { expect, test } from "./fixtures";
import { openMethod } from "./helpers/commercial-navigation";

// Helper: switch locale
async function switchLocale(page: import("@playwright/test").Page, locale: string) {
  const select = page.locator("select").first();
  await select.selectOption(locale);
  await expect.poll(() => page.locator("html").getAttribute("lang"), { timeout: 5000 }).toBe(locale);
}

test.describe("True Dynamic: Risk Summary States", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    test(`${locale}: Risk Summary UNKNOWN state`, async ({ page }) => {
      test.setTimeout(20000);
      await page.goto("/");
      await switchLocale(page, locale);

      // With no data provided (default fixture state), risk summary should be unknown
      const bodyText = await page.locator("#main-content").innerText();

      // No raw semantic keys
      expect(bodyText).not.toMatch(/riskSummary\.[a-zA-Z]/);
      expect(bodyText).not.toMatch(/wizardStep\.[a-z]/);
      expect(bodyText).not.toMatch(/decision\.[a-zA-Z]/);

      // No false positive/risk claims in unknown state
      // (Unknown state should not claim "safe" or "ready to view")
      if (locale === "en") {
        expect(bodyText).not.toContain("Worth viewing");
        expect(bodyText).not.toContain("Ready to schedule");
      }
    });
  }
});

test.describe("True Dynamic: Viewing Decision States", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    test(`${locale}: no raw decision IDs in page`, async ({ page }) => {
      test.setTimeout(15000);
      await page.goto("/");
      await switchLocale(page, locale);

      const text = await page.locator("#main-content").innerText();
      expect(text).not.toContain("decision.readyToView");
      expect(text).not.toContain("decision.needsMoreData");
      expect(text).not.toContain("decision.clarifyRiskFirst");
      expect(text).not.toContain("decision.reason");
    });
  }
});

test.describe("True Dynamic: Buying Wizard 4-Locale", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    test(`${locale}: wizard renders without raw keys`, async ({ page }) => {
      test.setTimeout(15000);
      await page.goto("/");
      await switchLocale(page, locale);

      const text = await page.locator("#main-content").innerText();
      expect(text).not.toContain("wizardStep.propertySearch");
      expect(text).not.toContain("wizardStep.valuation");
      expect(text).not.toContain("wizardStep.affordability");
      expect(text).not.toContain("wizard.introNote");
      expect(text).not.toContain("wizard.kicker");
      expect(text.length).toBeGreaterThan(200);
    });
  }
});

test.describe("True Dynamic: Aegis Real User Flow", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Aegis submit → result visible", async ({ page }) => {
    test.setTimeout(30000);
    // Override Aegis mock to return a meaningful result
    await page.route("**/aegis-credit/analyze", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          risk_score: 15,
          signal_color: "yellow",
          traces: ["月收入負擔比偏高", "自備款佔比需確認"],
          disclaimer: "本結果僅供初步參考，不代表銀行核貸判斷。",
        }),
      });
    });

    await page.goto("/");

    // Navigate through the public Methods entry and require the actual form.
    await openMethod(page, "Aegis-Credit");
    await expect(page.getByTestId("aegis-scenario-form")).toBeVisible({ timeout: 3000 });
    await page.waitForTimeout(500);
    await page.getByRole("button", { name: "執行房貸風險分析", exact: true }).click();

    const scenarioMetric = page.locator(".ds-metric").filter({ has: page.getByText("情境風險指標", { exact: true }) });
    await expect(scenarioMetric.getByText("情境風險指標", { exact: true })).toBeVisible();
    await expect(scenarioMetric.getByText("15", { exact: true })).toBeVisible();
    await expect(page.getByText("月收入負擔比偏高", { exact: false })).toBeVisible();
    await expect(page.getByText("自備款佔比需確認", { exact: false })).toBeVisible();

    // Look for Aegis form/section
    const aegisSection = page.locator("#main-content");
    const text = await aegisSection.innerText();

    // The mock fixture returns risk analysis data - verify no raw keys
    expect(text).not.toContain("aegis.");
    expect(text).not.toContain("undefined");
  });
});

test.describe("True Dynamic: Mobile Viewports", () => {
  const viewports = [
    { width: 360, height: 844, name: "360" },
    { width: 390, height: 844, name: "390" },
    { width: 430, height: 932, name: "430" },
  ];

  for (const vp of viewports) {
    test(`${vp.name}: no overflow, content renders, no raw keys`, async ({ page }) => {
      test.setTimeout(15000);
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await switchLocale(page, "en");

      const docWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(docWidth).toBeLessThanOrEqual(vp.width + 2);

      const main = page.locator("#main-content");
      await expect(main).toBeVisible();
      const text = await main.innerText();
      expect(text).not.toContain("wizardStep.");
      expect(text).not.toContain("riskSummary.");
      expect(text).not.toContain("decision.");
      expect(text.length).toBeGreaterThan(100);
    });
  }
});

test.describe("True Dynamic: Console/Error Monitoring", () => {
  test("no hydration or page errors across locale switches", async ({ page }) => {
    test.setTimeout(20000);
    const pageErrors: string[] = [];
    page.on("pageerror", (err) => pageErrors.push(err.message));

    await page.goto("/");
    for (const locale of ["zh-TW", "en", "ja", "ko"]) {
      await switchLocale(page, locale);
    }
    await page.waitForTimeout(300);

    const hydration = pageErrors.filter(e => /hydration|mismatch/i.test(e));
    expect(hydration).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
});
