"use client";

import type { RiskSummary } from "@/lib/risk-summary";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { localizeRiskSignalLabel, localizeRiskSuggestion, localizePriceLabel, localizeFactorTitle, localizeFactorMessage, type RiskSignal } from "@/lib/dynamic-copy-localizers";
import type { RuntimeCopyKey } from "@/lib/runtime-copy";

const tones = {
  green: "border-emerald-300 bg-emerald-50 text-emerald-900",
  yellow: "border-amber-300 bg-amber-50 text-amber-900",
  red: "border-rose-300 bg-rose-50 text-rose-900",
  unknown: "border-slate-300 bg-slate-50 text-slate-700",
};

const lights = { green: "bg-emerald-500", yellow: "bg-amber-400", red: "bg-rose-500", unknown: "bg-slate-400" };

export function RiskSummaryPanel({ summary }: { summary: RiskSummary }) {
  const { copy, locale } = useExperienceLocale();
  const localizedLabel = localizeRiskSignalLabel(summary.overallSignal as RiskSignal, locale);
  const localizedSuggestion = localizeRiskSuggestion(summary.overallSignal as RiskSignal, locale);
  const localizedPriceLabel = localizePriceLabel(summary.priceReasonableness.status as any, locale);
  const localizedPriceExplanation = copy(summary.priceReasonableness.explanation as RuntimeCopyKey, summary.priceReasonableness.params);
  const confidenceLabelFn = (value: RiskSummary["dataConfidence"]) => ({
    high: copy("risk.confidenceHigh"),
    medium: copy("risk.confidenceMedium"),
    low: copy("risk.confidenceLow"),
    unknown: copy("risk.confidenceUnknown"),
  })[value];

  function localizeItems(items: string[]): string[] {
    return items.map((item) => copy(item as RuntimeCopyKey));
  }

  return <section id="risk-summary" className="min-w-0 scroll-mt-20 overflow-hidden rounded-xl border border-stone-200 bg-white" aria-label={copy("risk.heading")}>
    <div className={`border-b p-4 ${tones[summary.overallSignal]}`}>
      <div className="flex flex-wrap items-center gap-3"><span className={`h-12 w-12 shrink-0 rounded-full border-4 border-white shadow-md ${lights[summary.overallSignal]}`} /><div className="min-w-0 flex-1"><p className="text-[10px] font-bold tracking-wider">{copy("risk.kicker")}</p><h2 className="mt-1 text-lg font-extrabold">{copy("risk.heading")}: {localizedLabel}</h2><p className="mt-1 text-xs leading-5">{localizedSuggestion}</p></div><div className="rounded-lg bg-white/75 px-3 py-2 text-center"><p className="text-[10px]">{copy("risk.overallScore")}</p><p className="text-xl font-black">{summary.overallScore ?? "—"}</p></div></div>
    </div>
    <div className="p-4"><DetailDisclosure title={copy("risk.sourceTitle")}><div className="grid min-w-0 gap-3 md:grid-cols-2">
      <SummaryBlock title={copy("risk.priceReasonableness")} items={[`${localizedPriceLabel}: ${localizedPriceExplanation}`]} noEmpty={copy("risk.noPositive")} />
      <SummaryBlock title={copy("risk.dataConfidence")} items={[confidenceLabelFn(summary.dataConfidence)]} noEmpty={copy("risk.noPositive")} />
      <SummaryBlock title={copy("risk.positiveFactors")} items={summary.positiveFactors.map((item) => `${localizeFactorTitle(item.key, locale)}: ${localizeFactorMessage(item.key, "positive", locale, item.params)}`)} noEmpty={copy("risk.noPositive")} />
      <SummaryBlock title={copy("risk.riskFactors")} items={summary.riskFactors.map((item) => `${localizeFactorTitle(item.key, locale)}: ${localizeFactorMessage(item.key, item.level, locale, item.params)}`)} noEmpty={copy("risk.noRisk")} />
      <SummaryBlock title={copy("risk.missingChecks")} items={localizeItems(summary.missingChecks)} noEmpty={copy("risk.noMissing")} />
      <SummaryBlock title={copy("risk.nextSteps")} items={localizeItems(summary.nextActions)} noEmpty={copy("risk.noNextSteps")} />
      <div className="md:col-span-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
        <p className="text-xs font-bold text-amber-900">{copy("risk.sourceTitle")}</p>
        <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-900">{summary.referenceNotes.map((item) => <li key={item} className="break-words">・{item}</li>)}</ul>
      </div>
    </div></DetailDisclosure></div>
    <p className="border-t border-stone-100 px-4 py-3 text-[10px] leading-5 text-slate-500">{copy("risk.boundary")}</p>
  </section>;
}

function SummaryBlock({ title, items, noEmpty }: { title: string; items: string[]; noEmpty: string }) {
  const visible = items.length ? items : [noEmpty];
  return <div className="min-w-0 rounded-lg bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{visible.map((item) => <li key={item} className="break-words">• {item}</li>)}</ul></div>;
}
