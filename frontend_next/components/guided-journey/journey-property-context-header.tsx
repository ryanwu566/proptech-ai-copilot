"use client";

import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { JourneyPropertyContext } from "@/lib/location-market-journey";

export function JourneyPropertyContextHeader({ context, onBackToProperty, onDirectValuation }: { context: JourneyPropertyContext; onBackToProperty: () => void; onDirectValuation?: () => void }) {
  const { t, formatNumber } = useExperienceLocale();
  const hasContext = context.selectionStatus !== "not_selected";
  const statusLabel = context.selectionStatus === "partial" ? t("state.partial.heading") : t("journey.property.title");
  const missing = t("state.empty.next");
  return <section data-testid="journey-property-context" aria-labelledby="journey-property-context-heading" className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-4">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0"><p className="text-[10px] font-bold tracking-wider text-cyan-700">{t("journey.property.title")}</p><h3 id="journey-property-context-heading" className="mt-1 text-base font-black text-slate-950">{hasContext ? t("journey.property.title") : t("state.empty.heading")}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{hasContext ? t("journey.property.description") : t("state.empty.explanation")}</p></div>
      <button type="button" onClick={onBackToProperty} className="shrink-0 rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800 transition hover:bg-cyan-50 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2">{hasContext ? t("journey.property.previous") : t("journey.property.next")}</button>
    </div>
    {hasContext && <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
      <ContextField label={t("page.map")} value={[context.city, context.district, context.road, context.addressSummary].filter(Boolean).join(" ") || missing} />
      <ContextField label={t("journey.property.title")} value={context.buildingType || missing} />
      <ContextField label={t("journey.price.title")} value={context.areaPing === undefined ? missing : `${formatNumber(context.areaPing)} Ping`} />
      <ContextField label={t("journey.price.next")} value={context.askingPriceWan === undefined ? missing : `${formatNumber(context.askingPriceWan)}`} />
      <div className="sm:col-span-2 lg:col-span-4"><dt className="font-bold text-slate-500">{t("evidence.source")}</dt><dd className="mt-1 text-slate-700">{context.sourceLabel} · {statusLabel}</dd></div>
    </dl>}
  </section>;
}

function ContextField({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-cyan-100 bg-white p-2.5"><dt className="font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-slate-800">{value}</dd></div>; }
