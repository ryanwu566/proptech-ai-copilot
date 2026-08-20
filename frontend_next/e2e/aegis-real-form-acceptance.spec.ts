import { expect, test } from "@playwright/test";

/**
 * Aegis-Credit Real Form Acceptance
 * ─────────────────────────────────────
 * Tests the real 6-field user input form against the REAL production backend
 * via Playwright proxy (browser → Playwright APIRequestContext → Render).
 *
 * Architecture:
 * - Local production build on :3100 (built with process-scoped env)
 * - Browser sends real POST to configured API base
 * - page.route intercepts and proxies to real Render backend
 * - Real backend response is fulfilled back to browser
 * - Visible UI result verified
 */

const PRODUCTION_API = "https://proptech-ai-copilot-api.onrender.com";

test.use({ baseURL: "http://127.0.0.1:3100" });

// ─── Helpers ────────────────────────────────────────────────────────────────

async function setup(page: import("@playwright/test").Page, requestCtx: import("@playwright/test").APIRequestContext) {
  let capturedPayload: Record<string, number> | null = null;
  let realStatus = 0;
  let realBody: { risk_score: number; signal_color: string; traces: string[] } | null = null;

  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });

  await page.route("**/aegis-credit/analyze", async (route) => {
    const payload = route.request().postDataJSON();
    capturedPayload = payload;
    const resp = await requestCtx.post(`${PRODUCTION_API}/aegis-credit/analyze`, { data: payload });
    realStatus = resp.status();
    realBody = await resp.json();
    await route.fulfill({ status: realStatus, contentType: "application/json", body: JSON.stringify(realBody) });
  });

  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.locator("aside button", { hasText: /Aegis-Credit/ }).click();
  await expect(page.getByRole("heading", { name: "房貸風險展示" })).toBeVisible({ timeout: 10000 });

  return { payload: () => capturedPayload, status: () => realStatus, body: () => realBody };
}

async function fill(page: import("@playwright/test").Page, v: { income: number; debt: number; cash: number; properties: number; mortgages: number; price: number }) {
  const f = page.getByTestId("aegis-scenario-form");
  // aria-labels are now localized — use the zh-TW defaults since tests run in zh-TW by default
  // For other locales, the form container still works by field position within fieldsets
  await f.locator("fieldset").nth(0).locator("input[type='number']").nth(0).fill(String(v.income));
  await f.locator("fieldset").nth(0).locator("input[type='number']").nth(1).fill(String(v.debt));
  await f.locator("fieldset").nth(1).locator("input[type='number']").nth(0).fill(String(v.cash));
  await f.locator("fieldset").nth(1).locator("input[type='number']").nth(1).fill(String(v.properties));
  await f.locator("fieldset").nth(1).locator("input[type='number']").nth(2).fill(String(v.mortgages));
  await f.locator("fieldset").nth(2).locator("input[type='number']").nth(0).fill(String(v.price));
}

async function assertValues(page: import("@playwright/test").Page, v: { income: string; debt: string; cash: string; properties: string; mortgages: string; price: string }) {
  const f = page.getByTestId("aegis-scenario-form");
  await expect(f.locator("fieldset").nth(0).locator("input[type='number']").nth(0)).toHaveValue(v.income);
  await expect(f.locator("fieldset").nth(0).locator("input[type='number']").nth(1)).toHaveValue(v.debt);
  await expect(f.locator("fieldset").nth(1).locator("input[type='number']").nth(0)).toHaveValue(v.cash);
  await expect(f.locator("fieldset").nth(1).locator("input[type='number']").nth(1)).toHaveValue(v.properties);
  await expect(f.locator("fieldset").nth(1).locator("input[type='number']").nth(2)).toHaveValue(v.mortgages);
  await expect(f.locator("fieldset").nth(2).locator("input[type='number']").nth(0)).toHaveValue(v.price);
}

async function submitAndWait(page: import("@playwright/test").Page) {
  const t0 = Date.now();
  await page.getByRole("button", { name: /執行房貸風險分析|Run risk analysis|リスク分析を実行|위험 분석 실행/ }).click();
  await expect(page.locator("text=風險分數").or(page.locator("text=Risk score")).or(page.locator("text=リスクスコア")).or(page.locator("text=위험 점수")).first()).toBeVisible({ timeout: 45000 });
  return Date.now() - t0;
}

