import type { MarketHistoryPoint } from "@/lib/market-insight-visualization";
import type { MarketDisplayState } from "@/lib/market-result-state";
import { ChartEmptyState } from "./chart-empty-state";
import { ChartUnavailableState } from "./chart-unavailable-state";

export function VolumeBarChart({ data, status }: { data: MarketHistoryPoint[]; status: MarketDisplayState }) {
  if (status !== "available") return status === "unavailable" ? <ChartUnavailableState /> : <ChartEmptyState />;
  if (data.length < 2) return <ChartEmptyState />;
  const max = Math.max(...data.map((point) => point.transaction_count));
  return <div className="min-h-[320px] overflow-x-auto" aria-label="交易量柱狀圖與文字摘要">
    <svg viewBox="0 0 640 280" role="img" aria-label="交易量柱狀圖" className="h-auto min-h-[320px] min-w-[560px] w-full">
      <title>交易量趨勢</title><desc>顯示各有效期別的交易筆數，不以缺失資料補零。</desc>
      {data.map((point, index) => { const x = 48 + (index * 544) / data.length; const barHeight = (point.transaction_count / max) * 200; return <g key={`${point.period}-${index}`}><rect x={x} y={224 - barHeight} width={Math.max(24, 480 / data.length)} height={barHeight} className="fill-cyan-600" /><text x={x + Math.max(24, 480 / data.length) / 2} y="252" textAnchor="middle" className="fill-slate-600 text-[11px]">{point.period}</text></g>; })}
    </svg>
    <p className="mt-2 text-xs text-slate-600">交易量圖表只呈現可驗證的正值交易筆數。</p>
  </div>;
}
