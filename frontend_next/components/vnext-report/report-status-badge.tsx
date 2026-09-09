import { evidenceStatusLabel } from "@/lib/vnext-report";
import type { ReportEvidenceStatus } from "@/lib/vnext-report";
import styles from "./decision-report-presentation.module.css";

export function ReportStatusBadge({ status }: { status: ReportEvidenceStatus }) {
  return <span className={`${styles.statusBadge} ${styles[`status_${status}`]}`} data-report-status={status}>{evidenceStatusLabel(status)}</span>;
}
