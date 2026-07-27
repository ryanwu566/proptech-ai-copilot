import type { SavedCase } from "@/lib/case-storage";

// 資料不足，排序信心較低；尚未快篩；本模組不以缺資料補成中性分數。

export type ComparedCase = {
  caseId: string;
  title: string;
  location: string;
  propertyPrice: number | null;
  areaPing: number | null;
  buildingType: string;
  completionRate: number;
  valuationMid: number | null;
  valuationRange: string;
  valuationConfidence: number | null;
  priceReasonableness: string;
  downPaymentWan: number | null;
  monthlyPayment: number | null;
  loanBurdenRatio: number | null;
  monthlyHoldingCost: number | null;
  holdingBurdenRatio: number | null;
  locationScore: number | null;
  transitScore: number | null;
  convenienceScore: number | null;
  educationScore: number | null;
  medicalScore: number | null;
  locationRiskGap: string;
  terrainRiskLevel: string;
  terrainRiskStatus: string;
  riskSignal: string;
  riskScore: number | null;
  mainRisks: string[];
  positives: string[];
  taxStatus: string;
  taxSignal: string;
  taxRiskScore: number | null;
  valuationTrusted: boolean;
};

export type ComparisonRank = {
  caseId: string;
  rank: number | null;
  score: number | null;
  label: string;
  reasons: string[];
  warnings: string[];
};

export type CaseComparisonResult = {
  cases: ComparedCase[];
  ranking: ComparisonRank[];
  bestCaseId?: string;
  summary: string;
  missingDataWarnings: string[];
  comparisonCoverageCount: number;
  comparisonCoverageRatio: number;
  comparisonStatus: "ready" | "partial" | "insufficient";
};

export function compareSavedCases(savedCases: SavedCase[]): CaseComparisonResult {
  const selected = savedCases.slice(0, 3).filter(isCaseCompareEligible);
  if (selected.length < 2) {
    return {
      cases: selected.map(toComparedCase),
      ranking: [],
      summary: "至少需要兩個具備案件名稱、地址與可比較價格的案件。",
      missingDataWarnings: ["比較資料不足，缺少案件名稱、地址或可比較價格。"],
      comparisonCoverageCount: 0,
      comparisonCoverageRatio: 0,
      comparisonStatus: "insufficient",
    };
  }
  const cases = selected.map(toComparedCase);
  const missingDataWarnings = [...new Set(cases.flatMap(missingWarnings))];
  const scored = cases.map(rankCase);
  const scorableCount = scored.filter((item) => item.score !== null).length;
  const comparisonStatus = scorableCount < 2 ? "insufficient" : scorableCount === cases.length ? "ready" : "partial";
  const ranking = comparisonStatus === "insufficient"
    ? scored.map((item) => ({ ...item, rank: null }))
    : scored.sort((a, b) => (b.score ?? -1) - (a.score ?? -1)).map((item, index) => ({ ...item, rank: index + 1 }));
  return {
    cases,
    ranking,
    bestCaseId: comparisonStatus === "insufficient" ? undefined : ranking.find((item) => item.rank === 1)?.caseId,
    summary: missingDataWarnings.length ? "部分資料尚未完成，以下比較只使用可辨識的資料。" : "比較結果僅供案件審閱參考。",
    missingDataWarnings,
    comparisonCoverageCount: scorableCount,
    comparisonCoverageRatio: cases.length ? scorableCount / cases.length : 0,
    comparisonStatus,
  };
}

export function isCaseCompareEligible(saved: SavedCase): boolean {
  return getCaseCompareMissingFields(saved).length === 0;
}

export function getCaseCompareMissingFields(saved: SavedCase): string[] {
  const missing: string[] = [];
  if (!saved.title.trim()) missing.push("案件名稱");
  if (![saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road].some((value) => value?.trim())) missing.push("物件地址／識別");
  if (!(saved.inputSummary.propertyPrice && saved.inputSummary.propertyPrice > 0)) missing.push("可比較價格資料");
  return missing;
}

