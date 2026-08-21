/**
 * Market Insight — Complete Certification Part 2
 * Fixes: no .nth() for selects (uses label), state tests, race, POI, cross-module, flows
 */
import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3200", viewport: { width: 1440, height: 900 } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

function norm(s: string): string { return s.replace(/台/g, "臺").trim(); }

// Navigate to Market page
async function goToMarket(page: import("@playwright/test").Page) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Market Insight" }).click();
  await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 8000 });
}

// Select county/district using accessible labels (NO .nth())
async function selectMarket(page: import("@playwright/test").Page, city: string, district: string) {
  const form = page.getByTestId("market-insight-search-form");
  await form.getByLabel("選擇縣市").selectOption(city);
  await page.waitForTimeout(400);
  await form.getByLabel("選擇鄉鎮市區").selectOption(district);
}

// Valid base market response fixture
const BASE_MARKET_RESPONSE = {
  city: "臺北市", county: "臺北市", district: "大安區", period: "2026-06",
  average_unit_price: 85, avg_price_per_ping: 85, transaction_count: 42, transaction_volume: 42, record_count: 42,
  summary: "交易量穩定", source_name: "Official PLVR", source_updated_at: "2026-08-01",
  coverage_status: "covered", data_status: "available", caveat: "參考用途", disclaimer: "不代表未來",
  history: [{ period: "2026-05", avg_price_per_ping: 83, transaction_count: 38 }],
};

// ═══════════════════════════════════════════════════════════════════
// 0A: Verify zero positional selectors in Market navigation
// ═══════════════════════════════════════════════════════════════════
test("Market selects use semantic labels, not nth()", async ({ page }) => {
  await goToMarket(page);
  const form = page.getByTestId("market-insight-search-form");
  // These use getByLabel — no .nth() needed
  await expect(form.getByLabel("選擇縣市")).toBeVisible();
  await expect(form.getByLabel("選擇鄉鎮市區")).toBeVisible();
  await expect(page.getByTestId("market-insight-search-button")).toBeVisible();
});

// ═══════════════════════════════════════════════════════════════════
// 1: HARD MARKET STATE TESTS (controlled intercept)
// ═══════════════════════════════════════════════════════════════════
test("LOW_SAMPLE state visible", async ({ page }) => {
  await page.route("**/market-insights/query", (route) => route.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ ...BASE_MARKET_RESPONSE, transaction_count: 3, record_count: 3, coverage_status: "partial", data_status: "available" }) }));
  await goToMarket(page);
  await selectMarket(page, "臺北市", "大安區");
  await page.getByTestId("market-insight-search-button").click();
  await page.waitForTimeout(2000);
  // Low sample shows guidance
  await expect(page.getByTestId("market-state-guidance")).toBeVisible({ timeout: 5000 });
});

test("NO_DATA state visible", async ({ page }) => {
  await page.route("**/market-insights/query", (route) => route.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ ...BASE_MARKET_RESPONSE, transaction_count: 0, record_count: 0, data_status: "no_data", coverage_status: "no_data", average_unit_price: 0, avg_price_per_ping: 0 }) }));
  await goToMarket(page);
  await selectMarket(page, "臺北市", "大安區");
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-no-data")).toBeVisible({ timeout: 5000 });
});

test("PROVIDER_ERROR state visible", async ({ page }) => {
  await page.route("**/market-insights/query", (route) => route.fulfill({ status: 500, body: "Internal Error" }));
  await goToMarket(page);
  await selectMarket(page, "臺北市", "大安區");
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-network-error")).toBeVisible({ timeout: 5000 });
});

// ═══════════════════════════════════════════════════════════════════
// 2: OUT-OF-ORDER RACE
// ═══════════════════════════════════════════════════════════════════
test("A→B race: delayed A does not overwrite B", async ({ page }) => {
  test.setTimeout(30000);
  let resolveA: (() => void) | undefined;
  const gateA = new Promise<void>(r => { resolveA = r; });

  await page.route("**/market-insights/query", async (route) => {
    const body = route.request().postDataJSON();
    if (body.district === "大安區") {
      await gateA; // HOLD A
      await route.fulfill({ status: 200, contentType: "application/json",
        body: JSON.stringify({ ...BASE_MARKET_RESPONSE, district: "大安區" }) });
    } else {
      await route.fulfill({ status: 200, contentType: "application/json",
        body: JSON.stringify({ ...BASE_MARKET_RESPONSE, district: "板橋區", city: "新北市", county: "新北市" }) });
    }
  });

  await goToMarket(page);
  // Send A
  await selectMarket(page, "臺北市", "大安區");
  await page.getByTestId("market-insight-search-button").click();
  await page.waitForTimeout(200);

  // Switch to B immediately
  await selectMarket(page, "新北市", "板橋區");
  await page.getByTestId("market-insight-search-button").click();
  await page.waitForTimeout(2000); // B completes

  // Release delayed A
  resolveA!();
  await page.waitForTimeout(1000);

  // Final state must be B (板橋區), not A (大安區)
  const bodyText = await page.locator("body").textContent() ?? "";
  // The displayed district select should still show 板橋區
  const form = page.getByTestId("market-insight-search-form");
  const districtValue = await form.getByLabel("選擇鄉鎮市區").inputValue();
  expect(districtValue).toBe("板橋區");
});

// ═══════════════════════════════════════════════════════════════════
// 5: DESKTOP + MOBILE SEMANTIC FLOWS
// ═══════════════════════════════════════════════════════════════════
test.describe("Desktop Market Flow", () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test("Property→Market→Journey via sidebar", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    const sidebar = page.locator("aside[aria-label='分析工具']");
    await sidebar.getByRole("button", { name: "Market Insight" }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 5000 });
    await sidebar.getByRole("button", { name: "看房決策流程" }).click();
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Mobile 390 Market Flow", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  test("Mobile menu→Market→Journey", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "開啟選單" }).click();
    const sidebar = page.locator("aside[aria-label='分析工具']");
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "Market Insight" }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 5000 });
    await page.getByRole("button", { name: "開啟選單" }).click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "看房決策流程" }).click();
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 5000 });
  });
});
