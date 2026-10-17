import type { Metadata } from "next";
import { DocumentEvidencePage } from "@/components/evidence/document-evidence-page";
export const metadata: Metadata = { title: "Evidence & Citations | PropTech AI Copilot" };
export default async function CaseEvidencePage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <DocumentEvidencePage key={caseId} caseId={caseId} />;
}
