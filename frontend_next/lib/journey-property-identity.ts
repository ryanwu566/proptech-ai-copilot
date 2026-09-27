import type { LocationInsightResult } from "@/lib/api";
import type { JourneyPropertyContext } from "@/lib/location-market-journey";

export type JourneyIdentityStatus =
  | "candidate"
  | "manual_confirmed"
  | "unresolved"
  | "unavailable"
  | "restricted"
  | "unsupported"
  | "error"
  | "stale";

export type JourneyIdentityConfidence = "high" | "medium" | "low" | "unknown";

export type JourneyIdentitySource = {
  source_id: string;
  kind: "user_selection" | "geocoding" | "administrative_boundary" | "manual_confirmation";
  checked_at: string;
};

export type JourneyIdentityCandidate = {
  candidate_id: string;
  display_value: string;
  source_id: string;
  confidence: JourneyIdentityConfidence;
  limitations: string[];
};

export type JourneyIdentitySubject = {
  status: Exclude<JourneyIdentityStatus, "stale">;
  candidate_id: string | null;
  candidates: JourneyIdentityCandidate[];
  source_id: string | null;
  confidence: JourneyIdentityConfidence;
  limitations: string[];
  confirmation: {
    status: "manual_confirmed";
    method: "manual";
    confirmed_at: string;
    source_candidate_id: string;
  } | null;
};

export type JourneyPropertyIdentityAnchorV1 = {
  version: 1;
  scope: "journey_browser_anchor";
  journey_anchor_id: string;
  address_input: string;
  normalized_address: string;
  coordinates: { latitude: number; longitude: number } | null;
  administrative_location: {
    city: string | null;
    district: string | null;
    village: string | null;
    village_code: string | null;
  };
  location_status: Extract<JourneyIdentityStatus, "candidate" | "unresolved" | "unavailable" | "unsupported" | "error" | "stale">;
  parcel: JourneyIdentitySubject;
  building: JourneyIdentitySubject;
  confidence: {
    level: JourneyIdentityConfidence;
    domain: "address_spatial_correlation";
    basis: string[];
    limitations: string[];
  };
  evidence: {
    sources: JourneyIdentitySource[];
    checked_at: string;
    limitations: string[];
  };
  revalidation: {
    status: "current" | "needs_revalidation";
    conflicts: Array<"normalized_address" | "coordinates" | "village_code" | "incomparable_identity">;
  };
};

