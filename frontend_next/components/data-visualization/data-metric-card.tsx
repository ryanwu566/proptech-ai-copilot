"use client";

import { formatMarketMetric } from "@/lib/market-insight-visualization";
import type { MarketDisplayState } from "@/lib/market-result-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function DataMetricCard({ label, value, suffix = "", status, note }: { label: string; value: number | null; suffix?: string; status: MarketDisplayState; note?: string }) {
  const { copy } = useExperienceLocale();
  const showValue = status === "available" && value !== null;
  return <article className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm" aria-label={label}>
    <p className="text-xs font-bold text-slate-500">{label}</p>
    <p className="mt-2 text-xl font-black tracking-tight text-slate-950">{showValue ? formatMarketMetric(value, suffix) : copy("viz.dataMetricNoData")}</p>
    {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
  </article>;
}
