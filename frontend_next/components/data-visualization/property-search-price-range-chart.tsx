import type { PropertyRangePoint } from "@/lib/property-search-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function PropertySearchPriceRangeChart({ title, data }: { title: string; data: PropertyRangePoint[] }) {
  if (!data.length) return <VisualDataUnavailableState message="目前沒有足夠的價格區間資料可呈現。" />;
  const max = Math.max(...data.map((item) => item.high));
  return <section aria-label={title} className="min-h-[320px] max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4"><h3 className="text-sm font-bold text-slate-900">{title}</h3><svg viewBox={`0 0 640 ${Math.max(220, data.length * 42 + 50)}`} role="img" aria-label={title} className="mt-3 h-auto w-full"><title>{title}</title><desc>顯示依行政區或路段彙整的 P25、中位總價與 P75 區間。</desc>{data.slice(0, 6).map((item, index) => { const y = 35 + index * 42; const scale = (value: number) => 160 + (value / max) * 400; return <g key={item.label}><text x="0" y={y + 5} className="fill-slate-700 text-[11px]">{item.label}</text><line x1={scale(item.low)} y1={y} x2={scale(item.high)} y2={y} className="stroke-cyan-200" strokeWidth="12" strokeLinecap="round" /><circle cx={scale(item.median)} cy={y} r="7" className="fill-slate-950" /><text x={scale(item.high) + 8} y={y + 5} className="fill-slate-500 text-[10px]">{item.sampleCount} 筆</text></g>; })}</svg><p className="mt-2 text-xs text-slate-600">區間只呈現有完整 P25 / 中位 / P75 的彙整資料。</p></section>;
}
