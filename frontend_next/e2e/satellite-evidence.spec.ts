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
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.locator(".commercial-methods > summary").click();
  await page.locator(".commercial-methods").getByRole("button", { name: "Terrain Risk", exact: true }).click();
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
    await page.getByRole("button", { name: "Start terrain and hazard check", exact: true }).click();

    const card = page.getByTestId("satellite-evidence-card");
    await expect(card).toBeVisible();
    await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "not_run");
    expect(requestBodies).toEqual([]);
    await page.getByTestId("satellite-request-action").click();
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

test("accepted Satellite mounts, rerenders, locale changes and remounts add zero requests", async ({ page }) => {
  let calls = 0;
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult()) }));
  await page.route("**/terrain/satellite-reference", (route) => {
    calls += 1;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(satelliteResponse("available")) });
  });
  await openTerrain(page);
  await page.locator("#terrain-risk-analysis input").first().fill("Taipei accepted fixture");
  await page.getByRole("button", { name: "Start terrain and hazard check", exact: true }).click();
  await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "not_run");
  for (const locale of ["ja", "ko", "zh-TW", "en"]) await page.getByTestId("locale-switcher").selectOption(locale);
  await expect(page.getByTestId("satellite-request-action")).toBeEnabled();
  expect(calls).toBe(0);
  await page.getByTestId("satellite-request-action").click();
  await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "available");
  await page.getByTestId("locale-switcher").selectOption("ja");
  await page.getByTestId("locale-switcher").selectOption("en");
  expect(calls).toBe(1);
  // A new Terrain result remounts Satellite; remounting itself must remain free.
  await page.getByRole("button", { name: "Start terrain and hazard check", exact: true }).click();
  await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "not_run");
  expect(calls).toBe(1);
});

test("Satellite action synchronously blocks duplicate clicks and ignores stale property A", async ({ page }) => {
  const requests: unknown[] = [];
  let finishA!: () => void;
  const pendingA = new Promise<void>((resolve) => { finishA = resolve; });
  await page.route("**/terrain-risk/analyze", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult()) }));
  await page.route("**/terrain/satellite-reference", async (route) => {
    requests.push(route.request().postDataJSON());
    if (requests.length === 1) await pendingA;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(satelliteResponse("available")) }).catch(() => undefined);
  });
  await openTerrain(page);
  await page.locator("#terrain-risk-analysis input").first().fill("Taipei accepted fixture");
  await page.getByRole("button", { name: "Start terrain and hazard check", exact: true }).click();
  const button = page.getByTestId("satellite-request-action");
  await button.evaluate((node) => { (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click(); });
  await expect.poll(() => requests.length).toBe(1);
  await expect(button).toBeDisabled();
  const propertyB = terrainResult();
  propertyB.resolved_location.latitude = 25.1;
  await page.evaluate((result) => window.dispatchEvent(new CustomEvent("proptech:terrain-risk-result-ready", { detail: result })), propertyB);
  await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "not_run");
  finishA();
  await page.waitForTimeout(100);
  await expect(page.getByTestId("satellite-reference-image")).toHaveCount(0);
  await expect(button).toBeEnabled();
  await button.click();
  await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "available");
  expect(requests).toEqual([{ latitude: 25.0375, longitude: 121.5645 }, { latitude: 25.1, longitude: 121.5645 }]);
});

test("Terrain explicit action suppresses duplicate same-turn provider fan-out", async ({ page }) => {
  let calls = 0;
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => { finish = resolve; });
  await page.route("**/terrain-risk/analyze", async (route) => {
    calls += 1;
    await pending;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(terrainResult()) });
  });
  await openTerrain(page);
  await page.locator("#terrain-risk-analysis input").first().fill("Taipei accepted fixture");
  await page.getByRole("button", { name: "Start terrain and hazard check", exact: true }).evaluate((node) => {
    (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click();
  });
  await expect.poll(() => calls).toBe(1);
  finish();
  await expect(page.getByTestId("satellite-evidence-status")).toHaveAttribute("data-status", "not_run");
});

test("Location explicit action suppresses duplicate same-turn Places fan-out", async ({ page }) => {
  let calls = 0;
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => { finish = resolve; });
  await page.route("**/location/insight", async (route) => {
    calls += 1;
    await pending;
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Fixture unavailable" }) });
  });
  await page.goto("/", { waitUntil: "networkidle" });
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" })));
  await expect(page.locator("#location-insight-calculator")).toBeVisible();
  await page.locator("#location-insight-calculator").getByLabel("Property address", { exact: true }).fill("Accepted fixture address");
  await page.getByRole("button", { name: "Start location analysis", exact: true }).evaluate((node) => {
    (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click();
  });
  await expect.poll(() => calls).toBe(1);
  finish();
  await expect(page.getByRole("button", { name: "Start location analysis", exact: true })).toBeEnabled();
});

test("changed Location radius invalidates in-flight evidence without starting another request", async ({ page }) => {
  let calls = 0;
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => { finish = resolve; });
  await page.route("**/location/insight", async (route) => {
    calls += 1;
    await pending;
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Fixture unavailable" }) });
  });
  await page.goto("/", { waitUntil: "networkidle" });
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" })));
  const calculator = page.locator("#location-insight-calculator");
  await calculator.getByLabel("Property address", { exact: true }).fill("Accepted fixture address");
  await calculator.getByRole("button", { name: "Start location analysis", exact: true }).click();
  await expect.poll(() => calls).toBe(1);
  await calculator.getByLabel("Analysis radius (m)", { exact: true }).fill("1100");
  await expect(calculator.getByRole("button", { name: "Start location analysis", exact: true })).toBeEnabled();
  finish();
  await page.waitForTimeout(100);
  await expect(calculator).not.toContainText("Location data is temporarily unavailable");
  expect(calls).toBe(1);
});

test("external Location property props replace A with B while A is pending", async ({ page }) => {
  let calls = 0;
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => { finish = resolve; });
  const resultA = {
    input: { address: "Property A" }, resolved_location: { address_label: "Property A", latitude: 25.03, longitude: 121.56, geocoding_confidence: "high" },
    radius_m: 800, location_score: 78,
    category_scores: { transit_score: 80, convenience_score: 70, education_score: 60, green_space_score: 50, medical_score: 40, risk_score: 30 },
    poi_summary: { transit_count: 4 }, nearest_pois: [], strengths: [], weaknesses: [], buyer_fit: {},
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "Reference only" },
    data_quality: { status: "good", missing_sources: [], warnings: [] }, scoring_method: { weights: {}, explanation: "Fixture" }, disclaimer: "Reference only",
  };
  await page.route("**/location/insight", async (route) => {
    calls += 1;
    await pending;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(resultA) });
  });
  await page.goto("/", { waitUntil: "networkidle" });
  await page.getByTestId("locale-switcher").selectOption("en");
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" })));
  const input = page.locator("#location-insight-calculator").getByLabel("Property address", { exact: true });
  await input.fill("Property A");
  await input.evaluate((node) => node.setAttribute("data-mounted-instance", "retained"));
  await page.getByRole("button", { name: "Start location analysis", exact: true }).click();
  await expect.poll(() => calls).toBe(1);
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("proptech:guided-demo-result", { detail: {
      inputs: { city: "臺北市", district: "信義區", road: "Property B", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
    } }));
    window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: "location" }));
  });
  await expect(input).toHaveValue("臺北市信義區Property B");
  await expect(input).toHaveAttribute("data-mounted-instance", "retained");
  finish();
  await page.waitForTimeout(100);
  await expect(page.getByTestId("location-result")).toHaveCount(0);
  expect(calls).toBe(1);
});
