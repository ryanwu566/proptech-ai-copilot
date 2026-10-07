import type { SavedCase } from "../case-storage";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { areJourneyPropertyAddressesEquivalent, type JourneyPropertyIdentityAnchorV1 } from "../journey-property-identity.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getActionableValuation, getStoredActionableValuation } from "../valuation-result-state.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { EVIDENCE_KEYS, type EvidenceKey, type PropertyCaseWorkspace, type WorkspaceEvidenceState } from "./workspace-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildMarketPriceModel } from "./market-price-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildLocationWorkspaceSnapshot } from "./location-context.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildFinanceModel } from "./finance-model.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { restoreFinanceModelFromSnapshot } from "./finance-persistence.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildStoredRiskEvidenceModel } from "./risk-evidence-model.ts";

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
  if (addressConflicts || anchor.revalidation.conflicts.length > 0 || anchor.revalidation.status === "needs_revalidation" || anchor.location_status === "stale") {
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
    finance: Boolean(saved.data.financeEvidence || saved.data.loan || saved.data.holdingCost || saved.data.taxOracle),
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
  const valuationUnavailable = journey?.valuationStatus === "unavailable" || ["unavailable", "partial"].includes(saved.data.valuationEvidence?.status ?? "");
  if (!presence.valuation && valuationUnavailable) {
    evidence.valuation = {
      query: "failed",
      usability: "unavailable",
      completeness: "insufficient",
      summaryOnly: true,
    };
  }
  const askingPriceWan = positive(journey?.propertyContext.askingPriceWan)
    ? journey.propertyContext.askingPriceWan
    : positive(saved.inputSummary.propertyPrice)
      ? saved.inputSummary.propertyPrice
      : undefined;
  const basis = journey?.priceBasis === "valuation" ? "estimate" : journey?.priceBasis ?? "asking";
  const actionableValuation = getActionableValuation(saved.data.valuation) ?? getStoredActionableValuation(saved.data.valuation);
  const activePriceWan = basis === "estimate"
    ? stale ? undefined : actionableValuation?.estimateTotal
    : positive(journey?.activePriceWan)
      ? journey.activePriceWan
      : basis === "asking"
        ? askingPriceWan
        : undefined;
  const marketPrice = buildMarketPriceModel({
    identityConfirmed: identity.state === "confirmed",
    activePriceBasis: basis,
    activePriceWan: identity.state === "confirmed" ? activePriceWan : undefined,
    askingPriceWan,
    market: saved.data.marketInsight,
    valuation: saved.data.valuation,
    valuationAttemptStatus: valuationUnavailable ? "unavailable" : "not_started",
    trend: saved.data.trend,
    stale,
  });
  const areaPing = typeof saved.inputSummary.areaPing === "number" && Number.isFinite(saved.inputSummary.areaPing) && saved.inputSummary.areaPing > 0
    ? saved.inputSummary.areaPing
    : typeof saved.data.inputs.area_ping === "number" && Number.isFinite(saved.data.inputs.area_ping) && saved.data.inputs.area_ping > 0
      ? saved.data.inputs.area_ping
      : null;
  const financeContext = {
    caseId: saved.id,
    revision: 1,
    identityAnchorId: identity.anchor?.journey_anchor_id ?? null,
    identityState: identity.state,
    activePriceBasis: basis,
    activePriceWan,
    areaPing,
  } as const;
  const finance = saved.data.financeEvidence
    ? restoreFinanceModelFromSnapshot(saved.data.financeEvidence, financeContext)
    : buildFinanceModel({
        ...financeContext,
        askingPriceWan,
        loanResult: saved.data.loan,
        holdingResult: saved.data.holdingCost,
        taxResult: saved.data.taxOracle,
        calculatedAt: null,
        resultSource: "saved_snapshot",
      });

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
      ...(areaPing !== null && areaPing > 0 ? { areaPing } : {}),
    },
    evidence,
    marketPrice,
    location: buildLocationWorkspaceSnapshot(saved),
    risk: saved.data.terrainReference
      ? buildStoredRiskEvidenceModel(saved.data.terrainReference, {
          stale,
          checkedAt: saved.data.riskEvidenceCheckedAt ?? null,
        })
      : null,
    finance,
    saveState: "saved",
  };
}
