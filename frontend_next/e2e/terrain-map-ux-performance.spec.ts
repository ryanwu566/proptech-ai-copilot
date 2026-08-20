import { expect, test } from "./fixtures";

const layerNames = {
  landslide: "大規模崩塌潛勢",
  debris_flow: "土石流潛勢溪流",
  flood: "淹水潛勢",
  geological_sensitivity: "地質敏感區",
  liquefaction: "土壤液化潛勢",
  active_fault: "活動斷層",
};

function hazard(key: keyof typeof layerNames, status: "available" | "limited" | "unavailable", matched = false) {
  return {
    key,
    label: layerNames[key],
    status,
    level: matched ? "high" : "unknown",
    matched,
    distance_m: matched ? 80 : null,
    value: null,
    explanation: matched ? `${layerNames[key]}有官方比對證據，請優先確認。` : status === "available" ? "已完成來源比對；未形成安全結論。" : "本次資料暫時不可用，不能解讀為低風險。",
    source: { name: `${layerNames[key]}來源`, agency: "官方測試來源", source_url: "https://example.invalid", status },
  };
}

const terrainResult = {
  input: { address: "台北市大安區和平東路二段", radius_m: 500, include_layers: ["terrain", ...Object.keys(layerNames)] },
  resolved_location: { address_label: "台北市大安區和平東路二段", latitude: 25.026, longitude: 121.543, geocoding_confidence: "high" },
  overall: { level: "high", label: "需優先確認", summary: "存在需優先確認的官方證據。", confidence: "medium" },
  terrain: { status: "available", slope_value: 8, slope_class: "緩坡", elevation_m: 22, explanation: "地勢資料可用。", source: { name: "地勢來源", agency: "官方測試來源", source_url: "https://example.invalid", status: "available" } },
  hazards: {
    landslide: hazard("landslide", "available", true),
    debris_flow: hazard("debris_flow", "available"),
    flood: hazard("flood", "unavailable"),
    geological_sensitivity: hazard("geological_sensitivity", "limited"),
    liquefaction: hazard("liquefaction", "available"),
    active_fault: hazard("active_fault", "available"),
  },
  risk_factors: [{ key: "landslide", level: "high", title: "大規模崩塌潛勢", message: "有官方比對證據，請優先確認。", source_name: "官方測試來源" }],
  missing_sources: ["淹水潛勢資料暫時不可用"],
  recommended_checks: ["向主管機關確認來源與現地條件。"],
  map_layers: [
    { key: "terrain", label: "地勢", status: "available" },
    ...Object.entries(layerNames).map(([key, label]) => ({ key, label, status: key === "flood" ? "unavailable" : "available" })),
  ],
  source_transparency: {
    notice: "資料不足或暫時不可用不代表沒有風險。",
    layers: ["terrain", ...Object.keys(layerNames)].map((key) => ({
      layer_id: key,
      display_name: key === "terrain" ? "地勢" : layerNames[key as keyof typeof layerNames],
      source_name: "官方測試來源",
      source_kind: "official",
      assessment_status: key === "landslide" ? "matched" : key === "flood" ? "unavailable" : "not_matched",
      coverage_status: key === "flood" ? "unknown" : "covered",
      data_updated_at: "2026-08-20",
      caveat: key === "flood" ? "暫時不可用不能解讀為低風險。" : "僅供參考，不形成安全結論。",
    })),
  },
  data_quality: { status: "limited", warnings: ["部分來源不可用。"], checked_at: "2026-08-20T00:00:00Z" },
  disclaimer: "僅供看房風險參考，不形成安全或購買結論。",
};

const place = {
  place_id: "google-place-1", name: "測試捷運站", lat: 25.027, lng: 121.544, address: "台北市大安區", rating: 4.5,
  user_rating_count: 100, business_status: "OPERATIONAL", opening_status: "operational", opening_status_label: "店家正常營運",
  opening_hours_source: "businessStatus", distance_m: 120, types: ["transit_station"], category: "transport", source: "google_places",
};

