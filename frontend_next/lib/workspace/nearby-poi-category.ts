/**
 * Provider types[] → one deterministic product category → marker style.
 * Raw provider types and these ids never reach the UI; only localized labels do.
 */
export const NEARBY_POI_KINDS = ["rail", "bus", "transit", "education", "medical", "park", "shopping", "food", "other"] as const;
export type NearbyPoiKind = (typeof NEARBY_POI_KINDS)[number];
/** Filter groups. Transportation keeps bus / rail / other stations under one toggle. */
export const NEARBY_POI_GROUPS = ["transit", "education", "healthcare", "parks", "shopping", "food", "other"] as const;
export type NearbyPoiGroup = (typeof NEARBY_POI_GROUPS)[number];
/** The requested provider query a place came from (`/map/nearby` categories). */
export type NearbyQueryCategory = "transport" | "shopping" | "food" | "school" | "medical" | "park";

// First match wins. Specific transit modes outrank the generic station type, and
// facility categories outrank food so a hospital café is still medical.
const TYPE_RULES: ReadonlyArray<readonly [NearbyPoiKind, ReadonlySet<string>]> = [
  ["rail", new Set(["subway_station", "train_station", "light_rail_station"])],
  ["bus", new Set(["bus_station", "bus_stop"])],
  ["transit", new Set(["transit_station"])],
  ["medical", new Set(["hospital", "doctor", "medical_clinic", "dentist", "pharmacy"])],
  ["education", new Set(["school", "primary_school", "secondary_school", "university", "preschool"])],
  ["park", new Set(["park", "national_park", "garden"])],
  ["shopping", new Set(["shopping_mall", "supermarket", "convenience_store"])],
  ["food", new Set(["restaurant", "cafe"])],
];
const QUERY_DEFAULT: Record<NearbyQueryCategory, NearbyPoiKind> = { transport: "transit", school: "education", medical: "medical", park: "park", shopping: "shopping", food: "food" };
const KIND_QUERY: Record<NearbyPoiKind, NearbyQueryCategory | undefined> = { rail: "transport", bus: "transport", transit: "transport", education: "school", medical: "medical", park: "park", shopping: "shopping", food: "food", other: undefined };
const KIND_GROUP: Record<NearbyPoiKind, NearbyPoiGroup> = { rail: "transit", bus: "transit", transit: "transit", education: "education", medical: "healthcare", park: "parks", shopping: "shopping", food: "food", other: "other" };

export const isNearbyPoiKind = (value: unknown): value is NearbyPoiKind => NEARBY_POI_KINDS.includes(value as NearbyPoiKind);
export const nearbyPoiGroup = (kind: NearbyPoiKind): NearbyPoiGroup => KIND_GROUP[kind];

/**
 * Classify one place. Types are matched only within the query that returned the place, so a
 * provider tag can refine (bus vs rail) but never move a place into an unrelated category.
 * Missing types (older saved evidence) use the query default; unmatched types fall back to "other".
 */
export function classifyNearbyPlace(types: unknown, query: NearbyQueryCategory): NearbyPoiKind {
  if (!Array.isArray(types) || !types.some((item) => typeof item === "string" && item.trim())) return QUERY_DEFAULT[query];
  const normalized = new Set(types.filter((item): item is string => typeof item === "string").map((item) => item.trim().toLowerCase()));
  for (const [kind, accepted] of TYPE_RULES) if (KIND_QUERY[kind] === query && [...accepted].some((type) => normalized.has(type))) return kind;
  return "other";
}

/** A stored kind is trusted only when it is compatible with the query it was saved under. */
export function compatibleNearbyKind(kind: unknown, query: NearbyQueryCategory): NearbyPoiKind | undefined {
  return isNearbyPoiKind(kind) && (kind === "other" || KIND_QUERY[kind] === query) ? kind : undefined;
}

export type NearbyPoiStyle = { color: string; glyph: string };
/**
 * Hues continue the original map palette (transport blue, school violet, park green, medical rose,
 * shopping orange). Food moves to a darker ochre so it is not confused with shopping orange; every
 * fill keeps ≥3:1 against the white glyph and outline. Each kind also has its own glyph, so colour
 * is never the only cue.
 */
export const NEARBY_POI_STYLES: Record<NearbyPoiKind, NearbyPoiStyle> = {
  rail: { color: "#2563eb", glyph: '<rect x="7" y="4" width="10" height="11" rx="2.5"/><path d="M7 10h10M9 19l1.5-4M15 19l-1.5-4"/>' },
  bus: { color: "#0f766e", glyph: '<rect x="5.5" y="5" width="13" height="11" rx="2"/><path d="M5.5 11h13M8.5 19v-3M15.5 19v-3"/>' },
  transit: { color: "#0369a1", glyph: '<circle cx="12" cy="12" r="7"/><path d="M8.5 9.5h7M12 9.5V16"/>' },
  education: { color: "#7c3aed", glyph: '<path d="M3.5 10 12 6l8.5 4-8.5 4z"/><path d="M7 12v3.5c3 2 7 2 10 0V12"/>' },
  medical: { color: "#e11d48", glyph: '<path d="M12 5.5v13M5.5 12h13"/>' },
  park: { color: "#16a34a", glyph: '<path d="M12 4.5 17.5 13h-11z"/><path d="M12 13v6"/>' },
  shopping: { color: "#ea580c", glyph: '<rect x="6" y="9" width="12" height="10" rx="1.5"/><path d="M9.5 9V7.5a2.5 2.5 0 0 1 5 0V9"/>' },
  food: { color: "#a16207", glyph: '<path d="M8 4.5v5a2 2 0 0 0 2 2M12 4.5v5a2 2 0 0 1-2 2v8M16 4.5c-1.5 1.5-1.8 5 0 7v8"/>' },
  other: { color: "#64748b", glyph: '<circle cx="12" cy="12" r="2.5"/>' },
};
export const NEARBY_PROPERTY_STYLE: NearbyPoiStyle = { color: "#0f172a", glyph: '<path d="M4.5 11.5 12 5l7.5 6.5"/><path d="M6.5 10v9h11v-9M10.5 19v-5h3v5"/>' };

/** Inline SVG for a legend swatch or marker; static, trusted strings only. */
export function nearbyPoiIconSvg(style: NearbyPoiStyle, size: number, shape: "circle" | "pin" = "circle"): string {
  const body = shape === "pin"
    ? `<rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="${style.color}" stroke="#fbbf24" stroke-width="2"/>`
    : `<circle cx="12" cy="12" r="10.5" fill="${style.color}" stroke="#fff" stroke-width="1.5"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true" focusable="false">${body}<g fill="none" stroke="#fff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" transform="translate(12 12) scale(.72) translate(-12 -12)">${style.glyph}</g></svg>`;
}
