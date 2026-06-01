import { ReportPage } from "@/components/report-page";

export default async function AegisCreditReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ReportPage
      assessmentId={id}
      backHref="/aegis-credit"
      moduleName="Aegis-Credit"
      moduleSlug="aegis-credit"
    />
  );
}
