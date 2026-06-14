import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, ValuationResult } from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";

export const WORKFLOW_REPORT_SESSION_KEY = "proptech:workflow-report-completed";
export const TAXORACLE_RESULT_SESSION_KEY = "proptech:taxoracle-result";
export const WORKFLOW_STATUS_EVENT = "proptech:workflow-status-updated";
export const OPEN_TAXORACLE_EVENT = "proptech:open-taxoracle";

export type WorkflowStatus = {
  currentStep: string;
  completedSteps: string[];
  nextStep: string;
  nextActionLabel: string;
  nextActionTargetId: string;
  missingItems: string[];
  overallProgress: number;
};

export type WorkflowStatusInputs = {
  propertySearch?: PropertySearchResult;
  valuation?: ValuationResult;
  loan?: LoanCalculationResult;
  holding?: HoldingCostResult;
  location?: LocationInsightResult;
  riskSummary?: RiskSummary;
  reportCompleted?: boolean;
  taxOracleResult?: TaxResult;
};

const steps = [
  ["找房雷達", "開始找房雷達", "property-finder"],
  ["估價與趨勢", "帶入估價", "valuation-calculator"],
  ["貸款與持有成本", "試算貸款月付", "loan-calculator"],
  ["區位分析", "分析區位", "location-insight-calculator"],
  ["風險總評", "查看風險總評", "risk-summary"],
  ["看屋決策報告", "匯出看屋報告", "decision-report"],
  ["TaxOracle 稅務快篩", "進行 TaxOracle 稅務快篩", "taxoracle"],
] as const;

export function buildWorkflowStatus(input: WorkflowStatusInputs): WorkflowStatus {
  const completed = [
    Boolean(input.propertySearch),
    Boolean(input.valuation),
    Boolean(input.loan && input.holding),
    Boolean(input.location),
    Boolean(input.riskSummary && input.riskSummary.overallSignal !== "unknown"),
    Boolean(input.reportCompleted),
    Boolean(input.taxOracleResult),
  ];
  const firstIncomplete = completed.findIndex((value) => !value);
  const nextIndex = firstIncomplete === -1 ? steps.length - 1 : firstIncomplete;
  const loanWithoutHolding = nextIndex === 2 && Boolean(input.loan) && !input.holding;
  const completedSteps = steps.filter((_, index) => completed[index]).map(([name]) => name);
  const missingItems = steps.filter((_, index) => !completed[index]).map(([name]) => name);
  return {
    currentStep: firstIncomplete <= 0 ? "尚未開始" : steps[Math.min(firstIncomplete - 1, steps.length - 1)][0],
    completedSteps,
    nextStep: firstIncomplete === -1 ? "流程完成" : steps[nextIndex][0],
    nextActionLabel: firstIncomplete === -1 ? "查看 TaxOracle 結果" : loanWithoutHolding ? "估算持有成本" : steps[nextIndex][1],
    nextActionTargetId: firstIncomplete === -1 ? "taxoracle" : loanWithoutHolding ? "holding-cost-calculator" : steps[nextIndex][2],
    missingItems,
    overallProgress: Math.round(completedSteps.length / steps.length * 100),
  };
}

export function markWorkflowReportCompleted() {
  window.sessionStorage.setItem(WORKFLOW_REPORT_SESSION_KEY, "true");
  window.dispatchEvent(new Event(WORKFLOW_STATUS_EVENT));
}

export function markTaxOracleCompleted(result: TaxResult) {
  window.sessionStorage.setItem(TAXORACLE_RESULT_SESSION_KEY, JSON.stringify(result));
  window.dispatchEvent(new Event(WORKFLOW_STATUS_EVENT));
}

export function readWorkflowSession(): { reportCompleted: boolean; taxOracleResult?: TaxResult } {
  if (typeof window === "undefined") return { reportCompleted: false };
  try {
    const tax = window.sessionStorage.getItem(TAXORACLE_RESULT_SESSION_KEY);
    return { reportCompleted: window.sessionStorage.getItem(WORKFLOW_REPORT_SESSION_KEY) === "true", taxOracleResult: tax ? JSON.parse(tax) as TaxResult : undefined };
  } catch {
    return { reportCompleted: false };
  }
}
