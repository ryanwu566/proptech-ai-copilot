"use client";

import type { LoanVisualModel } from "@/lib/loan-visualization";
import { Button, Notice } from "@/components/ui";
import { MetricTile, SectionCard } from "@/components/product-ui";
import { AffordabilityStatus } from "./affordability-status";
import { CalculationEvidenceDetails } from "./calculation-evidence-details";
import { LoanFinancingStructureChart } from "./loan-financing-structure-chart";
import { LoanGracePeriodChart } from "./loan-grace-period-chart";
import { LoanSensitivityChart } from "./loan-sensitivity-chart";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function LoanVisualPanel({ model, onHoldingCost }: { model: LoanVisualModel; onHoldingCost?: () => void }) {
  const { copy } = useExperienceLocale();
  if (model.state !== "available") return <VisualDataUnavailableState message={model.summary} />;
  return <div className="min-w-0 space-y-4"><SectionCard title={copy("viz.loanPanelTitle")}><p className="text-sm leading-6 text-slate-700">{model.summary}</p><p className="mt-2 text-xs text-amber-800">{copy("viz.loanPanelDisclaimer")}</p><div className="mt-3"><AffordabilityStatus value={model.affordability} /></div></SectionCard><div className="grid gap-3 sm:grid-cols-2"><MetricTile label={copy("viz.loanPanelDown")} value={`${model.metrics.downPayment?.toLocaleString()}`} /><MetricTile label={copy("viz.loanPanelAmount")} value={`${model.metrics.loanAmount?.toLocaleString()}`} /><MetricTile label={copy("viz.loanPanelMonthly")} value={`${model.metrics.monthlyPayment?.toLocaleString()}`} /><MetricTile label={copy("viz.loanPanelInterest")} value={`${model.metrics.totalInterest?.toLocaleString()}`} /></div><LoanFinancingStructureChart model={model} /><LoanSensitivityChart model={model} />{model.gracePeriodRequested ? <LoanGracePeriodChart model={model} /> : null}<CalculationEvidenceDetails model={model}/><Notice tone="warning">{copy("viz.loanPanelMissingNotice")}</Notice>{onHoldingCost && <Button secondary className="w-full sm:w-auto" onClick={onHoldingCost}>{copy("viz.loanPanelHoldingCost")}</Button>}</div>;
}
