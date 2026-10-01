import type { CommuteAddressLookupResult, CommuteRouteEvidence } from "@/lib/api";

/** Persist only the bounded route provenance contract, never provider payloads. */
export function compactCommuteRouteEvidence(value: CommuteRouteEvidence | undefined): CommuteRouteEvidence | undefined {
  if (!value) return undefined;
  return {
    source: value.source,
    origin: { latitude: value.origin.latitude, longitude: value.origin.longitude },
    destination: { address: value.destination.address },
    mode: value.mode,
    distance_m: value.distance_m,
    duration_seconds: value.duration_seconds,
    duration_min: value.duration_min,
    checked_at: value.checked_at,
    reason_code: value.reason_code,
    status: value.status,
    partial: value.partial,
    fallback: value.fallback,
  };
}

/** Persist only the bounded TDX context contract, never provider payloads or messages. */
export function compactCommuteTransitEvidence(value: CommuteAddressLookupResult | undefined): CommuteAddressLookupResult | undefined {
  if (!value) return undefined;
  return {
    status: value.status,
    source: value.source,
    station_name: value.station_name,
    line_ids: Array.isArray(value.line_ids) ? value.line_ids.filter((line) => typeof line === "string").slice(0, 16) : [],
    distance_meters: value.distance_meters,
    source_updated_at: value.source_updated_at,
    snapshot_generated_at: value.snapshot_generated_at,
    message: value.status,
  };
}
