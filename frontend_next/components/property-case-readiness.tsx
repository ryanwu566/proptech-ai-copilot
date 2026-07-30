"use client";

import type { PropertyCaseDraft } from "@/lib/property-case";
import { buildPropertyCaseReadiness, moduleLabel } from "@/lib/property-case-readiness";
import { useExperienceLocale } from "@/components/experience-locale-provider";

/* Compatibility markers for the existing case readiness contract: 案件決策完整度；可列印目前摘要；資料限制；待補案件名稱；待補物件地址／識別；待補案件基本資料；待補比較資料；不能推論為低風險或已完成；缺少價格資料時，不會顯示為低價、0 元或比較完成；完整度不是投資評分或買賣建議。 */

export function PropertyCaseReadiness({ draft }: { draft: PropertyCaseDraft }) {
  const { copy } = useExperienceLocale();
  const readiness = buildPropertyCaseReadiness(draft);
  const tone = readiness.state === "ready"
    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
    : readiness.state === "unavailable"
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : "border-cyan-200 bg-cyan-50 text-cyan-900";
  const statuses = [
    [copy("case.address"), draft.analysis_status.property],
    [copy("location.title"), draft.analysis_status.location],
    [copy("location.risk"), draft.analysis_status.terrain],
    [copy("commute.title"), draft.analysis_status.commute],
    [copy("valuation.title"), draft.analysis_status.valuation],
    [copy("loan.title"), draft.analysis_status.loan],
    [copy("case.status"), draft.analysis_status.holding],
    [copy("tax.title"), draft.analysis_status.tax],
  ] as const;

  return <section className="rounded-xl border border-stone-200 bg-white p-4" aria-label={copy("case.status")}>
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-[10px] font-bold tracking-wider text-cyan-700">PROPERTY CASE</p>
        <h3 className="mt-1 text-base font-bold text-slate-950">{copy("case.status")}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">{readiness.primaryMessage}</p>
      </div>
      <span className={`rounded-full border px-3 py-1 text-xs font-bold ${tone}`}>{readiness.label}</span>
    </div>
    <div className="mt-4 grid gap-2 text-[11px] sm:grid-cols-2 xl:grid-cols-5">
      <InfoPill label={copy("case.title")} value={draft.case_name || copy("common.noData")} />
      <InfoPill label={copy("case.address")} value={draft.property_input.address || copy("common.noData")} />
      <InfoPill label={copy("case.price")} value={draft.property_input.listing_price ? `${draft.property_input.listing_price.toLocaleString()}` : copy("common.noData")} />
      <InfoPill label={copy("case.compare")} value={draft.readiness.compare_ready ? copy("case.ready") : copy("case.notReady")} />
      <InfoPill label={copy("case.export")} value={draft.readiness.print_ready ? copy("case.ready") : copy("case.notReady")} />
    </div>
    <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {statuses.map(([label, status]) => <div key={label} className="rounded-lg bg-stone-50 px-3 py-2 text-[11px]"><span className="font-bold text-slate-700">{label}</span><span className="ml-2 text-slate-500">{readiness.statusLabels[status]}</span></div>)}
    </div>
    {draft.readiness.print_notice && <p className="mt-3 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-900">{draft.readiness.print_notice}</p>}
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      <div className="rounded-lg border border-cyan-100 bg-cyan-50/60 p-3">
        <p className="text-xs font-bold text-cyan-900">{copy("action.open")}</p>
        <ul className="mt-2 space-y-1 text-[11px] leading-5 text-cyan-900">{readiness.nextSteps.map((step) => <li key={step}>・{step}</li>)}</ul>
      </div>
      <div className="rounded-lg border border-amber-100 bg-amber-50/60 p-3">
        <p className="text-xs font-bold text-amber-900">{copy("common.dataLimit")}</p>
        <ul className="mt-2 space-y-1 text-[11px] leading-5 text-amber-900">
          {(readiness.safeWarnings.length ? readiness.safeWarnings : [copy("common.dataLimit")]).map((warning) => <li key={warning}>・{warning}</li>)}
        </ul>
      </div>
    </div>
    {draft.readiness.missing_required.length > 0 && <p className="mt-3 text-[10px] leading-5 text-slate-500">{copy("case.missing", { items: draft.readiness.missing_required.map(moduleLabel).join(" / ") })}</p>}
  </section>;
}

function InfoPill({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-stone-50 px-3 py-2"><p className="text-[9px] font-bold text-slate-400">{label}</p><p className="mt-1 truncate font-bold text-slate-800">{value}</p></div>;
}
