// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { resolveTaskReadiness } from "../commercial/readiness.ts";
import type { EvidenceKey, PropertyCaseWorkspace, WorkspaceSection } from "./workspace-model";

type OverviewItem = {
  id: string;
  label: string;
  reason: string;
  section: WorkspaceSection;
  href: string;
  evidenceKeys: EvidenceKey[];
};

const sectionRows: Array<{ section: Exclude<WorkspaceSection, "overview">; labels: Partial<Record<EvidenceKey, string>>; keys: EvidenceKey[] }> = [
  { section: "market", labels: { market: "確認市場資料", valuation: "確認價格推估" }, keys: ["market", "valuation"] },
  { section: "location", labels: { location: "確認地點資料", commute: "確認通勤資料" }, keys: ["location", "commute"] },
  { section: "risk", labels: { risk: "確認風險與環境證據" }, keys: ["risk"] },
  { section: "finance", labels: { finance: "建立資金與持有成本情境" }, keys: ["finance"] },
];

export function buildWorkspaceOverview(workspace: PropertyCaseWorkspace) {
  const unknowns: OverviewItem[] = [];
  const actions: OverviewItem[] = [];
  const findings: OverviewItem[] = [];
  for (const row of sectionRows) {
    const href = `/cases/${encodeURIComponent(workspace.caseId)}/${row.section}`;
    for (const key of row.keys) {
      const state = workspace.evidence[key];
      if (state.query !== "not_started" && state.usability !== "stale") continue;
      const item = {
        id: `${key}-${state.usability === "stale" ? "stale" : "not-started"}`,
        label: row.labels[key] ?? "確認此項證據",
        reason: state.usability === "stale" ? "既有摘要需要重新確認，暫不視為目前證據。" : "此項證據尚未查詢；沒有資料不代表沒有問題。",
        section: row.section,
        href,
        evidenceKeys: [key],
      };
      unknowns.push(item);
      if (!actions.some((action) => action.section === row.section)) actions.push(item);
    }
  }
  const blockers: OverviewItem[] = [];
  if (workspace.identity.state === "revalidation_required" || workspace.identity.state === "conflict") {
    blockers.push({
      id: "identity-revalidation",
      label: "重新確認目前物件",
      reason: "物件資料已變更，先前受影響的證據不可視為目前有效。",
      section: "overview",
      href: `/cases/${encodeURIComponent(workspace.caseId)}/overview`,
      evidenceKeys: [],
    });
  }
  const readiness = blockers.length > 0
    ? resolveTaskReadiness("viewing_preparation", "blocked", { blocker: "物件身分需重新確認" })
    : resolveTaskReadiness("viewing_preparation", "not_ready");
  const counts = Object.values(workspace.evidence).reduce((result, state) => {
    const key = state.usability ?? "not_started";
    result[key] = (result[key] ?? 0) + 1;
    return result;
  }, {} as Record<string, number>);
  return { findings, unknowns, blockers, actions: actions.slice(0, 5), readiness, evidenceCounts: counts };
}
