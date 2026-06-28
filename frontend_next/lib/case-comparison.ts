import type { SavedCase } from "@/lib/case-storage";

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
};

export type CaseComparisonResult = {
  cases: ComparedCase[];
  ranking: Array<{ caseId: string; rank: number; score: number | null; label: string; reasons: string[]; warnings: string[] }>;
  bestCaseId?: string;
  summary: string;
  missingDataWarnings: string[];
};

export function compareSavedCases(savedCases: SavedCase[]): CaseComparisonResult {
  const selected = savedCases.slice(0, 3);
  if (selected.length < 2) return { cases: selected.map(toComparedCase), ranking: [], summary: "請至少選擇兩個案件", missingDataWarnings: ["至少需要 2 筆已保存案件才能比較"] };
  const cases = selected.map(toComparedCase);
  const missingDataWarnings = cases.flatMap(missingWarnings);
  const ranking = cases.map((item) => rankCase(item)).sort((a, b) => (b.score ?? -1) - (a.score ?? -1)).map((item, index) => ({ ...item, rank: index + 1 }));
  return {
    cases,
    ranking,
    bestCaseId: ranking[0]?.caseId,
    summary: missingDataWarnings.length ? "已依現有資料排序；部分案件資料不足，排序信心較低。" : "已依風險、負擔、區位、估價與稅務快篩完成候選排序。",
    missingDataWarnings: [...new Set(missingDataWarnings)],
  };
}

export function buildCaseComparisonHtml(result: CaseComparisonResult): string {
  const rankingRows = result.ranking.map((row) => `<tr><td>第 ${row.rank} 名</td><td>${escapeHtml(result.cases.find((item) => item.caseId === row.caseId)?.title ?? "")}</td><td>${row.score ?? "資料不足"}</td><td>${escapeHtml(row.reasons.join("；") || "尚無明確加分")}</td><td>${escapeHtml(row.warnings.join("；") || "尚無主要風險")}</td></tr>`).join("");
  const comparisonRows = comparisonFields.map(([label, field, format]) => `<tr><th>${label}</th>${result.cases.map((item) => `<td>${escapeHtml(format(item[field] as never))}</td>`).join("")}</tr>`).join("");
  return `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>案件比較摘要</title><style>body{font-family:Arial,sans-serif;color:#172033;max-width:1100px;margin:32px auto;padding:0 20px}table{width:100%;border-collapse:collapse;margin:16px 0}th,td{border:1px solid #dbe2ea;padding:9px;text-align:left;vertical-align:top}th{background:#f3f7f8}.scroll{overflow-x:auto}.note{background:#fff7dc;padding:12px;border-radius:8px}</style></head><body><h1>案件比較 / 候選排序</h1><p>比較日期：${new Date().toLocaleString("zh-TW")}</p><p>${escapeHtml(result.summary)}</p><h2>推薦排序</h2><div class="scroll"><table><thead><tr><th>排名</th><th>案件</th><th>分數</th><th>推薦理由</th><th>主要風險</th></tr></thead><tbody>${rankingRows}</tbody></table></div><h2>案件比較</h2><div class="scroll"><table><thead><tr><th>欄位</th>${result.cases.map((item) => `<th>${escapeHtml(item.title)}</th>`).join("")}</tr></thead><tbody>${comparisonRows}</tbody></table></div><h2>資料不足提醒</h2><ul>${result.missingDataWarnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>目前比較資料相對完整。</li>"}</ul><p class="note">本比較非正式鑑價、非銀行核貸、非稅務申報建議，僅供看屋決策輔助；第 1 名不代表一定適合購買，仍需確認屋況、交易條件與議價空間。</p></body></html>`;
}

function toComparedCase(saved: SavedCase): ComparedCase {
  const { valuation, loan, holdingCost, locationInsight, terrainRisk, riskSummary, taxOracle, inputs } = saved.data;
  return {
    caseId: saved.id, title: saved.title, location: `${inputs.city}${inputs.district}${inputs.road}`, propertyPrice: saved.inputSummary.propertyPrice ?? loan?.property_price_wan ?? null,
    areaPing: saved.inputSummary.areaPing ?? inputs.area_ping ?? null, buildingType: inputs.building_type || "尚未完成", completionRate: saved.progress,
    valuationMid: valuation?.price_range.mid ?? null, valuationRange: valuation ? `${valuation.price_range.low.toLocaleString()}–${valuation.price_range.high.toLocaleString()} 萬` : "尚未完成",
    valuationConfidence: valuation?.confidence_score ?? null, priceReasonableness: riskSummary?.priceReasonableness.label ?? "未知",
    downPaymentWan: loan?.down_payment_wan ?? null, monthlyPayment: loan?.monthly_payment ?? null, loanBurdenRatio: loan?.income_burden_ratio ?? null,
    monthlyHoldingCost: holdingCost?.monthly_total_holding_cost ?? null, holdingBurdenRatio: holdingCost?.income_burden_ratio ?? null,
    locationScore: locationInsight?.location_score ?? null, transitScore: locationInsight?.category_scores.transit_score ?? null, convenienceScore: locationInsight?.category_scores.convenience_score ?? null,
    educationScore: locationInsight?.category_scores.education_score ?? null, medicalScore: locationInsight?.category_scores.medical_score ?? null,
    locationRiskGap: !locationInsight ? "尚未完成" : locationInsight.data_quality.missing_sources.join("、") || (locationInsight.poi_summary.risk_facility_count ? `風險設施 ${locationInsight.poi_summary.risk_facility_count} 處` : "無明顯缺口"),
    terrainRiskLevel: terrainRisk?.overall.label ?? "尚未完成",
    terrainRiskStatus: terrainRisk ? `${terrainRisk.overall.level} / ${terrainRisk.data_quality.status}` : "尚未完成",
    riskSignal: riskSummary?.overallSignal ?? "unknown", riskScore: riskSummary?.overallScore ?? null, mainRisks: riskSummary?.riskFactors.slice(0, 3).map((item) => item.title) ?? [],
    positives: riskSummary?.positiveFactors.slice(0, 3).map((item) => item.title) ?? [], taxStatus: taxOracle ? "已完成" : "尚未快篩", taxSignal: taxOracle?.signal_color ?? "unknown", taxRiskScore: taxOracle?.risk_score ?? null,
  };
}

