import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { classifyNearbyPlace, compatibleNearbyKind, NEARBY_POI_GROUPS, NEARBY_POI_KINDS, NEARBY_POI_STYLES, NEARBY_PROPERTY_STYLE, nearbyPoiGroup, nearbyPoiIconSvg } from "./nearby-poi-category.ts";
// @ts-expect-error Native TS runner extension.
import { captureNearbyFacilities, groupNearbyFacilities, normalizeNearbyFacilities } from "./nearby-facilities.ts";
// @ts-expect-error Native TS runner extension.
import { nearbyFacilitiesCopy } from "./nearby-facilities-copy.ts";
import type { NearbyPoiKind, NearbyQueryCategory } from "./nearby-poi-category";

test("each major category maps deterministically from provider types", () => {
  const cases: Array<[string[], NearbyQueryCategory, NearbyPoiKind]> = [
    [["subway_station", "transit_station", "point_of_interest"], "transport", "rail"],
    [["train_station", "transit_station"], "transport", "rail"],
    [["light_rail_station"], "transport", "rail"],
    [["bus_stop", "transit_station"], "transport", "bus"],
    [["bus_station"], "transport", "bus"],
    [["transit_station", "establishment"], "transport", "transit"],
    [["primary_school", "school"], "school", "education"],
    [["university"], "school", "education"],
    [["hospital", "health"], "medical", "medical"],
    [["pharmacy", "store"], "medical", "medical"],
    [["park", "tourist_attraction"], "park", "park"],
    [["garden"], "park", "park"],
    [["convenience_store", "food", "store"], "shopping", "shopping"],
    [["supermarket", "grocery_store"], "shopping", "shopping"],
    [["restaurant", "food"], "food", "food"],
    [["cafe"], "food", "food"],
  ];
  for (const [types, query, kind] of cases) assert.equal(classifyNearbyPlace(types, query), kind, `${types.join(",")} in ${query}`);
  // Rail outranks bus when a hub carries both; order inside types[] never matters.
  assert.equal(classifyNearbyPlace(["bus_station", "subway_station"], "transport"), "rail");
  assert.equal(classifyNearbyPlace(["subway_station", "bus_station"].reverse(), "transport"), "rail");
  assert.equal(classifyNearbyPlace([" Bus_Stop "], "transport"), "bus");
});

test("types refine only within the returned query; unknown types use a bounded fallback", () => {
  // A café returned by the medical query is not re-filed as food, and vice versa.
  assert.equal(classifyNearbyPlace(["cafe", "hospital"], "medical"), "medical");
  assert.equal(classifyNearbyPlace(["hospital"], "food"), "other");
  assert.equal(classifyNearbyPlace(["bakery", "store"], "food"), "other");
  // Older saved evidence without types keeps the query's default category.
  for (const missing of [undefined, null, [], [""], "restaurant", [42]]) assert.equal(classifyNearbyPlace(missing, "transport"), "transit");
  assert.equal(compatibleNearbyKind("bus", "transport"), "bus");
  assert.equal(compatibleNearbyKind("bus", "food"), undefined);
  assert.equal(compatibleNearbyKind("other", "park"), "other");
  assert.equal(compatibleNearbyKind("transport", "transport"), undefined);
});

test("every kind belongs to one filter group and every group is reachable", () => {
  const groups = new Set(NEARBY_POI_KINDS.map(nearbyPoiGroup));
  assert.deepEqual([...groups].sort(), [...NEARBY_POI_GROUPS].sort());
  assert.deepEqual((["rail", "bus", "transit"] as const).map(nearbyPoiGroup), ["transit", "transit", "transit"]);
});

