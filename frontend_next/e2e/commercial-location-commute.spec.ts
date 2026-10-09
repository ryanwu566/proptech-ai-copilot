import { expect, test } from "@playwright/test";

const CHECKED_AT = "2026-09-27T08:00:00.000Z";
const STORAGE_KEY = "proptech.savedCases.v1";

test.beforeEach(async ({ page }) => {
  await page.route("https://*.tile.openstreetmap.org/**", (route) => route.fulfill({ status: 204, body: "" }));
});

function savedCase(stale = false) {
  return {
    id: "location-case",
    title: "市府路案件",
    createdAt: CHECKED_AT,
    updatedAt: CHECKED_AT,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "location",
    progress: 60,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號" },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
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
        evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding", checked_at: CHECKED_AT }, { source_id: "nlsc_village_boundary", kind: "administrative_boundary", checked_at: CHECKED_AT }], checked_at: CHECKED_AT, limitations: ["journey_browser_correlation_only"] },
        revalidation: stale ? { status: "needs_revalidation", conflicts: ["coordinates"] } : { status: "current", conflicts: [] },
      },
      journeyContext: { version: 1, propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected" }, priceBasis: "asking" },
      locationInsight: {
        input: {}, resolved_location: { address_label: "臺北市信義區市府路1號", latitude: 25.0375, longitude: 121.5637, geocoding_confidence: "high" },
        village_resolution: { status: "resolved", county: "臺北市", town: "信義區", village: "西村里", village_code: "63000020-014", district_code: "63000020", source: "nlsc_village_boundary", source_vintage: "2026-08", reason: "resolved" },
        demographics: { status: "no_data", reason: "not_available" }, geocoding_acceptance: null, radius_m: 800, location_score: 91,
        category_scores: { transit_score: 80, convenience_score: 70, education_score: 60, green_space_score: 50, medical_score: 40, risk_score: 30 },
        poi_summary: { transit_count: 4, convenience_count: 8, school_count: 3, park_count: 2, medical_count: 4, risk_facility_count: 1 },
        nearest_pois: [{ category: "transit", name: "市政府站", distance_m: 420, source: "google_places" }], strengths: [], weaknesses: [],
        buyer_fit: { self_use_family: "", commuter: "", investor: "", elderly: "" }, valuation_context: { supports_price_reasonableness: "unknown", explanation: "" },
        data_quality: { status: "limited", missing_sources: [], warnings: ["部分地點明細未隨案件保存"] }, scoring_method: { weights: {}, explanation: "" }, disclaimer: "僅供區位參考",
      },
      commuteRoute: { status: "resolved", source: "google_routes", mode: "transit", duration_min: 23, duration_seconds: 1380, distance_m: 8100, partial: false, fallback: false, reason_code: "success", checked_at: CHECKED_AT, origin: { latitude: 25.0375, longitude: 121.5637 }, destination: { address: "台北車站" } },
      commuteTransit: { status: "unavailable", source: "none", station_name: null, line_ids: [], distance_meters: null, source_updated_at: null, snapshot_generated_at: CHECKED_AT, message: "unavailable" },
    },
  };
}

async function seed(page: import("@playwright/test").Page, stale = false) {
  await page.addInitScript(({ key, row }) => {
    if (!window.localStorage.getItem(key)) window.localStorage.setItem(key, JSON.stringify([row]));
  }, { key: STORAGE_KEY, row: savedCase(stale) });
}

test("location workspace leads with the active property map and explainable evidence", async ({ page }) => {
  let providerCalls = 0;
  await page.route(/\/(commute\/(route|address-lookup)|location-insight\/analyze)$/, (route) => { providerCalls += 1; return route.abort(); });
  await seed(page);
  await page.goto("/cases/location-case/location");

  await expect(page.getByRole("heading", { level: 1, name: "區位與通勤" })).toBeVisible();
  const map = page.getByRole("region", { name: "目前物件位置與周邊證據" });
  await expect(map).toContainText("臺北市信義區市府路1號");
  await expect(map).toContainText("25.037500, 121.563700");
  await expect(page.getByRole("heading", { name: "重要周邊證據" })).toBeVisible();
  await expect(page.getByTestId("poi-summary")).toContainText("交通");
  await expect(page.getByTestId("poi-summary")).toContainText("4");
  await expect(page.getByText("位置分數")).toHaveCount(0);

  const route = page.getByTestId("commute-route-card");
  await expect(route.getByLabel("目的地地址")).toHaveValue("台北車站");
  await expect(route).toContainText("約 23 分鐘");
  await expect(route).toContainText("8.1 公里");
  await expect(page.getByText("目的地路線可用；大眾運輸周邊資料目前無法取得。")).toBeVisible();
  await expect(page.getByText("次要里鄰人口背景", { exact: true })).toBeVisible();
  await expect(page.getByText("來源與查詢細節", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("commute-route-card")).toContainText("約 23 分鐘");
  expect(providerCalls).toBe(0);
});

test("route and TDX explicit actions synchronously suppress accidental duplicate submits", async ({ page }) => {
  await seed(page);
  const calls = { routes: 0, tdx: 0 };
  let finish!: () => void;
  const pending = new Promise<void>((resolve) => { finish = resolve; });
  await page.route("**/commute/route", async (route) => {
    calls.routes += 1;
    await pending;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...savedCase().data.commuteRoute, message: "Reference", disclaimer: "Reference only" }) });
  });
  await page.route("**/commute/address-lookup", async (route) => {
    calls.tdx += 1;
    await pending;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(savedCase().data.commuteTransit) });
  });
  await page.goto("/cases/location-case/location");
  await page.getByRole("button", { name: "估算通勤" }).evaluate((node) => { (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click(); });
  await page.getByRole("button", { name: "查看通勤資訊" }).evaluate((node) => { (node as HTMLButtonElement).click(); (node as HTMLButtonElement).click(); });
  await expect.poll(() => calls).toEqual({ routes: 1, tdx: 1 });
  finish();
  await expect(page.getByTestId("commute-route-state")).toHaveAttribute("data-status", "available");
  await expect(page.getByTestId("commute-transit-context-state")).toHaveAttribute("data-status", "unavailable");
});

