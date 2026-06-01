import { ReportPage } from "@/components/report-page";

export default async function LexPropReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ReportPage
      assessmentId={id}
      backHref="/lex-prop"
      moduleName="LexProp"
      moduleSlug="lex-prop"
    />
  );
}
