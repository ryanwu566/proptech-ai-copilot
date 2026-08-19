import { expect, test } from "./fixtures";

/**
 * B2-B5 True Dynamic E2E: Verifies actual runtime localization correctness.
 * Uses page state to verify no raw keys leak into rendered output.
 * Tests dynamic states through actual page interaction.
 */

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;

// Raw internal keys that must NEVER appear in user-visible text
const RAW_KEY_PATTERNS = [
  "riskSummary.label", "riskSummary.suggestion", "riskSummary.missing",
  "riskSummary.next", "riskSummary.burden", "riskSummary.location",
  "riskSummary.confidence", "riskSummary.titleLoan", "riskSummary.titleHolding",
  "riskSummary.titleLocation", "riskSummary.titlePrice", "riskSummary.titleConfidence",
  "riskSummary.priceUnknown", "riskSummary.priceOverpriced",
  "wizardStep.propertySearch", "wizardStep.valuation", "wizardStep.affordability",
  "wizardStep.location", "wizardStep.risk", "wizardStep.report", "wizardStep.tax",
  "wizard.introNote", "wizard.kicker", "wizard.stepLabel",
  "decision.readyToView", "decision.needsMoreData", "decision.clarifyRiskFirst",
  "decision.reason", "decision.rule",
];

async function switchLocale(page: import("@playwright/test").Page, locale: string) {
  const select = page.locator("select").first();
  await select.selectOption(locale);
  await expect.poll(() => page.locator("html").getAttribute("lang"), { timeout: 5000 }).toBe(locale);
}

// ────────────────────────────────────────────────────────────────
// RISK SUMMARY STATES (unknown / healthy / high-risk)
// The initial page load with no data = unknown state
// ────────────────────────────────────────────────────────────────

test.describe("Risk Summary Dynamic States", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of LOCALES) {
    test(`${locale}: unknown risk state - no raw keys in page`, async ({ page }) => {
      test.setTimeout(20000);
      await page.goto("/");
      await switchLocale(page, locale);

      // With no data injected, the app is in unknown/incomplete state
      const mainText = await page.locator("#main-content").innerText();
      expect(mainText.length).toBeGreaterThan(100);

      // No raw translation keys in visible text
      for (const pattern of RAW_KEY_PATTERNS) {
        expect(mainText, `Raw key "${pattern}" leaked in ${locale}`).not.toContain(pattern);
      }
    });
  }

  // The "unknown" state verification: page renders without data and shows appropriate labels
  test("EN unknown state: does NOT show Chinese risk labels", async ({ page }) => {
    test.setTimeout(15000);
    await page.goto("/");
    await switchLocale(page, "en");
    const mainText = await page.locator("#main-content").innerText();
    // These Chinese phrases are from the OLD risk summary before i18n
    expect(mainText).not.toContain("資料不足");
    expect(mainText).not.toContain("可進一步看屋");
    expect(mainText).not.toContain("需謹慎評估");
    expect(mainText).not.toContain("暫不建議");
  });

  test("KO unknown state: does NOT show Chinese risk labels", async ({ page }) => {
    test.setTimeout(15000);
    await page.goto("/");
    await switchLocale(page, "ko");
    const mainText = await page.locator("#main-content").innerText();
    expect(mainText).not.toContain("資料不足");
    expect(mainText).not.toContain("可進一步看屋");
    expect(mainText).not.toContain("暫不建議");
  });

  test("JA unknown state: does NOT show Chinese-only risk labels", async ({ page }) => {
    test.setTimeout(15000);
    await page.goto("/");
    await switchLocale(page, "ja");
    const mainText = await page.locator("#main-content").innerText();
    expect(mainText).not.toContain("可進一步看屋");
    expect(mainText).not.toContain("暫不建議");
    expect(mainText).not.toContain("需謹慎評估");
  });
});

// ────────────────────────────────────────────────────────────────
// VIEWING DECISION (needs_more_data is the default with no inputs)
// ────────────────────────────────────────────────────────────────

