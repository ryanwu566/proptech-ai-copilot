import type { MarketResult } from "./api";
import type { AnalysisCompletenessState, EvidenceUsabilityState, QueryExecutionState } from "./commercial/state";

export type MarketDisplayState = "available" | "low_sample" | "partial" | "no_data" | "unavailable" | "stale";

function isPositiveFinite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

export function getMarketDisplayState(result: MarketResult | undefined): MarketDisplayState {
  if (result?.data_status === "no_data") return "no_data";
  if (!result || result.data_status === "unavailable" || result.data_status === "invalid" || result.coverage_status === "not_covered" || result.coverage_status === "coverage_unknown" || result.coverage_status === "unknown") return "unavailable";
  const complete =
    result.data_status === "available" &&
    isPositiveFinite(result.avg_price_per_ping) &&
    isPositiveFinite(result.average_unit_price) &&
    result.avg_price_per_ping === result.average_unit_price &&
    isPositiveFinite(result.transaction_volume) &&
    isPositiveFinite(result.transaction_count) &&
    result.transaction_volume === result.transaction_count &&
    (isPositiveFinite(result.record_count) || isPositiveFinite(result.transaction_count)) &&
    typeof result.source_name === "string" &&
    result.source_name.trim().length > 0 &&
    Array.isArray(result.history);
  const hasPartialEvidence = typeof result.source_name === "string" && result.source_name.trim().length > 0 && Array.isArray(result.history) && [result.average_unit_price, result.avg_price_per_ping, result.transaction_count, result.transaction_volume, result.record_count, result.median_unit_price_ntd_sqm, result.median_total_price_ntd].some(isPositiveFinite);
  if (!complete) return hasPartialEvidence ? "partial" : "unavailable";
  const count = result.transaction_count ?? result.transaction_volume ?? result.record_count ?? 0;
  if (result.sample_status === "limited" || result.sample_status === "insufficient" || (isPositiveFinite(count) && count < 10)) return "low_sample";
  if (result.freshness_status === "stale" || result.freshness_status === "failed_latest_update" || result.freshness_status === "update_available") return "stale";
  return "available";
}

export function marketStateHasEvidence(state: MarketDisplayState): boolean {
  return state === "available" || state === "low_sample" || state === "partial" || state === "stale";
}

export type MarketCommercialState = {
  query: QueryExecutionState;
  evidence: EvidenceUsabilityState;
  completeness: AnalysisCompletenessState;
};

export function getMarketCommercialState(result: MarketResult | undefined): MarketCommercialState {
  if (!result) return { query: "not_started", evidence: "unavailable", completeness: "not_started" };
  if (result.coverage_status === "not_covered") return { query: "succeeded", evidence: "no_coverage", completeness: "insufficient" };
  if (result.coverage_status === "coverage_unknown" || result.coverage_status === "unknown") return { query: "succeeded", evidence: "unverified", completeness: "insufficient" };
  const state = getMarketDisplayState(result);
  if (state === "available") return { query: "succeeded", evidence: "usable", completeness: "sufficient_for_task" };
  if (state === "low_sample" || state === "partial") return { query: "succeeded", evidence: "limited", completeness: "partial" };
  if (state === "stale") return { query: "succeeded", evidence: "stale", completeness: "partial" };
  if (state === "no_data") return { query: "succeeded", evidence: "no_match", completeness: "insufficient" };
  return { query: "failed", evidence: "unavailable", completeness: "blocked" };
}
