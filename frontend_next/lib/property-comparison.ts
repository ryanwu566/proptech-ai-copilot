import type { CaseComparisonResult } from "@/lib/case-comparison";

export const PROPERTY_COMPARISON_MIN_CASES = 2;
export const PROPERTY_COMPARISON_MAX_CASES = 3;
export const PROPERTY_COMPARISON_REPORT_NOTICE =
  "本報告僅整理已保存案件的既有分析結果，資料不足或暫時不可用不代表沒有風險；請勿將本報告視為購買建議、法律意見、貸款承諾、稅務申報建議或正式鑑定。";

export type PropertyComparisonReport = {
  generatedAt: string;
  caseCount: number;
  summary: string;
  topCandidateTitle: string | null;
  keyDifferences: string[];
  missingData: string[];
  nextSteps: string[];
  notice: string;
};

export function buildPropertyComparisonReport(
  result: CaseComparisonResult,
  generatedAt = new Date().toISOString(),
): PropertyComparisonReport {
  const top = result.ranking[0];
  const topCase = top ? result.cases.find((item) => item.caseId === top.caseId) : undefined;
  return {
    generatedAt,
    caseCount: result.cases.length,
    summary: result.summary,
    topCandidateTitle: topCase?.title ?? null,
    keyDifferences: buildKeyDifferences(result),
    missingData: result.missingDataWarnings.slice(0, 8),
    nextSteps: buildNextSteps(result),
    notice: PROPERTY_COMPARISON_REPORT_NOTICE,
  };
}

export function canBuildPropertyComparisonReport(caseCount: number): boolean {
  return caseCount >= PROPERTY_COMPARISON_MIN_CASES && caseCount <= PROPERTY_COMPARISON_MAX_CASES;
}

function buildKeyDifferences(result: CaseComparisonResult): string[] {
  const rows = result.cases;
  if (rows.length < 2) return ["至少保存並選取 2 件案件後，才能形成比較重點。"];
  const differences = [
    spreadText("價格", rows.map((item) => item.propertyPrice)),
    spreadText("每月房貸", rows.map((item) => item.monthlyPayment)),
    spreadText("每月持有成本", rows.map((item) => item.monthlyHoldingCost)),
    spreadText("區位分數", rows.map((item) => item.locationScore)),
  ].filter(Boolean) as string[];
  const terrainUnknown = rows.filter((item) => item.terrainRiskStatus.includes("unknown") || item.terrainRiskStatus.includes("資料"));
  if (terrainUnknown.length) differences.push("部分案件的地勢或災害資料不足，不能推論為低風險。");
  const taxMissing = rows.filter((item) => item.taxRiskScore === null);
  if (taxMissing.length) differences.push("部分案件尚未完成 TaxOracle 快篩，稅務風險仍需補查。");
  return differences.length ? differences.slice(0, 6) : ["目前已保存資料的差異有限，建議補齊貸款、持有成本、區位與風險資料後再比較。"];
}

function buildNextSteps(result: CaseComparisonResult): string[] {
  const steps = new Set<string>();
  if (result.missingDataWarnings.length) steps.add("先補齊缺少的估價、貸款、持有成本、區位、地勢災害或稅務資料。");
  if (result.cases.some((item) => item.mainRisks.length > 0)) steps.add("針對主要風險逐項回到原分析模組複核，不要只看排名。");
  if (result.cases.some((item) => item.terrainRiskStatus.includes("unknown") || item.terrainRiskStatus.includes("unavailable"))) steps.add("地勢或災害資料不足的案件，請先補查官方資料與現場條件。");
  steps.add("若要與家人或同事討論，可使用列印功能另存 PDF。");
  return [...steps].slice(0, 5);
}

function spreadText(label: string, values: Array<number | null>): string | null {
  const finite = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (finite.length < 2) return null;
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) return `${label}目前差異不大。`;
  return `${label}落差約 ${formatNumber(max - min)}，請搭配風險與資料完整度一起看。`;
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1);
}
