import { expect, test } from "./fixtures";

const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/gL+5aq9WQAAAABJRU5ErkJggg==", "base64");
const hazardKeys = ["landslide", "debris_flow", "flood", "geological_sensitivity", "liquefaction", "active_fault"];
const polygonA = [[[121.55, 25.03], [121.55, 25.031], [121.551, 25.031], [121.551, 25.03], [121.55, 25.03]]];
const polygonB = [[[120.30, 22.63], [120.30, 22.631], [120.301, 22.631], [120.301, 22.63], [120.30, 22.63]]];

function pointEvidence() {
  return {
    status: "point_reference_only", source: "point_reference", geometry_type: "Point",
    geometry: { type: "Point", coordinates: [121.5505, 25.0305] }, centroid: { lat: 25.0305, lng: 121.5505 },
    crs_normalized: "EPSG:4326", area_semantics: "not_available", legal_boundary: false,
    can_spatial_intersect: false, geometry_validity: "VALID", source_label: "POINT_REFERENCE",
    limitation: "Point reference only; no parcel boundary or legal area.", checked_at: "2026-08-20T00:00:00Z",
    location_geometry_consistency: "NOT_CHECKED",
  };
}

function uploadedEvidence(name: string) {
  const isB = name.includes("b.") || name.includes("mismatch");
  const coordinates = isB ? polygonB : polygonA;
  const source = name.endsWith(".kml") ? "uploaded_kml" : name.endsWith(".zip") ? "uploaded_shapefile" : "uploaded_geojson";
  return {
    status: "user_provided", source, geometry_type: "Polygon", geometry: { type: "Polygon", coordinates },
    centroid: isB ? { lat: 22.6305, lng: 120.3005 } : { lat: 25.0305, lng: 121.5505 },
    bbox: isB ? [120.30, 22.63, 120.301, 22.631] : [121.55, 25.03, 121.551, 25.031],
    crs_original: "EPSG:4326", crs_normalized: "EPSG:4326", area_m2: 11250,
    area_semantics: "computed_geometry_area", legal_boundary: false, can_spatial_intersect: true,
    geometry_validity: "VALID", limitation: "USER_PROVIDED_GEOMETRY. Computed area is not legal area.",
    source_label: "USER_PROVIDED_GEOMETRY", checked_at: `2026-08-20T00:00:0${isB ? "2" : "1"}Z`,
    location_geometry_consistency: isB ? "POSSIBLE_MISMATCH" : "CONSISTENT",
    timing_ms: { parse_ms: 2.4, geometry_validation_ms: 1.2 },
  };
}

function terrainResult({ landsect = true } = {}) {
  const hazards = Object.fromEntries(hazardKeys.map((key) => [key, {
    key, label: key, status: "unavailable", level: "unknown", matched: false, distance_m: null,
    value: null, explanation: "No hazard geometry is available.",
    source: { name: key, agency: "fixture", status: "unavailable" },
  }]));
  return {
    input: { address: "Taipei fixture", radius_m: 500, include_layers: ["terrain", ...hazardKeys] },
    resolved_location: { address_label: "Taipei fixture", latitude: 25.0305, longitude: 121.5505, geocoding_confidence: "high", geocoding_source: "provided_coordinates" },
    overall: { level: "unknown", label: "Reference only", summary: "Evidence is incomplete.", confidence: "unknown" },
    terrain: { status: "unavailable", slope_value: null, slope_class: null, elevation_m: null, explanation: "Terrain unavailable.", source: { name: "fixture", agency: "fixture", status: "unavailable" } },
    hazards, risk_factors: [], missing_sources: ["hazard geometry"], recommended_checks: ["Confirm with the responsible authority."],
    map_layers: [{ key: "terrain", label: "Terrain", status: "unavailable" }],
    cadastral_evidence: { status: "not_configured", mode: "point_reference_only", provider: "NLSC", center: { lat: 25.0305, lng: 121.5505 }, raster_status: "not_configured", vector_status: "not_configured", limitation: "POINT_REFERENCE_ONLY", checked_at: "2026-08-20T00:00:00Z" },
    parcel_geometry_evidence: pointEvidence(),
    landsect_context: landsect ? {
      status: "VERIFIED_PUBLIC", semantics: "SECTION_CONTEXT_NOT_PARCEL_BOUNDARY", provider: "NLSC", layer: "LANDSECT",
      tile_url_template: "/e2e-landsect/{z}/{x}/{y}.png", attribution: "NLSC LANDSECT fixture",
      source_url: "https://maps.nlsc.gov.tw/S09SOA/pro/Wmts_ajax_spec.jsp",
      limitation: "Section map context only, not parcel boundary.", checked_at: "2026-08-20T00:00:00Z",
    } : { status: "UNAVAILABLE", semantics: "SECTION_CONTEXT_NOT_PARCEL_BOUNDARY", provider: "NLSC", layer: "LANDSECT", limitation: "Unavailable", checked_at: "2026-08-20T00:00:00Z" },
    source_transparency: { notice: "Reference only", layers: [] },
    data_quality: { status: "unavailable", warnings: ["No hazard geometry"], checked_at: "2026-08-20T00:00:00Z" },
    disclaimer: "Terrain reference only.",
  };
}

