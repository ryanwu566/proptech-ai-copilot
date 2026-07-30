"use client";

import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { JourneyDecisionContext } from "@/lib/decision-case-journey";

export function JourneyDecisionContextHeader({ context, onBackToProperty, onBackToPrice, onBackToAffordability }: { context: JourneyDecisionContext; onBackToProperty: () => void; onBackToPrice: () => void; onBackToAffordability: () => void }) {
  const { t } = useExperienceLocale();
  const noProperty = context.propertyContext.selectionStatus === "not_selected";
  const propertyStatus = noProperty ? t("state.empty.heading") : t("journey.property.title");
  const priceStatus = context.officialValuationAvailable ? t("state.ready.heading") : context.priceStatus === "unavailable" ? t("state.unavailable.heading") : t("state.not_assessed.heading");
  const loanStatus = context.loanKnown ? t("state.ready.heading") : t("state.not_assessed.heading");
  const caseStatus = context.candidateCaseId ? t("state.ready.heading") : t("state.not_assessed.heading");
  return <section aria-labelledby="journey-decision-context-heading" className="min-w-0 rounded-xl border border-cyan-100 bg-cyan-50/60 p-4">
    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"><div className="min-w-0"><p className="text-[10px] font-bold tracking-wider text-cyan-700">{t("journey.decision.title")}</p><h3 id="journey-decision-context-heading" className="mt-1 text-lg font-black text-slate-950">{t("journey.decision.question")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{noProperty ? t("state.empty.explanation") : t("journey.decision.description")}</p></div><div className="grid grid-cols-1 gap-2 sm:grid-cols-3"><button type="button" onClick={onBackToProperty} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800">{t("journey.property.previous")}</button><button type="button" onClick={onBackToPrice} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800">{t("journey.price.previous")}</button><button type="button" onClick={onBackToAffordability} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800">{t("journey.affordability.previous")}</button></div></div>
    <dl className="mt-4 grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-4"><ContextField label={t("journey.property.title")} value={propertyStatus} /><ContextField label={t("journey.price.title")} value={priceStatus} /><ContextField label={t("journey.affordability.title")} value={loanStatus} /><ContextField label={t("journey.decision.title")} value={caseStatus} /></dl>
  </section>;
}

function ContextField({ label, value }: { label: string; value: string }) { return <div className="min-w-0 rounded-lg border border-cyan-100 bg-white p-3"><dt className="text-[10px] font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold text-slate-900">{value}</dd></div>; }
