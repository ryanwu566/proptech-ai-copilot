import type { MarketResult } from "@/lib/api";

export type MarketInsightSnapshot = {
  county: string;
  district: string;
  period: string | null;
  transaction_type: string;
  median_unit_price_ntd_sqm: number | null;
  average_unit_price_ntd_sqm: number | null;
  median_total_price_ntd: number | null;
  transaction_count: number | null;
  source_release_id: string | null;
  generated_at: string;
  methodology_version: string | null;
  freshness_status: string | null;
  sample_status: string | null;
};

function safeNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
}

function safeText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim().slice(0, 160) : null;
}

export function buildMarketInsightSnapshot(result: MarketResult, generatedAt = new Date().toISOString()): MarketInsightSnapshot | null {
  const hasEvidenceStatus = result.data_status === "available" || result.data_status === "incomplete";
  const hasUsableCoverage = result.coverage_status === "covered" || result.coverage_status === "partial" || result.coverage_status === "nationwide";
  if (!hasEvidenceStatus || !hasUsableCoverage) return null;
  const county = safeText(result.county || result.city);
  const district = safeText(result.district);
  if (!county || !district) return null;
  return {
    county,
    district,
    period: safeText(result.period),
    transaction_type: "existing_sale",
    median_unit_price_ntd_sqm: safeNumber(result.median_unit_price_ntd_sqm),
    average_unit_price_ntd_sqm: safeNumber(result.mean_unit_price_ntd_sqm ?? result.average_unit_price),
    median_total_price_ntd: safeNumber(result.median_total_price_ntd),
    transaction_count: safeNumber(result.transaction_count),
    source_release_id: safeText(result.source_release_id),
    generated_at: safeText(generatedAt) || new Date(0).toISOString(),
    methodology_version: safeText(result.aggregation_version || result.aggregation_method),
    freshness_status: safeText(result.freshness_status),
    sample_status: safeText(result.sample_status),
  };
}