const mapResult = {
  center: { lat: 25.026, lng: 121.543 }, radius_m: 800, source: "google_places", partial: true, fallback: false,
  failed_categories: ["medical"], category_status: { medical: { status: "error", source: "unavailable", timing_ms: 500 } },
  categories: [
    { category: "transport", label: "交通", count: 1, places: [place], source: "google_places", availability: "available" },
    ...["school", "park", "shopping", "food"].map((category) => ({ category, label: category, count: 0, places: [], source: "google_places", availability: "available" })),
  ],
  livability_score: 25, livability_level: "不足", score_summary: "部分類別可用，結果僅供參考。",
  category_scores: ["transport", "school", "park", "medical", "shopping", "food"].map((category) => ({ category, label: category, weight: category === "transport" ? 25 : 15, score: category === "transport" ? 100 : 0, level: category === "transport" ? "極佳" : "不足", poi_count: category === "transport" ? 1 : 0, nearest_distance_m: category === "transport" ? 120 : null, explanation: category === "medical" ? "資料暫時不可用。" : "依可用資料呈現。" })),
  category_score_map: { transport: 100, school: 0, park: 0, medical: 0, shopping: 0, food: 0 }, nearest_places: [place],
  recommendation_text: "請搭配現地確認。", score_explanation: "依可用設施距離整理。",
  scoring_criteria: { radius_m: 800, category_weights: { transport: 25, school: 15, park: 10, medical: 10, shopping: 20, food: 20 }, distance_bands: [{ range: "0-300m", weight: "high" }, { range: "300-800m", weight: "medium" }, { range: "800m+", weight: "excluded" }], disclaimer: "僅供參考。" },
  summary: "部分真實類別可用。", disclaimer: "地圖結果僅供區位參考。",
};

async function openTool(page: import("@playwright/test").Page, name: "Terrain Risk" | "Map Insight") {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.locator("aside").getByRole("button", { name, exact: true }).click();
}

async function startProgressTracking(page: import("@playwright/test").Page, testId: string) {
  await page.evaluate((id) => {
    const trackedWindow = window as typeof window & { __analysisProgressValues?: number[]; __analysisProgressObserver?: MutationObserver };
    trackedWindow.__analysisProgressValues = [];
    trackedWindow.__analysisProgressObserver?.disconnect();
    const record = () => {
      const progressbar = document.querySelector(`[data-testid="${id}"] [role="progressbar"]`);
      const value = Number(progressbar?.getAttribute("aria-valuenow"));
      const values = trackedWindow.__analysisProgressValues ?? [];
      if (Number.isFinite(value) && values.at(-1) !== value) values.push(value);
      trackedWindow.__analysisProgressValues = values;
    };
    const observer = new MutationObserver(record);
    observer.observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ["aria-valuenow"] });
    trackedWindow.__analysisProgressObserver = observer;
  }, testId);
}

async function expectMonotonicCompletion(page: import("@playwright/test").Page) {
  const values = await page.evaluate(() => {
    const trackedWindow = window as typeof window & { __analysisProgressValues?: number[]; __analysisProgressObserver?: MutationObserver };
    trackedWindow.__analysisProgressObserver?.disconnect();
    return trackedWindow.__analysisProgressValues ?? [];
  });
  expect(values.some((value) => value < 100)).toBeTruthy();
  expect(values.at(-1)).toBe(100);
  expect(values.every((value, index) => index === 0 || value >= values[index - 1])).toBeTruthy();
}

test("Terrain buyer-first progress and evidence hierarchy are honest", async ({ page }) => {
  let releaseResponse!: () => void;
  const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve; });
  await page.route("**/terrain-risk/analyze", async (route) => { await responseGate; await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult) }); });
  await openTool(page, "Terrain Risk");

  const address = page.getByRole("textbox", { name: "物件地址" });
  await expect(address).toBeVisible();
  const advanced = page.getByTestId("terrain-advanced-settings");
  await expect(advanced).not.toHaveAttribute("open", "");
  await expect(page.getByRole("spinbutton", { name: "緯度" })).not.toBeVisible();
  await address.fill("台北市大安區和平東路二段");
  await startProgressTracking(page, "terrain-analysis-progress");

  const started = Date.now();
  await page.getByRole("button", { name: "開始地勢／災害檢查" }).click();
  const progress = page.getByTestId("terrain-analysis-progress");
  await expect(progress).toBeVisible({ timeout: 500 });
  expect(Date.now() - started).toBeLessThan(500);
  const waitingValue = Number(await progress.getByRole("progressbar").getAttribute("aria-valuenow"));
  expect(waitingValue).toBeLessThan(100);

  releaseResponse();
  await expect(progress.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  await expect(page.getByTestId("terrain-data-completeness")).toContainText("資料完整度");
  await expect(page.getByTestId("terrain-priority-follow-up")).toContainText("大規模崩塌潛勢");
  const floodCard = page.locator("div", { hasText: "淹水潛勢" }).filter({ hasText: "暫時不可用" }).last();
  await expect(floodCard).toBeVisible();
  await expect(floodCard).not.toContainText("較低風險");
  await expectMonotonicCompletion(page);
});