test("destination changes clear stale route evidence, preserve TDX, and save only the bounded route", async ({ page }) => {
  await seed(page);
  await page.route("**/commute/route", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ status: "resolved", source: "google_routes", mode: "transit", duration_min: 18, duration_seconds: 1080, distance_m: 6200, partial: false, fallback: false, reason_code: "success", checked_at: "2026-09-27T09:00:00.000Z", message: "provider detail", disclaimer: "reference only", raw_provider_payload: { forbidden: true } }),
  }));
  await page.goto("/cases/location-case/location");

  const routeCard = page.getByTestId("commute-route-card");
  await routeCard.getByLabel("目的地地址").fill("松山車站");
  await expect(routeCard).not.toContainText("8.1 公里");
  let stored = await page.evaluate((key) => JSON.parse(window.localStorage.getItem(key) ?? "[]")[0], STORAGE_KEY);
  expect(stored.data.commuteRoute).toBeUndefined();
  expect(stored.data.commuteTransit.status).toBe("unavailable");

  await routeCard.getByRole("button", { name: "估算通勤" }).click();
  await expect(routeCard).toContainText("約 18 分鐘");
  stored = await page.evaluate((key) => JSON.parse(window.localStorage.getItem(key) ?? "[]")[0], STORAGE_KEY);
  expect(stored.data.commuteRoute.destination.address).toBe("松山車站");
  expect(stored.data.commuteRoute.raw_provider_payload).toBeUndefined();
  expect(stored.data.commuteTransit.status).toBe("unavailable");

  await page.reload();
  await expect(page.getByTestId("commute-route-card").getByLabel("目的地地址")).toHaveValue("松山車站");
  await expect(page.getByTestId("commute-route-card")).toContainText("約 18 分鐘");
});

test("TDX unavailability remains explicit and does not clear a valid Google route", async ({ page }) => {
  const seeded = savedCase();
  Reflect.deleteProperty(seeded.data, "commuteTransit");
  const row = seeded;
  await page.addInitScript(({ key, saved }) => window.localStorage.setItem(key, JSON.stringify([saved])), { key: STORAGE_KEY, saved: row });
  await page.route("**/commute/address-lookup", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ status: "unavailable", source: "none", station_name: null, line_ids: [], distance_meters: null, source_updated_at: null, snapshot_generated_at: "2026-09-27T09:30:00.000Z", message: "provider detail must not persist" }),
  }));
  await page.goto("/cases/location-case/location");

  await page.getByRole("button", { name: "查看通勤資訊" }).click();
  await expect(page.getByTestId("commute-transit-context-state")).toHaveAttribute("data-status", "unavailable");
  await expect(page.getByTestId("commute-route-card")).toContainText("約 23 分鐘");
  await expect.poll(() => page.evaluate((key) => JSON.parse(window.localStorage.getItem(key) ?? "[]")[0]?.data?.commuteTransit?.status, STORAGE_KEY)).toBe("unavailable");

  const stored = await page.evaluate((key) => JSON.parse(window.localStorage.getItem(key) ?? "[]")[0], STORAGE_KEY);
  expect(stored.data.commuteTransit.status).toBe("unavailable");
  expect(stored.data.commuteTransit.message).toBe("unavailable");
  expect(stored.data.commuteRoute.destination.address).toBe("台北車站");
});

test("stale identity blocks the map and the 390px workspace has no page overflow", async ({ page }) => {
  await seed(page, true);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/cases/location-case/location");

  await expect(page.getByText("物件位置已變更，需重新確認", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "目前物件位置與周邊證據" })).toHaveCount(0);
  await page.getByText("來源與查詢細節", { exact: true }).click();
  await expect(page.getByText("已選路線：", { exact: false })).toHaveCount(0);
  await expect(page.getByText("物件位置需重新確認", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});
