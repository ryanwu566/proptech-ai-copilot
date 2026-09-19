import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ProfessionalWorkspaceShell, type WorkspaceContextInputState } from "@/components/professional-workspace-shell";
import { VNextAuthGate } from "@/components/vnext-auth-gate";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Professional Workspace | PropTech AI Copilot",
  description: "Feature-gated professional investigation shell with explicit capability readiness.",
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function singleUuid(value: string | string[] | undefined): string | null {
  return typeof value === "string" && UUID_PATTERN.test(value) ? value : null;
}

export default async function ProfessionalWorkspacePage({
  params,
  searchParams,
}: {
  params: Promise<{ caseId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  if (process.env.PROFESSIONAL_WORKSPACE !== "true") notFound();

  const { caseId } = await params;
  if (!UUID_PATTERN.test(caseId)) notFound();

  const query = await searchParams;
  const hasWorkspace = query.workspaceId !== undefined;
  const hasProperty = query.propertyId !== undefined;
  const workspaceId = singleUuid(query.workspaceId);
  const propertyId = singleUuid(query.propertyId);
  const contextState: WorkspaceContextInputState = !hasWorkspace && !hasProperty
    ? "missing"
    : workspaceId && propertyId ? "provided" : "invalid";

  return (
    <VNextAuthGate>
      <ProfessionalWorkspaceShell
        caseId={caseId}
        contextState={contextState}
        workspaceId={contextState === "provided" ? workspaceId : null}
        propertyId={contextState === "provided" ? propertyId : null}
      />
    </VNextAuthGate>
  );
}
