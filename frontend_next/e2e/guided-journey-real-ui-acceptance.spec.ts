import { expect, test } from "./fixtures";

/**
 * Gate 1: Real UI Acceptance — 5-Step Guided Property Decision Journey
 * ─────────────────────────────────────────────────────────────────────
 * The PRIMARY product flow is the 5-step Guided Journey on the dashboard.
 *
 * Steps:
 *   1. property   — 建立物件情境
 *   2. location   — 位置與資料證據
 *   3. price      — 價格與估價證據
 *   4. affordability — 資金與持有成本
 *   5. decision   — 看房決策摘要
 *
 * Legacy components (RiskSummaryPanel, 7-step BuyingWizard,
 * ImmersiveViewingWorkspace) are SECONDARY — reachable only through
 * the old ValuationPage flow, not the primary guided journey.
 *
 * Each test verifies:
 * A. REAL USER-REACHABLE PATH
 * B. COMPONENT-SPECIFIC LOCATOR
 * C. POSITIVE SEMANTIC ASSERTION
 */

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;

// ─── Journey titles by locale ──────────────────────────────────────────────

const JOURNEY_TITLE = {
  "zh-TW": "用五個步驟整理看房資訊",
  en: "Organize the viewing decision in five steps",
  ja: "内見判断を5つの手順で整理",
  ko: "내방 판단을 다섯 단계로 정리",
};

const STEP_TITLES = {
  property: { "zh-TW": "建立物件情境", en: "Establish property context", ja: "物件情報を整理", ko: "매물 정보 정리" },
  location: { "zh-TW": "位置與資料證據", en: "Location and evidence", ja: "位置と根拠", ko: "위치와 근거" },
  price: { "zh-TW": "價格與估價證據", en: "Price and valuation evidence", ja: "価格と査定の根拠", ko: "가격과 평가 근거" },
  affordability: { "zh-TW": "資金與持有成本", en: "Funding and holding costs", ja: "資金と保有コスト", ko: "자금과 보유 비용" },
  decision: { "zh-TW": "看房決策摘要", en: "Viewing decision summary", ja: "内見判断の要約", ko: "내방 판단 요약" },
};

// ─── Helpers ────────────────────────────────────────────────────────────────

async function switchLocale(page: import("@playwright/test").Page, locale: string) {
  // The locale switcher has a known aria-label pattern across locales
  const select = page.locator("select[aria-label*='語言'], select[aria-label*='language'], select[aria-label*='言語'], select[aria-label*='언어']").first();
  await select.selectOption(locale);
  // Wait for re-render by checking the heading changes to the target locale title
  if (locale !== "zh-TW") {
    await expect(page.getByRole("heading", { name: JOURNEY_TITLE[locale as keyof typeof JOURNEY_TITLE] })).toBeVisible({ timeout: 8000 });
  }
}

/** The Journey is the default dashboard — no navigation needed */
async function waitForJourney(page: import("@playwright/test").Page) {
  await expect(page.getByRole("heading", { name: JOURNEY_TITLE["zh-TW"] }).or(
    page.getByRole("heading", { name: JOURNEY_TITLE.en })
  ).or(
    page.getByRole("heading", { name: JOURNEY_TITLE.ja })
  ).or(
    page.getByRole("heading", { name: JOURNEY_TITLE.ko })
  )).toBeVisible({ timeout: 10000 });
}

