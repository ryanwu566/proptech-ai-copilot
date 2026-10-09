import { expect, test, type Page } from "@playwright/test";

const NOW = "2026-10-01T02:00:00.000Z";

function savedCase(stale = false) {
  return {
    id: "risk-case-1",
    title: "市府路風險查證",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "risk",
    progress: 60,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號", propertyPrice: 2480 },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "辦公室", area_ping: 30, building_age_years: 5, floor: 8 },
      propertyIdentityAnchor: {
        version: 1,
        scope: "journey_browser_anchor",
        journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
        address_input: "臺北市信義區市府路1號",
        normalized_address: "臺北市信義區市府路1號",
        coordinates: { latitude: 25.0375, longitude: 121.5637 },
        administrative_location: { city: "臺北市", district: "信義區", village: "西村里", village_code: "63000020-014" },
        location_status: stale ? "stale" : "candidate",
        parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
        building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
        confidence: { level: stale ? "unknown" : "high", domain: "address_spatial_correlation", basis: ["normalized_address", "trusted_geocoding_coordinates", "resolved_village"], limitations: [] },
        evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding", checked_at: NOW }, { source_id: "nlsc_village_boundary", kind: "administrative_boundary", checked_at: NOW }], checked_at: NOW, limitations: [] },
        revalidation: stale ? { status: "needs_revalidation", conflicts: ["coordinates"] } : { status: "current", conflicts: [] },
      },
      journeyContext: {
        version: 1,
        propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 2480 },
        priceBasis: "asking",
        activePriceWan: 2480,
      },
      terrainReference: {
        schema_version: 1,
        kind: "terrain_reference",
        status: "available",
        summary: "已有可供查看的參考圖層。",
        notice: "資料僅供查證規劃。",
        layers: [{
          layer_id: "flood",
          display_name: "淹水潛勢",
          state: "available",
          source_name: "淹水潛勢圖",
          source_agency: "經濟部水利署",
          data_updated_at: "2025 年版",
          coverage_status: "covered",
          caveat: "保存內容為摘要，需重新查詢完整結果。",
        }],
      },
    },
  };
}

function source(name: string, agency: string, status = "available") {
  return { name, agency, source_url: "https://example.gov.tw/evidence", status, data_updated_at: "2026-06-30", data_vintage: "2026 年版" };
}

