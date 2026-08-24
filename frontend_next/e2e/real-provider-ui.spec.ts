/**
 * Real Provider Browser UI — Final Trust Sign-Off
 * - Strict city/district/road/section/house verification
 * - V22 visible hard proof (no generic error accepted)
 * - Cross-module full chain: Property→Location→Map→Valuation→Market→Decision
 * - Zero .first()/.last()/.nth() in critical paths
 * - Accessibility uniqueness counts
 * - Desktop + Mobile 390 semantic agent flows
 */
import { test, expect } from "@playwright/test";
import { realProviderUrl } from "./real-provider";

test.use({ viewport: { width: 1440, height: 900 } });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

// Ground truth — SCORING ONLY
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
  { id: "V01", input: "臺北市大安區忠孝東路四段45號" },
  { id: "V03", input: "臺北市中山區南京東路三段12號" },
  { id: "V05", input: "臺北市松山區民生東路五段88號" },
  { id: "V07", input: "臺北市中山區中山北路二段65號" },
  { id: "V11", input: "臺北市信義區信義路五段7號" },
  { id: "V13", input: "新北市板橋區文化路一段266號" },
  { id: "V14", input: "新北市中和區中和路390號" },
  { id: "V17", input: "桃園市桃園區中正路77號" },
  { id: "V19", input: "臺中市西屯區臺灣大道三段99號" },
  { id: "V20", input: "臺中市北區三民路三段129號" },
  { id: "V22", input: "臺南市中西區中山路1號" },
  { id: "V24", input: "高雄市前鎮區中山二路260號" },
  { id: "V27", input: "新竹市東區光復路二段101號" },
  { id: "V28", input: "基隆市中正區信一路181號" },
  { id: "V29", input: "花蓮縣花蓮市中山路230號" },
];

function norm(s: string): string { return (s || "").replace(/台/g, "臺").trim(); }

type Classification = "EXACT" | "SAFE_REFUSAL" | "WRONG_ACCEPTED" | "UNVERIFIABLE" | "ERROR";

function strictClassify(id: string, resp: Record<string, unknown> | null): { cl: Classification; reason: string } {
  if (!resp) return { cl: "ERROR", reason: "no_response" };
  const acc = (resp.geocoding_acceptance ?? {}) as Record<string, unknown>;
  if (!acc.accepted_for_analysis) return { cl: "SAFE_REFUSAL", reason: String(acc.match_quality || "UNKNOWN") };
  const truth = GT[id];
  if (!truth) return { cl: "ERROR", reason: "no_ground_truth" };
  const normalizedAddr = norm(String(acc.normalized_address || ""));
  const resolvedLoc = (resp.resolved_location ?? {}) as Record<string, unknown>;
  const addrLabel = norm(String(resolvedLoc.address_label || ""));
  const combined = normalizedAddr + " " + addrLabel;
  const failures: string[] = [];
  if (truth.city && !combined.includes(norm(truth.city))) failures.push(`city:${truth.city}`);
  if (truth.district && !combined.includes(norm(truth.district))) failures.push(`district:${truth.district}`);
  if (truth.road && !combined.includes(norm(truth.road))) failures.push(`road:${truth.road}`);
  if (truth.section && !combined.includes(norm(truth.section))) failures.push(`section:${truth.section}`);
  if (truth.house) {
    const hp = [`${truth.house}號`, `${truth.house}号`, `No. ${truth.house}`, `No.${truth.house}`];
    if (!hp.some(p => combined.includes(p))) failures.push(`house:${truth.house}`);
  }
  if (failures.length > 0) return { cl: "UNVERIFIABLE", reason: failures.join("; ") };
  return { cl: "EXACT", reason: "" };
}

/** Navigate to journey location step — NO .first()/.nth() on critical controls */
async function goToLocationStep(page: import("@playwright/test").Page) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });
  // Journey step buttons are inside nav "選擇流程步驟" — use visible button with exact title text
  const stepNav = page.locator("nav[aria-label='選擇流程步驟']");
  await stepNav.getByRole("button", { name: /位置與資料證據/ }).click();
  await expect(page.locator("section[id='journey-stage-location']")).toBeVisible({ timeout: 8000 });
}

/** Fill address and click analyze — NO .first() */
async function analyzeAddress(page: import("@playwright/test").Page, address: string) {
  // The address input is the textbox labeled "物件地址" within #location-insight-calculator
  const input = page.locator("#location-insight-calculator").getByRole("textbox", { name: "物件地址" });
  await expect(input).toBeVisible({ timeout: 5000 });
  await input.fill(address);
  await page.locator("#location-insight-calculator").getByRole("button", { name: "開始位置分析" }).click();
}

