import type { MarketResult } from "./api";
import { getMarketDisplayState, type MarketDisplayState } from "./market-result-state";

export type VisualFreshnessStatus = "fresh" | "aging" | "stale" | "unknown";
export type VisualCoverageStatus = "covered" | "not_covered" | "partial" | "unknown";

export type MarketHistoryPoint = {
  period: string;
  average_unit_price: number;
  transaction_count: number;
};

export type MarketDistributionPoint = { label: string; count: number };

export type MarketTrendStats = {
  periodCount: number;
  latest: MarketHistoryPoint | null;
  previous: MarketHistoryPoint | null;
  periodChange: number | null;
  averageUnitPrice: number | null;
  maxPoint: MarketHistoryPoint | null;
  minPoint: MarketHistoryPoint | null;
  totalTransactions: number | null;
};

export type EvidenceKey = "source_name" | "source_updated_at" | "period" | "transaction_count" | "record_count" | "coverage_status" | "data_status" | "aggregation_method" | "caveat" | "disclaimer";

export type EvidenceItem = {
  key: EvidenceKey;
  label: string;
  value: string;
};

export const MARKET_METRIC_PRESENTATION_CONTRACT = {
  averageUnitPrice: {
    sourceField: "average_unit_price",
    unit: "wan_ntd_per_ping",
    converted: false,
  },
  medianUnitPrice: {
    sourceField: "median_unit_price_ntd_sqm",
    unit: "ntd_per_square_meter",
    converted: false,
  },
  transactionCount: {
    sourceFields: ["transaction_count", "transaction_volume"],
    periodScope: "result.period",
  },
} as const;

export type MarketMetricPresentation = {
  averageUnitPrice: number | null;
  transactionCount: number | null;
  period: string | null;
  medianUnitPrice: number | null;
  meanUnitPriceNtdSqm: number | null;
  medianTotalPrice: number | null;
  periodChange: number | null;
  yearOverYearChange: number | null;
  inclusionCount: number | null;
  exclusionCount: number | null;
  sampleStatus: string | null;
  freshnessStatus: string | null;
  sourceName: string | null;
  sourceUpdatedAt: string | null;
  coverageStatus: MarketResult["coverage_status"] | null;
};

export type MarketInsightVisualModel = {
  state: MarketDisplayState;
  freshness: VisualFreshnessStatus;
  coverage: VisualCoverageStatus;
  metrics: {
    averageUnitPrice: number | null;
    medianUnitPrice: number | null;
    medianTotalPrice: number | null;
    transactionVolume: number | null;
    recordCount: number | null;
  };
  history: MarketHistoryPoint[];
  trendStats: MarketTrendStats;
  priceDistribution: MarketDistributionPoint[];
  buildingTypeDistribution: MarketDistributionPoint[];
  ageBandDistribution: MarketDistributionPoint[];
  evidence: EvidenceItem[];
  chartTextSummary: string;
};

function isPositiveFinite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function safeText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function optionalStatus(value: unknown): string | null {
  const status = safeText(value);
  return status && status !== "unknown" && status !== "unavailable" ? status : null;
}

function readFreshness(result: MarketResult): VisualFreshnessStatus {
  const candidate = (result as unknown as { freshness_status?: unknown }).freshness_status;
  return candidate === "fresh" || candidate === "aging" || candidate === "stale" ? candidate : "unknown";
}

function mapCoverage(result: MarketResult): VisualCoverageStatus {
  if (result.coverage_status === "covered" || result.coverage_status === "nationwide") return "covered";
  if (result.coverage_status === "not_covered") return "not_covered";
  if (result.coverage_status === "partial") return "partial";
  return "unknown";
}

