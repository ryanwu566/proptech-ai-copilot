import type { PropertySearchResult, ValuationResult, ValuationTrendResult } from "@/lib/api";

export type ValuationDisplayKind = "available" | "partial" | "demo" | "no_data" | "unavailable";

export type ValuationDisplayState = {
  kind: ValuationDisplayKind;
  message: string;
  actionable: boolean;
};

type ValuationContractResult = ValuationResult & {
  valuation_status?: "available" | "no_data" | "unavailable" | "demo";
  result_origin?: "official" | "demo" | "none";
  is_actionable?: boolean;
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

export function getValuationDisplayState(result: ValuationResult): ValuationDisplayState {
  const contract = result as ValuationContractResult;
  if (contract.valuation_status === "demo" || contract.result_origin === "demo") {
    return { kind: "demo", actionable: false, message: "目前顯示展示資料，不是正式實價登錄估價，不能作為出價、貸款或案件決策依據。" };
  }
  if (contract.valuation_status === "unavailable" || contract.result_origin === "none") {
    // Even when status says unavailable, if comparables exist, report partial
    if (result.comparables?.length > 0) {
      return { kind: "partial", actionable: false, message: "官方可比成交資料可查閱，但估價信心不足，結果僅供參考。" };
    }
    return { kind: "unavailable", actionable: false, message: "估價資料目前無法使用，請稍後再試。" };
  }
  const values = [result.estimate_total_price, result.estimate_unit_price_per_ping, result.price_range?.low, result.price_range?.mid, result.price_range?.high];
  const valid = contract.valuation_status === "available" && contract.result_origin === "official" && contract.is_actionable === true && values.every(positive) && result.comparables?.length >= 3 && result.comparables.every((row) => row.source === "official_plvr_opendata");
  if (valid) return { kind: "available", actionable: true, message: "" };
  // Transactions exist but valuation quality is insufficient for actionable use
  if (result.comparables?.length > 0) {
    return { kind: "partial", actionable: false, message: "官方可比成交資料可查閱，但估價信心不足，結果僅供參考。" };
  }
  if (contract.valuation_status === "no_data") return { kind: "no_data", actionable: false, message: "目前沒有足夠的官方可比成交資料。" };
  return { kind: "unavailable", actionable: false, message: "估價資料目前無法使用，請稍後再試。" };
}

export function getValuationTrendDisplayState(result: ValuationTrendResult): ValuationDisplayState {
  const contract = result as TrendContractResult;
  if (contract.trend_status === "available" && contract.is_actionable === true && result.monthly_series.length >= 2 && positive(result.recent_median_unit_price) && typeof result.trend_annualized_rate === "number") {
    return { kind: "available", actionable: true, message: "" };
  }
  if (contract.trend_status === "no_data") return { kind: "no_data", actionable: false, message: "目前沒有足夠的官方成交月份可供趨勢分析。" };
  return { kind: "unavailable", actionable: false, message: "估價趨勢資料目前無法使用，請稍後再試。" };
}

export function getPropertySearchDisplayState(result: PropertySearchResult): ValuationDisplayState {
  const contract = result as SearchContractResult;
  if (contract.search_status === "available" && contract.is_actionable === true && (result.summary.matched_count ?? 0) > 0) {
    return { kind: "available", actionable: true, message: "" };
  }
  if (contract.search_status === "no_data") return { kind: "no_data", actionable: false, message: "目前篩選條件沒有可用的官方交易資料。" };
  return { kind: "unavailable", actionable: false, message: "市場資料目前無法使用，請稍後再試。" };
}
