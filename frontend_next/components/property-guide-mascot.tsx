"use client";

import type { WorkflowStatus } from "@/lib/workflow-status";
import { BUYING_WIZARD_STEPS, getActiveWizardStep, type BuyingWizardStep } from "@/lib/buying-wizard-status";
import { useViewMode } from "@/lib/view-mode";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { localizeWizardStepGuide, type BuyingWizardStepId } from "@/lib/dynamic-copy-localizers";

export function PropertyGuideMascot({ stage, riskSignal = "unknown", workflowStatus, activeWizardStep, caseMessage }: { stage: "start" | "finder" | "valuation" | "loan" | "location" | "complete"; riskSignal?: "green" | "yellow" | "red" | "unknown"; workflowStatus?: WorkflowStatus; activeWizardStep?: BuyingWizardStep; caseMessage?: string }) {
  const { copy, locale } = useExperienceLocale();
  const [viewMode] = useViewMode();
  const messages: Record<string, string> = {
    start: copy("intro.scene1"),
    finder: copy("workflow.step01Detail"),
    valuation: copy("workflow.step02Detail"),
    loan: copy("workflow.step03Detail"),
    location: copy("workflow.step02Detail"),
    complete: copy("workflow.step04Detail"),
  };
  const riskMessages: Record<string, string> = {
    green: copy("risk.noRisk"),
    yellow: copy("risk.missingChecks"),
    red: copy("risk.riskFactors"),
    unknown: messages[stage],
  };
  const wizardStep = activeWizardStep
    ? BUYING_WIZARD_STEPS.find((step) => step.id === activeWizardStep)
    : workflowStatus ? getActiveWizardStep(workflowStatus) : undefined;
  const localizedGuide = wizardStep ? localizeWizardStepGuide(wizardStep.id as BuyingWizardStepId, locale) : undefined;
  return <div className="flex min-w-0 items-center gap-3 rounded-xl border border-amber-300 bg-gradient-to-br from-yellow-50 to-amber-100 p-3 shadow-md ring-2 ring-yellow-200/70" aria-label={copy("mascot.name")} role="status">
    <div className="relative grid h-12 w-12 shrink-0 place-items-center rounded-[18px] bg-yellow-300 shadow-sm">
      <span className="absolute left-3 top-4 h-2 w-2 rounded-full bg-slate-800" /><span className="absolute right-3 top-4 h-2 w-2 rounded-full bg-slate-800" />
      <span className="mt-4 h-1.5 w-5 rounded-full bg-amber-700" />
      <span className="absolute -bottom-1 left-2 h-3 w-2 rounded-full bg-yellow-400" /><span className="absolute -bottom-1 right-2 h-3 w-2 rounded-full bg-yellow-400" />
    </div>
    <div className="min-w-0"><p className="text-xs font-extrabold tracking-wider text-amber-800">{copy("mascot.name")}</p><p className="mt-1 text-xs font-medium leading-5 text-slate-700">{caseMessage || (localizedGuide ?? riskMessages[riskSignal])}</p><p className="mt-1 text-[10px] leading-4 text-amber-800">{viewMode === "pro" ? copy("mascot.proMode") : copy("mascot.beginnerMode")}</p></div>
  </div>;
}
