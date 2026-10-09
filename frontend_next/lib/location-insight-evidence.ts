import type { LocationInsightResult } from "./api";
// @ts-expect-error Native TS runner extension.
import { locationValuationExplanation } from "./location-evidence-context.ts";

/** Legacy counts alone cannot prove coverage. Apply at live display and Save/Reopen boundaries. */
export function normalizeLocationInsightEvidence(result: LocationInsightResult): LocationInsightResult {
  const evidence = result.risk_facility_evidence;
  const missing = result.data_quality?.missing_sources?.includes("risk_facilities");
  const observed = !missing && (evidence?.status === "available" || evidence?.status === "no_match")
    && typeof evidence.source === "string" && Boolean(evidence.source.trim())
    && typeof evidence.checked_at === "string" && Number.isFinite(Date.parse(evidence.checked_at))
    && typeof evidence.count === "number" && Number.isInteger(evidence.count) && evidence.count >= 0
    && (evidence.status !== "no_match" || evidence.count === 0);
  const status = observed ? evidence!.status : evidence?.status === "no_coverage" ? "no_coverage" : missing || evidence?.status === "unavailable" ? "unavailable" : "unknown";
  const normalized = { status, count: observed ? evidence!.count : null, source: typeof evidence?.source === "string" ? evidence.source : null,
    checked_at: typeof evidence?.checked_at === "string" && Number.isFinite(Date.parse(evidence.checked_at)) ? evidence.checked_at : null,
    reason: typeof evidence?.reason === "string" ? evidence.reason : "risk_facilities_coverage_not_preserved",
    limitation: typeof evidence?.limitation === "string" ? evidence.limitation : "來源涵蓋未保存；未知不等於零處設施或安全。" };
  // No supported source-to-score method exists for the risk dimension. Never retain the old 50.
  return { ...result, risk_facility_evidence: normalized,
    poi_summary: result.poi_summary && { ...result.poi_summary, risk_facility_count: normalized.count },
    category_scores: result.category_scores && { ...result.category_scores, risk_score: null }, location_score: null,
    buyer_fit: { self_use_family: "資料不足", commuter: "資料不足", investor: "資料不足", elderly: "資料不足" },
    strengths: (result.strengths ?? []).filter((item) => typeof item === "string" && /^(交通便利|日常採買與餐飲|教育資源|公園綠地|醫療資源)覆蓋較完整（\d+ 分）。$/.test(item)),
    weaknesses: [...(result.weaknesses ?? []).filter((item) => typeof item === "string" && /^(交通便利|日常採買與餐飲|教育資源|公園綠地|醫療資源)(覆蓋偏弱|資料目前無法取得)/.test(item)), "缺少完整風險評分證據，整體適用性資料不足。"],
    valuation_context: { supports_price_reasonableness: "unknown", explanation: locationValuationExplanation(typeof result.input?.property_price_wan === "number" ? result.input.property_price_wan : undefined, typeof result.input?.area_ping === "number" ? result.input.area_ping : undefined, null) },
    data_quality: { ...result.data_quality, warnings: (result.data_quality?.warnings ?? []).filter((item) => typeof item === "string" && !/中性\s*50|風險分數.*50/.test(item)) },
  };
}

export function riskFacilityReasonLabel(reason: string | null | undefined): string {
  return ({ risk_facilities_source_unavailable: "設施來源目前無法取得", risk_facilities_coverage_not_preserved: "設施涵蓋未隨快照保存", successful_query: "來源查詢成功", property_identity_mismatch: "設施證據與目前地址不一致" } as Record<string, string>)[reason ?? ""] ?? "依來源提供的查詢狀態；詳見保存限制";
}
