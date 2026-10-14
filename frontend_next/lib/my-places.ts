import type { CommuteRouteMode, CommuteRouteResult } from "./api";

export const PLACES_KEY = "proptech.my-places.v1";
export const ROUTES_KEY = "proptech.case-commute.v1";
export const MAX_PLACES = 20;
export const CATEGORIES = ["work", "partner_work", "family", "school", "childcare", "healthcare", "fitness", "shopping", "custom"] as const;
export const MODES = ["driving", "transit", "walking"] as const;
export type MyPlace = {
  id: string; label: string; category: typeof CATEGORIES[number]; address: string;
  normalizedAddress?: string; latitude?: number; longitude?: number;
  transportMode: CommuteRouteMode; weeklyTrips: number; priority: "important" | "secondary";
  createdAt: string; updatedAt: string;
};
export type PropertyOrigin = { caseId: string; identity: string; address: string; latitude: number | null; longitude: number | null; confirmed: boolean };
export type RouteStatus = "NOT_CHECKED" | "LOADING" | "AVAILABLE" | "UNAVAILABLE" | "STALE";
export type StoredRoute = {
  key: string; caseId: string; placeId: string; propertyFingerprint: string; destinationFingerprint: string;
  propertyAddress: string; destinationAddress: string; requestedMode: CommuteRouteMode;
  source: CommuteRouteResult["source"]; mode: CommuteRouteMode; status: CommuteRouteResult["status"];
  durationMinutes: number | null; distanceM: number | null; checkedAt: string;
  reasonCode: CommuteRouteResult["reason_code"]; partial: boolean; fallback: boolean;
};
export type DestinationFact = { place: MyPlace; status: RouteStatus; route: StoredRoute | null; weeklyMinutes: number | null };
export type CommuteComparisonSummary = { knownWeeklyMinutes: number; knownDestinationsCount: number; unknownPlaceIds: string[]; destinations: DestinationFact[] };
export type LocalStoragePort = Pick<Storage, "getItem" | "setItem">;
type RouteData = { version: 1; routes: StoredRoute[]; selections: Record<string, string[]> };
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const text = (value: unknown, max = 300): value is string => typeof value === "string" && value.trim().length > 0 && value.length <= max;
const date = (value: unknown): value is string => typeof value === "string" && Number.isFinite(Date.parse(value));
const mode = (value: unknown): value is CommuteRouteMode => MODES.includes(value as CommuteRouteMode);
export function validPlace(value: unknown): value is MyPlace {
  if (!value || typeof value !== "object") return false;
  const p = value as MyPlace;
  return text(p.id, 100) && text(p.label, 100) && text(p.address) && CATEGORIES.includes(p.category)
    && mode(p.transportMode) && Number.isInteger(p.weeklyTrips) && p.weeklyTrips >= 0 && p.weeklyTrips <= 21
    && ["important", "secondary"].includes(p.priority) && date(p.createdAt) && date(p.updatedAt)
    && (p.normalizedAddress === undefined || text(p.normalizedAddress))
    && (p.latitude === undefined && p.longitude === undefined || finite(p.latitude) && Math.abs(p.latitude) <= 90 && finite(p.longitude) && Math.abs(p.longitude) <= 180);
}
function validPlaces(value: unknown): value is MyPlace[] {
  return Array.isArray(value) && value.length <= MAX_PLACES && value.every(validPlace) && new Set(value.map((p) => p.id)).size === value.length;
}
function compactPlace(p: MyPlace): MyPlace {
  return { id: p.id, label: p.label, category: p.category, address: p.address, transportMode: p.transportMode,
    weeklyTrips: p.weeklyTrips, priority: p.priority, createdAt: p.createdAt, updatedAt: p.updatedAt,
    ...(p.normalizedAddress !== undefined ? { normalizedAddress: p.normalizedAddress } : {}),
    ...(p.latitude !== undefined ? { latitude: p.latitude, longitude: p.longitude } : {}) };
}
export function browserStorage(): LocalStoragePort {
  return { getItem: (key) => window.localStorage.getItem(key), setItem: (key, value) => window.localStorage.setItem(key, value) };
}
export function createPlacesStore(storage: LocalStoragePort) {
  function read(): { places: MyPlace[]; error: boolean } {
    try {
      const raw = storage.getItem(PLACES_KEY);
      if (raw === null) return { places: [], error: false };
      if (raw.length > 100_000) throw Error("size");
      const data = JSON.parse(raw);
      if (data.version !== 1 || !validPlaces(data.places)) throw Error("schema");
      return { places: data.places.map(compactPlace), error: false };
    } catch { return { places: [], error: true }; }
  }
  return { read, save(places: MyPlace[]) {
    if (!validPlaces(places) || read().error) return false;
    try { storage.setItem(PLACES_KEY, JSON.stringify({ version: 1, places: places.map(compactPlace) })); return true; } catch { return false; }
  } };
}
export function updatePlace(places: MyPlace[], id: string, updates: Partial<Omit<MyPlace, "id" | "createdAt">>, now: string): MyPlace[] {
  return places.map((p) => p.id === id ? { ...p, ...updates, id: p.id, createdAt: p.createdAt, updatedAt: now } : p);
}
export function deletePlace(places: MyPlace[], id: string): MyPlace[] { return places.filter((p) => p.id !== id); }
export function movePlace(places: MyPlace[], id: string, delta: -1 | 1): MyPlace[] {
  const next = [...places]; const index = next.findIndex((p) => p.id === id); const target = index + delta;
  if (index >= 0 && target >= 0 && target < next.length) [next[index], next[target]] = [next[target], next[index]];
  return next;
}
export function propertyFingerprint(origin: PropertyOrigin): string {
  return JSON.stringify([origin.identity, origin.address, origin.latitude, origin.longitude, origin.confirmed]);
}
export function destinationFingerprint(place: MyPlace): string {
  return JSON.stringify([place.address, place.normalizedAddress ?? null, place.latitude ?? null, place.longitude ?? null]);
}
export function routeKey(origin: PropertyOrigin, place: MyPlace): string {
  return JSON.stringify([origin.caseId, place.id, propertyFingerprint(origin), destinationFingerprint(place), place.transportMode]);
}
export function validOrigin(o: PropertyOrigin): boolean {
  return o.confirmed && finite(o.latitude) && Math.abs(o.latitude) <= 90 && finite(o.longitude) && Math.abs(o.longitude) <= 180;
}
export function makeStoredRoute(origin: PropertyOrigin, place: MyPlace, result: Omit<CommuteRouteResult, "message" | "disclaimer">): StoredRoute {
  const validNumeric = (value: unknown) => finite(value) && value >= 0 ? value : null;
  return {
    key: routeKey(origin, place), caseId: origin.caseId, placeId: place.id,
    propertyFingerprint: propertyFingerprint(origin), destinationFingerprint: destinationFingerprint(place),
    propertyAddress: origin.address, destinationAddress: place.address, requestedMode: place.transportMode,
    source: ["google_routes", "mock", "none"].includes(result.source) ? result.source : "none",
    mode: mode(result.mode) ? result.mode : place.transportMode,
    status: mode(result.mode) && ["resolved", "unresolved", "unavailable"].includes(result.status) ? result.status : "unavailable",
    durationMinutes: validNumeric(result.duration_min), distanceM: validNumeric(result.distance_m),
    checkedAt: date(result.checked_at) ? result.checked_at : "",
    reasonCode: mode(result.mode) && ["destination_required", "invalid_input", "provider_timeout", "configuration_error", "provider_error", "malformed_response", "route_not_found", "success"].includes(result.reason_code) ? result.reason_code : "malformed_response",
    partial: result.partial !== false, fallback: result.fallback !== false,
  };
}
function validRoute(value: unknown): value is StoredRoute {
  if (!value || typeof value !== "object") return false;
  const r = value as StoredRoute;
  return text(r.key, 3000) && text(r.caseId, 100) && text(r.placeId, 100)
    && text(r.propertyFingerprint, 1000) && text(r.destinationFingerprint, 1000)
    && text(r.propertyAddress) && text(r.destinationAddress) && mode(r.mode) && mode(r.requestedMode)
    && ["google_routes", "mock", "none"].includes(r.source) && ["resolved", "unresolved", "unavailable"].includes(r.status)
    && (r.durationMinutes === null || finite(r.durationMinutes) && r.durationMinutes >= 0)
    && (r.distanceM === null || finite(r.distanceM) && r.distanceM >= 0)
    && (r.checkedAt === "" || date(r.checkedAt)) && typeof r.partial === "boolean" && typeof r.fallback === "boolean"
    && ["destination_required", "invalid_input", "provider_timeout", "configuration_error", "provider_error", "malformed_response", "route_not_found", "success"].includes(r.reasonCode)
    && r.key === JSON.stringify([r.caseId, r.placeId, r.propertyFingerprint, r.destinationFingerprint, r.requestedMode]);
}
function compactRoute(r: StoredRoute): StoredRoute {
  return { key: r.key, caseId: r.caseId, placeId: r.placeId, propertyFingerprint: r.propertyFingerprint,
    destinationFingerprint: r.destinationFingerprint, propertyAddress: r.propertyAddress, destinationAddress: r.destinationAddress,
    requestedMode: r.requestedMode, source: r.source, mode: r.mode, status: r.status, durationMinutes: r.durationMinutes,
    distanceM: r.distanceM, checkedAt: r.checkedAt, reasonCode: r.reasonCode, partial: r.partial, fallback: r.fallback };
}
export function createRoutesStore(storage: LocalStoragePort) {
  function read(): RouteData & { error: boolean } {
    try {
      const raw = storage.getItem(ROUTES_KEY);
      if (raw === null) return { version: 1, routes: [], selections: {}, error: false };
      if (raw.length > 1_000_000) throw Error("size");
      const data = JSON.parse(raw);
      if (data.version !== 1 || !Array.isArray(data.routes) || data.routes.length > 200 || !data.routes.every(validRoute)
        || !data.selections || typeof data.selections !== "object" || Array.isArray(data.selections)
        || Object.keys(data.selections).length > 100 || !Object.entries(data.selections).every(([key, ids]) => text(key, 100) && Array.isArray(ids) && ids.length <= MAX_PLACES && ids.every((id) => text(id, 100)) && new Set(ids).size === ids.length)) throw Error("schema");
      return { version: 1, routes: data.routes.map(compactRoute), selections: data.selections, error: false };
    } catch { return { version: 1, routes: [], selections: {}, error: true }; }
  }
  function write(data: RouteData) {
    try { storage.setItem(ROUTES_KEY, JSON.stringify(data)); return true; } catch { return false; }
  }
  return { read, put(route: StoredRoute) {
    const data = read(); if (data.error || !validRoute(route)) return false;
    return write({ version: 1, routes: [...data.routes.filter((r) => r.key !== route.key), compactRoute(route)].slice(-200), selections: data.selections });
  }, select(caseId: string, ids: string[]) {
    const data = read(); if (data.error || !text(caseId, 100) || ids.length > MAX_PLACES || !ids.every((id) => text(id, 100)) || new Set(ids).size !== ids.length) return false;
    const entries = Object.entries(data.selections).filter(([key]) => key !== caseId).slice(-99);
    return write({ version: 1, routes: data.routes, selections: Object.fromEntries([...entries, [caseId, ids]]) });
  } };
}
export function buildCommuteComparisonSummary(origin: PropertyOrigin, places: MyPlace[], routes: StoredRoute[]): CommuteComparisonSummary {
  const destinations = places.map((place): DestinationFact => {
    const candidates = routes.filter((r) => r.caseId === origin.caseId && r.placeId === place.id);
    const current = candidates.findLast((r) => r.key === routeKey(origin, place));
    const route = current ?? candidates.at(-1) ?? null;
    const available = current && validOrigin(origin) && current.status === "resolved" && current.reasonCode === "success" && current.source === "google_routes"
      && !current.partial && !current.fallback && current.mode === place.transportMode && finite(current.durationMinutes) && current.durationMinutes >= 0 && date(current.checkedAt);
    const status = !route ? "NOT_CHECKED" : !current ? "STALE" : available ? "AVAILABLE" : "UNAVAILABLE";
    return { place, route, status, weeklyMinutes: available ? current.durationMinutes! * 2 * place.weeklyTrips : null };
  });
  return { destinations, knownWeeklyMinutes: destinations.reduce((sum, d) => sum + (d.weeklyMinutes ?? 0), 0),
    knownDestinationsCount: destinations.filter((d) => d.weeklyMinutes !== null).length,
    unknownPlaceIds: destinations.filter((d) => d.weeklyMinutes === null).map((d) => d.place.id) };
}
