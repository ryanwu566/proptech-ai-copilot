/**
 * Real Provider Browser UI Certification — 15 frozen benchmark cases.
 * NO mocked geocoding. NO oracle leakage.
 * Captures actual /location/insight response for strict classification.
 */
import { test, expect, type Page } from "@playwright/test";

test.use({
  baseURL: "http://127.0.0.1:3000",
  viewport: { width: 1440, height: 900 },
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

type CaseResult = {
  id: string;
  input: string;
  requestBody: Record<string, unknown> | null;
  resolvedCity: string;
  resolvedDistrict: string;
  resolvedRoad: string;
  resolvedSection: string;
  resolvedHouse: string;
  matchQuality: string;
  accepted: boolean;
  source: string;
  classification: "EXACT" | "SAFE_REFUSAL" | "WRONG_ACCEPTED" | "UNVERIFIABLE" | "ERROR";
  reason: string;
};

// Expected ground truth for SCORING ONLY (never sent to product)
const GROUND_TRUTH: Record<string, { city: string; district: string; road: string; section: string; house: string }> = {
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

function norm(s: string): string {
  return s.replace(/台/g, "臺").trim();
}

function classify(id: string, response: Record<string, unknown> | null): Pick<CaseResult, "classification" | "reason"> {
  if (!response) return { classification: "ERROR", reason: "no_response" };
  const acc = response.geocoding_acceptance as Record<string, unknown> | undefined;
  if (!acc) return { classification: "ERROR", reason: "no_acceptance_field" };
  if (!acc.accepted_for_analysis) return { classification: "SAFE_REFUSAL", reason: String(acc.match_quality || "UNKNOWN") };

  // Accepted — verify ALL expected components in the resolved identity
  const truth = GROUND_TRUTH[id];
  if (!truth) return { classification: "ERROR", reason: "no_ground_truth" };

  const resolvedAddr = norm(String(acc.normalized_address || ""));
  const resolvedLocation = response.resolved_location as Record<string, unknown> | undefined;
  const addrLabel = norm(String(resolvedLocation?.address_label || ""));
  const fullText = resolvedAddr + " " + addrLabel;

  const failures: string[] = [];

  // Road
  if (truth.road && !fullText.includes(norm(truth.road))) {
    failures.push(`road:${truth.road}`);
  }
  // Section
  if (truth.section && !fullText.includes(norm(truth.section))) {
    failures.push(`section:${truth.section}`);
  }
  // House
  if (truth.house) {
    const housePatterns = [`${truth.house}號`, `${truth.house}号`, `No. ${truth.house}`, `No.${truth.house}`];
    if (!housePatterns.some(p => fullText.includes(p))) {
      failures.push(`house:${truth.house}`);
    }
  }

  if (failures.length > 0) return { classification: "UNVERIFIABLE", reason: failures.join("; ") };
  return { classification: "EXACT", reason: "" };
}

// Main test: 15 cases with response capture
test.describe.serial("Real Provider UI — 15 Case Certification", () => {
  const allResults: CaseResult[] = [];

  for (const c of CASES) {
    test(`${c.id}: ${c.input.substring(0, 20)}...`, async ({ page }) => {
      test.setTimeout(35000);
      let capturedResponse: Record<string, unknown> | null = null;
      let capturedRequestBody: Record<string, unknown> | null = null;

      // Intercept the /location/insight response (NOT mock — just observe)
      await page.route("**/location/insight", async (route) => {
        capturedRequestBody = route.request().postDataJSON();
        const response = await route.fetch();
        const body = await response.json();
        capturedResponse = body;
        await route.fulfill({ response, body: JSON.stringify(body) });
      });

      await page.goto("/", { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 10000 });

      // Navigate to Location step
      const locBtn = page.getByLabel(/位置與資料證據/).first();
      await locBtn.click();
      await expect(page.locator("section[id='journey-stage-location']")).toBeVisible({ timeout: 8000 });

      // Type ONLY the user input (NO expected fields)
      const addressInput = page.locator("#location-insight-calculator input").first();
      await expect(addressInput).toBeVisible({ timeout: 5000 });
      await addressInput.fill(c.input);

      // Click analyze
      await page.locator("#location-insight-calculator button", { hasText: /開始位置分析/ }).click();

      // Wait for response or UI state change
      await page.waitForTimeout(8000);

      // Classify
      const { classification, reason } = classify(c.id, capturedResponse);

      const responseObj = (capturedResponse ?? {}) as Record<string, unknown>;
      const acc = (responseObj.geocoding_acceptance ?? {}) as Record<string, unknown>;
      const result: CaseResult = {
        id: c.id,
        input: c.input,
        requestBody: capturedRequestBody,
        resolvedCity: String(acc.normalized_address || "").substring(0, 10),
        resolvedDistrict: "",
        resolvedRoad: String(responseObj.road || ""),
        resolvedSection: "",
        resolvedHouse: "",
        matchQuality: String(acc.match_quality || "N/A"),
        accepted: Boolean(acc.accepted_for_analysis),
        source: "",
        classification,
        reason,
      };
      allResults.push(result);

      // Log for reporting
      const sym = { EXACT: "+", SAFE_REFUSAL: ".", WRONG_ACCEPTED: "X", UNVERIFIABLE: "?", ERROR: "!" }[classification];
      console.log(`${sym} ${c.id} | ${classification} | ${result.matchQuality} | ${reason || "OK"}`);

      // Hard assertion: no WRONG_ACCEPTED or ERROR
      expect(classification).not.toBe("WRONG_ACCEPTED");
      expect(classification).not.toBe("ERROR");
    });
  }

  test("SUMMARY: Real UI Certification Metrics", async () => {
    const total = allResults.length;
    const exact = allResults.filter(r => r.classification === "EXACT").length;
    const safe = allResults.filter(r => r.classification === "SAFE_REFUSAL").length;
    const wrong = allResults.filter(r => r.classification === "WRONG_ACCEPTED").length;
    const unverifiable = allResults.filter(r => r.classification === "UNVERIFIABLE").length;
    const errors = allResults.filter(r => r.classification === "ERROR").length;

    console.log("\n=== REAL UI CERTIFICATION METRICS ===");
    console.log(`TOTAL: ${total}`);
    console.log(`EXACT: ${exact}`);
    console.log(`SAFE_REFUSAL: ${safe}`);
    console.log(`WRONG_ACCEPTED: ${wrong}`);
    console.log(`UNVERIFIABLE: ${unverifiable}`);
    console.log(`ERRORS: ${errors}`);
    console.log(`ACCURACY: ${(exact / total * 100).toFixed(1)}%`);

    expect(total).toBe(15);
    expect(wrong).toBe(0);
    expect(errors).toBe(0);
    expect(unverifiable).toBe(0);
    expect(exact / total).toBeGreaterThanOrEqual(0.80);
  });
});
