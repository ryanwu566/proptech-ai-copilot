import { expect, test } from "@playwright/test";

/**
 * Aegis-Credit Real Production UI Acceptance
 * ─────────────────────────────────────────────────────────────────
 * PRODUCTION: https://proptech-ai-copilot.vercel.app
 * BACKEND: https://proptech-ai-copilot-api.onrender.com
 *
 * ARCHITECTURE NOTE:
 * The current Aegis page uses a HARDCODED demo payload for the
 * "執行房貸風險分析" button. There are NO individual input fields
 * for monthly_income, monthly_debt, cash, property_count,
 * mortgage_count, or property_price.
 *
 * Therefore:
 * - UI acceptance verifies the FIXED-SCENARIO flow (navigate → submit → result)
 * - Scenario differentiation (Strong/Borderline/Stressed) is verified via
 *   direct API calls to confirm the backend heuristic logic works.
 * - Both are required for acceptance.
 *
 * Each UI test verifies:
 * A. REAL PRODUCTION PAGE — navigated via visible controls
 * B. REAL NETWORK REQUEST — POST to /aegis-credit/analyze observed
 * C. POSITIVE SEMANTIC RESULT — score, signal, and traces visible
 */

const PRODUCTION_URL = "https://proptech-ai-copilot.vercel.app";
const PRODUCTION_API = "https://proptech-ai-copilot-api.onrender.com";

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 1-3: REAL PRODUCTION UI — FIXED SCENARIO FLOW
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Real Production UI Flow", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Navigate to Aegis, submit, and verify result with network", async ({ browser }) => {
    test.setTimeout(90000);
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    try {
      await page.goto(PRODUCTION_URL, { waitUntil: "domcontentloaded", timeout: 30000 });

      // Dismiss onboarding if present
      const skipBtn = page.getByRole("button", { name: /略過|skip|スキップ/i });
      if (await skipBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await skipBtn.click();
      }

      // Navigate to Aegis via sidebar
      const aegisBtn = page.locator("aside button", { hasText: /Aegis-Credit|Aegis/ });
      await expect(aegisBtn).toBeVisible({ timeout: 10000 });
      await aegisBtn.click();

      // Wait for Aegis page content
      await expect(page.getByRole("heading", { name: "房貸風險展示" })).toBeVisible({ timeout: 15000 });

      // FORM VISIBLE: The submit button is the primary interaction
      const submitBtn = page.getByRole("button", { name: /執行房貸風險分析|分析中/ });
      await expect(submitBtn).toBeVisible({ timeout: 5000 });

      // Setup network listener BEFORE submit
      const requestPromise = page.waitForRequest((req) => req.url().includes("/aegis-credit/analyze"), { timeout: 15000 });
      const responsePromise = page.waitForResponse((res) => res.url().includes("/aegis-credit/analyze"), { timeout: 15000 });

      const t0 = Date.now();

      // SUBMIT
      await submitBtn.click();

      // Verify REAL network request
      const request = await requestPromise;
      expect(request.method()).toBe("POST");

      const response = await responsePromise;
      const t1 = Date.now();
      expect(response.status()).toBeGreaterThanOrEqual(200);
      expect(response.status()).toBeLessThan(300);

      // Wait for VISIBLE result
      await expect(page.locator("text=風險分數")).toBeVisible({ timeout: 10000 });
      const t2 = Date.now();

      // SEMANTIC ASSERTIONS on result
      const mainContent = await page.locator("#main-content").innerText();
      expect(mainContent).toMatch(/風險分數/);
      expect(mainContent).toMatch(/風險狀態/);
      expect(mainContent).toMatch(/風險提示/);

      // Score is a number
      const scoreMatch = mainContent.match(/風險分數[\s\S]*?(\d+)/);
      expect(scoreMatch).not.toBeNull();

      // Traces visible (at least one bullet point reason)
      expect(mainContent).toMatch(/•/);

      // Trust boundary: no POSITIVE bank approval claims
      // "不是核貸判定" / "不代表銀行核貸" are DISCLAIMERS (negations) — acceptable
      expect(mainContent).not.toMatch(/核貸保證|核貸結果|核准通知|loan approval guarantee|credit bureau score|聯徵分數/i);
      // Heuristic positioning visible (disclaimers present)
      expect(mainContent).toMatch(/heuristic|展示型|不代表|參考|不是核貸/i);

      // Timing
      const apiDuration = t1 - t0;
      const totalWait = t2 - t0;
      console.log(`AEGIS_API_DURATION_MS = ${apiDuration}`);
      console.log(`AEGIS_TOTAL_UI_WAIT_MS = ${totalWait}`);

      // Record
      console.log(`AEGIS_REQUEST_SEEN = YES`);
      console.log(`AEGIS_RESPONSE_2XX = YES`);

      await page.screenshot({ path: "test-results/aegis-production-result.png" });
    } finally {
      await context.close();
    }
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 3-5: BACKEND SCENARIO DIFFERENTIATION (API verification)
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Backend Scenario Differentiation", () => {

  test("Strong scenario returns low risk", async ({ request }) => {
    const response = await request.post(`${PRODUCTION_API}/aegis-credit/analyze`, {
      data: { monthly_income: 80000, monthly_debt: 5000, cash: 5000000, property_count: 0, mortgage_count: 0, property_price: 15000000 },
    });
    expect(response.status()).toBe(200);
    const result = await response.json();
    expect(result.risk_score).toBeDefined();
    expect(result.signal_color).toBeDefined();
    expect(result.traces).toBeDefined();
    expect(result.traces.length).toBeGreaterThan(0);
    // Strong scenario should have low risk
    expect(result.risk_score).toBeLessThanOrEqual(40);
    expect(result.signal_color).toBe("green");
    console.log(`STRONG_SCORE = ${result.risk_score}`);
    console.log(`STRONG_SIGNAL = ${result.signal_color}`);
    console.log(`STRONG_TRACES = ${result.traces.join(" | ")}`);
  });

  test("Borderline scenario returns medium risk", async ({ request }) => {
    const response = await request.post(`${PRODUCTION_API}/aegis-credit/analyze`, {
      data: { monthly_income: 60000, monthly_debt: 15000, cash: 2000000, property_count: 1, mortgage_count: 1, property_price: 15000000 },
    });
    expect(response.status()).toBe(200);
    const result = await response.json();
    expect(result.risk_score).toBeDefined();
    expect(result.signal_color).toBeDefined();
    expect(result.traces.length).toBeGreaterThan(0);
    // Borderline: yellow or elevated score
    expect(result.risk_score).toBeGreaterThan(20);
    expect(result.risk_score).toBeLessThan(80);
    console.log(`BORDERLINE_SCORE = ${result.risk_score}`);
    console.log(`BORDERLINE_SIGNAL = ${result.signal_color}`);
    console.log(`BORDERLINE_TRACES = ${result.traces.join(" | ")}`);
  });

  test("Stressed scenario returns high risk", async ({ request }) => {
    const response = await request.post(`${PRODUCTION_API}/aegis-credit/analyze`, {
      data: { monthly_income: 40000, monthly_debt: 25000, cash: 500000, property_count: 2, mortgage_count: 2, property_price: 20000000 },
    });
    expect(response.status()).toBe(200);
    const result = await response.json();
    expect(result.risk_score).toBeDefined();
    expect(result.signal_color).toBeDefined();
    expect(result.traces.length).toBeGreaterThanOrEqual(2);
    // Stressed: red/high
    expect(result.risk_score).toBeGreaterThanOrEqual(50);
    expect(result.signal_color).toBe("red");
    console.log(`STRESSED_SCORE = ${result.risk_score}`);
    console.log(`STRESSED_SIGNAL = ${result.signal_color}`);
    console.log(`STRESSED_TRACES = ${result.traces.join(" | ")}`);
  });

  test("Scenario differentiation: strong < stressed", async ({ request }) => {
    const [strongResp, stressedResp] = await Promise.all([
      request.post(`${PRODUCTION_API}/aegis-credit/analyze`, {
        data: { monthly_income: 80000, monthly_debt: 5000, cash: 5000000, property_count: 0, mortgage_count: 0, property_price: 15000000 },
      }),
      request.post(`${PRODUCTION_API}/aegis-credit/analyze`, {
        data: { monthly_income: 40000, monthly_debt: 25000, cash: 500000, property_count: 2, mortgage_count: 2, property_price: 20000000 },
      }),
    ]);
    const strong = await strongResp.json();
    const stressed = await stressedResp.json();
    expect(strong.risk_score).toBeLessThan(stressed.risk_score);
    console.log(`DIFFERENTIATION: strong=${strong.risk_score} < stressed=${stressed.risk_score}`);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 7: ERROR STATE
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Error Handling", () => {

  test("Invalid zero income returns valid response without crash", async ({ request }) => {
    const response = await request.post(`${PRODUCTION_API}/aegis-credit/analyze`, {
      data: { monthly_income: 0, monthly_debt: 0, cash: 0, property_count: 0, mortgage_count: 0, property_price: 0 },
    });
    // Should either return a valid response or a clean 422
    expect(response.status()).toBeLessThan(500);
    if (response.status() === 200) {
      const result = await response.json();
      expect(result).toHaveProperty("risk_score");
      expect(result).toHaveProperty("signal_color");
    }
    // No 500 error, no crash
    console.log(`ERROR_STATE_STATUS = ${response.status()}`);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 8: TRUST BOUNDARY (verified in UI test above)
// PHASE 9: LOCALE VERIFICATION
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Locale Verification", () => {
  const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;

  for (const locale of LOCALES) {
    test(`${locale}: Aegis page reachable and submit works`, async ({ browser }) => {
      test.setTimeout(90000);
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await context.newPage();

      try {
        await page.goto(PRODUCTION_URL, { waitUntil: "domcontentloaded", timeout: 30000 });

        // Dismiss onboarding
        const skipBtn = page.getByRole("button", { name: /略過|skip|スキップ|건너뛰기/i });
        if (await skipBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await skipBtn.click();
        }

        // Switch locale if needed
        if (locale !== "zh-TW") {
          const localeSelect = page.locator("select[aria-label]").first();
          await localeSelect.selectOption(locale);
          await page.waitForTimeout(500);
        }

        // Navigate to Aegis
        const aegisBtn = page.locator("aside button", { hasText: /Aegis-Credit|Aegis/ });
        await expect(aegisBtn).toBeVisible({ timeout: 10000 });
        await aegisBtn.click();

        // Wait for Aegis submit button — it's always "執行房貸風險分析" (hardcoded Chinese)
        const submitBtn = page.getByRole("button", { name: "執行房貸風險分析" });
        await expect(submitBtn).toBeVisible({ timeout: 15000 });

        // Submit and wait for result
        const responsePromise = page.waitForResponse((res) => res.url().includes("/aegis-credit/analyze"), { timeout: 30000 });
        await submitBtn.click();
        const response = await responsePromise;
        expect(response.status()).toBeLessThan(300);

        // Result visible — "風險分數" label is always in Chinese on this page
        await expect(page.locator("text=風險分數").first()).toBeVisible({ timeout: 10000 });

        // No raw keys
        const mainText = await page.locator("#main-content").innerText();
        expect(mainText).not.toMatch(/riskSummary\.\w+/);

        // Trust boundary maintained
        expect(mainText).not.toMatch(/核貸保證|loan approval guarantee|融資承認保証/i);
      } finally {
        await context.close();
      }
    });
  }
});

// ═════════════════════════════════════════════════════════════════════════════
// PHASE 10: MOBILE 390x844
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Mobile 390x844", () => {

  test("Mobile: Aegis form usable, submit works, result visible", async ({ browser }) => {
    test.setTimeout(90000);
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();

    try {
      await page.goto(PRODUCTION_URL, { waitUntil: "domcontentloaded", timeout: 30000 });

      // Dismiss onboarding
      const skipBtn = page.getByRole("button", { name: /略過|skip/i });
      if (await skipBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await skipBtn.click();
      }

      // Open mobile menu — the button is "開啟選單"
      const menuBtn = page.getByRole("button", { name: /開啟選單/ });
      await expect(menuBtn).toBeVisible({ timeout: 5000 });
      await menuBtn.click();

      // Wait for sidebar to become interactable (translate-x-0 applied)
      const aegisBtn = page.locator("aside button", { hasText: /Aegis-Credit/ });
      await expect(aegisBtn).toBeVisible({ timeout: 5000 });
      await aegisBtn.click();

      // Wait for Aegis page heading
      await expect(page.getByRole("heading", { name: "房貸風險展示" })).toBeVisible({ timeout: 15000 });

      // Wait for submit button
      const submitBtn = page.getByRole("button", { name: "執行房貸風險分析" });
      await submitBtn.scrollIntoViewIfNeeded();
      await expect(submitBtn).toBeVisible({ timeout: 10000 });

      // Submit
      const responsePromise = page.waitForResponse((res) => res.url().includes("/aegis-credit/analyze"), { timeout: 30000 });
      await submitBtn.click();
      const response = await responsePromise;
      expect(response.status()).toBeLessThan(300);

      // Result visible
      await expect(page.locator("text=風險分數").first()).toBeVisible({ timeout: 10000 });

      // No horizontal overflow
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      expect(bodyWidth).toBeLessThanOrEqual(395);
    } finally {
      await context.close();
    }
  });
});