async function prepare(page: import("@playwright/test").Page, options: { landsect?: boolean; tileFailure?: boolean } = {}) {
  await page.route("https://*.tile.openstreetmap.org/**", (route) => route.fulfill({ status: 200, contentType: "image/png", body: png }));
  await page.route("**/e2e-landsect/**", (route) => options.tileFailure ? route.abort("timedout") : route.fulfill({ status: 200, contentType: "image/png", body: png }));
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult({ landsect: options.landsect ?? true })) }));
  await page.goto("/", { waitUntil: "networkidle" });
  await page.locator("select").first().selectOption("en");
  const terrainButton = page.locator("aside").getByRole("button", { name: "Terrain Risk", exact: true });
  if ((page.viewportSize()?.width ?? 1000) <= 430) await terrainButton.evaluate((element) => (element as HTMLButtonElement).click());
  else await terrainButton.click();
  const advanced = page.getByTestId("terrain-advanced-settings");
  await expect(advanced).not.toHaveAttribute("open", "");
  await advanced.locator("summary").click();
  await expect(page.getByTestId("parcel-upload-control")).toBeVisible();
}

async function analyze(page: import("@playwright/test").Page) {
  await page.getByRole("textbox", { name: "Property address" }).fill("Taipei fixture");
  await page.getByRole("button", { name: "Start terrain and hazard check" }).click();
  await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
}

function installUploadFixture(page: import("@playwright/test").Page, delayA = 0) {
  return page.route("**/parcel-geometry/upload", async (route) => {
    const body = route.request().postDataBuffer()?.toString("latin1") ?? "";
    const match = body.match(/filename="([^"]+)"/i);
    const filename = match?.[1] ?? "unknown.geojson";
    if (filename.includes("unknown")) {
      await route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ detail: { code: "UNKNOWN_CRS", message: "Unknown CRS" } }) }); return;
    }
    if (filename.includes("invalid")) {
      await route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ detail: { code: "INVALID_GEOMETRY", message: "Invalid geometry" } }) }); return;
    }
    if (delayA && filename === "a.geojson") await new Promise((resolve) => setTimeout(resolve, delayA));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(uploadedEvidence(filename)) });
  });
}

test("address-only remains point reference and LANDSECT failure is non-blocking", async ({ page }) => {
  await prepare(page, { tileFailure: true });
  await analyze(page);
  await expect(page.getByTestId("parcel-source-badge")).toContainText("Point reference");
  await expect(page.getByTestId("cadastral-point-reference-limitation")).toContainText("POINT_REFERENCE");
  await expect(page.getByTestId("landsect-semantics")).toContainText("not a parcel boundary");
  await expect(page.getByTestId("terrain-data-completeness")).toBeVisible();
  await expect(page.locator('path[stroke="#0891b2"]')).toHaveCount(0);
});

test("actual GeoJSON upload shows progress, replaces A with B, warns mismatch, and removes without refresh", async ({ page }) => {
  await prepare(page);
  await installUploadFixture(page, 250);
  await analyze(page);
  const input = page.getByTestId("parcel-geometry-file-input");
  await input.setInputFiles({ name: "a.geojson", mimeType: "application/geo+json", buffer: Buffer.from(JSON.stringify({ type: "Polygon", coordinates: polygonA })) });
  await expect(page.getByTestId("parcel-upload-progress")).toContainText("Validating");
  await expect(page.getByTestId("parcel-upload-progress")).not.toContainText("Geometry loaded");
  await expect(page.getByTestId("parcel-upload-summary")).toBeVisible();
  const polygonPath = page.locator('path[stroke="#0891b2"]');
  await expect(polygonPath).toHaveCount(1);
  const firstPath = await polygonPath.getAttribute("d");

  await input.setInputFiles({ name: "b.geojson", mimeType: "application/geo+json", buffer: Buffer.from(JSON.stringify({ type: "Polygon", coordinates: polygonB })) });
  await expect(page.getByTestId("parcel-upload-filename")).toHaveText("b.geojson");
  await expect(page.getByTestId("parcel-location-consistency")).toContainText("may not match");
  await expect(polygonPath).toHaveCount(1);
  expect(await polygonPath.getAttribute("d")).not.toBe(firstPath);

  await page.getByTestId("remove-parcel-geometry").click();
  await expect(page.getByTestId("parcel-upload-summary")).toHaveCount(0);
  await expect(polygonPath).toHaveCount(0);
  await expect(page.getByTestId("terrain-cadastral-evidence")).toHaveAttribute("data-parcel-status", "point_reference_only");
});

