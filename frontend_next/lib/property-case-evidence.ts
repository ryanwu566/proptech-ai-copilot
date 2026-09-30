import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, TerrainRiskResult, ValuationResult, ValuationTrendResult } from "@/lib/api";
import { buildTerrainReferenceEvidence, type StoredTerrainReferenceEvidenceV1 } from "@/lib/terrain-reference-evidence";
import { getActionableValuation, getPropertySearchDisplayState, getValuationTrendDisplayState } from "@/lib/valuation-result-state";
import { formatMonthlyTwd, formatPriceRangeWan, formatValuationConfidence, formatWan } from "@/lib/commercial/formatters";

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
  if (!result) return notAssessed("成交資料推估");
  const contract = result as ValuationResult & { valuation_status?: string; result_origin?: string; is_actionable?: boolean };
  if (contract.valuation_status === "demo" || contract.result_origin === "demo") return unavailable("成交資料推估", "示範資料不可轉入案件資料");
  if (contract.valuation_status === "no_data") return partial("成交資料推估", "可比成交資料不足");
  if (contract.valuation_status === "unavailable" || contract.result_origin === "none") return unavailable("成交資料推估", "目前無法取得價格推估");
  const actionable = getActionableValuation(result);
  if (!actionable) {
    return unavailable("成交資料推估", "價格推估資料無法安全判讀");
  }
  return {
    status: "trusted",
    source: "official_valuation",
    label: "成交資料推估",
    value: formatWan(actionable.estimateTotal),
    range: formatPriceRangeWan(actionable.priceRange.low, actionable.priceRange.high),
    confidence: formatValuationConfidence(result.confidence),
    reason: "可比成交資料符合目前推估條件；不是正式不動產估價報告",
    transferable: true,
  };
}

export function getPropertySearchEvidence(result?: PropertySearchResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("找房結果");
  const state = getPropertySearchDisplayState(result);
  if (state.kind === "available") return { status: "trusted", source: "official_valuation", label: "成交資料搜尋結果", value: `${result.summary.matched_count} 筆`, range: null, confidence: null, reason: "僅作物件搜尋參考", transferable: false };
  if (state.kind === "no_data") return partial("找房結果", "目前沒有符合條件的資料");
  return unavailable("找房結果", "找房資料暫時不可用");
}

export function getTrendEvidence(result?: ValuationTrendResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("行情趨勢");
  const state = getValuationTrendDisplayState(result);
  if (state.kind === "available") return { status: "trusted", source: "official_valuation", label: "區域成交趨勢", value: `${result.sample_count} 筆`, range: result.period_min && result.period_max ? `${result.period_min}–${result.period_max}` : null, confidence: formatValuationConfidence(result.confidence_level), reason: "僅作市場參考", transferable: false };
  if (state.kind === "no_data") return partial("行情趨勢", "行情資料不足", "official_valuation");
  return unavailable("行情趨勢", "行情資料暫時不可用");
}

export function getLoanEvidence(result?: LoanCalculationResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("貸款試算");
  return { status: "manual", source: "loan_reference", label: "貸款試算", value: formatWan(result.loan_amount_wan), range: null, confidence: null, reason: "依輸入條件計算，不是估價或核貸結果", transferable: false };
}

export function getHoldingEvidence(result?: HoldingCostResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("持有成本");
  return { status: "manual", source: "holding_reference", label: "持有成本", value: formatMonthlyTwd(result.monthly_total_holding_cost), range: null, confidence: null, reason: "依輸入條件計算的成本試算參考", transferable: false };
}

export function getLocationEvidence(result?: LocationInsightResult | null): PropertyCaseEvidence {
  if (!result) return notAssessed("位置分析");
  if (result.data_quality.status === "unavailable") return unavailable("位置分析", "位置資料暫時不可用");
  if (result.data_quality.status === "limited") return partial("位置分析", "位置資料涵蓋有限", "location_reference");
  return { status: "trusted", source: "location_reference", label: "位置分析", value: "證據可供判讀", range: null, confidence: null, reason: "請查看各項距離、設施與來源；不以綜合分數判定物件好壞", transferable: false };
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
  return { status: "manual", source: "tax_reference", label: "稅務條件初步檢查", value: "已取得初步檢查結果", range: null, confidence: null, reason: "請查看未符合條件與待確認項目；不構成稅務或法律意見", transferable: false };
}
