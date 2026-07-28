import type { PropertyCaseVisualScenario } from "@/lib/property-case-visualization";

export function PropertyCaseFinancialComparison({ scenarios }: { scenarios: PropertyCaseVisualScenario[] }) {
  const fields = [
    ["totalCommitment", "總承諾金額"],
    ["cashNeeded", "初期所需現金"],
    ["monthlyPayment", "每月月付"],
    ["monthlyBurden", "每月總負擔"],
    ["postPurchaseCash", "購屋後現金"],
  ] as const;
  return <section className="rounded-2xl border border-stone-200 bg-white p-4" aria-label="財務情境比較">
    <div><p className="text-xs font-bold text-slate-500">FINANCIAL SCENARIOS</p><h3 className="mt-1 text-sm font-black text-slate-900">財務情境比較</h3><p className="mt-1 text-xs text-slate-600">保留基準方案與既有情境順序，只比較已知欄位，不選出最佳方案。</p></div>
    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{scenarios.map((scenario) => <article key={scenario.scenarioName} className="min-w-0 rounded-xl border border-stone-200 bg-stone-50 p-3"><h4 className="truncate text-xs font-black text-slate-900">{scenario.scenarioName}</h4><div className="mt-3 space-y-2 text-[11px]">{fields.map(([key, label]) => <Metric key={key} label={label} metric={scenario.analysis[key]} unit={key.includes("Payment") || key.includes("Burden") ? "元" : "萬元"} />)}</div></article>)}</div>
    <details className="mt-4 rounded-xl border border-stone-200"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-slate-700">查看財務情境欄位摘要</summary><div className="max-w-full overflow-x-auto border-t border-stone-200"><table className="w-full min-w-[620px] text-left text-[11px]"><thead><tr className="bg-stone-50"><th className="p-2">欄位</th>{scenarios.map((scenario) => <th key={scenario.scenarioName} className="p-2">{scenario.scenarioName}</th>)}</tr></thead><tbody>{fields.map(([key, label]) => <tr key={key} className="border-t border-stone-100"><th className="p-2 font-bold">{label}</th>{scenarios.map((scenario) => <td key={scenario.scenarioName} className="p-2">{formatMetric(scenario.analysis[key])}</td>)}</tr>)}</tbody></table></div></details>
  </section>;
}

function Metric({ label, metric, unit }: { label: string; metric: { status: string; value: number | null }; unit: string }) {
  return <div className="flex items-center justify-between gap-2"><span className="text-slate-600">{label}</span><strong className="text-slate-900">{formatMetric(metric)}{metric.status === "available" && metric.value !== null ? ` ${unit}` : ""}</strong></div>;
}

function formatMetric(metric: { status: string; value: number | null }): string {
  return metric.status === "available" && typeof metric.value === "number" && Number.isFinite(metric.value) ? metric.value.toLocaleString() : "未提供";
}
