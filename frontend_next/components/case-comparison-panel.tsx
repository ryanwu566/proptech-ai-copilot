"use client";

import type { SavedCase } from "@/lib/case-storage";
import { buildCaseComparisonHtml, compareSavedCases } from "@/lib/case-comparison";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { PropertyComparisonReport } from "@/components/property-comparison-report";

export function CaseComparisonPanel({ savedCases, selectedIds }: { savedCases: SavedCase[]; selectedIds: string[] }) {
  const selected = savedCases.filter((item) => selectedIds.includes(item.id)).slice(0, 3);
  const result = compareSavedCases(selected);
  function exportHtml() {
    const url = URL.createObjectURL(new Blob([buildCaseComparisonHtml(result)], { type: "text/html;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `案件比較摘要-${new Date().toISOString().slice(0, 10)}.html`; link.click(); URL.revokeObjectURL(url);
  }
  if (selected.length < 2) return <div className="mt-4 rounded-xl border border-dashed border-cyan-200 bg-cyan-50 p-4 text-xs text-cyan-900">請至少選擇兩個案件，最多可比較三個案件。</div>;
  return <section className="mt-4 min-w-0 space-y-4 rounded-xl border border-cyan-200 bg-cyan-50/40 p-4" aria-label="案件比較與候選排序">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="font-bold text-slate-950">案件比較 / 候選排序</h3><p className="mt-1 text-xs text-slate-600">{result.summary}</p></div><button type="button" onClick={exportHtml} className="rounded-lg bg-cyan-700 px-4 py-2 text-xs font-bold text-white">匯出比較摘要 HTML</button></div>
    <PropertyComparisonReport result={result} />
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{result.ranking.map((row) => { const item = result.cases.find((candidate) => candidate.caseId === row.caseId); return <article key={row.caseId} className="rounded-xl border border-stone-200 bg-white p-3"><p className="text-[10px] font-bold text-cyan-700">第 {row.rank} 名 · {row.label}</p><h4 className="mt-1 truncate text-sm font-bold text-slate-900">{item?.title}</h4><p className="mt-2 text-2xl font-extrabold text-slate-950">{row.score ?? "—"}<span className="text-xs text-slate-400"> 分</span></p><ul className="mt-2 space-y-1 text-[10px] text-emerald-700">{row.reasons.map((reason) => <li key={reason}>＋ {reason}</li>)}</ul><ul className="mt-2 space-y-1 text-[10px] text-amber-700">{row.warnings.map((warning) => <li key={warning}>！ {warning}</li>)}</ul></article>; })}</div>
    <DetailDisclosure title="查看案件比較完整表"><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[980px] text-left text-[10px]"><thead><tr className="bg-white"><th className="p-2">案件</th><th>總價</th><th>估價</th><th>月付</th><th>持有成本</th><th>區位</th><th>地勢風險</th><th>風險</th><th>稅務</th><th>完成度</th></tr></thead><tbody>{result.cases.map((item) => <tr key={item.caseId} className="border-t border-cyan-100 bg-white/80"><td className="p-2 font-bold">{item.title}</td><td>{formatWan(item.propertyPrice)}</td><td>{formatWan(item.valuationMid)}</td><td>{formatYuan(item.monthlyPayment)}</td><td>{formatYuan(item.monthlyHoldingCost)}</td><td>{item.locationScore ?? "尚未完成"}</td><td>{item.terrainRiskLevel}</td><td>{item.riskSignal} / {item.riskScore ?? "—"}</td><td>{item.taxStatus}</td><td>{item.completionRate}%</td></tr>)}</tbody></table></div></DetailDisclosure>
    <details className="rounded-xl border border-stone-200 bg-white"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-slate-800">查看完整比較欄位</summary><div className="max-w-full touch-pan-x overflow-x-auto border-t border-stone-200"><table className="w-full min-w-[920px] text-left text-[10px]"><thead><tr className="bg-stone-50"><th className="p-2">比較欄位</th>{result.cases.map((item)=><th key={item.caseId}>{item.title}</th>)}</tr></thead><tbody>{detailRows.map(([label,render])=><tr key={label} className="border-t border-stone-100"><th className="p-2">{label}</th>{result.cases.map((item)=><td key={item.caseId}>{render(item)}</td>)}</tr>)}</tbody></table></div></details>
    {result.missingDataWarnings.length > 0 && <details className="rounded-xl border border-amber-200 bg-amber-50"><summary className="cursor-pointer px-3 py-2 text-xs font-bold text-amber-900">缺資料提醒（{result.missingDataWarnings.length}）</summary><ul className="border-t border-amber-200 p-3 text-[11px] leading-5 text-amber-800">{result.missingDataWarnings.map((item) => <li key={item}>{item}</li>)}</ul></details>}
    <p className="text-[10px] leading-5 text-slate-500">第 1 名不代表一定要買，仍要確認屋況與議價空間；本排序非正式鑑價、銀行核貸或稅務申報建議。</p>
  </section>;
}

function formatWan(value: number | null) { return value === null ? "尚未完成" : `${value.toLocaleString()} 萬`; }
function formatYuan(value: number | null) { return value === null ? "尚未完成" : `${value.toLocaleString()} 元`; }
function formatRatio(value: number | null) { return value === null ? "尚未完成" : `${(value * 100).toFixed(1)}%`; }
const detailRows: Array<[string, (item: ReturnType<typeof compareSavedCases>["cases"][number]) => string | number]> = [
  ["地點", (item) => item.location], ["坪數 / 建物型態", (item) => `${item.areaPing ?? "尚未完成"} 坪 / ${item.buildingType}`],
  ["估價區間 / 信心", (item) => `${item.valuationRange} / ${item.valuationConfidence ?? "尚未完成"}`], ["開價合理性", (item) => item.priceReasonableness],
  ["頭期款", (item) => formatWan(item.downPaymentWan)], ["月付負擔率", (item) => formatRatio(item.loanBurdenRatio)], ["持有成本負擔率", (item) => formatRatio(item.holdingBurdenRatio)],
  ["交通 / 便利 / 教育 / 醫療", (item) => `${item.transitScore ?? "—"} / ${item.convenienceScore ?? "—"} / ${item.educationScore ?? "—"} / ${item.medicalScore ?? "—"}`],
  ["區位風險資料缺口", (item) => item.locationRiskGap], ["地勢與災害風險", (item) => `${item.terrainRiskLevel} / ${item.terrainRiskStatus}`], ["主要風險", (item) => item.mainRisks.join("、") || "尚未完成"], ["主要加分", (item) => item.positives.join("、") || "尚未完成"],
  ["TaxOracle", (item) => `${item.taxStatus} / ${item.taxSignal} / ${item.taxRiskScore ?? "—"}`],
];
