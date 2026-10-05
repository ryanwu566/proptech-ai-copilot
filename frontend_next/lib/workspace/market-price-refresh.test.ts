import assert from "node:assert/strict";
import test from "node:test";

const NOW = "2026-10-05T08:00:00.000Z";

function anchor() {
  return {
    version: 1 as const,
    scope: "journey_browser_anchor" as const,
    journey_anchor_id: "journey-browser-11111111-2222-4333-8444-555555555555",
    address_input: "臺北市信義區市府路1號",
    normalized_address: "臺北市信義區市府路1號",
    coordinates: { latitude: 25.0375, longitude: 121.5637 },
    administrative_location: { city: "臺北市", district: "信義區", village: "西村里", village_code: "63000020-014" },
    location_status: "candidate" as const,
    parcel: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: ["no_approved_parcel_identity_evidence"], confirmation: null },
    building: { status: "unavailable" as const, candidate_id: null, candidates: [], source_id: null, confidence: "unknown" as const, limitations: ["no_approved_building_identity_evidence"], confirmation: null },
    confidence: { level: "high" as const, domain: "address_spatial_correlation" as const, basis: ["normalized_address", "trusted_geocoding_coordinates"], limitations: ["not_legal_identity"] },
    evidence: { sources: [{ source_id: "google_geocoding", kind: "geocoding" as const, checked_at: NOW }], checked_at: NOW, limitations: ["journey_browser_correlation_only"] },
    revalidation: { status: "current" as const, conflicts: [] },
  };
}

function savedCase() {
  return {
    id: "case-a",
    title: "市府路案件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1 as const,
    workflowMode: "buying_wizard" as const,
    activeWizardStep: "report" as const,
    progress: 80,
    inputSummary: { city: "臺北市", district: "信義區", road: "市府路1號", propertyPrice: 2480, areaPing: 30 },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "市府路1號", building_type: "住宅大樓", area_ping: 30, building_age_years: 5, floor: 8 },
      propertyIdentityAnchor: anchor(),
    },
  };
}

function workspace() {
  return {
    caseId: "case-a",
    revision: 7,
    identity: { state: "confirmed", scope: "journey_browser_anchor", anchor: anchor() },
  };
}

test("refresh contexts use the confirmed active identity and existing production inputs", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const refresh = await import("./market-price-refresh.ts").catch(() => null);
  assert.ok(refresh, "Market / Valuation refresh adapter must exist");

  const market = refresh.buildMarketRefreshContext(workspace() as never, savedCase() as never);
  const valuation = refresh.buildValuationRefreshContext(workspace() as never, savedCase() as never);

  assert.deepEqual(market?.payload, { county: "臺北市", district: "信義區", road: "市府路1號" });
  assert.deepEqual(valuation?.payload, {
    city: "臺北市",
    district: "信義區",
    road: "市府路1號",
    address_text: "臺北市信義區市府路1號",
    building_type: "住宅大樓",
    area_ping: 30,
    building_age_years: 5,
    floor: 8,
    lat: 25.0375,
    lng: 121.5637,
  });
  assert.equal(market?.caseId, "case-a");
  assert.equal(market?.revision, 7);
  assert.deepEqual(market?.identity, {
    journeyAnchorId: anchor().journey_anchor_id,
    normalizedAddress: anchor().normalized_address,
    coordinates: anchor().coordinates,
  });
  assert.notEqual(market?.fingerprint, valuation?.fingerprint);
});

test("refresh contexts require a confirmed current saved identity", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const refresh = await import("./market-price-refresh.ts");
  const unconfirmed = { ...workspace(), identity: { ...workspace().identity, state: "unconfirmed" } };
  const mismatched = savedCase();
  mismatched.data.propertyIdentityAnchor.normalized_address = "臺北市大安區仁愛路1號";

  assert.equal(refresh.buildMarketRefreshContext(unconfirmed as never, savedCase() as never), null);
  assert.equal(refresh.buildValuationRefreshContext(workspace() as never, mismatched as never), null);
});

test("valuation refresh validates every required production input", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const refresh = await import("./market-price-refresh.ts");
  const missingArea = savedCase();
  missingArea.data.inputs.area_ping = 0;
  const invalidFloor = savedCase();
  invalidFloor.data.inputs.floor = 1.5;

  assert.equal(refresh.buildValuationRefreshContext(workspace() as never, missingArea as never), null);
  assert.equal(refresh.buildValuationRefreshContext(workspace() as never, invalidFloor as never), null);
});

