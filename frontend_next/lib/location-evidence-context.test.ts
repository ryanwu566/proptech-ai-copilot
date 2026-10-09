import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript runner requires the source extension.
import { locationEvidenceKey, locationValuationExplanation, withLocationAdvisoryContext } from "./location-evidence-context.ts";
// @ts-expect-error Native TS runner extension.
import { normalizeLocationInsightEvidence } from "./location-insight-evidence.ts";
import type { LocationInsightResult } from "./api";

function legacyLocation(): LocationInsightResult {
  return {
    input: { property_price_wan: 2000, area_ping: 30 },
    resolved_location: { address_label: "Property A", latitude: 25.03, longitude: 121.56, geocoding_confidence: "high" },
    location_score: 72, category_scores: { transit_score: 80, risk_score: 50 },
    poi_summary: { transit_count: 4, risk_facility_count: 0 },
    valuation_context: { supports_price_reasonableness: true, explanation: "Legacy suitable score 72" },
    data_quality: { status: "good", checked_at: "2026-10-09T01:00:00Z", missing_sources: ["risk_facilities"], warnings: [] },
  } as unknown as LocationInsightResult;
}

test("repeated normalization preserves newer advisory inputs independently of raw provider inputs", () => {
  for (const [price, area, unit] of [[2000, 35, "57.1"], [2600, 30, "86.7"]] as const) {
    const raw = legacyLocation();
    const current = withLocationAdvisoryContext(normalizeLocationInsightEvidence(raw), price, area);
    const twice = normalizeLocationInsightEvidence(normalizeLocationInsightEvidence(current));
    assert.match(twice.valuation_context.explanation, new RegExp(`${unit} 萬／坪`));
    assert.match(twice.valuation_context.explanation, /區位總分 資料不足/);
    assert.equal(twice.input, raw.input);
    assert.equal(twice.data_quality.checked_at, raw.data_quality.checked_at);
    assert.equal(twice.location_score, null);
    assert.equal(twice.category_scores.risk_score, null);
    assert.equal(twice.poi_summary.risk_facility_count, null);
    assert.equal(twice.valuation_context.supports_price_reasonableness, "unknown");
  }
});

test("serialized saved advisory survives stripped coordinates while cleared current inputs remain unknown", () => {
  const raw = legacyLocation();
  const current = withLocationAdvisoryContext(normalizeLocationInsightEvidence(raw), 2000, 35);
  const reopened = normalizeLocationInsightEvidence(JSON.parse(JSON.stringify({ ...current, resolved_location: null })));
  assert.match(reopened.valuation_context.explanation, /57\.1 萬／坪/);
  const cleared = normalizeLocationInsightEvidence(withLocationAdvisoryContext(current, undefined, 35));
  assert.match(cleared.valuation_context.explanation, /未提供完整價格與坪數/);
  assert.doesNotMatch(cleared.valuation_context.explanation, /66\.7|57\.1/);
});

const context = { city: "臺北市", district: "大安區", road: "和平東路二段", address: "和平東路二段100號", property_price: 2_000, area_ping: 30, building_type: "住宅大樓" };

test("non-spatial property edits keep the same Location provider identity", () => {
  const key = locationEvidenceKey(context, 800);
  for (const edit of [{ area_ping: 35 }, { property_price: 2_600 }, { building_type: "公寓" }]) {
    assert.equal(locationEvidenceKey({ ...context, ...edit }, 800), key);
  }
});

test("address, administrative context and radius changes require different Location evidence", () => {
  const key = locationEvidenceKey(context, 800);
  for (const edit of [{ address: "市府路1號" }, { city: "新北市" }, { district: "信義區" }, { road: "市府路" }]) {
    assert.notEqual(locationEvidenceKey({ ...context, ...edit }, 800), key);
  }
  assert.notEqual(locationEvidenceKey(context, 1_100), key);
});

test("Location price-per-ping advisory uses current area and price without requerying spatial evidence", () => {
  assert.match(locationValuationExplanation(2_000, 35, 78), /57\.1 萬／坪/);
  assert.match(locationValuationExplanation(2_600, 30, 78), /86\.7 萬／坪/);
  assert.match(locationValuationExplanation(2_000, 30, null), /區位總分 資料不足/);
});

test("incomplete or invalid advisory inputs remain unknown instead of producing a fabricated unit price", () => {
  for (const [price, area] of [[undefined, 30], [2_000, undefined], [2_000, 0], [NaN, 30], [2_000, Infinity]]) {
    assert.match(locationValuationExplanation(price, area, 78), /不能判斷價格合理性/);
  }
});

test("retained and saved Location results update advisory while preserving the original spatial observation", () => {
  const original = {
    input: { property_price_wan: 2_000, area_ping: 30 },
    resolved_location: { address_label: "Property A", latitude: 25.03, longitude: 121.56, geocoding_confidence: "high" },
    location_score: 78,
    valuation_context: { supports_price_reasonableness: "unknown" as const, explanation: "本物件約 66.7 萬／坪" },
    data_quality: { status: "good" as const, checked_at: "2026-10-08T00:00:00Z", missing_sources: [], warnings: [] },
  };
  const current = withLocationAdvisoryContext(original, 2_000, 35);
  assert.match(current.valuation_context.explanation, /57\.1 萬／坪/);
  assert.equal(current.resolved_location, original.resolved_location);
  assert.equal(current.input, original.input);
  assert.equal(current.data_quality, original.data_quality);
  assert.equal(current.valuation_context.supports_price_reasonableness, "unknown");
  assert.equal(withLocationAdvisoryContext(current, 2_000, 35), current);
  assert.match(original.valuation_context.explanation, /66\.7/);
  const unavailable = { ...original, resolved_location: null, data_quality: { ...original.data_quality, status: "unavailable" as const } };
  assert.equal(withLocationAdvisoryContext(unavailable, 2_000, 35), unavailable);
});
