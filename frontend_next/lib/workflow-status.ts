import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, ValuationResult } from "@/lib/api";
import type { RiskSummary } from "@/lib/risk-summary";

export const WORKFLOW_REPORT_SESSION_KEY = "proptech:workflow-report-completed";
export const TAXORACLE_RESULT_SESSION_KEY = "proptech:taxoracle-result";
export const WORKFLOW_STATUS_EVENT = "proptech:workflow-status-updated";
export const OPEN_TAXORACLE_EVENT = "proptech:open-taxoracle";

export type WorkflowStepId = "property_search" | "valuation" | "affordability" | "location" | "risk" | "report" | "tax";

export type WorkflowStatus = {
  currentStep: WorkflowStepId | "not_started" | "completed";
  completedSteps: WorkflowStepId[];
  nextStep: WorkflowStepId | "completed";
  nextActionLabel: string;
  nextActionTargetId: string;
  missingItems: WorkflowStepId[];
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

export type WorkflowStepDefinition = {
  id: WorkflowStepId;
  actionKey: string;
  targetId: string;
};

export const WORKFLOW_STEPS: WorkflowStepDefinition[] = [
  { id: "property_search", actionKey: "wizardStep.propertySearch", targetId: "property-finder" },
  { id: "valuation", actionKey: "wizardStep.valuation", targetId: "valuation-calculator" },
  { id: "affordability", actionKey: "wizardStep.affordability", targetId: "loan-calculator" },
  { id: "location", actionKey: "wizardStep.location", targetId: "location-insight-calculator" },
  { id: "risk", actionKey: "wizardStep.risk", targetId: "risk-summary" },
  { id: "report", actionKey: "wizardStep.report", targetId: "decision-report" },
  { id: "tax", actionKey: "wizardStep.tax", targetId: "taxoracle" },
];

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
  const nextIndex = firstIncomplete === -1 ? WORKFLOW_STEPS.length - 1 : firstIncomplete;
  const loanWithoutHolding = nextIndex === 2 && Boolean(input.loan) && !input.holding;
  const completedSteps = WORKFLOW_STEPS.filter((_, index) => completed[index]).map((step) => step.id);
  const missingItems = WORKFLOW_STEPS.filter((_, index) => !completed[index]).map((step) => step.id);
  return {
    currentStep: firstIncomplete <= 0 ? "not_started" : WORKFLOW_STEPS[Math.min(firstIncomplete - 1, WORKFLOW_STEPS.length - 1)].id,
    completedSteps,
    nextStep: firstIncomplete === -1 ? "completed" : WORKFLOW_STEPS[nextIndex].id,
    nextActionLabel: firstIncomplete === -1 ? "wizardStep.tax" : loanWithoutHolding ? "wizardStep.affordability" : WORKFLOW_STEPS[nextIndex].actionKey,
    nextActionTargetId: firstIncomplete === -1 ? "taxoracle" : loanWithoutHolding ? "holding-cost-calculator" : WORKFLOW_STEPS[nextIndex].targetId,
    missingItems,
    overallProgress: Math.round(completedSteps.length / WORKFLOW_STEPS.length * 100),
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
