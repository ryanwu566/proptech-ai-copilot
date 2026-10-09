import type { LocationAdvisoryContext, LocationInsightResult } from "./api";

type SpatialLocationContext = { city?: string; district?: string; road?: string; address?: string };

// Provider language/configuration is fixed by this UI contract. Non-spatial
// advisory inputs must not invalidate geocoding, POIs or village demographics.
export function locationEvidenceKey(context: SpatialLocationContext | undefined, radius: number): string {
  return JSON.stringify([context?.city, context?.district, context?.road, context?.address, radius]);
}

// Updates the backend's purely local advisory inputs without changing provider
// observations, their timestamps, acceptance or price-reasonableness status.
export function locationValuationExplanation(price: number | undefined, area: number | undefined, score: number | null): string {
  if (price === undefined || area === undefined || !Number.isFinite(price) || !Number.isFinite(area) || price <= 0 || area <= 0) {
    return "未提供完整價格與坪數，區位資料只能補充生活機能，不能判斷價格合理性。";
  }
  const unitPrice = Math.round(price / area * 10) / 10;
  return `本物件約 ${unitPrice} 萬／坪；區位總分 ${score ?? "資料不足"}，仍需搭配可比成交判斷價格。`;
}

export function createLocationAdvisoryContext(price: unknown, area: unknown): LocationAdvisoryContext {
  const amount = (value: unknown) => typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null;
  return { version: 1, property_price_wan: amount(price), area_ping: amount(area) };
}

type AdvisoryEvidence = Pick<LocationInsightResult, "resolved_location" | "location_score" | "valuation_context" | "data_quality" | "geocoding_acceptance" | "advisory_context">;

export function withLocationAdvisoryContext<T extends AdvisoryEvidence>(result: T, price: number | undefined, area: number | undefined): T {
  if (!result.resolved_location || result.data_quality.status === "unavailable" || result.geocoding_acceptance?.accepted_for_analysis === false) return result;
  const advisory_context = createLocationAdvisoryContext(price, area);
  const explanation = locationValuationExplanation(advisory_context.property_price_wan ?? undefined, advisory_context.area_ping ?? undefined, result.location_score);
  return explanation === result.valuation_context.explanation && result.advisory_context?.version === 1
    && result.advisory_context.property_price_wan === advisory_context.property_price_wan && result.advisory_context.area_ping === advisory_context.area_ping ? result : {
    ...result, advisory_context, valuation_context: { ...result.valuation_context, explanation },
  };
}
