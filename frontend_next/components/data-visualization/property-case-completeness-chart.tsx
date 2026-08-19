"use client";

import type { PropertyCaseVisualModel } from "@/lib/property-case-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PropertyCaseCompletenessChart({ model }: { model: PropertyCaseVisualModel }) {
  const { copy } = useExperienceLocale();
  const stateLabel = (state: string): string => {
    const map: Record<string, string> = { completed: copy("viz.completenessStateCompleted"), partial: copy("viz.completenessStatePartial"), missing: copy("viz.completenessStateMissing"), blocked: copy("viz.completenessStateBlocked"), not_assessed: copy("viz.completenessStateNotAssessed") };
    return map[state] ?? copy("viz.completenessStateNotAssessed");
  };
  return <section className="rounded-2xl border border-stone-200 bg-white p-4" aria-label={copy("viz.completenessTitle")}>
    <div className="flex items-baseline justify-between gap-3"><div><p className="text-xs font-bold text-slate-500">{copy("viz.completenessKicker")}</p><h3 className="mt-1 text-sm font-black text-slate-900">{copy("viz.completenessTitle")}</h3></div><span className="text-xs font-bold text-slate-600">{model.overall.completionRatio === null ? copy("viz.completenessNoItems") : `${Math.round(model.overall.completionRatio * 100)}%`}</span></div>
    <div className="mt-4 space-y-3" role="img" aria-label={copy("viz.completenessTitle")}>{model.sections.map((section) => <div key={section.id}><div className="flex items-center justify-between gap-3 text-xs"><span className="font-bold text-slate-800">{section.label}: {stateLabel(section.state)}</span><span className="text-slate-500">{section.completedCount} / {section.totalCount}</span></div><div className="mt-1 h-2 overflow-hidden rounded-full bg-stone-100"><div className="h-full rounded-full bg-cyan-600" style={{ width: `${section.totalCount ? (section.completedCount / section.totalCount) * 100 : 0}%` }} /></div>{section.missingItems.length > 0 && <p className="mt-1 text-[10px] text-amber-700">{copy("viz.completenessMissingPrefix")}{section.missingItems.length}: {section.missingItems.slice(0, 2).join(", ")}</p>}</div>)}</div>
    <p className="mt-3 text-[11px] leading-5 text-slate-500">{copy("viz.completenessNote")}</p>
  </section>;
}