test("Map performs one geocode and preserves partial real categories", async ({ page }) => {
  let releaseSearch!: () => void;
  const searchGate = new Promise<void>((resolve) => { releaseSearch = resolve; });
  let geocodingCalls = 0;
  await page.route("**/map/search", async (route) => {
    geocodingCalls += 1;
    await searchGate;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ query: "台北市大安區和平東路二段", matched: true, center: { lat: 25.026, lng: 121.543 }, city: "台北市", district: "大安區", road: "和平東路二段", source: "google_geocoding", source_chain: ["google_geocoding", "tgos_geocoding", "mock"], formatted_address: "台北市大安區和平東路二段", place_id: "google-address", confidence: "high", location_note: "Google Geocoding 定位結果。", disclaimer: "定位參考。" }) });
  });
  await page.route("**/map/nearby", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mapResult) }));
  await openTool(page, "Map Insight");

  const input = page.getByRole("textbox", { name: "輸入地址、地標或路段" });
  await expect(input).toBeVisible();
  await expect(page.getByTestId("map-advanced-settings")).not.toHaveAttribute("open", "");
  await input.fill("台北市大安區和平東路二段");
  await startProgressTracking(page, "map-analysis-progress");
  await page.getByRole("button", { name: "搜尋位置" }).click();
  const progress = page.getByTestId("map-analysis-progress");
  await expect(progress).toBeVisible({ timeout: 500 });
  expect(Number(await progress.getByRole("progressbar").getAttribute("aria-valuenow"))).toBeLessThan(100);

  releaseSearch();
  await expect(progress.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  await expect(page.getByTestId("map-partial-notice")).toBeVisible();
  await expect(page.getByText("測試捷運站").first()).toBeVisible();
  await expect(page.getByText("Google Places").first()).toBeVisible();
  expect(geocodingCalls).toBe(1);
  await expectMonotonicCompletion(page);
});

test("Map blocks rejected geocoding before POI analysis until explicit confirmation", async ({ page }) => {
  let nearbyCalls = 0;
  await page.route("**/map/search", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      query: "花蓮 富世291號",
      matched: true,
      center: { lat: 24.151, lng: 121.621 },
      city: "花蓮縣",
      district: "秀林鄉",
      road: "富世",
      source: "tgos_geocoding",
      source_chain: ["google_geocoding", "tgos_geocoding", "mock"],
      formatted_address: "花蓮縣秀林鄉富世135號",
      place_id: "",
      confidence: "low",
      location_note: "門牌不一致，必須先確認。",
      disclaimer: "定位參考。",
      geocoding_acceptance: {
        original_query: "花蓮 富世291號",
        normalized_address: "花蓮縣秀林鄉富世135號",
        resolved_lat: 24.151,
        resolved_lng: 121.621,
        geocoding_source: "tgos_geocoding",
        match_quality: "MISMATCH",
        accepted_for_analysis: false,
        requires_confirmation: true,
        mismatch_reasons: ["house_number_mismatch"],
        message: "門牌不一致；請確認或修正定位後再分析。",
      },
    }),
  }));
  await page.route("**/map/nearby", (route) => {
    nearbyCalls += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mapResult) });
  });
  await openTool(page, "Map Insight");

  await page.getByRole("textbox", { name: "輸入地址、地標或路段" }).fill("花蓮 富世291號");
  await page.getByRole("button", { name: "搜尋位置" }).click();
  const gate = page.getByTestId("geocoding-acceptance-gate");
  await expect(gate).toContainText("花蓮 富世291號");
  await expect(gate).toContainText("花蓮縣秀林鄉富世135號");
  await expect(gate).toContainText("MISMATCH");
  expect(nearbyCalls).toBe(0);
  await expect(page.getByText("測試捷運站")).toHaveCount(0);

  await page.getByTestId("confirm-geocoding-match").click();
  await expect(page.getByText("測試捷運站").first()).toBeVisible();
  expect(nearbyCalls).toBe(1);
});

