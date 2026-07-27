import { selectChartLabelIndexes, type ValuationVisualModel } from "@/lib/valuation-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function ValuationTrendChart({ model }: { model: ValuationVisualModel }) {
  if (model.state !== "available") return <VisualDataUnavailableState message="估價趨勢目前無法使用，請稍後再試。" />;
  if (model.trend.length < 2) return <VisualDataUnavailableState message="目前沒有足夠的官方成交月份可供趨勢分析。" />;
  const min = Math.min(...model.trend.map((point) => point.p25));
  const max = Math.max(...model.trend.map((point) => point.p75));
  const range = max - min || 1;
  const x = (index: number) => 48 + (index * 544) / (model.trend.length - 1);
  const y = (value: number) => 220 - ((value - min) / range) * 170;
  const medianPoints = model.trend.map((point, index) => `${x(index)},${y(point.median)}`).join(" ");
  const labels = selectChartLabelIndexes(model.trend.length);
  return <div aria-label="估價官方成交趨勢圖" className="min-h-[320px] max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <svg viewBox="0 0 640 270" role="img" aria-label="官方成交中位單價趨勢" className="h-auto w-full"><title>官方成交趨勢</title><desc>顯示官方成交的 P25、中位數與 P75 單價趨勢，不包含預測值。</desc><polyline points={model.trend.map((point, index) => `${x(index)},${y(point.p25)}`).join(" ")} fill="none" className="stroke-cyan-200" strokeWidth="2" /><polyline points={medianPoints} fill="none" className="stroke-cyan-700" strokeWidth="4" /><polyline points={model.trend.map((point, index) => `${x(index)},${y(point.p75)}`).join(" ")} fill="none" className="stroke-cyan-200" strokeWidth="2" />{labels.map((index) => <text key={`${model.trend[index].period}-${index}`} x={x(index)} y="250" textAnchor="middle" className="fill-slate-600 text-[11px]">{model.trend[index].period}</text>)}</svg>
    <p className="mt-2 text-xs text-slate-600">趨勢僅呈現已發生的官方成交月份；不將 forecast 當成歷史資料。</p>
  </div>;
}
