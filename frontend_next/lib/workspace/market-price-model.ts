import type { MarketResult, ValuationResult, ValuationTrendResult } from "../api";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { formatPriceRangeWan, formatWan, formatWanPerPing, PRICE_CONCEPT_LABELS } from "../commercial/formatters.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getMarketDisplayState, marketStateHasEvidence } from "../market-result-state.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { getActionableValuation, getStoredActionableValuation } from "../valuation-result-state.ts";

export type MarketPriceEvidenceStatus = "not_started" | "available" | "insufficient" | "limited" | "unavailable" | "stale";

export type MarketPriceValue = {
  label: string;
  formatted: string;
};

export type MarketPriceModel = {
  isStale: boolean;
  priceContext: {
    askingPrice: MarketPriceValue | null;
    activePrice: MarketPriceValue;
    estimateRange: MarketPriceValue | null;
    marketMedianTotal: MarketPriceValue | null;
    marketMedianUnit: MarketPriceValue | null;
  };
  market: {
    status: MarketPriceEvidenceStatus;
    result: MarketResult | null;
    history: MarketResult["history"];
    scopeLabel: string | null;
    analysisLevel: string | null;
    sampleCount: number | null;
    fallbackApplied: boolean;
  };
  valuation: {
    status: MarketPriceEvidenceStatus;
    result: ValuationResult | null;
    trend: ValuationTrendResult | null;
    estimate: MarketPriceValue | null;
    comparablesAvailable: boolean;
    comparables: ValuationResult["comparables"];
  };
  source: {
    sourceName: string | null;
    effectivePeriod: string | null;
    updatedAt: string | null;
  };
  primaryFinding: string;
  overview: {
    priceBasis: "asking" | "estimate" | "manual";
    evidenceStatus: MarketPriceEvidenceStatus;
    estimateRange: string | null;
    marketRange: string | null;
    unresolvedChecks: string[];
    freshness: string | null;
  };
};

type BuildMarketPriceModelInput = {
  identityConfirmed?: boolean;
  activePriceBasis: "asking" | "estimate" | "manual";
  activePriceWan?: number;
  askingPriceWan?: number;
  market?: MarketResult;
  valuation?: ValuationResult;
  trend?: ValuationTrendResult;
  stale: boolean;
  marketStale?: boolean;
  valuationStale?: boolean;
  marketFresh?: boolean;
  valuationFresh?: boolean;
};

