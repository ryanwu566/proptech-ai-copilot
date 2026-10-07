import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildLocationOverviewHandoff, buildLocationWorkspaceSnapshot } from "./location-context.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { adaptSavedCaseToWorkspace } from "./legacy-case-adapter.ts";

const CHECKED_AT = "2026-09-27T08:00:00.000Z";

function savedCase(options: { stale?: boolean; routeOrigin?: { latitude: number; longitude: number }; tdxStatus?: "resolved" | "unavailable"; destination?: string } = {}) {
  const stale = options.stale ?? false;
  return {
    id: "location-case",
    title: "市府路案件",
    createdAt: CHECKED_AT,
    updatedAt: CHECKED_AT,
    version: 1 as const,
    workflowMode: "buying_wizard" as const,
    activeWizardStep: "location" as const,
    progress: 60,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號" },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      propertyIdentityAnchor: {
        version: 1 as const,
        scope: "journey_browser_anchor" as const,
        journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
        address_input: "台北市信義區市府路1號",
        normalized_address: "臺北市信義區市府路1號",
        coordinates: { latitude: 25.0375, longitude: 121.5637 },
        administrative_location: { city: "臺北市", district: "信義區", village: "西村里", village_code: "63000020-014" },
        location_status: stale ? "stale" as const : "candidate" as const,
        parcel: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: [], confirmation: null },
        building: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: [], confirmation: null },
        confidence: { level: stale ? "unknown" as const : "high" as const, domain: "address_spatial_correlation" as const, basis: ["normalized_address", "trusted_geocoding_coordinates", "resolved_village"], limitations: [] },
        evidence: {
          sources: [
            { source_id: "google_geocoding", kind: "geocoding" as const, checked_at: CHECKED_AT },
            { source_id: "nlsc_village_boundary", kind: "administrative_boundary" as const, checked_at: CHECKED_AT },
          ],
          checked_at: CHECKED_AT,
          limitations: ["journey_browser_correlation_only"],
        },
        revalidation: stale ? { status: "needs_revalidation" as const, conflicts: ["coordinates" as const] } : { status: "current" as const, conflicts: [] },
      },
      journeyContext: {
        version: 1 as const,
        propertyContext: { city: "臺北市", district: "信義區", road: "市府路1號", addressSummary: "臺北市信義區市府路1號", sourceLabel: "Saved case", selectionStatus: "selected" as const },
        priceBasis: "asking" as const,
      },
      locationInsight: {
        input: {},
        resolved_location: { address_label: "不應覆蓋身分錨點", latitude: 24.1, longitude: 120.1, geocoding_confidence: "high" },
        village_resolution: { status: "resolved" as const, county: "臺北市", town: "信義區", village: "西村里", village_code: "63000020-014", district_code: "63000020", source: "nlsc_village_boundary", source_vintage: "2026-08", reason: "resolved" },
        demographics: { status: "no_data" as const, reason: "not_available" },
        geocoding_acceptance: null,
        radius_m: 800,
        location_score: 88,
        category_scores: { transit_score: 80, convenience_score: 70, education_score: 60, green_space_score: 50, medical_score: 40, risk_score: 30 },
        poi_summary: { transit_count: 4, convenience_count: 8, school_count: 3, park_count: 2, medical_count: 4, risk_facility_count: 1 },
        nearest_pois: [],
        strengths: [], weaknesses: [],
        buyer_fit: { self_use_family: "", commuter: "", investor: "", elderly: "" },
        valuation_context: { supports_price_reasonableness: "unknown" as const, explanation: "" },
        data_quality: { status: "limited" as const, missing_sources: [], warnings: ["POI 明細未隨案件保存"] },
        scoring_method: { weights: {}, explanation: "" },
        disclaimer: "僅供區位參考",
      },
      commuteRoute: options.destination === undefined ? undefined : {
        status: "resolved" as const,
        source: "google_routes" as const,
        mode: "transit" as const,
        duration_min: 23,
        duration_seconds: 1380,
        distance_m: 8100,
        partial: false,
        fallback: false,
        reason_code: "success" as const,
        checked_at: CHECKED_AT,
        origin: options.routeOrigin ?? { latitude: 25.0375, longitude: 121.5637 },
        destination: { address: options.destination },
      },
      commuteTransit: options.tdxStatus ? {
        status: options.tdxStatus,
        source: options.tdxStatus === "resolved" ? "tdx" as const : "none" as const,
        station_name: options.tdxStatus === "resolved" ? "市政府站" : null,
        line_ids: options.tdxStatus === "resolved" ? ["BL"] : [],
        distance_meters: options.tdxStatus === "resolved" ? 420 : null,
        source_updated_at: options.tdxStatus === "resolved" ? "2026-09-01" : null,
        snapshot_generated_at: CHECKED_AT,
        message: options.tdxStatus === "resolved" ? "resolved" : "unavailable",
      } : undefined,
    },
  };
}

