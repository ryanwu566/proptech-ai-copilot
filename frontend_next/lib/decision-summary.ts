import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, ValuationResult } from "@/lib/api";
import type { TerrainSafetyClass } from "@/lib/terrain-safety-gate";

export type DecisionSummary = {
  recommendation: "值得進一步看屋" | "需謹慎評估" | "暫不建議";
  reasons: string[];
  risks: string[];
  dataConfidence: "充足" | "有限" | "不足";
  checklist: { label: string; status: "通過" | "需確認" | "未完成"; detail: string }[];
};

// Terrain safety input for the decision summary. Callers pass the classification
// from terrain-safety-gate.ts when a full TerrainRiskResult is available. When
// only stored/reference evidence exists (e.g. export/share), callers pass
// "unproven" because stored evidence cannot prove known-low. Only "known_low"
// permits an unrestricted positive recommendation; "known_high" forces a
// non-positive conclusion; everything else is treated as incomplete/caution.
export type DecisionTerrainSafety = TerrainSafetyClass | "unproven";

export function buildDecisionSummary(
  propertySearch?: PropertySearchResult,
  valuation?: ValuationResult,
  loan?: LoanCalculationResult,
  holding?: HoldingCostResult,
  location?: LocationInsightResult,
  terrainSafety?: DecisionTerrainSafety,
): DecisionSummary {
  const risky = loan?.affordability_level === "risky" || holding?.affordability_level === "risky";
  const cautious = loan?.affordability_level === "tight" || holding?.affordability_level === "tight" || valuation?.confidence === "low" || location?.data_quality.status === "unavailable";
  // Terrain gate: known_high blocks a positive conclusion; anything that is not
  // positively known-low (unknown/unavailable/error/not_assessed/absent/
  // caution/limited/partial/no_match/unproven) prevents an unrestricted
  // "值得進一步看屋" all-clear. Undefined means the caller supplied no terrain
  // context and legacy behavior is preserved.
  const terrainKnownHigh = terrainSafety === "known_high";
  const terrainBlocksPositive = terrainSafety !== undefined && terrainSafety !== "known_low";
  const baseRecommendation = risky ? "暫不建議" : cautious ? "需謹慎評估" : valuation && (loan || holding || location) ? "值得進一步看屋" : "需謹慎評估";
  const recommendation = terrainKnownHigh
    ? "需謹慎評估"
    : terrainBlocksPositive && baseRecommendation === "值得進一步看屋"
      ? "需謹慎評估"
      : baseRecommendation;
  const reasons = [
    valuation ? `估價中位約 ${valuation.price_range.mid.toLocaleString()} 萬，已有 ${valuation.valuation_explanation.sample_count} 筆可比成交支持。` : "",
    loan && loan.affordability_level !== "risky" ? `貸款月付約 ${loan.monthly_payment.toLocaleString()} 元，負擔等級為 ${loan.affordability_level}。` : "",
    location?.location_score !== null && location?.location_score !== undefined ? `區位總分 ${location.location_score}，可作為實地看屋前的生活機能參考。` : "",
    propertySearch?.summary.matched_count ? `找房雷達找到 ${propertySearch.summary.matched_count} 筆符合條件的歷史成交。` : "",
  ].filter(Boolean).slice(0, 3);
  const risks = [
    holding?.affordability_level === "tight" || holding?.affordability_level === "risky" ? `每月總持有成本負擔為 ${holding.affordability_level}，需保留現金緩衝。` : "",
    valuation?.confidence === "low" ? "估價資料信心偏低，建議補查同社區或同路段成交。" : "",
    location?.data_quality.status !== "good" ? "區位資料來源有限，交通噪音、嫌惡設施與實際環境仍需現場確認。" : "",
    !loan ? "尚未完成貸款月付試算。" : "",
    !holding ? "尚未完成管理費、稅費與修繕等持有成本試算。" : "",
  ].filter(Boolean).slice(0, 3);
  const completed = [valuation, loan, holding, location].filter(Boolean).length;
  const dataConfidence = valuation?.confidence === "high" && location?.data_quality.status === "good" && completed >= 4 ? "充足" : valuation && completed >= 2 ? "有限" : "不足";
  const checklist: DecisionSummary["checklist"] = [
    { label: "價格是否合理", status: valuation ? (valuation.confidence === "low" ? "需確認" : "通過") : "未完成", detail: valuation ? valuation.confidence_reason : "先完成估價與可比成交確認。" },
    { label: "月付是否可承受", status: affordabilityStatus(loan?.affordability_level), detail: loan ? loan.affordability_message : "尚未完成貸款月付試算。" },
    { label: "持有成本是否可承受", status: affordabilityStatus(holding?.affordability_level), detail: holding ? holding.affordability_message : "尚未完成持有成本試算。" },
    { label: "區位是否符合需求", status: location ? (location.data_quality.status === "unavailable" ? "需確認" : "通過") : "未完成", detail: location ? location.valuation_context.explanation : "尚未完成區位分析。" },
    { label: "資料信心是否足夠", status: dataConfidence === "充足" ? "通過" : "需確認", detail: `目前資料信心：${dataConfidence}。` },
    { label: "是否建議實地看屋", status: recommendation === "值得進一步看屋" ? "通過" : recommendation === "暫不建議" ? "需確認" : "需確認", detail: terrainBlocksPositive && recommendation !== "值得進一步看屋" ? `${recommendation}；地勢與災害資料不足或未知，不代表沒有風險。` : recommendation },
    { label: "補查實際屋況與社區條件", status: "需確認", detail: "建議補查嫌惡設施、社區管理費、修繕紀錄與實際屋況。" },
  ];
  return { recommendation, reasons: reasons.length ? reasons : ["先完成找房、估價與成本試算，再形成決策結論。"], risks: risks.length ? risks : ["仍需實地確認屋況、交通噪音與社區管理狀況。"], dataConfidence, checklist };
}

function affordabilityStatus(level?: string): "通過" | "需確認" | "未完成" {
  if (!level || level === "unknown") return "未完成";
  return level === "comfortable" || level === "manageable" ? "通過" : "需確認";
}
