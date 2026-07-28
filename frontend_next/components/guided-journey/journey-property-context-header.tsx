import type { JourneyPropertyContext } from "@/lib/location-market-journey";

export function JourneyPropertyContextHeader({ context, onBackToProperty }: { context: JourneyPropertyContext; onBackToProperty: () => void }) {
  const hasContext = context.selectionStatus !== "not_selected";
  return <section aria-labelledby="journey-property-context-heading" className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-4">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="text-[10px] font-bold tracking-wider text-cyan-700">PROPERTY CONTEXT</p>
        <h3 id="journey-property-context-heading" className="mt-1 text-base font-black text-slate-950">{hasContext ? "目前研究中的物件" : "尚未選定物件"}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">{hasContext ? "以下只整理目前使用者輸入或選擇的物件脈絡，不表示資料完整、已驗證或可購買。" : "可以返回第一步選擇物件，或直接在下方輸入地點進行區域研究。"}</p>
      </div>
      <button type="button" onClick={onBackToProperty} className="shrink-0 rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800 transition hover:bg-cyan-50 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2">{hasContext ? "更換物件" : "返回第一步找物件"}</button>
    </div>
    {hasContext && <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
      <ContextField label="位置摘要" value={[context.city, context.district, context.road, context.addressSummary].filter(Boolean).join(" ") || "未提供"} />
      <ContextField label="建物類型" value={context.buildingType || "未提供"} />
      <ContextField label="坪數" value={context.areaPing === undefined ? "未提供" : `${context.areaPing} 坪`} />
      <ContextField label="開價" value={context.askingPriceWan === undefined ? "未提供" : `${context.askingPriceWan} 萬`} />
      <div className="sm:col-span-2 lg:col-span-4"><dt className="font-bold text-slate-500">資料來源</dt><dd className="mt-1 text-slate-700">{context.sourceLabel} · {context.selectionStatus === "partial" ? "部分脈絡" : "已選取脈絡"}</dd></div>
    </dl>}
  </section>;
}

function ContextField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-cyan-100 bg-white p-2.5"><dt className="font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-slate-800">{value}</dd></div>;
}
