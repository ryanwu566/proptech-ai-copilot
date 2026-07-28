import type { LoanVisualModel } from "@/lib/loan-visualization";
import { Button, Notice } from "@/components/ui";
import { MetricTile, SectionCard } from "@/components/product-ui";
import { AffordabilityStatus } from "./affordability-status";
import { CalculationEvidenceDetails } from "./calculation-evidence-details";
import { LoanFinancingStructureChart } from "./loan-financing-structure-chart";
import { LoanGracePeriodChart } from "./loan-grace-period-chart";
import { LoanSensitivityChart } from "./loan-sensitivity-chart";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function LoanVisualPanel({ model, onHoldingCost }: { model: LoanVisualModel; onHoldingCost?: () => void }) {
  if (model.state !== "available") return <VisualDataUnavailableState message={model.summary} />;
  return <div className="min-w-0 space-y-4"><SectionCard title="貸款試算摘要"><p className="text-sm leading-6 text-slate-700">{model.summary}</p><p className="mt-2 text-xs text-amber-800">貸款試算是現金流參考，不代表銀行核貸、保證負擔得起或任何銀行建議。</p><div className="mt-3"><AffordabilityStatus value={model.affordability} /></div></SectionCard><div className="grid gap-3 sm:grid-cols-2"><MetricTile label="頭期款" value={`${model.metrics.downPayment?.toLocaleString()} 萬`} /><MetricTile label="貸款金額" value={`${model.metrics.loanAmount?.toLocaleString()} 萬`} /><MetricTile label="每月月付" value={`${model.metrics.monthlyPayment?.toLocaleString()} 元`} /><MetricTile label="總利息" value={`${model.metrics.totalInterest?.toLocaleString()} 元`} /></div><LoanFinancingStructureChart model={model} /><LoanSensitivityChart model={model} />{model.gracePeriodRequested ? <LoanGracePeriodChart model={model} /> : null}<CalculationEvidenceDetails model={model}/><Notice tone="warning">缺少收入或回傳資料不足時，相關負擔率與圖表會維持未評估，不補成 0。</Notice>{onHoldingCost && <Button secondary className="w-full sm:w-auto" onClick={onHoldingCost}>帶入持有成本</Button>}</div>;
}