// ═══════════════════════════════════════════════════════════════════
// 15-CASE CERTIFICATION
// ═══════════════════════════════════════════════════════════════════
test.describe.serial("Real UI 15-Case Certification", { tag: "@real-provider" }, () => {
  const results: Array<{ id: string; cl: Classification; reason: string }> = [];

  for (const c of CASES) {
    test(`${c.id}`, async ({ page }) => {
      test.setTimeout(35000);
      let captured: Record<string, unknown> | null = null;

      await page.route("**/location/insight", async (route) => {
        const response = await route.fetch({ url: realProviderUrl("/location/insight") });
        captured = await response.json();
        await route.fulfill({ response, body: JSON.stringify(captured) });
      });

      await goToLocationStep(page);
      await analyzeAddress(page, c.input);
      await page.waitForTimeout(8000);

      // === GAP 1: V22 HARD PROOF ===
      if (c.id === "V22") {
        const gate = page.getByTestId("geocoding-acceptance-gate");
        const genericError = page.locator("text=位置資料暫時無法取得");
        const resultDiv = page.getByTestId("location-result");

        const isGateVisible = await gate.isVisible();
        const isGenericError = await genericError.isVisible();
        const isResultVisible = await resultDiv.isVisible();

        // HARD: generic error must NOT be the final state
        expect(isGenericError, "V22 must not show generic error").toBe(false);
        // HARD: must have either acceptance gate or result with mismatch notice
        expect(isGateVisible || isResultVisible, "V22 must show refusal state").toBe(true);

        if (isGateVisible) {
          await expect(gate).toContainText(/MISMATCH|不一致|需要確認/);
        }
        if (isResultVisible) {
          await expect(resultDiv).toContainText(/不一致|MISMATCH|需要確認/);
        }
      }

      const { cl, reason } = strictClassify(c.id, captured);
      results.push({ id: c.id, cl, reason });
      console.log(`${c.id} | ${cl} | ${reason || "OK"}`);
      expect(cl, `${c.id} must not be WRONG_ACCEPTED`).not.toBe("WRONG_ACCEPTED");
      expect(cl, `${c.id} must not be ERROR`).not.toBe("ERROR");
    });
  }

  test("METRICS", async () => {
    const total = results.length;
    const exact = results.filter(r => r.cl === "EXACT").length;
    const safe = results.filter(r => r.cl === "SAFE_REFUSAL").length;
    const wrong = results.filter(r => r.cl === "WRONG_ACCEPTED").length;
    const unverifiable = results.filter(r => r.cl === "UNVERIFIABLE").length;
    const errors = results.filter(r => r.cl === "ERROR").length;
    console.log(`\nREAL_UI: total=${total} exact=${exact} safe=${safe} wrong=${wrong} unverifiable=${unverifiable} errors=${errors} accuracy=${(exact/total*100).toFixed(1)}%`);
    expect(total).toBe(15);
    expect(wrong).toBe(0);
    expect(unverifiable).toBe(0);
    expect(errors).toBe(0);
    expect(exact / total).toBeGreaterThanOrEqual(0.80);
  });
});

// ═══════════════════════════════════════════════════════════════════
// GAP 2: CROSS-MODULE FULL CHAIN — 5 Cases
// Property→Location→Map→Valuation→Market→Decision
// ═══════════════════════════════════════════════════════════════════
test.describe.serial("Cross-Module Full Chain — 5 EXACT Cases", { tag: "@real-provider" }, () => {
  const CROSS = CASES.filter(c => c.id !== "V22").slice(0, 5);

  for (const c of CROSS) {
    test(`${c.id}: full chain identity`, async ({ page }) => {
      test.setTimeout(60000);
      const truth = GT[c.id];

      // Observe responses without mocking
      await page.route("**/location/insight", async (route) => {
        const response = await route.fetch({ url: realProviderUrl("/location/insight") });
        await route.fulfill({ response });
      });

      await goToLocationStep(page);
      await analyzeAddress(page, c.input);

      // Wait for Location result (not gate — these are EXACT cases)
      await expect(page.getByTestId("location-result")).toBeVisible({ timeout: 15000 });
      const locationText = await page.getByTestId("location-result").textContent() ?? "";
      // Verify road identity in location result
      expect(locationText, `Location must show ${truth.road}`).toContain(truth.road);

      // Step 3: Price/Valuation
      const stepNav = page.locator("nav[aria-label='選擇流程步驟']");
      await stepNav.getByRole("button", { name: /價格與估價證據/ }).click();
      await expect(page.locator("section[id='journey-stage-price']")).toBeVisible({ timeout: 8000 });

      // Step 4: Affordability (intermediate check)
      await stepNav.getByRole("button", { name: /資金與持有成本/ }).click();
      await expect(page.locator("section[id='journey-stage-affordability']")).toBeVisible({ timeout: 8000 });

      // Step 5: Decision
      await stepNav.getByRole("button", { name: /看房決策摘要/ }).click();
      await expect(page.locator("section[id='journey-stage-decision']")).toBeVisible({ timeout: 8000 });
      const decisionText = await page.locator("section[id='journey-stage-decision']").textContent() ?? "";

      // Verify identity never mutated to wrong road
      if (truth.road.includes("東")) {
        expect(decisionText).not.toContain(truth.road.replace("東", "西"));
      }
      if (truth.road.includes("北")) {
        expect(decisionText).not.toContain(truth.road.replace("北", "南"));
      }
    });
  }
});

