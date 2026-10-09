import type { PropertyCaseWorkspace } from "./workspace-model";
import type { CaseEvidenceModel, EvidenceField, EvidenceGap, EvidenceSource } from "./case-evidence";
// @ts-expect-error Native TS runner extension.
import { evidenceFields, projectCaseEvidence } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { CHECKLIST_IDS, checklistToken, normalizeChecklistReview, type ChecklistId, type ManualReviewState, type StoredChecklistReviewV1 } from "./checklist-persistence.ts";

export const CHECKLIST_DOMAINS = { identity: "物件身分", risk: "風險與環境", market: "價格與市場", location: "區位與通勤", finance: "資金與成本" } as const;
export const MANUAL_REVIEW_LABELS: Record<ManualReviewState, string> = { not_checked: "尚未核對", pending: "待人工核對", reviewed: "已由使用者核對", recheck: "需再次核對" };
export type ChecklistItem = {
  id: ChecklistId; name: string; domain: keyof typeof CHECKLIST_DOMAINS; fields: EvidenceField<string | number>[];
  gaps: EvidenceGap[]; sources: EvidenceSource[]; impact: string; nextAction: string; href: string;
  evidenceToken: string; reviewState: ManualReviewState; reviewedAt: string | null; outstanding: boolean;
};
function group(id: string): ChecklistId | null {
  if (id === "price-active" || id === "price-basis") return "price-asking";
  if (id.startsWith("demographics-")) return "location-summary";
  if (id === "identity-legal" || id === "property-area" || id === "price-asking" || id === "poi-risk" || id.startsWith("risk-")) return CHECKLIST_IDS.includes(id as ChecklistId) ? id as ChecklistId : null;
  if (id.startsWith("market-")) return "market-summary";
  if (id.startsWith("valuation-")) return "valuation-summary";
  if (id.startsWith("poi-")) return "location-summary";
  if (id.startsWith("commute-") || id === "transit-context") return "commute-summary";
  if (["finance-income", "finance-burden", "finance-affordability"].includes(id)) return "finance-affordability";
  if (id === "finance-tax") return "finance-tax";
  if (id.startsWith("cost-") || ["finance-missing-costs", "finance-management", "finance-repair", "finance-home-tax", "finance-land-tax", "finance-insurance", "finance-housing"].includes(id) || id.startsWith("finance-cost-")) return "finance-costs";
  if (id.startsWith("finance-") && !["finance-grace-payment", "finance-post-grace"].includes(id)) return "finance-scenario";
  return null;
}
const names: Partial<Record<ChecklistId, string>> = { "identity-legal": "地籍、建物與權利身分", "property-area": "物件面積", "price-asking": "開價與選定價格基準", "market-summary": "市場成交範圍與樣本", "valuation-summary": "價格推估與可比明細", "location-summary": "周邊設施與來源覆蓋", "commute-summary": "目的地路線與通勤條件", "finance-scenario": "房貸試算與保存假設", "finance-affordability": "收入與負擔能力", "finance-costs": "持有與交易成本", "finance-tax": "稅務補充檢查" };
function sourceId(id: ChecklistId): string { return id.startsWith("risk-") ? id : id.startsWith("identity") || id === "property-area" ? "identity" : id.startsWith("valuation") ? "valuation" : id.startsWith("market") || id === "price-asking" ? "market" : id.startsWith("commute") ? "commute" : id.startsWith("finance") ? "finance" : "location"; }

/** Derived actions only. Official evidence remains owned by CaseEvidenceModel. */
export function buildEvidenceChecklist(evidence: CaseEvidenceModel): ChecklistItem[] {
  const fields = evidenceFields(evidence); const review = evidence.checklistReview?.caseId === evidence.caseId ? normalizeChecklistReview(evidence.checklistReview) : null;
  return CHECKLIST_IDS.flatMap((id): ChecklistItem[] => {
    const members = fields.filter((field) => group(field.id) === id);
    const gaps = evidence.gaps.filter((gap) => group(gap.id) === id);
    const sources = evidence.sources.filter((source) => source.id === sourceId(id));
    const outstanding = gaps.length > 0 || members.some((field) => field.status !== "available") || evidence.risk.some((row) => row.evidence.id === id && row.matched === true);
    const previous = review?.entries.find((entry) => entry.id === id);
    if (!outstanding && !previous) return [];
    const evidenceToken = checklistToken({ id, members, gaps, sources, matched: evidence.risk.find((row) => row.evidence.id === id)?.matched });
    const changed = evidence.identity.state !== "confirmed" || previous?.identityToken !== evidence.checklistIdentityToken || previous?.evidenceToken !== evidenceToken;
    const reviewState = previous ? changed ? "recheck" : previous.state : "not_checked";
    const domain = id === "identity-legal" || id === "property-area" ? "identity" : members[0]?.domain === "overview" ? "identity" : members[0]?.domain ?? gaps[0]?.domain ?? "overview";
    return [{ id, domain, name: names[id] ?? members[0]?.label ?? gaps[0]?.item ?? id, fields: members, gaps, sources,
      impact: [...new Set(gaps.map((gap) => gap.impact).concat(members.map((field) => field.limitation)))].join(" ") || evidence.identity.limitation,
      nextAction: gaps[0]?.nextAction ?? members[0]?.nextAction ?? "回到物件總覽確認案件條件",
      href: gaps[0]?.href ?? `/cases/${encodeURIComponent(evidence.caseId)}/${domain === "identity" ? "overview" : domain}`,
      evidenceToken, reviewState, reviewedAt: previous?.reviewedAt ?? null, outstanding }];
  }).sort((left, right) => Number(right.reviewState === "recheck") - Number(left.reviewState === "recheck") || Number(left.reviewState === "reviewed") - Number(right.reviewState === "reviewed") || Number(right.gaps.length > 0) - Number(left.gaps.length > 0) || Object.keys(CHECKLIST_DOMAINS).indexOf(left.domain) - Object.keys(CHECKLIST_DOMAINS).indexOf(right.domain));
}

export function setChecklistReview(workspace: PropertyCaseWorkspace, id: ChecklistId, state: ManualReviewState, now: string): StoredChecklistReviewV1 | undefined {
  if (workspace.identity.state !== "confirmed") return undefined;
  const evidence = projectCaseEvidence(workspace);
  const item = buildEvidenceChecklist(evidence).find((item) => item.id === id);
  if (!item) return undefined;
  const current = reconcileChecklistReview(workspace);
  const entries = (current?.entries ?? []).filter((entry) => entry.id !== id);
  entries.push({ id, state, identityToken: evidence.checklistIdentityToken!, evidenceToken: item.evidenceToken, reviewedAt: state === "reviewed" ? now : item.reviewedAt, updatedAt: now });
  return normalizeChecklistReview({ version: 1, caseId: workspace.caseId, entries }) ?? undefined;
}

/** Called on writes; latches invalidation without rewriting historical dates or bindings. */
export function reconcileChecklistReview(workspace: PropertyCaseWorkspace): StoredChecklistReviewV1 | undefined {
  const current = normalizeChecklistReview(workspace.checklistReview);
  if (!current || current.caseId !== workspace.caseId) return undefined;
  const items = buildEvidenceChecklist(projectCaseEvidence(workspace));
  return { ...current, entries: current.entries.map((entry) => {
    const item = items.find((item) => item.id === entry.id);
    return item?.reviewState === "recheck" ? { ...entry, state: "recheck" } : entry;
  }) };
}
