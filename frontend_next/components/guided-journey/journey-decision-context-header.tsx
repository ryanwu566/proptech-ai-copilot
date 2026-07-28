import type { JourneyDecisionContext } from "@/lib/decision-case-journey";

export function JourneyDecisionContextHeader({ context, onBackToProperty, onBackToPrice, onBackToAffordability }: { context: JourneyDecisionContext; onBackToProperty: () => void; onBackToPrice: () => void; onBackToAffordability: () => void }) {
  return <section aria-labelledby="journey-decision-context-heading" className="min-w-0 rounded-xl border border-cyan-100 bg-cyan-50/60 p-4">
    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
      <div className="min-w-0"><p className="text-[10px] font-bold tracking-wider text-cyan-700">JOURNEY DECISION CONTEXT</p><h3 id="journey-decision-context-heading" className="mt-1 text-lg font-black text-slate-950">目前案件脈絡</h3><p className="mt-1 text-xs leading-5 text-slate-600">{context.propertyContext.selectionStatus === "not_selected" ? "尚未選定物件" : "只整理目前 Journey 已知摘要，不代表資料完整或可購買。"}</p></div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3"><button type="button" onClick={onBackToProperty} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800">返回物件步驟</button><button type="button" onClick={onBackToPrice} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800">返回價格步驟</button><button type="button" onClick={onBackToAffordability} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800">返回資金步驟</button></div>
    </div>
    <dl className="mt-4 grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-4"><ContextField label="物件" value={context.propertyContext.selectionStatus === "not_selected" ? "尚未選定物件" : [context.propertyContext.city, context.propertyContext.district, context.propertyContext.road].filter(Boolean).join(" ") || "部分提供"} /><ContextField label="價格資料" value={context.officialValuationAvailable ? "官方資料可用" : context.priceStatus === "unavailable" ? "資料暫時無法取得" : "尚無可採取行動的官方估價"} /><ContextField label="資金資料" value={context.loanKnown ? "已有貸款試算" : "尚未完成貸款試算"} /><ContextField label="案件" value={context.candidateCaseId ? "已有案件脈絡" : "尚未建立案件"} /></dl>
  </section>;
}

function ContextField({ label, value }: { label: string; value: string }) { return <div className="min-w-0 rounded-lg border border-cyan-100 bg-white p-3"><dt className="text-[10px] font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold text-slate-900">{value}</dd></div>; }
