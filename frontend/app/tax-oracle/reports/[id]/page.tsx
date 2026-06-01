import { ReportPage } from "@/components/report-page";

export default async function TaxOracleReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ReportPage
      assessmentId={id}
      backHref="/tax-oracle"
      moduleName="TaxOracle"
      moduleSlug="tax-oracle"
    />
  );
}
