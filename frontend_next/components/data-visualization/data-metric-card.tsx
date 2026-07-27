import { formatMarketMetric } from "@/lib/market-insight-visualization";
import type { MarketDisplayState } from "@/lib/market-result-state";

export function DataMetricCard({ label, value, suffix = "", status, note }: { label: string; value: number | null; suffix?: string; status: MarketDisplayState; note?: string }) {
  const showValue = status === "available" && value !== null;
  return <article className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm" aria-label={label}>
    <p className="text-xs font-bold text-slate-500">{label}</p>
    <p className="mt-2 text-xl font-black tracking-tight text-slate-950">{showValue ? formatMarketMetric(value, suffix) : "尚無可用資料"}</p>
    {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
  </article>;
}
