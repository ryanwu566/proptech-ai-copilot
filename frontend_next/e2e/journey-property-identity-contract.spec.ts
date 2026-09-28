import { expect, test } from "@playwright/test";
import type { LocationInsightResult } from "../lib/api";
import type { JourneyPropertyContext } from "../lib/location-market-journey";
import {
  createClosedLoopJourneyState,
  restoreJourneyLocationResult,
  setJourneyLocationResult,
  updateJourneyMarketLocation,
  updateJourneyProperty,
} from "../lib/closed-loop-journey";
import {
  readSavedCases,
  saveCase,
  SAVED_CASES_STORAGE_KEY,
  type SaveCaseInput,
} from "../lib/case-storage";
import {
  buildJourneyPropertyIdentityAnchor,
  normalizeJourneyPropertyIdentityAnchor,
  reconcileJourneyPropertyIdentityAnchor,
} from "../lib/journey-property-identity";

const CHECKED_AT = "2026-09-27T08:00:00.000Z";
const OPAQUE_UUID = "11111111-2222-4333-8444-555555555555";

const context: JourneyPropertyContext = {
  city: "臺北市",
  district: "信義區",
  road: "市府路1號",
  addressSummary: "臺北市信義區市府路1號",
  sourceLabel: "Property selection",
  selectionStatus: "selected",
};

function locationResult(overrides: Partial<LocationInsightResult> = {}): LocationInsightResult {
  return {
    input: {
      city: "臺北市",
      district: "信義區",
      road: "市府路1號",
      address: "臺北市信義區市府路1號",
      latitude: null,
      longitude: null,
      radius_m: 800,
      property_price_wan: null,
      area_ping: null,
      building_type: "",
      use_existing_poi_sources: true,
    },
    resolved_location: {
      address_label: "臺北市信義區市府路1號",
      latitude: 25.0375,
      longitude: 121.5637,
      geocoding_confidence: "high",
    },
    village_resolution: {
      status: "resolved",
      county: "臺北市",
      town: "信義區",
      village: "西村里",
      village_code: "63000020-014",
      district_code: "63000020-014",
      source: "nlsc_village_boundary",
      source_vintage: "2026-08",
      reason: "",
      candidate_count: 1,
    },
    demographics: { status: "no_data", reason: "not_requested" },
    geocoding_acceptance: {
      original_query: "臺北市信義區市府路1號",
      normalized_address: "臺北市信義區市府路1號",
      resolved_lat: 25.0375,
      resolved_lng: 121.5637,
      geocoding_source: "google_geocoding",
      match_quality: "EXACT_OR_ACCEPTABLE",
      accepted_for_analysis: true,
      requires_confirmation: false,
      mismatch_reasons: [],
      message: "accepted",
    },
    radius_m: 800,
    location_score: null,
    category_scores: {
      transit_score: 0,
      convenience_score: 0,
      education_score: 0,
      green_space_score: 0,
      medical_score: 0,
      risk_score: 50,
    },
    poi_summary: {
      transit_count: 0,
      convenience_count: 0,
      school_count: 0,
      park_count: 0,
      medical_count: 0,
      risk_facility_count: 0,
    },
    nearest_pois: [],
    strengths: [],
    weaknesses: [],
    buyer_fit: {
      self_use_family: "資料不足",
      commuter: "資料不足",
      investor: "資料不足",
      elderly: "資料不足",
    },
    valuation_context: {
      supports_price_reasonableness: "unknown",
      explanation: "not assessed",
    },
    data_quality: { status: "limited", missing_sources: [], warnings: [] },
    scoring_method: { weights: {}, explanation: "not used by identity" },
    disclaimer: "location reference only",
    ...overrides,
  };
}

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() { return values.size; },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => { values.delete(key); },
    setItem: (key, value) => { values.set(key, String(value)); },
  };
}

function withBrowserStorage<T>(run: (localStorage: Storage) => T): T {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  const localStorage = memoryStorage();
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { localStorage, sessionStorage: memoryStorage(), dispatchEvent: () => true },
  });
  try {
    return run(localStorage);
  } finally {
    if (previous) Object.defineProperty(globalThis, "window", previous);
    else Reflect.deleteProperty(globalThis, "window");
  }
}

