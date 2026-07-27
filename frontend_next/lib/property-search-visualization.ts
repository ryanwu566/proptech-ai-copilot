import type { PropertySearchResult } from "./api";
import { getPropertySearchDisplayState, type ValuationDisplayKind } from "./valuation-result-state";

export type PropertyRangePoint = { label: string; low: number; median: number; high: number; sampleCount: number };
export type PropertySearchVisualModel = {
  state: ValuationDisplayKind;
  actionable: boolean;
  metrics: { matchedCount: number | null; districtCount: number | null; roadCount: number | null; sampleCount: number | null };
  districtRanges: PropertyRangePoint[];
  roadRanges: PropertyRangePoint[];
  evidence: { key: string; label: string; value: string }[];
};

const positive = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value > 0;
const ordered = (low: unknown, median: unknown, high: unknown): boolean => positive(low) && positive(median) && positive(high) && low <= median && median <= high;

function ranges(items: PropertySearchResult["district_suggestions"] | PropertySearchResult["road_suggestions"]): PropertyRangePoint[] {
  return items.flatMap((item) => {
    if (!item.road && !item.district) return [];
    if (!positive(item.p25_total_price) || !positive(item.median_total_price) || !positive(item.p75_total_price) || !ordered(item.p25_total_price, item.median_total_price, item.p75_total_price) || !Number.isInteger(item.sample_count) || item.sample_count <= 0) return [];
    return [{ label: item.road ? `${item.district} ${item.road}` : `${item.city} ${item.district}`, low: item.p25_total_price, median: item.median_total_price, high: item.p75_total_price, sampleCount: item.sample_count }];
  });
}

export function buildPropertySearchVisualModel(result: PropertySearchResult | undefined): PropertySearchVisualModel {
  if (!result) return { state: "unavailable", actionable: false, metrics: { matchedCount: null, districtCount: null, roadCount: null, sampleCount: null }, districtRanges: [], roadRanges: [], evidence: [] };
  const display = getPropertySearchDisplayState(result);
  const summary = result.summary;
  return {
    state: display.kind,
    actionable: display.actionable,
    metrics: {
      matchedCount: display.kind === "available" && summary.matched_count > 0 ? summary.matched_count : null,
      districtCount: display.kind === "available" && summary.district_count > 0 ? summary.district_count : null,
      roadCount: display.kind === "available" && summary.road_count > 0 ? summary.road_count : null,
      sampleCount: display.kind === "available" && result.matched_transactions.length > 0 ? result.matched_transactions.length : null,
    },
    districtRanges: display.kind === "available" ? ranges(result.district_suggestions) : [],
    roadRanges: display.kind === "available" ? ranges(result.road_suggestions) : [],
    evidence: ([
      ["data_source_label", "資料來源", summary.data_source_label],
      ["matched_count", "符合筆數", summary.matched_count],
      ["period", "資料期間", summary.period_min && summary.period_max ? `${summary.period_min} ~ ${summary.period_max}` : null],
      ["methodology", "方法說明", result.methodology],
      ["disclaimer", "使用提醒", result.disclaimer],
    ] as Array<[string, string, unknown]>).flatMap(([key, label, value]) => value === null || value === undefined || value === "" ? [] : [{ key, label, value: String(value) }]),
  };
}
