"use client";

import { selectChartLabelIndexes } from "@/lib/market-insight-visualization";
import type { LoanVisualModel } from "@/lib/loan-visualization";
import { ChartEmptyState } from "./chart-empty-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function LoanSensitivityChart({ model }: { model: LoanVisualModel }) {
  const { copy } = useExperienceLocale();
  if (model.sensitivity.length < 2) return <ChartEmptyState />;
  const min = Math.min(...model.sensitivity.map((point) => point.monthlyPayment));
  const max = Math.max(...model.sensitivity.map((point) => point.monthlyPayment));
  const range = max - min || 1;
  const x = (index: number) => 46 + (index * 548) / (model.sensitivity.length - 1);
  const y = (value: number) => 205 - ((value - min) / range) * 145;
  const labels = selectChartLabelIndexes(model.sensitivity.length);
  const points = model.sensitivity.map((point, index) => `${x(index)},${y(point.monthlyPayment)}`).join(" ");
  return <section aria-label={copy("viz.loanSensitivitySvgLabel")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <h3 className="text-sm font-bold text-slate-900">{copy("viz.loanSensitivityTitle")}</h3>
    <svg viewBox="0 0 640 260" role="img" aria-label={copy("viz.loanSensitivitySvgLabel")} className="mt-3 h-auto w-full"><title>{copy("viz.loanSensitivityTitle")}</title><desc>{copy("viz.loanSensitivityDesc")}</desc><polyline points={points} fill="none" className="stroke-cyan-700" strokeWidth="4" />{model.sensitivity.map((point, index) => <circle key={`${point.annualInterestRate}-${index}`} cx={x(index)} cy={y(point.monthlyPayment)} r={point.differenceFromBase === 0 ? "7" : "4"} className={point.differenceFromBase === 0 ? "fill-amber-600" : "fill-cyan-700"} />)}{labels.map((index) => <text key={`${model.sensitivity[index].annualInterestRate}-${index}`} x={x(index)} y="240" textAnchor="middle" className="fill-slate-600 text-[11px]">{model.sensitivity[index].annualInterestRate}%</text>)}</svg>
    <ul className="mt-2 grid gap-1 text-xs text-slate-600 sm:grid-cols-2">{model.sensitivity.map((point, index) => <li key={`${point.annualInterestRate}-${index}`}>{point.differenceFromBase === 0 ? `${copy("viz.loanSensitivityBase")}: ` : ""}{point.annualInterestRate}% · {copy("viz.loanSensitivityPayment")} {point.monthlyPayment.toLocaleString()} · {copy("viz.loanSensitivityInterest")} {point.totalInterest.toLocaleString()}</li>)}</ul>
  </section>;
}
