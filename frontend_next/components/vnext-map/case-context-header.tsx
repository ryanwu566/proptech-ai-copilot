import type { CaseContextViewModel } from "@/lib/vnext-map-preview/contract";
import styles from "./map-workspace.module.css";

export function CaseContextHeader({ context }: { context: CaseContextViewModel }) {
  return (
    <header className={styles.contextHeader} aria-labelledby="map-workspace-title">
      <div className={styles.previewBar}>
        <div className={styles.previewLabels}>
          <span className={styles.devBadge}>Development-only preview</span>
          <span className={styles.syntheticBadge}>Synthetic / Demo data</span>
        </div>
        <span className={styles.caseReference}>Case ref · {context.caseId}</span>
      </div>

      <div className={styles.contextMain}>
        <div className={styles.contextTitleBlock}>
          <p className={styles.eyebrow}>Property Decision Intelligence / Map Workspace</p>
          <h1 id="map-workspace-title">Investigate location evidence in Case context</h1>
          <p className={styles.lede}>
            Inspect parcel possibilities and spatial observations together—without turning a map click into an identity or safety decision.
          </p>
        </div>
        <a className={styles.primaryAction} href="#parcel-review">Review parcel candidates <span aria-hidden="true">→</span></a>
      </div>

      <dl className={styles.contextGrid} aria-label="Case and property context">
        <div>
          <dt>Case</dt>
          <dd>{context.caseTitle}</dd>
          <span>{context.purpose}</span>
        </div>
        <div>
          <dt>Property context</dt>
          <dd>{context.selectedPropertyEntity?.displayLabel ?? "No PropertyEntity selected"}</dd>
          <span>{context.selectedPropertyEntity?.locationSummary ?? "Case-level investigation"}</span>
        </div>
        <div>
          <dt>Review stage</dt>
          <dd>{context.reviewStage}</dd>
          <span>{context.reviewOwner}</span>
        </div>
        <div>
          <dt>Workspace</dt>
          <dd>{context.workspaceId}</dd>
          <span>Local demo context</span>
        </div>
      </dl>
    </header>
  );
}
