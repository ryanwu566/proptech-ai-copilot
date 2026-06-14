"use client";

import { BuyingWizard, type WizardStepSummary } from "@/components/buying-wizard";
import type { WorkflowStatus } from "@/lib/workflow-status";

export function WorkflowCommandCenter({ status, summaries }: { status: WorkflowStatus; summaries?: WizardStepSummary }) {
  return <BuyingWizard status={status} summaries={summaries} />;
}
