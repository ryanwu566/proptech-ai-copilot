import type { HoldingCostVisualModel } from "@/lib/holding-cost-visualization";
import type { LoanVisualModel } from "@/lib/loan-visualization";

type Affordability = LoanVisualModel["affordability"] | HoldingCostVisualModel["affordability"];

export function AffordabilityStatus({ value }: { value: Affordability }) {
  return <section role="status" aria-label={`收入負擔狀態：${value.label}`} className="rounded-xl border border-amber-200 bg-amber-50 p-3">
    <p className="text-xs font-bold text-amber-900">收入負擔狀態：{value.label}</p>
    <p className="mt-1 text-xs leading-5 text-amber-800">{value.message}</p>
  </section>;
}
