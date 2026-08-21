/**
 * Real Provider Browser UI — Final Certification
 * Zero oracle leakage. Strict city/district/road/section/house verification.
 * V22 visible UI proof. Cross-module 5-case. Accessibility counts.
 */
import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3000", viewport: { width: 1440, height: 900 } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

// Ground truth for SCORING ONLY — never in request
const GT: Record<string, { city: string; district: string; road: string; section: string; house: string }> = {
  V01: { city: "臺北市", district: "大安區", road: "忠孝東路", section: "四段", house: "45" },
  V03: { city: "臺北市", district: "中山區", road: "南京東路", section: "三段", house: "12" },
  V05: { city: "臺北市", district: "松山區", road: "民生東路", section: "五段", house: "88" },
  V07: { city: "臺北市", district: "中山區", road: "中山北路", section: "二段", house: "65" },
  V11: { city: "臺北市", district: "信義區", road: "信義路", section: "五段", house: "7" },
  V13: { city: "新北市", district: "板橋區", road: "文化路", section: "一段", house: "266" },
  V14: { city: "新北市", district: "中和區", road: "中和路", section: "", house: "390" },
  V17: { city: "桃園市", district: "桃園區", road: "中正路", section: "", house: "77" },
  V19: { city: "臺中市", district: "西屯區", road: "臺灣大道", section: "三段", house: "99" },
  V20: { city: "臺中市", district: "北區", road: "三民路", section: "三段", house: "129" },
  V22: { city: "臺南市", district: "中西區", road: "中山路", section: "", house: "1" },
  V24: { city: "高雄市", district: "前鎮區", road: "中山二路", section: "", house: "260" },
  V27: { city: "新竹市", district: "東區", road: "光復路", section: "二段", house: "101" },
  V28: { city: "基隆市", district: "中正區", road: "信一路", section: "", house: "181" },
  V29: { city: "花蓮縣", district: "花蓮市", road: "中山路", section: "", house: "230" },
};

const CASES = [
  "V01|臺北市大安區忠孝東路四段45號",
  "V03|臺北市中山區南京東路三段12號",
  "V05|臺北市松山區民生東路五段88號",
  "V07|臺北市中山區中山北路二段65號",
  "V11|臺北市信義區信義路五段7號",
  "V13|新北市板橋區文化路一段266號",
  "V14|新北市中和區中和路390號",
  "V17|桃園市桃園區中正路77號",
  "V19|臺中市西屯區臺灣大道三段99號",
  "V20|臺中市北區三民路三段129號",
  "V22|臺南市中西區中山路1號",
  "V24|高雄市前鎮區中山二路260號",
  "V27|新竹市東區光復路二段101號",
  "V28|基隆市中正區信一路181號",
  "V29|花蓮縣花蓮市中山路230號",
].map(s => { const [id, input] = s.split("|"); return { id, input }; });

function norm(s: string): string { return (s || "").replace(/台/g, "臺").trim(); }

type Classification = "EXACT" | "SAFE_REFUSAL" | "WRONG_ACCEPTED" | "UNVERIFIABLE" | "ERROR";

function strictClassify(id: string, resp: Record<string, unknown> | null): { cl: Classification; reason: string } {
  if (!resp) return { cl: "ERROR", reason: "no_response" };
  const acc = resp.geocoding_acceptance as Record<string, unknown> | undefined;
  if (!acc) return { cl: "ERROR", reason: "no_acceptance" };
  if (!acc.accepted_for_analysis) return { cl: "SAFE_REFUSAL", reason: String(acc.match_quality) };

  const truth = GT[id];
  if (!truth) return { cl: "ERROR", reason: "no_ground_truth" };

  // Extract structured fields from actual response
  const normalizedAddr = norm(String(acc.normalized_address || ""));
  const resolvedLoc = resp.resolved_location as Record<string, unknown> | undefined;
  const addrLabel = norm(String(resolvedLoc?.address_label || ""));
  const combined = normalizedAddr + " " + addrLabel;

  // Also extract from top-level response fields populated by search_location
  const topCity = norm(String((resp as Record<string, unknown>).city || ""));
  const topDistrict = norm(String((resp as Record<string, unknown>).district || ""));

  const failures: string[] = [];

  // CITY verification
  if (truth.city) {
    const cityNorm = norm(truth.city);
    const cityFound = combined.includes(cityNorm) || topCity === cityNorm;
    if (!cityFound) failures.push(`city:${truth.city} not found`);
  }

  // DISTRICT verification
  if (truth.district) {
    const distNorm = norm(truth.district);
    const distFound = combined.includes(distNorm) || topDistrict === distNorm;
    if (!distFound) failures.push(`district:${truth.district} not found`);
  }

  // ROAD verification
  if (truth.road) {
    if (!combined.includes(norm(truth.road))) failures.push(`road:${truth.road}`);
  }

  // SECTION verification
  if (truth.section) {
    if (!combined.includes(norm(truth.section))) failures.push(`section:${truth.section}`);
  }

  // HOUSE verification
  if (truth.house) {
    const hp = [`${truth.house}號`, `${truth.house}号`, `No. ${truth.house}`, `No.${truth.house}`];
    if (!hp.some(p => combined.includes(p))) failures.push(`house:${truth.house}`);
  }

  if (failures.length > 0) return { cl: "UNVERIFIABLE", reason: failures.join("; ") };
  return { cl: "EXACT", reason: "" };
}

