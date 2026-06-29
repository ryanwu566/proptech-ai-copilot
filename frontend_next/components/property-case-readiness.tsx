"use client";

import type { PropertyCaseDraft } from "@/lib/property-case";
import { buildPropertyCaseReadiness, moduleLabel } from "@/lib/property-case-readiness";

export function PropertyCaseReadiness({ draft }: { draft: PropertyCaseDraft }) {
  const readiness = buildPropertyCaseReadiness(draft);
  const tone = readiness.state === "ready"
    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
    : readiness.state === "unavailable"
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : "border-cyan-200 bg-cyan-50 text-cyan-900";
  const statuses = [
    ["物件資料", draft.analysis_status.property],
    ["位置分析", draft.analysis_status.location],
    ["地勢風險", draft.analysis_status.terrain],
    ["通勤資訊", draft.analysis_status.commute],
    ["估價", draft.analysis_status.valuation],
    ["貸款", draft.analysis_status.loan],
    ["持有成本", draft.analysis_status.holding],
    ["稅費", draft.analysis_status.tax],
  ] as const;

  return <section className="rounded-xl border border-stone-200 bg-white p-4" aria-label="案件決策完整度">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-[10px] font-bold tracking-wider text-cyan-700">PROPERTY CASE</p>
        <h3 className="mt-1 text-base font-bold text-slate-950">案件決策完整度</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">{readiness.primaryMessage}</p>
      </div>
      <span className={`rounded-full border px-3 py-1 text-xs font-bold ${tone}`}>{readiness.label}</span>
    </div>
    <div className="mt-4 grid gap-2 text-[11px] sm:grid-cols-2 xl:grid-cols-5">
      <InfoPill label="案件名稱" value={draft.case_name || "待補案件名稱"} />
      <InfoPill label="物件地址／識別" value={draft.property_input.address || "待補物件地址／識別"} />
      <InfoPill label="可比較價格" value={draft.property_input.listing_price ? `${draft.property_input.listing_price.toLocaleString()} 萬` : "待補資料"} />
      <InfoPill label="可比較" value={draft.readiness.compare_ready ? "是" : "否"} />
      <InfoPill label="可列印目前摘要" value={draft.readiness.print_ready ? "是" : "否"} />
    </div>
    <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {statuses.map(([label, status]) => <div key={label} className="rounded-lg bg-stone-50 px-3 py-2 text-[11px]"><span className="font-bold text-slate-700">{label}</span><span className="ml-2 text-slate-500">{readiness.statusLabels[status]}</span></div>)}
    </div>
    {draft.readiness.print_notice && <p className="mt-3 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-900">{draft.readiness.print_notice}</p>}
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      <div className="rounded-lg border border-cyan-100 bg-cyan-50/60 p-3">
        <p className="text-xs font-bold text-cyan-900">下一步</p>
        <ul className="mt-2 space-y-1 text-[11px] leading-5 text-cyan-900">{readiness.nextSteps.map((step) => <li key={step}>・{step}</li>)}</ul>
      </div>
      <div className="rounded-lg border border-amber-100 bg-amber-50/60 p-3">
        <p className="text-xs font-bold text-amber-900">資料限制</p>
        <ul className="mt-2 space-y-1 text-[11px] leading-5 text-amber-900">
          {(readiness.safeWarnings.length ? readiness.safeWarnings : ["案件完整度只整理目前可用資訊，不是投資評分、買賣建議或核貸判斷。"]).map((warning) => <li key={warning}>・{warning}</li>)}
        </ul>
      </div>
    </div>
    {draft.readiness.missing_required.length > 0 && <p className="mt-3 text-[10px] leading-5 text-slate-500">待補資料：{draft.readiness.missing_required.map(moduleLabel).join("、")}</p>}
  </section>;
}

function InfoPill({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-stone-50 px-3 py-2"><p className="text-[9px] font-bold text-slate-400">{label}</p><p className="mt-1 truncate font-bold text-slate-800">{value}</p></div>;
}
