"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WorkspaceProvider } from "./workspace-provider";
import { CaseFrame, WorkspaceContent } from "./workspace-shell";
import { CaseWorkflowHandoff } from "@/components/navigation/case-workflow-handoff";
import { CasePulse, useSavedCase } from "./case-pulse";
import { PropertyContextHeader } from "./property-context-header";

/** Keep the frame above the route-family boundary. Diagnostic routes still own their reads and print gates. */
export function CaseRouteLayout({ caseId, children }: { caseId: string; children: ReactNode }) {
  const pathname = usePathname();
  const base = `/cases/${encodeURIComponent(caseId)}`;
  const standalone = ["evidence", "report", "decision-room", "commute-planner"].some((section) => pathname === `${base}/${section}`);
  const workspace = useSavedCase(caseId);
  return <CaseFrame caseId={caseId} header={workspace && <PropertyContextHeader key={caseId} workspace={workspace} readOnly={standalone} />} pulse={workspace && <CasePulse key={caseId} workspace={workspace} />}>
    {standalone
      ? <>{children}<div className="case-standalone-handoff"><CaseWorkflowHandoff caseId={caseId} /></div></>
      : <WorkspaceProvider key={caseId} caseId={caseId}><WorkspaceContent>{children}</WorkspaceContent></WorkspaceProvider>}
  </CaseFrame>;
}
