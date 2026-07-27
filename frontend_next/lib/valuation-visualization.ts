import type { ValuationResult, ValuationTrendResult } from "./api";
import { getValuationDisplayState, getValuationTrendDisplayState, type ValuationDisplayKind } from "./valuation-result-state";
import { selectChartLabelIndexes } from "./market-insight-visualization";

export type ValuationEvidenceItem = { key: string; label: string; value: string };
export type ValuationTrendPoint = { period: string; median: number; p25: number; p75: number; transactionCount: number };
export type ValuationVisualModel = {
  state: ValuationDisplayKind;
  actionable: boolean;
  metrics: { estimateTotal: number | null; estimateUnit: number | null; confidence: number | null; comparableCount: number | null };
  priceRange: { low: number; mid: number; high: number } | null;
  distribution: { p25: number; median: number; p75: number; estimate: number } | null;
  trend: ValuationTrendPoint[];
  evidence: ValuationEvidenceItem[];
};

const positive = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value > 0;
const ordered = (low: unknown, mid: unknown, high: unknown): boolean => positive(low) && positive(mid) && positive(high) && low <= mid && mid <= high;
const text = (value: unknown): string | null => typeof value === "string" && value.trim() ? value.trim() : null;

function validRange(low: unknown, mid: unknown, high: unknown): { low: number; mid: number; high: number } | null {
  if (!positive(low) || !positive(mid) || !positive(high) || !ordered(low, mid, high)) return null;
  return { low, mid, high };
}

function buildTrend(result: ValuationTrendResult | undefined): ValuationTrendPoint[] {
  if (!result || getValuationTrendDisplayState(result).kind !== "available") return [];
  return result.monthly_series.flatMap((point) => {
    const period = text(point.period);
    const range = validRange(point.p25_unit_price_per_ping, point.median_unit_price_per_ping, point.p75_unit_price_per_ping);
    if (!period || !range || !Number.isInteger(point.transaction_count) || point.transaction_count <= 0) return [];
    return [{ period, median: range.mid, p25: range.low, p75: range.high, transactionCount: point.transaction_count }];
  });
}

function evidence(result: ValuationResult | undefined, trend: ValuationTrendResult | undefined): ValuationEvidenceItem[] {
  if (!result) return [];
  const values: Array<[string, string, unknown]> = [
    ["estimate_level", "估價層級", result.estimate_level],
    ["estimate_source_label", "估價資料來源", result.estimate_source_label],
    ["data_composition", "資料組成", result.data_composition],
    ["candidate_pool_size", "可比候選數", result.candidate_pool_size],
    ["official_same_road_count", "官方同路段筆數", result.official_same_road_count],
    ["official_same_district_count", "官方同區筆數", result.official_same_district_count],
    ["freshness_status", "資料新鮮度", result.data_status.freshness_status],
    ["newest_effective_period", "最新有效期間", result.data_status.newest_effective_period],
    ["official_records_count", "官方紀錄數", result.data_status.official_records_count],
    ["trend_period", "趨勢期間", trend?.effective_period_min && trend.effective_period_max ? `${trend.effective_period_min} ~ ${trend.effective_period_max}` : null],
    ["methodology", "估算方法", result.methodology.join("；")],
    ["disclaimer", "使用提醒", result.disclaimer],
  ];
  return values.flatMap(([key, label, value]) => value === null || value === undefined || value === "" ? [] : [{ key, label, value: String(value) }]);
}

export function buildValuationVisualModel(result: ValuationResult | undefined, trend?: ValuationTrendResult): ValuationVisualModel {
  if (!result) return { state: "unavailable", actionable: false, metrics: { estimateTotal: null, estimateUnit: null, confidence: null, comparableCount: null }, priceRange: null, distribution: null, trend: [], evidence: [] };
  const display = getValuationDisplayState(result);
  const priceRange = display.kind === "available" ? validRange(result.price_range.low, result.price_range.mid, result.price_range.high) : null;
  const distribution = display.kind === "available" ? validRange(result.unit_price_distribution.p25, result.unit_price_distribution.weighted_median, result.unit_price_distribution.p75) : null;
  const estimate = display.kind === "available" && positive(result.estimate_unit_price_per_ping) ? result.estimate_unit_price_per_ping : null;
  return {
    state: display.kind,
    actionable: display.actionable && Boolean(priceRange && distribution && estimate),
    metrics: {
      estimateTotal: display.kind === "available" && positive(result.estimate_total_price) ? result.estimate_total_price : null,
      estimateUnit: estimate,
      confidence: display.kind === "available" && positive(result.confidence_score) ? result.confidence_score : null,
      comparableCount: display.kind === "available" && Number.isInteger(result.comparables.length) ? result.comparables.length : null,
    },
    priceRange,
    distribution: display.kind === "available" && distribution && estimate ? { p25: distribution.low, median: distribution.mid, p75: distribution.high, estimate } : null,
    trend: buildTrend(trend),
    evidence: evidence(result, trend),
  };
}

export { positive as isPositiveValuationMetric, selectChartLabelIndexes };
