"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WorkspaceProvider } from "./workspace-provider";
import { WorkspaceShell } from "./workspace-shell";
/** Dedicated report owns diagnostic reads and freezing independently of the live workspace shell. */
export function CaseRouteLayout({ caseId, children }: { caseId: string; children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === `/cases/${encodeURIComponent(caseId)}/report`) return children;
  return <WorkspaceProvider caseId={caseId}><WorkspaceShell>{children}</WorkspaceShell></WorkspaceProvider>;
}
