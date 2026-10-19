import { test, expect } from "./fixtures";
import { openLegacyJourneyWithAddress, openMethod } from "./helpers/commercial-navigation";
import { isProviderRequest } from "./helpers/provider-request";
import type { MapNearbyResult, NearbyPlace } from "../lib/api";

const ADDRESS = "臺北市信義區市府路1號";
const CHECKED_AT = "2026-10-19T04:00:00Z";

function mapResult(enriched: boolean): MapNearbyResult & { checked_at: string } {
  const places: NearbyPlace[] = ["近站 A", "近站 B"].map((name, index) => ({
    place_id: `station-${index}`, name, lat: 25.0385, lng: 121.5637,
    address: enriched ? `臺北市信義區站前${index + 1}號` : "",
    rating: enriched ? 4.2 + index * 0.5 : null,
    user_rating_count: enriched ? 80 + index * 20 : 0,
    business_status: enriched ? "OPERATIONAL" : "UNKNOWN",
    opening_status: enriched ? "open_now" : "unknown",
    opening_status_label: enriched ? "目前營業中" : "營業狀態未知",
    opening_hours_source: enriched ? "currentOpeningHours" : "businessStatus",
    distance_m: 120, types: ["transit_station"], category: "transport", source: "google_places",
  }));
  const keys = ["transport", "school", "park", "medical", "shopping", "food"];
  return {
    center: { lat: 25.0375, lng: 121.5637 }, radius_m: 800, source: "google_places", checked_at: CHECKED_AT,
    partial: false, fallback: false, failed_categories: [],
    categories: keys.map(category => ({ category, label: category === "transport" ? "交通" : category,
      count: category === "transport" ? 2 : 0, places: category === "transport" ? places : [],
      source: "google_places", availability: "available" })),
    category_status: Object.fromEntries(keys.map(category => [category, { status: "available", source: "google_places", timing_ms: 1 }])),
    evidence_quality: { status: "high", input_place_count: 2, accepted_place_count: 2, rejected_type_count: 0,
      deduplicated_count: 0, score_factor: 0.95, score_ceiling: 95 },
    livability_score: 12, livability_level: "不足", score_summary: "依兩處設施及步行距離整理。",
    category_scores: keys.map(category => ({ category, label: category === "transport" ? "交通" : category,
      weight: category === "transport" ? 25 : 15, score: category === "transport" ? 48 : 0, level: "不足",
      poi_count: category === "transport" ? 2 : 0, nearest_distance_m: category === "transport" ? 120 : null,
      explanation: "依設施數量與距離。" })),
    category_score_map: { transport: 48, school: 0, park: 0, medical: 0, shopping: 0, food: 0 },
    nearest_places: places, recommendation_text: "請核對現場步行條件。", score_explanation: "依距離與分類計分。",
    scoring_criteria: { radius_m: 800, category_weights: { transport: 25, school: 15, park: 10, medical: 10, shopping: 20, food: 20 },
      distance_bands: [{ range: "0-300m", weight: "high" }], disclaimer: "僅供參考。" },
    summary: "兩處交通設施。", disclaimer: "地圖結果僅供區位參考。",
  };
}