test("Map clears old evidence and ignores a late A response after B wins", async ({ page }) => {
  let releaseLateA!: () => void;
  const lateAGate = new Promise<void>((resolve) => { releaseLateA = resolve; });
  let nearbyCalls = 0;
  await page.route("**/map/search", async (route) => {
    const payload = route.request().postDataJSON() as { query: string };
    const isLateA = payload.query.includes("和平東路");
    if (isLateA) await lateAGate;
    const label = isLateA ? "LATE-A-RESOLVED" : payload.query.includes("市府路") ? "B-WINNER-RESOLVED" : "BASE-RESOLVED";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        query: payload.query,
        matched: true,
        center: { lat: isLateA ? 25.026 : 25.034, lng: isLateA ? 121.543 : 121.565 },
        city: "臺北市",
        district: isLateA ? "大安區" : "信義區",
        road: "",
        source: "google_geocoding",
        source_chain: ["google_geocoding", "tgos_geocoding", "mock"],
        formatted_address: label,
        place_id: label,
        confidence: "high",
        location_note: "Controlled accepted geocode.",
        disclaimer: "定位參考。",
        geocoding_acceptance: {
          original_query: payload.query,
          normalized_address: label,
          resolved_lat: isLateA ? 25.026 : 25.034,
          resolved_lng: isLateA ? 121.543 : 121.565,
          geocoding_source: "google_geocoding",
          match_quality: "EXACT_OR_ACCEPTABLE",
          accepted_for_analysis: true,
          requires_confirmation: false,
          mismatch_reasons: [],
          message: "可進行分析。",
        },
      }),
    });
  });
  await page.route("**/map/nearby", (route) => {
    nearbyCalls += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mapResult) });
  });
  await openTool(page, "Map Insight");

  const input = page.getByRole("textbox", { name: "輸入地址、地標或路段" });
  await input.fill("臺北市信義區松仁路BASE");
  await page.getByRole("button", { name: "搜尋位置" }).click();
  await expect(page.getByText("BASE-RESOLVED").first()).toBeVisible();

  await input.fill("臺北市大安區和平東路A");
  await page.getByRole("button", { name: "搜尋位置" }).click();
  await expect(page.getByText("BASE-RESOLVED")).toHaveCount(0);
  await input.fill("臺北市信義區市府路B");
  await expect(page.getByRole("button", { name: "搜尋位置" })).toBeEnabled();
  await page.getByRole("button", { name: "搜尋位置" }).click();
  await expect(page.getByText("B-WINNER-RESOLVED").first()).toBeVisible();
  releaseLateA();
  await page.waitForTimeout(100);
  await expect(page.getByText("B-WINNER-RESOLVED").first()).toBeVisible();
  await expect(page.getByText("LATE-A-RESOLVED")).toHaveCount(0);
  expect(nearbyCalls).toBe(2);
});

test("Terrain clears old evidence and ignores a late request after inputs change", async ({ page }) => {
  let releaseLate!: () => void;
  const lateGate = new Promise<void>((resolve) => { releaseLate = resolve; });
  let callCount = 0;
  await page.route("**/terrain-risk/analyze", async (route) => {
    callCount += 1;
    const currentCall = callCount;
    const payload = route.request().postDataJSON() as { address?: string };
    if (currentCall === 2) await lateGate;
    const title = currentCall === 1 ? "BASE-TERRAIN-EVIDENCE" : currentCall === 2 ? "LATE-A-TERRAIN-EVIDENCE" : "B-WINNER-TERRAIN-EVIDENCE";
    const response = {
      ...terrainResult,
      input: { ...terrainResult.input, address: payload.address },
      resolved_location: { ...terrainResult.resolved_location, address_label: payload.address },
      risk_factors: [{ key: "controlled", level: "high", title, message: "Controlled browser race fixture.", source_name: "E2E" }],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(response) });
  });
  await openTool(page, "Terrain Risk");

  const address = page.getByRole("textbox", { name: "物件地址" });
  const analyze = page.getByRole("button", { name: "開始地勢／災害檢查" });
  await address.fill("臺北市信義區松仁路BASE");
  await analyze.click();
  await expect(page.getByTestId("terrain-priority-follow-up")).toContainText("BASE-TERRAIN-EVIDENCE");

  await analyze.click();
  await expect(page.getByTestId("terrain-data-completeness")).toHaveCount(0);
  await address.fill("臺北市信義區市府路B");
  await expect(analyze).toBeEnabled();
  await analyze.click();
  await expect(page.getByTestId("terrain-priority-follow-up")).toContainText("B-WINNER-TERRAIN-EVIDENCE");
  releaseLate();
  await page.waitForTimeout(100);
  await expect(page.getByTestId("terrain-priority-follow-up")).toContainText("B-WINNER-TERRAIN-EVIDENCE");
  await expect(page.getByText("LATE-A-TERRAIN-EVIDENCE")).toHaveCount(0);
  expect(callCount).toBe(3);
});

for (const tool of ["Terrain Risk", "Map Insight"] as const) {
  test(`${tool} has no horizontal overflow at 390x844`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "開啟選單" }).click();
    await page.locator("aside").getByRole("button", { name: tool, exact: true }).click();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}