function saveInput(anchor: ReturnType<typeof buildJourneyPropertyIdentityAnchor>): SaveCaseInput {
  return {
    title: "市府路案件",
    activeWizardStep: "report",
    progress: 80,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號" },
    data: {
      inputs: {
        city: "臺北市",
        district: "信義區",
        road: "市府路1號",
        building_type: "住宅大樓",
        area_ping: 30,
        building_age_years: 5,
        floor: 8,
      },
      propertyIdentityAnchor: anchor,
      journeyContext: {
        version: 1,
        propertyContext: context,
        priceBasis: "asking",
      },
    },
  };
}

test("address selection creates an opaque browser anchor without parcel or building claims", () => {
  const anchor = buildJourneyPropertyIdentityAnchor(
    { context },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  expect(anchor.scope).toBe("journey_browser_anchor");
  expect(anchor.version).toBe(1);
  expect(anchor.journey_anchor_id).toBe(`journey-browser-${OPAQUE_UUID}`);
  expect(anchor.journey_anchor_id).not.toContain(context.addressSummary);
  expect(anchor.address_input).toBe("臺北市信義區市府路1號");
  expect(anchor.normalized_address).toBe("臺北市信義區市府路1號");
  expect(anchor.location_status).toBe("candidate");
  expect(anchor.coordinates).toBeNull();
  expect(anchor.parcel).toMatchObject({ status: "unavailable", candidates: [], confidence: "unknown" });
  expect(anchor.building).toMatchObject({ status: "unavailable", candidates: [], confidence: "unknown" });
  expect(anchor.confidence).toMatchObject({ level: "low", domain: "address_spatial_correlation" });
  expect(anchor.confidence.limitations).toContain("not_parcel_building_ownership_or_legal_boundary_confirmation");
  expect(anchor.evidence.sources).toEqual([{ source_id: "property_selection", kind: "user_selection", checked_at: CHECKED_AT }]);
  expect(anchor.revalidation).toEqual({ status: "current", conflicts: [] });
});

test("trusted geocoding plus resolved NLSC village raises only address-level confidence", () => {
  const anchor = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  expect(anchor.journey_anchor_id).toBe(`journey-browser-${OPAQUE_UUID}`);
  expect(anchor.journey_anchor_id).not.toContain("25.0375");
  expect(anchor.journey_anchor_id).not.toContain("63000020-014");
  expect(anchor.normalized_address).toBe("臺北市信義區市府路1號");
  expect(anchor.coordinates).toEqual({ latitude: 25.0375, longitude: 121.5637 });
  expect(anchor.administrative_location).toEqual({
    city: "臺北市",
    district: "信義區",
    village: "西村里",
    village_code: "63000020-014",
  });
  expect(anchor.location_status).toBe("candidate");
  expect(anchor.confidence).toMatchObject({
    level: "high",
    domain: "address_spatial_correlation",
    basis: ["normalized_address", "trusted_geocoding_coordinates", "administrative_area", "resolved_village"],
  });
  expect(anchor.evidence.sources).toEqual([
    { source_id: "property_selection", kind: "user_selection", checked_at: CHECKED_AT },
    { source_id: "google_geocoding", kind: "geocoding", checked_at: CHECKED_AT },
    { source_id: "nlsc_village_boundary", kind: "administrative_boundary", checked_at: CHECKED_AT },
  ]);
  expect(anchor.parcel.status).toBe("unavailable");
  expect(anchor.building.status).toBe("unavailable");
});

test("trusted resolved coordinates without a village produce medium address confidence", () => {
  const anchor = buildJourneyPropertyIdentityAnchor(
    {
      context,
      location: locationResult({
        village_resolution: {
          status: "unavailable",
          county: null,
          town: null,
          village: null,
          village_code: null,
          district_code: null,
          source: "nlsc_village_boundary",
          source_vintage: null,
          reason: "artifact_not_configured",
        },
      }),
    },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  expect(anchor.confidence.level).toBe("medium");
  expect(anchor.confidence.basis).toContain("trusted_geocoding_coordinates");
  expect(anchor.administrative_location.village).toBeNull();
  expect(anchor.evidence.sources.map((source) => source.source_id)).not.toContain("nlsc_village_boundary");
  expect(anchor.parcel.status).toBe("unavailable");
  expect(anchor.building.status).toBe("unavailable");
});

test("accepted non-provider point evidence is not described as trusted geocoding", () => {
  const provided = locationResult({
    geocoding_acceptance: {
      ...locationResult().geocoding_acceptance!,
      geocoding_source: "provided_coordinates",
    },
    village_resolution: {
      ...locationResult().village_resolution!,
      status: "unavailable",
      village: null,
      village_code: null,
    },
  });
  const anchor = buildJourneyPropertyIdentityAnchor(
    { context, location: provided },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  expect(anchor.confidence.level).toBe("medium");
  expect(anchor.confidence.basis).toContain("accepted_coordinates");
  expect(anchor.confidence.basis).not.toContain("trusted_geocoding_coordinates");
});

test("saved anchor normalization accepts the bounded contract and rejects property-derived or malformed IDs", () => {
  const anchor = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  expect(normalizeJourneyPropertyIdentityAnchor(JSON.parse(JSON.stringify(anchor)))).toEqual(anchor);
  expect(normalizeJourneyPropertyIdentityAnchor({ ...anchor, version: 2 })).toBeNull();
  expect(normalizeJourneyPropertyIdentityAnchor({ ...anchor, journey_anchor_id: `journey-browser-${context.addressSummary}` })).toBeNull();
  expect(normalizeJourneyPropertyIdentityAnchor({ ...anchor, evidence: { ...anchor.evidence, sources: [{ raw_payload: "forbidden" }] } })).toBeNull();
  expect(normalizeJourneyPropertyIdentityAnchor({
    ...anchor,
    evidence: {
      ...anchor.evidence,
      sources: anchor.evidence.sources.filter((source) => source.kind !== "geocoding"),
    },
  })).toBeNull();
  expect(normalizeJourneyPropertyIdentityAnchor({
    ...anchor,
    parcel: {
      ...anchor.parcel,
      status: "manual_confirmed",
      candidate_id: "parcel-candidate-1",
      source_id: "manual_confirmation",
      confirmation: {
        status: "manual_confirmed",
        method: "manual",
        confirmed_at: CHECKED_AT,
        source_candidate_id: "parcel-candidate-1",
      },
    },
  })).toBeNull();
});

test("formatting-only address and provider precision changes reconcile the same anchor", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const formattedStored = { ...stored, normalized_address: "臺北市 信義區　市府路1號" };
  const fresh = locationResult({
    resolved_location: {
      address_label: "臺北市信義區市府路1號",
      latitude: 25.0378,
      longitude: 121.5637,
      geocoding_confidence: "high",
    },
    geocoding_acceptance: {
      ...locationResult().geocoding_acceptance!,
      resolved_lat: 25.0378,
      resolved_lng: 121.5637,
    },
  });

  const reconciled = reconcileJourneyPropertyIdentityAnchor(formattedStored, context, fresh, {
    now: () => "2026-09-27T09:00:00.000Z",
  });

  expect(reconciled.journey_anchor_id).toBe(stored.journey_anchor_id);
  expect(reconciled.revalidation).toEqual({ status: "current", conflicts: [] });
  expect(reconciled.coordinates).toEqual({ latitude: 25.0378, longitude: 121.5637 });
  expect(reconciled.confidence.level).toBe("high");
});

test("nearby coordinates cannot reconcile an anchor without comparable accepted address evidence", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const coordinateOnly = locationResult({
    resolved_location: {
      address_label: "",
      latitude: 25.0376,
      longitude: 121.5637,
      geocoding_confidence: "provided_coordinates",
    },
    geocoding_acceptance: null,
  });
  const contextWithoutIdentity: JourneyPropertyContext = {
    sourceLabel: "Coordinates only",
    selectionStatus: "not_selected",
  };

  const reconciled = reconcileJourneyPropertyIdentityAnchor(stored, contextWithoutIdentity, coordinateOnly, {
    now: () => "2026-09-27T09:00:00.000Z",
  });

  expect(reconciled.journey_anchor_id).toBe(stored.journey_anchor_id);
  expect(reconciled.revalidation).toEqual({ status: "needs_revalidation", conflicts: ["incomparable_identity"] });
  expect(reconciled.location_status).toBe("stale");
  expect(reconciled.confidence.level).toBe("unknown");
  expect(reconciled.coordinates).toEqual(stored.coordinates);
  expect(reconciled.evidence.sources).toEqual(stored.evidence.sources);
});

test("material coordinate disagreement requires revalidation even when the address agrees", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const farLocation = locationResult({
    resolved_location: {
      address_label: "臺北市信義區市府路1號",
      latitude: 25.0395,
      longitude: 121.5637,
      geocoding_confidence: "high",
    },
    geocoding_acceptance: {
      ...locationResult().geocoding_acceptance!,
      resolved_lat: 25.0395,
      resolved_lng: 121.5637,
    },
  });

  const reconciled = reconcileJourneyPropertyIdentityAnchor(stored, context, farLocation, {
    now: () => "2026-09-27T09:00:00.000Z",
  });

  expect(reconciled.revalidation).toEqual({ status: "needs_revalidation", conflicts: ["coordinates"] });
  expect(reconciled.location_status).toBe("stale");
  expect(reconciled.confidence.level).toBe("unknown");
  expect(reconciled.coordinates).toEqual(stored.coordinates);
});

