import type { SpatialObservationStatus } from "@/lib/vnext-map-preview/contract";
import styles from "./map-workspace.module.css";

const labels: Record<SpatialObservationStatus, string> = {
  present: "Observed",
  unknown: "Unknown",
  unavailable: "Provider unavailable",
  partial_coverage: "Partial coverage",
  stale: "Stale",
  no_match: "No match",
};

export function observationStatusLabel(status: SpatialObservationStatus): string {
  return labels[status];
}

export function ObservationStatusBadge({ status }: { status: SpatialObservationStatus }) {
  return (
    <span className={`${styles.statusBadge} ${styles[`status_${status}`]}`} data-observation-status={status}>
      <span className={styles.statusDot} aria-hidden="true" />
      {labels[status]}
    </span>
  );
}
