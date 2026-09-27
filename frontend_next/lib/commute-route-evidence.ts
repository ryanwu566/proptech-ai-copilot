import type { CommuteRouteEvidence } from "@/lib/api";

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
