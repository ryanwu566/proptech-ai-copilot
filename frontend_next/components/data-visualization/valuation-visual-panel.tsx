import type { ValuationVisualModel } from "@/lib/valuation-visualization";
import { MetricTile, SectionCard } from "@/components/product-ui";
import { ValuationDistributionChart } from "./valuation-distribution-chart";
import { ValuationEvidenceSummary } from "./valuation-evidence-summary";
import { ValuationPriceRangeBand } from "./valuation-price-range-band";
import { ValuationTrendChart } from "./valuation-trend-chart";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function ValuationVisualPanel({ model }: { model: ValuationVisualModel }) {
  if (!model.actionable) return <VisualDataUnavailableState message="目前沒有足夠官方可比資料支援估價視覺化；不以零值或低風險代替缺失資料。" state={model.state === "no_data" || model.state === "demo" ? "no_official_data" : "unavailable"} />;
  return <div className="min-w-0 space-y-4">
    <ValuationEvidenceSummary model={model} />
    <details className="min-w-0 rounded-xl border border-stone-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-inset">查看估價圖表與比較細節</summary>
      <div className="min-w-0 space-y-4 border-t border-stone-100 p-4">
        <SectionCard title="估價結果摘要"><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label="估價總價" value={`${model.metrics.estimateTotal?.toLocaleString() ?? "目前無可用資料"} 萬`} /><MetricTile label="估算單價" value={`${model.metrics.estimateUnit?.toLocaleString() ?? "目前無可用資料"} 萬`} /><MetricTile label="資料信心" value={model.metrics.confidence ?? "目前無可用資料"} /><MetricTile label="有效比較筆數" value={model.metrics.comparableCount ?? "目前無可用資料"} /></div></SectionCard>
        <SectionCard title="估價價格範圍"><ValuationPriceRangeBand model={model} /></SectionCard>
        <SectionCard title="官方可比成交分布"><ValuationDistributionChart model={model} /></SectionCard>
        <SectionCard title="官方成交趨勢"><ValuationTrendChart model={model} /></SectionCard>
      </div>
    </details>
  </div>;
}
