import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native Node runner requires source extension.
const feature = await import("./my-places.ts").catch(() => null);
// @ts-expect-error Native Node runner requires source extension.
const queries = await import("./my-places-query.ts").catch(() => null);
import type { MyPlace, PropertyOrigin, StoredRoute } from "./my-places";

const time = "2026-10-12T04:00:00.000Z";
function memory() {
  const data = new Map<string, string>();
  return { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => { data.set(key, value); }, data };
}
const place = (id = "p1", overrides: Partial<MyPlace> = {}): MyPlace => ({ id, label: "父母家 / Home", category: "family", address: "臺北車站", transportMode: "transit", weeklyTrips: 5, priority: "important", createdAt: time, updatedAt: time, ...overrides });
const origin: PropertyOrigin = { caseId: "c1", identity: "anchor-a", address: "臺北市市府路1號", latitude: 25.03, longitude: 121.56, confirmed: true };
function route(p = place(), o = origin, overrides = {}) {
  return feature?.makeStoredRoute(o, p, { status: "resolved", source: "google_routes", mode: p.transportMode, duration_min: 24, duration_seconds: 1440, distance_m: 9800, partial: false, fallback: false, reason_code: "success", checked_at: time, ...overrides }) as StoredRoute;
}

test("versioned places persist verbatim labels, CRUD, frequency, explicit order, and reload", () => {
  const storage = memory(); const store = feature?.createPlacesStore(storage);
  assert.ok(store);
  assert.equal(store.save([place(), place("p2")]), true);
  assert.deepEqual(feature?.createPlacesStore(storage).read().places.map((p: MyPlace) => p.label), ["父母家 / Home", "父母家 / Home"]);
  const edited = feature?.updatePlace(store.read().places, "p1", { weeklyTrips: 0, address: "京都駅" }, time);
  assert.equal(edited?.[0].weeklyTrips, 0);
  const reordered = feature?.movePlace(edited!, "p2", -1);
  assert.deepEqual(reordered?.map((p: MyPlace) => p.id), ["p2", "p1"]);
  store.save(feature!.deletePlace(reordered!, "p1"));
  assert.deepEqual(store.read().places.map((p: MyPlace) => p.id), ["p2"]);
  assert.equal(JSON.parse(storage.getItem(feature!.PLACES_KEY)!).version, 1);
});

test("invalid frequencies, modes, duplicate IDs, and oversized stores fail closed", () => {
  const store = feature?.createPlacesStore(memory()); assert.ok(store);
  for (const bad of [-1, 1.5, 22, NaN]) assert.equal(store.save([place("p1", { weeklyTrips: bad })]), false);
  assert.equal(store.save([place(), place()]), false);
  assert.equal(store.save([place("p1", { transportMode: "bicycle" as never })]), false);
  assert.equal(store.save(Array.from({ length: 21 }, (_, i) => place(String(i)))), false);
});

test("corrupt, future-version, and denied storage are reported and not overwritten", () => {
  const storage = memory(); assert.ok(feature);
  for (const value of ["{", JSON.stringify({ version: 2, places: [] })]) {
    storage.setItem(feature.PLACES_KEY, value);
    const store = feature.createPlacesStore(storage);
    assert.equal(store.read().error, true); assert.equal(store.save([place()]), false);
    assert.equal(storage.getItem(feature.PLACES_KEY), value);
  }
  const denied = feature.createPlacesStore({ getItem: () => { throw Error("denied"); }, setItem: () => { throw Error("denied"); } });
  assert.equal(denied.read().error, true); assert.equal(denied.save([place()]), false);
});

test("weekly burden has known totals plus explicit unknown, never zero substitution", () => {
  assert.ok(feature);
  const places = [place(), place("p2"), place("p3", { weeklyTrips: 0 })];
  const summary = feature.buildCommuteComparisonSummary(origin, places, [route(), route(places[2])]);
  assert.equal(summary.knownWeeklyMinutes, 240);
  assert.equal(summary.knownDestinationsCount, 2);
  assert.deepEqual(summary.unknownPlaceIds, ["p2"]);
  assert.equal(summary.destinations[2].weeklyMinutes, 0);
  assert.equal(feature.buildCommuteComparisonSummary(origin, [places[2]], []).destinations[0].weeklyMinutes, null);
});

