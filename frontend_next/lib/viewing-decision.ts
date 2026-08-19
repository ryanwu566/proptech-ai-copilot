import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, TaxResult, TerrainRiskResult, ValuationResult } from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";

export type ViewingDecisionStatus = "ready_to_view" | "needs_more_data" | "clarify_risk_first";

export type ViewingDecision = {
  status: ViewingDecisionStatus;
  label: string;
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
];

export function buildViewingDecision(input: ViewingDecisionInputs): ViewingDecision {
  const completedData = criticalChecks.filter((item) => hasUsableCriticalData(item.key, input)).map((item) => item.key);
  const missingCriticalData = criticalChecks.filter((item) => !hasUsableCriticalData(item.key, input)).map((item) => item.key);
  const highRiskSources = collectHighRiskSources(input);
  const hasKnownHighRisk =
    input.riskSummary?.overallSignal === "red"
    || input.riskSummary?.riskFactors?.some((item) => item.level === "high")
    || input.loan?.affordability_level === "risky"
    || input.holding?.affordability_level === "risky"
    || Boolean(input.location?.poi_summary.risk_facility_count && input.location.poi_summary.risk_facility_count > 0)
    || input.taxOracleResult?.signal_color === "red"
    || input.taxOracleResult?.eligibility_status === "not_eligible";
  const firstMissing = criticalChecks.find((item) => !hasUsableCriticalData(item.key, input));
  const firstHighRiskTarget = firstHighRiskAction(input);

  if (hasKnownHighRisk) {
    return {
      status: "clarify_risk_first",
      label: "clarify_risk_first",
      reasons: (highRiskSources.length ? highRiskSources : ["high_risk_default"]).slice(0, 3),
      missingCriticalData,
      nextAction: firstHighRiskTarget,
      completedData,
      riskSources: highRiskSources.length ? highRiskSources : ["high_risk_default"],
      ruleNotes: ["rule_check_risk", "rule_check_data", "rule_unknown_not_low"],
    };
  }

  if (missingCriticalData.length > 0 && firstMissing) {
    return {
      status: "needs_more_data",
      label: "needs_more_data",
      reasons: [
        `missing:${missingCriticalData.slice(0, 3).join(",")}`,
        "missing_not_low_risk",
      ],
      missingCriticalData,
      nextAction: { label: firstMissing.key, targetId: firstMissing.targetId },
      completedData,
      riskSources: [],
      ruleNotes: ["rule_check_risk", "rule_check_data", "rule_unknown_not_low"],
    };
  }

  return {
    status: "ready_to_view",
    label: "ready_to_view",
    reasons: [
      "ready_no_high_risk",
      "ready_on_site",
    ],
    missingCriticalData: [],
    nextAction: { label: "view_report", targetId: "decision-report" },
    completedData,
    riskSources: [],
    ruleNotes: ["rule_check_risk", "rule_check_data", "rule_unknown_not_low"],
  };
}

function hasUsableCriticalData(key: keyof ViewingDecisionInputs, input: ViewingDecisionInputs) {
  return Boolean(input[key]);
}

function collectHighRiskSources(input: ViewingDecisionInputs) {
  const sources: string[] = [];
  if (input.riskSummary?.overallSignal === "red") sources.push("red_signal");
  for (const item of input.riskSummary?.riskFactors ?? []) {
    if (item.level === "high") sources.push(`high_item:${item.title}`);
  }
  if (input.loan?.affordability_level === "risky") sources.push("loan_risky");
  if (input.holding?.affordability_level === "risky") sources.push("holding_risky");
  if (input.location?.poi_summary.risk_facility_count && input.location.poi_summary.risk_facility_count > 0) sources.push("location_facility");
  if (input.taxOracleResult?.signal_color === "red" || input.taxOracleResult?.eligibility_status === "not_eligible") sources.push("tax_high");
  return [...new Set(sources)];
}

function firstHighRiskAction(input: ViewingDecisionInputs) {
  if (input.location?.poi_summary.risk_facility_count && input.location.poi_summary.risk_facility_count > 0) return { label: "check_location", targetId: "location-insight-calculator" };
  if (input.loan?.affordability_level === "risky") return { label: "check_loan", targetId: "loan-calculator" };
  if (input.holding?.affordability_level === "risky") return { label: "check_holding", targetId: "holding-cost-calculator" };
  return { label: "check_risk", targetId: "risk-summary" };
}

// Rule notes are now handled by the component localizer (localizeRuleNotes)
