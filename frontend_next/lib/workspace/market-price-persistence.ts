import type { MarketResult, ValuationResult, ValuationTrendResult } from "../api";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getActionableValuation, getStoredActionableValuation, getValuationTrendDisplayState } from "../valuation-result-state.ts";
// @ts-expect-error Native TS runner extension.
import { compactComparableExplanation } from "./comparable-explanation.ts";

function boundedHistory(history: MarketResult["history"] | undefined): MarketResult["history"] {
  if (!Array.isArray(history)) return [];
  return history
    .filter((row) => row && typeof row === "object")
    .slice(0, 24)
    .map((row) => ({
      period: typeof row.period === "string" || row.period === null ? row.period : null,
      average_unit_price: typeof row.average_unit_price === "number" && Number.isFinite(row.average_unit_price)
        ? row.average_unit_price
        : null,
      transaction_count: Number.isInteger(row.transaction_count) && row.transaction_count >= 0
        ? row.transaction_count
        : 0,
    }));
}

/**
 * Keeps only the aggregate, user-facing Market evidence needed after a case is
 * reopened. Provider identifiers, diagnostic payloads, distributions, and raw
 * rows deliberately remain session-only.
 */
export function compactMarketInsight(result: MarketResult | null | undefined): MarketResult | undefined {
  if (!result || typeof result !== "object") return undefined;

  return {
    city: result.city,
    county: result.county,
    district: result.district,
    period: result.period,
    average_unit_price: result.average_unit_price,
    avg_price_per_ping: result.avg_price_per_ping,
    transaction_count: result.transaction_count,
    transaction_volume: result.transaction_volume,
    record_count: result.record_count,
    summary: result.summary,
    source_name: result.source_name,
    source_updated_at: result.source_updated_at,
    coverage_status: result.coverage_status,
    data_status: result.data_status,
    caveat: result.caveat,
    disclaimer: result.disclaimer,
    history: boundedHistory(result.history),
    median_unit_price_ntd_sqm: result.median_unit_price_ntd_sqm,
    mean_unit_price_ntd_sqm: result.mean_unit_price_ntd_sqm,
    lower_quartile_unit_price_ntd_sqm: result.lower_quartile_unit_price_ntd_sqm,
    upper_quartile_unit_price_ntd_sqm: result.upper_quartile_unit_price_ntd_sqm,
    median_total_price_ntd: result.median_total_price_ntd,
    median_area_sqm: result.median_area_sqm,
    sample_status: result.sample_status,
    freshness_status: result.freshness_status,
    period_change: result.period_change,
    year_over_year_change: result.year_over_year_change,
    inclusion_count: result.inclusion_count,
    exclusion_count: result.exclusion_count,
    methodology: result.methodology,
    requested_scope: result.requested_scope,
    requested_city: result.requested_city,
    requested_district: result.requested_district,
    requested_road: result.requested_road,
    normalized_road: result.normalized_road,
    road_minimum_sample: result.road_minimum_sample,
    analysis_level: result.analysis_level,
    effective_analysis_level: result.effective_analysis_level,
    effective_scope_label: result.effective_scope_label,
    effective_sample_count: result.effective_sample_count,
    road_sample_count: result.road_sample_count,
    district_sample_count: result.district_sample_count,
    fallback_applied: result.fallback_applied,
    fallback_reason: result.fallback_reason,
    period_min: result.period_min,
    period_max: result.period_max,
    newest_effective_period: result.newest_effective_period,
    median_unit_price_per_ping: result.median_unit_price_per_ping,
    p25_unit_price_per_ping: result.p25_unit_price_per_ping,
    p75_unit_price_per_ping: result.p75_unit_price_per_ping,
    median_total_price: result.median_total_price,
    median_area_ping: result.median_area_ping,
    volatility: result.volatility,
  };
}

/**
 * Converts a validated official valuation into the only shape allowed to cross
 * the case-storage boundary. Comparable rows and provider/runtime diagnostics
 * are intentionally absent. A whitelisted bounded decision trace is frozen.
 */
export function compactActionableValuationSummary(
  value: ValuationResult | null | undefined,
): ValuationResult | undefined {
  const actionable = getActionableValuation(value) ?? getStoredActionableValuation(value);
  if (!actionable) return undefined;
  const result = actionable.result;
  const explanation = result.valuation_explanation;
  const trace = compactComparableExplanation(result.comparable_decision_trace);
  return {
    valuation_status: "available",
    valuation_reason_code: "stored_actionable_summary",
    result_origin: "official",
    is_actionable: true,
    estimate_data_composition: result.estimate_data_composition,
    estimate_total_price: actionable.estimateTotal,
    estimate_unit_price_per_ping: actionable.estimateUnit,
    price_range: { ...actionable.priceRange },
    confidence_score: actionable.confidenceScore,
    confidence: result.confidence,
    confidence_reason: result.confidence_reason,
    comparables: [],
    comparable_decision_trace: trace?.selected_count === actionable.sampleCount ? trace : undefined,
    valuation_explanation: {
      sample_count: actionable.sampleCount,
      same_road_count: explanation.same_road_count,
      same_district_count: explanation.same_district_count,
      same_city_count: explanation.same_city_count,
      same_building_type_count: explanation.same_building_type_count,
      nearest_distance_m: explanation.nearest_distance_m,
      average_area_difference_ping: explanation.average_area_difference_ping,
      average_age_difference_years: explanation.average_age_difference_years,
      average_similarity_score: explanation.average_similarity_score,
      method: explanation.method,
    },
    source_details: {
      file: "",
      nature: "official summary",
      complete_real_price_registry: false,
      formal_appraisal: false,
      bank_appraisal: false,
      future_adapter: "",
    },
    disclaimer: result.disclaimer,
  } as unknown as ValuationResult;
}

export function compactActionableValuationTrendSummary(
  value: ValuationTrendResult | null | undefined,
): ValuationTrendResult | undefined {
  if (!value || typeof value !== "object") return undefined;
  const storedSummary = value.trend_reason_code === "stored_actionable_summary"
    && value.trend_status === "available"
    && value.is_actionable === false
    && Array.isArray(value.monthly_series)
    && value.monthly_series.length === 0
    && typeof value.recent_median_unit_price === "number"
    && Number.isFinite(value.recent_median_unit_price)
    && value.recent_median_unit_price > 0
    && typeof value.trend_annualized_rate === "number"
    && Number.isFinite(value.trend_annualized_rate);
  if (!storedSummary && !getValuationTrendDisplayState(value).actionable) return undefined;

  return {
    trend_status: "available",
    trend_reason_code: "stored_actionable_summary",
    is_actionable: false,
    source: "official_plvr_opendata",
    data_scope: value.data_scope,
    effective_period_min: value.effective_period_min,
    effective_period_max: value.effective_period_max,
    excluded_future_period_count: value.excluded_future_period_count,
    excluded_out_of_window_count: value.excluded_out_of_window_count,
    period_min: value.period_min,
    period_max: value.period_max,
    sample_count: value.sample_count,
    road_sample_count: value.road_sample_count,
    district_sample_count: value.district_sample_count,
    monthly_series: [],
    yearly_series: [],
    recent_median_unit_price: value.recent_median_unit_price,
    trend_annualized_rate: value.trend_annualized_rate,
    volatility: value.volatility,
    confidence_level: value.confidence_level,
    confidence_reason: value.confidence_reason,
    scenario_forecast: { conservative: [], base: [], optimistic: [] },
    methodology: [],
    disclaimer: value.disclaimer,
  } as unknown as ValuationTrendResult;
}