function positive(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function period(result: MarketResult | undefined): string | null {
  const start = text(result?.period_min)?.replace("-", "/");
  const end = text(result?.period_max)?.replace("-", "/");
  if (start && end) return `${start}–${end}`;
  return text(result?.period);
}

function marketStatus(result: MarketResult | undefined, stale: boolean, fresh: boolean): MarketPriceEvidenceStatus {
  if (!result) return "not_started";
  const displayState = getMarketDisplayState(result);
  if (displayState === "no_data" || result.sample_status === "insufficient" || result.sample_status === "no_data") return "insufficient";
  if (displayState === "unavailable" || result.sample_status === "unavailable") return "unavailable";
  if (stale || displayState === "stale") return "stale";
  if (fresh) return "available";
  return "limited";
}

function primaryFinding(askingPriceWan: number | undefined, medianTotalWan: number | null): string {
  if (!positive(askingPriceWan)) return "目前尚未提供開價，先以成交證據建立價格比較基準。";
  if (!positive(medianTotalWan)) return "已記錄開價，但區域成交總價中位數仍不足以進行比較。";
  const difference = (askingPriceWan - medianTotalWan) / medianTotalWan;
  if (Math.abs(difference) < 0.05) return "開價與目前觀察到的市場成交總價中位數接近。";
  return difference > 0
    ? "開價高於目前觀察到的市場成交總價中位數，仍需以物件條件與可比成交確認差異。"
    : "開價低於目前觀察到的市場成交總價中位數，仍需確認物件條件與證據範圍。";
}

export function buildMarketPriceModel(input: BuildMarketPriceModelInput): MarketPriceModel {
  const marketStale = input.stale || input.marketStale === true;
  const valuationStale = input.stale || input.valuationStale === true;
  const actionableValuation = getActionableValuation(input.valuation) ?? getStoredActionableValuation(input.valuation);
  const status = marketStatus(input.market, marketStale, input.marketFresh === true);
  const displayState = getMarketDisplayState(input.market);
  const marketHasEvidence = Boolean(input.market)
    && marketStateHasEvidence(displayState)
    && input.market?.sample_status !== "insufficient"
    && input.market?.sample_status !== "no_data"
    && input.market?.sample_status !== "unavailable";
  const medianTotalWan = marketHasEvidence && positive(input.market?.median_total_price) ? input.market.median_total_price : null;
  const medianUnitWan = marketHasEvidence && positive(input.market?.median_unit_price_per_ping) ? input.market.median_unit_price_per_ping : null;
  const validatedActivePriceWan = input.activePriceBasis === "estimate"
    ? valuationStale ? undefined : actionableValuation?.estimateTotal
    : input.activePriceWan;
  const activeLabel = input.activePriceBasis === "manual"
    ? PRICE_CONCEPT_LABELS.user_entered_price
    : input.activePriceBasis === "estimate"
      ? PRICE_CONCEPT_LABELS.system_estimate
      : PRICE_CONCEPT_LABELS.asking_price;
  const marketRange = marketHasEvidence
    && positive(input.market?.p25_unit_price_per_ping)
    && positive(input.market?.p75_unit_price_per_ping)
    && input.market.p25_unit_price_per_ping <= input.market.p75_unit_price_per_ping
    ? `${formatWanPerPing(input.market.p25_unit_price_per_ping).replace(" 萬元／坪", "")}–${formatWanPerPing(input.market.p75_unit_price_per_ping)}`
    : null;
  const estimateRange = actionableValuation
    ? {
        label: PRICE_CONCEPT_LABELS.price_range,
        formatted: formatPriceRangeWan(actionableValuation.priceRange.low, actionableValuation.priceRange.high),
      }
    : null;
  const valuationStatus: MarketPriceEvidenceStatus = valuationStale && actionableValuation
    ? "stale"
    : actionableValuation
      ? input.valuationFresh ? "available" : "limited"
      : input.valuation
        ? "unavailable"
        : "not_started";
  const unresolvedChecks = input.stale
    ? ["重新確認目前物件後再採用價格證據"]
    : input.valuationStale
      ? ["價格推估輸入已變更，請重新取得可安全判讀的價格推估"]
    : input.valuation && !actionableValuation
      ? ["重新取得可安全判讀的價格推估"]
      : [];

  return {
    isStale: marketStale || valuationStale,
    priceContext: {
      askingPrice: positive(input.askingPriceWan) ? { label: PRICE_CONCEPT_LABELS.asking_price, formatted: formatWan(input.askingPriceWan) } : null,
      activePrice: { label: activeLabel, formatted: formatWan(validatedActivePriceWan, "not_provided") },
      estimateRange,
      marketMedianTotal: medianTotalWan ? { label: PRICE_CONCEPT_LABELS.market_median, formatted: formatWan(medianTotalWan) } : null,
      marketMedianUnit: medianUnitWan ? { label: PRICE_CONCEPT_LABELS.market_median, formatted: formatWanPerPing(medianUnitWan) } : null,
    },
    market: {
      status,
      result: input.market ?? null,
      history: marketHasEvidence
        ? (input.market?.history ?? []).filter((row) => typeof row === "object" && row !== null && text(row.period) && positive(row.average_unit_price) && Number.isInteger(row.transaction_count) && row.transaction_count > 0)
        : [],
      scopeLabel: marketHasEvidence ? text(input.market?.effective_scope_label) : null,
      analysisLevel: marketHasEvidence ? text(input.market?.effective_analysis_level ?? input.market?.analysis_level) : null,
      sampleCount: marketHasEvidence && Number.isInteger(input.market?.effective_sample_count) && input.market!.effective_sample_count! > 0
        ? input.market!.effective_sample_count!
        : null,
      fallbackApplied: marketHasEvidence && input.market?.fallback_applied === true,
    },
    valuation: {
      status: valuationStatus,
      result: input.valuation ?? null,
      trend: input.trend ?? null,
      estimate: actionableValuation
        ? { label: PRICE_CONCEPT_LABELS.system_estimate, formatted: formatWan(actionableValuation.estimateTotal) }
        : null,
      comparablesAvailable: Boolean(actionableValuation?.result.comparables.length),
      comparables: actionableValuation?.result.comparables ?? [],
    },
    source: {
      sourceName: text(input.market?.source_name),
      effectivePeriod: period(input.market),
      updatedAt: text(input.market?.source_updated_at),
    },
    primaryFinding: input.identityConfirmed === false
      ? "物件身分尚未確認；保留開價與市場觀察，但不進行物件價格比較。"
      : primaryFinding(input.askingPriceWan, medianTotalWan),
    overview: {
      priceBasis: input.activePriceBasis,
      evidenceStatus: status,
      estimateRange: estimateRange?.formatted ?? null,
      marketRange,
      unresolvedChecks,
      freshness: text(input.market?.source_updated_at),
    },
  };
}
