import { selectChartLabelIndexes, type MarketHistoryPoint } from "@/lib/market-insight-visualization";
import type { MarketDisplayState } from "@/lib/market-result-state";
import { ChartEmptyState } from "./chart-empty-state";
import { ChartUnavailableState } from "./chart-unavailable-state";

export function VolumeBarChart({ data, status }: { data: MarketHistoryPoint[]; status: MarketDisplayState }) {
  if (status !== "available") return status === "unavailable" ? <ChartUnavailableState /> : <ChartEmptyState />;
  if (data.length < 2) return <ChartEmptyState />;
  const max = Math.max(...data.map((point) => point.transaction_count));
  const labelIndexes = selectChartLabelIndexes(data.length);
  return <div className=" max-w-full overflow-hidden" aria-label="交易筆數（筆）柱狀圖與文字摘要">
    <svg viewBox="0 0 640 280" role="img" aria-label="交易筆數（筆）柱狀圖" className="h-auto w-full">
      <title>交易筆數（筆）趨勢</title><desc>顯示各有效期別的交易筆數，不以缺失資料補零。</desc>
      {data.map((point, index) => { const x = 48 + (index * 544) / data.length; const barWidth = Math.max(8, 480 / data.length); const barHeight = (point.transaction_count / max) * 200; return <rect key={`${point.period}-${index}`} x={x} y={224 - barHeight} width={barWidth} height={barHeight} className="fill-cyan-600" />; })}
      {labelIndexes.map((index) => { const point = data[index]; const x = 48 + (index * 544) / data.length; const barWidth = Math.max(8, 480 / data.length); return <text key={`${point.period}-label-${index}`} x={x + barWidth / 2} y="252" textAnchor="middle" className="fill-slate-600 text-[11px]">{point.period}</text>; })}
    </svg>
    <p className="mt-2 text-xs text-slate-600">交易量圖表只呈現可驗證的正值交易筆數（筆）。</p>
  </div>;
}