test("address or village conflict forces revalidation even when coordinates are close", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const conflictingAddress = locationResult({
    resolved_location: {
      address_label: "臺北市信義區松高路10號",
      latitude: 25.0376,
      longitude: 121.5637,
      geocoding_confidence: "high",
    },
    geocoding_acceptance: {
      ...locationResult().geocoding_acceptance!,
      original_query: "臺北市信義區松高路10號",
      normalized_address: "臺北市信義區松高路10號",
      resolved_lat: 25.0376,
      resolved_lng: 121.5637,
    },
  });
  const addressResult = reconcileJourneyPropertyIdentityAnchor(stored, context, conflictingAddress, {
    now: () => "2026-09-27T09:00:00.000Z",
  });
  expect(addressResult.revalidation.conflicts).toContain("normalized_address");
  expect(addressResult.revalidation.status).toBe("needs_revalidation");

  const conflictingVillage = locationResult({
    village_resolution: {
      ...locationResult().village_resolution!,
      village: "興雅里",
      village_code: "63000020-015",
      district_code: "63000020-015",
    },
  });
  const villageResult = reconcileJourneyPropertyIdentityAnchor(stored, context, conflictingVillage, {
    now: () => "2026-09-27T09:00:00.000Z",
  });
  expect(villageResult.revalidation.conflicts).toContain("village_code");
  expect(villageResult.revalidation.status).toBe("needs_revalidation");
});

