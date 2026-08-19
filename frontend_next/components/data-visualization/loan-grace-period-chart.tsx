"use client";

import type { LoanVisualModel } from "@/lib/loan-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function LoanGracePeriodChart({ model }: { model: LoanVisualModel }) {
  const { copy } = useExperienceLocale();
  if (!model.gracePeriod) return <VisualDataUnavailableState message={copy("viz.loanGraceUnavailable")} />;
  const values = [model.gracePeriod.graceMonthlyPayment, model.gracePeriod.postGraceMonthlyPayment, model.gracePeriod.baselineMonthlyPayment];
  const labels = [copy("viz.loanGraceInPeriod"), copy("viz.loanGraceAfterPeriod"), copy("viz.loanGraceBaseline")];
  const max = Math.max(...values);
  return <section aria-label={copy("viz.loanGraceHeading")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <h3 className="text-sm font-bold text-slate-900">{copy("viz.loanGraceTitle")}</h3>
    <svg viewBox="0 0 640 240" role="img" aria-label={copy("viz.loanGraceSvgLabel")} className="mt-3 h-auto w-full"><title>{copy("viz.loanGraceTitle")}</title><desc>{copy("viz.loanGraceNote")}</desc>{values.map((value, index) => { const height = (value / max) * 150; const x = 80 + index * 190; return <g key={value}><rect x={x} y={190 - height} width="80" height={height} className={index === 0 ? "fill-cyan-600" : index === 1 ? "fill-slate-700" : "fill-amber-600"} /><text x={x + 40} y="215" textAnchor="middle" className="fill-slate-700 text-[11px]">{labels[index]}</text><text x={x + 40} y={180 - height} textAnchor="middle" className="fill-slate-800 text-[11px]">{value.toLocaleString()}</text></g>; })}</svg>
    <p className="mt-2 text-xs text-amber-800">{copy("viz.loanGraceNote")}</p>
  </section>;
}
