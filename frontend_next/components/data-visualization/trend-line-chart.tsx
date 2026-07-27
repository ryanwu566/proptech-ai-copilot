import type { MarketHistoryPoint } from "@/lib/market-insight-visualization";
import type { MarketDisplayState } from "@/lib/market-result-state";
import { ChartEmptyState } from "./chart-empty-state";
import { ChartUnavailableState } from "./chart-unavailable-state";

export function TrendLineChart({ data, status, textSummary }: { data: MarketHistoryPoint[]; status: MarketDisplayState; textSummary: string }) {
  if (status !== "available") return status === "unavailable" ? <ChartUnavailableState /> : <ChartEmptyState />;
  if (data.length < 2) return <ChartEmptyState />;
  const width = 640;
  const height = 280;
  const min = Math.min(...data.map((point) => point.average_unit_price));
  const max = Math.max(...data.map((point) => point.average_unit_price));
  const range = max - min || 1;
  const points = data.map((point, index) => `${40 + (index * 560) / (data.length - 1)},${24 + (1 - (point.average_unit_price - min) / range) * 200}`).join(" ");
  return <div className="min-h-[320px] overflow-x-auto" aria-label="平均單價趨勢圖與文字摘要">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="平均單價趨勢折線圖" className="h-auto min-h-[320px] min-w-[560px] w-full">
      <title>平均單價趨勢</title><desc>{textSummary}</desc>
      <polyline fill="none" stroke="currentColor" strokeWidth="4" points={points} className="text-cyan-700" />
      {data.map((point, index) => <text key={`${point.period}-${index}`} x={40 + (index * 560) / (data.length - 1)} y="252" textAnchor="middle" className="fill-slate-600 text-[11px]">{point.period}</text>)}
    </svg>
    <p className="mt-2 text-xs text-slate-600">{textSummary}</p>
  </div>;
}
