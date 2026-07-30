import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, TerrainRiskResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import { buildTerrainReferenceEvidence, type StoredTerrainReferenceEvidenceV1 } from "@/lib/terrain-reference-evidence";
import { getPropertySearchDisplayState, getValuationTrendDisplayState } from "@/lib/valuation-result-state";

export type PropertyCaseEvidenceStatus = "trusted" | "manual" | "partial" | "unavailable" | "not_assessed";
export type PropertyCaseEvidenceSource = "official_valuation" | "manual_user_input" | "loan_reference" | "holding_reference" | "location_reference" | "terrain_reference" | "tax_reference" | "none";

export type PropertyCaseEvidence = {
  status: PropertyCaseEvidenceStatus;
  source: PropertyCaseEvidenceSource;
  label: string;
  value: string | null;
  range: string | null;
  confidence: string | null;
  reason: string;
  transferable: boolean;
};

const notAssessed = (label: string): PropertyCaseEvidence => ({
  status: "not_assessed", source: "none", label, value: null, range: null, confidence: null, reason: "尚未評估", transferable: false,
});

function unavailable(label: string, reason: string): PropertyCaseEvidence {
  return { status: "unavailable", source: "none", label, value: null, range: null, confidence: null, reason, transferable: false };
}

function partial(label: string, reason: string, source: PropertyCaseEvidenceSource = "none"): PropertyCaseEvidence {
  return { status: "partial", source, label, value: null, range: null, confidence: null, reason, transferable: false };
}

export function getTrustedValuationEvidence(result?: ValuationResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("官方估價");
  const contract = result as ValuationResult & { valuation_status?: string; result_origin?: string; is_actionable?: boolean };
  if (contract.valuation_status === "demo" || contract.result_origin === "demo") return unavailable("官方估價", "示範資料不可轉入案件資料");
  if (contract.valuation_status === "no_data") return partial("官方估價", "官方可比成交資料不足");
  if (contract.valuation_status === "unavailable" || contract.result_origin === "none") return unavailable("官方估價", "官方估價暫時不可用");
  const values = [result.estimate_total_price, result.estimate_unit_price_per_ping, result.price_range?.low, result.price_range?.mid, result.price_range?.high];
  if (contract.valuation_status !== "available" || contract.result_origin !== "official" || contract.is_actionable !== true || !values.every((value) => typeof value === "number" && Number.isFinite(value) && value > 0)) {
    return unavailable("官方估價", "估價契約或數值不完整");
  }
  if (!Array.isArray(result.comparables) || result.comparables.length < 3 || !result.comparables.every((row) => row.source === "official_plvr_opendata")) {
    return partial("官方估價", "官方可比成交筆數不足或來源不完整");
  }
  return {
    status: "trusted",
    source: "official_valuation",
    label: "官方估價",
    value: `${result.estimate_total_price} 萬元`,
    range: `${result.price_range.low}–${result.price_range.high} 萬元`,
    confidence: result.confidence,
    reason: "官方可比成交資料符合可轉移條件",
    transferable: true,
  };
}

export function getPropertySearchEvidence(result?: PropertySearchResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("找房結果");
  const state = getPropertySearchDisplayState(result);
  if (state.kind === "available") return { status: "trusted", source: "official_valuation", label: "官方找房結果", value: `${result.summary.matched_count} 筆`, range: null, confidence: null, reason: "僅作物件搜尋參考", transferable: false };
  if (state.kind === "no_data") return partial("找房結果", "目前沒有符合條件的資料");
  return unavailable("找房結果", "找房資料暫時不可用");
}

export function getTrendEvidence(result?: ValuationTrendResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("行情趨勢");
  const state = getValuationTrendDisplayState(result);
  if (state.kind === "available") return { status: "trusted", source: "official_valuation", label: "官方行情趨勢", value: `${result.sample_count} 筆`, range: result.period_min && result.period_max ? `${result.period_min}–${result.period_max}` : null, confidence: result.confidence_level, reason: "僅作市場參考", transferable: false };
  if (state.kind === "no_data") return partial("行情趨勢", "行情資料不足", "official_valuation");
  return unavailable("行情趨勢", "行情資料暫時不可用");
}

export function getLoanEvidence(result?: LoanCalculationResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("貸款試算");
  return { status: "manual", source: "loan_reference", label: "貸款試算", value: `${result.loan_amount_wan} 萬元`, range: null, confidence: null, reason: "使用者輸入的試算參考，不是估價證據", transferable: false };
}

export function getHoldingEvidence(result?: HoldingCostResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("持有成本");
  return { status: "manual", source: "holding_reference", label: "持有成本", value: `${result.monthly_total_holding_cost} 元／月`, range: null, confidence: null, reason: "使用者輸入的成本試算參考", transferable: false };
}

export function getLocationEvidence(result?: LocationInsightResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("位置分析");
  if (result.data_quality.status === "unavailable") return unavailable("位置分析", "位置資料暫時不可用");
  if (result.data_quality.status === "limited") return partial("位置分析", "位置資料涵蓋有限", "location_reference");
  return { status: "trusted", source: "location_reference", label: "位置分析", value: result.location_score === null ? null : `${result.location_score} 分`, range: null, confidence: null, reason: "僅作位置參考，不改變其他決策", transferable: false };
}

export function getTerrainEvidence(result?: TerrainRiskResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("地勢與災害");
  const reference = buildTerrainReferenceEvidence(result);
  if (["unavailable", "error", "unknown", "not_assessed"].includes(reference.status)) return unavailable("地勢與災害", "資料不足或暫時不可用，不代表沒有風險。");
  if (reference.status === "limited" || reference.status === "partial") return partial("地勢與災害", "目前只有部分資料可用，僅作看房風險參考。", "terrain_reference");
  return partial("地勢與災害", "地勢與災害結果僅作看房風險參考，不形成安全結論。", "terrain_reference");
}

export function getStoredTerrainReferenceEvidence(result?: StoredTerrainReferenceEvidenceV1): PropertyCaseEvidence {
  if (!result) return notAssessed("地勢與災害");
  if (result.status === "unknown" || result.status === "not_assessed") return notAssessed("地勢與災害");
  if (result.status === "unavailable" || result.status === "error") return unavailable("地勢與災害", "資料不足或暫時不可用，不代表沒有風險。");
  if (result.status === "no_match") return partial("地勢與災害", "目前未命中明確圖層訊號，不代表沒有風險。", "terrain_reference");
  return partial("地勢與災害", "地勢與災害參考資料已附加，僅作看房風險參考。", "terrain_reference");
}

export function getTaxEvidence(result?: TaxResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("稅務參考");
  return { status: "manual", source: "tax_reference", label: "稅務參考", value: result.signal_color, range: null, confidence: null, reason: "不構成稅務或法律意見", transferable: false };
}
