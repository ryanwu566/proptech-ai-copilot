import type { PropertySearchResult, ValuationResult, ValuationTrendResult } from "@/lib/api";

export type ValuationDisplayKind = "available" | "partial" | "demo" | "no_data" | "unavailable" | "error";

export type ValuationDisplayState = {
  kind: ValuationDisplayKind;
  message: string;
  actionable: boolean;
};

export type ActionableValuationResult = Omit<ValuationResult, "estimate_total_price" | "estimate_unit_price_per_ping" | "price_range" | "confidence_score" | "confidence" | "valuation_explanation"> & {
  estimate_total_price: number;
  estimate_unit_price_per_ping: number;
  price_range: { low: number; mid: number; high: number };
  confidence_score: number;
  confidence: "high" | "medium" | "low";
  valuation_explanation: Omit<ValuationResult["valuation_explanation"], "average_similarity_score"> & {
    average_similarity_score: number;
  };
};

export type ActionableValuation = {
  result: ActionableValuationResult;
  estimateTotal: number;
  estimateUnit: number;
  priceRange: { low: number; mid: number; high: number };
  confidenceScore: number;
  sampleCount: number;
};

type TrendContractResult = ValuationTrendResult & {
  trend_status?: "available" | "no_data" | "unavailable";
  is_actionable?: boolean;
};

type SearchContractResult = PropertySearchResult & {
  search_status?: "available" | "no_data" | "unavailable";
  is_actionable?: boolean;
};

const positive = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value > 0;
const nonNegative = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0;
const finiteScore = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100;
const nonNegativeInteger = (value: unknown): value is number => typeof value === "number" && Number.isInteger(value) && value >= 0;
const record = (value: unknown): Record<string, unknown> | null => typeof value === "object" && value !== null ? value as Record<string, unknown> : null;
const officialComposition = (value: unknown): boolean => value === "official" || value === "official_limited" || value === "official_district";
const confidence = (value: unknown): boolean => value === "high" || value === "medium" || value === "low";

function validOfficialComparable(value: unknown): boolean {
  const item = record(value);
  return item?.source === "official_plvr_opendata"
    && positive(item.area_ping)
    && positive(item.unit_price_per_ping)
    && positive(item.total_price)
    && nonNegative(item.building_age_years)
    && finiteScore(item.similarity_score)
    && positive(item.weight);
}

export function getActionableValuation(value: unknown): ActionableValuation | null {
  const result = record(value);
  const range = record(result?.price_range);
  const explanation = record(result?.valuation_explanation);
  const comparables = result?.comparables;
  if (
    result?.valuation_status !== "available"
    || result.result_origin !== "official"
    || result.is_actionable !== true
    || !officialComposition(result.estimate_data_composition)
    || !positive(result.estimate_total_price)
    || !positive(result.estimate_unit_price_per_ping)
    || !positive(range?.low)
    || !positive(range?.mid)
    || !positive(range?.high)
    || range.low > range.mid
    || range.mid > range.high
    || !finiteScore(result.confidence_score)
    || !confidence(result.confidence)
    || !nonNegativeInteger(explanation?.sample_count)
    || explanation.sample_count < 3
    || !finiteScore(explanation.average_similarity_score)
    || !Array.isArray(comparables)
    || comparables.length < 3
    || !comparables.every(validOfficialComparable)
  ) return null;
  return {
    result: value as ActionableValuationResult,
    estimateTotal: result.estimate_total_price,
    estimateUnit: result.estimate_unit_price_per_ping,
    priceRange: { low: range.low, mid: range.mid, high: range.high },
    confidenceScore: result.confidence_score,
    sampleCount: explanation.sample_count,
  };
}

/**
 * Validates the bounded valuation summary stored with a saved case. Comparables
 * are deliberately removed at that boundary, so this is stricter about the
 * remaining official-result contract while requiring the array to stay empty.
 */
