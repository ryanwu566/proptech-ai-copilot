import type { HoldingCostVisualModel } from "@/lib/holding-cost-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function HoldingCostBreakdownChart({ model }: { model: HoldingCostVisualModel }) {
  if (!model.breakdown.length) return <VisualDataUnavailableState message="目前沒有足夠的成本組成資料可呈現。" />;
  const max = Math.max(...model.breakdown.map((item) => item.monthlyAmount), 1);
  return <section aria-label="每月持有成本組成" className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4"><h3 className="text-sm font-bold text-slate-900">每月成本組成</h3><svg viewBox={`0 0 640 ${Math.max(220, model.breakdown.length * 42 + 50)}`} role="img" aria-label="每月持有成本組成圖" className="mt-3 h-auto w-full"><title>每月成本組成</title><desc>依 API 回傳順序顯示每月成本項目、金額與占總成本比例。</desc>{model.breakdown.map((item, index) => { const y = 35 + index * 42; const width = (item.monthlyAmount / max) * 380; return <g key={item.key}><text x="0" y={y + 5} className="fill-slate-700 text-[11px]">{item.label}</text><rect x="170" y={y - 10} width={width} height="20" rx="10" className="fill-cyan-600" /><text x={180 + width} y={y + 5} className="fill-slate-700 text-[11px]">{item.monthlyAmount.toLocaleString()} 元 · {item.percentage === null ? "無法計算占比" : `${item.percentage.toFixed(1)}%`}</text></g>; })}</svg>{model.omittedBreakdownCount > 0 && <p className="mt-2 text-xs text-slate-600">另有 {model.omittedBreakdownCount} 項可在完整明細查看。</p>}<p className="mt-2 text-xs text-slate-600">不以圖表順序暗示成本重要性；完整項目仍可展開查看。</p></section>;
}
