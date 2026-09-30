import { redirect } from "next/navigation";

export default async function PropertyCaseCommandCenterPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  redirect(`/cases/${encodeURIComponent(decodeURIComponent(caseId))}/overview`);
}
