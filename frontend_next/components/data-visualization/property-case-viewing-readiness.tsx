import type { ViewingOfferReadinessResult } from "@/lib/property-case-viewing-offer";

export function PropertyCaseViewingReadiness({ readiness }: { readiness: ViewingOfferReadinessResult }) {
  return <section className="rounded-2xl border border-stone-200 bg-white p-4" aria-label="看屋與出價準備度"><div><p className="text-xs font-bold text-slate-500">VIEWING & OFFER</p><h3 className="mt-1 text-sm font-black text-slate-900">看屋／出價準備度</h3><p className="mt-1 text-xs text-slate-600">只呈現使用者已輸入的紀錄、問題與方案，不自動產生或選擇出價。</p></div><div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-5"><Stat label="看屋紀錄" value={readiness.viewing_count} /><Stat label="完成看屋" value={readiness.completed_viewing_count} /><Stat label="待問問題" value={readiness.open_question_count} /><Stat label="出價方案" value={readiness.offer_plan_count} /><Stat label="手動下一步" value={readiness.next_step_count} /></div><div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 p-3 text-xs leading-5 text-amber-900"><strong>準備度：{readinessLabel(readiness.readiness)}</strong><p className="mt-1">必要步驟仍由使用者判斷；資料不足不代表低風險或適合購買。</p></div></section>;
}

function Stat({ label, value }: { label: string; value: number }) { return <div className="rounded-lg bg-stone-50 p-2 text-center"><p className="text-[10px] text-slate-500">{label}</p><p className="mt-1 text-lg font-black text-slate-900">{value}</p></div>; }
function readinessLabel(value: string): string { return value === "completed" ? "部分條件已完成" : value === "partial" ? "部分提供" : "尚未提供"; }