type AnchorOptions = {
  now?: () => string;
  idFactory?: () => string;
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TRUSTED_GEOCODERS = new Set(["google_geocoding", "tgos_geocoding"]);
const CONFIDENCE_LIMITATION = "not_parcel_building_ownership_or_legal_boundary_confirmation";
const ANCHOR_LIMITATIONS = [
  "journey_browser_correlation_only",
  "not_a_government_or_vnext_property_identifier",
  CONFIDENCE_LIMITATION,
];

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function checkedAt(options: AnchorOptions): string {
  const selected = options.now?.() ?? new Date().toISOString();
  if (!Number.isFinite(Date.parse(selected))) throw new Error("Invalid identity evidence timestamp");
  return selected;
}

function opaqueAnchorId(options: AnchorOptions): string {
  const randomUuid = options.idFactory?.() ?? globalThis.crypto?.randomUUID?.();
  if (!randomUuid || !UUID_PATTERN.test(randomUuid)) throw new Error("A random UUID is required for a journey identity anchor");
  return `journey-browser-${randomUuid.toLowerCase()}`;
}

function unavailableSubject(kind: "parcel" | "building"): JourneyIdentitySubject {
  return {
    status: "unavailable",
    candidate_id: null,
    candidates: [],
    source_id: null,
    confidence: "unknown",
    limitations: [
      `no_approved_${kind}_identity_evidence`,
      "map_imagery_proximity_and_address_heuristics_are_not_identity_evidence",
    ],
    confirmation: null,
  };
}

function addressFromContext(context: JourneyPropertyContext): string {
  return text(context.addressSummary)
    ?? [context.city, context.district, context.road].map(text).filter((value): value is string => value !== null).join("");
}

function safeCoordinates(location: LocationInsightResult | undefined): { latitude: number; longitude: number } | null {
  const resolved = location?.resolved_location;
  if (!resolved || !Number.isFinite(resolved.latitude) || !Number.isFinite(resolved.longitude)) return null;
  if (resolved.latitude < -90 || resolved.latitude > 90 || resolved.longitude < -180 || resolved.longitude > 180) return null;
  return { latitude: resolved.latitude, longitude: resolved.longitude };
}

export function buildJourneyPropertyIdentityAnchor(
  input: { context: JourneyPropertyContext; location?: LocationInsightResult },
  options: AnchorOptions = {},
): JourneyPropertyIdentityAnchorV1 {
  const evidenceCheckedAt = checkedAt(options);
  const addressInput = addressFromContext(input.context);
  const acceptance = input.location?.geocoding_acceptance;
  const accepted = acceptance?.accepted_for_analysis === true;
  const sourceId = accepted ? text(acceptance.geocoding_source) : null;
  const trustedGeocoder = sourceId !== null && TRUSTED_GEOCODERS.has(sourceId);
  const coordinates = accepted ? safeCoordinates(input.location) : null;
  const village = input.location?.village_resolution;
  const villageResolved = village?.status === "resolved" && text(village.village) !== null && text(village.village_code) !== null;
  const normalizedAddress = accepted
    ? text(acceptance.normalized_address) ?? text(input.location?.resolved_location?.address_label) ?? addressInput
    : addressInput;
  const sources: JourneyIdentitySource[] = [];
  if (addressInput) sources.push({ source_id: "property_selection", kind: "user_selection", checked_at: evidenceCheckedAt });
  if (sourceId && coordinates) sources.push({ source_id: sourceId, kind: "geocoding", checked_at: evidenceCheckedAt });
  if (villageResolved && village?.source === "nlsc_village_boundary") {
    sources.push({ source_id: "nlsc_village_boundary", kind: "administrative_boundary", checked_at: evidenceCheckedAt });
  }

  const confidence: JourneyIdentityConfidence = !normalizedAddress
    ? "unknown"
    : trustedGeocoder && coordinates && villageResolved
      ? "high"
      : accepted && coordinates
        ? "medium"
        : "low";
  const basis = [
    normalizedAddress ? "normalized_address" : null,
    accepted && coordinates ? (trustedGeocoder ? "trusted_geocoding_coordinates" : "accepted_coordinates") : null,
    text(input.context.city) && text(input.context.district) ? "administrative_area" : null,
    villageResolved ? "resolved_village" : null,
  ].filter((value): value is string => value !== null);

  return {
    version: 1,
    scope: "journey_browser_anchor",
    journey_anchor_id: opaqueAnchorId(options),
    address_input: addressInput,
    normalized_address: normalizedAddress,
    coordinates,
    administrative_location: {
      city: text(village?.county) ?? text(input.context.city),
      district: text(village?.town) ?? text(input.context.district),
      village: villageResolved ? text(village?.village) : null,
      village_code: villageResolved ? text(village?.village_code) : null,
    },
    location_status: normalizedAddress ? "candidate" : "unresolved",
    parcel: unavailableSubject("parcel"),
    building: unavailableSubject("building"),
    confidence: {
      level: confidence,
      domain: "address_spatial_correlation",
      basis,
      limitations: [CONFIDENCE_LIMITATION],
    },
    evidence: {
      sources,
      checked_at: evidenceCheckedAt,
      limitations: [...ANCHOR_LIMITATIONS],
    },
    revalidation: { status: "current", conflicts: [] },
  };
}

type JsonRecord = Record<string, unknown>;

function record(value: unknown): JsonRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : null;
}

