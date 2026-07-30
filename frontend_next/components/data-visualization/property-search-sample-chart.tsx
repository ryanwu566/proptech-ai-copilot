import type { PropertyRangePoint } from "@/lib/property-search-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function PropertySearchSampleChart({ data }: { data: PropertyRangePoint[] }) {
  if (!data.length) return <VisualDataUnavailableState message="目前沒有足夠的找房樣本資料可呈現。" />;
  const max = Math.max(...data.map((item) => item.sampleCount));
  return <section aria-label="找房樣本量圖" className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4"><h3 className="text-sm font-bold text-slate-900">推薦區域樣本量</h3><svg viewBox="0 0 640 240" role="img" aria-label="推薦區域樣本量柱狀圖" className="mt-3 h-auto w-full"><title>推薦區域樣本量</title><desc>顯示各推薦區域的可用成交樣本數。</desc>{data.slice(0, 6).map((item, index) => { const x = 48 + index * 96; const height = (item.sampleCount / max) * 150; return <g key={item.label}><rect x={x} y={190 - height} width="56" height={height} className="fill-cyan-600" /><text x={x + 28} y="212" textAnchor="middle" className="fill-slate-600 text-[10px]">{item.sampleCount}</text><text x={x + 28} y={185 - height} textAnchor="middle" className="fill-slate-700 text-[9px]">{item.label.slice(-4)}</text></g>; })}</svg><p className="mt-2 text-xs text-slate-600">樣本量是歷史成交資料量，不代表待售物件數量。</p></section>;
}
