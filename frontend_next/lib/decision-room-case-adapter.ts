import type { PropertyCaseRepository } from "./workspace/case-repository";
import type { PropertyCaseWorkspace } from "./workspace/workspace-model";
import type { RoomEvidence, EvidenceActionInput } from "./decision-room-store";
// @ts-expect-error Native TS runner extension.
import { projectCaseEvidence } from "./workspace/case-evidence.ts";
// @ts-expect-error Native TS runner extension.
import { buildEvidenceChecklist } from "./workspace/evidence-checklist.ts";

export type DecisionRoomCaseContext = { caseId: string; title: string; address: string; snapshotDate: string; savedAskingPriceWan: number | null; identityState: string; parcelStatus: string; buildingStatus: string; evidence: RoomEvidence[]; evidenceActions: EvidenceActionInput[] };
export type DecisionRoomCaseRead = { status: "ready"; context: DecisionRoomCaseContext } | { status: "missing" | "unreadable" };
export type DecisionRoomCaseAdapter = { read(caseId: string): DecisionRoomCaseRead; subscribe(listener: () => void): () => void };
function project(workspace: PropertyCaseWorkspace): DecisionRoomCaseContext {
  return {
    caseId: workspace.caseId, title: workspace.title, address: workspace.displayAddress, snapshotDate: workspace.updatedAt,
    savedAskingPriceWan: workspace.assumptions.askingPriceWan ?? null,
    identityState: workspace.identity.state,
    parcelStatus: workspace.identity.anchor?.parcel.status ?? "unavailable",
    buildingStatus: workspace.identity.anchor?.building.status ?? "unavailable",
    evidence: Object.entries(workspace.evidence).map(([key, value]) => ({ key, query: value.query, usability: value.usability, completeness: value.completeness })),
    evidenceActions: evidenceActionCandidates(workspace),
  };
}
/** Outstanding saved-evidence checklist items, keyed by their stable checklist ID. Saved text stays as saved. */
export function evidenceActionCandidates(workspace: PropertyCaseWorkspace): EvidenceActionInput[] {
  try {
    const items = buildEvidenceChecklist(projectCaseEvidence(workspace)) as Array<{ id: string; domain: string; name: string; nextAction: string; outstanding: boolean }>;
    const origins: string[] = ["identity", "market", "location", "risk", "finance"];
    return items.filter((item) => item.outstanding).map((item) => ({ origin: (item.domain === "overview" ? "identity" : item.domain) as EvidenceActionInput["origin"], sourceKey: item.id, title: item.name, note: item.nextAction })).filter((item) => origins.includes(item.origin));
  } catch { return []; }
}
/** Uses current Saved Case diagnostic reads/subscriptions; never calls a case writer. */
export function createDecisionRoomCaseAdapter(repository: Pick<PropertyCaseRepository, "readDiagnostic" | "subscribe">): DecisionRoomCaseAdapter {
  return {
    read(caseId) {
      try {
        const diagnostic = repository.readDiagnostic();
        const workspace = diagnostic.cases.find((row) => row.caseId === caseId);
        if (workspace) return { status: "ready", context: project(workspace) };
        const unreadable = ["parse_error", "invalid_storage", "storage_unavailable"].includes(diagnostic.status) || diagnostic.issues.some((issue) => issue.caseId === caseId);
        return { status: unreadable ? "unreadable" : "missing" };
      } catch { return { status: "unreadable" }; }
    },
    subscribe: repository.subscribe,
  };
}
