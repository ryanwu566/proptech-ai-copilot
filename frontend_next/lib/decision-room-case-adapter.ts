import type { PropertyCaseRepository } from "./workspace/case-repository";
import type { PropertyCaseWorkspace } from "./workspace/workspace-model";
import type { RoomEvidence } from "./decision-room-store";

export type DecisionRoomCaseContext = { caseId: string; title: string; address: string; snapshotDate: string; savedAskingPriceWan: number | null; identityState: string; parcelStatus: string; buildingStatus: string; evidence: RoomEvidence[] };
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
  };
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
