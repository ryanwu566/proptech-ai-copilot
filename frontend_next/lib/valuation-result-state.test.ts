import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getActionableValuation, getValuationDisplayState } from "./valuation-result-state.ts";

const officialComparable = {
  transaction_period: "2026-01", city: "Taipei", district: "Daan", road: "Xinyi Road",
  building_type: "Apartment", area_ping: 30, unit_price_per_ping: 70, total_price: 2100,
  building_age_years: 10, distance_m: 100, similarity_score: 90, weight: 1,
  note: "official", source: "official_plvr_opendata", source_label: "PLVR",
};

function valuation(overrides: Record<string, unknown> = {}): unknown {
  return {
    valuation_status: "available", valuation_reason_code: "official_result_available",
    result_origin: "official", is_actionable: true,
    estimate_data_composition: "official", confidence: "high",
    estimate_total_price: 2100, estimate_unit_price_per_ping: 70,
    price_range: { low: 1900, mid: 2100, high: 2300 }, confidence_score: 80,
    comparables: [officialComparable, officialComparable, officialComparable],
    valuation_explanation: { sample_count: 3, average_similarity_score: 90 },
    ...overrides,
  };
}

test("complete official valuation is actionable", () => {
  const result = valuation();

  assert.deepEqual(getValuationDisplayState(result), { kind: "available", actionable: true, message: "" });
  assert.equal(getActionableValuation(result)?.priceRange.mid, 2100);
});

test("nullable price range is bounded as an invalid response", () => {
  const result = valuation({ price_range: { low: null, mid: 2100, high: 2300 } });

  assert.equal(getValuationDisplayState(result).kind, "error");
  assert.equal(getActionableValuation(result), null);
});

test("missing optional valuation explanation does not throw", () => {
  const result = valuation({ valuation_explanation: undefined });

  assert.doesNotThrow(() => getValuationDisplayState(result));
  assert.equal(getValuationDisplayState(result).kind, "error");
});

test("insufficient evidence stays non-actionable without fabricated numbers", () => {
  const result = valuation({
    valuation_status: "no_data", result_origin: "official", is_actionable: false,
    estimate_total_price: null, estimate_unit_price_per_ping: null,
    price_range: { low: null, mid: null, high: null }, confidence_score: null, comparables: [],
  });

  assert.equal(getValuationDisplayState(result).kind, "no_data");
  assert.equal(getActionableValuation(result), null);
});

test("provider unavailable stays non-actionable", () => {
  const result = valuation({
    valuation_status: "unavailable", result_origin: "none", is_actionable: false,
    estimate_total_price: null, estimate_unit_price_per_ping: null,
    price_range: { low: null, mid: null, high: null }, confidence_score: null, comparables: [],
  });

  assert.equal(getValuationDisplayState(result).kind, "unavailable");
  assert.equal(getActionableValuation(result), null);
});

test("non-finite successful valuation is a bounded contract error", () => {
  const result = valuation({ confidence_score: Number.NaN });

  assert.equal(getValuationDisplayState(result).kind, "error");
  assert.equal(getActionableValuation(result), null);
});

test("sample-backed or malformed comparable evidence cannot become actionable", () => {
  const sampleBacked = valuation({ estimate_data_composition: "sample" });
  const malformedComparable = valuation({ comparables: [officialComparable, officialComparable, { ...officialComparable, total_price: null }] });

  assert.equal(getValuationDisplayState(sampleBacked).kind, "error");
  assert.equal(getActionableValuation(sampleBacked), null);
  assert.equal(getValuationDisplayState(malformedComparable).kind, "error");
  assert.equal(getActionableValuation(malformedComparable), null);
});
