import type { LocationMarketStatusItem } from "@/lib/location-market-journey";

export function LocationMarketSnapshot({ items, evidenceAvailable }: { items: readonly LocationMarketStatusItem[]; evidenceAvailable?: boolean }) {
  return <section aria-labelledby="location-market-snapshot-heading" data-evidence-available={evidenceAvailable ? "yes" : "no"} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
    <h3 id="location-market-snapshot-heading" className="text-sm font-black text-slate-950">地點與市場資料概況</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">各項資料彼此獨立，僅整理目前已知狀態，不代表綜合評價。</p>
    <ul className="mt-3 grid gap-2 text-xs sm:grid-cols-2">{items.map((item) => <li key={item.id} className="flex items-start justify-between gap-3 rounded-lg border border-stone-200 bg-white px-3 py-2"><span className="font-bold text-slate-700">{item.label}</span><span className="text-right text-slate-600">{item.statusLabel}</span></li>)}</ul>
  </section>;
}