test("address and village conflicts force revalidation when fresh coordinates are unavailable", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const conflictingAddress = locationResult({
    resolved_location: null,
    geocoding_acceptance: {
      ...locationResult().geocoding_acceptance!,
      normalized_address: "Different nearby building",
    },
  });
  const addressResult = reconcileJourneyPropertyIdentityAnchor(stored, context, conflictingAddress);
  expect(addressResult.revalidation).toEqual({ status: "needs_revalidation", conflicts: ["normalized_address"] });

  const conflictingVillage = locationResult({
    resolved_location: null,
    village_resolution: {
      ...locationResult().village_resolution!,
      village_code: "63000020-015",
      district_code: "63000020-015",
    },
  });
  const villageResult = reconcileJourneyPropertyIdentityAnchor(stored, context, conflictingVillage);
  expect(villageResult.revalidation).toEqual({ status: "needs_revalidation", conflicts: ["village_code"] });
});

test("unavailable fresh village evidence preserves the stored village without inventing a conflict", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const unavailableVillage = locationResult({
    village_resolution: {
      status: "unavailable",
      county: null,
      town: null,
      village: null,
      village_code: null,
      district_code: null,
      source: "nlsc_village_boundary",
      source_vintage: null,
      reason: "runtime_unavailable",
    },
  });

  const reconciled = reconcileJourneyPropertyIdentityAnchor(stored, context, unavailableVillage, {
    now: () => "2026-09-27T09:00:00.000Z",
  });

  expect(reconciled.revalidation).toEqual({ status: "current", conflicts: [] });
  expect(reconciled.administrative_location.village).toBe("西村里");
  expect(reconciled.administrative_location.village_code).toBe("63000020-014");
});

