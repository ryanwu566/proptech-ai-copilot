import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { captureNearbyFacilities, normalizeNearbyFacilities, groupNearbyFacilities, shareNearbyAcquisition } from "./nearby-facilities.ts";
// @ts-expect-error Native TS runner extension.
import { nearbyFacilitiesCopy } from "./nearby-facilities-copy.ts";

const origin = { lat: 24.16525, lng: 120.64555 };
const place = (name = "Local shop") => ({ place_id: name, name, lat: origin.lat + 0.001, lng: origin.lng, source: "google_places", rating: 5, address: "must not persist" });
const response = (categories: unknown[]) => ({ center: origin, radius_m: 800, source: "google_places", categories, checked_at: "2026-10-20T01:00:00Z" });

test("all four locales cover the same controls, evidence limits and failure states", () => {
  const keys = Object.keys(nearbyFacilitiesCopy["zh-TW"]).sort();
  for (const [locale, copy] of Object.entries(nearbyFacilitiesCopy)) {
    assert.deepEqual(Object.keys(copy).sort(), keys, locale);
    assert.ok(Object.values(copy).every((text) => text.trim().length > 0));
    assert.match(copy.distance, /\{\{distance\}\}/);
    assert.match(copy.checked, /\{\{date\}\}/);
    assert.match(copy.scope, /\{\{radius\}\}/);
    if (locale === "en" || locale === "ko") assert.doesNotMatch(Object.values(copy).join(""), /[一-鿿]/);
  }
});

test("groups only returned facilities and computes straight-line distance locally", () => {
  const evidence = captureNearbyFacilities(response([
    { category: "shopping", places: [place()] }, { category: "food", places: [place("Cafe")] },
    { category: "school", places: [] },
  ]), origin);
  const groups = groupNearbyFacilities(evidence);
  assert.deepEqual(groups.map((g) => g.category), ["shopping", "food"]);
  assert.deepEqual(groups.map((g) => g.places.length), [1, 1]);
  assert.ok(groups[0].places[0].distanceM > 110 && groups[0].places[0].distanceM < 112);
  assert.equal(JSON.stringify(evidence).includes("rating"), false);
  assert.equal(JSON.stringify(evidence).includes("must not persist"), false);
});

test("partial, failed, unknown and malformed categories cannot fabricate facilities", () => {
  const evidence = captureNearbyFacilities({ ...response([
    { category: "transport", places: [place("Station"), null, { name: "No point" }] },
    { category: "medical", places: [place("Failed medical")] },
    { category: "invented", places: [place("Unknown")] },
  ]), partial: true, failed_categories: ["medical"] }, origin);
  assert.equal(evidence.partial, true);
  assert.deepEqual(groupNearbyFacilities(evidence).map((g) => g.category), ["transit"]);
  assert.equal(evidence.places.length, 1);
  assert.throws(() => captureNearbyFacilities(null, origin));
  assert.throws(() => captureNearbyFacilities({}, origin));
  assert.throws(() => captureNearbyFacilities(response([]), { lat: 25, lng: 121 }));
});

test("fallback never becomes real property evidence; successful empty is retained", () => {
  assert.throws(() => captureNearbyFacilities({ ...response([]), source: "mock", fallback: true }, origin));
  const empty = captureNearbyFacilities(response([{ category: "park", places: [] }]), origin);
  assert.deepEqual(empty.places, []);
  assert.deepEqual(empty.successfulCategories, ["park"]);
  assert.deepEqual(normalizeNearbyFacilities(JSON.parse(JSON.stringify(empty))), empty);
});

test("persistence bounds, deduplicates and rejects foreign/out-of-range points", () => {
  const evidence = captureNearbyFacilities(response([{ category: "shopping", places: [
    ...Array.from({ length: 30 }, (_, i) => place(`Shop ${i}`)), place("Shop 0"),
    { ...place("Far"), lat: 25 }, { ...place("Invalid"), lng: NaN },
  ] }]), origin);
  assert.equal(evidence.places.length, 10);
  assert.deepEqual(normalizeNearbyFacilities(JSON.parse(JSON.stringify(evidence))), evidence);
  assert.equal(normalizeNearbyFacilities({ version: 1, places: "broken" }), undefined);
});

test("concurrent accidental clicks share acquisition, later explicit refresh can run", async () => {
  let calls = 0;
  let done!: (v: string) => void;
  const acquire = () => { calls++; return new Promise<string>((resolve) => { done = resolve; }); };
  const first = shareNearbyAcquisition("case-a:origin", acquire);
  const second = shareNearbyAcquisition("case-a:origin", acquire);
  assert.equal(calls, 1);
  done("saved");
  assert.deepEqual(await Promise.all([first, second]), ["saved", "saved"]);
  await shareNearbyAcquisition("case-a:origin", async () => { calls++; return "refreshed"; });
  assert.equal(calls, 2);
});
