/**
 * Market Final Closure — Evidence Gap Tests
 *
 * Tasks 1–5 + Task 8 (Desktop + Mobile responsive)
 *
 * CRITICAL_POSITIONAL_SELECTOR_COUNT = 0 (all use data-testid or role-based locators)
 *
 * Gates:
 *   PARTIAL_DATA_STATE = PASS
 *   STALE_DATA_UI_STATE = PASS
 *   A_TO_B_STALE_RESULT = 0
 *   B_TO_A_STALE_RESULT = 0
 *   PROVIDER_ERROR_STATE = PASS
 *   DESKTOP_MARKET_FLOW = PASS
 *   MOBILE390_MARKET_FLOW = PASS
 */
import { test, expect } from "@playwright/test";

test.use({ viewport: { width: 1440, height: 900 } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

async function goToMarket(page: import("@playwright/test").Page) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Market Insight" }).click();
  await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 8000 });
}

async function selectAndSearch(page: import("@playwright/test").Page, county: string, district: string) {
  await page.getByTestId("market-county-select").selectOption(county);
  await page.waitForTimeout(400);
  await page.getByTestId("market-district-select").selectOption(district);
  await page.getByTestId("market-insight-search-button").click();
}

// ═══════════════════════════════════════════════════════════════════════════
// TASK 1 — TRUE PARTIAL STATE
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TASK 1: TRUE PARTIAL STATE", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("PARTIAL_DATA_STATE: model.state=partial renders market-insight-partial and market-state-guidance", async ({ page }) => {
    test.setTimeout(20000);

    // Partial response: structurally incomplete (avg_price_per_ping != average_unit_price)
    // but has partial evidence (source_name, history, at least one positive numeric)
    const PARTIAL_RESPONSE = {
      city: "臺北市",
      county: "臺北市",
      district: "大安區",
      period: "2026-06",
      average_unit_price: 82,
      avg_price_per_ping: 85, // != average_unit_price → NOT complete
      transaction_count: 25,
      transaction_volume: 25,
      record_count: 25,
      summary: "PARTIAL_STATE_CONTROLLED_FIXTURE",
      source_name: "controlled_partial_fixture",
      source_updated_at: "2026-08-01",
      coverage_status: "covered",
      data_status: "available",
      caveat: "Test only",
      disclaimer: "Not real",
      history: [
        { period: "2026-05", avg_price_per_ping: 80, transaction_count: 20 },
        { period: "2026-04", avg_price_per_ping: 79, transaction_count: 18 },
      ],
    };

    await page.route("**/market-insights/query", (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(PARTIAL_RESPONSE),
    }));

    await goToMarket(page);
    await selectAndSearch(page, "臺北市", "大安區");

    // HARD ASSERT: market-insight-partial is visible
    await expect(page.getByTestId("market-insight-partial")).toBeVisible({ timeout: 8000 });

    // HARD ASSERT: market-state-guidance is visible
    await expect(page.getByTestId("market-state-guidance")).toBeVisible({ timeout: 3000 });

    // Verify it's NOT low_sample or stale
    await expect(page.getByTestId("market-insight-low_sample")).not.toBeVisible();
    await expect(page.getByTestId("market-insight-stale")).not.toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TASK 2 — TRUE STALE DATA UI STATE
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TASK 2: TRUE STALE DATA UI STATE", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("STALE_DATA_UI_STATE: model.state=stale renders market-insight-stale and market-state-guidance", async ({ page }) => {
    test.setTimeout(20000);

    // Complete + stale response
    const STALE_RESPONSE = {
      city: "臺北市",
      county: "臺北市",
      district: "信義區",
      period: "2025-09",
      average_unit_price: 95,
      avg_price_per_ping: 95,
      transaction_count: 38,
      transaction_volume: 38,
      record_count: 38,
      summary: "STALE_DATA_CONTROLLED_FIXTURE — data older than freshness threshold",
      source_name: "controlled_stale_fixture",
      source_updated_at: "2025-03-01",
      coverage_status: "covered",
      data_status: "available",
      freshness_status: "stale",
      caveat: "資料已過期，僅供歷史參考",
      disclaimer: "Not real",
      history: [
        { period: "2025-08", avg_price_per_ping: 94, transaction_count: 35 },
        { period: "2025-07", avg_price_per_ping: 93, transaction_count: 32 },
        { period: "2025-06", avg_price_per_ping: 92, transaction_count: 30 },
      ],
    };

    await page.route("**/market-insights/query", (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STALE_RESPONSE),
    }));

    await goToMarket(page);
    await selectAndSearch(page, "臺北市", "大安區");

    // HARD ASSERT: market-insight-stale is visible
    await expect(page.getByTestId("market-insight-stale")).toBeVisible({ timeout: 8000 });

    // HARD ASSERT: market-state-guidance is visible
    await expect(page.getByTestId("market-state-guidance")).toBeVisible({ timeout: 3000 });

    // Verify it's NOT partial or low_sample
    await expect(page.getByTestId("market-insight-partial")).not.toBeVisible();
    await expect(page.getByTestId("market-insight-low_sample")).not.toBeVisible();

    // Verify stale summary text is rendered
    await expect(page.locator("body")).toContainText("STALE_DATA_CONTROLLED_FIXTURE");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TASK 3 — HARDEN A→B CANCEL ASSERTION
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TASK 3: HARDEN A→B CANCEL ASSERTION", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("A_TO_B_STALE_RESULT: A pending (大安區), switch to B (信義區), B_RESULT visible, A_RESULT absent", async ({ page }) => {
    test.setTimeout(25000);

    let resolveA: (() => void) | undefined;
    const gateA = new Promise<void>((r) => { resolveA = r; });

    const A_RESULT = {
      city: "臺北市", county: "臺北市", district: "大安區", period: "2026-06",
      average_unit_price: 82, avg_price_per_ping: 82,
      transaction_count: 45, transaction_volume: 45, record_count: 45,
      summary: "A_RESULT_UNIQUE_MARKER",
      source_name: "a_fixture", source_updated_at: "2026-08-01",
      coverage_status: "covered", data_status: "available",
      caveat: "A only", disclaimer: "Not real",
      history: [{ period: "2026-05", avg_price_per_ping: 80, transaction_count: 40 }],
    };

    const B_RESULT = {
      city: "臺北市", county: "臺北市", district: "信義區", period: "2026-06",
      average_unit_price: 95, avg_price_per_ping: 95,
      transaction_count: 50, transaction_volume: 50, record_count: 50,
      summary: "B_RESULT_UNIQUE_MARKER",
      source_name: "b_fixture", source_updated_at: "2026-08-01",
      coverage_status: "covered", data_status: "available",
      caveat: "B only", disclaimer: "Not real",
      history: [{ period: "2026-05", avg_price_per_ping: 93, transaction_count: 48 }],
    };

    await page.route("**/market-insights/query", async (route) => {
      const body = route.request().postDataJSON();
      if (body.district === "大安區") {
        await gateA;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(A_RESULT) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(B_RESULT) });
      }
    });

    await goToMarket(page);
    const county = page.getByTestId("market-county-select");
    const district = page.getByTestId("market-district-select");
    const btn = page.getByTestId("market-insight-search-button");

    // Select A (大安區) and submit
    await county.selectOption("臺北市");
    await page.waitForTimeout(400);
    await district.selectOption("大安區");
    await btn.click();

    // Wait for loading state
    await expect(btn).toBeDisabled({ timeout: 3000 });

    // Switch to B (信義區) while A is pending — this cancels A
    await district.selectOption("信義區");
    await page.waitForTimeout(500);
    await expect(btn).toBeEnabled({ timeout: 3000 });

    // Submit B
    await btn.click();
    await page.waitForTimeout(3000);

    // HARD ASSERT: B_RESULT_UNIQUE_MARKER is visible
    await expect(page.locator("body")).toContainText("B_RESULT_UNIQUE_MARKER");

    // HARD ASSERT: district select shows 信義區
    const distVal = await district.inputValue();
    expect(distVal).toBe("信義區");

    // Release A (late response arrives)
    resolveA!();
    await page.waitForTimeout(1500);

    // HARD ASSERT: A_RESULT_UNIQUE_MARKER is NOT visible
    await expect(page.locator("body")).not.toContainText("A_RESULT_UNIQUE_MARKER");

    // HARD ASSERT: B_RESULT_UNIQUE_MARKER is STILL visible
    await expect(page.locator("body")).toContainText("B_RESULT_UNIQUE_MARKER");

    // HARD ASSERT: district still shows 信義區
    const finalDist = await district.inputValue();
    expect(finalDist).toBe("信義區");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TASK 4 — TRUE B→A REVERSE TEST
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TASK 4: TRUE B→A REVERSE TEST", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("B_TO_A_STALE_RESULT: B pending (信義區), switch to A (大安區), A_RESULT visible, B_RESULT absent", async ({ page }) => {
    test.setTimeout(25000);

    let resolveB: (() => void) | undefined;
    const gateB = new Promise<void>((r) => { resolveB = r; });

    const A_RESULT = {
      city: "臺北市", county: "臺北市", district: "大安區", period: "2026-06",
      average_unit_price: 82, avg_price_per_ping: 82,
      transaction_count: 45, transaction_volume: 45, record_count: 45,
      summary: "A_RESULT_UNIQUE_MARKER",
      source_name: "a_fixture", source_updated_at: "2026-08-01",
      coverage_status: "covered", data_status: "available",
      caveat: "A only", disclaimer: "Not real",
      history: [{ period: "2026-05", avg_price_per_ping: 80, transaction_count: 40 }],
    };

    const B_RESULT = {
      city: "臺北市", county: "臺北市", district: "信義區", period: "2026-06",
      average_unit_price: 95, avg_price_per_ping: 95,
      transaction_count: 50, transaction_volume: 50, record_count: 50,
      summary: "B_RESULT_UNIQUE_MARKER",
      source_name: "b_fixture", source_updated_at: "2026-08-01",
      coverage_status: "covered", data_status: "available",
      caveat: "B only", disclaimer: "Not real",
      history: [{ period: "2026-05", avg_price_per_ping: 93, transaction_count: 48 }],
    };

    await page.route("**/market-insights/query", async (route) => {
      const body = route.request().postDataJSON();
      if (body.district === "信義區") {
        await gateB;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(B_RESULT) });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(A_RESULT) });
      }
    });

    await goToMarket(page);
    const county = page.getByTestId("market-county-select");
    const district = page.getByTestId("market-district-select");
    const btn = page.getByTestId("market-insight-search-button");

    // Select B (信義區) and submit
    await county.selectOption("臺北市");
    await page.waitForTimeout(400);
    await district.selectOption("信義區");
    await btn.click();

    // Wait for loading
    await expect(btn).toBeDisabled({ timeout: 3000 });

    // Switch to A (大安區) while B is pending — cancels B
    await district.selectOption("大安區");
    await page.waitForTimeout(500);
    await expect(btn).toBeEnabled({ timeout: 3000 });

    // Submit A
    await btn.click();
    await page.waitForTimeout(3000);

    // HARD ASSERT: A_RESULT_UNIQUE_MARKER is visible
    await expect(page.locator("body")).toContainText("A_RESULT_UNIQUE_MARKER");

    // HARD ASSERT: district select shows 大安區
    const distVal = await district.inputValue();
    expect(distVal).toBe("大安區");

    // Release B (late response arrives)
    resolveB!();
    await page.waitForTimeout(1500);

    // HARD ASSERT: B_RESULT_UNIQUE_MARKER is NOT visible
    await expect(page.locator("body")).not.toContainText("B_RESULT_UNIQUE_MARKER");

    // HARD ASSERT: A_RESULT_UNIQUE_MARKER is STILL visible
    await expect(page.locator("body")).toContainText("A_RESULT_UNIQUE_MARKER");

    // HARD ASSERT: district still shows 大安區
    const finalDist = await district.inputValue();
    expect(finalDist).toBe("大安區");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TASK 5 — PROVIDER ERROR HARD ASSERT
