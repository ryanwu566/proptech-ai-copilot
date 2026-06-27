import type { WorkflowStatus } from "@/lib/workflow-status";

export type BuyingWizardStep = "property_search" | "valuation" | "affordability" | "location" | "risk" | "report" | "tax";
export type ActiveWorkflowMode = "home" | "buying_wizard" | "taxoracle" | "advanced";

export type BuyingWizardStepDefinition = {
  id: BuyingWizardStep;
  label: string;
  title: string;
  targetId: string;
  guide: string;
};

export const BUYING_WIZARD_STEPS: BuyingWizardStepDefinition[] = [
  { id: "property_search", label: "找房雷達", title: "先找出你預算內可能買得到的路段", targetId: "property-finder", guide: "先不用想太多，填預算和地點就好。" },
  { id: "valuation", label: "估價與趨勢", title: "確認這個路段的合理價格", targetId: "valuation-calculator", guide: "這一步是看價格合不合理。" },
  { id: "affordability", label: "貸款與持有成本", title: "看看月付與持有成本撐不撐得住", targetId: "loan-calculator", guide: "買得起不只看總價，還要看月付和持有成本。" },
  { id: "location", label: "區位分析", title: "檢查生活機能與區位條件，並補查地勢風險", targetId: "location-insight-calculator", guide: "看看附近生活機能好不好，也補查坡度、淹水、坡地災害與地質風險。" },
  { id: "risk", label: "風險總評", title: "看紅黃綠燈號，判斷是否值得看屋", targetId: "risk-summary", guide: "綠燈不是保證能買，紅燈也不是絕對不能買，它是提醒你要不要繼續花時間看屋。" },
  { id: "report", label: "看屋決策報告", title: "產出可分享的看屋報告", targetId: "decision-report", guide: "把重點整理成報告，方便和家人或客戶討論。" },
  { id: "tax", label: "TaxOracle 稅務快篩", title: "補做稅務快篩", targetId: "taxoracle", guide: "最後再補查交易條件可能涉及的稅務風險。" },
];

export function getActiveWizardStep(status: WorkflowStatus): BuyingWizardStepDefinition {
  return BUYING_WIZARD_STEPS.find((step) => step.targetId === status.nextActionTargetId)
    ?? BUYING_WIZARD_STEPS.find((step) => step.label === status.nextStep)
    ?? BUYING_WIZARD_STEPS[0];
}

export function isWizardStepCompleted(status: WorkflowStatus, step: BuyingWizardStepDefinition) {
  return status.completedSteps.includes(step.label);
}
