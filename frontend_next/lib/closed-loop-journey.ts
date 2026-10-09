import type {
  HoldingCostResult,
  CommuteAddressLookupResult,
  CommuteRouteEvidence,
  LoanCalculationResult,
  LocationInsightResult,
  MarketResult,
  PropertySearchResult,
  TaxResult,
  TerrainRiskResult,
  ValuationResult,
} from "@/lib/api";
import { deriveJourneyRoadFromAcceptedAddress, getSafeJourneyPropertyContext, type JourneyPropertyContext, type LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import type { PriceJourneyDisplayStatus } from "@/lib/price-affordability-journey";
import type { StoredTerrainReferenceEvidenceV1, TerrainReferenceEvidence } from "@/lib/terrain-reference-evidence";
import { getActionableValuation } from "@/lib/valuation-result-state";
import { withLocationAdvisoryContext } from "@/lib/location-evidence-context";
import {
  buildJourneyPropertyIdentityAnchor,
  reconcileJourneyPropertyIdentityAnchor,
  type JourneyPropertyIdentityAnchorV1,
} from "@/lib/journey-property-identity";

export type JourneyPriceBasis = "asking" | "valuation" | "manual";
import { priceSourceFromBasis, type FinancePriceEvidence } from "@/lib/finance-price-provenance";

export type ClosedLoopJourneyState = {
  propertyContext: JourneyPropertyContext;
  identityAnchor?: JourneyPropertyIdentityAnchorV1;
  propertySearchResult?: PropertySearchResult;
  locationResult?: LocationInsightResult;
  locationStatus: LocationMarketDisplayStatus;
  commuteRouteEvidence?: CommuteRouteEvidence;
  commuteRouteStatus: LocationMarketDisplayStatus;
  commuteTransitResult?: CommuteAddressLookupResult;
  commuteTransitStatus: LocationMarketDisplayStatus;
  terrainResult?: TerrainRiskResult;
  terrainReference?: TerrainReferenceEvidence;
  storedTerrainReference?: StoredTerrainReferenceEvidenceV1;
  terrainStatus: LocationMarketDisplayStatus;
  marketResult?: MarketResult;
  marketStatus: LocationMarketDisplayStatus;
  valuationResult?: ValuationResult;
  valuationStatus: PriceJourneyDisplayStatus;
  priceBasis: JourneyPriceBasis;
  activePriceWan?: number;
  manualPriceWan?: number;
  loanResult?: LoanCalculationResult;
  financePriceEvidence?: FinancePriceEvidence;
  holdingResult?: HoldingCostResult;
  taxResult?: TaxResult;
};

type JourneyIdentityTransitionOptions = {
  now?: () => string;
  idFactory?: () => string;
};

function positive(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

export function journeyAddressKey(context: JourneyPropertyContext): string {
  return [context.city, context.district, context.road, context.addressSummary]
    .map((value) => value?.trim() ?? "")
    .join("|");
}

export function journeyValuationKey(context: JourneyPropertyContext): string {
  return [
    journeyAddressKey(context),
    context.buildingType?.trim() ?? "",
    context.areaPing ?? "",
    context.buildingAgeYears ?? "",
    context.floor ?? "",
  ].join("|");
}

export function createClosedLoopJourneyState(
  input?: Partial<JourneyPropertyContext>,
  identityOptions: JourneyIdentityTransitionOptions = {},
): ClosedLoopJourneyState {
  const propertyContext = getSafeJourneyPropertyContext(input);
  const askingPriceWan = positive(propertyContext.askingPriceWan) ? propertyContext.askingPriceWan : undefined;
  const hasAddress = Boolean(journeyAddressKey(propertyContext).replaceAll("|", ""));
  return {
    propertyContext,
    ...(hasAddress ? { identityAnchor: buildJourneyPropertyIdentityAnchor({ context: propertyContext }, identityOptions) } : {}),
    locationStatus: "not_started",
    commuteRouteStatus: "not_started",
    commuteTransitStatus: "not_started",
    terrainStatus: "not_started",
    marketStatus: "not_started",
    valuationStatus: "not_started",
    priceBasis: "asking",
    ...(askingPriceWan ? { activePriceWan: askingPriceWan } : {}),
  };
}

export function updateJourneyProperty(
  state: ClosedLoopJourneyState,
  input: Partial<JourneyPropertyContext>,
  identityOptions: JourneyIdentityTransitionOptions = {},
): ClosedLoopJourneyState {
  const propertyContext = getSafeJourneyPropertyContext({ ...state.propertyContext, ...input });
  const addressChanged = journeyAddressKey(state.propertyContext) !== journeyAddressKey(propertyContext);
  const valuationChanged = journeyValuationKey(state.propertyContext) !== journeyValuationKey(propertyContext);
  const askingChanged = state.propertyContext.askingPriceWan !== propertyContext.askingPriceWan;
  const advisoryChanged = askingChanged || state.propertyContext.areaPing !== propertyContext.areaPing;

  let next: ClosedLoopJourneyState = {
    ...state, propertyContext,
    locationResult: advisoryChanged && state.locationResult ? withLocationAdvisoryContext(state.locationResult, propertyContext.askingPriceWan, propertyContext.areaPing) : state.locationResult,
  };
  if (addressChanged) {
    const hasAddress = Boolean(journeyAddressKey(propertyContext).replaceAll("|", ""));
    next = {
      ...next,
      propertySearchResult: undefined,
      identityAnchor: hasAddress ? buildJourneyPropertyIdentityAnchor({ context: propertyContext }, identityOptions) : undefined,
      locationResult: undefined,
      locationStatus: "not_started",
      commuteRouteEvidence: undefined,
      commuteRouteStatus: "not_started",
      commuteTransitResult: undefined,
      commuteTransitStatus: "not_started",
      terrainResult: undefined,
      terrainReference: undefined,
      storedTerrainReference: undefined,
      terrainStatus: "not_started",
      marketResult: undefined,
      marketStatus: "not_started",
    };
  }
  if (valuationChanged) {
    next = { ...next, valuationResult: undefined, valuationStatus: "not_started" };
  }

  const selectedNewProperty = addressChanged && propertyContext.selectionStatus !== "not_selected";
  if (selectedNewProperty || askingChanged) {
    next = {
      ...next,
      priceBasis: "asking",
      activePriceWan: positive(propertyContext.askingPriceWan) ? propertyContext.askingPriceWan : undefined,
      manualPriceWan: undefined,
    };
  } else if (valuationChanged && state.priceBasis === "valuation") {
    next = { ...next, activePriceWan: undefined };
  }

  const activePriceChanged = state.activePriceWan !== next.activePriceWan;
  if (valuationChanged || activePriceChanged) next = clearJourneyAffordability(next);
  return next;
}

export function updateJourneyMarketLocation(
  state: ClosedLoopJourneyState,
  input: Pick<JourneyPropertyContext, "city" | "district" | "road">,
  identityOptions: JourneyIdentityTransitionOptions = {},
): ClosedLoopJourneyState {
  const propertyContext = getSafeJourneyPropertyContext({
    ...state.propertyContext,
    city: input.city,
    district: input.district,
    road: input.road,
    addressSummary: [input.city, input.district, input.road].filter(Boolean).join(""),
  });
  if (journeyAddressKey(state.propertyContext) === journeyAddressKey(propertyContext)) {
    return {
      ...state,
      propertyContext,
      marketResult: undefined,
      marketStatus: "not_started",
    };
  }

  const hasAddress = Boolean(journeyAddressKey(propertyContext).replaceAll("|", ""));
  const next = {
    ...state,
    propertyContext,
    propertySearchResult: undefined,
    identityAnchor: hasAddress ? buildJourneyPropertyIdentityAnchor({ context: propertyContext }, identityOptions) : undefined,
    locationResult: undefined,
    locationStatus: "not_started" as const,
    commuteRouteEvidence: undefined,
    commuteRouteStatus: "not_started" as const,
    commuteTransitResult: undefined,
    commuteTransitStatus: "not_started" as const,
    terrainResult: undefined,
    terrainReference: undefined,
    storedTerrainReference: undefined,
    terrainStatus: "not_started" as const,
    marketResult: undefined,
    marketStatus: "not_started" as const,
    valuationResult: undefined,
    valuationStatus: "not_started" as const,
    ...(state.priceBasis === "valuation" ? { activePriceWan: undefined } : {}),
  };
  return clearJourneyAffordability(next);
}

export function setJourneyLocationResult(
  state: ClosedLoopJourneyState,
  result: LocationInsightResult | null,
  status: LocationMarketDisplayStatus,
  identityOptions: JourneyIdentityTransitionOptions = {},
): ClosedLoopJourneyState {
  if (!result) return { ...state, locationResult: undefined, locationStatus: status };
  const identityAnchor = state.identityAnchor
    ? reconcileJourneyPropertyIdentityAnchor(state.identityAnchor, state.propertyContext, result, identityOptions)
    : buildJourneyPropertyIdentityAnchor({ context: state.propertyContext, location: result }, identityOptions);
  if (identityAnchor.revalidation.status !== "current" || result.geocoding_acceptance?.accepted_for_analysis !== true) {
    return { ...state, identityAnchor, locationResult: result, locationStatus: status };
  }
  const city = identityAnchor.administrative_location.city ?? state.propertyContext.city;
  const district = identityAnchor.administrative_location.district ?? state.propertyContext.district;
  const road = deriveJourneyRoadFromAcceptedAddress(identityAnchor.normalized_address, city, district, identityAnchor.administrative_location.village)
    ?? state.propertyContext.road;
  const propertyContext = getSafeJourneyPropertyContext({
    ...state.propertyContext,
    ...(city ? { city } : {}),
    ...(district ? { district } : {}),
    ...(road ? { road } : { road: undefined }),
    addressSummary: identityAnchor.normalized_address,
  });
  return { ...state, propertyContext, identityAnchor, locationResult: result, locationStatus: status };
}

export function restoreJourneyLocationResult(
  state: ClosedLoopJourneyState,
  result: LocationInsightResult,
  status: LocationMarketDisplayStatus,
): ClosedLoopJourneyState {
  return { ...state, locationResult: result, locationStatus: status };
}

export function setJourneyCommuteRoute(
  state: ClosedLoopJourneyState,
  evidence: CommuteRouteEvidence | null,
  status: LocationMarketDisplayStatus,
): ClosedLoopJourneyState {
  return { ...state, commuteRouteEvidence: evidence ?? undefined, commuteRouteStatus: status };
}

export function setJourneyCommuteTransit(
  state: ClosedLoopJourneyState,
  result: CommuteAddressLookupResult | null,
  status: LocationMarketDisplayStatus,
): ClosedLoopJourneyState {
  return { ...state, commuteTransitResult: result ?? undefined, commuteTransitStatus: status };
}

export function setJourneyTerrainResult(
  state: ClosedLoopJourneyState,
  result: TerrainRiskResult | null,
  status: LocationMarketDisplayStatus,
): ClosedLoopJourneyState {
  return { ...state, terrainResult: result ?? undefined, terrainStatus: status };
}

export function setJourneyMarketResult(
  state: ClosedLoopJourneyState,
  result: MarketResult | null,
  status: LocationMarketDisplayStatus,
): ClosedLoopJourneyState {
  return { ...state, marketResult: result ?? undefined, marketStatus: status };
}

export function setJourneyValuation(
  state: ClosedLoopJourneyState,
  result: ValuationResult | undefined,
  status: PriceJourneyDisplayStatus,
): ClosedLoopJourneyState {
  const previousMidpoint = getActionableValuation(state.valuationResult)?.priceRange.mid;
  const nextMidpoint = getActionableValuation(result)?.priceRange.mid;
  let next: ClosedLoopJourneyState = { ...state, valuationResult: result, valuationStatus: status };
  if (state.priceBasis === "valuation") next = { ...next, activePriceWan: positive(nextMidpoint) ? nextMidpoint : undefined };
  if (state.priceBasis !== "asking" && !state.activePriceWan && positive(nextMidpoint)) {
    next = { ...next, priceBasis: "valuation", activePriceWan: nextMidpoint };
  }
  if (previousMidpoint !== nextMidpoint && state.priceBasis === "valuation") next = clearJourneyAffordability(next);
  return next;
}

export function selectJourneyPrice(
  state: ClosedLoopJourneyState,
  basis: JourneyPriceBasis,
  manualPriceWan?: number,
): ClosedLoopJourneyState {
  const amount = basis === "asking"
    ? state.propertyContext.askingPriceWan
    : basis === "valuation"
      ? getActionableValuation(state.valuationResult)?.priceRange.mid
      : manualPriceWan;
  const next = {
    ...state,
    priceBasis: basis,
    activePriceWan: positive(amount) ? amount : undefined,
    manualPriceWan: basis === "manual" && positive(manualPriceWan) ? manualPriceWan : undefined,
  };
  return state.priceBasis === next.priceBasis && state.activePriceWan === next.activePriceWan
    ? next
    : clearJourneyAffordability(next);
}

export function clearJourneyAffordability(state: ClosedLoopJourneyState): ClosedLoopJourneyState {
  return { ...state, loanResult: undefined, holdingResult: undefined, taxResult: undefined, financePriceEvidence: undefined };
}

/** Capture the calculator's actual input. Editing it never overwrites the case asking price. */
export function setJourneyLoanResult(state: ClosedLoopJourneyState, loanResult: LoanCalculationResult | undefined, now = () => new Date().toISOString()): ClosedLoopJourneyState {
  if (!loanResult) return { ...state, loanResult: undefined, holdingResult: undefined, financePriceEvidence: undefined };
  const price = loanResult.property_price_wan;
  const selected = positive(state.activePriceWan) && price === state.activePriceWan;
  return { ...state, loanResult, holdingResult: state.holdingResult?.property_price_wan === price && state.holdingResult.input?.loan_monthly_payment === loanResult.monthly_payment ? state.holdingResult : undefined,
    financePriceEvidence: positive(price) ? { price_twd: price * 10000, source: selected ? priceSourceFromBasis(state.priceBasis) : "MANUAL_SCENARIO", calculated_at: now() } : undefined };
}

export function setJourneyHoldingResult(state: ClosedLoopJourneyState, holdingResult: HoldingCostResult | undefined, now = () => new Date().toISOString()): ClosedLoopJourneyState {
  if (!holdingResult) return { ...state, holdingResult: undefined };
  const price = holdingResult.property_price_wan;
  const sameLoan = state.loanResult?.property_price_wan === price && state.loanResult.monthly_payment === holdingResult.input?.loan_monthly_payment;
  const selected = positive(state.activePriceWan) && price === state.activePriceWan;
  return { ...state, holdingResult, loanResult: sameLoan ? state.loanResult : undefined,
    financePriceEvidence: sameLoan && state.financePriceEvidence ? { ...state.financePriceEvidence, calculated_at: now() } : positive(price) ? { price_twd: price * 10000, source: selected ? priceSourceFromBasis(state.priceBasis) : "MANUAL_SCENARIO", calculated_at: now() } : undefined };
}

export function journeyPriceBasisLabel(basis: JourneyPriceBasis, locale: "zh-TW" | "en" | "ja" | "ko"): string {
  const labels = {
    "zh-TW": { asking: "開價", valuation: "成交資料推估中位值", manual: "手動試算情境" },
    en: { asking: "Asking price", valuation: "Transaction-based midpoint estimate", manual: "Manual calculation scenario" },
    ja: { asking: "売出価格", valuation: "取引データによる推定中央値", manual: "手動試算シナリオ" },
    ko: { asking: "매도 희망가", valuation: "거래 자료 추정 중간값", manual: "수동 계산 시나리오" },
  } as const;
  return labels[locale][basis];
}

export function journeyWorkflowStateLabel(
  state: "complete" | "partial" | "not_available" | "needs_review",
  locale: "zh-TW" | "en" | "ja" | "ko",
): string {
  const labels = {
    "zh-TW": { complete: "已完成", partial: "部分完成", not_available: "資料不可用", needs_review: "需要確認" },
    en: { complete: "Complete", partial: "Partial", not_available: "Not available", needs_review: "Needs review" },
    ja: { complete: "完了", partial: "一部完了", not_available: "利用不可", needs_review: "確認が必要" },
    ko: { complete: "완료", partial: "일부 완료", not_available: "이용 불가", needs_review: "확인 필요" },
  } as const;
  return labels[locale][state];
}