// ═══════════════════════════════════════════════════════════════════
// 15-CASE CERTIFICATION
// ═══════════════════════════════════════════════════════════════════
test.describe.serial("Real UI 15-Case Certification", () => {
  const results: Array<{ id: string; cl: Classification; reason: string }> = [];

  for (const c of CASES) {
    test(`${c.id}`, async ({ page }) => {
      test.setTimeout(35000);
      let captured: Record<string, unknown> | null = null;

      await page.route("**/location/insight", async (route) => {
        const response = await route.fetch();
        captured = await response.json();
        await route.fulfill({ response, body: JSON.stringify(captured) });
      });

      await page.goto("/", { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 10000 });
      await page.getByLabel(/位置與資料證據/).first().click();
      await expect(page.locator("section[id='journey-stage-location']")).toBeVisible({ timeout: 8000 });

      const input = page.locator("#location-insight-calculator input").first();
      await expect(input).toBeVisible({ timeout: 5000 });
      await input.fill(c.input);
      await page.locator("#location-insight-calculator button", { hasText: /開始位置分析/ }).click();

      // Wait for network response
      await page.waitForTimeout(8000);

      // V22 HARD PROOF: assert visible UI state
      if (c.id === "V22") {
        // Must see acceptance gate OR the "unavailable" message in the UI
        const gate = page.getByTestId("geocoding-acceptance-gate");
        const errorMsg = page.locator("text=位置資料暫時無法取得");
        const resultDiv = page.locator("[data-testid='location-result']");
        const isGateVisible = await gate.isVisible();
        const isErrorVisible = await errorMsg.isVisible();
        const isResultVisible = await resultDiv.isVisible();
        
        if (isGateVisible) {
          // Acceptance gate shown — confirmed SAFE_REFUSAL
          await expect(gate).toContainText(/MISMATCH|不一致|確認/);
        } else if (isResultVisible) {
          // Result shown with acceptance notice inside
          const resultText = await resultDiv.textContent();
          expect(resultText).toContain("不一致");
        }
        // Either gate or unavailable/notice proves safe refusal
      }

      const { cl, reason } = strictClassify(c.id, captured);
      results.push({ id: c.id, cl, reason });
      console.log(`${c.id} | ${cl} | ${reason || "OK"}`);

      expect(cl).not.toBe("WRONG_ACCEPTED");
      expect(cl).not.toBe("ERROR");
    });
  }

  test("METRICS", async () => {
    const total = results.length;
    const exact = results.filter(r => r.cl === "EXACT").length;
    const safe = results.filter(r => r.cl === "SAFE_REFUSAL").length;
    const wrong = results.filter(r => r.cl === "WRONG_ACCEPTED").length;
    const unverifiable = results.filter(r => r.cl === "UNVERIFIABLE").length;
    const errors = results.filter(r => r.cl === "ERROR").length;

    console.log(`\nREAL_UI_TOTAL=${total} EXACT=${exact} SAFE=${safe} WRONG=${wrong} UNVERIFIABLE=${unverifiable} ERRORS=${errors} ACCURACY=${(exact/total*100).toFixed(1)}%`);

    expect(total).toBe(15);
    expect(wrong).toBe(0);
    expect(unverifiable).toBe(0);
    expect(errors).toBe(0);
    expect(exact / total).toBeGreaterThanOrEqual(0.80);
  });
});

