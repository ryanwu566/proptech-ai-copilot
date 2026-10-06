import { expect, test } from "@playwright/test";
import type { LocationInsightResult } from "../lib/api";
import {
  createClosedLoopJourneyState,
  setJourneyLocationResult,
  updateJourneyProperty,
} from "../lib/closed-loop-journey";
import {
  getDraftSaveMissingFields,
  readSavedCases,
  saveCase,
  type SaveCaseInput,
} from "../lib/case-storage";
import { getSafePriceContext } from "../lib/price-affordability-journey";

const CHECKED_AT = "2026-10-06T05:00:00.000Z";
const ADDRESS = "臺中市西屯區臺灣大道三段100號";

function acceptedLocation(address = ADDRESS): LocationInsightResult {
  return {
    input: { address },
    resolved_location: {
      address_label: address,
      latitude: 24.16525,
      longitude: 120.64555,
      geocoding_confidence: "high",
    },
    geocoding_acceptance: {
      original_query: ADDRESS,
      normalized_address: address,
      resolved_lat: 24.16525,
      resolved_lng: 120.64555,
      geocoding_source: "google_geocoding",
      match_quality: "EXACT_OR_ACCEPTABLE",
      accepted_for_analysis: true,
      requires_confirmation: false,
      mismatch_reasons: [],
      message: "Accepted for bounded analysis.",
    },
    village_resolution: {
      status: "resolved",
      county: "臺中市",
      town: "西屯區",
      village: "潮洋里",
      village_code: "66000060-020",
      district_code: "66000060",
      source: "nlsc_village_boundary",
      source_vintage: "2026-09",
      reason: "resolved",
    },
    radius_m: 800,
    location_score: 75,
    category_scores: { transit_score: 70, convenience_score: 80, education_score: 65, green_space_score: 60, medical_score: 70, risk_score: 40 },
    poi_summary: { transit_count: 2, convenience_count: 5, school_count: 1, park_count: 1, medical_count: 2, risk_facility_count: 0 },
    nearest_pois: [],
    strengths: [],
    weaknesses: [],
    buyer_fit: { self_use_family: "Review", commuter: "Review", investor: "Review", elderly: "Review" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "Location does not determine price." },
    data_quality: { status: "good", missing_sources: [], warnings: [] },
    scoring_method: { weights: {}, explanation: "Fixture" },
    disclaimer: "Reference only.",
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

function withBrowserStorage<T>(run: () => T): T {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { localStorage: memoryStorage(), sessionStorage: memoryStorage(), dispatchEvent: () => true },
  });
  try {
    return run();
  } finally {
    if (previous) Object.defineProperty(globalThis, "window", previous);
    else Reflect.deleteProperty(globalThis, "window");
  }
}

function saveInput(state: ReturnType<typeof setJourneyLocationResult>): SaveCaseInput {
  return {
    title: "臺灣大道案件",
    activeWizardStep: "report",
    progress: 60,
    inputSummary: {},
    data: {
      inputs: { city: "", district: "", road: "", building_type: "", area_ping: 0, building_age_years: 0, floor: 0 },
      propertyIdentityAnchor: state.identityAnchor,
      journeyContext: {
        version: 1,
        propertyContext: state.propertyContext,
        priceBasis: state.priceBasis,
        valuationStatus: state.valuationStatus,
      } as SaveCaseInput["data"]["journeyContext"],
    },
  };
}

test("accepted Location evidence enriches one current journey context and derives the valuation road", () => {
  const initial = createClosedLoopJourneyState({
    addressSummary: ADDRESS,
    sourceLabel: "Property selection",
    selectionStatus: "selected",
  }, { now: () => CHECKED_AT, idFactory: () => "11111111-2222-4333-8444-555555555555" });

  const next = setJourneyLocationResult(initial, acceptedLocation(), "available", { now: () => CHECKED_AT });

  expect(next.identityAnchor?.revalidation).toEqual({ status: "current", conflicts: [] });
  expect(next.identityAnchor?.coordinates).toEqual({ latitude: 24.16525, longitude: 120.64555 });
  expect(next.propertyContext).toMatchObject({
    city: "臺中市",
    district: "西屯區",
    road: "臺灣大道三段",
    addressSummary: ADDRESS,
    selectionStatus: "selected",
  });
});

