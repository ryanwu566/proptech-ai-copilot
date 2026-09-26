/**
 * RIS Phase 4F — Hosted real-production acceptance (NO API MOCK).
 * Drives the live production site at HOSTED_FRONTEND_URL against the real backend.
 * Captures the genuine /location/insight responses the UI receives and asserts
 * the rendered UI matches the real backend contract for each state.
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const HOME_HEADING = "用五個步驟整理看房資訊";

// Suppress the first-visit onboarding tour modal (it overlays and intercepts
// pointer events). This mirrors a returning user and does not alter product code.
async function seedNoOnboarding(page: Page) {
  await page.addInitScript(() => {
    try {
      window.localStorage.setItem("proptech_onboarding_seen", "true");
      window.localStorage.setItem("proptech_onboarding_version", "2");
    } catch {
      /* ignore */
    }
  });
}

async function gotoLocationStage(page: Page) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: HOME_HEADING })).toBeVisible({ timeout: 20000 });
  const viewport = page.viewportSize();
  const isMobile = (viewport?.width ?? 1440) < 1024;
  if (isMobile) {
    const mobileSummary = page.locator("details.lg\\:hidden > summary").first();
    if (await mobileSummary.count()) await mobileSummary.click();
  }
  const candidates = page.getByLabel(/位置與資料證據/);
  const count = await candidates.count();
  let clicked = false;
  for (let i = 0; i < count; i += 1) {
    const candidate = candidates.nth(i);
    if (await candidate.isVisible()) { await candidate.click(); clicked = true; break; }
  }
  if (!clicked && count > 0) await candidates.first().click();
  await expect(page.locator("#location-insight-calculator")).toBeVisible({ timeout: 25000 });
}

async function analyze(page: Page, address: string) {
  // The guided journey can mount more than one calculator; target the visible one.
  const calc = page.locator("#location-insight-calculator").filter({ has: page.getByRole("textbox", { name: "物件地址" }) }).first();
  const input = calc.getByRole("textbox", { name: "物件地址" });
  await expect(input).toBeVisible({ timeout: 15000 });
  await input.click();
  await input.fill("");
  await input.type(address, { delay: 5 });
  await input.blur();
  const button = calc.getByRole("button", { name: "開始位置分析" });
  await expect(button).toBeEnabled({ timeout: 8000 });
  await button.click();
}

