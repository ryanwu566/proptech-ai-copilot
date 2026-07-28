import type { JourneyDecisionContext } from "@/lib/decision-case-journey";

export function DecisionCaseStatusStrip({ context }: { context: JourneyDecisionContext }) {
  const items = [
    ["物件資料", context.propertyContext.selectionStatus === "not_selected" ? "未提供" : context.propertyContext.selectionStatus === "partial" ? "部分提供" : "已輸入"],
    ["價格證據", context.officialValuationAvailable ? "官方資料可用" : context.priceStatus === "demo" ? "展示資料不可轉入" : context.priceStatus === "unavailable" ? "資料暫時無法取得" : "資料不足"],
    ["資金與稅務", context.affordabilityStatus === "available" ? "已有試算" : context.affordabilityStatus === "partial" ? "部分資料" : context.taxStatus === "not_eligible" ? "有待人工複核" : "尚未試算"],
    ["盡職調查", "尚未開始"],
    ["看屋與下一步", "尚無看屋紀錄"],
  ] as const;
  return <section aria-label="案件狀態摘要" className="min-w-0 rounded-xl border border-stone-200 bg-white p-4"><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">{items.map(([label, value]) => <div key={label} className="min-w-0 rounded-lg border border-stone-200 bg-stone-50 p-3"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className="mt-1 break-words text-xs font-black text-slate-900">{value}</p></div>)}</div></section>;
}
