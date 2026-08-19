"use client";

import { selectChartLabelIndexes, type ValuationVisualModel } from "@/lib/valuation-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function ValuationTrendChart({ model }: { model: ValuationVisualModel }) {
  const { copy } = useExperienceLocale();
  if (model.state !== "available") return <VisualDataUnavailableState message={copy("viz.valuationTrendUnavailable")} />;
  if (model.trend.length < 2) return <VisualDataUnavailableState message={copy("viz.valuationTrendInsufficient")} />;
  const min = Math.min(...model.trend.map((point) => point.p25));
  const max = Math.max(...model.trend.map((point) => point.p75));
  const range = max - min || 1;
  const x = (index: number) => 48 + (index * 544) / (model.trend.length - 1);
  const y = (value: number) => 220 - ((value - min) / range) * 170;
  const medianPoints = model.trend.map((point, index) => `${x(index)},${y(point.median)}`).join(" ");
  const labels = selectChartLabelIndexes(model.trend.length);
  return <div aria-label={copy("viz.valuationTrendNote")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <svg viewBox="0 0 640 270" role="img" aria-label={copy("viz.valuationTrendNote")} className="h-auto w-full"><title>{copy("valuation.trend")}</title><desc>{copy("viz.valuationTrendNote")}</desc><polyline points={model.trend.map((point, index) => `${x(index)},${y(point.p25)}`).join(" ")} fill="none" className="stroke-cyan-200" strokeWidth="2" /><polyline points={medianPoints} fill="none" className="stroke-cyan-700" strokeWidth="4" /><polyline points={model.trend.map((point, index) => `${x(index)},${y(point.p75)}`).join(" ")} fill="none" className="stroke-cyan-200" strokeWidth="2" />{labels.map((index) => <text key={`${model.trend[index].period}-${index}`} x={x(index)} y="250" textAnchor="middle" className="fill-slate-600 text-[11px]">{model.trend[index].period}</text>)}</svg>
    <p className="mt-2 text-xs text-slate-600">{copy("viz.valuationTrendNote")}</p>
  </div>;
}
