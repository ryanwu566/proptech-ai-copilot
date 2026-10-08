import { expect, test } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

test("partial Location reopens with unknown failed counts and preserves unrelated route evidence at 390px", async ({ page }) => {
  const saved = e9Case();
  saved.data.locationInsight = {
    input: {}, resolved_location: { address_label: saved.data.propertyIdentityAnchor!.normalized_address, latitude: 24.16525, longitude: 120.64555, geocoding_confidence: "high" }, radius_m: 800, location_score: null,
    category_scores: { transit_score: 80, convenience_score: 60, education_score: null, green_space_score: 0, medical_score: null, risk_score: 50 },
    poi_summary: { transit_count: 1, convenience_count: 3, school_count: null, park_count: 0, medical_count: null, risk_facility_count: null }, nearest_pois: [], strengths: [], weaknesses: [], buyer_fit: { self_use_family: "資料不足", commuter: "資料不足", investor: "資料不足", elderly: "資料不足" }, valuation_context: { supports_price_reasonableness: "unknown", explanation: "" }, data_quality: { status: "limited", source: "google_places", partial: true, failed_categories: ["school", "medical"], coverage: { requested: 6, successful: 4, failed: 2 }, missing_sources: ["poi:school", "poi:medical"], warnings: ["部分 POI 類別目前無法取得。"] }, scoring_method: { weights: {}, explanation: "" }, disclaimer: "歷史查詢資料僅供參考",
  };
  const automaticCalls: string[] = [];
  await page.route("**/*", async (route) => {
    const request = route.request();
    if (request.method() === "POST" && /\/(valuation|location|terrain-risk|commute|market|satellite)\//.test(request.url())) { automaticCalls.push(request.url()); return route.abort(); }
    return route.continue();
  });
  await page.addInitScript((row) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row])), saved);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/cases/case-a/location");
  await expect(page.getByRole("heading", { level: 1, name: "區位與通勤" })).toBeVisible();
  const summary = page.getByTestId("poi-summary");
  await expect(summary).toContainText("交通");
  await expect(summary).toContainText("1");
  await expect(summary).toContainText("學校");
  await expect(summary).toContainText("學校 未提供");
  await expect(summary).toContainText("公園綠地 0");
  await expect(page.getByTestId("commute-route-card")).toContainText("24");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.reload();
  await expect(page.getByTestId("poi-summary")).toContainText("學校 未提供");
  expect(automaticCalls).toEqual([]);
});