function rankCase(item: ComparedCase) {
  const risk = item.riskScore ?? 40;
  const burden = burdenScore(item.loanBurdenRatio, item.holdingBurdenRatio);
  const location = item.locationScore ?? 40;
  const valuation = valuationScore(item.valuationConfidence, item.priceReasonableness);
  const tax = item.taxSignal === "green" ? 90 : item.taxSignal === "yellow" ? 60 : item.taxSignal === "red" ? 20 : 40;
  const raw = risk * 0.30 + burden * 0.25 + location * 0.20 + valuation * 0.15 + tax * 0.10;
  const score = Math.round(raw * (0.65 + item.completionRate / 100 * 0.35));
  const reasons = [...item.positives, item.locationScore !== null && item.locationScore >= 75 ? "區位條件佳" : "", burden >= 75 ? "負擔相對健康" : "", item.priceReasonableness.includes("合理") || item.priceReasonableness.includes("低於") ? "價格條件具支持性" : ""].filter(Boolean).slice(0, 3);
  const warnings = [...item.mainRisks, item.completionRate < 70 ? "資料不足，排序信心較低" : "", item.taxStatus === "尚未快篩" ? "TaxOracle 尚未快篩" : ""].filter(Boolean).slice(0, 3);
  return { caseId: item.caseId, rank: 0, score, label: score >= 75 ? "優先安排看屋" : score >= 55 ? "可比較評估" : "建議先補查", reasons, warnings };
}

function burdenScore(loan: number | null, holding: number | null) {
  const ratios = [loan, holding].filter((value): value is number => value !== null);
  if (!ratios.length) return 40;
  const worst = Math.max(...ratios);
  return worst <= 0.30 ? 95 : worst <= 0.40 ? 75 : worst <= 0.50 ? 50 : 20;
}

function valuationScore(confidence: number | null, price: string) {
  const priceScore = price.includes("低於") ? 90 : price.includes("合理") || price.includes("接近") ? 80 : price.includes("高於") ? 30 : 40;
  return (confidence ?? 40) * 0.6 + priceScore * 0.4;
}

function missingWarnings(item: ComparedCase) {
  return [["估價", item.valuationMid], ["貸款", item.monthlyPayment], ["持有成本", item.monthlyHoldingCost], ["區位", item.locationScore], ["風險總評", item.riskScore], ["稅務快篩", item.taxRiskScore]].filter(([, value]) => value === null).map(([label]) => `${item.title}：${label}尚未完成`).concat(item.terrainRiskStatus === "尚未完成" ? [`${item.title}：地勢與災害風險尚未完成`] : []);
}

const comparisonFields: Array<[string, keyof ComparedCase, (value: never) => string]> = [
  ["地點", "location", text], ["總價", "propertyPrice", wan], ["坪數", "areaPing", numberText], ["建物型態", "buildingType", text], ["完成度", "completionRate", percent],
  ["估價中位數", "valuationMid", wan], ["估價區間", "valuationRange", text], ["估價信心", "valuationConfidence", scoreText], ["開價合理性", "priceReasonableness", text],
  ["頭期款", "downPaymentWan", wan], ["月付", "monthlyPayment", yuan], ["月付負擔率", "loanBurdenRatio", ratio], ["每月持有成本", "monthlyHoldingCost", yuan], ["持有成本負擔率", "holdingBurdenRatio", ratio],
  ["區位總分", "locationScore", scoreText], ["交通", "transitScore", scoreText], ["生活便利", "convenienceScore", scoreText], ["教育", "educationScore", scoreText], ["醫療", "medicalScore", scoreText], ["風險資料缺口", "locationRiskGap", text],
  ["地勢風險", "terrainRiskLevel", text], ["地勢資料狀態", "terrainRiskStatus", text],
  ["風險燈號", "riskSignal", text], ["風險總分", "riskScore", scoreText], ["TaxOracle", "taxStatus", text], ["稅務燈號", "taxSignal", text],
];
function text(value: unknown) { return value === null || value === "" ? "尚未完成" : String(value); }
function numberText(value: unknown) { return typeof value === "number" ? String(value) : "尚未完成"; }
function wan(value: unknown) { return typeof value === "number" ? `${value.toLocaleString()} 萬` : "尚未完成"; }
function yuan(value: unknown) { return typeof value === "number" ? `${value.toLocaleString()} 元` : "尚未完成"; }
function percent(value: unknown) { return typeof value === "number" ? `${value}%` : "尚未完成"; }
function ratio(value: unknown) { return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "尚未完成"; }
function scoreText(value: unknown) { return typeof value === "number" ? `${value} 分` : "尚未完成"; }
function escapeHtml(value: string) { return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char); }
