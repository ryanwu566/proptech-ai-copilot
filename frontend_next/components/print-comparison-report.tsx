"use client";

import type { PropertyComparisonReport } from "@/lib/property-comparison";

export function PrintComparisonReport({ report }: { report: PropertyComparisonReport }) {
  function printReport() {
    window.print();
  }
  return <div className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-[10px] font-bold tracking-wider text-cyan-700">COMPARISON REPORT</p>
        <h3 className="mt-1 font-bold text-slate-950">案件比較決策報告</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">整理 {report.caseCount} 件已保存案件，協助討論下一步要補哪些資料。</p>
      </div>
      <button type="button" onClick={printReport} className="rounded-lg bg-cyan-700 px-4 py-2 text-xs font-bold text-white print:hidden">列印／另存 PDF</button>
    </div>
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      <ReportBlock title="比較摘要" items={[report.summary, report.topCandidateTitle ? `目前排序較前的案件：${report.topCandidateTitle}` : "目前尚無足夠資料形成排序。"]} />
      <ReportBlock title="主要差異" items={report.keyDifferences} />
      <ReportBlock title="缺少資料" items={report.missingData.length ? report.missingData : ["目前未偵測到明確缺漏，但仍需回到各模組確認資料品質。"]} />
      <ReportBlock title="建議下一步" items={report.nextSteps} />
    </div>
    <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-900">{report.notice}</p>
    <p className="mt-2 text-[10px] text-slate-400">產生時間：{new Date(report.generatedAt).toLocaleString("zh-TW")}</p>
  </div>;
}

function ReportBlock({ title, items }: { title: string; items: string[] }) {
  return <section className="rounded-lg border border-stone-100 bg-stone-50 p-3">
    <p className="text-xs font-bold text-slate-900">{title}</p>
    <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">
      {items.map((item) => <li key={item}>• {item}</li>)}
    </ul>
  </section>;
}