function luminance(hex: string) {
  const channel = (i: number) => { const c = parseInt(hex.slice(i, i + 2), 16) / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

test("palette is bounded, accessible and never relies on colour alone", () => {
  const styles = NEARBY_POI_KINDS.map((kind) => NEARBY_POI_STYLES[kind]);
  assert.equal(new Set(styles.map((s) => s.color)).size, NEARBY_POI_KINDS.length);
  assert.equal(new Set(styles.map((s) => s.glyph)).size, NEARBY_POI_KINDS.length);
  for (const style of [...styles, NEARBY_PROPERTY_STYLE]) {
    assert.match(style.color, /^#[0-9a-f]{6}$/);
    // White glyph on the fill meets the 3:1 non-text contrast minimum.
    assert.ok(1.05 / (luminance(style.color) + 0.05) >= 3, style.color);
  }
  assert.ok(!styles.some((s) => s.color === NEARBY_PROPERTY_STYLE.color || s.glyph === NEARBY_PROPERTY_STYLE.glyph));
  assert.match(nearbyPoiIconSvg(NEARBY_PROPERTY_STYLE, 38, "pin"), /<rect[^>]+rx="6"/);
  assert.match(nearbyPoiIconSvg(NEARBY_POI_STYLES.bus, 26), /<circle cx="12" cy="12" r="10.5"/);
});

test("every product category has a label in all four locales, with no raw ids or provider types", () => {
  const keys = ["transit", "education", "healthcare", "parks", "shopping", "food", "other", "kindRail", "kindBus", "kindTransit", "legend", "filter", "filterAll", "filterCount", "property"];
  const labels = new Set<string>();
  for (const [locale, copy] of Object.entries(nearbyFacilitiesCopy as Record<string, Record<string, string>>)) {
    for (const key of keys) {
      assert.ok(copy[key]?.trim(), `${locale}.${key}`);
      // Neither provider types (snake_case) nor internal ids (bare lowercase tokens) may leak into labels.
      assert.doesNotMatch(copy[key], /[a-z]+_[a-z]+|^(rail|bus|transit|education|medical|park|shopping|food|other|healthcare|parks)$/);
    }
    for (const key of ["kindRail", "kindBus", "kindTransit", "education", "healthcare", "parks", "shopping", "food", "other"]) labels.add(`${locale}:${copy[key]}`);
  }
  assert.equal(labels.size, 9 * 4);
});

const origin = { lat: 24.16525, lng: 120.64555 };
const place = (id: string, types?: string[]) => ({ place_id: id, name: `Place ${id}`, lat: origin.lat + 0.001, lng: origin.lng, source: "google_places", ...(types ? { types } : {}) });

test("capture classifies once, keeps provider names, and never persists raw types", () => {
  const evidence = captureNearbyFacilities({ center: origin, radius_m: 800, source: "google_places", checked_at: "2026-10-20T01:00:00Z", categories: [
    { category: "transport", places: [place("mrt", ["subway_station", "transit_station"]), place("bus", ["bus_stop"]), place("hub", ["transit_station"])] },
    { category: "food", places: [{ ...place("bakery", ["bakery"]), kind: "food" }] },
    { category: "park", places: [place("legacy")] },
  ] }, origin);
  assert.deepEqual(evidence.places.map((p: { id: string; kind: string }) => [p.id, p.kind]), [["mrt", "rail"], ["bus", "bus"], ["hub", "transit"], ["bakery", "other"], ["legacy", "park"]]);
  assert.equal(evidence.places[0].name, "Place mrt");
  assert.equal(JSON.stringify(evidence).includes("subway_station"), false);
  assert.deepEqual(groupNearbyFacilities(evidence).map((g: { category: string }) => g.category), ["transit", "parks", "other"]);
  // Round-trip keeps the derived kind; a tampered incompatible kind is re-derived from the query.
  const stored = JSON.parse(JSON.stringify(evidence));
  assert.deepEqual(normalizeNearbyFacilities(stored), evidence);
  stored.places[0].kind = "food";
  assert.equal(normalizeNearbyFacilities(stored)!.places[0].kind, "transit");
  // Saved evidence from before kinds existed still renders with its query default.
  for (const p of stored.places) delete p.kind;
  assert.deepEqual(normalizeNearbyFacilities(stored)!.places.map((p: { kind: string }) => p.kind), ["transit", "transit", "transit", "food", "park"]);
});
