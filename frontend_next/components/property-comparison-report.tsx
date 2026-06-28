"use client";

import type { CaseComparisonResult } from "@/lib/case-comparison";
import { PrintComparisonReport } from "@/components/print-comparison-report";
import { buildPropertyComparisonReport, canBuildPropertyComparisonReport, PROPERTY_COMPARISON_MAX_CASES, PROPERTY_COMPARISON_MIN_CASES } from "@/lib/property-comparison";

export function PropertyComparisonReport({ result }: { result: CaseComparisonResult }) {
  const valid = canBuildPropertyComparisonReport(result.cases.length);
  if (!valid) {
    return <div className="rounded-xl border border-dashed border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">
      請選取 {PROPERTY_COMPARISON_MIN_CASES} 至 {PROPERTY_COMPARISON_MAX_CASES} 件已保存案件，再產生比較決策報告。
    </div>;
  }
  const report = buildPropertyComparisonReport(result);
  return <PrintComparisonReport report={report} />;
}
