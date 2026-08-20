import { expect, test } from "./fixtures";

const transparentPng = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/gL+5aq9WQAAAABJRU5ErkJggg==", "base64");

const hazardNames = {
  landslide: "大規模崩塌潛勢",
  debris_flow: "土石流潛勢溪流",
  flood: "淹水潛勢",
  geological_sensitivity: "地質敏感區",
  liquefaction: "土壤液化潛勢",
  active_fault: "活動斷層",
};

function terrainResult(lat = 25.0375, lng = 121.5645, cadastral: Record<string, unknown> = {}) {
  const hazards = Object.fromEntries(Object.entries(hazardNames).map(([key, label]) => [key, {
    key, label, status: "unavailable", level: "unknown", matched: false, distance_m: null, value: null,
    explanation: "本次來源暫時不可用，不能解讀為低風險。",
    source: { name: label, agency: "官方測試來源", status: "unavailable" },
  }]));
  return {
    input: { address: "臺北市信義區市府路1號", radius_m: 500, include_layers: ["terrain", ...Object.keys(hazardNames)] },
    resolved_location: { address_label: "臺北市信義區市府路1號", latitude: lat, longitude: lng, geocoding_confidence: "high", geocoding_source: "tgos_geocoding" },
    overall: { level: "unknown", label: "資料不足，無法判定", summary: "部分來源尚待確認。", confidence: "unknown" },
    terrain: { status: "unavailable", slope_value: null, slope_class: null, elevation_m: null, explanation: "地勢來源暫時不可用。", source: { name: "NLSC 地勢", agency: "內政部國土測繪中心", status: "unavailable" } },
    hazards,
    risk_factors: [],
    missing_sources: ["地勢與災害官方查詢"],
    recommended_checks: ["向主管機關與地政事務所確認。"],
    map_layers: [{ key: "terrain", label: "地勢", status: "unavailable" }],
    source_transparency: { notice: "資料不足不代表沒有風險。", layers: [] },
    cadastral_evidence: {
      status: "not_configured", mode: "point_reference_only", provider: "NLSC", provider_name: "內政部國土測繪中心",
      center: { lat, lng }, raster_status: "not_configured", vector_status: "not_configured",
      source_url: "https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH",
      limitation: "POINT_REFERENCE_ONLY", checked_at: "2026-08-20T00:00:00Z", ...cadastral,
    },
    data_quality: { status: "unavailable", warnings: ["資料不足不代表沒有風險。"], checked_at: "2026-08-20T00:00:00Z" },
    timing_ms: { address_resolution_ms: 12, terrain_provider_ms: 20, slope_provider_ms: 20, flood_provider_ms: 20, geology_provider_ms: 20, total_terrain_ms: 35 },
    disclaimer: "僅供看房風險參考。",
  };
}

async function openTerrain(page: import("@playwright/test").Page) {
  await page.goto("/", { waitUntil: "networkidle" });
  const terrainButton = page.locator("aside").getByRole("button", { name: "Terrain Risk", exact: true });
  await expect(terrainButton).toBeVisible();
  await terrainButton.click();
  await expect(page.getByRole("textbox", { name: "物件地址" })).toBeVisible();
}

async function analyze(page: import("@playwright/test").Page, address = "臺北市信義區市府路1號") {
  await page.getByRole("textbox", { name: "物件地址" }).fill(address);
  await page.getByRole("button", { name: "開始地勢／災害檢查" }).click();
}

async function stubBaseTiles(page: import("@playwright/test").Page) {
  await page.route("https://*.tile.openstreetmap.org/**", (route) => route.fulfill({ status: 200, contentType: "image/png", body: transparentPng }));
}

