// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { resolveTaskReadiness, type NamedTaskReadiness } from "../commercial/readiness.ts";
// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildLocationOverviewHandoff, type LocationOverviewHandoff } from "./location-context.ts";
import type { EvidenceUsabilityState } from "../commercial/state";
import type { EvidenceKey, PropertyCaseWorkspace, WorkspaceSection } from "./workspace-model";

export type OverviewItemState = "known" | "not_started" | "unavailable" | "partial" | "stale" | "saved_snapshot" | "action_required";

export type OverviewItem = {
  id: string;
  label: string;
  reason: string;
  section: WorkspaceSection;
  href: string;
  evidenceKeys: EvidenceKey[];
  state: OverviewItemState;
};

type OverviewFreshness = "current" | "saved_snapshot" | "partial" | "stale" | "unavailable" | "not_started";

export type WorkspaceOverviewModel = {
  property: { caseId: string; revision: number; title: string; displayAddress: string; identityState: PropertyCaseWorkspace["identity"]["state"] };
  snapshot: { kind: "saved_snapshot"; savedAt: string; isLive: false };
  domains: {
    market: {
      href: string;
      askingPrice: PropertyCaseWorkspace["marketPrice"]["priceContext"]["askingPrice"];
      activePrice: PropertyCaseWorkspace["marketPrice"]["priceContext"]["activePrice"];
      evidenceStatus: PropertyCaseWorkspace["marketPrice"]["overview"]["evidenceStatus"];
      valuationStatus: PropertyCaseWorkspace["marketPrice"]["valuation"]["status"];
      estimateRange: string | null;
      marketRange: string | null;
      marketMedianUnit: PropertyCaseWorkspace["marketPrice"]["priceContext"]["marketMedianUnit"];
      sampleCount: number | null;
      unresolvedChecks: string[];
      freshness: OverviewFreshness;
    };
    location: LocationOverviewHandoff & { href: string; secondaryTransitStatus: "available" | "unavailable" | "not_started"; freshness: OverviewFreshness; route: LocationOverviewHandoff["selectedRoute"] | null };
    risk: {
      href: string;
      materialMatchedEvidence: NonNullable<PropertyCaseWorkspace["risk"]>["overview"]["materialMatchedEvidence"];
      noMatchEvidence: NonNullable<PropertyCaseWorkspace["risk"]>["overview"]["noMatchEvidence"];
      unknownOrUnavailableEvidence: NonNullable<PropertyCaseWorkspace["risk"]>["overview"]["unknownOrUnavailableEvidence"];
      outstandingVerificationActions: string[];
      evidenceFreshness: string | null;
      freshness: OverviewFreshness;
    };
    finance: {
      priceSource: NonNullable<PropertyCaseWorkspace["finance"]>["priceSource"];
      href: string;
      activePriceBasis: PropertyCaseWorkspace["assumptions"]["activePriceBasis"];
      calculationStatus: NonNullable<PropertyCaseWorkspace["finance"]>["overview"]["calculationStatus"];
      monthlyPaymentTwd: number | null;
      knownRecurringMonthlyTwd: number | null;
      missingCosts: string[];
      affordabilityStatus: "assessed" | "unassessed" | "stale";
      unresolvedActions: string[];
      freshness: OverviewFreshness;
    };
  };
  known: OverviewItem[];
  unknown: OverviewItem[];
  unknowns: OverviewItem[];
  attention: OverviewItem[];
  blockers: OverviewItem[];
  actions: OverviewItem[];
  findings: OverviewItem[];
  readiness: NamedTaskReadiness;
  unresolvedCount: number;
  evidenceCounts: Record<string, number>;
};

const sections: Array<{ section: Exclude<WorkspaceSection, "overview">; key: EvidenceKey; label: string }> = [
  { section: "market", key: "market", label: "確認市場成交證據" },
  { section: "market", key: "valuation", label: "確認價格推估" },
  { section: "location", key: "location", label: "確認地點資料" },
  { section: "location", key: "commute", label: "設定通勤目的地" },
  { section: "risk", key: "risk", label: "確認風險與環境證據" },
  { section: "finance", key: "finance", label: "建立資金與持有成本情境" },
];

function href(workspace: PropertyCaseWorkspace, section: WorkspaceSection): string {
  return `/cases/${encodeURIComponent(workspace.caseId)}/${section}`;
}

function item(workspace: PropertyCaseWorkspace, input: Omit<OverviewItem, "href">): OverviewItem {
  return { ...input, href: href(workspace, input.section) };
}

function evidenceFreshness(workspace: PropertyCaseWorkspace, keys: EvidenceKey[]): OverviewFreshness {
  const states = keys.map((key) => workspace.evidence[key]);
  if (states.some((state) => state.usability === "stale")) return "stale";
  const hasUnavailable = states.some((state) => state.usability === "unavailable" || state.usability === "no_coverage");
  const hasNotStarted = states.some((state) => state.query === "not_started");
  const hasUsableEvidence = states.some((state) => state.query === "succeeded" && state.usability !== "unavailable" && state.usability !== "no_coverage");
  if (hasUsableEvidence && (hasUnavailable || hasNotStarted)) return "partial";
  if (hasUnavailable) return "unavailable";
  if (states.every((state) => state.query === "not_started")) return "not_started";
  if (states.some((state) => state.summaryOnly)) return "saved_snapshot";
  return "current";
}

