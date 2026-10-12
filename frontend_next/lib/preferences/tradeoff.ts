import type { PreferenceRule } from "./profile";
import type { PropertyCaseWorkspace } from "../workspace/workspace-model";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence, type EvidenceField } from "../workspace/case-evidence.ts";
export type Outcome = { rule: PreferenceRule; caseId: string; status: "met" | "unmet" | "unknown"; value: number | null; reason: "saved_input" | "saved_estimate" | "documented_evidence" | "missing" | "identity" | "route_mismatch" | "unbound_transit" | "risk_gap"; vetoBreached: boolean };
function usable(field: EvidenceField<string | number>) { return field.value !== null && !["stale", "not_run", "unavailable", "unsupported", "no_coverage", "insufficient"].includes(field.status) && field.freshness.inputRelation !== "stale" && field.freshness.timeRelation !== "stale"; }
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= 0;
const address = (v: string) => v.trim().replace(/\s+/g, " ");
const absentMetadata = new Set(["unknown", "not_configured", "not_available", "not_preserved", "unavailable", "none", "n/a", "未提供", "未提供來源名稱", "來源摘要未保存", "來源未保存", "未設定", "未取得"]);
const recorded = (v: string | null | undefined) => !!v?.trim() && !absentMetadata.has(v.trim().toLowerCase());
export function evaluatePreferences(rules: PreferenceRule[], workspace: PropertyCaseWorkspace): Outcome[] {
  const evidence = projectCaseEvidence(workspace);
  return rules.map((rule) => {
    let status: Outcome["status"] = "unknown", value: number | null = null, reason: Outcome["reason"] = "missing";
    if (workspace.identity.state !== "confirmed") reason = "identity";
    else if (rule.metric === "risk") {
      const row = workspace.risk?.rows.find(r => r.key === rule.risk);
      const checked = workspace.risk?.freshness.checkedAt;
      const documented = row && ["usable", "no_match"].includes(row.usability) && row.coverage === "covered" && recorded(row.source) && checked && Number.isFinite(Date.parse(checked)) && workspace.risk?.freshness.status !== "stale";
      reason = "risk_gap";
      if (documented) {
        reason = "documented_evidence";
        if (rule.requirement === "documented") status = "met";
        else if (rule.requirement === "versioned") status = recorded(row.datasetVersion) ? "met" : "unknown";
        else status = row.matched === true && row.usability === "usable" ? "unmet" : row.matched === false && row.usability === "no_match" ? "met" : "unknown";
        if (status === "unknown") reason = "risk_gap";
      }
    } else {
      if (rule.metric === "commute") {
        const route = workspace.location.routeEvidence;
        reason = "route_mismatch";
        if (route && address(route.destination.address) === address(rule.destination) && route.mode === rule.mode && usable(evidence.commute.duration)) { value = evidence.commute.duration.value; reason = "saved_estimate"; }
      } else if (rule.metric === "transit") {
        // The legacy surrounding-station snapshot has no saved property binding.
        // Do not promote it into a property-specific walking distance.
        reason = "unbound_transit";
      } else if (rule.metric === "age" || rule.metric === "floor") {
        const saved = rule.metric === "age" ? workspace.assumptions.ageYears : workspace.assumptions.floor;
        if (finite(saved)) { value = saved; reason = "saved_input"; }
      } else {
        const field = rule.metric === "price" ? evidence.price.asking : rule.metric === "size" ? evidence.price.area : evidence.finance.downPayment;
        if (usable(field) && finite(field.value)) { value = field.value; reason = rule.metric === "cash" ? "saved_estimate" : "saved_input"; }
      }
      if (value !== null) {
        const min = rule.metric === "commute" ? null : rule.min;
        status = (min === null || value >= min) && (rule.max === null || value <= rule.max) ? "met" : "unmet";
      }
    }
    return { rule, caseId: workspace.caseId, status, value, reason, vetoBreached: rule.priority === "veto" && status === "unmet" };
  });
}
type Statement = { kind: "commute_cash"; commuteCase: string; cashCase: string } | { kind: "cash_incomparable" };
function financeComparable(a: PropertyCaseWorkspace, b: PropertyCaseWorkspace) {
  if (!a.finance || !b.finance || !a.finance.priceSource || a.finance.priceSource !== b.finance.priceSource) return false;
  const signature = (w: PropertyCaseWorkspace) => { const f = w.finance!; return [f.savedAssumptions?.basis ?? f.priceBasis.basis, f.loan.downPaymentRatio, f.loan.annualInterestRate, f.loan.loanYears, f.loan.gracePeriodYears]; };
  const left = signature(a), right = signature(b);
  return left.every((v, i) => v !== null && v !== undefined && v === right[i]);
}
/** Stable input order, per-rule predicates only. No ranking, weights, aggregate or provider calls. */
export function buildTradeoffs(rules: PreferenceRule[], cases: PropertyCaseWorkspace[]) {
  const evaluations = cases.map(workspace => ({ caseId: workspace.caseId, outcomes: evaluatePreferences(rules, workspace) }));
  const pairs: Array<{ left: string; right: string; statements: Statement[] }> = [];
  cases.forEach((a, i) => cases.slice(i + 1).forEach((b, offset) => {
    const ao = evaluations[i].outcomes, bo = evaluations[i + offset + 1].outcomes;
    const statements: Statement[] = [];
    const cashIndex = rules.findIndex(r => r.metric === "cash");
    if (cashIndex >= 0 && ao[cashIndex].value !== null && bo[cashIndex].value !== null && ao[cashIndex].value !== bo[cashIndex].value) {
      if (!financeComparable(a, b)) statements.push({ kind: "cash_incomparable" });
      else {
        const cashCase = ao[cashIndex].value! < bo[cashIndex].value! ? a.caseId : b.caseId;
        const commuteIndex = rules.findIndex((r, index) => r.metric === "commute" && ao[index].status !== "unknown" && bo[index].status !== "unknown" && ao[index].status !== bo[index].status);
        if (commuteIndex >= 0) { const commuteCase = ao[commuteIndex].status === "met" ? a.caseId : b.caseId; if (commuteCase !== cashCase) statements.push({ kind: "commute_cash", commuteCase, cashCase }); }
      }
    }
    pairs.push({ left: a.caseId, right: b.caseId, statements });
  }));
  return { evaluations, pairs };
}
