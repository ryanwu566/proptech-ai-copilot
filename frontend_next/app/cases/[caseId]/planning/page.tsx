import { PropertyCaseCommandCenter } from "@/components/property-case-command-center";

export default async function LegacyCasePlanningPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <div data-testid="legacy-case-workbench">
    <PropertyCaseCommandCenter caseId={decodeURIComponent(caseId)} embedded showPrintAction />
  </div>;
}
