"use client";

import type { ValuationVisualModel } from "@/lib/valuation-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function ValuationDistributionChart({ model }: { model: ValuationVisualModel }) {
  const { copy } = useExperienceLocale();
  if (model.state !== "available" || !model.distribution) return <VisualDataUnavailableState message={copy("viz.valuationDistUnavailable")} />;
  const { p25, median, p75, estimate } = model.distribution;
  const max = Math.max(p75, estimate);
  const scale = (value: number) => 70 + (value / max) * 500;
  return <div aria-label={copy("viz.valuationDistNote")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <svg viewBox="0 0 640 220" role="img" aria-label={copy("viz.valuationDistNote")} className="h-auto w-full"><title>{copy("valuation.unitPrice")}</title><desc>{copy("viz.valuationDistNote")}</desc><line x1={scale(p25)} y1="90" x2={scale(p75)} y2="90" className="stroke-cyan-200" strokeWidth="28" strokeLinecap="round" /><circle cx={scale(p25)} cy="90" r="8" className="fill-cyan-700" /><circle cx={scale(median)} cy="90" r="10" className="fill-slate-950" /><circle cx={scale(p75)} cy="90" r="8" className="fill-cyan-700" /><line x1={scale(estimate)} y1="45" x2={scale(estimate)} y2="135" className="stroke-amber-600" strokeWidth="4" /><text x={scale(p25)} y="170" textAnchor="middle" className="fill-slate-700 text-[12px]">P25</text><text x={scale(median)} y="190" textAnchor="middle" className="fill-slate-950 text-[12px]">{copy("valuation.mid")}</text><text x={scale(p75)} y="170" textAnchor="middle" className="fill-slate-700 text-[12px]">P75</text><text x={scale(estimate)} y="35" textAnchor="middle" className="fill-amber-700 text-[12px]">{copy("valuation.estimate")}</text></svg>
    <p className="mt-2 text-xs text-slate-600">{copy("viz.valuationDistNote")}</p>
  </div>;
}