/** Activate a step by clicking the step button in the stepper nav */
async function activateStep(page: import("@playwright/test").Page, stepTitle: string) {
  // Map title to step ID for later assertions
  const stepId = stepTitle.includes("物件") || stepTitle.includes("property") || stepTitle.includes("物件の") || stepTitle.includes("매물") ? "property"
    : stepTitle.includes("位置") || stepTitle.includes("Location") || stepTitle.includes("位置と") || stepTitle.includes("위치") ? "location"
    : stepTitle.includes("價格") || stepTitle.includes("Price") || stepTitle.includes("価格") || stepTitle.includes("가격") ? "price"
    : stepTitle.includes("資金") || stepTitle.includes("Funding") || stepTitle.includes("資金と") || stepTitle.includes("자금") ? "affordability"
    : "decision";

  // Use getByLabel with partial match to find the step button
  const stepBtn = page.getByLabel(new RegExp(stepTitle)).first();
  await expect(stepBtn).toBeVisible({ timeout: 5000 });
  await stepBtn.click();
  // Wait for the step section to be rendered and visible
  await expect(page.locator(`section[id="journey-stage-${stepId}"]`)).toBeVisible({ timeout: 8000 });
}

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 5: GUIDED JOURNEY — 5 STEPS DOM COUNT
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Guided Journey — 5-Step DOM Verification", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Journey visible with exactly 5 step buttons", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    // On desktop (1440px), step buttons are in the div that's lg:block
    // Both desktop and mobile sets exist in DOM, so filter by visibility
    const stepperNav = page.locator("nav[aria-label]").filter({ hasText: "建立物件情境" });
    const visibleButtons = stepperNav.locator("button[aria-label]:visible");
    await expect(visibleButtons).toHaveCount(5);
  });

  test("All 5 step labels are correct in zh-TW", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    const stepperNav = page.locator("nav[aria-label]").filter({ hasText: "建立物件情境" });
    const navText = await stepperNav.innerText();

    for (const [, title] of Object.entries(STEP_TITLES)) {
      expect(navText, `Step "${title["zh-TW"]}" visible`).toContain(title["zh-TW"]);
    }
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 6: STEP 1 — PROPERTY CONTEXT
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Step 1 — Property Context", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Step 1 is active by default with property tool card", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    // Step 1 button should be active (use first to avoid desktop+mobile duplicate)
    const step1Btn = page.locator("nav button[aria-current='step']", { hasText: "建立物件情境" }).first();
    await expect(step1Btn).toBeVisible();

    // Property tool card visible
    const toolCard = page.getByRole("button", { name: "開始輸入物件資料" });
    await expect(toolCard).toBeVisible();

    // Next step button available
    const nextBtn = page.getByRole("button", { name: /查看位置|位置與生活機能/ });
    await expect(nextBtn).toBeVisible();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 7: STEP 2 — LOCATION & EVIDENCE
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Step 2 — Location and Evidence", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Step 2 activates and shows location tools", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    // Activate step 2
    await activateStep(page, "位置與資料證據");

    // Step 2 content should be visible with its question
    await expect(page.locator("text=位置與可用的資料證據能說明什麼").or(
      page.getByRole("heading", { name: "位置與資料證據" }).nth(1)
    )).toBeVisible({ timeout: 5000 });

    // Location tool UI should be accessible
    const mainContent = page.locator("main").last();
    const text = await mainContent.innerText();
    expect(text).toMatch(/Location Insight|位置/);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 8: STEP 3 — PRICE & VALUATION
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Step 3 — Price and Valuation Evidence", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Step 3 activates and shows price/valuation UI", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    await activateStep(page, "價格與估價證據");

    // Step 3 content visible
    const mainContent = page.locator("main").last();
    const text = await mainContent.innerText();
    expect(text).toMatch(/價格|Valuation|估價|price/i);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 9: STEP 4 — AFFORDABILITY
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Step 4 — Funding and Holding Costs", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Step 4 activates and shows affordability tools", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    await activateStep(page, "資金與持有成本");

    const mainContent = page.locator("main").last();
    const text = await mainContent.innerText();
    // Should show loan/holding/tax related content
    expect(text).toMatch(/Loan|貸款|Holding|持有|TaxOracle|稅務/);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 10: STEP 5 — DECISION SUMMARY
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Step 5 — Decision Summary", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Step 5 activates and shows decision components", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    await activateStep(page, "看房決策摘要");

    // DecisionReadinessSummary has aria-labelledby="decision-readiness-summary-heading"
    const readiness = page.locator("#decision-readiness-summary-heading");
    await expect(readiness).toBeVisible({ timeout: 5000 });

    // DecisionAttentionPanel has id="decision-attention-heading"
    const attention = page.locator("#decision-attention-heading");
    await expect(attention).toBeVisible();

    // DecisionCaseStatusStrip has aria-label with case action title
    const statusStrip = page.locator("section").filter({ has: page.locator("text=物件狀態").or(page.locator("text=Property")) });
    await expect(statusStrip.first()).toBeVisible();
  });

  test("Step 5 decision readiness shows known item count", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    await activateStep(page, "看房決策摘要");

    // Readiness section — use the specific section with aria-labelledby
    const readinessSection = page.locator("section[aria-labelledby='decision-readiness-summary-heading']");
    const text = await readinessSection.innerText();
    // Contains the known count (a number) and readiness labels
    expect(text).toMatch(/\d/);
    // Should contain specific data status items
    expect(text).toMatch(/價格|Price|가격|価格/);
  });

  test("Step 5 attention panel shows items or empty state", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    await activateStep(page, "看房決策摘要");

    const attentionSection = page.locator("section[aria-labelledby='decision-attention-heading']");
    const text = await attentionSection.innerText();
    // Should show attention items or empty message
    expect(text).toMatch(/ATTENTION|待注意|注意/i);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 12: FOUR-LOCALE JOURNEY NAVIGATION
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Guided Journey — 4 Locale Verification", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const locale of LOCALES) {
    test(`${locale}: Journey title and 5 steps visible, no raw keys`, async ({ page }) => {
      await page.goto("/", { waitUntil: "domcontentloaded" });
      await switchLocale(page, locale);

      // Journey title
      const titleHeading = page.getByRole("heading", { name: JOURNEY_TITLE[locale] });
      await expect(titleHeading).toBeVisible({ timeout: 10000 });

      // 5 step buttons in stepper
      const stepperNav = page.locator("nav[aria-label]").filter({ has: page.locator("button[aria-label]") }).filter({ hasText: STEP_TITLES.property[locale] });
      const navButtons = stepperNav.locator("button[aria-label]:visible");
      await expect(navButtons).toHaveCount(5);

      // Each step title localized
      const navText = await stepperNav.innerText();
      for (const [, titles] of Object.entries(STEP_TITLES)) {
        expect(navText, `Step title "${titles[locale]}" visible in ${locale}`).toContain(titles[locale]);
      }

      // No raw translation keys leaked
      expect(navText).not.toMatch(/journey\.\w+\./);
    });

    test(`${locale}: Step 5 activates with localized decision content`, async ({ page }) => {
      await page.goto("/", { waitUntil: "domcontentloaded" });
      await switchLocale(page, locale);

      // Activate step 5
      await activateStep(page, STEP_TITLES.decision[locale]);

      // Decision heading visible
      const decisionHeading = page.locator("#decision-readiness-summary-heading");
      await expect(decisionHeading).toBeVisible({ timeout: 5000 });

      // Attention panel visible
      const attentionHeading = page.locator("#decision-attention-heading");
      await expect(attentionHeading).toBeVisible();

      // No raw keys in step content
      const mainText = await page.locator("main").last().innerText();
      expect(mainText).not.toMatch(/journey\.\w+\./);
      expect(mainText).not.toMatch(/decision\.\w+/);
    });
  }
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 13: MOBILE CORE SMOKE (390x844)
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Mobile 390x844 — Journey Usable", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("Mobile: Journey visible, steps accessible via mobile stepper", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await waitForJourney(page);

    // On mobile, the stepper is in a details element
    const mobileStepper = page.locator("details summary", { hasText: /選擇流程步驟|Select step/ });
    await expect(mobileStepper).toBeVisible({ timeout: 5000 });
    await mobileStepper.click();

    // Step buttons visible inside the opened details
    const navButtons = page.locator("details nav button, details div button").filter({ has: page.locator("strong") });
    const count = await navButtons.count();
    expect(count).toBe(5);

    // No horizontal overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(395); // 5px tolerance

    // Activate step 5 on mobile
    const step5Btn = navButtons.filter({ hasText: "看房決策摘要" });
    await step5Btn.click();

    // Decision components reachable on mobile
    await page.locator("#decision-readiness-summary-heading").scrollIntoViewIfNeeded();
    await expect(page.locator("#decision-readiness-summary-heading")).toBeVisible({ timeout: 5000 });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// LEGACY CLASSIFICATION
// ═════════════════════════════════════════════════════════════════════════════

/**
 * ARCHITECTURE CLASSIFICATION:
 *
 * PRIMARY (tested above):
 * - GuidedPropertyJourney (5 steps)
 * - DecisionCaseStage
 * - DecisionReadinessSummary
 * - DecisionAttentionPanel
 * - DecisionCaseStatusStrip
 *
 * LEGACY / SECONDARY (not tested here):
 * - RiskSummaryPanel (inside ImmersiveViewingWorkspace, reachable via sidebar 房價估算 → details)
 * - BuyingWizard / WorkflowCommandCenter (same path)
 * - ViewingDecisionPanel (old Dashboard fallback — unreachable in normal flow)
 * - ImmersiveViewingWorkspace (secondary path)
 */
