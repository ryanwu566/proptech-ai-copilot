import type { SavedCase } from "../case-storage";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { areJourneyPropertyAddressesEquivalent, type JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { EVIDENCE_KEYS, type EvidenceKey, type PropertyCaseWorkspace, type WorkspaceEvidenceState } from "./workspace-model.ts";

function positive(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function addressFor(saved: SavedCase): string {
  const context = saved.data.journeyContext?.propertyContext;
  const summary = context?.addressSummary?.trim();
  if (summary) return summary;
  const parts = [saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road]
    .filter((part): part is string => typeof part === "string" && part.trim().length > 0);
  return parts.join("") || saved.title;
}

function identityState(anchor: JourneyPropertyIdentityAnchorV1 | undefined, displayAddress?: string): PropertyCaseWorkspace["identity"] {
  if (!anchor) return { state: "unconfirmed", scope: "unconfirmed", anchor: null };
  const addressConflicts = Boolean(displayAddress)
    && !areJourneyPropertyAddressesEquivalent(displayAddress!, anchor.address_input)
    && !areJourneyPropertyAddressesEquivalent(displayAddress!, anchor.normalized_address);
  if (addressConflicts || anchor.revalidation.status === "needs_revalidation" || anchor.location_status === "stale") {
    return { state: "revalidation_required", scope: "journey_browser_anchor", anchor };
  }
  if (anchor.confidence.level === "high" || anchor.confidence.level === "medium") {
    return { state: "confirmed", scope: "journey_browser_anchor", anchor };
  }
  return { state: "unconfirmed", scope: "journey_browser_anchor", anchor };
}

function reopenedEvidence(present: boolean, stale: boolean): WorkspaceEvidenceState {
  if (!present) return { query: "not_started", completeness: "not_started", summaryOnly: false };
  return {
    query: "succeeded",
    usability: stale ? "stale" : "limited",
    completeness: "partial",
    summaryOnly: true,
  };
}

function evidencePresence(saved: SavedCase): Record<EvidenceKey, boolean> {
  return {
    market: Boolean(saved.data.marketInsight),
    valuation: Boolean(saved.data.valuation),
    location: Boolean(saved.data.locationInsight),
    commute: Boolean(saved.data.commuteRoute || saved.data.commuteTransit),
    risk: Boolean(saved.data.terrainReference || saved.data.terrainRisk),
    finance: Boolean(saved.data.loan || saved.data.holdingCost || saved.data.taxOracle),
  };
}

export function adaptSavedCaseToWorkspace(saved: SavedCase): PropertyCaseWorkspace {
  const displayAddress = addressFor(saved);
  const identityAddress = saved.data.journeyContext?.propertyContext.addressSummary?.trim()
    || [saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road].filter(Boolean).join("");
  const identity = identityState(saved.data.propertyIdentityAnchor, identityAddress || undefined);
  const stale = identity.state === "revalidation_required";
  const presence = evidencePresence(saved);
  const evidence = Object.fromEntries(
    EVIDENCE_KEYS.map((key) => [key, reopenedEvidence(presence[key], stale)]),
  ) as Record<EvidenceKey, WorkspaceEvidenceState>;
  const journey = saved.data.journeyContext;
  const askingPriceWan = positive(journey?.propertyContext.askingPriceWan)
    ? journey.propertyContext.askingPriceWan
    : positive(saved.inputSummary.propertyPrice)
      ? saved.inputSummary.propertyPrice
      : undefined;
  const basis = journey?.priceBasis === "valuation" ? "estimate" : journey?.priceBasis ?? "asking";
  const activePriceWan = positive(journey?.activePriceWan)
    ? journey.activePriceWan
    : basis === "asking"
      ? askingPriceWan
      : undefined;

  return {
    caseId: saved.id,
    revision: 1,
    title: saved.title || addressFor(saved),
    displayAddress,
    updatedAt: saved.updatedAt,
    identity,
    assumptions: {
      activePriceBasis: basis,
      ...(activePriceWan ? { activePriceWan } : {}),
      ...(askingPriceWan ? { askingPriceWan } : {}),
      ...(positive(journey?.manualPriceWan) ? { manualPriceWan: journey.manualPriceWan } : {}),
    },
    evidence,
    saveState: "saved",
  };
}
