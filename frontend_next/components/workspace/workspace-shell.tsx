"use client";

import type { ReactNode } from "react";
import { PropertyContextHeader } from "./property-context-header";
import { useWorkspace } from "./workspace-provider";
import { WorkspaceNavigation } from "./workspace-navigation";
import styles from "./workspace-shell.module.css";

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const workspace = useWorkspace();
  return <div className={styles.shell}>
    <PropertyContextHeader />
    <div className={styles.body}>
      <aside className={styles.rail}><WorkspaceNavigation caseId={workspace.caseId} /></aside>
      <main className={styles.content} id="main-content">{children}</main>
    </div>
  </div>;
}
