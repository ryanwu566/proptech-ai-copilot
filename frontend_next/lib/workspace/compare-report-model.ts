// @ts-expect-error Native TS runner extension.
import { evidenceFields, type CaseEvidenceModel, type EvidenceField } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { isOpaqueCaseId } from "./compare-selection.ts";
// @ts-expect-error Native TS runner extension.
export { parseCompareSelection, compareHref } from "./compare-selection.ts";
import type { WorkspaceSection } from "./workspace-model";

export type EvidenceRow = { id: string; label: string; cells: Array<EvidenceField<string | number>> };
export type EvidenceSectionModel = { id: WorkspaceSection; title: string; description: string; rows: EvidenceRow[] };
const domains = [
  { id: "overview", title: "物件脈絡", description: "案件關聯僅限本機瀏覽器，不代表地籍或法律身分。" },
  { id: "market", title: "價格與市場", description: "開價、選定價格、市場成交分布與成交資料推估分別呈現。P25–P75 是觀察分布。" },
  { id: "location", title: "區位與通勤", description: "通勤必須連同目的地、交通方式、來源與保存時間判讀。人口為行政區次要脈絡。" },
  { id: "risk", title: "風險與環境", description: "逐來源判讀；未命中、未知或無法取得均不代表安全。" },
  { id: "finance", title: "資金與持有成本", description: "數字只適用於旁列的保存假設。已知每月住宅支出含房貸，不應重複加總。" },
] satisfies Array<{ id: WorkspaceSection; title: string; description: string }>;
export type ComparisonStatus = "ready" | "too_few" | "too_many" | "duplicate" | "invalid_selection" | "case_not_found" | "identity_requires_revalidation";
export type ComparisonModel = { status: ComparisonStatus; cases: CaseEvidenceModel[]; warnings: string[]; sections: EvidenceSectionModel[] };
export function buildEvidenceSections(cases: CaseEvidenceModel[]): EvidenceSectionModel[] {
  return domains.map((domain) => {
    const ids = [...new Set(cases.flatMap((item) => evidenceFields(item).filter((field) => field.domain === domain.id).map((field) => field.id)))];
    return { ...domain, rows: ids.map((id) => {
      const template = cases.flatMap(evidenceFields).find((field) => field.id === id)!;
      return { id, label: template.label, cells: cases.map((item) => evidenceFields(item).find((field) => field.id === id) ?? { ...template, value: null, historicalValue: null, status: "limited", missingReason: "not_preserved", source: "來源未保存", freshness: { origin: "saved_snapshot", inputRelation: "unknown", timeRelation: "unknown", checkedAt: null, sourceUpdatedAt: null }, limitation: "此案件快照未保存這項明細。" }) };
    }) };
  });
}
export function buildComparisonModel(allCases: CaseEvidenceModel[], ids: string[]): ComparisonModel {
  const blocked = (status: ComparisonStatus): ComparisonModel => ({ status, cases: [], warnings: [], sections: [] });
  if (ids.length > 4) return blocked("too_many");
  if (new Set(ids).size !== ids.length) return blocked("duplicate");
  if (ids.some((id) => !isOpaqueCaseId(id))) return blocked("invalid_selection");
  if (ids.some((id) => !allCases.some((item) => item.caseId === id))) return blocked("case_not_found");
  if (ids.length < 2) return blocked("too_few");
  const cases = ids.map((id) => allCases.find((item) => item.caseId === id)!);
  if (cases.some((item) => item.identity.state !== "confirmed")) return blocked("identity_requires_revalidation");
  const warnings = ["這是已儲存的證據比較；未知與限制請先閱讀，不提供物件排名或購買建議。"];
  if (cases.some((item) => item.gaps.length)) warnings.push("部分項目尚未取得、無法取得或快照未保存；缺值不等於零。詳見待查證缺口。");
  if (cases.some((item) => item.commute.duration.value === null)) warnings.push("部分案件缺少有效路線；通勤時間不能直接比較。");
  if (new Set(cases.map((item) => item.commute.destination.value)).size > 1) warnings.push("通勤目的地不同；並列數字不代表相同通勤需求。");
  if (new Set(cases.map((item) => item.commute.mode.value)).size > 1) warnings.push("交通方式不同；路線時間不能直接比較。");
  warnings.push("保存路線受查詢時段與路況限制；時段條件未保存，不保證目前交通時間。");
  if (new Set(cases.map((item) => [item.location.radius.value, item.location.coverage.value].join("|"))).size > 1) warnings.push("POI 半徑或來源覆蓋不同；設施計數不能直接當成同範圍差異。");
  if (new Set(cases.map((item) => [item.price.scope.value, item.price.period.value].join("|"))).size > 1) warnings.push("市場範圍或資料期間不同；成交分布需連同樣本範圍判讀。");
  const assumptions = cases.map((item) => [item.finance.price.value, item.finance.basis.value, item.finance.interestRate.value, item.finance.term.value, item.finance.downPaymentRatio.value, item.finance.gracePeriod.value, item.finance.monthlyIncome.value].join("|"));
  if (new Set(assumptions).size > 1) warnings.push("財務價格、利率、年限、自備款或收入假設不同；月付差異不代表某物件較能負擔。");
  return { status: "ready", cases, warnings, sections: buildEvidenceSections(cases) };
}

