import type { CaseEvidenceModel, EvidenceField, GapReason } from "./case-evidence";
import type { WorkspaceSection } from "./workspace-model";

/**
 * Client-facing core pages (2 and 3) of one frozen report snapshot. Page one is the
 * executive summary; every detailed report section moves to the appendix unchanged.
 * Facts are a fixed, deterministic selection of existing evidence fields: missing,
 * stale and unknown fields stay listed with their state, never dropped or filled in.
 * Inputs are the frozen evidence only: no provider, storage or clock reads.
 * Display copy is resolved by the view from area IDs (report-core-copy).
 */
export type ReportCoreArea = Exclude<WorkspaceSection, "overview">;
export type ReportCoreGroup = { id: ReportCoreArea; facts: Array<EvidenceField<string | number>> };
export type ReportCoreNextStep = { domain: WorkspaceSection; count: number; items: Array<{ gapId: string; label: string; reason: GapReason }>; more: number; actions: string[]; href: string };
export type ReportCore = {
  contract: "report-core-v1"; caseId: string;
  pages: [
    { id: "decision"; number: 1 },
    { id: "market_location_risk"; number: 2; groups: ReportCoreGroup[] },
    { id: "finance_next"; number: 3; groups: ReportCoreGroup[]; nextSteps: ReportCoreNextStep[]; gapTotal: number },
  ];
  /** Detailed report section IDs, in order; every section is kept, none is dropped. */
  appendix: string[];
};

export const REPORT_CORE_LIMITS = { itemsPerStep: 6 } as const;
export const REPORT_APPENDIX_SECTIONS = ["context", "summary", "market", "location", "risk", "finance", "limits", "actions", "sources"] as const;
const DOMAINS: WorkspaceSection[] = ["overview", "market", "location", "risk", "finance"];

export function buildReportCore(evidence: CaseEvidenceModel): ReportCore {
  const { price, location, commute, finance } = evidence;
  // A current, usable match leads; every other risk source follows in saved order and stays unresolved.
  const current = (row: CaseEvidenceModel["risk"][number]) => Number(row.matched === true && row.evidence.value !== null && row.evidence.status !== "stale");
  const risks = [...evidence.risk].sort((a, b) => current(b) - current(a)).map((row) => row.evidence);
  const gaps = evidence.gaps.filter((gap) => gap.caseId === evidence.caseId);
  const nextSteps = DOMAINS.map((id): ReportCoreNextStep | null => {
    const own = gaps.filter((gap) => gap.domain === id);
    if (!own.length) return null;
    const items = own.slice(0, REPORT_CORE_LIMITS.itemsPerStep).map((gap) => ({ gapId: gap.id, label: gap.item, reason: gap.reason }));
    return { domain: id, count: own.length, items, more: own.length - items.length, actions: [...new Set(own.map((gap) => gap.nextAction))], href: `/cases/${encodeURIComponent(evidence.caseId)}/${id}` };
  }).filter((item): item is ReportCoreNextStep => Boolean(item));
  return {
    contract: "report-core-v1", caseId: evidence.caseId,
    pages: [
      { id: "decision", number: 1 },
      { id: "market_location_risk", number: 2, groups: [
        { id: "market", facts: [price.asking, price.active, price.area, price.marketMedianUnit, price.marketP25, price.marketP75, price.sampleSize, price.period, price.scope, price.valuationEstimate] },
        { id: "location", facts: [commute.duration, commute.destination, commute.mode, location.transit, location.convenience, location.medical, location.school, location.riskFacility, location.radius] },
        { id: "risk", facts: risks },
      ] },
      { id: "finance_next", number: 3, groups: [
        { id: "finance", facts: [finance.price, finance.basis, finance.downPayment, finance.interestRate, finance.term, finance.monthlyPayment, finance.knownMonthlyHousing, finance.affordability, finance.burdenRatio, finance.missingCosts] },
      ], nextSteps, gapTotal: gaps.length },
    ],
    appendix: [...REPORT_APPENDIX_SECTIONS],
  };
}
