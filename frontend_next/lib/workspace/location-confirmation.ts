import type { LocationInsightResult, LocationResolveResult } from "../api";
import type { JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity";
import type { SavedCase } from "../case-storage";
import type { PropertyCaseWorkspace } from "./workspace-model";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildJourneyPropertyIdentityAnchor, normalizeJourneyPropertyIdentityAnchor } from "../journey-property-identity.ts";

/**
 * In-case location confirmation for an address-only case.
 * Step 1 interprets ONE geocode-only /location/resolve result as unconfirmed UI data.
 * Step 2 builds the identity anchor only after the user explicitly confirms it.
 * Geocoder confidence never confirms anything on its own.
 */
export type LocationCandidate = {
  addressInput: string;
  interpretedAddress: string;
  county: string | null;
  district: string | null;
  latitude: number;
  longitude: number;
  source: "tgos" | "google";
};
export type LocationCandidateBlock = "unresolved" | "unavailable" | "capacity_unavailable" | "provider_unavailable" | "invalid" | "low_confidence" | "missing_coordinates";
export type LocationCandidateResult = { kind: "candidate"; candidate: LocationCandidate } | { kind: "blocked"; reason: LocationCandidateBlock | "case_changed" | "already_identified" | "invalid_anchor" | "write_failed" | "lock_unavailable" | "storage_unavailable" };

const GEOCODER_SOURCE_IDS = { tgos: "tgos_geocoding", google: "google_geocoding" } as const;
// Taiwan, Penghu, Kinmen and Matsu; anything outside is not this product's property.
const TAIWAN_BOUNDS = { minLatitude: 21.7, maxLatitude: 26.5, minLongitude: 118, maxLongitude: 122.2 };

/** Only a case that was never located can be located here; revalidation keeps its own flow. */
export function needsLocationConfirmation(workspace: Pick<PropertyCaseWorkspace, "identity">): boolean {
  return workspace.identity.state === "unconfirmed" && workspace.identity.anchor === null;
}

function boundedText(value: unknown, maximum: number): string | null {
  return typeof value === "string" && value.trim() && value.trim().length <= maximum ? value.trim() : null;
}

export function locationRequestFailure(status?: number): LocationCandidateBlock {
  return status === 429 ? "capacity_unavailable" : status === 503 ? "provider_unavailable" : "unavailable";
}

/** One explicitly requested lookup, with the same truth and error semantics at Home and in-case retry. */
export const LOCATION_RESOLVE_TIMEOUT_MS = 10_000;
export async function acquireLocationResolution(address: string, acquire: (signal: AbortSignal) => Promise<unknown>, options: { timeoutMs?: number; signal?: AbortSignal } = {}): Promise<LocationCandidateResult> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  const cancelled = new Promise<never>((_, reject) => {
    controller.signal.addEventListener("abort", () => reject(new Error("Location lookup stopped")), { once: true });
  });
  options.signal?.addEventListener("abort", abort, { once: true });
  if (options.signal?.aborted) abort();
  const timer = setTimeout(abort, options.timeoutMs ?? LOCATION_RESOLVE_TIMEOUT_MS);
  try {
    return interpretLocationResolution(await Promise.race([cancelled, controller.signal.aborted ? cancelled : acquire(controller.signal)]), address);
  } catch (error) {
    const status = error instanceof Error && "status" in error && typeof error.status === "number" ? error.status : undefined;
    return { kind: "blocked", reason: locationRequestFailure(status) };
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", abort);
  }
}

/** Confirm only trusted, high-confidence Taiwan coordinates; administrative completeness is independent. */
export function interpretLocationResolution(value: unknown, addressInput: string): LocationCandidateResult {
  if (!value || typeof value !== "object" || Array.isArray(value)) return { kind: "blocked", reason: "invalid" };
  const result = value as Partial<LocationResolveResult>;
  if (result.status === "unresolved") return { kind: "blocked", reason: "unresolved" };
  if (result.status === "unavailable") return { kind: "blocked", reason: "unavailable" };
  if (result.status !== "resolved" || (result.source !== "tgos" && result.source !== "google")) return { kind: "blocked", reason: "invalid" };
  // The resolver reports "high" only for trusted accepted geocodes; "unknown" is never promoted.
  if (result.confidence !== "high") return { kind: "blocked", reason: "low_confidence" };
  const { latitude, longitude } = result;
  if (typeof latitude !== "number" || typeof longitude !== "number" || !Number.isFinite(latitude) || !Number.isFinite(longitude)) return { kind: "blocked", reason: "missing_coordinates" };
  if (latitude < TAIWAN_BOUNDS.minLatitude || latitude > TAIWAN_BOUNDS.maxLatitude || longitude < TAIWAN_BOUNDS.minLongitude || longitude > TAIWAN_BOUNDS.maxLongitude) return { kind: "blocked", reason: "invalid" };
  const county = boundedText(result.county, 20);
  const district = boundedText(result.district, 20);
  const input = boundedText(addressInput, 500);
  if (!input) return { kind: "blocked", reason: "invalid" };
  return { kind: "candidate", candidate: { addressInput: input, interpretedAddress: boundedText(result.formatted_address, 500) ?? input, county, district, latitude, longitude, source: result.source } };
}

/** Explicit user confirmation → the same browser-anchor contract the guided journey produces. */
export function buildConfirmedLocationAnchor(candidate: LocationCandidate, options: { now: () => string; idFactory: () => string }): JourneyPropertyIdentityAnchorV1 | null {
  const anchor = buildJourneyPropertyIdentityAnchor({
    context: { addressSummary: candidate.addressInput, city: candidate.county ?? undefined, district: candidate.district ?? undefined, sourceLabel: "使用者確認", selectionStatus: "selected" },
    // Only the geocode fields the anchor builder reads; no nearby, village or demographic evidence exists here.
    location: {
      resolved_location: { address_label: candidate.interpretedAddress, latitude: candidate.latitude, longitude: candidate.longitude, geocoding_confidence: "high" },
      geocoding_acceptance: { accepted_for_analysis: true, geocoding_source: GEOCODER_SOURCE_IDS[candidate.source], normalized_address: candidate.interpretedAddress },
    } as unknown as LocationInsightResult,
  }, options);
  const normalized = normalizeJourneyPropertyIdentityAnchor(anchor);
  return normalized?.coordinates ? normalized : null;
}

export type IdentityConfirmationBlock = "case_changed" | "already_identified" | "invalid_anchor";

/** Pure compare-and-swap decision made inside the storage lock. */
export function planIdentityConfirmation(current: SavedCase | undefined, anchor: unknown, expectedVersion: string): { kind: "write"; anchor: JourneyPropertyIdentityAnchorV1 } | { kind: "blocked"; reason: IdentityConfirmationBlock } {
  if (!current || JSON.stringify(current) !== expectedVersion) return { kind: "blocked", reason: "case_changed" };
  if (current.data.propertyIdentityAnchor) return { kind: "blocked", reason: "already_identified" };
  const normalized = normalizeJourneyPropertyIdentityAnchor(anchor);
  // Same identity address the workspace adapter compares against (journey summary, else saved address parts).
  const addressInput = current.data.journeyContext?.propertyContext.addressSummary?.trim()
    || [current.inputSummary.city, current.inputSummary.district, current.inputSummary.road].filter((part) => typeof part === "string" && part.trim()).join("");
  if (!normalized?.coordinates || normalized.revalidation.status !== "current" || !addressInput || normalized.address_input !== addressInput) return { kind: "blocked", reason: "invalid_anchor" };
  return { kind: "write", anchor: normalized };
}
