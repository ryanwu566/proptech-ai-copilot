"use client";

import Link from "next/link";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import type { PropertyCaseWorkspace, WorkspaceLoadState } from "@/lib/workspace/workspace-model";

const WorkspaceContext = createContext<PropertyCaseWorkspace | null>(null);
// After the first hydrated mount, later mounts (in-app navigation) read storage during render instead of
// flashing the loading state; the server render and hydration still start from "loading".
let hydrated = false;

export function WorkspaceProvider({ caseId, children }: { caseId: string; children: ReactNode }) {
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const [state, setState] = useState<WorkspaceLoadState>(() => hydrated ? readCase(repository, caseId) : { status: "loading" });

  useEffect(() => {
    hydrated = true;
    const load = () => setState(readCase(repository, caseId));
    load();
    return repository.subscribe(load);
  }, [caseId, repository]);

  if (state.status === "loading") return <WorkspaceLoading />;
  if (state.status === "not_found") return <WorkspaceNotFound />;
  return <WorkspaceContext.Provider value={state.workspace}>{children}</WorkspaceContext.Provider>;
}

function readCase(repository: ReturnType<typeof createBrowserCaseRepository>, caseId: string): WorkspaceLoadState {
  const workspace = repository.getCase(caseId);
  return workspace ? { status: "ready", workspace } : { status: "not_found", caseId };
}

export function useWorkspace(): PropertyCaseWorkspace {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return workspace;
}

function WorkspaceLoading() {
  return <main className="workspace-state" aria-busy="true"><p>正在開啟已儲存案件…</p></main>;
}

function WorkspaceNotFound() {
  return <main className="workspace-state">
    <h1 className="text-page">找不到已儲存案件</h1>
    <p className="text-body">這個瀏覽器沒有可開啟的案件資料，或案件已被移除。</p>
    <Link className="ds-button ds-button--secondary" href="/cases">返回已儲存案件</Link>
  </main>;
}