export function getMarketMetricPresentation(result: MarketResult): MarketMetricPresentation {
  const isAvailable = getMarketDisplayState(result) === "available";
  const transactionCount = isPositiveFinite(result.transaction_count)
    ? result.transaction_count
    : isPositiveFinite(result.transaction_volume)
      ? result.transaction_volume
      : null;
  return {
    averageUnitPrice: isAvailable && isPositiveFinite(result.average_unit_price) ? result.average_unit_price : null,
    transactionCount: isAvailable ? transactionCount : null,
    period: isAvailable ? safeText(result.period) : null,
    medianUnitPrice: isAvailable && isPositiveFinite(result.median_unit_price_ntd_sqm) ? result.median_unit_price_ntd_sqm : null,
    meanUnitPriceNtdSqm: isAvailable && isPositiveFinite(result.mean_unit_price_ntd_sqm) ? result.mean_unit_price_ntd_sqm : null,
    medianTotalPrice: isAvailable && isPositiveFinite(result.median_total_price_ntd) ? result.median_total_price_ntd : null,
    periodChange: isAvailable && isFiniteNumber(result.period_change) ? result.period_change : null,
    yearOverYearChange: isAvailable && isFiniteNumber(result.year_over_year_change) ? result.year_over_year_change : null,
    inclusionCount: isAvailable && Number.isInteger(result.inclusion_count) && isPositiveFinite(result.inclusion_count) ? result.inclusion_count : null,
    exclusionCount: isAvailable && Number.isInteger(result.exclusion_count) && isPositiveFinite(result.exclusion_count) ? result.exclusion_count : null,
    sampleStatus: isAvailable ? optionalStatus(result.sample_status) : null,
    freshnessStatus: isAvailable ? optionalStatus(result.freshness_status) : null,
    sourceName: isAvailable ? safeText(result.source_name) : null,
    sourceUpdatedAt: isAvailable ? safeText(result.source_updated_at) : null,
    coverageStatus: isAvailable ? result.coverage_status : null,
  };
}

export function sanitizeMarketHistory(result: MarketResult | undefined): MarketHistoryPoint[] {
  if (!result || getMarketDisplayState(result) !== "available" || !Array.isArray(result.history)) return [];
  return result.history.flatMap((point) => {
    const period = safeText(point.period);
    if (!period || !isPositiveFinite(point.average_unit_price) || !isPositiveFinite(point.transaction_count)) return [];
    return [{ period, average_unit_price: point.average_unit_price, transaction_count: point.transaction_count }];
  }).slice(0, 6);
}

export function buildMarketTrendStats(history: readonly MarketHistoryPoint[]): MarketTrendStats {
  const points = history.flatMap((point) => {
    const period = safeText(point.period);
    const validAverage = isFiniteNumber(point.average_unit_price) && point.average_unit_price >= 0;
    const validCount = Number.isInteger(point.transaction_count) && point.transaction_count >= 0;
    if (!period || !validAverage || !validCount) return [];
    return [{
      period,
      average_unit_price: point.average_unit_price,
      transaction_count: point.transaction_count,
    }];
  }).slice(0, 6);
  const latest = points[0] ?? null;
  const previous = points[1] ?? null;
  const periodChange = latest && previous && previous.average_unit_price > 0
    ? (latest.average_unit_price - previous.average_unit_price) / previous.average_unit_price
    : null;
  if (!points.length) {
    return {
      periodCount: 0,
      latest: null,
      previous: null,
      periodChange: null,
      averageUnitPrice: null,
      maxPoint: null,
      minPoint: null,
      totalTransactions: null,
    };
  }
  const totalUnitPrice = points.reduce((sum, point) => sum + point.average_unit_price, 0);
  const totalTransactions = points.reduce((sum, point) => sum + point.transaction_count, 0);
  const maxPoint = points.reduce((current, point) => point.average_unit_price > current.average_unit_price ? point : current);
  const minPoint = points.reduce((current, point) => point.average_unit_price < current.average_unit_price ? point : current);
  return {
    periodCount: points.length,
    latest,
    previous,
    periodChange,
    averageUnitPrice: totalUnitPrice / points.length,
    maxPoint,
    minPoint,
    totalTransactions,
  };
}