for (const width of [1440, 390]) {
  for (const enriched of [true, false]) {
    test(`${width}px legacy Map ${enriched ? "enriched reference" : "minimal fields"} cards and popup stay honest`, async ({ page, baseURL }, testInfo) => {
      await page.setViewportSize({ width, height: 1000 });
      const calls: string[] = [];
      const providerRequests: string[] = [];
      const errors: string[] = [];
      page.on("request", request => {
        const url = new URL(request.url());
        const metadata = /^\/(roads\/(cities|districts|roads)|map\/google-health)$/.test(url.pathname);
        const basemap = url.hostname.endsWith(".tile.openstreetmap.org");
        if (isProviderRequest(request, baseURL!) && !metadata && !basemap) providerRequests.push(`${request.method()} ${url.pathname}`);
      });
      page.on("pageerror", error => errors.push(error.message));
      await page.route("https://*.tile.openstreetmap.org/**", route => route.fulfill({ status: 204, body: "" }));
      await page.route("**/map/google-health", route => route.fulfill({ json: {
        google_key_configured: true, geocoding_enabled: true, places_enabled: true, last_error: "", mode: "google", safe_message: "Available",
      } }));
      await page.route("**/map/search", route => {
        calls.push("search");
        return route.fulfill({ json: { query: ADDRESS, matched: true, center: { lat: 25.0375, lng: 121.5637 },
          city: "臺北市", district: "信義區", road: "市府路1號", formatted_address: ADDRESS,
          place_id: "property-address", confidence: "high", source: "google_geocoding",
          source_chain: ["google_geocoding"], location_note: "Google 地址解析", disclaimer: "僅供定位參考。" } });
      });
      await page.route("**/map/nearby", route => { calls.push("nearby"); return route.fulfill({ json: mapResult(enriched) }); });
      await page.goto("/");
      await openMethod(page, "Map Insight");
      expect(calls).toEqual([]); // Entering the tool must not trigger enrichment or analysis.
      expect(providerRequests).toEqual([]);
      const map = page.locator("#map-insight");
      await map.getByRole("textbox", { name: "輸入地址、地標或路段" }).fill(ADDRESS);
      await map.getByRole("button", { name: "搜尋位置", exact: true }).click();
      const card = map.locator('button[data-assistive-label="近站 A"]');
      await expect(card).toBeVisible();
      await expect(card).toContainText("120 m");
      await expect(card).toContainText("Google Places");
      const cards = map.locator("button[data-assistive-label]");
      await expect(cards).toHaveCount(2);
      expect(await cards.evaluateAll(nodes => nodes.map(node => node.getAttribute("data-assistive-label"))))
        .toEqual(enriched ? ["近站 B", "近站 A"] : ["近站 A", "近站 B"]);
      if (enriched) {
        await expect(card).toContainText("★ 4.2 (80)");
        await expect(card).toContainText("臺北市信義區站前1號");
        await expect(card).toContainText("目前營業中");
      } else {
        await expect(card).not.toContainText(/★|\(0\)|站前|目前營業中|店家正常營運/);
        await expect(card.getByText("營業狀態未知", { exact: true })).toHaveClass(/text-slate-500/);
        expect(await card.locator("p").allTextContents()).not.toContain("");
      }
      await testInfo.attach("legacy-card", { body: await card.screenshot(), contentType: "image/png" });
      await card.click();
      const popup = map.locator(".leaflet-popup-content");
      await expect(popup).toContainText("近站 A");
      await expect(popup).toContainText("120");
      if (enriched) await expect(popup).toContainText("臺北市信義區站前1號");
      else await expect(popup).not.toContainText(/評分|站前|目前營業中/);
      await expect(map).not.toContainText(/\bundefined\b|\bnull\b|NaN/);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
      expect(calls).toEqual(["search", "nearby"]);
      expect(providerRequests).toEqual(["POST /map/search", "POST /map/nearby"]);
      expect(errors).toEqual([]);
      await testInfo.attach("legacy-rendering", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
    });
  }

  test(`${width}px guided Location keeps named-distance evidence without enrichment`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    let calls = 0;
    await page.route("**/location/insight", route => {
      calls++;
      return route.fulfill({ json: {
        input: {}, resolved_location: { address_label: ADDRESS, latitude: 25.0375, longitude: 121.5637, geocoding_confidence: "high" },
        radius_m: 800, location_score: null,
        category_scores: { transit_score: 48, convenience_score: 0, education_score: 0, green_space_score: 0, medical_score: 0, risk_score: null },
        poi_summary: { transit_count: 2, convenience_count: 0, school_count: 0, park_count: 0, medical_count: 0, risk_facility_count: null },
        nearest_pois: [{ category: "transport", name: "近站 A", distance_m: 120, source: "google_places" }],
        risk_facility_evidence: { status: "unavailable", count: null, source: null, checked_at: null, reason: "risk_facilities_source_unavailable", limitation: "未知不代表安全。" },
        strengths: ["交通設施可核對。"], weaknesses: ["風險來源未取得。"],
        buyer_fit: { self_use_family: "資料不足", commuter: "資料不足", investor: "資料不足", elderly: "資料不足" },
        valuation_context: { supports_price_reasonableness: "unknown", explanation: "區位證據僅供參考。" },
        data_quality: { status: "good", source: "google_places", checked_at: CHECKED_AT, warnings: [], missing_sources: ["risk_facilities"] },
        scoring_method: { weights: {}, explanation: "沿用設施數量與距離。" }, disclaimer: "僅供區位參考。",
      } });
    });
    await openLegacyJourneyWithAddress(page, ADDRESS);
    expect(calls).toBe(0);
    await page.locator("#location-insight-calculator").getByRole("button", { name: "開始位置分析", exact: true }).click();
    const result = page.getByTestId("location-result");
    await expect(result).toBeVisible();
    const detail = result.locator("details").filter({ hasText: "查看附近 POI 詳細資料" });
    await detail.locator("summary").click();
    await expect(detail.getByRole("row", { name: "transport 近站 A 120m google_places" })).toBeVisible();
    await expect(result).not.toContainText(/營業狀態未知|\bundefined\b|\bnull\b|NaN/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
    expect(calls).toBe(1);
    await testInfo.attach("guided-rendering", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
  });
}
