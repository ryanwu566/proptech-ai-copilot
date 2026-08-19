"use client";

import type { PropertyCaseVisualModel } from "@/lib/property-case-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PropertyCaseMissingDataPanel({ model }: { model: PropertyCaseVisualModel }) {
  const { copy } = useExperienceLocale();
  return <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4" aria-label={copy("viz.missingTitle")}><div className="flex items-baseline justify-between gap-3"><div><p className="text-xs font-bold text-amber-800">{copy("viz.missingKicker")}</p><h3 className="mt-1 text-sm font-black text-amber-950">{copy("viz.missingTitle")}</h3></div><span className="text-xs font-bold text-amber-800">{copy("viz.missingCount", { count: model.missingItems.length })}</span></div>{model.missingItems.length ? <ul className="mt-3 grid gap-2 text-xs text-amber-900 sm:grid-cols-2">{model.missingItems.map((item) => <li key={item} className="rounded-lg bg-white/70 px-3 py-2">{item}</li>)}</ul> : <p className="mt-3 text-xs text-amber-900">{copy("viz.missingNone")}</p>}<p className="mt-3 text-[11px] leading-5 text-amber-800">{copy("viz.missingNote")}</p></section>;
}
