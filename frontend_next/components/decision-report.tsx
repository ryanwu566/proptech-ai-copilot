"use client";

import type { HoldingCostResult, LoanCalculationResult, LocationInsightResult, PropertySearchResult, TaxResult, TerrainRiskResult, ValuationResult } from "@/lib/api";
import { buildDecisionSummary } from "@/lib/decision-summary";
import type { RiskSummary } from "@/lib/risk-summary";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { ViewingDecisionPanel } from "@/components/viewing-decision-panel";
import { buildViewingDecision } from "@/lib/viewing-decision";
import { useExperienceLocale } from "@/components/experience-locale-provider";


export function DecisionReport({
  propertySearch, valuation, loan, holding, location, terrainRisk, riskSummary, taxOracleResult, onDecisionNext,
}: {
  propertySearch?: PropertySearchResult; valuation?: ValuationResult; loan?: LoanCalculationResult; holding?: HoldingCostResult; location?: LocationInsightResult; terrainRisk?: TerrainRiskResult; riskSummary?: RiskSummary; taxOracleResult?: TaxResult; onDecisionNext?: (targetId: string) => void;
}) {
  const { copy } = useExperienceLocale();
  if (!valuation) return <section id="decision-report" className="scroll-mt-20 rounded-xl border border-dashed border-stone-300 bg-white p-5 text-center"><h2 className="font-bold text-slate-900">{copy("tour.clientReport")}</h2><p className="mt-2 text-xs leading-5 text-slate-500">{copy("common.notStarted")}</p></section>;
  const summary = buildDecisionSummary(propertySearch, valuation, loan, holding, location);
  const viewingDecision = buildViewingDecision({ valuation, loan, holding, location, terrainRisk, riskSummary, taxOracleResult });
  const tone = summary.recommendation === "值得進一步看屋" ? "text-emerald-800 bg-emerald-50 border-emerald-200" : summary.recommendation === "暫不建議" ? "text-rose-800 bg-rose-50 border-rose-200" : "text-amber-800 bg-amber-50 border-amber-200";
  return <section id="decision-report" className="scroll-mt-20 rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">RULE-BASED DECISION SUMMARY</p><h2 className="mt-1 font-bold text-slate-950">{copy("tour.clientReport")}</h2></div><span className={`rounded-full border px-3 py-1 text-xs font-bold ${tone}`}>{summary.recommendation}</span></div>
    <div className="mt-4 grid gap-3 md:grid-cols-2"><SummaryList title={copy("valuation.basis")} items={summary.reasons} /><SummaryList title={copy("location.risk")} items={summary.risks} /></div>
    <p className="mt-3 text-xs font-bold text-slate-600">{copy("valuation.confidence")}: {summary.dataConfidence}</p>
    <div className="mt-4"><ViewingDecisionPanel decision={viewingDecision} onNext={onDecisionNext ?? ((targetId) => document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" }))} /></div>
    {riskSummary && <p className="mt-2 rounded-lg bg-stone-50 px-3 py-2 text-xs text-slate-600">{copy("location.risk")}: <strong>{riskSummary.overallLabel}</strong> · {copy("valuation.level")}: <strong>{riskSummary.priceReasonableness.label}</strong> · {copy("valuation.confidence")}: <strong>{riskSummary.overallScore ?? copy("common.noData")}</strong></p>}
    <p className="mt-2 rounded-lg bg-violet-50 px-3 py-2 text-xs text-violet-800">{copy("tax.title")}: <strong>{taxOracleResult ? `${taxOracleResult.signal_color} · ${taxOracleResult.eligibility_status}` : copy("common.notStarted")}</strong></p>
    <div className="mt-4"><DetailDisclosure title={copy("case.status")}><div className="max-w-full overflow-x-auto"><table className="w-full min-w-[640px] text-left text-xs"><thead><tr className="bg-stone-50"><th className="p-2">{copy("case.status")}</th><th>{copy("common.updated")}</th><th>{copy("common.dataLimit")}</th></tr></thead><tbody>{summary.checklist.map((item) => <tr key={item.label} className="border-t border-stone-100"><td className="p-2 font-bold">{item.label}</td><td>{item.status}</td><td className="text-slate-500">{item.detail}</td></tr>)}</tbody></table></div></DetailDisclosure></div>
  </section>;
}
function SummaryList({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-lg bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">{title}</p><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}