function toComparedCase(saved: SavedCase): ComparedCase {
  const { valuation, loan, holdingCost, locationInsight, terrainRisk, riskSummary, taxOracle, inputs, valuationEvidence } = saved.data;
  const valuationTrusted = valuationEvidence?.transferable === true;
  return {
    caseId: saved.id,
    title: saved.title,
    location: [inputs.city, inputs.district, inputs.road].join(""),
    propertyPrice: positive(saved.inputSummary.propertyPrice),
    areaPing: positive(inputs.area_ping),
    buildingType: inputs.building_type || "尚未填寫",
    completionRate: saved.progress,
    valuationMid: valuationTrusted ? positive(valuation?.price_range.mid) : null,
    valuationRange: valuationTrusted && valuation ? valuation.price_range.low.toLocaleString() + "–" + valuation.price_range.high.toLocaleString() + " 萬" : "尚未完成",
    valuationConfidence: valuationTrusted ? finite(valuation?.confidence_score) : null,
    priceReasonableness: valuationTrusted ? riskSummary?.priceReasonableness.label ?? "未知" : "尚未完成",
    downPaymentWan: positive(loan?.down_payment_wan),
    monthlyPayment: positive(loan?.monthly_payment),
    loanBurdenRatio: finite(loan?.income_burden_ratio),
    monthlyHoldingCost: positive(holdingCost?.monthly_total_holding_cost),
    holdingBurdenRatio: finite(holdingCost?.income_burden_ratio),
    locationScore: finite(locationInsight?.location_score),
    transitScore: finite(locationInsight?.category_scores.transit_score),
    convenienceScore: finite(locationInsight?.category_scores.convenience_score),
    educationScore: finite(locationInsight?.category_scores.education_score),
    medicalScore: finite(locationInsight?.category_scores.medical_score),
    locationRiskGap: locationInsight ? locationInsight.data_quality.missing_sources.join("、") || "目前沒有額外缺口" : "尚未完成",
    terrainRiskLevel: terrainRisk?.overall.label ?? "尚未完成",
    terrainRiskStatus: terrainRisk ? terrainRisk.overall.level + " / " + terrainRisk.data_quality.status : "尚未完成",
    riskSignal: riskSummary?.overallSignal ?? "unknown",
    riskScore: finite(riskSummary?.overallScore),
    mainRisks: riskSummary?.riskFactors.slice(0, 3).map((item) => item.title) ?? [],
    positives: riskSummary?.positiveFactors.slice(0, 3).map((item) => item.title) ?? [],
    taxStatus: taxOracle ? "已完成" : "尚未取得資料",
    taxSignal: taxOracle?.signal_color ?? "unknown",
    taxRiskScore: finite(taxOracle?.risk_score),
    valuationTrusted,
  };
}

function rankCase(item: ComparedCase): ComparisonRank {
  const dimensions: Array<[number, number]> = [];
  if (item.riskScore !== null) dimensions.push([item.riskScore, 0.30]);
  const burden = burdenScore(item.loanBurdenRatio, item.holdingBurdenRatio);
  if (burden !== null) dimensions.push([burden, 0.25]);
  if (item.locationScore !== null) dimensions.push([item.locationScore, 0.20]);
  const valuation = valuationScore(item.valuationConfidence, item.priceReasonableness, item.valuationTrusted);
  if (valuation !== null) dimensions.push([valuation, 0.15]);
  const tax = taxScore(item.taxSignal);
  if (tax !== null) dimensions.push([tax, 0.10]);
  const weight = dimensions.reduce((sum, [, part]) => sum + part, 0);
  const score = weight === 0 ? null : Math.round(dimensions.reduce((sum, [value, part]) => sum + value * part, 0) / weight);
  const warnings = [...item.mainRisks];
  if (score === null) warnings.push("可評分資料不足，未產生分數或排名");
  if (item.completionRate < 70) warnings.push("資料尚未完整");
  return {
    caseId: item.caseId,
    rank: null,
    score,
    label: score === null ? "資料不足，無法評分" : score >= 75 ? "可優先審閱" : score >= 55 ? "需要進一步確認" : "資料或風險需審慎檢視",
    reasons: item.positives.slice(0, 3),
    warnings: warnings.slice(0, 3),
  };
}

