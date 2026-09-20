import { expect, test } from "./fixtures";

const imageReference = "data:image/jpeg;base64,/9j/2Q==";

function terrainResult() {
  const hazards = Object.fromEntries([
    "landslide",
    "debris_flow",
    "flood",
    "geological_sensitivity",
    "liquefaction",
    "active_fault",
  ].map((key) => [key, {
    key,
    label: key,
    status: "unavailable",
    level: "unknown",
    matched: false,
    distance_m: null,
    value: null,
    explanation: "Unavailable fixture layer.",
    source: { name: key, agency: "fixture", status: "unavailable" },
  }]));
  return {
    input: { address: "Taipei accepted fixture", radius_m: 500, include_layers: ["terrain", ...Object.keys(hazards)] },
    resolved_location: {
      address_label: "Taipei accepted fixture",
      latitude: 25.0375,
      longitude: 121.5645,
      geocoding_confidence: "high",
      geocoding_source: "tgos_geocoding",
    },
    overall: { level: "unknown", label: "Unknown", summary: "Reference data incomplete.", confidence: "unknown" },
    terrain: {
      status: "unavailable",
      slope_value: null,
      slope_class: null,
      elevation_m: null,
      explanation: "Terrain unavailable.",
      source: { name: "fixture terrain", agency: "fixture", status: "unavailable" },
    },
    hazards,
    risk_factors: [],
    missing_sources: ["fixture source"],
    recommended_checks: ["Verify with the responsible authority."],
    map_layers: [],
    source_transparency: { notice: "Reference only.", layers: [] },
    cadastral_evidence: {
      status: "not_configured",
      mode: "point_reference_only",
      provider: "NLSC",
      provider_name: "NLSC",
      center: { lat: 25.0375, lng: 121.5645 },
      raster_status: "not_configured",
      vector_status: "not_configured",
      source_url: "https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH",
      limitation: "POINT_REFERENCE_ONLY",
      checked_at: "2026-09-20T12:00:00Z",
    },
    parcel_geometry_evidence: {
      status: "point_reference_only",
      source: "point_reference",
      geometry_type: "Point",
      centroid: { lat: 25.0375, lng: 121.5645 },
      crs_normalized: "EPSG:4326",
      area_semantics: "not_available",
      legal_boundary: false,
      can_spatial_intersect: false,
      geometry_validity: "VALID",
      limitation: "Point reference only.",
      source_label: "Accepted coordinate",
      checked_at: "2026-09-20T12:00:00Z",
    },
    landsect_context: {
      status: "UNAVAILABLE",
      semantics: "SECTION_CONTEXT_NOT_PARCEL_BOUNDARY",
      source_label: "NLSC",
      source_url: "https://maps.nlsc.gov.tw/",
      limitation: "No parcel boundary.",
    },
    data_quality: { status: "unavailable", warnings: ["Reference data incomplete."], checked_at: "2026-09-20T12:00:00Z" },
    timing_ms: { address_resolution_ms: 1, terrain_provider_ms: 1, slope_provider_ms: 1, flood_provider_ms: 1, geology_provider_ms: 1, total_terrain_ms: 5 },
    disclaimer: "Reference only.",
  };
}

function satelliteResponse(status: "available" | "limited" | "unavailable") {
  return {
    status,
    reason_code: status === "available" ? null : status === "limited" ? "limited_observation_coverage" : "credential_unavailable",
    source: "Sentinel-2 / Copernicus",
    dataset: "COPERNICUS/S2_SR_HARMONIZED",
    window_start: "2026-06-22",
    window_end: "2026-09-20",
    retrieval_time: "2026-09-20T12:00:00Z",
    aoi_radius_m: 500,
    composite_method: "Median satellite reference composite using Sentinel-2 B4/B3/B2 across the fixed 90-day window.",
    cloud_filter_percent: 35,
    image_reference: status === "unavailable" ? null : imageReference,
    attribution: "Contains modified Copernicus Sentinel data processed by Google Earth Engine.",
    limitations: [
      "Cloud filtering and masking may leave residual cloud, haze, or incomplete coverage.",
      "The fixed 500 m radius context area is not a parcel boundary.",
    ],
    disclaimer: "Satellite reference imagery — not cadastral or statutory evidence.",
  };
}

async function openTerrain(page: import("@playwright/test").Page) {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.locator("aside").getByRole("button", { name: "Terrain Risk", exact: true }).click();
  await expect(page.locator("#terrain-risk-analysis")).toBeVisible();
}

test("satellite endpoint is not called before terrain returns an accepted coordinate", async ({ page }) => {
  let satelliteCalls = 0;
  await page.route("**/terrain/satellite-reference", (route) => {
    satelliteCalls += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(satelliteResponse("available")) });
  });
  await openTerrain(page);

  const card = page.getByTestId("satellite-evidence-card");
  await expect(card).toBeVisible();
  await expect(page.getByTestId("satellite-evidence-status")).toContainText("Confirmation required");
  await page.locator("#terrain-risk-analysis input").first().fill("raw, unconfirmed address");
  await page.waitForTimeout(100);

  expect(satelliteCalls).toBe(0);
  await expect(card).toContainText("Satellite reference imagery — not cadastral or statutory evidence.");
});

for (const status of ["available", "limited", "unavailable"] as const) {
  test(`satellite evidence renders the ${status} state from the accepted terrain coordinate`, async ({ page }) => {
    const requestBodies: unknown[] = [];
    await page.route("**/terrain-risk/analyze", (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(terrainResult()),
    }));
    await page.route("**/terrain/satellite-reference", async (route) => {
      requestBodies.push(route.request().postDataJSON());
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(satelliteResponse(status)),
      });
    });
    await openTerrain(page);
    await page.locator("#terrain-risk-analysis input").first().fill("Taipei accepted fixture");
    await page.getByRole("button", { name: "開始地勢／災害檢查" }).click();

    const card = page.getByTestId("satellite-evidence-card");
    await expect(card).toBeVisible();
    await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", status);
    await expect(card).toContainText("Sentinel-2 / Copernicus");
    await expect(card).toContainText("COPERNICUS/S2_SR_HARMONIZED");
    await expect(card).toContainText("2026-06-22 — 2026-09-20");
    await expect(card).toContainText("Median satellite reference composite");
    await expect(card).toContainText("2026-09-20T12:00:00Z");
    await expect(card.locator("dt").filter({ hasText: status === "unavailable" ? "Checked" : "Retrieved" })).toHaveCount(1);
    await expect(card).toContainText("Cloud filtering and masking may leave residual cloud, haze, or incomplete coverage.");
    await expect(card).toContainText("Satellite reference imagery — not cadastral or statutory evidence.");
    await expect(page.getByTestId("satellite-reference-image")).toHaveCount(status === "unavailable" ? 0 : 1);
    expect(requestBodies).toEqual([{ latitude: 25.0375, longitude: 121.5645 }]);
    const visibleCopy = (await card.innerText()).toLowerCase();
    for (const forbidden of ["ownership confirmed", "zoning confirmed", "legal boundary verified", "disaster certified", "building permit evidence"]) {
      expect(visibleCopy).not.toContain(forbidden);
    }
  });
}