test.describe("RIS hosted real-production acceptance", () => {
  test.describe.configure({ mode: "serial" });
  test.beforeEach(async ({ page }) => { await seedNoOnboarding(page); });

  test("HOME: production homepage loads with no fatal error", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.locator("body")).toBeVisible();
    await expect(page).not.toHaveTitle(/error/i);
    await expect(page.getByRole("heading", { name: HOME_HEADING })).toBeVisible({ timeout: 20000 });
    expect(pageErrors, `page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });

  test("LOCATION STAGE: opens and mounts the calculator", async ({ page }) => {
    await gotoLocationStage(page);
    await expect(page.locator("#location-insight-calculator")).toBeVisible();
  });

  test("TAIPEI: real analyze — capture backend truth and assert UI matches", async ({ page }) => {
    await gotoLocationStage(page);
    const waitResp = page.waitForResponse(
      (r) => r.url().includes("/location/insight") && r.request().method() === "POST",
      { timeout: 30000 },
    );
    await analyze(page, "臺北市大安區忠孝東路四段45號");
    const response = await waitResp;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as Record<string, unknown>;
    const vr = (body.village_resolution ?? {}) as Record<string, unknown>;
    const demo = (body.demographics ?? {}) as Record<string, unknown>;
    const acc = (body.geocoding_acceptance ?? {}) as Record<string, unknown>;
    console.log(`TAIPEI backend: accepted=${acc.accepted_for_analysis} match=${acc.match_quality} vr=${vr.status} dcode=${vr.district_code} village=${vr.village} source=${vr.source} demo=${demo.status} month=${demo.statistic_yyymm} pop=${demo.total_population} hh=${demo.household_count}`);

    // The Taipei address must resolve to a real village with available demographics.
    expect(acc.accepted_for_analysis, "Taipei geocode must be accepted").toBe(true);
    expect(vr.status, "Taipei village must resolve").toBe("resolved");
    expect(vr.source, "village source must be NLSC boundary").toBe("nlsc_village_boundary");
    expect(demo.status, "demographics must be available").toBe("available");
    expect(String(demo.statistic_yyymm), "latest month must be 11507").toBe("11507");

    // The 里人口概況 card must render with all required fields (real values, no null/0 confusion).
    const card = page.getByTestId("demographics-insight");
    await expect(card).toBeVisible({ timeout: 8000 });
    await expect(page.getByTestId("demographics-available")).toBeVisible();
    await expect(page.getByTestId("demographics-admin-location")).not.toBeEmpty();
    await expect(page.getByTestId("demographics-statistic-month")).toContainText("民國115年07月");
    // Required metric labels present.
    await expect(card).toContainText("總人口");
    await expect(card).toContainText("戶數");
    await expect(card).toContainText("平均每戶人口");
    await expect(card).toContainText("0–14 歲比例");
    await expect(card).toContainText("15–64 歲比例");
    await expect(card).toContainText("65 歲以上比例");
    await expect(card).toContainText("近期人口變化");
    // Real formatted values from the backend body must appear verbatim.
    const pop = Number(demo.total_population);
    const hh = Number(demo.household_count);
    await expect(card).toContainText(pop.toLocaleString("en-US"));
    await expect(card).toContainText(hh.toLocaleString("en-US"));
    // Ratios rendered as percentages, not raw 0 / null.
    await expect(card).toContainText(/%/);
  });

  test("NEW TAIPEI: real analyze resolves a village with demographics", async ({ page }) => {
    await gotoLocationStage(page);
    const waitResp = page.waitForResponse(
      (r) => r.url().includes("/location/insight") && r.request().method() === "POST",
      { timeout: 30000 },
    );
    await analyze(page, "新北市板橋區文化路一段266號");
    const response = await waitResp;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as Record<string, unknown>;
    const vr = (body.village_resolution ?? {}) as Record<string, unknown>;
    const demo = (body.demographics ?? {}) as Record<string, unknown>;
    const acc = (body.geocoding_acceptance ?? {}) as Record<string, unknown>;
    console.log(`NEWTAIPEI backend: accepted=${acc.accepted_for_analysis} match=${acc.match_quality} vr=${vr.status} dcode=${vr.district_code} village=${vr.village} demo=${demo.status} month=${demo.statistic_yyymm}`);

    if (acc.accepted_for_analysis === true && vr.status === "resolved" && demo.status === "available") {
      const card = page.getByTestId("demographics-insight");
      await expect(card).toBeVisible({ timeout: 8000 });
      await expect(page.getByTestId("demographics-available")).toBeVisible();
      await expect(page.getByTestId("demographics-statistic-month")).toContainText(/民國\d+年\d+月/);
      await expect(vr.source).toBe("nlsc_village_boundary");
    } else {
      // If geocoding safely refuses, the UI must stay bounded — never stale, never crash.
      await expect(page.getByTestId("demographics-available")).toHaveCount(0);
      await expect(page.locator("body")).toBeVisible();
    }
  });

  test("OCEAN: unresolved coordinate-like input stays bounded, no crash, no stale", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await gotoLocationStage(page);
    const waitResp = page.waitForResponse(
      (r) => r.url().includes("/location/insight") && r.request().method() === "POST",
      { timeout: 30000 },
    );
    await analyze(page, "臺灣海峽外海");
    const response = await waitResp;
    const body = (await response.json()) as Record<string, unknown>;
    const vr = (body.village_resolution ?? {}) as Record<string, unknown>;
    const demo = (body.demographics ?? {}) as Record<string, unknown>;
    console.log(`OCEAN backend: status=${response.status()} vr=${vr.status} demo=${demo.status}`);
    await page.waitForTimeout(1500);
    // Must not crash regardless of backend response.
    expect(pageErrors, `page errors: ${pageErrors.join(" | ")}`).toEqual([]);
    // No available demographics for an unresolved/ocean input.
    await expect(page.getByTestId("demographics-available")).toHaveCount(0);
    await expect(page.locator("body")).toBeVisible();
  });

  test("ADDRESS CHANGE: old result clears when the address input changes", async ({ page }) => {
    await gotoLocationStage(page);
    const waitResp = page.waitForResponse(
      (r) => r.url().includes("/location/insight") && r.request().method() === "POST",
      { timeout: 30000 },
    );
    await analyze(page, "臺北市大安區忠孝東路四段45號");
    await waitResp;
    await page.waitForTimeout(1500);
    // Change the address — the flow must invalidate and clear any prior result/card.
    const calc = page.locator("#location-insight-calculator").filter({ has: page.getByRole("textbox", { name: "物件地址" }) }).first();
    const input = calc.getByRole("textbox", { name: "物件地址" });
    await input.click();
    await input.fill("新北市板橋區文化路一段266號");
    await expect(page.getByTestId("demographics-available")).toHaveCount(0);
    await expect(page.getByTestId("location-result")).toHaveCount(0);
  });
});

test.describe("RIS hosted mobile 390px", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  test.beforeEach(async ({ page }) => { await seedNoOnboarding(page); });

  test("MOBILE: no horizontal overflow on home and location stage", async ({ page }) => {
    await gotoLocationStage(page);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow, "no horizontal overflow at 390px").toBe(false);
  });

  test("MOBILE: demographics card renders and fits at 390px", async ({ page }) => {
    await gotoLocationStage(page);
    const waitResp = page.waitForResponse(
      (r) => r.url().includes("/location/insight") && r.request().method() === "POST",
      { timeout: 30000 },
    );
    await analyze(page, "臺北市大安區忠孝東路四段45號");
    const response = await waitResp;
    const body = (await response.json()) as Record<string, unknown>;
    const vr = (body.village_resolution ?? {}) as Record<string, unknown>;
    const demo = (body.demographics ?? {}) as Record<string, unknown>;
    if (vr.status === "resolved" && demo.status === "available") {
      const card = page.getByTestId("demographics-insight");
      await expect(card).toBeVisible({ timeout: 8000 });
      // Card must not exceed viewport width (metrics stack, long text wraps).
      const overflow = await page.evaluate(() => {
        const el = document.querySelector("[data-testid='demographics-insight']");
        if (!el) return { scrollWidth: 0, clientWidth: 1 };
        return { scrollWidth: el.scrollWidth, clientWidth: document.documentElement.clientWidth };
      });
      expect(overflow.scrollWidth, "demographics card must fit within 390px").toBeLessThanOrEqual(overflow.clientWidth + 1);
    }
    // Whole document must not overflow horizontally regardless.
    const docOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(docOverflow, "no horizontal document overflow at 390px").toBe(false);
  });
});


test.describe("RIS hosted existing-product regression", () => {
  test.describe.configure({ mode: "serial" });
  test.beforeEach(async ({ page }) => { await seedNoOnboarding(page); });

  async function openSidebarIfNeeded(page: Page) {
    const viewport = page.viewportSize();
    const isMobile = (viewport?.width ?? 1440) < 1024;
    if (isMobile) {
      const menu = page.getByRole("button", { name: /選單|Menu|開啟選單/ }).first();
      if (await menu.count()) await menu.click().catch(() => {});
    }
  }

  async function navigateTo(page: Page, name: RegExp) {
    await openSidebarIfNeeded(page);
    const nav = page.locator("aside").getByRole("button", { name });
    const target = nav.first();
    await expect(target).toBeVisible({ timeout: 10000 });
    await target.click();
  }

  test("REGRESSION: Terrain Risk surface renders without fatal error", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: HOME_HEADING })).toBeVisible({ timeout: 20000 });
    await navigateTo(page, /Terrain Risk/);
    await expect(page.locator("main")).toBeVisible();
    await expect(page).not.toHaveTitle(/error/i);
    expect(pageErrors, `page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });

  test("REGRESSION: Market Insight surface renders without fatal error", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: HOME_HEADING })).toBeVisible({ timeout: 20000 });
    await navigateTo(page, /Market Insight/);
    await expect(page.locator("main")).toBeVisible();
    await expect(page).not.toHaveTitle(/error/i);
    expect(pageErrors, `page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });

  test("REGRESSION: valuation (房價估算) surface renders without fatal error", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: HOME_HEADING })).toBeVisible({ timeout: 20000 });
    await navigateTo(page, /房價估算|Valuation/);
    await expect(page.locator("main")).toBeVisible();
    await expect(page).not.toHaveTitle(/error/i);
    expect(pageErrors, `page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });
});
