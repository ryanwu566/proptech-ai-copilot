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
  /** Optional provider evidence; never identity on its own. */
  postalCode?: string | null;
  /** The user's address named no county; the candidate's county is the provider's and must be checked. */
  countyUnverified?: boolean;
};
/** A provider result shown only so the user can see why it cannot be confirmed. */
export type RejectedLocationCandidate = {
  interpretedAddress: string;
  county: string | null;
  district: string | null;
  latitude: number;
  longitude: number;
  source: "tgos" | "google";
  blockReason: "administrative_mismatch" | "address_mismatch" | "low_precision";
};
export type LocationCandidateBlock = "unresolved" | "unavailable" | "capacity_unavailable" | "provider_unavailable" | "invalid" | "low_confidence" | "missing_coordinates" | "administrative_mismatch" | "address_mismatch" | "low_precision";
export type LocationCandidateResult =
  | { kind: "candidate"; candidate: LocationCandidate }
  | { kind: "choice"; candidates: LocationCandidate[] }
  | { kind: "blocked"; reason: LocationCandidateBlock | "case_changed" | "already_identified" | "invalid_anchor" | "write_failed" | "lock_unavailable" | "storage_unavailable"; rejected?: RejectedLocationCandidate[] };
export const MAX_LOCATION_CANDIDATES = 5;

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

export const LOCATION_RESOLUTION_TIMEOUT_MS = 10_000;

/** One explicit lookup. The deadline settles even if the transport ignores abort. */
export async function acquireLocationResolution(address: string, acquire: (signal: AbortSignal) => Promise<unknown>, signal?: AbortSignal): Promise<LocationCandidateResult> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  let rejectAbort!: (reason: Error) => void;
  const aborted = new Promise<never>((_, reject) => { rejectAbort = reject; });
  const onAbort = () => rejectAbort(new Error("Location lookup ended"));
  controller.signal.addEventListener("abort", onAbort, { once: true });
  signal?.addEventListener("abort", cancel, { once: true });
  const deadline = setTimeout(cancel, LOCATION_RESOLUTION_TIMEOUT_MS);
  try {
    if (signal?.aborted) controller.abort();
    return interpretLocationResolution(await Promise.race([aborted, controller.signal.aborted ? aborted : acquire(controller.signal)]), address);
  } catch (error) {
    const status = error instanceof Error && "status" in error && typeof error.status === "number" ? error.status : undefined;
    return { kind: "blocked", reason: locationRequestFailure(status) };
  } finally {
    clearTimeout(deadline);
    signal?.removeEventListener("abort", cancel);
    controller.signal.removeEventListener("abort", onAbort);
  }
}

/** Shared bounded administrative-prefix check; does not infer geography from coordinates. */
export function administrativeParts(address: string): { county?: string; district?: string } {
  let text = address.replaceAll("台", "臺").replace(/[\s,，、。]/g, "").replace(/^[0-9０-９]{3,6}/, "").replace(/^(臺灣|中華民國)/, "").replace(/^[0-9０-９]{3,6}/, "");
  const county = text.match(/^(臺北市|新北市|桃園市|臺中市|臺南市|高雄市|基隆市|新竹市|嘉義市|新竹縣|苗栗縣|彰化縣|南投縣|雲林縣|嘉義縣|屏東縣|宜蘭縣|花蓮縣|臺東縣|澎湖縣|金門縣|連江縣)/)?.[0];
  if (county) text = text.slice(county.length);
  return { county, district: text.match(/^([\u4e00-\u9fff]{1,8}?[區鄉鎮]|[\u4e00-\u9fff]{1,8}?市)(?![區鄉鎮路街])/)?.[0] };
}

const BLOCK_REASONS = ["administrative_mismatch", "address_mismatch", "low_precision"] as const;
const inTaiwan = (latitude: number, longitude: number) => latitude >= TAIWAN_BOUNDS.minLatitude && latitude <= TAIWAN_BOUNDS.maxLatitude && longitude >= TAIWAN_BOUNDS.minLongitude && longitude <= TAIWAN_BOUNDS.maxLongitude;
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

