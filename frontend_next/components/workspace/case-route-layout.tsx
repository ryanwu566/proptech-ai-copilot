"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WorkspaceProvider } from "./workspace-provider";
import { WorkspaceShell } from "./workspace-shell";
/** Evidence, Report, Decision Room and Commute Planner own diagnostic reads independently of the snapshot-writing shell. */
export function CaseRouteLayout({ caseId, children }: { caseId: string; children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === `/cases/${encodeURIComponent(caseId)}/evidence` || pathname === `/cases/${encodeURIComponent(caseId)}/report` || pathname === `/cases/${encodeURIComponent(caseId)}/decision-room` || pathname === `/cases/${encodeURIComponent(caseId)}/commute-planner`) return children;
  return <WorkspaceProvider key={caseId} caseId={caseId}><WorkspaceShell>{children}</WorkspaceShell></WorkspaceProvider>;
}
