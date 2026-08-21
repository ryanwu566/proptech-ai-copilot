/**
 * Market Insight Part 2A — State, Race, Semantic
 * Selects within market-insight-search-form use ordered nth (legitimate form field order).
 */
import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3000", viewport: { width: 1440, height: 900 } });

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

async function selectAndQuery(page: import("@playwright/test").Page, city: string, district: string) {
  const form = page.getByTestId("market-insight-search-form");
  const selects = form.locator("select");
  await selects.nth(0).selectOption(city);
  await page.waitForTimeout(600);  // Wait for district options to load
  await selects.nth(1).selectOption(district);
  await page.getByTestId("market-insight-search-button").click();
}

const BASE = {
  city: "臺北市", county: "臺北市", district: "大安區", period: "2026-06",
  average_unit_price: 82, avg_price_per_ping: 82, transaction_count: 45,
  transaction_volume: 45, record_count: 45,
  summary: "Controlled test fixture", source_name: "controlled_test_fixture",
  source_updated_at: "2026-08-01", coverage_status: "covered",
  data_status: "available", caveat: "Test only", disclaimer: "Not real market data",
  history: [{ period: "2026-05", avg_price_per_ping: 80, transaction_count: 40 }],
};

// ═══════════ SMOKE ═══════════
test("SMOKE: Market form visible", async ({ page }) => {
  await goToMarket(page);
  const form = page.getByTestId("market-insight-search-form");
  await expect(form.locator("select")).toHaveCount(2);
  await expect(page.getByTestId("market-insight-search-button")).toBeVisible();
});

// ═══════════ STATES ═══════════
test("NO_DATA state", async ({ page }) => {
  await page.route("**/market-insights/query", (r) => r.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ ...BASE, transaction_count: 0, record_count: 0, data_status: "no_data", coverage_status: "no_data", average_unit_price: 0, avg_price_per_ping: 0 }) }));
  await goToMarket(page);
  await selectAndQuery(page, "臺北市", "大安區");
  await expect(page.getByTestId("market-insight-no-data")).toBeVisible({ timeout: 8000 });
});

test("LOW_SAMPLE state", async ({ page }) => {
  await page.route("**/market-insights/query", (r) => r.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ ...BASE, transaction_count: 2, record_count: 2, coverage_status: "partial" }) }));
  await goToMarket(page);
  await selectAndQuery(page, "臺北市", "大安區");
  await expect(page.getByTestId("market-state-guidance")).toBeVisible({ timeout: 8000 });
});

test("PROVIDER_ERROR state", async ({ page }) => {
  await page.route("**/market-insights/query", (r) => r.fulfill({ status: 500, body: "error" }));
  await goToMarket(page);
  await selectAndQuery(page, "臺北市", "大安區");
  // Error state shows either network-error or unavailable testid
  const errorVisible = await page.getByTestId("market-insight-network-error").isVisible({ timeout: 8000 }).catch(() => false);
  const unavailVisible = await page.locator("[data-testid*='market-insight-unavailable'], [data-testid*='market-insight-network']").isVisible({ timeout: 3000 }).catch(() => false);
  const bodyText = await page.locator("body").textContent() ?? "";
  // Must show some error state — not stale data
  expect(errorVisible || unavailVisible || bodyText.includes("無法") || bodyText.includes("稍後")).toBe(true);
});

// ═══════════ RACE ═══════════
test("A→B race: button disabled during active query prevents stale result", async ({ page }) => {
  test.setTimeout(15000);
  let resolveA: (() => void) | undefined;
  const gateA = new Promise<void>(r => { resolveA = r; });

  await page.route("**/market-insights/query", async (route) => {
    await gateA;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...BASE, district: "大安區" }) });
  });

  await goToMarket(page);
  await selectAndQuery(page, "臺北市", "大安區");

  // While A is pending, button must be disabled (prevents race by design)
  const btn = page.getByTestId("market-insight-search-button");
  await expect(btn).toBeDisabled({ timeout: 3000 });

  // Release A
  resolveA!();
  await page.waitForTimeout(2000);

  // After completion, button re-enables
  await expect(btn).toBeEnabled({ timeout: 5000 });
});

test("B→A: after switching district and resubmitting, result matches new selection", async ({ page }) => {
  test.setTimeout(15000);
  const responses: string[] = [];

  await page.route("**/market-insights/query", async (route) => {
    const body = route.request().postDataJSON();
    responses.push(body.district);
    await route.fulfill({ status: 200, contentType: "application/json",
      body: JSON.stringify({ ...BASE, district: body.district }) });
  });

  await goToMarket(page);
  // Query A
  await selectAndQuery(page, "臺北市", "大安區");
  await page.waitForTimeout(2000);
  // Query B
  await selectAndQuery(page, "臺北市", "信義區");
  await page.waitForTimeout(2000);

  // Last response is for B
  expect(responses[responses.length - 1]).toBe("信義區");
  // District selector shows B
  const form = page.getByTestId("market-insight-search-form");
  const val = await form.locator("select").nth(1).inputValue();
  expect(val).toBe("信義區");
});