test("unavailable, malformed, simulated, fallback, partial, and provider mode mismatch stay unknown", () => {
  assert.ok(feature);
  for (const overrides of [{ status: "unavailable", duration_min: null }, { duration_min: -1 }, { duration_min: Infinity }, { source: "none" }, { source: "mock", fallback: true }, { partial: true }, { fallback: true }, { mode: "walking" }, { mode: "bicycle" }, { checked_at: "invalid" }, { reason_code: "malformed_response" }, { reason_code: "provider_error" }, { reason_code: "unrecognized_reason" }]) {
    const summary = feature.buildCommuteComparisonSummary(origin, [place()], [route(place(), origin, overrides)]);
    assert.equal(summary.knownWeeklyMinutes, 0); assert.deepEqual(summary.unknownPlaceIds, ["p1"]);
    assert.equal(summary.destinations[0].status, "UNAVAILABLE");
  }
});

test("property, destination, coordinates, mode, and identity state changes invalidate evidence", () => {
  assert.ok(feature);
  for (const [o, p] of [[{ ...origin, address: "高雄市" }, place()], [{ ...origin, identity: "anchor-b" }, place()], [{ ...origin, latitude: 24 }, place()], [{ ...origin, confirmed: false }, place()], [origin, place("p1", { address: "京都駅" })], [origin, place("p1", { transportMode: "walking" })]] as [PropertyOrigin, MyPlace][]) {
    const summary = feature.buildCommuteComparisonSummary(o, [p], [route()]);
    assert.equal(summary.destinations[0].status, "STALE"); assert.equal(summary.destinations[0].weeklyMinutes, null);
    assert.equal(summary.destinations[0].route?.destinationAddress, "臺北車站");
  }
  assert.equal(feature.buildCommuteComparisonSummary({ ...origin, caseId: "c2" }, [place()], [route()]).destinations[0].status, "NOT_CHECKED");
  assert.equal(feature.buildCommuteComparisonSummary(origin, [place("p2")], [route()]).destinations[0].status, "NOT_CHECKED");
});

test("label, frequency, priority, and order changes reuse routes without provider calls", () => {
  assert.ok(feature);
  const summary = feature.buildCommuteComparisonSummary(origin, [place("p1", { label: "会社", weeklyTrips: 2, priority: "secondary" })], [route()]);
  assert.equal(summary.destinations[0].status, "AVAILABLE"); assert.equal(summary.knownWeeklyMinutes, 96);
});

test("route store is versioned, bounded, reloadable and selection is case isolated", () => {
  assert.ok(feature); const storage = memory(); const store = feature.createRoutesStore(storage);
  for (let i = 0; i < 205; i++) assert.equal(store.put(route(place(String(i)))), true);
  assert.equal(store.read().routes.length, 200);
  assert.equal(feature.createRoutesStore(storage).read().routes.length, 200);
  assert.equal(store.select("c1", ["p1", "p2"]), true);
  assert.deepEqual(store.read().selections.c1, ["p1", "p2"]);
  assert.equal(store.read().selections.c2, undefined);
  assert.equal(JSON.parse(storage.getItem(feature.ROUTES_KEY)!).version, 1);
});

test("explicit query helper makes no calls on creation and deduplicates concurrent identical routes", async () => {
  assert.ok(queries); let attempts = 0;
  let resolve!: (value: unknown) => void;
  const pending = new Promise((done) => { resolve = done; });
  const call = async () => { attempts++; return await pending as never; };
  const query = queries.createExplicitRouteQuery(call);
  assert.equal(attempts, 0);
  const a = query(origin, place()); const b = query(origin, place("p2"));
  assert.equal(attempts, 1);
  resolve({ status: "resolved", source: "google_routes", mode: "transit", duration_min: 24, duration_seconds: 1440, distance_m: 9800, partial: false, fallback: false, reason_code: "success", checked_at: time });
  await Promise.all([a, b]);
  await query(origin, place()); assert.equal(attempts, 2);
  await query(origin, place("p1", { transportMode: "walking" })); assert.equal(attempts, 3);
});