test("journey selection creates and enriches one browser anchor", () => {
  const selected = updateJourneyProperty(createClosedLoopJourneyState(), context, {
    now: () => CHECKED_AT,
    idFactory: () => OPAQUE_UUID,
  });

  expect(selected.identityAnchor?.journey_anchor_id).toBe(`journey-browser-${OPAQUE_UUID}`);
  expect(selected.identityAnchor?.confidence.level).toBe("low");

  const enriched = setJourneyLocationResult(selected, locationResult(), "available", {
    now: () => "2026-09-27T09:00:00.000Z",
  });

  expect(enriched.identityAnchor?.journey_anchor_id).toBe(selected.identityAnchor?.journey_anchor_id);
  expect(enriched.identityAnchor?.confidence.level).toBe("high");
  expect(enriched.identityAnchor?.administrative_location.village_code).toBe("63000020-014");
});

test("changing property identity replaces the anchor and clears all Address A evidence", () => {
  const selected = updateJourneyProperty(createClosedLoopJourneyState(), context, {
    now: () => CHECKED_AT,
    idFactory: () => OPAQUE_UUID,
  });
  const addressA = {
    ...setJourneyLocationResult(selected, locationResult(), "available", { now: () => CHECKED_AT }),
    propertySearchResult: { search_status: "available" } as never,
    terrainResult: { overall: { level: "low" } } as never,
    terrainReference: { status: "available" } as never,
    storedTerrainReference: { version: 1 } as never,
    marketResult: { data_status: "available" } as never,
    valuationResult: { price_range: { mid: 2_000 } } as never,
    loanResult: { monthly_payment: 50_000 } as never,
    holdingResult: { monthly_total_holding_cost: 60_000 } as never,
    taxResult: { eligibility_status: "manual_review" } as never,
  };

  const addressB = updateJourneyProperty(addressA, {
    city: "臺北市",
    district: "大安區",
    road: "仁愛路四段1號",
    addressSummary: "臺北市大安區仁愛路四段1號",
    sourceLabel: "Property selection",
    selectionStatus: "selected",
  }, {
    now: () => "2026-09-27T10:00:00.000Z",
    idFactory: () => "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
  });

  expect(addressB.identityAnchor?.journey_anchor_id).toBe("journey-browser-aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee");
  expect(addressB.identityAnchor?.journey_anchor_id).not.toBe(addressA.identityAnchor?.journey_anchor_id);
  expect(addressB.identityAnchor?.address_input).toBe("臺北市大安區仁愛路四段1號");
  expect(addressB.propertySearchResult).toBeUndefined();
  expect(addressB.locationResult).toBeUndefined();
  expect(addressB.terrainResult).toBeUndefined();
  expect(addressB.terrainReference).toBeUndefined();
  expect(addressB.storedTerrainReference).toBeUndefined();
  expect(addressB.marketResult).toBeUndefined();
  expect(addressB.valuationResult).toBeUndefined();
  expect(addressB.loanResult).toBeUndefined();
  expect(addressB.holdingResult).toBeUndefined();
  expect(addressB.taxResult).toBeUndefined();
});