test("late responses are rejected after a case, revision, address, or valuation-input change", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const refresh = await import("./market-price-refresh.ts");
  assert.equal(typeof refresh.canCommitMarketPriceResponse, "function", "late-response guard must exist");
  const response = refresh.buildValuationRefreshContext(workspace() as never, savedCase() as never)!;
  const changedInput = savedCase();
  changedInput.data.inputs.area_ping = 31;
  const currentInput = refresh.buildValuationRefreshContext(workspace() as never, changedInput as never)!;
  const changedRevision = { ...response, revision: 8 };
  const changedAddress = { ...response, fingerprint: `${response.fingerprint}:new-address` };
  const changedCase = { ...response, caseId: "case-b" };

  assert.equal(refresh.canCommitMarketPriceResponse(response, response), true);
  assert.equal(refresh.canCommitMarketPriceResponse(currentInput, response), false);
  assert.equal(refresh.canCommitMarketPriceResponse(changedRevision, response), false);
  assert.equal(refresh.canCommitMarketPriceResponse(changedAddress, response), false);
  assert.equal(refresh.canCommitMarketPriceResponse(changedCase, response), false);
});

test("valuation and valuation trend share one guarded input context", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const refresh = await import("./market-price-refresh.ts");
  const context = refresh.buildValuationRefreshContext(workspace() as never, savedCase() as never)!;

  assert.deepEqual(context.trendPayload, {
    city: context.payload.city,
    district: context.payload.district,
    road: context.payload.road,
    building_type: context.payload.building_type,
    area_ping: context.payload.area_ping,
    building_age_years: context.payload.building_age_years,
    horizon_months: [6, 12, 36],
  });
});

test("only fail-closed actionable valuations are eligible for persistence", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const refresh = await import("./market-price-refresh.ts");
  const comparable = {
    transaction_period: "2026-01", city: "Taipei", district: "Daan", road: "Xinyi Road",
    building_type: "Apartment", area_ping: 30, unit_price_per_ping: 70, total_price: 2100,
    building_age_years: 10, distance_m: 100, similarity_score: 90, weight: 1,
    note: "official", source: "official_plvr_opendata", source_label: "PLVR",
  };
  const actionable = {
    valuation_status: "available", result_origin: "official", is_actionable: true,
    estimate_data_composition: "official", confidence: "high", confidence_score: 80,
    estimate_total_price: 2100, estimate_unit_price_per_ping: 70,
    price_range: { low: 1900, mid: 2100, high: 2300 },
    comparables: [comparable, comparable, comparable],
    valuation_explanation: { sample_count: 3, average_similarity_score: 90 },
  };

  assert.equal(refresh.classifyValuationRefresh(actionable).shouldPersist, true);
  assert.equal(refresh.classifyValuationRefresh({ ...actionable, valuation_status: "no_data", is_actionable: false, comparables: [] }).shouldPersist, false);
  assert.equal(refresh.classifyValuationRefresh({ ...actionable, valuation_status: "unavailable", result_origin: "none", is_actionable: false, comparables: [] }).shouldPersist, false);
  assert.equal(refresh.classifyValuationRefresh({ ...actionable, price_range: { low: null, mid: 2100, high: 2300 } }).shouldPersist, false);
  assert.equal(refresh.classifyValuationRefresh({ ...actionable, valuation_explanation: undefined }).shouldPersist, false);
  assert.equal(refresh.classifyValuationRefresh({ ...actionable, comparables: [comparable] }).shouldPersist, false);
});

test("case compaction retains bounded Market aggregates and drops provider internals", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const persistence = await import("./market-price-persistence.ts").catch(() => null);
  assert.ok(persistence, "bounded Market persistence adapter must exist");
  const market = {
    city: "臺北市",
    county: "臺北市",
    district: "信義區",
    period: "2026-07",
    average_unit_price: 53.1,
    avg_price_per_ping: 53.1,
    transaction_count: 18,
    transaction_volume: 18,
    record_count: 18,
    summary: "近期成交單價集中。",
    source_name: "內政部不動產實價登錄",
    source_updated_at: "2026-08-31",
    coverage_status: "covered",
    data_status: "available",
    caveat: "樣本僅供初步比較。",
    disclaimer: "成交資料不等同正式估價。",
    history: [{ period: "2026-07", average_unit_price: 53.1, transaction_count: 18 }],
    sample_status: "sufficient",
    freshness_status: "fresh",
    effective_scope_label: "臺北市信義區",
    effective_analysis_level: "DISTRICT",
    effective_sample_count: 18,
    median_unit_price_per_ping: 52.4,
    median_total_price: 1850,
    source_file_hash: "secret-provider-hash",
    source_release_id: "provider-release-id",
    support_reference: "internal-support-reference",
    provider_debug_payload: { raw_rows: [1, 2, 3] },
  };

  const stored = persistence.compactMarketInsight(market as never) as unknown as Record<string, unknown>;

  assert.equal(stored.median_total_price, 1850);
  assert.equal(stored.effective_scope_label, "臺北市信義區");
  assert.equal(stored.source_file_hash, undefined);
  assert.equal(stored.source_release_id, undefined);
  assert.equal(stored.support_reference, undefined);
  assert.equal(stored.provider_debug_payload, undefined);
});

