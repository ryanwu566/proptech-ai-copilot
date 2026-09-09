import type { ReportSectionModel } from "@/lib/vnext-report";
import { ReportStatusBadge } from "./report-status-badge";
import styles from "./decision-report-presentation.module.css";

export function ReportSectionCard({ section }: { section: ReportSectionModel }) {
  return <section className={styles.analysisCard} data-testid={`report-section-${section.id}`} aria-labelledby={`report-section-${section.id}-title`}>
    <div className={styles.cardHeading}>
      <div>
        <p className={styles.eyebrow}>{section.eyebrow}</p>
        <h3 id={`report-section-${section.id}-title`}>{section.title}</h3>
      </div>
      <ReportStatusBadge status={section.status} />
    </div>
    <p className={styles.stateSummary}>{section.summary}</p>
    <dl className={styles.metricGrid}>
      {section.metrics.map((metric) => <div className={styles.metric} key={metric.label}>
        <dt>{metric.label}</dt>
        <dd className={metric.value === null ? styles.missingValue : undefined}>{metric.value ?? "未提供（不等於 0）"}</dd>
        {metric.note && <span>{metric.note}</span>}
      </div>)}
    </dl>
    <div className={styles.cardBodyColumns}>
      <div>
        <h4>目前觀察</h4>
        <ul>{section.observations.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>
      <div>
        <h4>限制與待確認</h4>
        <ul>{section.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>
    </div>
    <p className={styles.evidenceLinks}>
      證據識別碼：{section.evidenceIds.length ? section.evidenceIds.join("、") : "未提供／尚無可連結證據"}
    </p>
  </section>;
}
