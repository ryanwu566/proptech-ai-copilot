import type { ValuationVisualModel } from "@/lib/valuation-visualization";
import { MetricTile, SectionCard } from "@/components/product-ui";
import { ValuationDistributionChart } from "./valuation-distribution-chart";
import { ValuationEvidenceSummary } from "./valuation-evidence-summary";
import { ValuationPriceRangeBand } from "./valuation-price-range-band";
import { ValuationTrendChart } from "./valuation-trend-chart";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function ValuationVisualPanel({ model }: { model: ValuationVisualModel }) {
  if (!model.actionable) return <VisualDataUnavailableState message="目前沒有足夠的官方可比成交資料可安全呈現估值圖表。" />;
  return <div className="min-w-0 space-y-4"><SectionCard title="估價視覺化與證據"><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label="估算總價" value={`${model.metrics.estimateTotal?.toLocaleString() ?? "尚無可用資料"} 萬`} /><MetricTile label="每坪估算單價" value={`${model.metrics.estimateUnit?.toLocaleString() ?? "尚無可用資料"} 萬`} /><MetricTile label="信心分數" value={model.metrics.confidence ?? "尚無可用資料"} /><MetricTile label="官方可比筆數" value={model.metrics.comparableCount ?? "尚無可用資料"} /></div></SectionCard><SectionCard title="估值區間"><ValuationPriceRangeBand model={model} /></SectionCard><SectionCard title="有效官方單價分布"><ValuationDistributionChart model={model} /></SectionCard><SectionCard title="官方成交趨勢"><ValuationTrendChart model={model} /></SectionCard><ValuationEvidenceSummary model={model} /></div>;
}