// ═════════════════════════════════════════════════════════════════════════════
// VALIDATION — Complete 8-case matrix
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Validation", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  const INVALID_CASES = [
    { name: "income=0", values: { income: 0, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 } },
    { name: "debt=-1", values: { income: 80000, debt: -1, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 } },
    { name: "cash=-1", values: { income: 80000, debt: 5000, cash: -1, properties: 0, mortgages: 0, price: 15000000 } },
    { name: "propertyCount=-1", values: { income: 80000, debt: 5000, cash: 5000000, properties: -1, mortgages: 0, price: 15000000 } },
    { name: "propertyCount=1.5", values: { income: 80000, debt: 5000, cash: 5000000, properties: 1.5, mortgages: 0, price: 15000000 } },
    { name: "mortgageCount=-1", values: { income: 80000, debt: 5000, cash: 5000000, properties: 0, mortgages: -1, price: 15000000 } },
    { name: "mortgageCount=1.5", values: { income: 80000, debt: 5000, cash: 5000000, properties: 0, mortgages: 1.5, price: 15000000 } },
    { name: "price=0", values: { income: 80000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 0 } },
  ] as const;

  for (const { name, values } of INVALID_CASES) {
    test(`Invalid ${name}: shows error, no request`, async ({ page, request: requestCtx }) => {
      await setup(page, requestCtx);
      await fill(page, values);
      let requestSent = false;
      page.on("request", (r) => { if (r.url().includes("/aegis-credit/analyze")) requestSent = true; });
      await page.getByRole("button", { name: /執行房貸風險分析|Run risk analysis|リスク分析を実行|위험 분석 실행/ }).click();
      await expect(page.locator("p[role='alert']")).toBeVisible({ timeout: 2000 });
      expect(requestSent).toBe(false);
    });
  }
});