function riskResult() {
  const hazards = {
    flood: { key: "flood", label: "淹水潛勢", status: "available", level: "high", matched: true, distance_m: 0, value: { scenario: "24h-350mm" }, explanation: "位置符合官方淹水潛勢圖層。", source: source("淹水潛勢圖", "經濟部水利署") },
    landslide: { key: "landslide", label: "大規模崩塌潛勢", status: "available", level: "unknown", matched: false, distance_m: null, value: null, explanation: "查詢完成且未比對到圖層。", source: source("大規模崩塌潛勢圖", "農業部農村發展及水土保持署") },
    debris_flow: { key: "debris_flow", label: "土石流潛勢溪流", status: "error", level: "unknown", matched: false, distance_m: null, value: null, explanation: "來源目前無法查詢。", source: source("土石流潛勢溪流", "農業部農村發展及水土保持署", "error") },
    liquefaction: { key: "liquefaction", label: "土壤液化潛勢", status: "available", level: "medium", matched: true, distance_m: 0, value: { official_classification: "中潛勢", queried_area: "臺北" }, explanation: "位置符合官方中潛勢圖層。", source: source("土壤液化潛勢範圍", "經濟部地質調查及礦業管理中心") },
    geological_sensitivity: { key: "geological_sensitivity", label: "地質敏感區", status: "available", level: "unknown", matched: true, distance_m: 0, value: { dataset_version: "2024-06-27", matched_count: 2, matches: [{ official_category: "活動斷層地質敏感區", canonical_category: "active_fault_sensitive_area" }, { official_category: "山崩與地滑地質敏感區", canonical_category: "landslide_sensitive_area" }] }, explanation: "位置交集兩項官方公告類別，不代表風險分級。", source: source("地質敏感區範圍數值檔", "經濟部地質調查及礦業管理中心") },
    active_fault: { key: "active_fault", label: "活動斷層", status: "unavailable", level: "unknown", matched: false, distance_m: null, value: null, explanation: "目前未設定可直接比對座標的官方圖資查詢。", source: source("地質雲與地質敏感圖資", "經濟部地質調查及礦業管理中心", "unavailable") },
  };
  return {
    input: { latitude: 25.0375, longitude: 121.5637, radius_m: 500 },
    resolved_location: { latitude: 25.0375, longitude: 121.5637, geocoding_source: "provided_coordinates" },
    overall: { level: "high", label: "legacy aggregate", summary: "legacy aggregate", confidence: "high" },
    terrain: { status: "available", slope_value: 3.2, slope_class: "平緩", explanation: "坡度圖資僅供參考。", source: source("國土利用與坡度資料", "內政部國土測繪中心") },
    hazards,
    risk_factors: [],
    missing_sources: ["土石流潛勢溪流官方查詢", "活動斷層官方查詢"],
    recommended_checks: [],
    map_layers: [],
    cadastral_evidence: { status: "reference_only", mode: "point_reference_only", provider: "NLSC", center: { lat: 25.0375, lng: 121.5637 }, limitation: "POINT_REFERENCE_ONLY", checked_at: NOW },
    hazard_geometries: { flood: { type: "Polygon", coordinates: [[[121.56, 25.035], [121.567, 25.035], [121.567, 25.04], [121.56, 25.04], [121.56, 25.035]]] } },
    source_transparency: {
      notice: "逐項判讀。",
      layers: Object.values(hazards).map((item) => ({ layer_id: item.key, display_name: item.label, source_name: item.source.name, source_kind: item.source.agency, assessment_status: item.status === "available" ? (item.matched ? "matched" : "not_matched") : "unavailable", coverage_status: item.status === "available" ? "covered" : "unknown", data_updated_at: item.source.data_updated_at, caveat: item.explanation })),
    },
    official_data_sources: [{ provider_id: "gsmma_geological_sensitivity", agency: "經濟部地質調查及礦業管理中心", dataset_name: "地質敏感區範圍數值檔", access_mode: "processed_artifact", authentication_mode: "none", coverage: "公告多邊形", published_version: "2024-06-27", effective_date: "2024-06-27", fetched_at: NOW, freshness_status: "configured", runtime_status: "available", limitation_summary: "僅涵蓋已載入的明確版本。" }],
    data_quality: { status: "limited", warnings: [], checked_at: NOW },
    disclaimer: "證據導向查證，不形成安全或投資建議。",
  };
}

async function seed(page: Page, stale = false, withSavedRisk = true) {
  const row = savedCase(stale);
  if (!withSavedRisk) Reflect.deleteProperty(row.data, "terrainReference");
  await page.addInitScript(({ key, row }) => {
    if (!window.localStorage.getItem(key)) window.localStorage.setItem(key, JSON.stringify([row]));
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  }, { key: "proptech.savedCases.v1", row });
  await page.route("https://*.tile.openstreetmap.org/**", (route) => route.fulfill({ status: 204, body: "" }));
  await page.route("**/terrain/satellite-reference", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ status: "limited", reason_code: null, source: "Sentinel-2 / Copernicus", dataset: "COPERNICUS/S2_SR_HARMONIZED", window_start: "2026-06-01", window_end: "2026-08-30", retrieval_time: NOW, aoi_radius_m: 500, composite_method: "90 日中位數合成", cloud_filter_percent: 35, image_reference: null, attribution: "Contains modified Copernicus Sentinel data.", limitations: ["影像不能證明法定或地質狀態。"], disclaimer: "衛星影像僅作視覺脈絡。" }),
  }));
}

test("risk route keeps saved evidence limited until an explicit refresh", async ({ page }) => {
  let analysisCalls = 0;
  await page.route("**/terrain-risk/analyze", (route) => { analysisCalls += 1; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(riskResult()) }); });
  await seed(page);
  await page.goto("/cases/risk-case-1/risk");

  await expect(page.getByRole("heading", { level: 1, name: "風險與環境" })).toBeVisible();
  await expect(page.getByText("在繼續評估此物件前，哪些環境或災害證據需要查證？")).toBeVisible();
  await expect(page.getByText("已儲存的摘要證據", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("需重新查詢才能檢視完整結果；摘要不會被重建成即時證據。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查詢目前物件風險證據" })).toBeEnabled();
  await page.reload();
  await expect(page.getByRole("button", { name: "查詢目前物件風險證據" })).toBeEnabled();
  expect(analysisCalls).toBe(0);
});

