import type { MarketResult } from "./api";

export type MarketDisplayState = "available" | "no_data" | "unavailable";

function isPositiveFinite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

export function getMarketDisplayState(result: MarketResult | undefined): MarketDisplayState {
  if (
    result?.data_status === "available" &&
    result.coverage_status === "covered" &&
    isPositiveFinite(result.avg_price_per_ping) &&
    isPositiveFinite(result.average_unit_price) &&
    result.avg_price_per_ping === result.average_unit_price &&
    isPositiveFinite(result.transaction_volume) &&
    isPositiveFinite(result.transaction_count) &&
    result.transaction_volume === result.transaction_count &&
    (isPositiveFinite(result.record_count) || isPositiveFinite(result.transaction_count)) &&
    typeof result.source_name === "string" &&
    result.source_name.trim().length > 0 &&
    Array.isArray(result.history)
  ) {
    return "available";
  }

  if (result?.data_status === "no_data" && result.coverage_status === "covered") {
    return "no_data";
  }

  return "unavailable";
}
