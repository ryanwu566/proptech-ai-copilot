"use client";

import type { ValuationVisualModel } from "@/lib/valuation-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function ValuationPriceRangeBand({ model }: { model: ValuationVisualModel }) {
  const { copy } = useExperienceLocale();
  if (model.state !== "available" || !model.priceRange) return <VisualDataUnavailableState message={copy("viz.valuationRangeUnavailable")} />;
  const { low, mid, high } = model.priceRange;
  const width = high - low || 1;
  const marker = Math.max(0, Math.min(100, ((mid - low) / width) * 100));
  return <div aria-label={copy("viz.valuationRangeNote")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <svg viewBox="0 0 640 180" role="img" aria-label={copy("viz.valuationRangeNote")} className="h-auto w-full"><title>{copy("valuation.range")}</title><desc>{copy("viz.valuationRangeNote")}</desc><line x1="70" y1="82" x2="570" y2="82" className="stroke-cyan-100" strokeWidth="24" strokeLinecap="round" /><line x1="70" y1="82" x2="570" y2="82" className="stroke-cyan-600" strokeWidth="8" strokeLinecap="round" /><line x1={70 + marker * 5} y1="50" x2={70 + marker * 5} y2="114" className="stroke-slate-950" strokeWidth="4" /><text x="70" y="145" textAnchor="middle" className="fill-slate-700 text-[13px]">P25 {low.toLocaleString()}</text><text x={70 + marker * 5} y="35" textAnchor="middle" className="fill-slate-950 text-[13px]">{copy("valuation.mid")} {mid.toLocaleString()}</text><text x="570" y="145" textAnchor="middle" className="fill-slate-700 text-[13px]">P75 {high.toLocaleString()}</text></svg>
    <p className="mt-2 text-xs text-slate-600">{copy("viz.valuationRangeNote")}</p>
  </div>;
}