test("first accepted geocoding enriches an anchor across equivalent Taiwan character variants", () => {
  const initialContext: JourneyPropertyContext = {
    city: "\u53f0\u5317\u5e02",
    district: "\u4fe1\u7fa9\u5340",
    road: "\u5e02\u5e9c\u8def1\u865f",
    addressSummary: "\u53f0\u5317\u5e02\u4fe1\u7fa9\u5340\u5e02\u5e9c\u8def1\u865f",
    sourceLabel: "Property selection",
    selectionStatus: "selected",
  };
  const stored = buildJourneyPropertyIdentityAnchor(
    { context: initialContext },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const accepted = locationResult({
    resolved_location: {
      address_label: "\u81fa\u5317\u5e02\u4fe1\u7fa9\u5340\u5e02\u5e9c\u8def1\u865f",
      latitude: 25.0375,
      longitude: 121.5637,
      geocoding_confidence: "high",
    },
    geocoding_acceptance: {
      ...locationResult().geocoding_acceptance!,
      original_query: initialContext.addressSummary!,
      normalized_address: "\u81fa\u5317\u5e02\u4fe1\u7fa9\u5340\u5e02\u5e9c\u8def1\u865f",
    },
  });

  const reconciled = reconcileJourneyPropertyIdentityAnchor(stored, initialContext, accepted, {
    now: () => "2026-09-27T09:00:00.000Z",
  });

  expect(reconciled.journey_anchor_id).toBe(stored.journey_anchor_id);
  expect(reconciled.revalidation).toEqual({ status: "current", conflicts: [] });
  expect(reconciled.coordinates).toEqual({ latitude: 25.0375, longitude: 121.5637 });
  expect(reconciled.normalized_address).toBe("\u81fa\u5317\u5e02\u4fe1\u7fa9\u5340\u5e02\u5e9c\u8def1\u865f");
});

test("market-driven address changes replace the anchor and clear property-bound evidence", () => {
  const addressA = {
    ...createClosedLoopJourneyState(context, {
      now: () => CHECKED_AT,
      idFactory: () => OPAQUE_UUID,
    }),
    propertySearchResult: { search_status: "available" } as never,
    commuteRouteEvidence: { status: "resolved" } as never,
    commuteRouteStatus: "available" as const,
  };

  const addressB = updateJourneyMarketLocation(addressA, {
    city: "Taipei",
    district: "Daan",
    road: "Renai Road 1",
  });

  expect(addressB.identityAnchor?.journey_anchor_id).not.toBe(addressA.identityAnchor?.journey_anchor_id);
  expect(addressB.identityAnchor?.address_input).toBe("TaipeiDaanRenai Road 1");
  expect(addressB.propertySearchResult).toBeUndefined();
  expect(addressB.commuteRouteEvidence).toBeUndefined();
  expect(addressB.commuteRouteStatus).toBe("not_started");
});

test("non-location valuation edits retain identity and location evidence", () => {
  const selected = updateJourneyProperty(createClosedLoopJourneyState(), context, {
    now: () => CHECKED_AT,
    idFactory: () => OPAQUE_UUID,
  });
  const enriched = {
    ...setJourneyLocationResult(selected, locationResult(), "available", { now: () => CHECKED_AT }),
    marketResult: { data_status: "available" } as never,
    valuationResult: { price_range: { mid: 2_000 } } as never,
    loanResult: { monthly_payment: 50_000 } as never,
  };

  const edited = updateJourneyProperty(enriched, { buildingType: "住宅大樓" }, {
    now: () => "2026-09-27T10:00:00.000Z",
    idFactory: () => "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
  });

  expect(edited.identityAnchor).toEqual(enriched.identityAnchor);
  expect(edited.locationResult).toEqual(enriched.locationResult);
  expect(edited.marketResult).toEqual(enriched.marketResult);
  expect(edited.valuationResult).toBeUndefined();
  expect(edited.loanResult).toBeUndefined();
});

test("fresh conflicting location marks a reopened anchor stale without overwriting stored provenance", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const reopened = { ...createClosedLoopJourneyState(context), identityAnchor: stored };
  const conflicting = locationResult({
    geocoding_acceptance: {
      ...locationResult().geocoding_acceptance!,
      original_query: "臺北市信義區松高路10號",
      normalized_address: "臺北市信義區松高路10號",
    },
    resolved_location: {
      address_label: "臺北市信義區松高路10號",
      latitude: 25.0376,
      longitude: 121.5637,
      geocoding_confidence: "high",
    },
  });

  const state = setJourneyLocationResult(reopened, conflicting, "available", {
    now: () => "2026-09-27T10:00:00.000Z",
  });

  expect(state.identityAnchor?.revalidation).toEqual({
    status: "needs_revalidation",
    conflicts: ["normalized_address"],
  });
  expect(state.identityAnchor?.normalized_address).toBe(stored.normalized_address);
  expect(state.identityAnchor?.coordinates).toEqual(stored.coordinates);
  expect(state.identityAnchor?.evidence.sources).toEqual(stored.evidence.sources);
});

