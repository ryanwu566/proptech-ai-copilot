import type { EvidenceItem } from "@/lib/market-insight-visualization";

export function EvidenceSummary({ items }: { items: EvidenceItem[] }) {
  const summaryItems = items.filter((item) => ["資料來源", "資料更新日期", "資料期間", "交易筆數", "涵蓋狀態", "資料狀態"].includes(item.label));
  return <section aria-label="市場資料證據摘要" className="rounded-xl border border-cyan-100 bg-cyan-50/50 p-4">
    <h3 className="text-sm font-bold text-slate-900">資料來源與限制摘要</h3>
    <dl className="mt-3 grid gap-2 text-xs text-slate-700 sm:grid-cols-2">{summaryItems.map((item) => <div key={item.label}><dt className="font-bold text-slate-800">{item.label}</dt><dd>{item.value}</dd></div>)}</dl>
  </section>;
}
