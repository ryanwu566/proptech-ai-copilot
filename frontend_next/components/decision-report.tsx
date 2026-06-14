"use client";

import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, ValuationResult } from "@/lib/api";
import { buildDecisionSummary } from "@/lib/decision-summary";
import type { RiskSummary } from "@/lib/risk-summary";

export function DecisionReport({
  propertySearch, valuation, loan, holding, location, riskSummary, taxOracleResult,
}: {
  propertySearch?: PropertySearchResult; valuation?: ValuationResult; loan?: LoanCalculationResult; holding?: HoldingCostResult; location?: LocationInsightResult; riskSummary?: RiskSummary; taxOracleResult?: TaxResult;
}) {
  const summary = buildDecisionSummary(propertySearch, valuation, loan, holding, location);
  const tone = summary.recommendation === "值得進一步看屋" ? "text-emerald-800 bg-emerald-50 border-emerald-200" : summary.recommendation === "暫不建議" ? "text-rose-800 bg-rose-50 border-rose-200" : "text-amber-800 bg-amber-50 border-amber-200";
  return <section id="decision-report" className="scroll-mt-20 rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">RULE-BASED DECISION SUMMARY</p><h2 className="mt-1 font-bold text-slate-950">看屋決策摘要</h2></div><span className={`rounded-full border px-3 py-1 text-xs font-bold ${tone}`}>{summary.recommendation}</span></div>
    <div className="mt-4 grid gap-3 md:grid-cols-2"><SummaryList title="主要理由" items={summary.reasons} /><SummaryList title="主要風險" items={summary.risks} /></div>
    <p className="mt-3 text-xs font-bold text-slate-600">資料信心：{summary.dataConfidence}</p>
    {riskSummary && <p className="mt-2 rounded-lg bg-stone-50 px-3 py-2 text-xs text-slate-600">風險總評：<strong>{riskSummary.overallLabel}</strong> · 開價合理性：<strong>{riskSummary.priceReasonableness.label}</strong> · 總分：<strong>{riskSummary.overallScore ?? "資料不足"}</strong></p>}
    <p className="mt-2 rounded-lg bg-violet-50 px-3 py-2 text-xs text-violet-800">TaxOracle 稅務快篩：<strong>{taxOracleResult ? `${taxOracleResult.signal_color} · ${taxOracleResult.eligibility_status}` : "尚未完成"}</strong></p>
    <div className="mt-4 max-w-full overflow-x-auto"><table className="w-full min-w-[640px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">決策 checklist</th><th>狀態</th><th>提醒</th></tr></thead><tbody>{summary.checklist.map((item) => <tr key={item.label} className="border-t border-stone-100"><td className="p-2 font-bold">{item.label}</td><td>{item.status}</td><td className="text-slate-500">{item.detail}</td></tr>)}</tbody></table></div>
  </section>;
}

function SummaryList({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-lg bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}
