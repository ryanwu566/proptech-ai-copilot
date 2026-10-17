import type { CaseEvidenceModel, EvidenceField, GapReason } from "./case-evidence";
import type { Citation, EvidenceState } from "./document-evidence";
import type { WorkspaceSection } from "./workspace-model";
// @ts-expect-error Native TS runner extension.
import { evidenceFields } from "./case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { PRICE_BASIS_LABELS } from "./evidence-labels.ts";

/**
 * Deterministic page-one summary of one frozen report snapshot.
 * Inputs are the frozen evidence and the report's own citation list only: no provider,
 * storage, clock or other-case reads. Every evidence-backed item carries the existing
 * report citation IDs of all of its inputs; an item whose inputs cannot all be cited is
 * omitted rather than shown uncited. Absence statements carry gap IDs instead.
 */
export type ExecutiveTrust = "user_entered" | "saved_estimate" | "saved_source" | "saved_calculation" | "derived";
export type ExecutiveRef = { fieldId: string; citationId: string; state: EvidenceState };
export type ExecutiveKeyNumber = {
  id: "asking" | "selected" | "asking_unit" | "market" | "housing" | "commute";
  trust: ExecutiveTrust; label: string; value: number; unit: string;
  /** Saved text context (source language), e.g. price basis, destination and mode. */
  context: string[];
  band: { low: number; high: number; unit: string } | null;
  /** Derived comparison of the asking unit price against the saved observed band. */
  position: "below" | "within" | "above" | null;
  samples: number | null; period: string | null;
  refs: ExecutiveRef[];
};
export type ExecutiveAttention =
  | { id: "conflicting_price"; finance: number; selected: number; unit: string; refs: ExecutiveRef[]; gapIds: string[] }
  | { id: "stale"; labels: string[]; count: number; refs: ExecutiveRef[]; gapIds: string[] }
  | { id: "risk_match"; labels: string[]; refs: ExecutiveRef[]; gapIds: string[] }
  | { id: "risk_unresolved"; count: number; total: number; labels: string[]; refs: ExecutiveRef[]; gapIds: string[] }
  | { id: "affordability_not_assessed"; refs: ExecutiveRef[]; gapIds: string[] };
export type ExecutiveOpenItem = { domain: WorkspaceSection; count: number; items: Array<{ gapId: string; label: string; reason: GapReason }>; more: number; href: string };
export type ReportExecutiveSummary = {
  contract: "report-executive-v1"; caseId: string;
  property: { title: string; address: string; identity: CaseEvidenceModel["identity"]["state"]; identityScope: CaseEvidenceModel["identity"]["scope"] };
  snapshot: { origin: "saved_snapshot"; savedAt: string; generatedAt: string; autoRefresh: false };
  keyNumbers: ExecutiveKeyNumber[]; attention: ExecutiveAttention[];
  open: { total: number; areas: ExecutiveOpenItem[] };
};

export const EXECUTIVE_LIMITS = { keyNumbers: 6, attention: 5, openAreas: 5, openItemsPerArea: 3, labels: 4 } as const;
const DOMAINS: WorkspaceSection[] = ["overview", "market", "location", "risk", "finance"];
const usable = (field: EvidenceField<string | number>) => field.value !== null && field.status !== "stale";
const num = (field: EvidenceField<string | number>): number | null => usable(field) && typeof field.value === "number" ? field.value : null;
const str = (field: EvidenceField<string | number>): string | null => usable(field) && typeof field.value === "string" ? field.value : null;
const round = (value: number) => Math.round(value * 100) / 100;

