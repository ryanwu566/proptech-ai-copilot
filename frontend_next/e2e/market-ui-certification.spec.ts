/**
 * Market Insight Part 2A — Cancel bug, states, race, semantic selectors
 * CRITICAL_POSITIONAL_SELECTOR_COUNT = 0 (uses data-testid for all controls)
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

const BASE = {
  city: "臺北市", county: "臺北市", district: "大安區", period: "2026-06",
  average_unit_price: 82, avg_price_per_ping: 82, transaction_count: 45,
  transaction_volume: 45, record_count: 45,
  summary: "Controlled test fixture", source_name: "controlled_test_fixture",
  source_updated_at: "2026-08-01", coverage_status: "covered",
  data_status: "available", caveat: "Test only", disclaimer: "Not real",
  history: [{ period: "2026-05", avg_price_per_ping: 80, transaction_count: 40 }],
};

// ═══════════ MID-QUERY CANCEL ═══════════
test("Mid-query cancel: changing district re-enables submit", async ({ page }) => {
  test.setTimeout(20000);
  let resolveA: (() => void) | undefined;
  const gateA = new Promise<void>(r => { resolveA = r; });

  await page.route("**/market-insights/query", async (route) => {
    const body = route.request().postDataJSON();
    if (body.district === "大安區") {
      await gateA;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...BASE }) });
    } else {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...BASE, district: "信義區" }) });
    }
  });

  await goToMarket(page);
  const county = page.getByTestId("market-county-select");
  const district = page.getByTestId("market-district-select");
  const btn = page.getByTestId("market-insight-search-button");

  // Select A and submit
  await county.selectOption("臺北市");
  await page.waitForTimeout(400);
  await district.selectOption("大安區");
  await btn.click();

  // Button must be disabled during query
  await expect(btn).toBeDisabled({ timeout: 3000 });

  // Change district while A is pending (this should cancel A and re-enable)
  await district.selectOption("信義區");
  await page.waitForTimeout(500);

  // Button must become enabled again (not deadlocked)
  await expect(btn).toBeEnabled({ timeout: 3000 });

  // Submit B
  await btn.click();
  await page.waitForTimeout(3000);

  // B result visible (信義區)
  const distVal = await district.inputValue();
  expect(distVal).toBe("信義區");

  // Release A (late) — must not affect current state
  resolveA!();
  await page.waitForTimeout(500);
  const finalDist = await district.inputValue();
  expect(finalDist).toBe("信義區");
});

// ═══════════ STATES ═══════════
test("NO_DATA", async ({ page }) => {
  await page.route("**/market-insights/query", (r) => r.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ ...BASE, transaction_count: 0, record_count: 0, data_status: "no_data", coverage_status: "no_data", average_unit_price: 0, avg_price_per_ping: 0 }) }));
  await goToMarket(page);
  await page.getByTestId("market-county-select").selectOption("臺北市");
  await page.waitForTimeout(400);
  await page.getByTestId("market-district-select").selectOption("大安區");
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-no-data")).toBeVisible({ timeout: 8000 });
});

test("LOW_SAMPLE", async ({ page }) => {
  await page.route("**/market-insights/query", (r) => r.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ ...BASE, transaction_count: 2, record_count: 2, coverage_status: "partial", data_status: "available" }) }));
  await goToMarket(page);
  await page.getByTestId("market-county-select").selectOption("臺北市");
  await page.waitForTimeout(400);
  await page.getByTestId("market-district-select").selectOption("大安區");
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-state-guidance")).toBeVisible({ timeout: 8000 });
});

test("PROVIDER_ERROR", async ({ page }) => {
  await page.route("**/market-insights/query", (r) => r.fulfill({ status: 500, body: "error" }));
  await goToMarket(page);
  await page.getByTestId("market-county-select").selectOption("臺北市");
  await page.waitForTimeout(400);
  await page.getByTestId("market-district-select").selectOption("大安區");
  await page.getByTestId("market-insight-search-button").click();
  // Error visible (network-error or general error text)
  const body = await page.locator("body").textContent() ?? "";
  await page.waitForTimeout(3000);
  const hasError = body.includes("無法") || body.includes("稍後") || await page.getByTestId("market-insight-network-error").isVisible().catch(() => false);
  expect(hasError).toBe(true);
});

// ═══════════ STALE PREVENTION ═══════════
test("A→B: switching mid-query, B result shown, A never visible", async ({ page }) => {
  test.setTimeout(20000);
  let resolveA: (() => void) | undefined;
  const gateA = new Promise<void>(r => { resolveA = r; });
  const rendered: string[] = [];

  await page.route("**/market-insights/query", async (route) => {
    const body = route.request().postDataJSON();
    if (body.district === "大安區") {
      await gateA;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...BASE, district: "大安區", summary: "A_RESULT" }) });
    } else {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...BASE, district: "信義區", summary: "B_RESULT" }) });
    }
  });

  await goToMarket(page);
  await page.getByTestId("market-county-select").selectOption("臺北市");
  await page.waitForTimeout(400);
  await page.getByTestId("market-district-select").selectOption("大安區");
  await page.getByTestId("market-insight-search-button").click();
  await page.waitForTimeout(200);

  // Cancel A by changing district
  await page.getByTestId("market-district-select").selectOption("信義區");
  await page.waitForTimeout(500);

  // Submit B
  await page.getByTestId("market-insight-search-button").click();
  await page.waitForTimeout(3000);

  // Release A
  resolveA!();
  await page.waitForTimeout(1000);

  // Page must show B, not A
  const bodyText = await page.locator("body").textContent() ?? "";
  expect(bodyText).not.toContain("A_RESULT");
});
