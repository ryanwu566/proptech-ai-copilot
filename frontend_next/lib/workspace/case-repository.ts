"use client";

import { CASE_LOADED_EVENT, CASE_UPDATED_EVENT, SAVED_CASES_STORAGE_KEY, readSavedCasesDiagnostic, resaveSavedCaseSnapshot, type SavedCase } from "@/lib/case-storage";
import type { SavedCaseReadDiagnostic } from "./saved-case-diagnostics";
import type { SaveSnapshotResult } from "@/lib/workspace/case-snapshot-save";
import { adaptSavedCaseToWorkspace } from "@/lib/workspace/legacy-case-adapter";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import type { StoredChecklistReviewV1 } from "./checklist-persistence";

export type PropertyCaseRepository = {
  readDiagnostic(): WorkspaceReadDiagnostic;
  getCase(caseId: string): PropertyCaseWorkspace | null;
  listCases(): PropertyCaseWorkspace[];
  saveSnapshot(workspace: PropertyCaseWorkspace): SaveSnapshotResult;
  saveChecklist(workspace: PropertyCaseWorkspace, review: StoredChecklistReviewV1): SaveSnapshotResult;
  subscribe(listener: () => void): () => void;
};

export type WorkspaceReadDiagnostic = Omit<SavedCaseReadDiagnostic, "cases"> & { cases: PropertyCaseWorkspace[] };

function readWorkspaceDiagnostic(): WorkspaceReadDiagnostic {
  const read = readSavedCasesDiagnostic();
  const cases: PropertyCaseWorkspace[] = [];
  const issues = [...read.issues];
  for (const saved of read.cases) {
    try { cases.push(adaptSavedCaseToWorkspace(saved)); }
    catch { issues.push({ caseId: saved.id, reason: "invalid_record" }); }
  }
  return { cases, issues, status: issues.length ? "partial" : read.status };
}

export function createBrowserCaseRepository(): PropertyCaseRepository {
  return {
    readDiagnostic: readWorkspaceDiagnostic,
    getCase(caseId) {
      return readWorkspaceDiagnostic().cases.find((row) => row.caseId === caseId) ?? null;
    },
    listCases() {
      return readWorkspaceDiagnostic().cases;
    },
    saveSnapshot(workspace) {
      const anchor = workspace.identity.anchor;
      return resaveSavedCaseSnapshot(workspace.caseId, anchor?.coordinates ? {
        journeyAnchorId: anchor.journey_anchor_id,
        normalizedAddress: anchor.normalized_address,
        coordinates: anchor.coordinates,
      } : undefined, workspace.identity.state, workspace.updatedAt);
    },
    saveChecklist(workspace, review) {
      const anchor = workspace.identity.anchor;
      return resaveSavedCaseSnapshot(workspace.caseId, anchor?.coordinates ? {
        journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates: anchor.coordinates,
      } : undefined, workspace.identity.state, workspace.updatedAt, () => new Date().toISOString(), review);
    },
    subscribe(listener) {
      const onStorage = (event: StorageEvent) => {
        if (event.key === SAVED_CASES_STORAGE_KEY || event.key === null) listener();
      };
      const onLoaded = (_event: Event) => listener();
      window.addEventListener("storage", onStorage);
      window.addEventListener(CASE_LOADED_EVENT, onLoaded as EventListener);
      window.addEventListener(CASE_UPDATED_EVENT, onLoaded as EventListener);
      return () => {
        window.removeEventListener("storage", onStorage);
        window.removeEventListener(CASE_LOADED_EVENT, onLoaded as EventListener);
        window.removeEventListener(CASE_UPDATED_EVENT, onLoaded as EventListener);
      };
    },
  };
}

export function savedCaseHref(saved: Pick<SavedCase, "id">): string {
  return `/cases/${encodeURIComponent(saved.id)}/overview`;
}