test("accepted normalized address may add a postal code without forcing false revalidation", () => {
  const initial = createClosedLoopJourneyState({
    city: "臺中市",
    district: "西屯區",
    road: "臺灣大道三段100號",
    addressSummary: ADDRESS,
    sourceLabel: "Property selection",
    selectionStatus: "selected",
  }, { now: () => CHECKED_AT, idFactory: () => "11111111-2222-4333-8444-555555555555" });

  const next = setJourneyLocationResult(initial, acceptedLocation(`407${ADDRESS}`), "available", { now: () => CHECKED_AT });

  expect(next.identityAnchor?.revalidation).toEqual({ status: "current", conflicts: [] });
  expect(next.identityAnchor?.normalized_address).toBe(`407${ADDRESS}`);
});

test("an address without a safely derivable road remains unconfirmed instead of receiving a default road", () => {
  const ambiguous = "臺北市信義區市政府";
  const initial = createClosedLoopJourneyState({ addressSummary: ambiguous, sourceLabel: "User input", selectionStatus: "selected" });
  const next = setJourneyLocationResult(initial, acceptedLocation(ambiguous), "available");

  expect(next.propertyContext.road).toBeUndefined();
});

test("current accepted anchor with normalized address and coordinates satisfies Save Case and reopens bounded state", () => {
  const initial = createClosedLoopJourneyState({ addressSummary: ADDRESS, sourceLabel: "Property selection", selectionStatus: "selected" });
  const accepted = setJourneyLocationResult(initial, acceptedLocation(), "available");
  const input = saveInput({ ...accepted, valuationStatus: "unavailable" });

  withBrowserStorage(() => {
    expect(getDraftSaveMissingFields(input)).toEqual([]);
    const saved = saveCase(input);
    expect(saved).not.toBeNull();
    const reopened = readSavedCases()[0];
    expect(reopened.data.propertyIdentityAnchor?.normalized_address).toBe(ADDRESS);
    expect(reopened.data.propertyIdentityAnchor?.coordinates).toEqual({ latitude: 24.16525, longitude: 120.64555 });
    expect((reopened.data.journeyContext as unknown as { valuationStatus?: string })?.valuationStatus).toBe("unavailable");
    expect(JSON.stringify(reopened.data)).not.toMatch(/raw_payload|api_key|provider_secret/);
  });
});

test("Save Case reports the exact identity correction when the accepted anchor is stale", () => {
  const initial = createClosedLoopJourneyState({ addressSummary: ADDRESS, sourceLabel: "Property selection", selectionStatus: "selected" });
  const accepted = setJourneyLocationResult(initial, acceptedLocation(), "available");
  const stale = {
    ...accepted,
    identityAnchor: accepted.identityAnchor && {
      ...accepted.identityAnchor,
      location_status: "stale" as const,
      revalidation: { status: "needs_revalidation" as const, conflicts: ["normalized_address" as const] },
    },
  };

  expect(getDraftSaveMissingFields(saveInput(stale))).toEqual(["property_identity_revalidation"]);
});

test("Save Case identifies missing accepted coordinates instead of bypassing identity validation", () => {
  const initial = createClosedLoopJourneyState({ addressSummary: ADDRESS, sourceLabel: "Property selection", selectionStatus: "selected" });

  expect(getDraftSaveMissingFields(saveInput(initial))).toEqual(["accepted_property_coordinates"]);
});

test("attempted unavailable valuation remains distinct from not started in downstream price context", () => {
  const propertyContext = createClosedLoopJourneyState({ addressSummary: ADDRESS, sourceLabel: "Property selection", selectionStatus: "selected" }).propertyContext;

  expect(getSafePriceContext({ propertyContext }).officialValuationStatus).toBe("not_started");
  expect(getSafePriceContext({ propertyContext, valuationStatus: "unavailable" } as never).officialValuationStatus).toBe("unavailable");
});

test("property switch clears prior road, valuation attempt, and property-bound evidence", () => {
  const initial = createClosedLoopJourneyState({ addressSummary: ADDRESS, sourceLabel: "Property selection", selectionStatus: "selected" });
  const accepted = {
    ...setJourneyLocationResult(initial, acceptedLocation(), "available"),
    valuationStatus: "unavailable" as const,
    terrainResult: { overall: { level: "unknown" } } as never,
    terrainStatus: "partial" as const,
  };

  const switched = updateJourneyProperty(accepted, {
    city: "臺北市",
    district: "信義區",
    road: undefined,
    addressSummary: "臺北市信義區市政府",
    selectionStatus: "selected",
  });

  expect(switched.propertyContext.road).toBeUndefined();
  expect(switched.valuationStatus).toBe("not_started");
  expect(switched.terrainResult).toBeUndefined();
  expect(switched.identityAnchor?.journey_anchor_id).not.toBe(accepted.identityAnchor?.journey_anchor_id);
});
