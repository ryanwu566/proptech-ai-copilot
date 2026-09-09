"use client";

import { useEffect, useState } from "react";
import type { MapLayerViewModel, ParcelFeatureViewModel } from "@/lib/vnext-map-preview/contract";
import { ObservationStatusBadge } from "./status-badge";
import styles from "./map-workspace.module.css";

function EvidenceItem({ layer, isSelected }: { layer: MapLayerViewModel; isSelected: boolean }) {
  const [expanded, setExpanded] = useState(isSelected);

  useEffect(() => {
    if (isSelected) setExpanded(true);
  }, [isSelected]);

  return (
    <article
      className={`${styles.evidenceItem} ${isSelected ? styles.evidenceItemSelected : ""}`}
      data-testid={`evidence-state-${layer.status}`}
      data-evidence-id={layer.evidenceId}
    >
      <div className={styles.evidenceItemTop}>
        <span className={styles.evidenceIndex} aria-hidden="true">{layer.title.slice(0, 2).toUpperCase()}</span>
        <div>
          <h3>{layer.title}</h3>
          <p>{layer.summary}</p>
        </div>
      </div>
      <div className={styles.evidenceBadges}>
        <ObservationStatusBadge status={layer.status} />
        <span className={styles.authorityBadge}>Synthetic authority</span>
      </div>
      <button
        type="button"
        className={styles.disclosureButton}
        aria-expanded={expanded}
        aria-controls={`evidence-details-${layer.key}`}
        onClick={() => setExpanded((current) => !current)}
      >
        {expanded ? "Hide evidence details" : "Show evidence details"}
        <span aria-hidden="true">{expanded ? "−" : "+"}</span>
      </button>
      {expanded ? (
        <dl className={styles.evidenceDetails} id={`evidence-details-${layer.key}`}>
          <div><dt>Source</dt><dd>{layer.sourceLabel}</dd></div>
          <div><dt>Coverage</dt><dd>{layer.coverageLabel}</dd></div>
          <div><dt>Observed</dt><dd>{new Date(layer.observedAt).toLocaleString("en-GB", { timeZone: "Asia/Taipei", dateStyle: "medium", timeStyle: "short" })}</dd></div>
          <div><dt>Evidence ID</dt><dd>{layer.evidenceId}</dd></div>
          <div className={styles.limitationRow}><dt>Limitation</dt><dd>{layer.limitation}</dd></div>
          <div className={styles.attributionRow}><dt>Attribution</dt><dd>{layer.attribution}</dd></div>
        </dl>
      ) : null}
    </article>
  );
}

export function EvidencePanel({
  layers,
  selectedParcel,
  selectedLayerKeys,
  limitations,
}: {
  layers: readonly MapLayerViewModel[];
  selectedParcel: ParcelFeatureViewModel | null;
  selectedLayerKeys: ReadonlySet<string>;
  limitations: readonly string[];
}) {
  const selectedEvidenceId = selectedParcel?.evidenceId ?? null;
  const selectedLayerEvidenceId = selectedParcel ? layers.find((layer) => layer.key === selectedParcel.layerKey)?.evidenceId : null;

  return (
    <aside className={styles.evidencePanel} aria-labelledby="evidence-panel-title" data-testid="evidence-panel">
      <div className={styles.panelHeading}>
        <div>
          <p className={styles.panelKicker}>Provenance rail</p>
          <h2 id="evidence-panel-title">Evidence & limitations</h2>
        </div>
        <span className={styles.countLabel}>{layers.length} checks</span>
      </div>

      {selectedParcel ? (
        <section className={styles.selectionSummary} aria-label="Selected feature" data-testid="selected-feature-summary">
          <p>Inspection focus</p>
          <h3>{selectedParcel.label}</h3>
          <span className={selectedParcel.relationship === "candidate" ? styles.candidatePill : styles.confirmedPill}>
            {selectedParcel.relationship === "candidate" ? "Candidate — not confirmed" : "Reviewed working geometry"}
          </span>
          <dl>
            <div><dt>Why shown</dt><dd>{selectedParcel.matchBasis}</dd></div>
            <div><dt>Source</dt><dd>{selectedParcel.sourceLabel}</dd></div>
            <div><dt>Feature evidence</dt><dd>{selectedEvidenceId}</dd></div>
          </dl>
          <p className={styles.selectionBoundary}>Inspection only. This selection creates no PropertyEntity, CasePropertyLink, confirmation, ownership claim, or safety finding.</p>
        </section>
      ) : (
        <section className={styles.noSelection} aria-label="No feature selected" data-testid="no-feature-selected">
          <span aria-hidden="true">⌖</span>
          <div><h3>No feature selected</h3><p>Choose a parcel on the map or in Parcel review to inspect its evidence.</p></div>
        </section>
      )}

      <div className={styles.safetyBoundary} role="note" data-testid="empty-layer-boundary">
        <strong>Unknown-safe reading</strong>
        <p>An empty layer never means “safe” or “no risk.” Check coverage, freshness, and source limitations below.</p>
      </div>

      <div className={styles.evidenceList} aria-label="Spatial observations">
        {layers.map((layer) => (
          <div key={layer.key} className={!selectedLayerKeys.has(layer.key) ? styles.hiddenLayerEvidence : ""}>
            {!selectedLayerKeys.has(layer.key) ? <span className={styles.visibilityNote}>Layer hidden · evidence retained</span> : null}
            <EvidenceItem layer={layer} isSelected={layer.evidenceId === selectedLayerEvidenceId} />
          </div>
        ))}
      </div>

      <section className={styles.limitations} aria-labelledby="workspace-limitations-title">
        <h3 id="workspace-limitations-title">Workspace limitations</h3>
        <ul>{limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      </section>
    </aside>
  );
}