function rejectedCandidates(value: unknown): RejectedLocationCandidate[] {
  return (Array.isArray(value) ? value : []).slice(0, MAX_LOCATION_CANDIDATES).flatMap((raw): RejectedLocationCandidate[] => {
    const item = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
    const blockReason = BLOCK_REASONS.find((reason) => reason === item.block_reason);
    const address = boundedText(item.formatted_address, 500);
    if (item.confirmable !== false || !blockReason || !address || (item.source !== "google" && item.source !== "tgos")
      || !finite(item.latitude) || !finite(item.longitude) || !inTaiwan(item.latitude, item.longitude)) return [];
    return [{ interpretedAddress: address, county: boundedText(item.county, 20), district: boundedText(item.district, 20), latitude: item.latitude, longitude: item.longitude, source: item.source, blockReason }];
  });
}

/** Confirm only trusted, high-confidence Taiwan coordinates; administrative completeness is independent. */
export function interpretLocationResolution(value: unknown, addressInput: string): LocationCandidateResult {
  if (!value || typeof value !== "object" || Array.isArray(value)) return { kind: "blocked", reason: "invalid" };
  const result = value as Partial<LocationResolveResult>;
  if (result.status === "ambiguous") {
    // Each choice passes the same acceptance as a single result; never guess between them.
    const choices = (Array.isArray(result.candidates) ? result.candidates : []).slice(0, MAX_LOCATION_CANDIDATES).flatMap((item) => {
      if (!item || item.confirmable !== true) return [];
      const one = interpretLocationResolution({ status: "resolved", confidence: "high", ...item }, addressInput);
      return one.kind === "candidate" ? [one.candidate] : [];
    });
    if (choices.length > 1) return { kind: "choice", candidates: choices };
    return choices.length === 1 ? { kind: "candidate", candidate: choices[0] } : { kind: "blocked", reason: "invalid" };
  }
  if (result.status === "unresolved") {
    const reason = BLOCK_REASONS.find((item) => item === result.resolution_reason) ?? "unresolved";
    const rejected = rejectedCandidates(result.candidates);
    return rejected.length ? { kind: "blocked", reason, rejected } : { kind: "blocked", reason };
  }
  if (result.status === "unavailable") return { kind: "blocked", reason: "unavailable" };
  if (result.status !== "resolved" || (result.source !== "tgos" && result.source !== "google")) return { kind: "blocked", reason: "invalid" };
  // The resolver reports "high" only for trusted accepted geocodes; "unknown" is never promoted.
  if (result.confidence !== "high") return { kind: "blocked", reason: "low_confidence" };
  const { latitude, longitude } = result;
  if (!finite(latitude) || !finite(longitude)) return { kind: "blocked", reason: "missing_coordinates" };
  if (!inTaiwan(latitude, longitude)) return { kind: "blocked", reason: "invalid" };
  const county = boundedText(result.county, 20);
  const district = boundedText(result.district, 20);
  const input = boundedText(addressInput, 500);
  if (!input) return { kind: "blocked", reason: "invalid" };
  const supplied = administrativeParts(input);
  const formatted = administrativeParts(boundedText(result.formatted_address, 500) ?? "");
  for (const key of ["county", "district"] as const) {
    const metadata = key === "county" ? county : district;
    // Defence in depth: a district/county the user typed can never be overridden by the provider.
    if (supplied[key] && [metadata?.replaceAll("台", "臺"), formatted[key]].some((value) => value && value !== supplied[key])) return { kind: "blocked", reason: "administrative_mismatch" };
  }
  const postalCode = typeof result.postal_code === "string" && /^\d{3,6}$/.test(result.postal_code) ? result.postal_code : null;
  return { kind: "candidate", candidate: {
    addressInput: input, interpretedAddress: boundedText(result.formatted_address, 500) ?? input, county, district, latitude, longitude, source: result.source,
    ...(postalCode ? { postalCode } : {}),
    ...(!supplied.county ? { countyUnverified: true } : {}),
  } };
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