function burdenScore(loan: number | null, holding: number | null): number | null {
  const ratios = [loan, holding].filter((value): value is number => value !== null);
  if (!ratios.length) return null;
  const worst = Math.max(...ratios);
  return worst <= 0.30 ? 95 : worst <= 0.40 ? 75 : worst <= 0.50 ? 50 : 20;
}

function valuationScore(confidence: number | null, price: string, trusted: boolean): number | null {
  if (!trusted || confidence === null) return null;
  const priceScore = price.includes("合理") ? 90 : price.includes("偏低") ? 80 : price.includes("偏高") ? 30 : null;
  return priceScore === null ? confidence : confidence * 0.6 + priceScore * 0.4;
}

function taxScore(signal: string): number | null {
  if (signal === "green") return 90;
  if (signal === "yellow") return 60;
  if (signal === "red") return 20;
  return null;
}

function missingWarnings(item: ComparedCase): string[] {
  return [
    ["估價", item.valuationMid],
    ["貸款", item.monthlyPayment],
    ["持有成本", item.monthlyHoldingCost],
    ["區位", item.locationScore],
    ["風險總評", item.riskScore],
    ["稅務參考", item.taxRiskScore],
  ].filter(([, value]) => value === null).map(([label]) => item.title + "：" + label + "尚未完成");
}

const comparisonFields: Array<[string, keyof ComparedCase, (value: never) => string]> = [
  ["位置", "location", text], ["總價", "propertyPrice", wan], ["坪數", "areaPing", numberText], ["屋型", "buildingType", text],
  ["完成度", "completionRate", percent], ["估價中位數", "valuationMid", wan], ["估價區間", "valuationRange", text],
  ["估價信心", "valuationConfidence", scoreText], ["月付", "monthlyPayment", yuan], ["持有成本", "monthlyHoldingCost", yuan],
  ["區位", "locationScore", scoreText], ["地勢風險", "terrainRiskStatus", text], ["風險總評", "riskScore", scoreText], ["稅務參考", "taxStatus", text],
];

export function buildCaseComparisonHtml(result: CaseComparisonResult): string {
  const rankingRows = result.ranking.map((row) => "<tr><td>" + (row.rank ?? "資料不足") + "</td><td>" + escapeHtml(result.cases.find((item) => item.caseId === row.caseId)?.title ?? "") + "</td><td>" + (row.score ?? "資料不足") + "</td><td>" + escapeHtml(row.reasons.join("、") || "無") + "</td><td>" + escapeHtml(row.warnings.join("、") || "無") + "</td></tr>").join("");
  const comparisonRows = comparisonFields.map(([label, field, format]) => "<tr><th>" + label + "</th>" + result.cases.map((item) => "<td>" + escapeHtml(format(item[field] as never)) + "</td>").join("") + "</tr>").join("");
  return "<!doctype html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\"><title>案件比較</title></head><body><h1>案件比較</h1><p>" + escapeHtml(result.summary) + "</p><p>可評分案件：" + result.comparisonCoverageCount + " / " + result.cases.length + "</p><table><tbody>" + rankingRows + comparisonRows + "</tbody></table><p>本比較不納入市場行情或通勤資訊，也不構成購買建議。</p></body></html>";
}

function positive(value: number | null | undefined): number | null { return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null; }
function finite(value: number | null | undefined): number | null { return typeof value === "number" && Number.isFinite(value) ? value : null; }
function text(value: unknown): string { return value === null || value === "" ? "尚未完成" : String(value); }
function numberText(value: unknown): string { return typeof value === "number" ? String(value) : "尚未完成"; }
function wan(value: unknown): string { return typeof value === "number" ? value.toLocaleString() + " 萬" : "尚未完成"; }
function yuan(value: unknown): string { return typeof value === "number" ? value.toLocaleString() + " 元" : "尚未完成"; }
function percent(value: unknown): string { return typeof value === "number" ? String(value) + "%" : "尚未完成"; }
function scoreText(value: unknown): string { return typeof value === "number" ? String(value) + " 分" : "尚未完成"; }
function escapeHtml(value: string): string { return value.replace(/[&<>\"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[char] ?? char); }
