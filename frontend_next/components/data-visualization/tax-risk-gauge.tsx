"use client";

import type { TaxVisualModel } from "@/lib/tax-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function TaxRiskGauge({ model }: { model: TaxVisualModel }) {
  const { copy } = useExperienceLocale();
  if (model.riskScore === null) return <div role="status" aria-label={copy("viz.taxRiskNoScore")} className="grid min-h-32 place-items-center rounded-xl border border-stone-200 bg-stone-50 p-4 text-center text-sm text-slate-600">{copy("viz.taxRiskNoScore")}</div>;
  return <div role="img" aria-label={`${copy("viz.taxRiskScore")} ${model.riskScore}`} className="grid place-items-center rounded-xl border border-stone-200 bg-white p-4"><div className="grid h-32 w-32 place-items-center rounded-full" style={{ background: `conic-gradient(#0e7490 ${model.riskScore * 3.6}deg, #e7e5e4 0deg)` }}><div className="grid h-24 w-24 place-items-center rounded-full bg-white text-center"><strong className="text-3xl text-slate-950">{model.riskScore}</strong><span className="text-[10px] text-slate-500">{copy("tax.riskScore")}</span></div></div><p className="mt-2 text-xs font-bold text-slate-700">{model.eligibility.label} · {model.signal.label}</p><p className="mt-1 text-center text-[10px] text-slate-500">{copy("viz.taxRiskNote")}</p></div>;
}