test("valuation compaction keeps only an actionable summary", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const persistence = await import("./market-price-persistence.ts");
  const comparable = {
    transaction_period: "2026-01", city: "Taipei", district: "Daan", road: "Xinyi Road",
    building_type: "Apartment", area_ping: 30, unit_price_per_ping: 70, total_price: 2100,
    building_age_years: 10, distance_m: 100, similarity_score: 90, weight: 1,
    note: "official", source: "official_plvr_opendata", source_label: "PLVR",
  };
  const result = {
    valuation_status: "available", valuation_reason_code: "official_result_available",
    result_origin: "official", is_actionable: true, estimate_data_composition: "official",
    confidence: "high", confidence_score: 80, confidence_reason: "Enough evidence.",
    estimate_total_price: 2100, estimate_unit_price_per_ping: 70,
    price_range: { low: 1900, mid: 2100, high: 2300 },
    comparables: [comparable, comparable, comparable],
    valuation_explanation: { sample_count: 3, average_similarity_score: 90 },
    disclaimer: "Reference only.",
    source_details: { file: "provider-file.csv", db_rows_returned: 500 },
    data_status: { provider_debug_payload: { rows: [1, 2, 3] } },
    provider_debug_payload: { raw: true },
  };

  const stored = persistence.compactActionableValuationSummary(result as never) as unknown as Record<string, unknown>;
  assert.deepEqual(stored.comparables, []);
  assert.equal(stored.estimate_total_price, 2100);
  assert.equal(stored.data_status, undefined);
  assert.equal(stored.provider_debug_payload, undefined);
  assert.deepEqual(stored.source_details, {
    file: "",
    nature: "official summary",
    complete_real_price_registry: false,
    formal_appraisal: false,
    bank_appraisal: false,
    future_adapter: "",
  });
});

test("valuation trend compaction removes series, forecasts, and provider diagnostics", async () => {
  // @ts-expect-error Node's native TypeScript test runner requires the source extension.
  const persistence = await import("./market-price-persistence.ts");
  const trend = {
    trend_status: "available", trend_reason_code: "official_trend_available", is_actionable: true,
    source: "official_plvr_opendata", data_scope: "road", raw_period_min: "2026-01", raw_period_max: "2026-08",
    effective_period_min: "2026-01", effective_period_max: "2026-08", excluded_future_period_count: 0,
    excluded_out_of_window_count: 0, period_min: "2026-01", period_max: "2026-08", sample_count: 12,
    road_sample_count: 12, district_sample_count: 24,
    monthly_series: [
      { period: "2026-07", median_unit_price_per_ping: 81, p25_unit_price_per_ping: 78, p75_unit_price_per_ping: 84, transaction_count: 6 },
      { period: "2026-08", median_unit_price_per_ping: 83, p25_unit_price_per_ping: 80, p75_unit_price_per_ping: 86, transaction_count: 6 },
    ],
    yearly_series: [{ year: "2026", median_unit_price_per_ping: 82, transaction_count: 12, yoy_change_percent: null }],
    recent_median_unit_price: 83, trend_annualized_rate: 2.4, volatility: 1.2,
    confidence_level: "high", confidence_reason: "Enough official evidence.",
    scenario_forecast: { conservative: [{ raw: true }], base: [{ raw: true }], optimistic: [{ raw: true }] },
    methodology: ["provider method"], disclaimer: "Reference only.", provider_debug_payload: { rows: [1, 2] },
  };

  const stored = persistence.compactActionableValuationTrendSummary(trend as never) as unknown as Record<string, unknown>;
  assert.equal(stored.recent_median_unit_price, 83);
  assert.equal(stored.is_actionable, false);
  assert.deepEqual(stored.monthly_series, []);
  assert.deepEqual(stored.yearly_series, []);
  assert.deepEqual(stored.scenario_forecast, { conservative: [], base: [], optimistic: [] });
  assert.equal(stored.raw_period_min, undefined);
  assert.equal(stored.provider_debug_payload, undefined);
});
