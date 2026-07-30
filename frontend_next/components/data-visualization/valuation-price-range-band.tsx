import type { ValuationVisualModel } from "@/lib/valuation-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function ValuationPriceRangeBand({ model }: { model: ValuationVisualModel }) {
  if (model.state !== "available" || !model.priceRange) return <VisualDataUnavailableState message="估值區間目前無法安全呈現，請先確認官方可比成交資料。" />;
  const { low, mid, high } = model.priceRange;
  const width = high - low || 1;
  const marker = Math.max(0, Math.min(100, ((mid - low) / width) * 100));
  return <div aria-label="估值價格區間圖" className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <svg viewBox="0 0 640 180" role="img" aria-label="估值低中高價格區間" className="h-auto w-full"><title>估值區間</title><desc>顯示官方可比成交支持的低、中、高估值區間。</desc><line x1="70" y1="82" x2="570" y2="82" className="stroke-cyan-100" strokeWidth="24" strokeLinecap="round" /><line x1="70" y1="82" x2="570" y2="82" className="stroke-cyan-600" strokeWidth="8" strokeLinecap="round" /><line x1={70 + marker * 5} y1="50" x2={70 + marker * 5} y2="114" className="stroke-slate-950" strokeWidth="4" /><text x="70" y="145" textAnchor="middle" className="fill-slate-700 text-[13px]">P25 {low.toLocaleString()} 萬</text><text x={70 + marker * 5} y="35" textAnchor="middle" className="fill-slate-950 text-[13px]">中位 {mid.toLocaleString()} 萬</text><text x="570" y="145" textAnchor="middle" className="fill-slate-700 text-[13px]">P75 {high.toLocaleString()} 萬</text></svg>
    <p className="mt-2 text-xs text-slate-600">區間是估值參考，不是保證成交價或購買建議。</p>
  </div>;
}
