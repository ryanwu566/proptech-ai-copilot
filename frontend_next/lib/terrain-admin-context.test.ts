import assert from "node:assert/strict";
import test from "node:test";

import type { LocationInsightResult } from "./api.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { acceptedTerrainAdministrativeContext } from "./terrain-admin-context.ts";

function location(accepted: boolean): LocationInsightResult {
  return {
    input: { city: "偽造市", district: "偽造區" },
    resolved_location: { address_label: "106台灣臺北市大安區群賢里敦化南路二段100號", latitude: 25.026, longitude: 121.548, geocoding_confidence: "high" },
    geocoding_acceptance: { accepted_for_analysis: accepted, normalized_address: "臺北市大安區敦化南路二段100號", geocoding_source: "google_geocoding" } as LocationInsightResult["geocoding_acceptance"],
    village_resolution: { status: "resolved", county: "臺北市", town: "大安區", village: "群賢里", village_code: "63000030-010", source: "nlsc_village_boundary" } as LocationInsightResult["village_resolution"],
    radius_m: 500, location_score: null,
    category_scores: { transit_score: 0, convenience_score: 0, education_score: 0, green_space_score: 0, medical_score: 0, risk_score: 0 },
    poi_summary: { transit_count: 0, convenience_count: 0, school_count: 0, park_count: 0, medical_count: 0, risk_facility_count: 0 },
    nearest_pois: [], strengths: [], weaknesses: [], buyer_fit: { self_use_family: "", commuter: "", investor: "", elderly: "" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "" }, data_quality: { status: "limited", missing_sources: [], warnings: [] }, scoring_method: { weights: {}, explanation: "" }, disclaimer: "",
  };
}

test("Terrain receives bounded administration from accepted Location evidence", () => {
  assert.deepEqual(acceptedTerrainAdministrativeContext(location(true)), { city: "臺北市", district: "大安區" });
});

test("Terrain does not reuse administrative text from an unaccepted Location result", () => {
  assert.deepEqual(acceptedTerrainAdministrativeContext(location(false)), {});
});
