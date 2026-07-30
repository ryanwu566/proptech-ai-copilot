import type { LoanVisualModel } from "@/lib/loan-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function LoanFinancingStructureChart({ model }: { model: LoanVisualModel }) {
  if (!model.structure) return <VisualDataUnavailableState message="頭期款與貸款金額不一致，暫不繪製資金結構圖。" />;
  const { propertyPrice, downPayment, loanAmount, downPaymentRatio, loanRatio } = model.structure;
  return <section aria-label="頭期款與貸款結構" className=" max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4">
    <h3 className="text-sm font-bold text-slate-900">頭期款／貸款結構</h3>
    <svg viewBox="0 0 640 190" role="img" aria-label="頭期款與貸款占比圖" className="mt-3 h-auto w-full"><title>頭期款與貸款結構</title><desc>顯示頭期款與貸款金額及各自在房屋總價中的比例。</desc><rect x="40" y="62" width={520} height="34" rx="17" className="fill-cyan-100" /><rect x="40" y="62" width={520 * downPaymentRatio} height="34" rx="17" className="fill-cyan-700" /><rect x={40 + 520 * downPaymentRatio} y="62" width={520 * loanRatio} height="34" className="fill-slate-700" /><text x="40" y="130" className="fill-slate-700 text-[13px]">頭期款 {downPayment.toLocaleString()} 萬（{(downPaymentRatio * 100).toFixed(1)}%）</text><text x="40" y="158" className="fill-slate-700 text-[13px]">貸款 {loanAmount.toLocaleString()} 萬（{(loanRatio * 100).toFixed(1)}%）</text><text x="560" y="130" textAnchor="end" className="fill-slate-500 text-[12px]">總價 {propertyPrice.toLocaleString()} 萬</text></svg>
    <p className="mt-2 text-xs text-slate-600">金額與比例依本次試算輸入；這是資金結構參考，不是核貸結果。</p>
  </section>;
}
