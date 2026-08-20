import type {
  HoldingCostResult,
  LoanCalculationResult,
  LocationInsightResult,
  MarketResult,
  PropertySearchResult,
  TaxResult,
  TerrainRiskResult,
  ValuationResult,
} from "@/lib/api";
import { getSafeJourneyPropertyContext, type JourneyPropertyContext, type LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import type { PriceJourneyDisplayStatus } from "@/lib/price-affordability-journey";
import type { StoredTerrainReferenceEvidenceV1, TerrainReferenceEvidence } from "@/lib/terrain-reference-evidence";

export type JourneyPriceBasis = "asking" | "valuation" | "manual";

export type ClosedLoopJourneyState = {
  propertyContext: JourneyPropertyContext;
  propertySearchResult?: PropertySearchResult;
  locationResult?: LocationInsightResult;
  locationStatus: LocationMarketDisplayStatus;
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
  holdingResult?: HoldingCostResult;
  taxResult?: TaxResult;
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

export function createClosedLoopJourneyState(input?: Partial<JourneyPropertyContext>): ClosedLoopJourneyState {
  const propertyContext = getSafeJourneyPropertyContext(input);
  const askingPriceWan = positive(propertyContext.askingPriceWan) ? propertyContext.askingPriceWan : undefined;
  return {
    propertyContext,
    locationStatus: "not_started",
    terrainStatus: "not_started",
    marketStatus: "not_started",
    valuationStatus: "not_started",
    priceBasis: "asking",
    ...(askingPriceWan ? { activePriceWan: askingPriceWan } : {}),
  };
}

export function updateJourneyProperty(state: ClosedLoopJourneyState, input: Partial<JourneyPropertyContext>): ClosedLoopJourneyState {
  const propertyContext = getSafeJourneyPropertyContext({ ...state.propertyContext, ...input });
  const addressChanged = journeyAddressKey(state.propertyContext) !== journeyAddressKey(propertyContext);
  const valuationChanged = journeyValuationKey(state.propertyContext) !== journeyValuationKey(propertyContext);
  const askingChanged = state.propertyContext.askingPriceWan !== propertyContext.askingPriceWan;

  let next: ClosedLoopJourneyState = { ...state, propertyContext };
  if (addressChanged) {
    next = {
      ...next,
      locationResult: undefined,
      locationStatus: "not_started",
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

export function setJourneyLocationResult(
  state: ClosedLoopJourneyState,
  result: LocationInsightResult | null,
  status: LocationMarketDisplayStatus,
): ClosedLoopJourneyState {
  return { ...state, locationResult: result ?? undefined, locationStatus: status };
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
  const previousMidpoint = state.valuationResult?.price_range.mid;
  const nextMidpoint = result?.price_range.mid;
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
      ? state.valuationResult?.price_range.mid
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
  return { ...state, loanResult: undefined, holdingResult: undefined, taxResult: undefined };
}

export function journeyPriceBasisLabel(basis: JourneyPriceBasis, locale: "zh-TW" | "en" | "ja" | "ko"): string {
  const labels = {
    "zh-TW": { asking: "開價", valuation: "估價中位數", manual: "手動輸入" },
    en: { asking: "Asking price", valuation: "Valuation midpoint", manual: "Manual override" },
    ja: { asking: "売出価格", valuation: "査定中央値", manual: "手動入力" },
    ko: { asking: "매도 희망가", valuation: "평가 중간값", manual: "수동 입력" },
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
