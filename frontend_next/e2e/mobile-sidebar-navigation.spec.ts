/**
 * Mobile Sidebar Navigation — Normal Click Test
 *
 * Proves that at 390×844, opening the mobile menu and clicking sidebar
 * buttons with NORMAL Playwright clicks (no force, no dispatchEvent,
 * no JS click) successfully navigates to each module.
 *
 * FORCE_CLICK_COUNT = 0
 * DISPATCH_EVENT_COUNT = 0
 * JS_CLICK_COUNT = 0
 */
import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

// ─── Helper: open mobile menu ──────────────────────────────────────────────

async function openMenu(page: import("@playwright/test").Page) {
  const menuBtn = page.getByRole("button", { name: "開啟選單" });
  await expect(menuBtn).toBeVisible({ timeout: 5000 });
  await menuBtn.click();
  // Wait for sidebar to animate in
  const sidebar = page.locator("aside[aria-label='分析工具']");
  await expect(sidebar).toBeVisible({ timeout: 3000 });
}

// ═══════════════════════════════════════════════════════════════════════════
// MOBILE 390×844 — Normal click navigation
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Mobile sidebar normal click navigation", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("All sidebar buttons respond to normal clicks at 390×844", async ({ page }) => {
    test.setTimeout(60000);
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    // 1. Menu → Map Insight
    await openMenu(page);
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Map Insight" }).click();
    await expect(page.getByRole("textbox", { name: /輸入地址|地標|路段/ })).toBeVisible({ timeout: 10000 });

    // 2. Menu → Market Insight
    await openMenu(page);
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Market Insight" }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 10000 });

    // 3. Menu → Terrain Risk
    await openMenu(page);
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Terrain Risk" }).click();
    await expect(page.getByRole("textbox", { name: /物件地址/ })).toBeVisible({ timeout: 10000 });

    // 4. Menu → Aegis-Credit
    await openMenu(page);
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Aegis-Credit" }).click();
    await expect(page.getByTestId("aegis-scenario-form")).toBeVisible({ timeout: 10000 });

    // 5. Menu → Market Insight (return)
    await openMenu(page);
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Market Insight" }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// MOBILE 430×932 — Normal click navigation
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Mobile sidebar normal click 430×932", () => {
  test.use({ viewport: { width: 430, height: 932 } });

  test("Sidebar buttons respond to normal clicks at 430×932", async ({ page }) => {
    test.setTimeout(45000);
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    await openMenu(page);
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Map Insight" }).click();
    await expect(page.getByRole("textbox", { name: /輸入地址|地標|路段/ })).toBeVisible({ timeout: 10000 });

    await openMenu(page);
    await page.locator("aside[aria-label='分析工具']").getByRole("button", { name: "Market Insight" }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// DESKTOP 1440×900 — Normal click navigation (should always work)
// ═══════════════════════════════════════════════════════════════════════════

test.describe("Desktop sidebar normal click 1440×900", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Sidebar buttons respond to normal clicks at 1440×900", async ({ page }) => {
    test.setTimeout(45000);
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    const sidebar = page.locator("aside[aria-label='分析工具']");
    await sidebar.getByRole("button", { name: "Map Insight" }).click();
    await expect(page.getByRole("textbox", { name: /輸入地址|地標|路段/ })).toBeVisible({ timeout: 10000 });

    await sidebar.getByRole("button", { name: "Market Insight" }).click();
    await expect(page.getByTestId("market-insight-search-form")).toBeVisible({ timeout: 10000 });

    await sidebar.getByRole("button", { name: "Terrain Risk" }).click();
    await expect(page.getByRole("textbox", { name: /物件地址/ })).toBeVisible({ timeout: 10000 });
  });
});
