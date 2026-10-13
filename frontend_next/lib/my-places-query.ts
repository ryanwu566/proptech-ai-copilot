import type { CommuteRouteResult } from "./api";
import type { MyPlace, PropertyOrigin } from "./my-places";
// @ts-expect-error Native Node runner requires source extension.
import { validOrigin, validPlace } from "./my-places.ts";
type Payload = { origin_latitude: number; origin_longitude: number; destination_address?: string; destination_latitude?: number; destination_longitude?: number; mode: MyPlace["transportMode"] };
function routePayload(origin: PropertyOrigin, place: MyPlace): Payload {
  return { origin_latitude: origin.latitude!, origin_longitude: origin.longitude!, mode: place.transportMode,
    ...(place.latitude !== undefined && place.longitude !== undefined
      ? { destination_latitude: place.latitude, destination_longitude: place.longitude }
      : { destination_address: (place.normalizedAddress ?? place.address).trim() }) };
}

/** This helper is inert until explicitly invoked by a calculation handler. No retry or background work. */
export function createExplicitRouteQuery(call: (payload: Payload, signal?: AbortSignal) => Promise<CommuteRouteResult>, options: { maxPending?: number; timeoutMs?: number } = {}) {
  const pending = new Map<string, Promise<CommuteRouteResult>>();
  const maxPending = Math.min(20, Math.max(1, options.maxPending ?? 20));
  const timeoutMs = Math.min(30_000, Math.max(1, options.timeoutMs ?? 30_000));
  return async (origin: PropertyOrigin, place: MyPlace): Promise<CommuteRouteResult> => {
    if (!validOrigin(origin) || !validPlace(place)) throw Error("invalid_route_inputs");
    const payload = routePayload(origin, place);
    const key = JSON.stringify(payload);
    let request = pending.get(key);
    if (!request) {
      if (pending.size >= maxPending) throw Error("route_capacity");
      const controller = new AbortController();
      let timer: ReturnType<typeof setTimeout>;
      request = new Promise<CommuteRouteResult>((resolve, reject) => {
        timer = setTimeout(() => { controller.abort(); reject(Error("route_timeout")); }, timeoutMs);
        // Finite wait even if a provider implementation ignores the abort signal.
        Promise.resolve(call(payload, controller.signal)).then(resolve, reject);
      }).finally(() => clearTimeout(timer));
      pending.set(key, request);
    }
    try { return await request; } finally { if (pending.get(key) === request) pending.delete(key); }
  };
}

/** Short-lived action scope: repeated destinations share results only within this explicit batch. */
export function createExplicitRouteBatch(query: (origin: PropertyOrigin, place: MyPlace) => Promise<CommuteRouteResult>) {
  const requests = new Map<string, Promise<CommuteRouteResult>>();
  return (origin: PropertyOrigin, place: MyPlace) => {
    if (!validOrigin(origin) || !validPlace(place)) return Promise.reject(new Error("invalid_route_inputs"));
    const key = JSON.stringify(routePayload(origin, place));
    let request = requests.get(key);
    if (!request) { request = query(origin, place); requests.set(key, request); }
    return request;
  };
}