function unavailableReason(usability: EvidenceUsabilityState | undefined): string {
  if (usability === "no_coverage") return "不在目前資料涵蓋範圍，仍需改由其他來源確認。";
  if (usability === "stale") return "既有摘要需要重新確認，暫不視為目前證據。";
  return "目前無法取得此項證據；未知仍為未知。";
}

export function buildWorkspaceOverview(workspace: PropertyCaseWorkspace): WorkspaceOverviewModel {
  const known: OverviewItem[] = [];
  const unknown: OverviewItem[] = [];
  const attention: OverviewItem[] = [];
  const blockers: OverviewItem[] = [];
  const location = buildLocationOverviewHandoff(workspace);
  const risk = workspace.risk?.overview;
  const finance = workspace.finance?.overview;

  if (workspace.identity.state === "revalidation_required" || workspace.identity.state === "conflict") {
    blockers.push({ ...item(workspace, { id: "identity-revalidation", label: "重新確認目前物件", reason: "物件資料已變更，先前受影響的證據不可視為目前有效。", section: "overview", evidenceKeys: [], state: "action_required" }), href: "/" });
  }

  for (const row of sections) {
    const state = workspace.evidence[row.key];
    if (state.query === "not_started") {
      unknown.push(item(workspace, { id: `${row.key}-not-started`, label: row.label, reason: "此項證據尚未查詢；沒有資料不代表沒有問題。", section: row.section, evidenceKeys: [row.key], state: "not_started" }));
    } else if (state.usability === "stale") {
      attention.push(item(workspace, { id: `${row.key}-stale`, label: `${row.label}（需重新確認）`, reason: unavailableReason(state.usability), section: row.section, evidenceKeys: [row.key], state: "stale" }));
    } else if (state.usability === "unavailable" || state.usability === "no_coverage") {
      unknown.push(item(workspace, { id: `${row.key}-unavailable`, label: row.key === "valuation" ? "目前無法取得價格推估" : row.label, reason: unavailableReason(state.usability), section: row.section, evidenceKeys: [row.key], state: "unavailable" }));
    }
  }

  if (!workspace.marketPrice.isStale && ["available", "limited"].includes(workspace.marketPrice.market.status)) {
    known.push(item(workspace, { id: "market-evidence", label: "已保存市場成交摘要", reason: workspace.marketPrice.primaryFinding, section: "market", evidenceKeys: ["market"], state: workspace.evidence.market.summaryOnly ? "saved_snapshot" : "known" }));
  }
  if (location.selectedRoute) {
    known.push(item(workspace, { id: "commute-route", label: `已保存前往${location.selectedRoute.destination}的路線`, reason: `已保存 ${location.selectedRoute.mode} 路線距離與時間摘要；不會在總覽自動重查。`, section: "location", evidenceKeys: ["commute"], state: workspace.evidence.commute.summaryOnly ? "saved_snapshot" : "known" }));
  }
  if (workspace.location.transitContext && workspace.location.transitContext.status !== "resolved") {
    attention.push(item(workspace, { id: "secondary-transit-unavailable", label: "次要大眾運輸證據目前無法取得", reason: "已保存的 Google 路線仍可使用；兩項證據維持獨立。", section: "location", evidenceKeys: ["commute"], state: "unavailable" }));
  }
  for (const row of risk?.materialMatchedEvidence ?? []) {
    known.push(item(workspace, { id: `risk-material-${row.key}`, label: row.label, reason: row.result, section: "risk", evidenceKeys: ["risk"], state: "saved_snapshot" }));
  }
  for (const row of risk?.noMatchEvidence ?? []) {
    attention.push(item(workspace, { id: `risk-no-match-${row.key}`, label: `${row.label}：保存摘要未命中`, reason: `${row.result} 仍需核對來源範圍與現場。`, section: "risk", evidenceKeys: ["risk"], state: "partial" }));
  }
  for (const row of risk?.unknownOrUnavailableEvidence ?? []) {
    unknown.push(item(workspace, { id: `risk-unknown-${row.key}`, label: `${row.label}仍無法判定`, reason: row.result, section: "risk", evidenceKeys: ["risk"], state: row.usability === "stale" ? "stale" : "unavailable" }));
  }
  const financeFreshness = workspace.finance?.freshness.status === "stale" ? "stale" : evidenceFreshness(workspace, ["finance"]);
  const financeCurrent = workspace.identity.state === "confirmed" && financeFreshness !== "stale";
  if (financeCurrent && finance?.calculationStatus === "succeeded" && finance.monthlyPaymentTwd !== null) {
    known.push(item(workspace, { id: "finance-calculation", label: "已保存資金試算摘要", reason: "已保留頭期款與每月付款等有界結果；計算完成不代表負擔能力已評估。", section: "finance", evidenceKeys: ["finance"], state: workspace.evidence.finance.summaryOnly ? "saved_snapshot" : "known" }));
  }
  if (financeCurrent && finance?.calculationStatus === "succeeded" && finance.affordabilityStatus === "unassessed") {
    unknown.push(item(workspace, { id: "finance-affordability-unassessed", label: "負擔能力尚未評估", reason: "未提供月收入；試算完成與負擔能力評估維持不同狀態。", section: "finance", evidenceKeys: ["finance"], state: "partial" }));
  }

  const orderedKnown = known.slice(0, 5);
  const verificationActions = [
    item(workspace, { id: "verify-market-sources", label: "核對價格與市場來源", reason: "檢視已保存證據的範圍、期間與限制。", section: "market", evidenceKeys: ["market", "valuation"], state: "action_required" }),
    item(workspace, { id: "verify-location-context", label: "核對區位與通勤條件", reason: "確認目的地、交通方式與次要交通證據是否符合本次需求。", section: "location", evidenceKeys: ["location", "commute"], state: "action_required" }),
    item(workspace, { id: "verify-risk-sources", label: "逐項核對風險來源", reason: "依各來源涵蓋範圍與限制完成查證。", section: "risk", evidenceKeys: ["risk"], state: "action_required" }),
    item(workspace, { id: "verify-finance-assumptions", label: "檢查資金與成本假設", reason: "核對收入、貸款與尚未納入的持有成本。", section: "finance", evidenceKeys: ["finance"], state: "action_required" }),
  ];
  const actionCandidates = [...blockers, ...unknown, ...attention, ...verificationActions];
  const actions = actionCandidates.filter((candidate, index, rows) => rows.findIndex((row) => row.section === candidate.section) === index).slice(0, 5);
  const readiness = blockers.length
    ? resolveTaskReadiness("viewing_preparation", "blocked", { blocker: "物件身分需重新確認" })
    : orderedKnown.length === 0
      ? resolveTaskReadiness("viewing_preparation", "not_ready")
      : unknown.length || attention.length
        ? resolveTaskReadiness("viewing_preparation", "ready_with_limits", { limitation: "尚未確認事項" })
        : resolveTaskReadiness("viewing_preparation", "ready");
  const evidenceCounts = Object.values(workspace.evidence).reduce((result, state) => {
    const key = state.usability ?? "not_started";
    result[key] = (result[key] ?? 0) + 1;
    return result;
  }, {} as Record<string, number>);

  return {
    property: { caseId: workspace.caseId, revision: workspace.revision, title: workspace.title, displayAddress: workspace.displayAddress, identityState: workspace.identity.state },
    snapshot: { kind: "saved_snapshot", savedAt: workspace.updatedAt, isLive: false },
    domains: {
      market: { href: href(workspace, "market"), askingPrice: workspace.marketPrice.priceContext.askingPrice, activePrice: workspace.marketPrice.priceContext.activePrice, evidenceStatus: workspace.marketPrice.overview.evidenceStatus, valuationStatus: workspace.marketPrice.valuation.status, estimateRange: workspace.marketPrice.overview.estimateRange, marketRange: workspace.marketPrice.overview.marketRange, marketMedianUnit: workspace.marketPrice.priceContext.marketMedianUnit, sampleCount: workspace.marketPrice.market.sampleCount, unresolvedChecks: workspace.marketPrice.overview.unresolvedChecks, freshness: evidenceFreshness(workspace, ["market", "valuation"]) },
      location: { ...location, href: href(workspace, "location"), route: location.selectedRoute ?? null, secondaryTransitStatus: !workspace.location.transitContext ? "not_started" : workspace.location.transitContext.status === "resolved" ? "available" : "unavailable", freshness: evidenceFreshness(workspace, ["location", "commute"]) },
      risk: { href: href(workspace, "risk"), materialMatchedEvidence: risk?.materialMatchedEvidence ?? [], noMatchEvidence: risk?.noMatchEvidence ?? [], unknownOrUnavailableEvidence: risk?.unknownOrUnavailableEvidence ?? [], outstandingVerificationActions: risk?.outstandingVerificationActions ?? [], evidenceFreshness: risk?.evidenceFreshness ?? null, freshness: evidenceFreshness(workspace, ["risk"]) },
      finance: { priceSource: workspace.finance?.priceSource, href: href(workspace, "finance"), activePriceBasis: finance?.activePriceBasis ?? workspace.assumptions.activePriceBasis, calculationStatus: finance?.calculationStatus ?? "not_started", monthlyPaymentTwd: financeCurrent ? finance?.monthlyPaymentTwd ?? null : null, knownRecurringMonthlyTwd: financeCurrent ? finance?.knownRecurringMonthlyTwd ?? null : null, missingCosts: finance?.missingCosts ?? [], affordabilityStatus: financeCurrent ? finance?.affordabilityStatus ?? "unassessed" : "stale", unresolvedActions: finance?.unresolvedActions ?? [], freshness: financeFreshness },
    },
    known: orderedKnown,
    unknown,
    unknowns: unknown,
    attention,
    blockers,
    actions,
    findings: orderedKnown,
    readiness,
    unresolvedCount: new Set([...unknown, ...attention, ...blockers].map((row) => row.id)).size,
    evidenceCounts,
  };
}