test("risk refresh blocks duplicate same-turn submit and disclosure remains free", async ({ page }) => {
  await seed(page, false, false);
  let calls = 0;
  let satelliteCalls = 0;
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => { finish = resolve; });
  await page.route("**/terrain-risk/analyze", async (route) => {
    calls += 1;
    await pending;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(riskResult()) });
  });
  await page.route("**/terrain/satellite-reference", (route) => { satelliteCalls += 1; return route.abort(); });
  await page.goto("/cases/risk-case-1/risk");
  await page.getByRole("button", { name: "查詢目前物件風險證據" }).evaluate((node) => {
    (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click();
  });
  await expect.poll(() => calls).toBe(1);
  finish();
  await expect(page.getByRole("table", { name: "風險證據表" })).toBeVisible();
  await page.getByText("衛星影像參考（輔助證據）").click();
  await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "not_run");
  expect(satelliteCalls).toBe(0);
  await page.reload();
  await expect(page.getByText("已儲存的摘要證據", { exact: true }).first()).toBeVisible();
  expect(calls).toBe(1);
  expect(satelliteCalls).toBe(0);
});

test("fresh query renders a primary map, ordered evidence, unknowns, actions, and source details", async ({ page }) => {
  await seed(page, false, false);
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(riskResult()) }));
  await page.goto("/cases/risk-case-1/risk");
  await page.getByRole("button", { name: "查詢目前物件風險證據" }).click();

  await expect(page.getByRole("region", { name: "風險與環境圖" })).toBeVisible();
  await expect(page.getByTestId("risk-property-marker")).toBeVisible();
  await expect(page.getByRole("table", { name: "風險證據表" })).toBeVisible();
  await expect(page.getByRole("button", { name: "淹水潛勢", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "本次位置符合來源分類「中潛勢」。", exact: true })).toBeVisible();
  await expect(page.getByText("2024-06-27", { exact: true })).toBeVisible();
  await expect(page.getByText("活動斷層地質敏感區", { exact: false })).toBeVisible();
  await expect(page.getByText("山崩與地滑地質敏感區", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "未知或目前無法取得" })).toBeVisible();
  await expect(page.getByText("活動斷層", { exact: true }).last()).toBeVisible();
  await expect(page.getByText("目前自動查詢路徑尚未提供完成的活動斷層判讀結果。", { exact: true }).last()).toBeVisible();
  await expect(page.getByRole("heading", { name: "下一步查證" })).toBeVisible();
  await expect(page.getByLabel("風險證據摘要").getByText("2026-10-01T02:00:00.000Z", { exact: true })).toBeVisible();
  await expect(page.getByText("legacy aggregate")).toHaveCount(0);

  const stored = await page.evaluate(() => JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0]);
  expect(stored.data.terrainReference.layers.length).toBeGreaterThan(0);
  expect(stored.data.terrainReference.layers[0].source_name).toBeTruthy();
  expect(stored.data.terrainRisk).toBeUndefined();
  expect(stored.data.hazard_geometries).toBeUndefined();

  await page.getByText("來源與方法詳情").click();
  await expect(page.getByText("地質敏感區範圍數值檔", { exact: true })).toBeVisible();
  await page.getByText("衛星影像參考（輔助證據）").click();
  await expect(page.getByTestId("satellite-evidence-card")).toBeVisible();

  await page.reload();
  await expect(page.getByText("已儲存的摘要證據", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("需重新查詢才能檢視完整結果；摘要不會被重建成即時證據。", { exact: true })).toBeVisible();
});

test("partial provider failure remains local and mobile has no document overflow", async ({ page }) => {
  await seed(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(riskResult()) }));
  await page.goto("/cases/risk-case-1/risk");
  await page.getByRole("button", { name: "查詢目前物件風險證據" }).click();

  await expect(page.getByRole("button", { name: "土石流潛勢溪流", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "目前無法取得此項證據，風險仍無法判定。", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "淹水潛勢", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});

test("stale property identity blocks a new query and keeps prior summary stale", async ({ page }) => {
  await seed(page, true);
  await page.goto("/cases/risk-case-1/risk");

  await expect(page.getByText("物件資料已變更，需重新確認後再查詢")).toBeVisible();
  await expect(page.getByRole("button", { name: "查詢目前物件風險證據" })).toBeDisabled();
  await expect(page.getByText("此摘要屬於先前物件狀態，不能作為目前證據。", { exact: true }).first()).toBeVisible();
});