test.describe("Viewing Decision Dynamic States", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of ["en", "ja", "ko"] as const) {
    test(`${locale}: viewing decision area has no Chinese product copy`, async ({ page }) => {
      test.setTimeout(15000);
      await page.goto("/");
      await switchLocale(page, locale);

      const mainText = await page.locator("#main-content").innerText();

      // No Chinese viewing decision copy
      const chineseDecisionPhrases = [
        "可安排看屋", "建議補資料後再判斷", "先釐清風險再看屋",
        "已有高風險訊號", "核心分析已完成", "可進一步約看",
        "先看既有風險摘要", "再檢查估價",
        "尚缺", "資料不足、unknown",
      ];
      for (const phrase of chineseDecisionPhrases) {
        expect(mainText, `${locale}: Chinese decision copy "${phrase}"`).not.toContain(phrase);
      }
    });
  }

  test("all locales: no raw decision semantic IDs visible", async ({ page }) => {
    test.setTimeout(20000);
    await page.goto("/");
    for (const locale of LOCALES) {
      await switchLocale(page, locale);
      const mainText = await page.locator("#main-content").innerText();
      expect(mainText).not.toContain("decision.readyToView");
      expect(mainText).not.toContain("decision.needsMoreData");
      expect(mainText).not.toContain("decision.clarifyRiskFirst");
    }
  });
});

// ────────────────────────────────────────────────────────────────
// BUYING WIZARD (4-locale step labels)
// ────────────────────────────────────────────────────────────────

test.describe("Buying Wizard 4-Locale Steps", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of LOCALES) {
    test(`${locale}: wizard step labels are translated, not raw keys`, async ({ page }) => {
      test.setTimeout(15000);
      await page.goto("/");
      await switchLocale(page, locale);

      const mainText = await page.locator("#main-content").innerText();

      // No raw wizard step keys in visible text
      expect(mainText).not.toContain("wizardStep.propertySearch");
      expect(mainText).not.toContain("wizardStep.valuation");
      expect(mainText).not.toContain("wizardStep.affordability");
      expect(mainText).not.toContain("wizardStep.location");
      expect(mainText).not.toContain("wizardStep.risk");
      expect(mainText).not.toContain("wizardStep.report");
      expect(mainText).not.toContain("wizardStep.tax");

      // No raw wizard UI keys
      expect(mainText).not.toContain("wizard.introNote");
      expect(mainText).not.toContain("wizard.progress");
      expect(mainText).not.toContain("wizard.completedSummary");
      expect(mainText).not.toContain("wizard.goBack");
      expect(mainText).not.toContain("wizard.nextAction");
    });
  }
});

// ────────────────────────────────────────────────────────────────
// MOBILE DYNAMIC (360 / 390 / 430)
// ────────────────────────────────────────────────────────────────

test.describe("Mobile Dynamic 360/390/430", () => {
  const viewports = [
    { width: 360, height: 844, name: "360" },
    { width: 390, height: 844, name: "390" },
    { width: 430, height: 932, name: "430" },
  ];

  for (const vp of viewports) {
    test(`mobile ${vp.name} EN: no overflow, no raw keys, content renders`, async ({ page }) => {
      test.setTimeout(15000);
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await switchLocale(page, "en");

      // No horizontal overflow
      const docWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(docWidth).toBeLessThanOrEqual(vp.width + 2);

      // Content renders
      const main = page.locator("#main-content");
      await expect(main).toBeVisible();
      const mainText = await main.innerText();
      expect(mainText.length).toBeGreaterThan(50);

      // No raw keys
      expect(mainText).not.toContain("wizardStep.");
      expect(mainText).not.toContain("riskSummary.");
    });

    test(`mobile ${vp.name} KO: no overflow, no raw keys`, async ({ page }) => {
      test.setTimeout(15000);
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await switchLocale(page, "ko");

      const docWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(docWidth).toBeLessThanOrEqual(vp.width + 2);

      const mainText = await page.locator("#main-content").innerText();
      expect(mainText).not.toContain("wizardStep.");
      expect(mainText).not.toContain("riskSummary.");
      expect(mainText).not.toContain("decision.");
    });
  }
});

// ────────────────────────────────────────────────────────────────
// CONSOLE ERROR MONITORING
// ────────────────────────────────────────────────────────────────

test.describe("Console Error Check", () => {
  test("no page errors or hydration errors on load + locale switch", async ({ page }) => {
    test.setTimeout(20000);
    const pageErrors: string[] = [];
    page.on("pageerror", (err) => pageErrors.push(err.message));

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    for (const locale of LOCALES) {
      await switchLocale(page, locale);
    }
    await page.waitForTimeout(300);

    const hydrationErrors = pageErrors.filter((e) => /hydration|mismatch/i.test(e));
    expect(hydrationErrors, "Hydration errors").toEqual([]);
    expect(pageErrors, "Page errors").toEqual([]);
  });
});
