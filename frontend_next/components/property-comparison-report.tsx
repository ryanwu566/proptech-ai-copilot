"use client";

import type { CaseComparisonResult } from "@/lib/case-comparison";
import { PrintComparisonReport } from "@/components/print-comparison-report";
import { buildPropertyComparisonReport, canBuildPropertyComparisonReport, PROPERTY_COMPARISON_MAX_CASES, PROPERTY_COMPARISON_MIN_CASES } from "@/lib/property-comparison";

export function PropertyComparisonReport({ result }: { result: CaseComparisonResult }) {
  const valid = canBuildPropertyComparisonReport(result.cases.length);
  const canExportOfficial = valid && result.comparisonStatus === "ready" && result.ranking.some((row) => row.rank !== null);
  if (!valid || result.comparisonStatus === "insufficient") {
    return <div className="rounded-xl border border-dashed border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">
      {valid ? "目前資料不足，無法建立正式案件比較報告。" : "請選擇 " + PROPERTY_COMPARISON_MIN_CASES + "–" + PROPERTY_COMPARISON_MAX_CASES + " 件案件。"}
    </div>;
  }
  if (!canExportOfficial) {
    return <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">
      <p className="font-bold">目前為部分資料摘要</p>
      <p className="mt-1">資料尚未足以產生正式比較報告；缺資料不會被視為 0、低風險或完成。</p>
      {result.missingDataWarnings.length > 0 && <ul className="mt-2 list-disc pl-5">{result.missingDataWarnings.slice(0, 5).map((item) => <li key={item}>{item}</li>)}</ul>}
    </div>;
  }
  return <PrintComparisonReport report={buildPropertyComparisonReport(result)} />;
}