test("saved case round-trip preserves only the bounded identity anchor and provenance", () => {
  const anchor = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  withBrowserStorage((localStorage) => {
    const saved = saveCase(saveInput(anchor));
    expect(saved?.data.propertyIdentityAnchor).toEqual(anchor);

    const reopened = readSavedCases();
    expect(reopened).toHaveLength(1);
    expect(reopened[0].data.propertyIdentityAnchor).toEqual(anchor);
    const raw = localStorage.getItem(SAVED_CASES_STORAGE_KEY) ?? "";
    expect(raw).toContain("journey_browser_anchor");
    expect(raw).toContain("google_geocoding");
    expect(raw).not.toContain("raw_payload");
    expect(raw).not.toContain("api_key");
  });
});

test("malformed stored anchor is dropped without losing the saved case", () => {
  const anchor = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  withBrowserStorage((localStorage) => {
    const saved = saveCase(saveInput(anchor));
    expect(saved).not.toBeNull();
    const rows = JSON.parse(localStorage.getItem(SAVED_CASES_STORAGE_KEY) ?? "[]") as Array<Record<string, unknown>>;
    const data = rows[0].data as Record<string, unknown>;
    data.propertyIdentityAnchor = {
      ...anchor,
      journey_anchor_id: "journey-browser-臺北市信義區市府路1號",
      raw_payload: { provider_secret: "must-not-survive" },
    };
    localStorage.setItem(SAVED_CASES_STORAGE_KEY, JSON.stringify(rows));

    const reopened = readSavedCases();
    expect(reopened).toHaveLength(1);
    expect(reopened[0].data.propertyIdentityAnchor).toBeUndefined();
    expect(reopened[0].title).toBe("市府路案件");
  });
});

test("reopened stored anchor keeps provenance and later conflict requires revalidation", () => {
  const anchor = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );

  withBrowserStorage(() => {
    saveCase(saveInput(anchor));
    const stored = readSavedCases()[0].data.propertyIdentityAnchor;
    expect(stored?.journey_anchor_id).toBe(anchor.journey_anchor_id);
    expect(stored?.evidence.sources).toEqual(anchor.evidence.sources);

    const reopenedState = { ...createClosedLoopJourneyState(context), identityAnchor: stored };
    const conflicting = locationResult({
      geocoding_acceptance: {
        ...locationResult().geocoding_acceptance!,
        original_query: "臺北市信義區松高路10號",
        normalized_address: "臺北市信義區松高路10號",
      },
    });
    const reconciled = setJourneyLocationResult(reopenedState, conflicting, "available", {
      now: () => "2026-09-27T10:00:00.000Z",
    });
    expect(reconciled.identityAnchor?.revalidation.status).toBe("needs_revalidation");
    expect(reconciled.identityAnchor?.journey_anchor_id).toBe(anchor.journey_anchor_id);
    expect(reconciled.identityAnchor?.evidence.sources).toEqual(anchor.evidence.sources);
  });
});

test("saved Location evidence is restored without refreshing anchor provenance", () => {
  const stored = buildJourneyPropertyIdentityAnchor(
    { context, location: locationResult() },
    { now: () => CHECKED_AT, idFactory: () => OPAQUE_UUID },
  );
  const reopened = {
    ...createClosedLoopJourneyState(context, { now: () => "2026-09-27T12:00:00.000Z", idFactory: () => "99999999-2222-4333-8444-555555555555" }),
    identityAnchor: stored,
  };

  const restored = restoreJourneyLocationResult(reopened, locationResult(), "partial");

  expect(restored.identityAnchor).toEqual(stored);
  expect(restored.locationResult).toEqual(locationResult());
  expect(restored.locationStatus).toBe("partial");
});
