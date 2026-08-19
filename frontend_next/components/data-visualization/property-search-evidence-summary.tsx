"use client";

import type { PropertySearchVisualModel } from "@/lib/property-search-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PropertySearchEvidenceSummary({ model }: { model: PropertySearchVisualModel }) {
  const { copy } = useExperienceLocale();
  return <section aria-label={copy("viz.searchEvidenceTitle")} className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-4"><h3 className="text-sm font-bold text-slate-900">{copy("viz.searchEvidenceTitle")}</h3><dl className="mt-3 grid gap-2 text-xs text-slate-700 sm:grid-cols-2">{model.evidence.slice(0, 4).map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl><details className="mt-3 rounded-lg border border-cyan-100 bg-white"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-slate-800">{copy("viz.searchEvidenceMethodTitle")}</summary><dl className="grid gap-2 border-t border-stone-100 p-3 text-xs text-slate-700">{model.evidence.slice(4).map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl></details></section>;
}
