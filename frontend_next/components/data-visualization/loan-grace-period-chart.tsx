import type { LoanVisualModel } from "@/lib/loan-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function LoanGracePeriodChart({ model }: { model: LoanVisualModel }) {
  if (!model.gracePeriod) return <VisualDataUnavailableState message="無法取得寬限期月付明細。" />;
  const values = [model.gracePeriod.graceMonthlyPayment, model.gracePeriod.postGraceMonthlyPayment, model.gracePeriod.baselineMonthlyPayment];
  const max = Math.max(...values);
  return <section aria-label="寬限期月付比較" className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <h3 className="text-sm font-bold text-slate-900">寬限期前後月付比較</h3>
    <svg viewBox="0 0 640 240" role="img" aria-label="寬限期內、寬限期後與基準月付比較" className="mt-3 h-auto w-full"><title>寬限期月付比較</title><desc>比較寬限期內、寬限期後與基準月付；寬限期內通常只繳利息，不代表總成本較低。</desc>{values.map((value, index) => { const height = (value / max) * 150; const x = 80 + index * 190; return <g key={value}><rect x={x} y={190 - height} width="80" height={height} className={index === 0 ? "fill-cyan-600" : index === 1 ? "fill-slate-700" : "fill-amber-600"} /><text x={x + 40} y="215" textAnchor="middle" className="fill-slate-700 text-[11px]">{["寬限期內", "寬限期後", "基準月付"][index]}</text><text x={x + 40} y={180 - height} textAnchor="middle" className="fill-slate-800 text-[11px]">{value.toLocaleString()} 元</text></g>; })}</svg>
    <p className="mt-2 text-xs text-amber-800">寬限期內通常只繳利息，不代表總成本較低。</p>
  </section>;
}
