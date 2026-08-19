"use client";

import type { LoanVisualModel } from "@/lib/loan-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function LoanFinancingStructureChart({ model }: { model: LoanVisualModel }) {
  const { copy } = useExperienceLocale();
  if (!model.structure) return <VisualDataUnavailableState message={copy("viz.loanStructureUnavailable")} />;
  const { propertyPrice, downPayment, loanAmount, downPaymentRatio, loanRatio } = model.structure;
  return <section aria-label={copy("viz.loanStructureHeading")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <h3 className="text-sm font-bold text-slate-900">{copy("viz.loanStructureHeading")}</h3>
    <svg viewBox="0 0 640 190" role="img" aria-label={copy("viz.loanStructureSvgLabel")} className="mt-3 h-auto w-full"><title>{copy("viz.loanStructureHeading")}</title><desc>{copy("viz.loanStructureNote")}</desc><rect x="40" y="62" width={520} height="34" rx="17" className="fill-cyan-100" /><rect x="40" y="62" width={520 * downPaymentRatio} height="34" rx="17" className="fill-cyan-700" /><rect x={40 + 520 * downPaymentRatio} y="62" width={520 * loanRatio} height="34" className="fill-slate-700" /><text x="40" y="130" className="fill-slate-700 text-[13px]">{copy("viz.loanStructureDown")} {downPayment.toLocaleString()} ({(downPaymentRatio * 100).toFixed(1)}%)</text><text x="40" y="158" className="fill-slate-700 text-[13px]">{copy("viz.loanStructureLoan")} {loanAmount.toLocaleString()} ({(loanRatio * 100).toFixed(1)}%)</text><text x="560" y="130" textAnchor="end" className="fill-slate-500 text-[12px]">{copy("viz.loanStructureTotal")} {propertyPrice.toLocaleString()}</text></svg>
    <p className="mt-2 text-xs text-slate-600">{copy("viz.loanPanelDisclaimer")}</p>
  </section>;
}
