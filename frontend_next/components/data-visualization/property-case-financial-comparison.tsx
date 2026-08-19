"use client";

import type { PropertyCaseVisualScenario } from "@/lib/property-case-visualization";
import type { PropertyCaseFinancialAnalysis } from "@/lib/property-case-financials";
import { useExperienceLocale } from "@/components/experience-locale-provider";

type FieldKey = keyof Pick<PropertyCaseFinancialAnalysis, "totalCommitment" | "cashNeeded" | "monthlyPayment" | "monthlyBurden" | "postPurchaseCash">;

export function PropertyCaseFinancialComparison({ scenarios }: { scenarios: PropertyCaseVisualScenario[] }) {
  const { copy } = useExperienceLocale();
  const fields: [FieldKey, string][] = [
    ["totalCommitment", copy("viz.financialTotalCommitment")],
    ["cashNeeded", copy("viz.financialCashNeeded")],
    ["monthlyPayment", copy("viz.financialMonthlyPayment")],
    ["monthlyBurden", copy("viz.financialMonthlyBurden")],
    ["postPurchaseCash", copy("viz.financialPostPurchaseCash")],
  ];
  return <section className="rounded-2xl border border-stone-200 bg-white p-4" aria-label={copy("viz.financialTitle")}>
    <div><p className="text-xs font-bold text-slate-500">{copy("viz.financialKicker")}</p><h3 className="mt-1 text-sm font-black text-slate-900">{copy("viz.financialTitle")}</h3><p className="mt-1 text-xs text-slate-600">{copy("viz.financialDesc")}</p></div>
    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{scenarios.map((scenario) => <article key={scenario.scenarioName} className="min-w-0 rounded-xl border border-stone-200 bg-stone-50 p-3"><h4 className="truncate text-xs font-black text-slate-900">{scenario.scenarioName}</h4><div className="mt-3 space-y-2 text-[11px]">{fields.map(([key, label]) => <Metric key={key} label={label} metric={scenario.analysis[key]} notProvided={copy("viz.financialNotProvided")} />)}</div></article>)}</div>
    <details className="mt-4 rounded-xl border border-stone-200"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-slate-700">{copy("viz.financialDetailsTitle")}</summary><div className="max-w-full overflow-x-auto border-t border-stone-200"><table className="w-full min-w-[620px] text-left text-[11px]"><thead><tr className="bg-stone-50"><th className="p-2">{copy("viz.financialFieldLabel")}</th>{scenarios.map((scenario) => <th key={scenario.scenarioName} className="p-2">{scenario.scenarioName}</th>)}</tr></thead><tbody>{fields.map(([key, label]) => <tr key={key} className="border-t border-stone-100"><th className="p-2 font-bold">{label}</th>{scenarios.map((scenario) => <td key={scenario.scenarioName} className="p-2">{formatMetric(scenario.analysis[key], copy("viz.financialNotProvided"))}</td>)}</tr>)}</tbody></table></div></details>
  </section>;
}

function Metric({ label, metric, notProvided }: { label: string; metric: { status: string; value: number | null }; notProvided: string }) {
  return <div className="flex items-center justify-between gap-2"><span className="text-slate-600">{label}</span><strong className="text-slate-900">{formatMetric(metric, notProvided)}</strong></div>;
}

function formatMetric(metric: { status: string; value: number | null }, notProvided: string): string {
  return metric.status === "available" && typeof metric.value === "number" && Number.isFinite(metric.value) ? metric.value.toLocaleString() : notProvided;
}