test("point-reference result and marker render without waiting for slow base tiles", async ({ page }) => {
  let releaseTiles!: () => void;
  const tileGate = new Promise<void>((resolve) => { releaseTiles = resolve; });
  await page.route("https://*.tile.openstreetmap.org/**", async (route) => { await tileGate; await route.fulfill({ status: 200, contentType: "image/png", body: transparentPng }); });
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult()) }));
  await openTerrain(page);

  const started = Date.now();
  await analyze(page);
  await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
  const terrainResultVisibleMs = Date.now() - started;
  await expect(page.getByTestId("cadastral-map-shell")).toBeVisible();
  const mapShellMs = Date.now() - started;
  await expect(page.getByTestId("terrain-analyzed-marker")).toBeVisible();
  await expect(page.getByTestId("cadastral-availability-status")).toContainText("未設定可用的地籍圖資服務");
  await expect(page.getByTestId("cadastral-point-reference-limitation")).toContainText("POINT_REFERENCE_ONLY");
  await expect(page.getByTestId("cadastral-point-reference-limitation")).toContainText("系統未取得法定地籍向量");
  const totalUsefulResultMs = Date.now() - started;
  expect(totalUsefulResultMs).toBeLessThan(5000);
  console.log(`GEOSPATIAL_LOCAL_TIMING=${JSON.stringify({ terrain_result_visible_ms: terrainResultVisibleMs, cadastral_map_shell_ms: mapShellMs, total_useful_result_ms: totalUsefulResultMs })}`);

  releaseTiles();
});

test("configured fixture tile becomes visible as reference without a parcel polygon", async ({ page }) => {
  await stubBaseTiles(page);
  await page.route("**/e2e-cadastral/**", (route) => route.fulfill({ status: 200, contentType: "image/png", body: transparentPng }));
  const result = terrainResult(25.0375, 121.5645, {
    status: "reference_only", mode: "wmts", raster_status: "verified_configured",
    tile_url_template: "/e2e-cadastral/{z}/{x}/{y}.png", attribution: "NLSC fixture",
  });
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) }));
  await openTerrain(page);

  const started = Date.now();
  await analyze(page);
  await expect(page.getByTestId("cadastral-availability-status")).toContainText("地籍影像僅供位置參考");
  const cadastralVisibleMs = Date.now() - started;
  await expect(page.getByTestId("terrain-analyzed-marker")).toBeVisible();
  await expect(page.getByTestId("terrain-cadastral-map").locator(".leaflet-overlay-pane polygon")).toHaveCount(0);
  await expect(page.getByTestId("cadastral-point-reference-limitation")).toBeVisible();
  console.log(`CADASTRAL_FIXTURE_TIMING=${JSON.stringify({ cadastral_first_tile_ms: cadastralVisibleMs, cadastral_visible_ms: cadastralVisibleMs })}`);
});

test("slow cadastral overlay stays off the useful-result critical path", async ({ page }) => {
  await stubBaseTiles(page);
  let releaseCadastralTiles!: () => void;
  const cadastralTileGate = new Promise<void>((resolve) => { releaseCadastralTiles = resolve; });
  await page.route("**/e2e-cadastral/**", async (route) => { await cadastralTileGate; await route.fulfill({ status: 200, contentType: "image/png", body: transparentPng }); });
  const result = terrainResult(25.0375, 121.5645, {
    status: "reference_only", mode: "wmts", raster_status: "verified_configured",
    tile_url_template: "/e2e-cadastral/{z}/{x}/{y}.png", attribution: "NLSC fixture",
  });
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) }));
  await openTerrain(page);

  const started = Date.now();
  await analyze(page);
  await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
  await expect(page.getByTestId("cadastral-map-shell")).toBeVisible();
  await expect(page.getByTestId("terrain-analyzed-marker")).toBeVisible();
  await expect(page.getByTestId("cadastral-availability-status")).toContainText("地籍參考圖載入中");
  expect(Date.now() - started).toBeLessThan(5000);

  releaseCadastralTiles();
  await expect(page.getByTestId("cadastral-availability-status")).toContainText("地籍影像僅供位置參考");
});

for (const failure of ["404", "timeout"] as const) {
  test(`cadastral tile ${failure} does not destroy Terrain result`, async ({ page }) => {
    await stubBaseTiles(page);
    await page.route("**/e2e-cadastral/**", (route) => failure === "404" ? route.fulfill({ status: 404, body: "" }) : route.abort("timedout"));
    const result = terrainResult(25.0375, 121.5645, {
      status: "reference_only", mode: "wmts", raster_status: "verified_configured",
      tile_url_template: "/e2e-cadastral/{z}/{x}/{y}.png", attribution: "NLSC fixture",
    });
    await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) }));
    await openTerrain(page);

    await analyze(page);
    await expect(page.getByTestId("cadastral-availability-status")).toContainText("地籍參考暫時不可用");
    await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
    await expect(page.getByTestId("terrain-priority-follow-up")).toBeVisible();
  });
}

