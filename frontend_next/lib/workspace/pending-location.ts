import type { SavedCase } from "../case-storage";
import type { LocationCandidate } from "./location-confirmation";
// @ts-expect-error Native TS runner extension.
import { interpretLocationResolution } from "./location-confirmation.ts";

/** Confirmation UI data only. This is never an identity anchor or downstream evidence. */
export type PendingLocationCandidate = {
  version: 1;
  state: "unconfirmed";
  caseId: string;
  addressKey: string;
  candidate: LocationCandidate;
};

export function caseLocationAddress(saved: SavedCase): string {
  return saved.data.journeyContext?.propertyContext.addressSummary?.trim()
    || [saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road].filter((part) => typeof part === "string" && part.trim()).join("");
}

/** Bind both editable address representations, even when the journey summary takes precedence. */
function addressKey(saved: SavedCase): string {
  return JSON.stringify([caseLocationAddress(saved), saved.inputSummary.city ?? null, saved.inputSummary.district ?? null, saved.inputSummary.road ?? null,
    saved.data.journeyContext?.propertyContext.city ?? null, saved.data.journeyContext?.propertyContext.district ?? null, saved.data.journeyContext?.propertyContext.road ?? null]);
}

export function capturePendingLocation(saved: SavedCase, value: LocationCandidate): PendingLocationCandidate | undefined {
  if (saved.data.propertyIdentityAnchor || value?.addressInput !== caseLocationAddress(saved)) return undefined;
  const result = interpretLocationResolution({ status: "resolved", confidence: "high", source: value.source, formatted_address: value.interpretedAddress,
    county: value.county, district: value.district, latitude: value.latitude, longitude: value.longitude, postal_code: value.postalCode ?? null }, value.addressInput);
  if (result.kind !== "candidate" || result.candidate.interpretedAddress !== value.interpretedAddress) return undefined;
  return { version: 1, state: "unconfirmed", caseId: saved.id, addressKey: addressKey(saved), candidate: result.candidate };
}

/** Malformed or foreign pending data is discarded without losing the case itself. */
export function restorePendingLocation(saved: SavedCase): PendingLocationCandidate | undefined {
  const pending = saved.data.pendingLocationCandidate;
  if (!pending || pending.version !== 1 || pending.state !== "unconfirmed" || pending.caseId !== saved.id || pending.addressKey !== addressKey(saved) || !pending.candidate) return undefined;
  return capturePendingLocation(saved, pending.candidate);
}
