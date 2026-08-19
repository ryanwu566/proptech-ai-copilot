import type { WorkflowStatus, WorkflowStepId } from "@/lib/workflow-status";
import { WORKFLOW_STEPS } from "@/lib/workflow-status";

export type BuyingWizardStep = WorkflowStepId;
export type ActiveWorkflowMode = "home" | "buying_wizard" | "taxoracle" | "advanced";

export type BuyingWizardStepDefinition = {
  id: BuyingWizardStep;
  targetId: string;
};

export const BUYING_WIZARD_STEPS: BuyingWizardStepDefinition[] = WORKFLOW_STEPS.map((step) => ({
  id: step.id,
  targetId: step.targetId,
}));

export function getActiveWizardStep(status: WorkflowStatus): BuyingWizardStepDefinition {
  return BUYING_WIZARD_STEPS.find((step) => step.targetId === status.nextActionTargetId)
    ?? BUYING_WIZARD_STEPS.find((step) => step.id === status.nextStep)
    ?? BUYING_WIZARD_STEPS[0];
}

export function isWizardStepCompleted(status: WorkflowStatus, step: BuyingWizardStepDefinition) {
  return status.completedSteps.includes(step.id);
}
