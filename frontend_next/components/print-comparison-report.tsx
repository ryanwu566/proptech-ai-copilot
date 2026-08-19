"use client";

import type { PropertyComparisonReport } from "@/lib/property-comparison";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PrintComparisonReport({ report }: { report: PropertyComparisonReport }) {
  const { copy, formatDate } = useExperienceLocale();
  function printReport() { window.print(); }
  return <div className="rounded-xl border border-stone-200 bg-white p-4">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-[10px] font-bold tracking-wider text-cyan-700">{copy("comparison.kicker")}</p>
        <h3 className="mt-1 font-bold text-slate-950">{copy("comparison.title")}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">{report.caseCount} cases</p>
      </div>
      <button type="button" onClick={printReport} className="rounded-lg bg-cyan-700 px-4 py-2 text-xs font-bold text-white print:hidden">{copy("comparison.printButton")}</button>
    </div>
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      <ReportBlock title={copy("comparison.summaryTitle")} items={[report.summary, report.topCandidateTitle ? `${copy("comparison.topCandidate")}: ${report.topCandidateTitle}` : copy("comparison.noRanking")]} />
      <ReportBlock title={copy("comparison.differencesTitle")} items={report.keyDifferences} />
      <ReportBlock title={copy("comparison.missingTitle")} items={report.missingData.length ? report.missingData : [copy("comparison.missingNone")]} />
      <ReportBlock title={copy("comparison.nextStepsTitle")} items={report.nextSteps} />
    </div>
    <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-900">{report.notice}</p>
    <p className="mt-2 text-[10px] text-slate-400">{copy("comparison.generated")}: {formatDate(report.generatedAt)}</p>
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
