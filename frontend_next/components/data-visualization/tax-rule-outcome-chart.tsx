import type { TaxVisualModel } from "@/lib/tax-visualization";
import { VisualDataUnavailableState } from "./visual-data-unavailable-state";

export function TaxRuleOutcomeChart({ model }: { model: TaxVisualModel }) {
  if (!model.outcomes.length) return <VisualDataUnavailableState message="目前沒有可呈現的規則結果分布。" />;
  const max = Math.max(...model.outcomes.map((item) => item.count), 1);
  return <section aria-label="稅務規則結果分布" className="min-h-[320px] max-w-full overflow-hidden rounded-xl border border-stone-200 bg-white p-4"><h3 className="text-sm font-bold text-slate-900">規則結果分布</h3><div role="img" aria-label="TaxOracle 規則結果分布圖" className="mt-3 grid gap-3">{model.outcomes.map((item) => <div key={item.key}><div className="flex items-center justify-between gap-3 text-xs"><span className="font-bold text-slate-700">{item.label}</span><strong>{item.count} 條</strong></div><div className="mt-1 h-4 rounded-full bg-stone-100"><div className="h-4 rounded-full bg-cyan-700" style={{ width: `${(item.count / max) * 100}%` }} /></div></div>)}</div><p className="mt-3 text-xs text-slate-600">數量直接來自既有 rule_traces outcome；未辨識值不會被當成通過。</p></section>;
}
