"use client";

import type { ReactNode } from "react";
import { PropertyContextHeader } from "./property-context-header";
import { useWorkspace } from "./workspace-provider";
import { WorkspaceNavigation } from "./workspace-navigation";
import styles from "./workspace-shell.module.css";
import { CaseWorkflowHandoff } from "@/components/navigation/case-workflow-handoff";
import { CopilotEntry } from "./copilot/copilot-entry";
import { CasePulse } from "./case-pulse";
import { DemoCaseNotice } from "./demo-case-notice";

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const workspace = useWorkspace();
  return <div className={styles.shell}>
    <PropertyContextHeader />
    <DemoCaseNotice caseIds={[workspace.caseId]} />
    <CasePulse workspace={workspace} />
    <div className={styles.body}>
      <aside className={styles.rail}><WorkspaceNavigation caseId={workspace.caseId} /></aside>
      <main className={styles.content} id="main-content" tabIndex={-1}><CopilotEntry />{children}<CaseWorkflowHandoff caseId={workspace.caseId} /></main>
    </div>
  </div>;
}
