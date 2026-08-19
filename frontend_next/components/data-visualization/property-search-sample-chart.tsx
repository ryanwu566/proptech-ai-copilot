"use client";

import type { PropertyRangePoint } from "@/lib/property-search-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PropertySearchSampleChart({ data }: { data: PropertyRangePoint[] }) {
  const { copy } = useExperienceLocale();
  if (!data.length) return <VisualDataUnavailableState message={copy("viz.searchSampleUnavailable")} />;
  const max = Math.max(...data.map((item) => item.sampleCount));
  return <section aria-label={copy("viz.searchSampleTitle")} className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4"><h3 className="text-sm font-bold text-slate-900">{copy("viz.searchSampleTitle")}</h3><svg viewBox="0 0 640 240" role="img" aria-label={copy("viz.searchSampleSvgLabel")} className="mt-3 h-auto w-full"><title>{copy("viz.searchSampleTitle")}</title><desc>{copy("viz.searchSampleDesc")}</desc>{data.slice(0, 6).map((item, index) => { const x = 48 + index * 96; const height = (item.sampleCount / max) * 150; return <g key={item.label}><rect x={x} y={190 - height} width="56" height={height} className="fill-cyan-600" /><text x={x + 28} y="212" textAnchor="middle" className="fill-slate-600 text-[10px]">{item.sampleCount}</text><text x={x + 28} y={185 - height} textAnchor="middle" className="fill-slate-700 text-[9px]">{item.label.slice(-4)}</text></g>; })}</svg><p className="mt-2 text-xs text-slate-600">{copy("viz.searchSampleNote")}</p></section>;
}
