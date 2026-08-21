"use client";

import type { ValuationDataStatus, ValuationFreshnessStatus } from "@/lib/api";
import { useExperienceLocale } from "@/components/experience-locale-provider";

const LABELS: Record<ValuationFreshnessStatus, string> = {
  fresh: "資料更新狀態正常",
  aging: "資料逐漸接近建議更新時間",
  stale: "官方資料已超過建議更新週期",
  unknown: "目前無法確認資料新鮮度",
  no_official_data: "目前沒有可確認的官方 PLVR 資料",
  unavailable: "目前無法讀取資料維運狀態",
};

export function ValuationDataFreshness({ status }: { status: ValuationDataStatus }) {
  const { copy } = useExperienceLocale();
  const freshnessStatus = status.freshness_status || "unknown";
  const officialCount = typeof status.official_records_count === "number" ? status.official_records_count : null;
  const period = status.newest_effective_period || "尚無可確認的有效期別";
  const importedAt = officialCount && status.latest_import_at ? status.latest_import_at : "尚無可確認的官方匯入時間";
  return <section aria-label={copy("aria.plvrFreshness")} className="mt-4 rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs text-slate-700">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="font-bold text-slate-900">官方 PLVR 資料新鮮度</h3>
      <span className={freshnessStatus === "fresh" ? "rounded-full bg-emerald-50 px-2 py-1 text-emerald-800" : "rounded-full bg-amber-50 px-2 py-1 text-amber-800"}>{LABELS[freshnessStatus]}</span>
    </div>
    <div className="mt-2 grid gap-2 sm:grid-cols-3">
      <p>最近完成匯入：<strong>{importedAt}</strong></p>
      <p>最新有效期別：<strong>{period}</strong></p>
      <p>官方資料筆數：<strong>{officialCount === null ? "資料不足" : officialCount === 0 ? "目前沒有可確認的官方資料筆數" : officialCount.toLocaleString()}</strong></p>
    </div>
    <p className="mt-2 leading-5">{status.freshness_user_message}</p>
    {status.operator_attention_required && <p className="mt-2 rounded-lg bg-amber-100 px-2 py-2 font-medium text-amber-900">目前需要維運人員確認資料狀態；資料不足不代表沒有交易或估價結果較低。</p>}
    <p className="mt-2 leading-5 text-slate-500">資料新鮮度只描述資料維運狀態，不代表個別估價準確度，也不會自動修改估價、貸款、稅務或看房決策。</p>
  </section>;
}
