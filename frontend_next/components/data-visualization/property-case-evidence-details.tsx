"use client";

import type { PropertyCaseDraft } from "@/lib/property-case";
import type { PropertyCaseVisualModel } from "@/lib/property-case-visualization";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PropertyCaseEvidenceDetails({ draft, model }: { draft: PropertyCaseDraft; model: PropertyCaseVisualModel }) {
  const { copy } = useExperienceLocale();
  return <details className="rounded-2xl border border-stone-200 bg-white"><summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-800">{copy("viz.evidenceDetailsTitle")}</summary><div className="grid gap-4 border-t border-stone-200 p-4 text-xs text-slate-700 md:grid-cols-2"><section><h3 className="font-bold text-slate-900">{copy("viz.evidenceDetailsSafeFields")}</h3><dl className="mt-2 space-y-2">{model.evidence.map((item) => <div key={item.label}><dt className="font-bold text-slate-500">{item.label}</dt><dd>{item.value}</dd></div>)}</dl></section><section><h3 className="font-bold text-slate-900">{copy("viz.evidenceDetailsInputSummary")}</h3><dl className="mt-2 space-y-2"><div><dt className="font-bold text-slate-500">{copy("viz.evidenceDetailsCaseName")}</dt><dd>{draft.case_name || copy("viz.evidenceDetailsNotProvided")}</dd></div><div><dt className="font-bold text-slate-500">{copy("viz.evidenceDetailsAddress")}</dt><dd>{draft.property_input.address || copy("viz.evidenceDetailsNotProvided")}</dd></div><div><dt className="font-bold text-slate-500">{copy("viz.evidenceDetailsNotes")}</dt><dd>{draft.property_input.notes || copy("viz.evidenceDetailsNotProvided")}</dd></div><div><dt className="font-bold text-slate-500">{copy("viz.evidenceDetailsPrint")}</dt><dd>{draft.readiness.print_ready ? copy("viz.evidenceDetailsPrintReady") : copy("viz.evidenceDetailsPrintNotReady")}</dd></div></dl></section><p className="md:col-span-2 rounded-xl bg-stone-50 p-3 leading-5">{copy("viz.evidenceDetailsBoundary")}</p></div></details>;
}
