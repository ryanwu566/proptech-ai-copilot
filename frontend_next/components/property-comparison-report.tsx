"use client";

import type { CaseComparisonResult } from "@/lib/case-comparison";
import { PrintComparisonReport } from "@/components/print-comparison-report";
import { buildPropertyComparisonReport, canBuildPropertyComparisonReport, PROPERTY_COMPARISON_MAX_CASES, PROPERTY_COMPARISON_MIN_CASES } from "@/lib/property-comparison";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function PropertyComparisonReport({ result }: { result: CaseComparisonResult }) {
  const { copy } = useExperienceLocale();
  const valid = canBuildPropertyComparisonReport(result.cases.length);
  const canExportOfficial = valid && result.comparisonStatus === "ready" && result.ranking.some((row) => row.rank !== null);
  if (!valid || result.comparisonStatus === "insufficient") {
    return <div className="rounded-xl border border-dashed border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">
      {valid ? copy("comparison.insufficientData") : `${copy("comparison.selectRange")} (${PROPERTY_COMPARISON_MIN_CASES}–${PROPERTY_COMPARISON_MAX_CASES})`}
    </div>;
  }
  if (!canExportOfficial) {
    return <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">
      <p className="font-bold">{copy("comparison.partialTitle")}</p>
      <p className="mt-1">{copy("comparison.partialNote")}</p>
      {result.missingDataWarnings.length > 0 && <ul className="mt-2 list-disc pl-5">{result.missingDataWarnings.slice(0, 5).map((item) => <li key={item}>{item}</li>)}</ul>}
    </div>;
  }
  return <PrintComparisonReport report={buildPropertyComparisonReport(result)} />;
}