test("unconfirmed or missing property coordinates never call provider", async () => {
  assert.ok(queries); let attempts = 0;
  const query = queries.createExplicitRouteQuery(async () => { attempts++; return {} as never; });
  await assert.rejects(query({ ...origin, confirmed: false }, place()));
  await assert.rejects(query({ ...origin, latitude: NaN }, place()));
  assert.equal(attempts, 0);
});

test("one explicit batch deduplicates sequential identical routes without deduplicating a later refresh", async () => {
  assert.ok(queries); let attempts = 0;
  const call = queries.createExplicitRouteQuery(async (payload) => { attempts++; return { status: "resolved", source: "google_routes", mode: payload.mode, duration_min: 24, duration_seconds: 1440, distance_m: 9800, partial: false, fallback: false, reason_code: "success", checked_at: time, message: "", disclaimer: "" }; });
  const batch = queries.createExplicitRouteBatch(call);
  await batch(origin, place()); await batch(origin, place("p2")); assert.equal(attempts, 1);
  await batch(origin, place("p2", { transportMode: "walking" })); assert.equal(attempts, 2);
  await queries.createExplicitRouteBatch(call)(origin, place()); assert.equal(attempts, 3);
});

test("normalized destination coordinates determine payload and deduplication", async () => {
  assert.ok(queries);
  const payloads: unknown[] = [];
  const query = queries.createExplicitRouteQuery(async (payload) => { payloads.push(payload); return {} as never; });
  const batch = queries.createExplicitRouteBatch(query);
  await batch(origin, place("p1", { latitude: 25, longitude: 121 }));
  await batch(origin, place("p2", { latitude: 24, longitude: 120 }));
  await batch(origin, place("p3", { address: "Different authored address", latitude: 25, longitude: 121 }));
  assert.deepEqual(payloads, [
    { origin_latitude: 25.03, origin_longitude: 121.56, destination_latitude: 25, destination_longitude: 121, mode: "transit" },
    { origin_latitude: 25.03, origin_longitude: 121.56, destination_latitude: 24, destination_longitude: 120, mode: "transit" },
  ]);
  await query(origin, place("p4", { normalizedAddress: "Normalized destination" }));
  assert.equal((payloads.at(-1) as unknown as { destination_address: string }).destination_address, "Normalized destination");
});

test("stalled provider requests are capped, aborted and released for an explicit later refresh", { timeout: 1000 }, async () => {
  assert.ok(queries);
  const signals: AbortSignal[] = [];
  const query = queries.createExplicitRouteQuery((_payload, signal) => {
    signals.push(signal!); return new Promise(() => {});
  }, { maxPending: 2, timeoutMs: 20 });
  const a = query(origin, place("p1", { address: "A" }));
  const b = query(origin, place("p2", { address: "B" }));
  const errors = Promise.all([assert.rejects(a, /route_timeout/), assert.rejects(b, /route_timeout/)]);
  await assert.rejects(query(origin, place("p3", { address: "C" })), /route_capacity/);
  assert.equal(signals.length, 2);
  await errors;
  assert.ok(signals.every((signal) => signal.aborted));
  await assert.rejects(query(origin, place("p1", { address: "A" })), /route_timeout/);
  assert.equal(signals.length, 3);
});

test("route persistence strips unexpected credentials from input and existing records", () => {
  assert.ok(feature);
  const storage = memory(); const store = feature.createRoutesStore(storage);
  const injected = { ...route(), access_token: "do-not-persist", providerCredentials: { token: "secret" } };
  assert.equal(store.put(injected), true);
  assert.equal(storage.getItem(feature.ROUTES_KEY)!.includes("do-not-persist"), false);
  storage.setItem(feature.ROUTES_KEY, JSON.stringify({ version: 1, routes: [injected], selections: {} }));
  assert.equal(JSON.stringify(store.read().routes).includes("access_token"), false);
  assert.equal(store.select("c1", ["p1"]), true);
  assert.equal(storage.getItem(feature.ROUTES_KEY)!.includes("providerCredentials"), false);
});