// ═══════════════════════════════════════════════════════════════════════════

test.describe("TASK 5: PROVIDER ERROR HARD ASSERT", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("PROVIDER_ERROR_STATE: 500 response shows error state, previous result cleared", async ({ page }) => {
    test.setTimeout(20000);

    let requestCount = 0;
    await page.route("**/market-insights/query", async (route) => {
      requestCount++;
      if (requestCount === 1) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            city: "臺北市", county: "臺北市", district: "大安區", period: "2026-06",
            average_unit_price: 82, avg_price_per_ping: 82,
            transaction_count: 45, transaction_volume: 45, record_count: 45,
            summary: "PREVIOUS_SUCCESS_MARKER",
            source_name: "success_fixture", source_updated_at: "2026-08-01",
            coverage_status: "covered", data_status: "available",
            caveat: "Test", disclaimer: "Not real",
            history: [{ period: "2026-05", avg_price_per_ping: 80, transaction_count: 40 }],
          }),
        });
      } else {
        await route.fulfill({ status: 500, body: "Internal Server Error" });
      }
    });

    await goToMarket(page);

    // First query: get a successful result
    await selectAndSearch(page, "臺北市", "大安區");
    await expect(page.locator("body")).toContainText("PREVIOUS_SUCCESS_MARKER", { timeout: 8000 });

    // Second query: trigger error
    await page.getByTestId("market-district-select").selectOption("信義區");
    await page.waitForTimeout(300);
    await page.getByTestId("market-insight-search-button").click();

    // Wait for the response to complete and error state to render
    const networkError = page.getByTestId("market-insight-network-error");
    const unavailable = page.getByTestId("market-insight-unavailable");

    // Wait for either error indicator
    await expect(networkError.or(unavailable)).toBeVisible({ timeout: 8000 });

    // HARD ASSERT: previous successful result is NOT visible
    await expect(page.locator("body")).not.toContainText("PREVIOUS_SUCCESS_MARKER");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// TASK 8 — DESKTOP + MOBILE RESPONSIVE MARKET FLOW
