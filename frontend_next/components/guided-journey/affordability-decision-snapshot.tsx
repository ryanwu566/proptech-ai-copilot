import type { JourneyAffordabilityContext } from "@/lib/price-affordability-journey";
import { buildAffordabilityDecisionSnapshot } from "@/lib/price-affordability-journey";

export function AffordabilityDecisionSnapshot({ context }: { context: JourneyAffordabilityContext }) {
  const snapshot = buildAffordabilityDecisionSnapshot(context);
  return <section aria-labelledby="affordability-snapshot-heading" className="rounded-xl border border-violet-100 bg-violet-50/50 p-4">
    <h3 id="affordability-snapshot-heading" className="text-base font-black text-slate-950">{snapshot.title}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{snapshot.description}</p>
    <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{[
      ["房屋價格", snapshot.propertyPriceWan === undefined ? "未提供" : `${snapshot.propertyPriceWan} 萬`],
      ["頭期款", snapshot.downPaymentWan === undefined ? "尚未試算" : `${snapshot.downPaymentWan} 萬`],
      ["貸款金額", snapshot.loanAmountWan === undefined ? "尚未試算" : `${snapshot.loanAmountWan} 萬`],
      ["每月月付", snapshot.monthlyPayment === undefined ? "尚未試算" : `${snapshot.monthlyPayment} 元`],
      ["每月持有成本", snapshot.monthlyHoldingCost === undefined ? "尚未試算" : `${snapshot.monthlyHoldingCost} 元`],
      ["收入負擔狀態", snapshot.incomeBurdenRatio === undefined ? "未輸入收入，尚未評估" : "已取得試算資料"],
      ["TaxOracle", snapshot.taxOracleStatus],
      ["資料待補", snapshot.missingDataLabels.length ? snapshot.missingDataLabels.join("、") : "目前沒有列出的待補項目"],
    ].map(([label, value]) => <SnapshotField key={label} label={label} value={value} />)}</dl>
  </section>;
}

function SnapshotField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-violet-100 bg-white p-3"><dt className="text-[10px] font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold text-slate-900">{value}</dd></div>;
}
