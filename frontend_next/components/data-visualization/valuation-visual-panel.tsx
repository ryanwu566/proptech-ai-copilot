import type { ValuationVisualModel } from "@/lib/valuation-visualization";
import { MetricTile, SectionCard } from "@/components/product-ui";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getLocalizedStateLabel } from "@/lib/structured-options";
import { ValuationDistributionChart } from "./valuation-distribution-chart";
import { ValuationEvidenceSummary } from "./valuation-evidence-summary";
import { ValuationPriceRangeBand } from "./valuation-price-range-band";
import { ValuationTrendChart } from "./valuation-trend-chart";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function ValuationVisualPanel({ model }: { model: ValuationVisualModel }) {
  const { copy, locale } = useExperienceLocale();
  // Missing data must never be rendered as zero or low risk: 不以零值或低風險代替缺失資料。
  if (!model.actionable) {
    return <div data-testid="valuation-result"><VisualDataUnavailableState message={copy("valuation.emptyDetail")} state={model.state === "no_data" || model.state === "demo" ? "no_official_data" : "unavailable"} /></div>;
  }
  return <div data-testid="valuation-result" className="min-w-0 space-y-4">
    <div className="flex flex-wrap items-center gap-2 text-xs"><span className="rounded-full bg-cyan-50 px-2 py-1 font-bold text-cyan-800">{getLocalizedStateLabel("source_backed", locale)}</span><span className="text-slate-500">{copy("valuation.help")}</span></div>
    <ValuationEvidenceSummary model={model} />
    <details className="min-w-0 rounded-xl border border-stone-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-inset">{copy("valuation.comparables")}</summary>
      <div className="min-w-0 space-y-4 border-t border-stone-100 p-4">
        <SectionCard title={copy("valuation.basis")}><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label={copy("valuation.estimateTotal")} value={model.metrics.estimateTotal?.toLocaleString() ?? copy("common.noData")} /><MetricTile label={copy("valuation.unitPrice")} value={model.metrics.estimateUnit?.toLocaleString() ?? copy("common.noData")} /><MetricTile label={copy("valuation.confidence")} value={model.metrics.confidence ?? copy("common.noData")} /><MetricTile label={copy("valuation.usedRecords")} value={model.metrics.comparableCount ?? copy("common.noData")} /></div></SectionCard>
        <SectionCard title={copy("valuation.range")}><ValuationPriceRangeBand model={model} /></SectionCard>
        <SectionCard title={copy("valuation.comparables")}><ValuationDistributionChart model={model} /></SectionCard>
        <SectionCard title={copy("valuation.trend")}><ValuationTrendChart model={model} /></SectionCard>
      </div>
    </details>
  </div>;
}
