"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WorkspaceProvider } from "./workspace-provider";
import { WorkspaceShell } from "./workspace-shell";
import { CaseWorkflowHandoff } from "@/components/navigation/case-workflow-handoff";
import { WorkspaceNavigation } from "./workspace-navigation";
import { GuidedTourEntry } from "@/components/guided-tour-entry";
import { SavedCasePulse } from "./case-pulse";
import { DemoCaseNotice } from "./demo-case-notice";
/** Evidence, Report, Decision Room and Commute Planner own diagnostic reads independently of the snapshot-writing shell; they share its case navigation as a strip. */
export function CaseRouteLayout({ caseId, children }: { caseId: string; children: ReactNode }) {
  const pathname = usePathname();
  const base = `/cases/${encodeURIComponent(caseId)}`;
  // The Decision Room renders its own case navigation once its case context loads.
  if (pathname === `${base}/evidence` || pathname === `${base}/report` || pathname === `${base}/decision-room` || pathname === `${base}/commute-planner`) return <><div className="case-standalone-nav">{pathname !== `${base}/decision-room` && <WorkspaceNavigation caseId={caseId} />}<GuidedTourEntry cta="demo" className="ds-button ds-button--tertiary ds-button--compact" /></div><DemoCaseNotice caseIds={[caseId]} /><SavedCasePulse key={caseId} caseId={caseId} />{children}<div className="case-standalone-handoff"><CaseWorkflowHandoff caseId={caseId} /></div></>;
  return <WorkspaceProvider key={caseId} caseId={caseId}><WorkspaceShell>{children}</WorkspaceShell></WorkspaceProvider>;
}
