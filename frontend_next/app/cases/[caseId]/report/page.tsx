import type { Metadata } from "next";
import { ReportView } from "@/components/evidence/report-view";
export const metadata: Metadata = { title: "案件證據報告 | PropTech AI Copilot" };
export default async function CaseReportPage({ params }: { params: Promise<{ caseId: string }> }) { const { caseId } = await params; return <ReportView key={caseId} caseId={caseId} />; }