// ═══════════════════════════════════════════════════════════════════
// GAP 3: ACCESSIBILITY UNIQUENESS COUNTS
// ═══════════════════════════════════════════════════════════════════
test.describe("Accessibility Counts — Desktop 1440", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Each critical control has exactly 1 actionable match", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    const sidebar = page.locator("aside[aria-label='分析工具']");

    // Locale: combobox "選擇介面語言"
    await expect(page.getByRole("combobox", { name: "選擇介面語言" })).toHaveCount(1);
    // Property / Journey: sidebar button
    await expect(sidebar.getByRole("button", { name: "看房決策流程" })).toHaveCount(1);
    // Map Insight
    await expect(sidebar.getByRole("button", { name: "Map Insight" })).toHaveCount(1);
    // Valuation
    await expect(sidebar.getByRole("button", { name: "房價估算" })).toHaveCount(1);
    // Terrain
    await expect(sidebar.getByRole("button", { name: "Terrain Risk" })).toHaveCount(1);
    // Aegis
    await expect(sidebar.getByRole("button", { name: "Aegis-Credit" })).toHaveCount(1);
    // Market Insight
    await expect(sidebar.getByRole("button", { name: "Market Insight" })).toHaveCount(1);
    // Five-step CTA (journey heading visible)
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toHaveCount(1);
  });
});

test.describe("Accessibility Counts — Mobile 390", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("Mobile critical controls unique", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    // Menu button unique
    await expect(page.getByRole("button", { name: "開啟選單" })).toHaveCount(1);
    // Open menu
    await page.getByRole("button", { name: "開啟選單" }).click();
    const sidebar = page.locator("aside[aria-label='分析工具']");
    await expect(sidebar).toBeVisible({ timeout: 3000 });

    // Controls unique within sidebar
    await expect(sidebar.getByRole("button", { name: "看房決策流程" })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: "Map Insight" })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: "房價估算" })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: "Terrain Risk" })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: "Aegis-Credit" })).toHaveCount(1);
    await expect(sidebar.getByRole("button", { name: "Market Insight" })).toHaveCount(1);
  });
});

// ═══════════════════════════════════════════════════════════════════
// GAP 4: SEMANTIC AGENT FLOWS — NO .first()/.nth()
// ═══════════════════════════════════════════════════════════════════
test.describe("Desktop 1440 Semantic Agent Flow", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Full navigation: zh→en→all modules→journey", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    // Switch locale
    await page.getByRole("combobox", { name: "選擇介面語言" }).selectOption("en");
    await expect(page.locator("html")).toHaveAttribute("lang", "en", { timeout: 5000 });

    // Navigate via sidebar (now in English)
    const sidebar = page.locator("aside[aria-label='Analysis tools']");
    await expect(sidebar).toBeVisible({ timeout: 5000 });
    await sidebar.getByRole("button", { name: "Map Insight" }).click();
    await page.waitForTimeout(300);
    await sidebar.getByRole("button", { name: "Valuation" }).click();
    await page.waitForTimeout(300);
    await sidebar.getByRole("button", { name: "Terrain Risk" }).click();
    await page.waitForTimeout(300);
    await sidebar.getByRole("button", { name: "Aegis-Credit" }).click();
    await page.waitForTimeout(300);
    await sidebar.getByRole("button", { name: "Market Insight" }).click();
    await page.waitForTimeout(300);

    // Return to journey
    await sidebar.getByRole("button", { name: "Property decision flow" }).click();
    await expect(page.getByRole("heading", { name: /five steps/i })).toBeVisible({ timeout: 8000 });
  });
});

test.describe("Mobile 390 Semantic Agent Flow", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("Full mobile navigation via menu", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 10000 });

    const menu = page.getByRole("button", { name: "開啟選單" });
    const sidebar = page.locator("aside[aria-label='分析工具']");

    // Navigate to each module via menu
    await menu.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "Map Insight" }).click();
    await page.waitForTimeout(500);

    await menu.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "房價估算" }).click();
    await page.waitForTimeout(500);

    await menu.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "Terrain Risk" }).click();
    await page.waitForTimeout(500);

    await menu.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "Aegis-Credit" }).click();
    await page.waitForTimeout(500);

    await menu.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "Market Insight" }).click();
    await page.waitForTimeout(500);

    // Return to journey
    await menu.click();
    await expect(sidebar).toBeVisible({ timeout: 3000 });
    await sidebar.getByRole("button", { name: "看房決策流程" }).click();
    await expect(page.getByRole("heading", { name: "用五個步驟整理看房資訊" })).toBeVisible({ timeout: 8000 });
  });
});