export type ReportStatus = "ready" | "ready_with_limits" | "case_not_found" | "identity_requires_revalidation";
export type ReportModel = {
  status: ReportStatus; evidence: CaseEvidenceModel | null; generatedAt: string; summary: string[];
  sections: Array<{ id: string; title: string; evidenceSection?: EvidenceSectionModel }>;
};
export function buildReportModel(evidence: CaseEvidenceModel | null, generatedAt = new Date().toISOString()): ReportModel {
  if (!evidence || evidence.identity.state !== "confirmed") return { status: evidence ? "identity_requires_revalidation" : "case_not_found", evidence, generatedAt, summary: [], sections: [] };
  const sections = buildEvidenceSections([evidence]);
  const summary = [
    "本報告依已儲存證據快照製作，不是即時重新查詢。",
    evidence.price.valuationEstimate.value === null ? "成交資料推估尚無可採用的保存數值；請依欄位狀態區分尚未查詢、無法取得與過期。" : "已保存成交資料推估摘要；不等同正式估價或銀行鑑價。",
    evidence.commute.duration.value === null ? "尚無可採用的目的地路線時間。" : `已保存前往${evidence.commute.destination.value}的${evidence.commute.mode.value}路線；目前路況仍需確認。`,
    "風險依個別來源呈現；未命中不等於安全，未知項目仍待查證。",
    evidence.finance.monthlyPayment.value === null ? "尚無可採用的保存房貸月付結果。" : "已保存財務試算；結果僅適用於保存假設，未另行重算。",
  ];
  return { status: evidence.gaps.length ? "ready_with_limits" : "ready", evidence, generatedAt, summary, sections: [
    { id: "context", title: "物件脈絡", evidenceSection: sections[0] }, { id: "summary", title: "證據摘要" },
    { id: "market", title: "價格與市場", evidenceSection: sections[1] }, { id: "location", title: "區位與通勤", evidenceSection: sections[2] },
    { id: "risk", title: "風險與環境", evidenceSection: sections[3] }, { id: "finance", title: "資金與持有成本", evidenceSection: sections[4] },
    { id: "limits", title: "未知與限制" }, { id: "actions", title: "下一步查證" }, { id: "sources", title: "來源、日期與方法" },
  ] };
}
export type SnapshotAssessment = "unchanged" | "snapshot_changed" | "case_not_found" | "invalid_case" | "identity_requires_revalidation";
export function assessReportSnapshot(frozen: CaseEvidenceModel, current: CaseEvidenceModel | null, invalid: boolean): SnapshotAssessment {
  if (invalid) return "invalid_case";
  if (!current) return "case_not_found";
  if (current.identity.state !== "confirmed") return "identity_requires_revalidation";
  return current.snapshotToken === frozen.snapshotToken ? "unchanged" : "snapshot_changed";
}
