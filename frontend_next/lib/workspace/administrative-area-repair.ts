import type { SavedCase } from "../case-storage";
import type { JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity";
import type { LocationCandidate } from "./location-confirmation";
// @ts-expect-error Native TS runner extension.
import { areJourneyPropertyAddressesEquivalent, hasCompleteAdministrativeArea, normalizeJourneyPropertyIdentityAnchor } from "../journey-property-identity.ts";
// @ts-expect-error Native TS runner extension.
import { administrativeParts, interpretLocationResolution } from "./location-confirmation.ts";
// @ts-expect-error Native TS runner extension.
import { caseLocationAddress } from "./pending-location.ts";

export type AdministrativeAreaRepairPlan =
  | { kind: "write"; anchor: JourneyPropertyIdentityAnchorV1 }
  | { kind: "blocked"; reason: "case_changed" | "invalid_anchor" };

/** Administrative repair never replaces the confirmed spatial identity. */
export function planAdministrativeAreaRepair(current: SavedCase | undefined, candidate: LocationCandidate, expectedVersion: string, checkedAt: string): AdministrativeAreaRepairPlan {
  if (!current || JSON.stringify(current) !== expectedVersion) return { kind: "blocked", reason: "case_changed" };
  const anchor = normalizeJourneyPropertyIdentityAnchor(current.data.propertyIdentityAnchor);
  const invalid = { kind: "blocked", reason: "invalid_anchor" } as const;
  if (!anchor?.coordinates || hasCompleteAdministrativeArea(anchor) || anchor.revalidation.status !== "current"
    || anchor.revalidation.conflicts.length || anchor.location_status === "stale"
    || !["medium", "high"].includes(anchor.confidence.level) || !Number.isFinite(Date.parse(checkedAt))) return invalid;
  // Repair cannot resolve an ambiguous legacy identity by assigning new geography.
  const originalArea = administrativeParts(anchor.normalized_address);
  if (!originalArea.county || !originalArea.district) return invalid;
  if (candidate.addressInput !== anchor.address_input || !areJourneyPropertyAddressesEquivalent(caseLocationAddress(current), anchor.address_input)
    || !areJourneyPropertyAddressesEquivalent(candidate.interpretedAddress, anchor.normalized_address)) return invalid;
  const result = interpretLocationResolution({ status: "resolved", confidence: "high", source: candidate.source,
    formatted_address: candidate.interpretedAddress, latitude: candidate.latitude, longitude: candidate.longitude,
    county: candidate.county, district: candidate.district }, anchor.normalized_address);
  if (result.kind !== "candidate" || !result.candidate.county || !result.candidate.district
    || Math.abs(candidate.latitude - anchor.coordinates.latitude) > 0.000001
    || Math.abs(candidate.longitude - anchor.coordinates.longitude) > 0.000001) return invalid;
  const city = result.candidate.county.replaceAll("台", "臺");
  const district = result.candidate.district.replaceAll("台", "臺");
  for (const [key, value] of [["city", city], ["district", district]] as const) {
    const previous = anchor.administrative_location[key]?.trim().replaceAll("台", "臺");
    if (previous && previous !== value) return invalid;
  }
  const repaired = normalizeJourneyPropertyIdentityAnchor({ ...anchor,
    administrative_location: { ...anchor.administrative_location, city, district },
    confidence: { ...anchor.confidence, basis: [...new Set([...anchor.confidence.basis, "administrative_area"])] },
    evidence: { ...anchor.evidence, checked_at: checkedAt, sources: [...anchor.evidence.sources,
      { source_id: candidate.source === "google" ? "google_geocoding" : "tgos_geocoding", kind: "geocoding", checked_at: checkedAt },
      { source_id: "administrative_area_recheck", kind: "manual_confirmation", checked_at: checkedAt }] },
  });
  return repaired ? { kind: "write", anchor: repaired } : invalid;
}
