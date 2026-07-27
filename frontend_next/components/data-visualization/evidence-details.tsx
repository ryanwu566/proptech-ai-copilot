import type { EvidenceItem } from "@/lib/market-insight-visualization";

export function EvidenceDetails({ items }: { items: EvidenceItem[] }) {
  return <details className="rounded-xl border border-stone-200 bg-white">
    <summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-800">查看完整證據欄位</summary>
    <div className="border-t border-stone-100 p-4"><dl className="grid gap-2 text-xs text-slate-700 sm:grid-cols-2">{items.map((item) => <div key={item.key}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl></div>
  </details>;
}
