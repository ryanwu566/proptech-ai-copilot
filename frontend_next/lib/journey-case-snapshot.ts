import type { SaveCaseInput } from "./case-storage";
import type { ClosedLoopJourneyState } from "./closed-loop-journey";
import { toStoredTerrainReferenceEvidence } from "./terrain-reference-evidence";

export function buildJourneySaveCase(state: ClosedLoopJourneyState): SaveCaseInput {
  const context = state.propertyContext;
  const title = context.addressSummary || [context.city, context.district, context.road].filter(Boolean).join("") || "Journey case";
  const completed = [Boolean(state.identityAnchor?.coordinates), Boolean(state.locationResult && state.locationStatus !== "unavailable"), Boolean(state.valuationResult && state.valuationStatus === "available"), Boolean(state.loanResult), false].filter(Boolean).length;
  return {
    title, activeWizardStep: "report", progress: completed * 20,
    inputSummary: { city: context.city, district: context.district, road: context.road, propertyPrice: context.askingPriceWan, areaPing: context.areaPing },
    data: {
      inputs: { city: context.city ?? "", district: context.district ?? "", road: context.road ?? "", building_type: context.buildingType ?? "", area_ping: context.areaPing ?? 0, building_age_years: context.buildingAgeYears ?? 0, floor: context.floor ?? 0 },
      propertyIdentityAnchor: state.identityAnchor, propertySearch: state.propertySearchResult, valuation: state.valuationResult,
      loan: state.loanResult, holdingCost: state.holdingResult, financePriceEvidence: state.financePriceEvidence,
      locationInsight: state.locationResult, commuteRoute: state.commuteRouteEvidence, commuteTransit: state.commuteTransitResult,
      marketInsight: state.marketResult,
      terrainReference: state.storedTerrainReference ?? (state.terrainReference ? toStoredTerrainReferenceEvidence(state.terrainReference) ?? undefined : undefined),
      taxOracle: state.taxResult,
      journeyContext: { version: 1, propertyContext: context, priceBasis: state.priceBasis, activePriceWan: state.activePriceWan, manualPriceWan: state.manualPriceWan, valuationStatus: state.valuationStatus },
    },
  };
}