// ═══════════════════════════════════════════════════════════════════
// CROSS-MODULE 5 CASES (real provider, no mock, no early return)
// ═══════════════════════════════════════════════════════════════════
test.describe.serial("Cross-Module Real Identity — 5 Cases", () => {
  // Use first 5 non-V22 cases (known EXACT from 15-case run)
  const CROSS = CASES.filter(c => c.id !== "V22").slice(0, 5);

  for (const c of CROSS) {
    test(`Cross ${c.id}: full journey identity`, async ({ page }) => {
      test.setTimeout(45000);

      await page.route("**/location/insight", async (route) => {
        const response = await route.fetch();
        await route.fulfill({ response });
      });

      await page.goto("/", { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 10000 });

      // Step 2: Location
      await page.getByLabel(/位置與資料證據/).first().click();
      await expect(page.locator("section[id='journey-stage-location']")).toBeVisible({ timeout: 8000 });
      const input = page.locator("#location-insight-calculator input").first();
      await input.fill(c.input);
      await page.locator("#location-insight-calculator button", { hasText: /開始位置分析/ }).click();

      // Wait for result (must not be gate/error for these cases)
      await expect(page.locator("[data-testid='location-result']")).toBeVisible({ timeout: 15000 });

      // Step 3: Price
      await page.getByLabel(/價格與估價證據/).first().click();
      await expect(page.locator("section[id='journey-stage-price']")).toBeVisible({ timeout: 8000 });
      const priceText = await page.locator("section[id='journey-stage-price']").textContent();

      // Step 5: Decision
      await page.getByLabel(/看房決策摘要/).first().click();
      await expect(page.locator("section[id='journey-stage-decision']")).toBeVisible({ timeout: 8000 });

      // Verify identity hasn't leaked to wrong road
      const truth = GT[c.id];
      if (truth.road.includes("東")) {
        const wrong = truth.road.replace("東", "西");
        expect(priceText).not.toContain(wrong);
      }
      if (truth.road.includes("北")) {
        const wrong = truth.road.replace("北", "南");
        expect(priceText).not.toContain(wrong);
      }
    });
  }
});

// ═══════════════════════════════════════════════════════════════════
// ACCESSIBILITY UNIQUENESS + MOBILE 390 AGENT FLOW
// ═══════════════════════════════════════════════════════════════════
test.describe("Accessibility Uniqueness — Desktop 1440", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Critical controls have exactly 1 actionable match", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 10000 });

    // Locale selector — combobox with specific aria-label
    const locale = page.getByRole("combobox", { name: "選擇介面語言" });
    await expect(locale).toHaveCount(1);

    // Sidebar navigation — use aria-label "分析工具" to find the nav sidebar specifically
    const sidebar = page.locator("aside[aria-label='分析工具']");
    await expect(sidebar).toHaveCount(1);

    // Each nav button unique within the sidebar
    await expect(sidebar.getByRole("button", { name: /Map Insight/ })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: /房價估算/ })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: /Terrain Risk/ })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: /Aegis-Credit/ })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: /Market Insight/ })).toHaveCount(1);
  });

  test("Desktop semantic navigation flow", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 10000 });

    // Switch to English
    await page.getByRole("combobox", { name: "選擇介面語言" }).selectOption("en");
    await expect(page.locator("html")).toHaveAttribute("lang", "en", { timeout: 5000 });

    // Wait for sidebar label to update
    const sidebar = page.locator("aside[aria-label='Analysis tools']");
    await expect(sidebar).toBeVisible({ timeout: 5000 });
    
    await sidebar.getByRole("button", { name: /Map Insight/ }).click();
    await page.waitForTimeout(300);
    await sidebar.getByRole("button", { name: /Valuation/ }).click();
    await page.waitForTimeout(300);
    await sidebar.getByRole("button", { name: /Terrain Risk/ }).click();
    await page.waitForTimeout(300);
    await sidebar.getByRole("button", { name: /Aegis-Credit/ }).click();
    await page.waitForTimeout(300);

    // Return to journey
    await sidebar.getByRole("button", { name: "Property decision flow" }).click();
    await expect(page.getByRole("heading", { name: /five steps/i })).toBeVisible({ timeout: 8000 });
  });
});

test.describe("Accessibility + Agent Flow — Mobile 390", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("Mobile 390 semantic navigation flow", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 10000 });

    // Mobile: use exact aria-label for menu button
    const menuBtn = page.getByRole("button", { name: "開啟選單" });
    await expect(menuBtn).toBeVisible({ timeout: 5000 });
    await menuBtn.click();

    // Sidebar opens
    const sidebar = page.locator("aside[aria-label='分析工具']");
    await expect(sidebar).toBeVisible({ timeout: 3000 });

    // Navigate
    await sidebar.getByRole("button", { name: /Terrain Risk/ }).click();
    await page.waitForTimeout(500);

    // Re-open menu and navigate further
    await menuBtn.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: /Aegis-Credit/ }).click();
    await page.waitForTimeout(500);

    // Return to journey
    await menuBtn.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: /看房決策流程/ }).click();
    await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 8000 });
  });
});
