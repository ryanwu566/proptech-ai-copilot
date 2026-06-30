import { PropertyCaseCommandCenter } from "@/components/property-case-command-center";

export default async function PropertyCaseCommandCenterPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <PropertyCaseCommandCenter caseId={decodeURIComponent(caseId)} />;
}
