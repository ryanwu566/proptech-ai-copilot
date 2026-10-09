// @ts-expect-error Native TS runner extension.
import { isOpaqueCaseId } from "./compare-selection.ts";
import type { SavedCase } from "../case-storage";

export const CHECKLIST_IDS = ["identity-legal", "property-area", "price-asking", "market-summary", "valuation-summary", "location-summary", "poi-risk", "commute-summary", "risk-terrain", "risk-flood", "risk-landslide", "risk-debris_flow", "risk-liquefaction", "risk-geological_sensitivity", "risk-active_fault", "finance-scenario", "finance-affordability", "finance-costs", "finance-tax"] as const;
export type ChecklistId = typeof CHECKLIST_IDS[number];
export type ManualReviewState = "not_checked" | "pending" | "reviewed" | "recheck";
export type ChecklistReviewEntry = {
  id: ChecklistId; state: ManualReviewState; identityToken: string; evidenceToken: string;
  reviewedAt: string | null; updatedAt: string;
};
export type StoredChecklistReviewV1 = { version: 1; caseId: string; entries: ChecklistReviewEntry[] };
export const MAX_CHECKLIST_ITEMS = 24;
export const MAX_CHECKLIST_BYTES = 8192;

function object(value: unknown): value is Record<string, unknown> { return Boolean(value && typeof value === "object" && !Array.isArray(value)); }
function date(value: unknown): value is string { return typeof value === "string" && value.length <= 40 && Number.isFinite(Date.parse(value)); }
function token(value: unknown): value is string { return typeof value === "string" && /^c1-[a-f0-9]{16}$/.test(value); }

/** Local change detector, not authentication or proof of verification. Stores no source payload. */
export function checklistToken(value: unknown): string {
  const text = JSON.stringify(value); let a = 2166136261; let b = 3339675911;
  for (let index = 0; index < text.length; index++) { const code = text.charCodeAt(index); a = Math.imul(a ^ code, 16777619); b = Math.imul(b ^ code, 2246822519); }
  return `c1-${(a >>> 0).toString(16).padStart(8, "0")}${(b >>> 0).toString(16).padStart(8, "0")}`;
}

/** Strict required fields, version/ID/state bounds; extra properties never survive normalization. */
export function normalizeChecklistReview(value: unknown): StoredChecklistReviewV1 | null {
  if (!object(value) || value.version !== 1 || !isOpaqueCaseId(value.caseId) || !Array.isArray(value.entries) || value.entries.length > MAX_CHECKLIST_ITEMS) return null;
  const entries: ChecklistReviewEntry[] = []; const ids = new Set<string>();
  for (const entry of value.entries) {
    if (!object(entry) || !CHECKLIST_IDS.includes(entry.id as ChecklistId) || ids.has(String(entry.id)) || !["not_checked", "pending", "reviewed", "recheck"].includes(String(entry.state)) || !token(entry.identityToken) || !token(entry.evidenceToken) || !date(entry.updatedAt) || !(entry.reviewedAt === null || date(entry.reviewedAt)) || entry.state === "reviewed" && entry.reviewedAt === null) return null;
    ids.add(String(entry.id));
    entries.push({ id: entry.id as ChecklistId, state: entry.state as ManualReviewState, identityToken: entry.identityToken, evidenceToken: entry.evidenceToken, reviewedAt: entry.reviewedAt as string | null, updatedAt: entry.updatedAt });
  }
  entries.sort((left, right) => CHECKLIST_IDS.indexOf(left.id) - CHECKLIST_IDS.indexOf(right.id));
  const normalized: StoredChecklistReviewV1 = { version: 1, caseId: value.caseId, entries };
  return new TextEncoder().encode(JSON.stringify(normalized)).length <= MAX_CHECKLIST_BYTES ? normalized : null;
}

/** Conservative write-time latch. Source changes invalidate their whole action domain. */
export function invalidateChangedChecklist(previous: SavedCase | undefined, current: SavedCase): StoredChecklistReviewV1 | undefined {
  const review = normalizeChecklistReview(current.data.checklistReview);
  if (!review || review.caseId !== current.id) return undefined;
  if (!previous) return { ...review, entries: review.entries.map((entry) => ({ ...entry, state: "recheck" })) };
  const identity = (row: SavedCase) => [row.data.propertyIdentityAnchor, row.data.journeyContext?.propertyContext.addressSummary, row.inputSummary.city, row.inputSummary.district, row.inputSummary.road];
  const domain = (row: SavedCase, id: ChecklistId): unknown => {
    const data = row.data;
    if (id.startsWith("risk-")) return [data.terrainReference, data.riskEvidenceCheckedAt];
    if (id.startsWith("finance-")) return [data.financeEvidence, data.financePriceEvidence, data.loan, data.holdingCost, data.taxOracle, data.journeyContext, row.inputSummary.areaPing, data.inputs.area_ping];
    if (id === "commute-summary") return [data.commuteRoute, data.commuteTransit];
    if (id === "location-summary" || id === "poi-risk") return data.locationInsight;
    return [data.marketInsight, data.valuation, data.valuationEvidence, data.journeyContext, row.inputSummary.areaPing];
  };
  const changedIdentity = checklistToken(identity(previous)) !== checklistToken(identity(current));
  return { ...review, entries: review.entries.map((entry) => changedIdentity || checklistToken(domain(previous, entry.id)) !== checklistToken(domain(current, entry.id)) ? { ...entry, state: "recheck" } : entry) };
}
