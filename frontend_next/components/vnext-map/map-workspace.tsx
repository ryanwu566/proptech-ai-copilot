"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { MapFeatureSelectionViewModel, MapWorkspaceViewModel, ParcelFeatureViewModel } from "@/lib/vnext-map-preview/contract";
import { legendForLayers } from "@/lib/vnext-map-preview/contract";
import { CaseContextHeader } from "./case-context-header";
import { EvidencePanel } from "./evidence-panel";
import { InvestigationMap } from "./investigation-map";
import { LayerControls } from "./layer-controls";
import { ParcelReviewList } from "./parcel-review-list";
import styles from "./map-workspace.module.css";

export function MapWorkspace({ workspace }: { workspace: MapWorkspaceViewModel }) {
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [selectedLayerKeys, setSelectedLayerKeys] = useState<Set<string>>(
    () => new Set(workspace.layers.filter((layer) => layer.selectedByDefault).map((layer) => layer.key)),
  );
  const [selection, setSelection] = useState<MapFeatureSelectionViewModel | null>(null);
  const [zoom, setZoom] = useState(workspace.viewport.zoom);
  const [isLoading, setIsLoading] = useState(false);
  const [announcement, setAnnouncement] = useState("Map workspace ready. No parcel is selected.");

  useEffect(() => () => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
  }, []);

  const allParcels = useMemo(
    () => [...workspace.candidateParcels, ...workspace.confirmedParcels],
    [workspace.candidateParcels, workspace.confirmedParcels],
  );
  const selectedParcel = selection ? allParcels.find((parcel) => parcel.geometryId === selection.featureId) ?? null : null;
  const visibleLayers = workspace.layers.filter((layer) => selectedLayerKeys.has(layer.key));
  const legend = legendForLayers(visibleLayers);
  const needsChecking = workspace.layers.filter((layer) => layer.status !== "present").length;

  function selectParcel(parcel: ParcelFeatureViewModel) {
    const featureType = parcel.relationship === "candidate" ? "candidate_parcel" : "confirmed_parcel";
    if (!selectedLayerKeys.has(parcel.layerKey)) {
      setSelectedLayerKeys((current) => new Set(current).add(parcel.layerKey));
    }
    setSelection({
      featureId: parcel.geometryId,
      featureType,
      layerKey: parcel.layerKey,
      evidenceId: parcel.evidenceId,
    });
    setAnnouncement(
      parcel.relationship === "candidate"
        ? `${parcel.label} selected for inspection only. Parcel identity remains unconfirmed.${selectedLayerKeys.has(parcel.layerKey) ? "" : " Its layer was restored."}`
        : `${parcel.label} selected for inspection. It remains a reviewed working geometry, not a legal boundary.`,
    );
  }

  function toggleLayer(layerKey: string) {
    const willBeVisible = !selectedLayerKeys.has(layerKey);
    setSelectedLayerKeys((current) => {
      const next = new Set(current);
      if (next.has(layerKey)) next.delete(layerKey);
      else next.add(layerKey);
      return next;
    });
    if (!willBeVisible && selection?.layerKey === layerKey) {
      setSelection(null);
      setAnnouncement("The selected feature was cleared because its layer was hidden. No record was changed.");
    } else {
      const title = workspace.layers.find((layer) => layer.key === layerKey)?.title ?? layerKey;
      setAnnouncement(`${title} layer ${willBeVisible ? "shown" : "hidden"}. Evidence remains available in the rail.`);
    }
  }

  function changeZoom(change: number) {
    setZoom((current) => Math.min(24, Math.max(0, current + change)));
  }

  function refreshDemo() {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    setIsLoading(true);
    setAnnouncement("Loading deterministic synthetic observations.");
    refreshTimer.current = setTimeout(() => {
      setIsLoading(false);
      setAnnouncement("Synthetic observations reloaded. No external source was contacted.");
      refreshTimer.current = null;
    }, 700);
  }

  return (
    <main className={styles.page} data-testid="map-workspace-shell">
      <CaseContextHeader context={workspace.context} />

      <section className={styles.trustStrip} aria-label="Preview trust boundary">
        <span className={styles.trustIcon} aria-hidden="true">S</span>
        <div>
          <strong>Synthetic evidence boundary</strong>
          <p>All parcels, layers, identifiers, dates, and sources on this page are deterministic demo fixtures. No live API, external map tile, production session, or customer data is used.</p>
        </div>
        <button type="button" onClick={refreshDemo} disabled={isLoading} data-testid="refresh-demo-observations">
          {isLoading ? "Loading…" : "Reload demo states"}
        </button>
      </section>

      <div className={styles.workspaceGrid}>
        <div className={styles.leftRail}>
          <ParcelReviewList
            candidates={workspace.candidateParcels}
            confirmed={workspace.confirmedParcels}
            selectedGeometryId={selection?.featureId ?? null}
            onSelect={selectParcel}
          />
          <LayerControls layers={workspace.layers} selectedLayerKeys={selectedLayerKeys} onToggle={toggleLayer} />
        </div>

        <div className={styles.mapColumn}>
          <InvestigationMap
            candidates={workspace.candidateParcels}
            confirmed={workspace.confirmedParcels}
            layers={workspace.layers}
            selectedLayerKeys={selectedLayerKeys}
            selectedGeometryId={selection?.featureId ?? null}
            viewport={workspace.viewport}
            zoom={zoom}
            isLoading={isLoading}
            onSelectParcel={selectParcel}
            onZoom={changeZoom}
          />

          <section className={styles.knowledgeSummary} aria-labelledby="knowledge-summary-title">
            <div>
              <p className={styles.panelKicker}>Decision posture</p>
              <h2 id="knowledge-summary-title">What is known—and what still needs checking</h2>
            </div>
            <div className={styles.summaryMetrics}>
              <div><strong>{workspace.layers.length - needsChecking}</strong><span>observed layers</span></div>
              <div><strong>{needsChecking}</strong><span>need follow-up</span></div>
              <div><strong>{workspace.candidateParcels.length}</strong><span>parcel candidates</span></div>
            </div>
            <p>Next action: review the candidate evidence, resolve unavailable and incomplete coverage, then use the separate human identity-confirmation workflow if warranted.</p>
          </section>
        </div>

        <EvidencePanel
          layers={workspace.layers}
          selectedParcel={selectedParcel}
          selectedLayerKeys={selectedLayerKeys}
          limitations={workspace.limitations}
        />
      </div>

      <footer className={styles.previewFooter}>
        <span>Component development preview · no persistence</span>
        <span>Legend entries: {legend.length} · Observation references: {workspace.observationIds.length}</span>
      </footer>
      <p className={styles.srOnly} role="status" aria-live="polite">{announcement}</p>
    </main>
  );
}