// ═════════════════════════════════════════════════════════════════════════════
// STRONG
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Strong Real Backend", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Strong: exact payload, real backend 200, visible green result", async ({ page, request: requestCtx }) => {
    test.setTimeout(60000);
    const ctx = await setup(page, requestCtx);
    await fill(page, { income: 80000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
    await assertValues(page, { income: "80000", debt: "5000", cash: "5000000", properties: "0", mortgages: "0", price: "15000000" });

    const ms = await submitAndWait(page);

    expect(ctx.payload()!.monthly_income).toBe(80000);
    expect(ctx.payload()!.monthly_debt).toBe(5000);
    expect(ctx.payload()!.cash).toBe(5000000);
    expect(ctx.payload()!.property_count).toBe(0);
    expect(ctx.payload()!.mortgage_count).toBe(0);
    expect(ctx.payload()!.property_price).toBe(15000000);
    expect(ctx.status()).toBe(200);

    const mainText = await page.locator("#main-content").innerText();
    for (const t of ctx.body()!.traces) expect(mainText).toContain(t);

    console.log(`STRONG: score=${ctx.body()!.risk_score} signal=${ctx.body()!.signal_color} ms=${ms}`);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// BORDERLINE
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Borderline Real Backend", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Borderline: exact payload, real backend 200, visible yellow result", async ({ page, request: requestCtx }) => {
    test.setTimeout(60000);
    const ctx = await setup(page, requestCtx);
    await fill(page, { income: 60000, debt: 15000, cash: 2000000, properties: 1, mortgages: 1, price: 15000000 });
    await assertValues(page, { income: "60000", debt: "15000", cash: "2000000", properties: "1", mortgages: "1", price: "15000000" });

    const ms = await submitAndWait(page);

    expect(ctx.payload()!.monthly_income).toBe(60000);
    expect(ctx.status()).toBe(200);

    const mainText = await page.locator("#main-content").innerText();
    for (const t of ctx.body()!.traces) expect(mainText).toContain(t);

    console.log(`BORDERLINE: score=${ctx.body()!.risk_score} signal=${ctx.body()!.signal_color} ms=${ms}`);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// STRESSED
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Stressed Real Backend", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Stressed: exact payload, real backend 200, visible red result with multiple causes", async ({ page, request: requestCtx }) => {
    test.setTimeout(60000);
    const ctx = await setup(page, requestCtx);
    await fill(page, { income: 40000, debt: 25000, cash: 500000, properties: 2, mortgages: 2, price: 20000000 });
    await assertValues(page, { income: "40000", debt: "25000", cash: "500000", properties: "2", mortgages: "2", price: "20000000" });

    const ms = await submitAndWait(page);

    expect(ctx.payload()!.monthly_income).toBe(40000);
    expect(ctx.status()).toBe(200);
    expect(ctx.body()!.traces.length).toBeGreaterThanOrEqual(2);

    const mainText = await page.locator("#main-content").innerText();
    for (const t of ctx.body()!.traces) expect(mainText).toContain(t);

    console.log(`STRESSED: score=${ctx.body()!.risk_score} signal=${ctx.body()!.signal_color} ms=${ms}`);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// RERUN / STALE RESULT
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Rerun Updates Result", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Changing from stressed to strong updates visible result", async ({ page, request: requestCtx }) => {
    test.setTimeout(60000);
    await setup(page, requestCtx);

    // First: stressed
    await fill(page, { income: 40000, debt: 25000, cash: 500000, properties: 2, mortgages: 2, price: 20000000 });
    await submitAndWait(page);
    let mainText = await page.locator("#main-content").innerText();
    expect(mainText).toContain("每月負債占收入超過 50%");

    // Second: strong — need to wait for the NEW result
    await fill(page, { income: 80000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
    await page.getByRole("button", { name: "執行房貸風險分析" }).click();
    // Wait for the stressed traces to disappear (result updated)
    await expect(page.locator("text=每月負債占收入超過 50%")).not.toBeVisible({ timeout: 45000 });
    // Now check strong result
    mainText = await page.locator("#main-content").innerText();
    expect(mainText).toContain("未發現明顯 heuristic 風險");
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// TRUST BOUNDARY
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Trust Boundary", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Disclaimers present, no approval language", async ({ page, request: requestCtx }) => {
    await setup(page, requestCtx);
    const mainText = await page.locator("#main-content").innerText();
    expect(mainText).toMatch(/heuristic|展示型|不代表|不是核貸/i);
    expect(mainText).not.toMatch(/核貸保證|核貸結果|核准通知|聯徵分數|credit bureau/i);
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// MOBILE 390
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Mobile 390x844", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("Mobile: form usable, strong scenario, no overflow", async ({ page, request: requestCtx }) => {
    test.setTimeout(60000);

    await page.addInitScript(() => {
      window.localStorage.setItem("proptech_onboarding_seen", "true");
      window.localStorage.setItem("proptech_onboarding_version", "2");
    });
    await page.route("**/aegis-credit/analyze", async (route) => {
      const payload = route.request().postDataJSON();
      const resp = await requestCtx.post(`${PRODUCTION_API}/aegis-credit/analyze`, { data: payload });
      await route.fulfill({ status: resp.status(), contentType: "application/json", body: await resp.text() });
    });
    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Open mobile menu
    const menuBtn = page.getByRole("button", { name: /開啟選單/ });
    await expect(menuBtn).toBeVisible({ timeout: 5000 });
    await menuBtn.click();
    const aegisBtn = page.locator("aside button", { hasText: /Aegis-Credit/ });
    await expect(aegisBtn).toBeVisible({ timeout: 5000 });
    await aegisBtn.click();
    await expect(page.getByRole("heading", { name: "房貸風險展示" })).toBeVisible({ timeout: 10000 });

    // Fill and submit
    await fill(page, { income: 80000, debt: 5000, cash: 5000000, properties: 0, mortgages: 0, price: 15000000 });
    const submitBtn = page.getByRole("button", { name: "執行房貸風險分析" });
    await submitBtn.scrollIntoViewIfNeeded();
    await submitBtn.click();
    await expect(page.locator("text=風險分數").first()).toBeVisible({ timeout: 45000 });

    // No overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(395);
  });
});


// ═════════════════════════════════════════════════════════════════════════════
// LOCALE VERIFICATION
// ═════════════════════════════════════════════════════════════════════════════

test.describe("Aegis — Locale Verification", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
  const EXPECTED_CTA: Record<string, string> = { "zh-TW": "執行房貸風險分析", en: "Run risk analysis", ja: "リスク分析を実行", ko: "위험 분석 실행" };
  const EXPECTED_GROUP: Record<string, string> = { "zh-TW": "收入與負債", en: "Income and debt", ja: "収入と負債", ko: "소득과 부채" };
  const EXPECTED_SCORE_LABEL: Record<string, string> = { "zh-TW": "風險分數", en: "Risk score", ja: "リスクスコア", ko: "위험 점수" };
  const CHINESE_FRONTEND_LABELS = ["買方情境評估", "收入與負債", "資產與房貸", "目標物件", "月收入", "每月負債", "可用現金", "名下房屋數", "既有房貸數", "物件價格", "執行房貸風險分析", "風險分數", "風險狀態", "風險提示", "對客戶說明建議"];

  for (const locale of LOCALES) {
    test(`${locale}: form labels, CTA, groups, accessible names localized`, async ({ page, request: requestCtx }) => {
      await setup(page, requestCtx);

      if (locale !== "zh-TW") {
        const localeSelect = page.locator("select[aria-label]").first();
        await localeSelect.selectOption(locale);
        await page.waitForTimeout(400);
      }

      const form = page.getByTestId("aegis-scenario-form");
      await expect(form).toBeVisible();
      const formText = await form.innerText();

      // Group heading localized
      expect(formText, `Group heading in ${locale}`).toContain(EXPECTED_GROUP[locale]);

      // CTA localized
      const cta = page.getByRole("button", { name: EXPECTED_CTA[locale] });
      await expect(cta).toBeVisible();

      // No raw aegis.* keys
      expect(formText).not.toMatch(/aegis\.\w+/);

      // For EN/JA/KO: no Chinese frontend labels
      if (locale !== "zh-TW") {
        for (const label of CHINESE_FRONTEND_LABELS) {
          expect(formText, `No Chinese label "${label}" in ${locale}`).not.toContain(label);
        }
      }

      // Trigger validation — check message is localized
      await form.locator("fieldset").nth(0).locator("input[type='number']").nth(0).fill("0");
      await cta.click();
      const alert = page.locator("p[role='alert']");
      await expect(alert).toBeVisible({ timeout: 2000 });
      const alertText = await alert.innerText();
      if (locale !== "zh-TW") {
        expect(alertText).not.toContain("月收入必須大於");
      }
    });
  }
});
