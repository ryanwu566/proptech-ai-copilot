import { test, expect } from "@playwright/test";

const PROD = "https://proptech-ai-copilot.vercel.app";
const API = "https://proptech-ai-copilot-api.onrender.com";

test.describe("Production Certification", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Aegis: 3 real production scenarios via API", async ({ page }) => {
    test.setTimeout(30000);
    await page.goto(PROD, { waitUntil: "domcontentloaded", timeout: 15000 });

    // Strong scenario
    const strong = await page.evaluate(async () => {
      const res = await fetch("https://proptech-ai-copilot-api.onrender.com/aegis-credit/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ monthly_income: 150000, monthly_debt: 5000, cash: 8000000, property_count: 0, mortgage_count: 0, property_price: 12000000 }) });
      return res.json();
    });
    console.log("AEGIS_STRONG:", JSON.stringify({ risk_score: strong.risk_score, signal_color: strong.signal_color, traces: strong.traces }));

    // Borderline scenario
    const borderline = await page.evaluate(async () => {
      const res = await fetch("https://proptech-ai-copilot-api.onrender.com/aegis-credit/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ monthly_income: 60000, monthly_debt: 15000, cash: 2000000, property_count: 1, mortgage_count: 1, property_price: 15000000 }) });
      return res.json();
    });
    console.log("AEGIS_BORDERLINE:", JSON.stringify({ risk_score: borderline.risk_score, signal_color: borderline.signal_color, traces: borderline.traces }));

    // Stressed scenario
    const stressed = await page.evaluate(async () => {
      const res = await fetch("https://proptech-ai-copilot-api.onrender.com/aegis-credit/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ monthly_income: 40000, monthly_debt: 25000, cash: 500000, property_count: 2, mortgage_count: 2, property_price: 20000000 }) });
      return res.json();
    });
    console.log("AEGIS_STRESSED:", JSON.stringify({ risk_score: stressed.risk_score, signal_color: stressed.signal_color, traces: stressed.traces }));

    // Logic must vary
    expect(strong.risk_score).toBeLessThan(stressed.risk_score);
    expect(strong.signal_color).not.toBe(stressed.signal_color);

    // No bank approval language
    const allText = JSON.stringify([strong, borderline, stressed]);
    expect(allText).not.toContain("approved");
    expect(allText).not.toContain("核貸");
  });

  test("Cache TTL expiry: wait 130s then measure", async ({ page }) => {
    test.setTimeout(200000);
    await page.goto(PROD, { waitUntil: "domcontentloaded", timeout: 15000 });

    const payload = { city: "桃園市", district: "大溪區", road: "中山路", area_ping: 30, building_type: "住宅大樓", building_age_years: 10, floor: 5 };

    // Step A: Warm the cache
    const warm1 = await page.evaluate(async (body) => {
      const t0 = performance.now();
      await fetch("https://proptech-ai-copilot-api.onrender.com/valuation/estimate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      return Math.round(performance.now() - t0);
    }, payload);
    console.log("WARM_1:", warm1, "ms");

    const warm2 = await page.evaluate(async (body) => {
      const t0 = performance.now();
      await fetch("https://proptech-ai-copilot-api.onrender.com/valuation/estimate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      return Math.round(performance.now() - t0);
    }, payload);
    console.log("PRE_EXPIRY:", warm2, "ms");

    // Step B: Wait 130 seconds (TTL is 120s)
    console.log("Waiting 130s for cache TTL expiry...");
    await page.waitForTimeout(130000);

    // Step C: First request after expiry
    const postExpiry1 = await page.evaluate(async (body) => {
      const t0 = performance.now();
      await fetch("https://proptech-ai-copilot-api.onrender.com/valuation/estimate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      return Math.round(performance.now() - t0);
    }, payload);
    console.log("POST_EXPIRY_FIRST:", postExpiry1, "ms");

    // Step D: Second request (cache repopulated)
    const postExpiry2 = await page.evaluate(async (body) => {
      const t0 = performance.now();
      await fetch("https://proptech-ai-copilot-api.onrender.com/valuation/estimate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      return Math.round(performance.now() - t0);
    }, payload);
    console.log("POST_EXPIRY_SECOND:", postExpiry2, "ms");

    // Analysis
    if (postExpiry1 > 3000 && postExpiry2 < 1500) {
      console.log("CACHE_EXPIRY_SPIKE: CONFIRMED (first post-expiry request hit data_status aggregate)");
    } else if (postExpiry1 < 1500) {
      console.log("CACHE_EXPIRY_SPIKE: NOT_CONFIRMED (cache may have been refreshed by another request or TTL extended)");
    }

    expect(warm2).toBeLessThan(2000);
  });

  test("Demo rehearsal: 5-min flow timing", async ({ page }) => {
    test.setTimeout(90000);

    await page.addInitScript(() => {
      window.localStorage.setItem("proptech_onboarding_seen", "true");
      window.localStorage.setItem("proptech_onboarding_version", "2");
    });

    const t0 = Date.now();
    await page.goto(PROD, { waitUntil: "domcontentloaded", timeout: 15000 });
    await expect(page.locator("#main-content")).toBeVisible({ timeout: 10000 });
    console.log("PAGE_LOAD:", Date.now() - t0, "ms");

    // Navigate Map
    const mapBtn = page.getByRole("button", { name: /Map Insight|地圖/i }).first();
    await mapBtn.click();
    await page.waitForTimeout(1000);
    console.log("MAP_NAV:", Date.now() - t0, "ms");

    // TaxOracle
    const taxBtn = page.getByRole("button", { name: /TaxOracle|稅務/i }).first();
    await taxBtn.click();
    await page.waitForTimeout(1000);
    console.log("TAX_NAV:", Date.now() - t0, "ms");

    // Valuation
    const valBtn = page.getByRole("button", { name: /房價估算|Valuation|価格/i }).first();
    await valBtn.click();
    await page.waitForTimeout(500);
    console.log("VAL_NAV:", Date.now() - t0, "ms");

    // Aegis
    const aegisBtn = page.getByRole("button", { name: /Aegis|Credit/i }).first();
    await aegisBtn.click();
    await page.waitForTimeout(500);
    console.log("AEGIS_NAV:", Date.now() - t0, "ms");

    // Back to dashboard
    const dashBtn = page.getByRole("button", { name: /看房決策|Property|물건|物件/i }).first();
    await dashBtn.click();
    await page.waitForTimeout(500);
    console.log("DASH_NAV:", Date.now() - t0, "ms");

    const total = Date.now() - t0;
    console.log("DEMO_REHEARSAL_TOTAL:", total, "ms");
    console.log("DEMO_NAVIGATION_SMOOTH:", total < 15000 ? "YES" : "NO");

    expect(total).toBeLessThan(30000); // Demo navigation should be fast
  });
});
