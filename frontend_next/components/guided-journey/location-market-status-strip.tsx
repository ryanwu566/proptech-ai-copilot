import type { LocationMarketStatusItem } from "@/lib/location-market-journey";

export function LocationMarketStatusStrip({ items, onOpen }: { items: readonly LocationMarketStatusItem[]; onOpen: (id: LocationMarketStatusItem["id"]) => void }) {
  return <section aria-labelledby="location-market-status-heading" className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex items-baseline justify-between gap-3"><h3 id="location-market-status-heading" className="text-sm font-black text-slate-950">地點與市場四面向狀態</h3><span className="text-[10px] text-slate-500">各面向彼此獨立</span></div>
    <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{items.map((item) => <article key={item.id} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
      <div className="flex items-start justify-between gap-2"><div><p className="text-xs font-bold text-slate-900">{item.label}</p><p className="mt-1 text-[11px] font-bold text-slate-700">{item.statusLabel}</p></div><span aria-hidden="true" className="mt-1 h-2 w-2 shrink-0 rounded-full bg-slate-400" /></div>
      <p className="mt-2 text-[10px] leading-5 text-slate-500">{item.summary}</p>
      <button type="button" onClick={() => onOpen(item.id)} className="mt-3 w-full rounded-md border border-stone-300 bg-white px-2 py-1.5 text-[11px] font-bold text-slate-700 transition hover:border-cyan-300 hover:text-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2">開啟</button>
    </article>)}</div>
  </section>;
}
