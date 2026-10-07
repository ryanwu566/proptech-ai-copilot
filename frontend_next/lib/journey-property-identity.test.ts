import assert from "node:assert/strict";
import test from "node:test";

import type { LocationInsightResult } from "./api.ts";
import type { JourneyPropertyContext } from "./location-market-journey.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { areJourneyPropertyAddressesEquivalent, buildJourneyPropertyIdentityAnchor, reconcileJourneyPropertyIdentityAnchor } from "./journey-property-identity.ts";

const context: JourneyPropertyContext = {
  city: "台北市",
  district: "大安區",
  road: "敦化南路二段",
  addressSummary: "台北市大安區敦化南路二段100號",
  sourceLabel: "test",
  selectionStatus: "selected",
};

function location(address: string, latitude = 25.026, longitude = 121.548, villageCode = "63000030-010"): LocationInsightResult {
  return {
    input: { city: "台北市", district: "大安區", road: "敦化南路二段", address: context.addressSummary! },
    resolved_location: { address_label: address, latitude, longitude, geocoding_confidence: "high" },
    geocoding_acceptance: { accepted_for_analysis: true, normalized_address: address, geocoding_source: "google_geocoding" } as LocationInsightResult["geocoding_acceptance"],
    village_resolution: { status: "resolved", county: "臺北市", town: "大安區", village: "群賢里", village_code: villageCode, source: "nlsc_village_boundary" } as LocationInsightResult["village_resolution"],
    radius_m: 500,
    location_score: null,
    category_scores: { transit_score: 0, convenience_score: 0, education_score: 0, green_space_score: 0, medical_score: 0, risk_score: 0 },
    poi_summary: { transit_count: 0, convenience_count: 0, school_count: 0, park_count: 0, medical_count: 0, risk_facility_count: 0 },
    nearest_pois: [], strengths: [], weaknesses: [],
    buyer_fit: { self_use_family: "", commuter: "", investor: "", elderly: "" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "" },
    data_quality: { status: "limited", missing_sources: [], warnings: [] },
    scoring_method: { weights: {}, explanation: "" }, disclaimer: "",
  };
}

test("Taiwan address equivalence tolerates only bounded administrative enrichment", () => {
  const base = "台北市大安區敦化南路二段100號";
  for (const enriched of [
    "106臺北市大安區敦化南路二段100號",
    "臺北市大安區敦化南路二段100號",
    "台灣臺北市大安區敦化南路二段100號",
    "106台灣臺北市大安區群賢里敦化南路二段100號",
  ]) assert.equal(areJourneyPropertyAddressesEquivalent(base, enriched), true, enriched);
});

test("Taiwan address equivalence rejects meaningful disagreement", () => {
  assert.equal(areJourneyPropertyAddressesEquivalent("台北市大安區敦化南路二段100號", "臺北市大安區敦化南路二段102號"), false);
  assert.equal(areJourneyPropertyAddressesEquivalent("台北市大安區敦化南路二段100號", "臺北市大安區和平東路二段100號"), false);
  assert.equal(areJourneyPropertyAddressesEquivalent("台北市大安區敦化南路二段100號", "新北市板橋區敦化南路二段100號"), false);
  assert.equal(areJourneyPropertyAddressesEquivalent("台北市大安區敦化南路二段100-1號", "台北市大安區敦化南路二段1001號"), false);
});

test("harmless geocoder enrichment does not require revalidation", () => {
  const initial = buildJourneyPropertyIdentityAnchor({ context, location: location(context.addressSummary!) }, { now: () => "2026-10-07T00:00:00.000Z", idFactory: () => "11111111-1111-4111-8111-111111111111" });
  const reconciled = reconcileJourneyPropertyIdentityAnchor(initial, context, location("106台灣臺北市大安區群賢里敦化南路二段100號"), { now: () => "2026-10-07T00:01:00.000Z" });
  assert.equal(reconciled.revalidation.status, "current");
  assert.deepEqual(reconciled.revalidation.conflicts, []);
});

test("coordinate and village-code conflicts remain independent safeguards", () => {
  const initial = buildJourneyPropertyIdentityAnchor({ context, location: location(context.addressSummary!) }, { now: () => "2026-10-07T00:00:00.000Z", idFactory: () => "11111111-1111-4111-8111-111111111111" });
  const coordinateConflict = reconcileJourneyPropertyIdentityAnchor(initial, context, location("106台灣臺北市大安區群賢里敦化南路二段100號", 25.03, 121.55));
  assert.deepEqual(coordinateConflict.revalidation.conflicts, ["coordinates"]);
  const villageConflict = reconcileJourneyPropertyIdentityAnchor(initial, context, location("106台灣臺北市大安區群賢里敦化南路二段100號", 25.026, 121.548, "63000030-999"));
  assert.deepEqual(villageConflict.revalidation.conflicts, ["village_code"]);
});
