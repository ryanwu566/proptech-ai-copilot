"use client";

import type { TaxVisualModel } from "@/lib/tax-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function TaxRuleOutcomeChart({ model }: { model: TaxVisualModel }) {
  const { copy } = useExperienceLocale();
  if (!model.outcomes.length) return <VisualDataUnavailableState message={copy("viz.taxRuleUnavailable")} />;
  const max = Math.max(...model.outcomes.map((item) => item.count), 1);
  return <section aria-label={copy("viz.taxRuleTitle")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4"><h3 className="text-sm font-bold text-slate-900">{copy("viz.taxRuleTitle")}</h3><div role="img" aria-label={copy("viz.taxRuleTitle")} className="mt-3 grid gap-3">{model.outcomes.map((item) => <div key={item.key}><div className="flex items-center justify-between gap-3 text-xs"><span className="font-bold text-slate-700">{item.label}</span><strong>{copy("viz.taxRuleCount", { count: item.count })}</strong></div><div className="mt-1 h-4 rounded-full bg-stone-100"><div className="h-4 rounded-full bg-cyan-700" style={{ width: `${(item.count / max) * 100}%` }} /></div></div>)}</div><p className="mt-3 text-xs text-slate-600">{copy("viz.taxRuleNote")}</p></section>;
}