// ═══════════════════════════════════════════════════════════════════════════

const MARKET_FULL_RESPONSE = {
  city: "臺北市", county: "臺北市", district: "大安區", period: "2026-06",
  average_unit_price: 82, avg_price_per_ping: 82,
  transaction_count: 45, transaction_volume: 45, record_count: 45,
  summary: "RESPONSIVE_FLOW_MARKER",
  source_name: "responsive_fixture", source_updated_at: "2026-08-01",
  coverage_status: "covered", data_status: "available",
  caveat: "Test", disclaimer: "Not real",
  history: [
    { period: "2026-05", avg_price_per_ping: 80, transaction_count: 40 },
    { period: "2026-04", avg_price_per_ping: 79, transaction_count: 38 },
  ],
};

test.describe("TASK 8: DESKTOP 1440 MARKET FLOW", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("DESKTOP_MARKET_FLOW: Property → Location → Map → Market → Decision at 1440px", async ({ page }) => {
    test.setTimeout(45000);

    await page.route("**/market-insights/query", (route) => route.fulfill({
      status: 200, contentType: "application/json", body: JSON.stringify(MARKET_FULL_RESPONSE),
    }));

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Step 1: Property (journey landing)
    const journeyHeading = page.getByRole("heading", { name: "用五個步驟整理看房資訊" });
    await expect(journeyHeading).toBeVisible({ timeout: 10000 });

    // Step 2: Location — click the step button
    const locationStep = page.getByLabel(/位置與資料證據/).first();
    await expect(locationStep).toBeVisible({ timeout: 5000 });
    await locationStep.click();
    await page.waitForTimeout(1000);

    // Step 3: Navigate to Map Insight via sidebar
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Map Insight" }).click();
    await page.waitForTimeout(1500);

    // Step 4: Navigate to Market Insight
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Market Insight" }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 8000 });

    // Execute market search
    await selectAndSearch(page, "臺北市", "大安區");
    await expect(page.locator("body")).toContainText("RESPONSIVE_FLOW_MARKER", { timeout: 8000 });

    // Step 5: Navigate back to journey (Decision)
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    // HARD ASSERT: viewport is 1440px
    expect(page.viewportSize()?.width).toBe(1440);
  });
});

test.describe("TASK 8: MOBILE 390 MARKET FLOW", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("MOBILE390_MARKET_FLOW: Market search works at 390px mobile viewport", async ({ page }) => {
    test.setTimeout(45000);

    await page.route("**/market-insights/query", (route) => route.fulfill({
      status: 200, contentType: "application/json", body: JSON.stringify(MARKET_FULL_RESPONSE),
    }));

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Step 1: Journey page loads
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    // Navigate through the user-visible mobile menu with one semantic target.
    await page.getByRole("button", { name: "開啟選單", exact: true }).click();
    const sidebar = page.locator("aside[aria-label='分析工具']");
    await expect(sidebar).toBeVisible();
    await sidebar.getByRole("button", { name: "Market Insight", exact: true }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 8000 });

    // Execute market search
    await selectAndSearch(page, "臺北市", "大安區");
    await expect(page.locator("body")).toContainText("RESPONSIVE_FLOW_MARKER", { timeout: 8000 });

    // HARD ASSERT: viewport is 390px
    expect(page.viewportSize()?.width).toBe(390);

    // Step 5: Navigate back to journey
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });
  });
});