test("location snapshot uses the canonical identity coordinate and never a competing saved geocode", () => {
  const snapshot = buildLocationWorkspaceSnapshot(savedCase() as never);

  assert.deepEqual(snapshot.property.coordinates, { latitude: 25.0375, longitude: 121.5637 });
  assert.equal(snapshot.property.normalizedAddress, "臺北市信義區市府路1號");
  assert.deepEqual(snapshot.property.sourceIds, ["google_geocoding", "nlsc_village_boundary"]);
  assert.equal(snapshot.insight?.resolved_location?.latitude, 24.1);
  assert.deepEqual(snapshot.poiSummary, { transit_count: 4, convenience_count: 8, school_count: 3, park_count: 2, medical_count: 4, risk_facility_count: 1 });
});

test("a route from another property is invalidated instead of presented as current", () => {
  const snapshot = buildLocationWorkspaceSnapshot(savedCase({ destination: "台北車站", routeOrigin: { latitude: 24.1, longitude: 120.1 } }) as never);

  assert.equal(snapshot.routeEvidence, undefined);
  assert.equal(snapshot.routeInvalidated, true);
});

test("Google route success remains ready with limits when TDX context is unavailable", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ destination: "台北車站", tdxStatus: "unavailable" }) as never);
  const handoff = buildLocationOverviewHandoff(workspace);

  assert.equal(handoff.commuteReadiness, "ready_with_limits");
  assert.deepEqual(handoff.selectedRoute, { destination: "台北車站", mode: "transit", distanceM: 8100, durationMinutes: 23, checkedAt: CHECKED_AT });
  assert.ok(handoff.unresolved.includes("大眾運輸周邊資料目前無法取得"));
  assert.ok(!handoff.unresolved.includes("目的地路線目前無法取得"));
});

test("mock or fallback routes cannot establish real commute readiness", () => {
  const workspace = adaptSavedCaseToWorkspace(savedCase({ destination: "台北車站", tdxStatus: "resolved" }) as never);
  workspace.location.routeEvidence = { ...workspace.location.routeEvidence!, source: "mock", fallback: true };
  const handoff = buildLocationOverviewHandoff(workspace);

  assert.equal(handoff.commuteReadiness, "not_ready");
  assert.equal(handoff.selectedRoute, undefined);
  assert.match(handoff.unresolved.join(" "), /模擬|備援|部分/);
});

test("missing destination is input-required and stale identity blocks current location evidence", () => {
  const missing = buildLocationOverviewHandoff(adaptSavedCaseToWorkspace(savedCase() as never));
  assert.equal(missing.commuteReadiness, "not_ready");
  assert.ok(missing.unresolved.includes("尚未設定通勤目的地"));

  const stale = buildLocationOverviewHandoff(adaptSavedCaseToWorkspace(savedCase({ stale: true, destination: "台北車站", tdxStatus: "resolved" }) as never));
  assert.equal(stale.commuteReadiness, "blocked");
  assert.equal(stale.mapReady, false);
  assert.equal(stale.selectedRoute, undefined);
  assert.ok(stale.unresolved.includes("物件位置已變更，需重新確認"));
});

test("reopen treats bounded geocoder enrichment as the same browser property", () => {
  const row = savedCase() as never as ReturnType<typeof savedCase>;
  row.data.propertyIdentityAnchor.address_input = "台北市信義區市府路1號";
  row.data.propertyIdentityAnchor.normalized_address = "106台灣臺北市信義區西村里市府路1號";
  row.data.journeyContext.propertyContext.addressSummary = "臺北市信義區市府路1號";
  assert.equal(adaptSavedCaseToWorkspace(row as never).identity.state, "confirmed");
});

test("reopen still requires revalidation for a different house number", () => {
  const row = savedCase() as never as ReturnType<typeof savedCase>;
  row.data.propertyIdentityAnchor.address_input = "台北市信義區市府路1號";
  row.data.propertyIdentityAnchor.normalized_address = "臺北市信義區市府路1號";
  row.data.journeyContext.propertyContext.addressSummary = "臺北市信義區市府路2號";
  assert.equal(adaptSavedCaseToWorkspace(row as never).identity.state, "revalidation_required");
});
