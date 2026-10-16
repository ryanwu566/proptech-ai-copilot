"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WorkspaceProvider } from "./workspace-provider";
import { WorkspaceShell } from "./workspace-shell";
import { CaseWorkflowHandoff } from "@/components/navigation/case-workflow-handoff";
/** Report, Decision Room and Commute Planner own diagnostic reads independently of the snapshot-writing shell. */
export function CaseRouteLayout({ caseId, children }: { caseId: string; children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === `/cases/${encodeURIComponent(caseId)}/report` || pathname === `/cases/${encodeURIComponent(caseId)}/decision-room` || pathname === `/cases/${encodeURIComponent(caseId)}/commute-planner`) return <>{children}<div className="case-standalone-handoff"><CaseWorkflowHandoff caseId={caseId} /></div></>;
  return <WorkspaceProvider key={caseId} caseId={caseId}><WorkspaceShell>{children}</WorkspaceShell></WorkspaceProvider>;
}