export function formatMarketPeriodChange(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return "—";
  return `${value > 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

export function sanitizeMarketDistribution(result: MarketResult | undefined, field: "price_distribution" | "building_type_distribution" | "age_band_distribution"): MarketDistributionPoint[] {
  if (!result || getMarketDisplayState(result) !== "available" || !Array.isArray(result[field])) return [];
  return result[field].flatMap((point) => {
    const label = safeText(point?.label);
    const count = Number(point?.count);
    if (!label || !Number.isInteger(count) || count <= 0 || count > 2_000_000) return [];
    return [{ label, count }];
  }).slice(0, 12);
}

export function formatMarketMetric(value: number | null | undefined, suffix = ""): string {
  if (!isPositiveFinite(value)) return "尚無可用資料";
  return `${value.toLocaleString()}${suffix}`;
}

export function buildEvidenceItems(result: MarketResult | undefined): EvidenceItem[] {
  if (!result) return [];
  const items: Array<[EvidenceKey, string, unknown]> = [
    ["source_name", "資料來源", result.source_name],
    ["source_updated_at", "資料更新日期", result.source_updated_at],
    ["period", "資料期間", result.period],
    ["transaction_count", "交易筆數", result.transaction_count],
    ["record_count", "彙整紀錄數", result.record_count],
    ["coverage_status", "涵蓋狀態", result.coverage_status],
    ["data_status", "資料狀態", result.data_status],
    ["aggregation_method", "彙整方法", result.aggregation_method],
    ["caveat", "資料限制", result.caveat],
    ["disclaimer", "使用提醒", result.disclaimer],
  ];
  return items.flatMap(([key, label, value]) => {
    if (value === null || value === undefined || value === "") return [];
    return [{ key, label, value: String(value) }];
  });
}

export function buildChartTextSummary(history: MarketHistoryPoint[]): string {
  if (history.length < 2) return "目前沒有足夠的有效期別資料可繪製趨勢。";
  return `已顯示 ${history.length} 個有效期別的平均單價（萬元／坪）與交易筆數（筆）趨勢。`;
}

export function selectChartLabelIndexes(count: number): number[] {
  if (count <= 0) return [];
  if (count <= 6) return Array.from({ length: count }, (_, index) => index);
  const interval = count <= 12 ? 2 : count <= 24 ? 4 : 8;
  return Array.from(new Set([0, ...Array.from({ length: Math.ceil((count - 1) / interval) }, (_, index) => Math.min(count - 1, (index + 1) * interval)), count - 1]));
}

export function buildMarketInsightVisualModel(result: MarketResult | undefined): MarketInsightVisualModel {
  const state = getMarketDisplayState(result);
  const history = sanitizeMarketHistory(result);
  const presentation = result ? getMarketMetricPresentation(result) : null;
  const metrics = {
    averageUnitPrice: presentation?.averageUnitPrice ?? null,
    medianUnitPrice: presentation?.medianUnitPrice ?? null,
    medianTotalPrice: presentation?.medianTotalPrice ?? null,
    transactionVolume: presentation?.transactionCount ?? null,
    recordCount: state === "available" && result && isPositiveFinite(result.record_count ?? result.transaction_count)
      ? (result.record_count ?? result.transaction_count ?? null)
      : null,
  };
  return {
    state,
    freshness: result ? readFreshness(result) : "unknown",
    coverage: result ? mapCoverage(result) : "unknown",
    metrics,
    history,
    trendStats: buildMarketTrendStats(history),
    priceDistribution: sanitizeMarketDistribution(result, "price_distribution"),
    buildingTypeDistribution: sanitizeMarketDistribution(result, "building_type_distribution"),
    ageBandDistribution: sanitizeMarketDistribution(result, "age_band_distribution"),
    evidence: buildEvidenceItems(result),
    chartTextSummary: buildChartTextSummary(history),
  };
}
