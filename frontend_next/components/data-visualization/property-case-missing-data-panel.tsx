import type { PropertyCaseVisualModel } from "@/lib/property-case-visualization";

export function PropertyCaseMissingDataPanel({ model }: { model: PropertyCaseVisualModel }) {
  return <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4" aria-label="案件缺失資料"><div className="flex items-baseline justify-between gap-3"><div><p className="text-xs font-bold text-amber-800">MISSING DATA</p><h3 className="mt-1 text-sm font-black text-amber-950">待補資料與未評估項目</h3></div><span className="text-xs font-bold text-amber-800">{model.missingItems.length} 項</span></div>{model.missingItems.length ? <ul className="mt-3 grid gap-2 text-xs text-amber-900 sm:grid-cols-2">{model.missingItems.map((item) => <li key={item} className="rounded-lg bg-white/70 px-3 py-2">{item}</li>)}</ul> : <p className="mt-3 text-xs text-amber-900">目前沒有明確缺失項目；仍請依證據來源與人工確認判斷。</p>}<p className="mt-3 text-[11px] leading-5 text-amber-800">資料不足不會被填成 0、低風險、無成本或已完成。</p></section>;
}