export function getStoredActionableValuation(value: unknown): ActionableValuation | null {
  const result = record(value);
  const range = record(result?.price_range);
  const explanation = record(result?.valuation_explanation);
  if (
    result?.valuation_status !== "available"
    || result.result_origin !== "official"
    || result.is_actionable !== true
    || !officialComposition(result.estimate_data_composition)
    || !positive(result.estimate_total_price)
    || !positive(result.estimate_unit_price_per_ping)
    || !positive(range?.low)
    || !positive(range?.mid)
    || !positive(range?.high)
    || range.low > range.mid
    || range.mid > range.high
    || !finiteScore(result.confidence_score)
    || !confidence(result.confidence)
    || !nonNegativeInteger(explanation?.sample_count)
    || explanation.sample_count < 3
    || !finiteScore(explanation.average_similarity_score)
    || !Array.isArray(result.comparables)
    || result.comparables.length !== 0
  ) return null;
  return {
    result: value as ActionableValuationResult,
    estimateTotal: result.estimate_total_price,
    estimateUnit: result.estimate_unit_price_per_ping,
    priceRange: { low: range.low, mid: range.mid, high: range.high },
    confidenceScore: result.confidence_score,
    sampleCount: explanation.sample_count,
  };
}

export function getValuationDisplayState(value: unknown): ValuationDisplayState {
  const result = record(value);
  if (!result) return { kind: "error", actionable: false, message: "目前無法產出可採用的完整估價結果。" };
  if (result.valuation_status === "demo" || result.result_origin === "demo") {
    return { kind: "demo", actionable: false, message: "這是示範估價資料，不可作為交易或貸款決策依據。" };
  }
  if (result.valuation_status === "unavailable" || result.result_origin === "none") {
    if (Array.isArray(result.comparables) && result.comparables.length > 0) {
      return { kind: "partial", actionable: false, message: "目前只有部分成交證據，無法形成可採用的估價。" };
    }
    return { kind: "unavailable", actionable: false, message: "估價資料目前無法取得，請稍後再試。" };
  }
  if (result.valuation_status === "no_data") {
    return { kind: "no_data", actionable: false, message: "官方成交證據不足，無法提供估價。" };
  }
  if (getActionableValuation(result)) return { kind: "available", actionable: true, message: "" };
  if (result.valuation_status === "available") {
    return { kind: "error", actionable: false, message: "目前無法產出可採用的完整估價結果。" };
  }
  if (Array.isArray(result.comparables) && result.comparables.length > 0) {
    return { kind: "partial", actionable: false, message: "目前只有部分成交證據，無法形成可採用的估價。" };
  }
  return { kind: "unavailable", actionable: false, message: "估價資料目前無法取得，請稍後再試。" };
}

export function getValuationTrendDisplayState(result: ValuationTrendResult): ValuationDisplayState {
  const contract = result as TrendContractResult;
  if (contract.trend_status === "available" && contract.is_actionable === true && Array.isArray(result.monthly_series) && result.monthly_series.length >= 2 && positive(result.recent_median_unit_price) && typeof result.trend_annualized_rate === "number" && Number.isFinite(result.trend_annualized_rate)) {
    return { kind: "available", actionable: true, message: "" };
  }
  if (contract.trend_status === "no_data") return { kind: "no_data", actionable: false, message: "官方成交證據不足，無法提供市場趨勢。" };
  return { kind: "unavailable", actionable: false, message: "市場趨勢資料目前無法取得，請稍後再試。" };
}

export function getPropertySearchDisplayState(result: PropertySearchResult): ValuationDisplayState {
  const contract = result as SearchContractResult;
  if (contract.search_status === "available" && contract.is_actionable === true && (result.summary?.matched_count ?? 0) > 0) {
    return { kind: "available", actionable: true, message: "" };
  }
  if (contract.search_status === "no_data") return { kind: "no_data", actionable: false, message: "官方成交資料不足，無法提供找房方向。" };
  return { kind: "unavailable", actionable: false, message: "找房資料目前無法取得，請稍後再試。" };
}
