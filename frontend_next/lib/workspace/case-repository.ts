"use client";

import { CASE_LOADED_EVENT, SAVED_CASES_STORAGE_KEY, readSavedCases, type SavedCase } from "@/lib/case-storage";
import { adaptSavedCaseToWorkspace } from "@/lib/workspace/legacy-case-adapter";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";

export type PropertyCaseRepository = {
  getCase(caseId: string): PropertyCaseWorkspace | null;
  listCases(): PropertyCaseWorkspace[];
  subscribe(listener: () => void): () => void;
};

export function createBrowserCaseRepository(): PropertyCaseRepository {
  return {
    getCase(caseId) {
      const saved = readSavedCases().find((row) => row.id === caseId);
      return saved ? adaptSavedCaseToWorkspace(saved) : null;
    },
    listCases() {
      return readSavedCases().map(adaptSavedCaseToWorkspace);
    },
    subscribe(listener) {
      const onStorage = (event: StorageEvent) => {
        if (event.key === SAVED_CASES_STORAGE_KEY) listener();
      };
      const onLoaded = (_event: Event) => listener();
      window.addEventListener("storage", onStorage);
      window.addEventListener(CASE_LOADED_EVENT, onLoaded as EventListener);
      return () => {
        window.removeEventListener("storage", onStorage);
        window.removeEventListener(CASE_LOADED_EVENT, onLoaded as EventListener);
      };
    },
  };
}

export function savedCaseHref(saved: Pick<SavedCase, "id">): string {
  return `/cases/${encodeURIComponent(saved.id)}/overview`;
}