export function buildReportExecutiveSummary(evidence: CaseEvidenceModel, citations: Citation[], generatedAt: string): ReportExecutiveSummary {
  // Only this case's report citations may support its summary.
  const own = citations.filter((citation) => citation.caseId === evidence.caseId);
  /** All-or-nothing: returns null unless every input field resolves to a report citation. */
  const cite = (...fields: Array<EvidenceField<string | number>>): ExecutiveRef[] | null => {
    const refs = fields.map((field) => {
      const citation = own.find((item) => item.observationId === field.id);
      return citation ? { fieldId: field.id, citationId: citation.id, state: citation.state } : null;
    });
    return refs.every(Boolean) ? refs as ExecutiveRef[] : null;
  };
  const gapIds = (prefix: string) => evidence.gaps.filter((gap) => gap.id.startsWith(prefix)).map((gap) => gap.id);
  const { price, commute, finance } = evidence;

  const keyNumbers: ExecutiveKeyNumber[] = [];
  const push = (item: Omit<ExecutiveKeyNumber, "band" | "position" | "samples" | "period" | "context"> & Partial<ExecutiveKeyNumber>) => keyNumbers.push({ context: [], band: null, position: null, samples: null, period: null, ...item });
  const asking = num(price.asking);
  const askingRefs = asking === null ? null : cite(price.asking);
  if (asking !== null && askingRefs) push({ id: "asking", trust: "user_entered", label: price.asking.label, value: asking, unit: price.asking.unit, refs: askingRefs });
  const selected = num(price.active); const basis = str(price.basis);
  // The selected price is only repeated when it is not simply the asking price.
  if (selected !== null && basis !== null && (selected !== asking || price.basis.value !== PRICE_BASIS_LABELS.asking)) {
    // An estimate-based selection is a saved transaction estimate, not a user-entered price;
    // it also cites the saved estimate when that evidence is still citable.
    const estimate = price.basis.value === PRICE_BASIS_LABELS.estimate;
    const refs = cite(price.active, price.basis);
    const estimateRefs = estimate && usable(price.valuationEstimate) ? cite(price.valuationEstimate) ?? [] : [];
    if (refs) refs.push(...estimateRefs);
    if (refs) push({ id: "selected", trust: estimate ? "saved_estimate" : "user_entered", label: price.active.label, value: selected, unit: price.active.unit, context: [basis], refs });
  }
  const area = num(price.area);
  const p25 = num(price.marketP25); const p75 = num(price.marketP75);
  const sameUnit = price.marketP25.unit === price.marketP75.unit;
  if (asking !== null && area !== null && area > 0) {
    const exact = asking / area; const unitPrice = round(exact);
    const comparable = p25 !== null && p75 !== null && sameUnit && p25 <= p75 && price.marketP25.unit === `${price.asking.unit}／${price.area.unit}`;
    const refs = comparable ? cite(price.asking, price.area, price.marketP25, price.marketP75) : cite(price.asking, price.area);
    if (refs) push({ id: "asking_unit", trust: "derived", label: "asking_unit", value: unitPrice, unit: `${price.asking.unit}／${price.area.unit}`,
      band: comparable ? { low: p25!, high: p75!, unit: price.marketP25.unit } : null,
      // Position uses the unrounded quotient; rounding is for display only.
      position: comparable ? exact < p25! ? "below" : exact > p75! ? "above" : "within" : null, refs });
  }
  const median = num(price.marketMedianUnit);
  if (median !== null) {
    const band = p25 !== null && p75 !== null && sameUnit && p25 <= p75;
    const samples = num(price.sampleSize); const period = str(price.period); const scope = str(price.scope);
    const fields = [price.marketMedianUnit, ...(band ? [price.marketP25, price.marketP75] : []), ...(samples !== null ? [price.sampleSize] : []), ...(period !== null ? [price.period] : []), ...(scope !== null ? [price.scope] : [])];
    const refs = cite(...fields);
    if (refs) push({ id: "market", trust: "saved_source", label: price.marketMedianUnit.label, value: median, unit: price.marketMedianUnit.unit, context: scope ? [scope] : [], band: band ? { low: p25!, high: p75!, unit: price.marketP25.unit } : null, samples, period, refs });
  }
  const housing = num(finance.knownMonthlyHousing);
  const housingRefs = housing === null ? null : cite(finance.knownMonthlyHousing);
  if (housing !== null && housingRefs) push({ id: "housing", trust: "saved_calculation", label: finance.knownMonthlyHousing.label, value: housing, unit: finance.knownMonthlyHousing.unit, refs: housingRefs });
  const duration = num(commute.duration); const destination = str(commute.destination); const mode = str(commute.mode);
  // A duration without its destination and mode is not decision-useful on page one.
  if (duration !== null && destination !== null && mode !== null) {
    const refs = cite(commute.duration, commute.destination, commute.mode);
    if (refs) push({ id: "commute", trust: "saved_source", label: commute.duration.label, value: duration, unit: commute.duration.unit, context: [destination, mode], refs });
  }

  const attention: ExecutiveAttention[] = [];
  const financePrice = num(finance.price);
  if (financePrice !== null && selected !== null && financePrice !== selected && finance.price.unit === price.active.unit) {
    const refs = cite(finance.price, price.active);
    if (refs) attention.push({ id: "conflicting_price", finance: financePrice, selected, unit: price.active.unit, refs, gapIds: [] });
  }
  const stale = (evidenceFields(evidence) as Array<EvidenceField<string | number>>).filter((field) => field.status === "stale");
  const staleRefs = stale.map((field) => cite(field)?.[0]).filter((ref): ref is ExecutiveRef => Boolean(ref));
  if (stale.length) attention.push({ id: "stale", labels: stale.slice(0, EXECUTIVE_LIMITS.labels).map((field) => field.label), count: stale.length, refs: staleRefs, gapIds: stale.map((field) => field.id).filter((id) => evidence.gaps.some((gap) => gap.id === id)) });
  const matched = evidence.risk.filter((row) => row.matched === true && usable(row.evidence));
  const matchedRefs = matched.length ? cite(...matched.map((row) => row.evidence)) : null;
  if (matchedRefs) attention.push({ id: "risk_match", labels: matched.map((row) => row.evidence.label), refs: matchedRefs, gapIds: [] });
  // Anything short of a current, usable match stays unresolved (no match, unknown, stale,
  // not run, unavailable, unsupported); none of these means safe.
  const unresolved = evidence.risk.filter((row) => row.matched !== true || !usable(row.evidence));
  if (unresolved.length) {
    const cited = unresolved.map((row) => cite(row.evidence)?.[0]).filter((ref): ref is ExecutiveRef => Boolean(ref));
    attention.push({ id: "risk_unresolved", count: unresolved.length, total: evidence.risk.length, labels: unresolved.slice(0, EXECUTIVE_LIMITS.labels).map((row) => row.evidence.label), refs: cited, gapIds: gapIds("risk-") });
  }
  // Only a saved burden ratio means affordability was assessed; the summary never restates it as a conclusion.
  const assessed = num(finance.burdenRatio) !== null || finance.affordability.value === "依保存假設已評估";
  if (!assessed && (finance.affordability.value !== null || housing !== null || num(finance.monthlyPayment) !== null)) {
    // An absence statement stays visible, gap-backed, even when its state field cannot be cited.
    const refs = finance.affordability.value !== null ? cite(finance.affordability) ?? [] : [];
    attention.push({ id: "affordability_not_assessed", refs, gapIds: ["finance-affordability", "finance-income", "finance-burden"].filter((id) => evidence.gaps.some((gap) => gap.id === id)) });
  }

  const areas = DOMAINS.map((domain): ExecutiveOpenItem | null => {
    const gaps = evidence.gaps.filter((gap) => gap.domain === domain && gap.caseId === evidence.caseId);
    if (!gaps.length) return null;
    const items = gaps.slice(0, EXECUTIVE_LIMITS.openItemsPerArea).map((gap) => ({ gapId: gap.id, label: gap.item, reason: gap.reason }));
    return { domain, count: gaps.length, items, more: gaps.length - items.length, href: `/cases/${encodeURIComponent(evidence.caseId)}/${domain}` };
  }).filter((item): item is ExecutiveOpenItem => Boolean(item));

  return {
    contract: "report-executive-v1", caseId: evidence.caseId,
    property: { title: evidence.title, address: evidence.displayAddress, identity: evidence.identity.state, identityScope: evidence.identity.scope },
    snapshot: { origin: "saved_snapshot", savedAt: evidence.savedAt, generatedAt, autoRefresh: false },
    keyNumbers: keyNumbers.slice(0, EXECUTIVE_LIMITS.keyNumbers), attention: attention.slice(0, EXECUTIVE_LIMITS.attention),
    open: { total: evidence.gaps.filter((gap) => gap.caseId === evidence.caseId).length, areas: areas.slice(0, EXECUTIVE_LIMITS.openAreas) },
  };
}
