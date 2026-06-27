import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, TaxResult, TerrainRiskResult, ValuationResult } from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";

export type ViewingDecisionStatus = "ready_to_view" | "needs_more_data" | "clarify_risk_first";

export type ViewingDecision = {
  status: ViewingDecisionStatus;
  label: "可安排看屋" | "建議補資料後再判斷" | "先釐清風險再看屋";
  reasons: string[];
  missingCriticalData: string[];
  nextAction: {
    label: string;
    targetId: string;
  };
  completedData: string[];
  riskSources: string[];
  ruleNotes: string[];
};

export type ViewingDecisionInputs = {
  valuation?: ValuationResult;
  loan?: LoanCalculationResult;
  holding?: HoldingCostResult;
  location?: LocationInsightResult;
  terrainRisk?: TerrainRiskResult;
  riskSummary?: RiskSummary;
  taxOracleResult?: TaxResult;
};

const criticalChecks: Array<{ key: keyof ViewingDecisionInputs; label: string; targetId: string; action: string }> = [
  { key: "valuation", label: "合理價格區間", targetId: "valuation-calculator", action: "先完成合理價格估算" },
  { key: "loan", label: "貸款月付", targetId: "loan-calculator", action: "先試算每月房貸" },
  { key: "holding", label: "每月持有成本", targetId: "holding-cost-calculator", action: "先估算每月總支出" },
  { key: "location", label: "生活機能與區位", targetId: "location-insight-calculator", action: "先分析生活機能與區位" },
  { key: "terrainRisk", label: "地勢與災害風險", targetId: "terrain-risk-analysis", action: "先補查地勢與災害風險" },
];

export function buildViewingDecision(input: ViewingDecisionInputs): ViewingDecision {
  const completedData = criticalChecks.filter((item) => hasUsableCriticalData(item.key, input)).map((item) => item.label);
  const missingCriticalData = criticalChecks.filter((item) => !hasUsableCriticalData(item.key, input)).map((item) => item.label);
  const highRiskSources = collectHighRiskSources(input);
  const hasKnownHighRisk =
    input.riskSummary?.overallSignal === "red"
    || input.riskSummary?.riskFactors?.some((item) => item.level === "high")
    || input.loan?.affordability_level === "risky"
    || input.holding?.affordability_level === "risky"
    || Boolean(input.location?.poi_summary.risk_facility_count && input.location.poi_summary.risk_facility_count > 0)
    || input.terrainRisk?.overall.level === "high"
    || input.taxOracleResult?.signal_color === "red"
    || input.taxOracleResult?.eligibility_status === "not_eligible";
  const firstMissing = criticalChecks.find((item) => !hasUsableCriticalData(item.key, input));
  const firstHighRiskTarget = firstHighRiskAction(input);

  if (hasKnownHighRisk) {
    return {
      status: "clarify_risk_first",
      label: "先釐清風險再看屋",
      reasons: (highRiskSources.length ? highRiskSources : ["已有高風險訊號，建議先釐清再決定是否約看。"]).slice(0, 3),
      missingCriticalData,
      nextAction: firstHighRiskTarget,
      completedData,
      riskSources: highRiskSources.length ? highRiskSources : ["已有高風險訊號，需先釐清。"],
      ruleNotes: baseRuleNotes(),
    };
  }

  if (missingCriticalData.length > 0 && firstMissing) {
    return {
      status: "needs_more_data",
      label: "建議補資料後再判斷",
      reasons: [
        `尚缺 ${missingCriticalData.slice(0, 3).join("、")}。`,
        "缺資料不會被視為低風險，建議先補齊再決定是否約看。",
      ],
      missingCriticalData,
      nextAction: { label: firstMissing.action, targetId: firstMissing.targetId },
      completedData,
      riskSources: [],
      ruleNotes: baseRuleNotes(),
    };
  }

  return {
    status: "ready_to_view",
    label: "可安排看屋",
    reasons: [
      "核心分析已完成，且目前沒有已知高風險訊號。",
      "可進一步約看，但仍需現場確認屋況、噪音、管理與周邊環境。",
    ],
    missingCriticalData: [],
    nextAction: { label: "查看看屋決策報告", targetId: "decision-report" },
    completedData,
    riskSources: [],
    ruleNotes: baseRuleNotes(),
  };
}

function hasUsableCriticalData(key: keyof ViewingDecisionInputs, input: ViewingDecisionInputs) {
  if (key !== "terrainRisk") return Boolean(input[key]);
  const terrain = input.terrainRisk;
  if (!terrain) return false;
  return terrain.overall.level !== "unknown" && terrain.data_quality.status !== "unavailable";
}

function collectHighRiskSources(input: ViewingDecisionInputs) {
  const sources: string[] = [];
  if (input.riskSummary?.overallSignal === "red") sources.push("風險總評出現紅燈，建議先釐清主要風險。");
  for (const item of input.riskSummary?.riskFactors ?? []) {
    if (item.level === "high") sources.push(`高風險項目：${item.title}。`);
  }
  if (input.loan?.affordability_level === "risky") sources.push("貸款月付負擔偏高，需先確認收入與核貸條件。");
  if (input.holding?.affordability_level === "risky") sources.push("每月持有成本負擔偏高，需先確認總支出是否可承受。");
  if (input.location?.poi_summary.risk_facility_count && input.location.poi_summary.risk_facility_count > 0) sources.push("區位分析顯示附近有風險設施，建議先實地確認。");
  if (input.terrainRisk?.overall.level === "high") sources.push("地勢與災害風險結果為高，建議先確認官方圖資與現場條件。");
  if (input.taxOracleResult?.signal_color === "red" || input.taxOracleResult?.eligibility_status === "not_eligible") sources.push("TaxOracle 稅務快篩顯示高風險，建議先釐清稅務條件。");
  return [...new Set(sources)];
}

function firstHighRiskAction(input: ViewingDecisionInputs) {
  if (input.terrainRisk?.overall.level === "high") return { label: "查看地勢與災害風險", targetId: "terrain-risk-analysis" };
  if (input.location?.poi_summary.risk_facility_count && input.location.poi_summary.risk_facility_count > 0) return { label: "查看區位分析", targetId: "location-insight-calculator" };
  if (input.loan?.affordability_level === "risky") return { label: "重新檢查貸款月付", targetId: "loan-calculator" };
  if (input.holding?.affordability_level === "risky") return { label: "重新檢查持有成本", targetId: "holding-cost-calculator" };
  return { label: "查看風險總評", targetId: "risk-summary" };
}

function baseRuleNotes() {
  return [
    "先看既有風險摘要與已知高風險。",
    "再檢查估價、貸款、持有成本、區位與地勢風險是否完成。",
    "資料不足、unknown 或 unavailable 不會被推論為低風險。",
  ];
}