test("wrong or CSP-ineligible tile host fails closed", async ({ page }) => {
  await stubBaseTiles(page);
  const result = terrainResult(25.0375, 121.5645, {
    status: "reference_only", mode: "wmts", raster_status: "verified_configured",
    tile_url_template: "https://wrong.invalid/cadastral/{z}/{x}/{y}.png",
  });
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) }));
  await openTerrain(page);

  await analyze(page);
  await expect(page.getByTestId("cadastral-availability-status")).toContainText("地籍參考暫時不可用");
  await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
});

test("CSP-blocked NLSC fixture tile leaves Terrain result intact", async ({ page }) => {
  await stubBaseTiles(page);
  const result = terrainResult(25.0375, 121.5645, {
    status: "reference_only", mode: "wmts", raster_status: "verified_configured",
    tile_url_template: "https://wmts.nlsc.gov.tw/e2e-cadastral/{z}/{x}/{y}.png",
  });
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) }));
  await openTerrain(page);

  await analyze(page);
  await expect(page.getByTestId("cadastral-availability-status")).toContainText("地籍參考暫時不可用");
  await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
  await expect(page.getByTestId("terrain-analyzed-marker")).toBeVisible();
});

test("second analysis replaces coordinates and marker position", async ({ page }) => {
  await stubBaseTiles(page);
  let call = 0;
  await page.route("**/terrain-risk/analyze", (route) => {
    call += 1;
    const result = call === 1 ? terrainResult(25.0375, 121.5645) : terrainResult(24.1477, 120.6736);
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) });
  });
  await openTerrain(page);

  await analyze(page);
  await expect(page.getByText("25.037500, 121.564500")).toBeVisible();
  await expect(page.getByTestId("terrain-analyzed-marker")).toHaveAttribute("data-lat", "25.0375");
  await page.getByRole("textbox", { name: "物件地址" }).fill("臺中市西屯區臺灣大道三段99號");
  await page.getByRole("button", { name: "開始地勢／災害檢查" }).click();
  await expect(page.getByText("24.147700, 120.673600")).toBeVisible();
  await expect(page.getByTestId("terrain-analyzed-marker")).toHaveAttribute("data-lat", "24.1477");

  expect(call).toBe(2);
});

test("cadastral evidence copy changes at runtime in all four locales", async ({ page }) => {
  await stubBaseTiles(page);
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult()) }));
  await openTerrain(page);
  await analyze(page);

  const locale = page.locator("select").first();
  for (const [value, title, limitation] of [
    ["zh-TW", "地籍參考證據", "點位參考模式"],
    ["en", "Cadastral reference evidence", "Point-reference-only mode"],
    ["ja", "地籍参照エビデンス", "点位置参照モード"],
    ["ko", "지적 참고 근거", "점 위치 참고 모드"],
  ] as const) {
    await locale.selectOption(value);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
    await expect(page.getByTestId("cadastral-point-reference-limitation")).toContainText(limitation);
  }
});

test("cadastral map fits 390x844 with attribution and limitation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await stubBaseTiles(page);
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult()) }));
  await page.goto("/", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "開啟選單" }).click();
  await page.locator("aside").getByRole("button", { name: "Terrain Risk", exact: true }).click();

  await analyze(page);
  const mobileMap = page.getByTestId("cadastral-map-shell").locator(".leaflet-container");
  await expect(mobileMap).toBeVisible();
  await expect(mobileMap.locator(".leaflet-control-attribution")).toBeVisible();
  await expect(page.getByTestId("cadastral-point-reference-limitation")).toBeVisible();
  const metrics = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth, mapWidth: document.querySelector<HTMLElement>('[data-testid="cadastral-map-shell"] .leaflet-container')?.getBoundingClientRect().width ?? 0 }));
  expect(metrics.overflow).toBeLessThanOrEqual(0);
  expect(metrics.mapWidth).toBeLessThanOrEqual(390);
  expect(metrics.mapWidth).toBeGreaterThan(300);
});