test("invalid upload recovers and KML, SHP ZIP, and unknown CRS use real file inputs", async ({ page }) => {
  await prepare(page); await installUploadFixture(page); await analyze(page);
  const input = page.getByTestId("parcel-geometry-file-input");
  await input.setInputFiles({ name: "invalid.geojson", mimeType: "application/geo+json", buffer: Buffer.from("{bad") });
  await expect(page.getByTestId("parcel-upload-progress")).toContainText("INVALID_GEOMETRY");

  await input.setInputFiles({ name: "parcel.kml", mimeType: "application/vnd.google-earth.kml+xml", buffer: Buffer.from("<kml><Polygon/></kml>") });
  await expect(page.getByTestId("parcel-upload-summary")).toContainText("Polygon");
  await expect(page.getByTestId("parcel-upload-filename")).toHaveText("parcel.kml");

  await input.setInputFiles({ name: "parcel.zip", mimeType: "application/zip", buffer: Buffer.from("PK fixture") });
  await expect(page.getByTestId("parcel-upload-filename")).toHaveText("parcel.zip");
  await expect(page.getByTestId("parcel-upload-summary")).toBeVisible();

  await input.setInputFiles({ name: "unknown.zip", mimeType: "application/zip", buffer: Buffer.from("PK unknown") });
  await expect(page.getByTestId("parcel-upload-progress")).toContainText("UNKNOWN_CRS");
  await expect(page.getByTestId("parcel-upload-summary")).toHaveCount(0);
});

test("latest upload wins, location changes clear geometry, and locale changes do not corrupt state", async ({ page }) => {
  await prepare(page); await installUploadFixture(page, 500); await analyze(page);
  const input = page.getByTestId("parcel-geometry-file-input");
  await input.setInputFiles({ name: "a.geojson", mimeType: "application/geo+json", buffer: Buffer.from("A") });
  await page.locator("select").first().selectOption("ja");
  await expect(page.getByTestId("parcel-upload-progress")).toContainText("ジオメトリ検証");
  await input.setInputFiles({ name: "b.geojson", mimeType: "application/geo+json", buffer: Buffer.from("B") });
  await expect(page.getByTestId("parcel-upload-filename")).toHaveText("b.geojson");
  await expect(page.getByTestId("parcel-upload-summary")).toBeVisible();
  await page.waitForTimeout(550);
  await expect(page.getByTestId("parcel-upload-filename")).toHaveText("b.geojson");
  for (const [locale, readyText] of [["zh-TW", "幾何已載入"], ["en", "Geometry loaded"], ["ja", "ジオメトリを読み込みました"], ["ko", "지오메트리 로드됨"]] as const) {
    await page.locator("select").first().selectOption(locale);
    await expect(page.getByTestId("parcel-upload-progress")).toContainText(readyText);
  }
  await page.locator("select").first().selectOption("en");
  await page.getByRole("textbox", { name: "Property address" }).fill("Different property");
  await expect(page.getByTestId("parcel-upload-summary")).toHaveCount(0);

  await input.setInputFiles({ name: "a.geojson", mimeType: "application/geo+json", buffer: Buffer.from("A") });
  await page.getByTestId("remove-parcel-geometry").click();
  await page.waitForTimeout(550);
  await expect(page.getByTestId("parcel-upload-summary")).toHaveCount(0);
  await expect(page.getByTestId("parcel-upload-filename")).toHaveCount(0);

  await input.setInputFiles({ name: "b.geojson", mimeType: "application/geo+json", buffer: Buffer.from("B") });
  await expect(page.getByTestId("parcel-upload-summary")).toBeVisible();
  await page.locator("aside").getByRole("button", { name: "Valuation", exact: true }).click();
  await page.locator("aside").getByRole("button", { name: "Terrain Risk", exact: true }).click();
  await page.getByTestId("terrain-advanced-settings").locator("summary").click();
  await expect(page.getByTestId("parcel-upload-summary")).toHaveCount(0);
});

test("mobile 390 keeps upload, filename, map, legend, and errors inside viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepare(page); await installUploadFixture(page); await analyze(page);
  await page.getByTestId("parcel-geometry-file-input").setInputFiles({ name: "a-very-long-private-parcel-geometry-filename.geojson", mimeType: "application/geo+json", buffer: Buffer.from("A") });
  await expect(page.getByTestId("parcel-upload-summary")).toBeVisible();
  const metrics = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth, mapWidth: document.querySelector<HTMLElement>('[data-testid="cadastral-map-shell"] .leaflet-container')?.getBoundingClientRect().width ?? 0 }));
  expect(metrics.overflow).toBeLessThanOrEqual(0);
  expect(metrics.mapWidth).toBeGreaterThan(300);
  expect(metrics.mapWidth).toBeLessThanOrEqual(390);
  await expect(page.getByTestId("remove-parcel-geometry")).toBeVisible();
  await expect(page.getByTestId("landsect-semantics")).toBeVisible();
  for (const width of [360, 430]) {
    await page.setViewportSize({ width, height: width === 360 ? 740 : 932 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
  }
});
