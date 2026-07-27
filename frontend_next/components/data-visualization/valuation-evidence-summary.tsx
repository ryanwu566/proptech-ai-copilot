import type { ValuationVisualModel } from "@/lib/valuation-visualization";

export function ValuationEvidenceSummary({ model }: { model: ValuationVisualModel }) {
  return <section aria-label="估價資料證據摘要" className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-4"><h3 className="text-sm font-bold text-slate-900">估價資料來源與限制</h3><dl className="mt-3 grid gap-2 text-xs text-slate-700 sm:grid-cols-2">{model.evidence.slice(0, 6).map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl><details className="mt-3 rounded-lg border border-cyan-100 bg-white"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-slate-800">查看估價方法與完整限制</summary><dl className="grid gap-2 border-t border-stone-100 p-3 text-xs text-slate-700 sm:grid-cols-2">{model.evidence.slice(6).map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl></details></section>;
}