function hasOnlyKeys(value: JsonRecord, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function boundedString(value: unknown, maximum = 512): value is string {
  return typeof value === "string" && value.length <= maximum && !value.includes("\0");
}

function nullableBoundedString(value: unknown, maximum = 512): value is string | null {
  return value === null || boundedString(value, maximum);
}

function stringList(value: unknown, maximum = 32): value is string[] {
  return Array.isArray(value)
    && value.length <= maximum
    && value.every((item) => boundedString(item, 160));
}

function validTimestamp(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function validConfidence(value: unknown): value is JourneyIdentityConfidence {
  return value === "high" || value === "medium" || value === "low" || value === "unknown";
}

function validSubjectStatus(value: unknown): value is JourneyIdentitySubject["status"] {
  return value === "candidate"
    || value === "manual_confirmed"
    || value === "unresolved"
    || value === "unavailable"
    || value === "restricted"
    || value === "unsupported"
    || value === "error";
}

function normalizeCandidate(value: unknown): JourneyIdentityCandidate | null {
  const item = record(value);
  if (!item || !hasOnlyKeys(item, ["candidate_id", "display_value", "source_id", "confidence", "limitations"])) return null;
  if (
    !boundedString(item.candidate_id, 160)
    || !boundedString(item.display_value)
    || !boundedString(item.source_id, 160)
    || !validConfidence(item.confidence)
    || !stringList(item.limitations)
  ) return null;
  return {
    candidate_id: item.candidate_id,
    display_value: item.display_value,
    source_id: item.source_id,
    confidence: item.confidence,
    limitations: [...item.limitations],
  };
}

function normalizeSubject(value: unknown): JourneyIdentitySubject | null {
  const item = record(value);
  if (!item || !hasOnlyKeys(item, ["status", "candidate_id", "candidates", "source_id", "confidence", "limitations", "confirmation"])) return null;
  if (
    !validSubjectStatus(item.status)
    || !nullableBoundedString(item.candidate_id, 160)
    || !nullableBoundedString(item.source_id, 160)
    || !validConfidence(item.confidence)
    || !stringList(item.limitations)
    || !Array.isArray(item.candidates)
    || item.candidates.length > 16
  ) return null;
  const candidates = item.candidates.map(normalizeCandidate);
  if (candidates.some((candidate) => candidate === null)) return null;

  let confirmation: JourneyIdentitySubject["confirmation"] = null;
  if (item.confirmation !== null) {
    const selected = record(item.confirmation);
    if (
      !selected
      || !hasOnlyKeys(selected, ["status", "method", "confirmed_at", "source_candidate_id"])
      || selected.status !== "manual_confirmed"
      || selected.method !== "manual"
      || !validTimestamp(selected.confirmed_at)
      || !boundedString(selected.source_candidate_id, 160)
    ) return null;
    confirmation = {
      status: "manual_confirmed",
      method: "manual",
      confirmed_at: selected.confirmed_at,
      source_candidate_id: selected.source_candidate_id,
    };
  }
  if ((item.status === "manual_confirmed") !== (confirmation !== null)) return null;
  if (confirmation && item.candidate_id !== confirmation.source_candidate_id) return null;
  if (confirmation && !candidates.some((candidate) => candidate?.candidate_id === confirmation.source_candidate_id)) return null;

  return {
    status: item.status,
    candidate_id: item.candidate_id,
    candidates: candidates as JourneyIdentityCandidate[],
    source_id: item.source_id,
    confidence: item.confidence,
    limitations: [...item.limitations],
    confirmation,
  };
}

function normalizeSource(value: unknown): JourneyIdentitySource | null {
  const item = record(value);
  if (!item || !hasOnlyKeys(item, ["source_id", "kind", "checked_at"])) return null;
  if (
    !boundedString(item.source_id, 160)
    || !validTimestamp(item.checked_at)
    || !["user_selection", "geocoding", "administrative_boundary", "manual_confirmation"].includes(String(item.kind))
  ) return null;
  return {
    source_id: item.source_id,
    kind: item.kind as JourneyIdentitySource["kind"],
    checked_at: item.checked_at,
  };
}

export function normalizeJourneyPropertyIdentityAnchor(value: unknown): JourneyPropertyIdentityAnchorV1 | null {
  const item = record(value);
  if (!item || !hasOnlyKeys(item, [
    "version", "scope", "journey_anchor_id", "address_input", "normalized_address", "coordinates",
    "administrative_location", "location_status", "parcel", "building", "confidence", "evidence", "revalidation",
  ])) return null;
  if (
    item.version !== 1
    || item.scope !== "journey_browser_anchor"
    || typeof item.journey_anchor_id !== "string"
    || !new RegExp(`^journey-browser-${UUID_PATTERN.source.slice(1, -1)}$`, "i").test(item.journey_anchor_id)
    || !boundedString(item.address_input)
    || !boundedString(item.normalized_address)
    || !["candidate", "unresolved", "unavailable", "unsupported", "error", "stale"].includes(String(item.location_status))
  ) return null;

  let coordinates: JourneyPropertyIdentityAnchorV1["coordinates"] = null;
  if (item.coordinates !== null) {
    const selected = record(item.coordinates);
    if (
      !selected
      || !hasOnlyKeys(selected, ["latitude", "longitude"])
      || typeof selected.latitude !== "number"
      || typeof selected.longitude !== "number"
      || !Number.isFinite(selected.latitude)
      || !Number.isFinite(selected.longitude)
      || selected.latitude < -90
      || selected.latitude > 90
      || selected.longitude < -180
      || selected.longitude > 180
    ) return null;
    coordinates = { latitude: selected.latitude, longitude: selected.longitude };
  }

  const administrative = record(item.administrative_location);
  if (
    !administrative
    || !hasOnlyKeys(administrative, ["city", "district", "village", "village_code"])
    || !nullableBoundedString(administrative.city, 160)
    || !nullableBoundedString(administrative.district, 160)
    || !nullableBoundedString(administrative.village, 160)
    || !nullableBoundedString(administrative.village_code, 160)
  ) return null;

  const parcel = normalizeSubject(item.parcel);
  const building = normalizeSubject(item.building);
  const confidence = record(item.confidence);
  const evidence = record(item.evidence);
  const revalidation = record(item.revalidation);
  if (!parcel || !building || !confidence || !evidence || !revalidation) return null;
  if (
    !hasOnlyKeys(confidence, ["level", "domain", "basis", "limitations"])
    || !validConfidence(confidence.level)
    || confidence.domain !== "address_spatial_correlation"
    || !stringList(confidence.basis)
    || !stringList(confidence.limitations)
    || !hasOnlyKeys(evidence, ["sources", "checked_at", "limitations"])
    || !Array.isArray(evidence.sources)
    || evidence.sources.length > 8
    || !validTimestamp(evidence.checked_at)
    || !stringList(evidence.limitations)
    || !hasOnlyKeys(revalidation, ["status", "conflicts"])
    || !["current", "needs_revalidation"].includes(String(revalidation.status))
    || !Array.isArray(revalidation.conflicts)
    || revalidation.conflicts.some((conflict) => !["normalized_address", "coordinates", "village_code", "incomparable_identity"].includes(String(conflict)))
  ) return null;
  const sources = evidence.sources.map(normalizeSource);
  if (sources.some((source) => source === null)) return null;
  const normalizedSources = sources as JourneyIdentitySource[];
  if (confidence.level === "high") {
    const hasTrustedGeocoder = normalizedSources.some(
      (source) => source.kind === "geocoding" && TRUSTED_GEOCODERS.has(source.source_id),
    );
    const hasNlscVillage = normalizedSources.some(
      (source) => source.kind === "administrative_boundary" && source.source_id === "nlsc_village_boundary",
    );
    if (
      !item.normalized_address.trim()
      || !coordinates
      || !administrative.city
      || !administrative.district
      || !administrative.village
      || !administrative.village_code
      || !hasTrustedGeocoder
      || !hasNlscVillage
    ) return null;
  }

  return {
    version: 1,
    scope: "journey_browser_anchor",
    journey_anchor_id: item.journey_anchor_id,
    address_input: item.address_input,
    normalized_address: item.normalized_address,
    coordinates,
    administrative_location: {
      city: administrative.city,
      district: administrative.district,
      village: administrative.village,
      village_code: administrative.village_code,
    },
    location_status: item.location_status as JourneyPropertyIdentityAnchorV1["location_status"],
    parcel,
    building,
    confidence: {
      level: confidence.level,
      domain: "address_spatial_correlation",
      basis: [...confidence.basis],
      limitations: [...confidence.limitations],
    },
    evidence: {
      sources: normalizedSources,
      checked_at: evidence.checked_at,
      limitations: [...evidence.limitations],
    },
    revalidation: {
      status: revalidation.status as JourneyPropertyIdentityAnchorV1["revalidation"]["status"],
      conflicts: [...revalidation.conflicts] as JourneyPropertyIdentityAnchorV1["revalidation"]["conflicts"],
    },
  };
}

function comparableAddress(value: string): string {
  return value.normalize("NFKC").replace(/\s+/gu, "").toLocaleLowerCase("zh-TW");
}

function coordinateDistanceMetres(
  left: { latitude: number; longitude: number },
  right: { latitude: number; longitude: number },
): number {
  const radians = (degrees: number) => degrees * Math.PI / 180;
  const latitudeDelta = radians(right.latitude - left.latitude);
  const longitudeDelta = radians(right.longitude - left.longitude);
  const leftLatitude = radians(left.latitude);
  const rightLatitude = radians(right.latitude);
  const haversine = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(leftLatitude) * Math.cos(rightLatitude) * Math.sin(longitudeDelta / 2) ** 2;
  return 6_371_000 * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

function storedUuid(anchorId: string): string {
  return anchorId.slice("journey-browser-".length);
}

function staleAnchor(
  stored: JourneyPropertyIdentityAnchorV1,
  conflicts: JourneyPropertyIdentityAnchorV1["revalidation"]["conflicts"],
): JourneyPropertyIdentityAnchorV1 {
  return {
    ...stored,
    location_status: "stale",
    confidence: { ...stored.confidence, level: "unknown" },
    revalidation: { status: "needs_revalidation", conflicts },
  };
}

export function reconcileJourneyPropertyIdentityAnchor(
  storedValue: JourneyPropertyIdentityAnchorV1,
  context: JourneyPropertyContext,
  location: LocationInsightResult,
  options: Pick<AnchorOptions, "now"> = {},
): JourneyPropertyIdentityAnchorV1 {
  const stored = normalizeJourneyPropertyIdentityAnchor(storedValue);
  if (!stored) throw new Error("Invalid stored journey identity anchor");

  const resolvedCoordinates = safeCoordinates(location);
  const contextAddress = addressFromContext(context);
  const acceptedAddress = location.geocoding_acceptance?.accepted_for_analysis === true
    ? text(location.geocoding_acceptance.normalized_address)
    : null;

  const conflicts: JourneyPropertyIdentityAnchorV1["revalidation"]["conflicts"] = [];
  if (contextAddress && acceptedAddress && (
    comparableAddress(contextAddress) !== comparableAddress(stored.address_input)
    || comparableAddress(acceptedAddress) !== comparableAddress(stored.normalized_address)
  )) conflicts.push("normalized_address");
  else if (resolvedCoordinates && (!contextAddress || !acceptedAddress)) conflicts.push("incomparable_identity");

  // Provider precision is supporting evidence only after address compatibility.
  if (conflicts.length === 0 && stored.coordinates && resolvedCoordinates && coordinateDistanceMetres(stored.coordinates, resolvedCoordinates) > 100) {
    conflicts.push("coordinates");
  }
  const freshVillageCode = location.village_resolution?.status === "resolved"
    ? text(location.village_resolution.village_code)
    : null;
  if (
    freshVillageCode
    && stored.administrative_location.village_code
    && freshVillageCode !== stored.administrative_location.village_code
  ) conflicts.push("village_code");
  if (conflicts.length > 0) return staleAnchor(stored, conflicts);
  if (!resolvedCoordinates || !contextAddress || !acceptedAddress) return stored;

  const fresh = buildJourneyPropertyIdentityAnchor(
    { context, location },
    { ...options, idFactory: () => storedUuid(stored.journey_anchor_id) },
  );
  const sourceKey = (source: JourneyIdentitySource) => `${source.kind}:${source.source_id}`;
  const mergedSources = new Map(stored.evidence.sources.map((source) => [sourceKey(source), source]));
  for (const source of fresh.evidence.sources) mergedSources.set(sourceKey(source), source);
  return {
    ...fresh,
    journey_anchor_id: stored.journey_anchor_id,
    administrative_location: {
      ...fresh.administrative_location,
      village: fresh.administrative_location.village ?? stored.administrative_location.village,
      village_code: fresh.administrative_location.village_code ?? stored.administrative_location.village_code,
    },
    parcel: stored.parcel,
    building: stored.building,
    evidence: { ...fresh.evidence, sources: [...mergedSources.values()] },
    revalidation: { status: "current", conflicts: [] },
  };
}
