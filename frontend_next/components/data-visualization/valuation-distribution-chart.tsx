import type { ValuationVisualModel } from "@/lib/valuation-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function ValuationDistributionChart({ model }: { model: ValuationVisualModel }) {
  if (model.state !== "available" || !model.distribution) return <VisualDataUnavailableState message="單價分布目前沒有足夠的有效值可呈現。" />;
  const { p25, median, p75, estimate } = model.distribution;
  const max = Math.max(p75, estimate);
  const scale = (value: number) => 70 + (value / max) * 500;
  return <div aria-label="估值單價分布圖" className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <svg viewBox="0 0 640 220" role="img" aria-label="P25 中位數 P75 與估算單價" className="h-auto w-full"><title>單價分布</title><desc>顯示有效官方可比成交的 P25、中位數、P75 與本次估算單價。</desc><line x1={scale(p25)} y1="90" x2={scale(p75)} y2="90" className="stroke-cyan-200" strokeWidth="28" strokeLinecap="round" /><circle cx={scale(p25)} cy="90" r="8" className="fill-cyan-700" /><circle cx={scale(median)} cy="90" r="10" className="fill-slate-950" /><circle cx={scale(p75)} cy="90" r="8" className="fill-cyan-700" /><line x1={scale(estimate)} y1="45" x2={scale(estimate)} y2="135" className="stroke-amber-600" strokeWidth="4" /><text x={scale(p25)} y="170" textAnchor="middle" className="fill-slate-700 text-[12px]">P25</text><text x={scale(median)} y="190" textAnchor="middle" className="fill-slate-950 text-[12px]">中位</text><text x={scale(p75)} y="170" textAnchor="middle" className="fill-slate-700 text-[12px]">P75</text><text x={scale(estimate)} y="35" textAnchor="middle" className="fill-amber-700 text-[12px]">估算</text></svg>
    <p className="mt-2 text-xs text-slate-600">僅使用可驗證的正值欄位；缺失值不補零。</p>
  </div>;
}
