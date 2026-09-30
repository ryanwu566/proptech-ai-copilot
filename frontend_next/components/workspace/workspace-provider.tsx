"use client";

import Link from "next/link";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import type { PropertyCaseWorkspace, WorkspaceLoadState } from "@/lib/workspace/workspace-model";

const WorkspaceContext = createContext<PropertyCaseWorkspace | null>(null);

export function WorkspaceProvider({ caseId, children }: { caseId: string; children: ReactNode }) {
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const [state, setState] = useState<WorkspaceLoadState>({ status: "loading" });

  useEffect(() => {
    const load = () => {
      const workspace = repository.getCase(caseId);
      setState(workspace ? { status: "ready", workspace } : { status: "not_found", caseId });
    };
    load();
    return repository.subscribe(load);
  }, [caseId, repository]);

  if (state.status === "loading") return <WorkspaceLoading />;
  if (state.status === "not_found") return <WorkspaceNotFound />;
  return <WorkspaceContext.Provider value={state.workspace}>{children}</WorkspaceContext.Provider>;
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
