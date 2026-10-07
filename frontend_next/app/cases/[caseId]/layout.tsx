import type { ReactNode } from "react";
import { CaseRouteLayout } from "@/components/workspace/case-route-layout";

export default async function PropertyCaseLayout({ children, params }: { children: ReactNode; params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <CaseRouteLayout caseId={caseId}>{children}</CaseRouteLayout>;
}
