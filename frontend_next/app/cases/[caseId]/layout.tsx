import type { ReactNode } from "react";
import { WorkspaceProvider } from "@/components/workspace/workspace-provider";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";

export default async function PropertyCaseLayout({ children, params }: { children: ReactNode; params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <WorkspaceProvider caseId={decodeURIComponent(caseId)}><WorkspaceShell>{children}</WorkspaceShell></WorkspaceProvider>;
}
