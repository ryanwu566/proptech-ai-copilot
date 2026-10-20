/** Bounded contextual evidence. No provider scores, ratings, addresses or opening hours. */
export const NEARBY_CATEGORIES = ["transport", "shopping", "food", "school", "medical", "park"] as const;
export const NEARBY_RADIUS_M = 800;
type Category = (typeof NEARBY_CATEGORIES)[number];
export type FacilityGroup = "transit" | "convenience" | "education" | "healthcare" | "parks";
type Point = { lat: number; lng: number };
type Facility = Point & { id: string; name: string; category: Category; distanceM: number };
export type NearbyFacilitiesEvidence = {
  version: 1;
  source: "google_places";
  origin: Point;
  radiusM: 800;
  checkedAt: string;
  partial: boolean;
  successfulCategories: Category[];
  places: Facility[];
};

const record = (value: unknown): Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
const category = (value: unknown): value is Category => NEARBY_CATEGORIES.includes(value as Category);
function point(value: unknown): Point | undefined {
  const p = record(value);
  return typeof p.lat === "number" && Number.isFinite(p.lat) && Math.abs(p.lat) <= 90
    && typeof p.lng === "number" && Number.isFinite(p.lng) && Math.abs(p.lng) <= 180 ? { lat: p.lat, lng: p.lng } : undefined;
}

function distance(a: Point, b: Point): number {
  const rad = Math.PI / 180;
  const h = Math.sin((a.lat - b.lat) * rad / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin((a.lng - b.lng) * rad / 2) ** 2;
  return Math.round(6371000 * 2 * Math.asin(Math.sqrt(Math.min(1, h))));
}

/** Capture the existing /map/nearby contract; distances always come from coordinates. */
export function captureNearbyFacilities(value: unknown, expectedOrigin: Point, now = () => new Date().toISOString()): NearbyFacilitiesEvidence {
  const data = record(value);
  const origin = point(data.center);
  if (!origin || !point(expectedOrigin) || Math.abs(origin.lat - expectedOrigin.lat) > 0.000001 || Math.abs(origin.lng - expectedOrigin.lng) > 0.000001
    || data.source !== "google_places" || data.fallback === true || data.radius_m !== NEARBY_RADIUS_M || !Array.isArray(data.categories)) throw new Error("unavailable_nearby_evidence");
  const failed = Array.isArray(data.failed_categories) ? data.failed_categories : [];
  const statuses = record(data.category_status);
  const successfulCategories: Category[] = [];
  const places: Facility[] = [];
  const seen = new Set<string>();
  for (const raw of data.categories) {
    const group = record(raw);
    if (!category(group.category) || successfulCategories.includes(group.category) || failed.includes(group.category)
      || (group.source !== undefined && group.source !== "google_places") || group.availability === "fallback"
      || (record(statuses[group.category]).status !== undefined && record(statuses[group.category]).status !== "available")
      || !Array.isArray(group.places)) continue;
    const key = group.category;
    successfulCategories.push(key);
    let count = 0;
    for (const rawPlace of group.places.slice(0, 100)) {
      const p = record(rawPlace);
      const coordinates = point(p);
      if (!coordinates || typeof p.name !== "string" || !p.name.trim() || (p.source !== undefined && p.source !== "google_places")) continue;
      const name = p.name.trim().slice(0, 160);
      const id = typeof p.place_id === "string" && p.place_id ? p.place_id.slice(0, 200) : `${name}:${coordinates.lat}:${coordinates.lng}`;
      const distanceM = distance(origin, coordinates);
      if (seen.has(id) || distanceM > NEARBY_RADIUS_M || count >= 10) continue;
      seen.add(id);
      places.push({ id, name, category: key, ...coordinates, distanceM });
      count++;
    }
  }
  const checkedAt = typeof data.checked_at === "string" && Number.isFinite(Date.parse(data.checked_at)) ? data.checked_at : now();
  return { version: 1, source: "google_places", origin, radiusM: NEARBY_RADIUS_M, checkedAt, partial: data.partial === true || successfulCategories.length < NEARBY_CATEGORIES.length, successfulCategories, places };
}

/** Revalidate and compact on every save/read so old or malformed storage stays bounded. */
export function normalizeNearbyFacilities(value: unknown): NearbyFacilitiesEvidence | undefined {
  const stored = record(value);
  if (stored.version !== 1 || stored.source !== "google_places" || stored.radiusM !== NEARBY_RADIUS_M || !point(stored.origin)
    || !Array.isArray(stored.successfulCategories) || !Array.isArray(stored.places)
    || typeof stored.checkedAt !== "string" || !Number.isFinite(Date.parse(stored.checkedAt))) return undefined;
  const categories = NEARBY_CATEGORIES.filter((key) => (stored.successfulCategories as unknown[]).includes(key)).map((key) => ({
    category: key,
    places: (stored.places as unknown[]).slice(0, 60).map(record).filter((p) => p.category === key).map((p) => ({ ...p, place_id: p.id })),
  }));
  try { return captureNearbyFacilities({ center: stored.origin, source: stored.source, radius_m: stored.radiusM, checked_at: stored.checkedAt, partial: stored.partial, categories }, point(stored.origin)!); }
  catch { return undefined; }
}

const GROUPS: Record<Category, FacilityGroup> = { transport: "transit", shopping: "convenience", food: "convenience", school: "education", medical: "healthcare", park: "parks" };
export function groupNearbyFacilities(evidence: NearbyFacilitiesEvidence): Array<{ category: FacilityGroup; places: Facility[] }> {
  return (["transit", "convenience", "education", "healthcare", "parks"] as const).flatMap((category) => {
    const places = evidence.places.filter((p) => GROUPS[p.category] === category).sort((a, b) => a.distanceM - b.distanceM);
    return places.length ? [{ category, places }] : [];
  });
}

const inFlight = new Map<string, Promise<unknown>>();
/** Share the whole acquisition + persistence operation across rapid clicks or remounts. */
export function shareNearbyAcquisition<T>(key: string, acquire: () => Promise<T>): Promise<T> {
  const existing = inFlight.get(key);
  if (existing) return existing as Promise<T>;
  const pending = acquire().finally(() => { if (inFlight.get(key) === pending) inFlight.delete(key); });
  inFlight.set(key, pending);
  return pending;
}
