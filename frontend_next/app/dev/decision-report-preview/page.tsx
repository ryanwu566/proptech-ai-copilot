import { notFound } from "next/navigation";
import { DecisionReportPresentation } from "@/components/vnext-report";
import { getReportPreviewScenario, REPORT_PREVIEW_SCENARIOS } from "@/lib/vnext-report-preview";
import styles from "./preview-page.module.css";

export const dynamic = "force-dynamic";

export default async function DecisionReportPreviewPage({ searchParams }: { searchParams: Promise<{ scenario?: string | string[] }> }) {
  if (process.env.NODE_ENV === "production") notFound();
  const params = await searchParams;
  const scenarioId = Array.isArray(params.scenario) ? params.scenario[0] : params.scenario;
  const selected = getReportPreviewScenario(scenarioId);

  return <main className={styles.previewPage}>
    <section className={styles.previewIntro} data-preview-chrome>
      <p>LOCAL DEVELOPMENT ONLY</p>
      <h1>決策報告呈現測試台</h1>
      <p>全部情境均為合成固定資料，不會連線至資料庫、即時提供者或客戶案件。</p>
      <nav aria-label="合成報告情境">
        {REPORT_PREVIEW_SCENARIOS.map((scenario) => <a key={scenario.id} href={`?scenario=${encodeURIComponent(scenario.id)}`} aria-current={scenario.id === selected.id ? "page" : undefined}>
          <b>{scenario.title}</b><span>{scenario.description}</span>
        </a>)}
      </nav>
    </section>
    <DecisionReportPresentation report={selected.report} />
  </main>;
}
