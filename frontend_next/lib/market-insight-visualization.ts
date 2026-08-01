import type { MarketResult } from "./api";
import { getMarketDisplayState, type MarketDisplayState } from "./market-result-state";

export type VisualFreshnessStatus = "fresh" | "aging" | "stale" | "unknown";
export type VisualCoverageStatus = "covered" | "not_covered" | "partial" | "unknown";

export type MarketHistoryPoint = {
  period: string;
  average_unit_price: number;
  transaction_count: number;
};

export type EvidenceKey = "source_name" | "source_updated_at" | "period" | "transaction_count" | "record_count" | "coverage_status" | "data_status" | "aggregation_method" | "caveat" | "disclaimer";

export type EvidenceItem = {
  key: EvidenceKey;
  label: string;
  value: string;
};

export type MarketInsightVisualModel = {
  state: MarketDisplayState;
  freshness: VisualFreshnessStatus;
  coverage: VisualCoverageStatus;
  metrics: {
    averageUnitPrice: number | null;
    medianUnitPrice: number | null;
    transactionVolume: number | null;
    recordCount: number | null;
  };
  history: MarketHistoryPoint[];
  evidence: EvidenceItem[];
  chartTextSummary: string;
};

function isPositiveFinite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function safeText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
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

export function sanitizeMarketHistory(result: MarketResult | undefined): MarketHistoryPoint[] {
  if (!result || getMarketDisplayState(result) !== "available" || !Array.isArray(result.history)) return [];
  return result.history.flatMap((point) => {
    const period = safeText(point.period);
    if (!period || !isPositiveFinite(point.average_unit_price) || !isPositiveFinite(point.transaction_count)) return [];
    return [{ period, average_unit_price: point.average_unit_price, transaction_count: point.transaction_count }];
  });
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
  return `已顯示 ${history.length} 個有效期別的平均單價與交易量趨勢。`;
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
  const metrics = {
    averageUnitPrice: state === "available" && result && isPositiveFinite(result.average_unit_price) ? result.average_unit_price : null,
    medianUnitPrice: state === "available" && result && isPositiveFinite(result.median_unit_price_ntd_sqm) ? result.median_unit_price_ntd_sqm : null,
    transactionVolume: state === "available" && result && isPositiveFinite(result.transaction_volume) ? result.transaction_volume : null,
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
    evidence: buildEvidenceItems(result),
    chartTextSummary: buildChartTextSummary(history),
  };
}
