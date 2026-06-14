import type { WorkflowStatus } from "@/lib/workflow-status";

export type BuyingWizardStep = "property_search" | "valuation" | "affordability" | "location" | "risk" | "report" | "tax";
export type ActiveWorkflowMode = "home" | "buying_wizard" | "taxoracle" | "advanced";

export type BuyingWizardStepDefinition = {
  id: BuyingWizardStep;
  label: string;
  targetId: string;
  guide: string;
};

export const BUYING_WIZARD_STEPS: BuyingWizardStepDefinition[] = [
  { id: "property_search", label: "找房雷達", targetId: "property-finder", guide: "先用預算和地點找可負擔路段。" },
  { id: "valuation", label: "估價與趨勢", targetId: "valuation-calculator", guide: "確認這個路段的合理價格。" },
  { id: "affordability", label: "貸款與持有成本", targetId: "loan-calculator", guide: "月付之外也要看稅費與管理費。" },
  { id: "location", label: "區位分析", targetId: "location-insight-calculator", guide: "區位分數高也要實地確認。" },
  { id: "risk", label: "風險總評", targetId: "risk-summary", guide: "看紅黃綠燈號，不要只看單一分數。" },
  { id: "report", label: "看屋報告", targetId: "decision-report", guide: "把報告匯出給家人或客戶討論。" },
  { id: "tax", label: "稅務快篩", targetId: "taxoracle", guide: "最後補做稅務快篩。" },
];

export function getActiveWizardStep(status: WorkflowStatus): BuyingWizardStepDefinition {
  return BUYING_WIZARD_STEPS.find((step) => step.targetId === status.nextActionTargetId)
    ?? BUYING_WIZARD_STEPS.find((step) => step.label === status.nextStep)
    ?? BUYING_WIZARD_STEPS[0];
}

export function isWizardStepCompleted(status: WorkflowStatus, step: BuyingWizardStepDefinition) {
  return status.completedSteps.includes(step.label);
}
