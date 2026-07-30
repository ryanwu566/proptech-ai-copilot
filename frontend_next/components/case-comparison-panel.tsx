"use client";

import type { SavedCase } from "@/lib/case-storage";
import { buildCaseComparisonHtml, compareSavedCases } from "@/lib/case-comparison";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { PropertyComparisonReport } from "@/components/property-comparison-report";
import { useExperienceLocale } from "@/components/experience-locale-provider";



export function CaseComparisonPanel({ savedCases, selectedIds }: { savedCases: SavedCase[]; selectedIds: string[] }) {
  const { copy } = useExperienceLocale();
  const selected = savedCases.filter((item) => selectedIds.includes(item.id)).slice(0, 3);
  const result = compareSavedCases(selected);
  const detailRows = getDetailRows(copy);
  function exportHtml() {
    const url = URL.createObjectURL(new Blob([buildCaseComparisonHtml(result)], { type: "text/html;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `property-comparison-${new Date().toISOString().slice(0, 10)}.html`; link.click(); URL.revokeObjectURL(url);
  }
  if (selected.length < 2) return <div className="mt-4 rounded-xl border border-dashed border-cyan-200 bg-cyan-50 p-4 text-xs text-cyan-900">{copy("case.compareCount", { selected: selected.length })}</div>;
  return <section className="mt-4 min-w-0 space-y-4 rounded-xl border border-cyan-200 bg-cyan-50/40 p-4" aria-label={copy("case.compare")}>
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="font-bold text-slate-950">{copy("case.compare")}</h3><p className="mt-1 text-xs text-slate-600">{result.summary}</p></div><button type="button" onClick={exportHtml} className="rounded-lg bg-cyan-700 px-4 py-2 text-xs font-bold text-white">{copy("case.export")}</button></div>
    <PropertyComparisonReport result={result} />
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{result.ranking.map((row) => { const item = result.cases.find((candidate) => candidate.caseId === row.caseId); return <article key={row.caseId} className="rounded-xl border border-stone-200 bg-white p-3"><p className="text-[10px] font-bold text-cyan-700">#{row.rank} · {row.label}</p><h4 className="mt-1 truncate text-sm font-bold text-slate-900">{item?.title}</h4><p className="mt-2 text-2xl font-extrabold text-slate-950">{row.score ?? "—"}</p><ul className="mt-2 space-y-1 text-[10px] text-emerald-700">{row.reasons.map((reason) => <li key={reason}>+ {reason}</li>)}</ul><ul className="mt-2 space-y-1 text-[10px] text-amber-700">{row.warnings.map((warning) => <li key={warning}>! {warning}</li>)}</ul></article>; })}</div>
    <DetailDisclosure title={copy("case.compare")}><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[980px] text-left text-[10px]"><thead><tr className="bg-white"><th className="p-2">{copy("case.title")}</th><th>{copy("valuation.totalPrice")}</th><th>{copy("valuation.title")}</th><th>{copy("loan.title")}</th><th>{copy("case.status")}</th><th>{copy("location.title")}</th><th>{copy("location.risk")}</th><th>{copy("location.risk")}</th><th>{copy("tax.title")}</th><th>{copy("case.status")}</th></tr></thead><tbody>{result.cases.map((item) => <tr key={item.caseId} className="border-t border-cyan-100 bg-white/80"><td className="p-2 font-bold">{item.title}</td><td>{formatWan(item.propertyPrice)}</td><td>{formatWan(item.valuationMid)}</td><td>{formatYuan(item.monthlyPayment)}</td><td>{formatYuan(item.monthlyHoldingCost)}</td><td>{item.locationScore ?? copy("common.noData")}</td><td>{item.terrainRiskLevel}</td><td>{item.riskSignal} / {item.riskScore ?? "—"}</td><td>{item.taxStatus}</td><td>{item.completionRate}%</td></tr>)}</tbody></table></div></DetailDisclosure>
    <details className="rounded-xl border border-stone-200 bg-white"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-slate-800">{copy("valuation.comparables")}</summary><div className="max-w-full touch-pan-x overflow-x-auto border-t border-stone-200"><table className="w-full min-w-[920px] text-left text-[10px]"><thead><tr className="bg-stone-50"><th className="p-2">{copy("case.status")}</th>{result.cases.map((item)=><th key={item.caseId}>{item.title}</th>)}</tr></thead><tbody>{detailRows.map(([label,render])=><tr key={label} className="border-t border-stone-100"><th className="p-2">{label}</th>{result.cases.map((item)=><td key={item.caseId}>{render(item)}</td>)}</tr>)}</tbody></table></div></details>
    {result.missingDataWarnings.length > 0 && <details className="rounded-xl border border-amber-200 bg-amber-50"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-amber-900">{copy("case.missing", { items: result.missingDataWarnings.length })}</summary><ul className="border-t border-amber-200 p-3 text-[11px] leading-5 text-amber-800">{result.missingDataWarnings.map((item) => <li key={item}>{item}</li>)}</ul></details>}
    <p className="text-[10px] leading-5 text-slate-500">{copy("common.dataLimit")}</p>
  </section>;
}

function formatWan(value: number | null) { return value === null ? "—" : value.toLocaleString(); }
function formatYuan(value: number | null) { return value === null ? "—" : value.toLocaleString(); }
function formatRatio(value: number | null) { return value === null ? "—" : `${(value * 100).toFixed(1)}%`; }
function getDetailRows(copy: (key: import("@/lib/runtime-copy").RuntimeCopyKey) => string): Array<[string, (item: ReturnType<typeof compareSavedCases>["cases"][number]) => string | number]> {
  return [[copy("location.title"), (item) => item.location], [copy("location.area"), (item) => `${item.areaPing ?? copy("common.noData")} / ${item.buildingType}`], [copy("valuation.range"), (item) => `${item.valuationRange} / ${item.valuationConfidence ?? copy("common.noData")}`], [copy("valuation.level"), (item) => item.priceReasonableness], [copy("loan.downPayment"), (item) => formatWan(item.downPaymentWan)], [copy("loan.rate"), (item) => formatRatio(item.loanBurdenRatio)], [copy("case.status"), (item) => formatRatio(item.holdingBurdenRatio)], [copy("location.transit"), (item) => `${item.transitScore ?? "—"} / ${item.convenienceScore ?? "—"} / ${item.educationScore ?? "—"} / ${item.medicalScore ?? "—"}`], [copy("location.dataQuality"), (item) => item.locationRiskGap], [copy("location.risk"), (item) => `${item.terrainRiskLevel} / ${item.terrainRiskStatus}`], [copy("location.weaknesses"), (item) => item.mainRisks.join(" / ") || copy("common.noData")], [copy("location.strengths"), (item) => item.positives.join(" / ") || copy("common.noData")], [copy("tax.title"), (item) => `${item.taxStatus} / ${item.taxSignal} / ${item.taxRiskScore ?? "—"}`]];
}
