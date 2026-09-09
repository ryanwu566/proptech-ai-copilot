import type { KeyboardEvent } from "react";
import type { MapLayerViewModel, MapViewportViewModel, ParcelFeatureViewModel } from "@/lib/vnext-map-preview/contract";
import { MapLegend } from "./map-legend";
import styles from "./map-workspace.module.css";

function polygonPoints(parcel: ParcelFeatureViewModel): string {
  return parcel.polygon.map(([x, y]) => `${x},${y}`).join(" ");
}

function parcelKeyboardSelect(event: KeyboardEvent<SVGPolygonElement>, parcel: ParcelFeatureViewModel, onSelect: (parcel: ParcelFeatureViewModel) => void) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  onSelect(parcel);
}

function ParcelPolygon({
  parcel,
  selectedGeometryId,
  onSelect,
}: {
  parcel: ParcelFeatureViewModel;
  selectedGeometryId: string | null;
  onSelect: (parcel: ParcelFeatureViewModel) => void;
}) {
  const isCandidate = parcel.relationship === "candidate";
  const selected = parcel.geometryId === selectedGeometryId;
  return (
    <polygon
      points={polygonPoints(parcel)}
      className={`${styles.parcelPolygon} ${isCandidate ? styles.candidatePolygon : styles.confirmedPolygon} ${selected ? styles.selectedPolygon : ""}`}
      role="button"
      tabIndex={0}
      aria-label={`${parcel.label}. ${isCandidate ? "Candidate parcel, inspection only" : "Reviewed working geometry"}. ${parcel.areaLabel}`}
      aria-pressed={selected}
      data-testid={`map-feature-${parcel.geometryId}`}
      onClick={() => onSelect(parcel)}
      onKeyDown={(event) => parcelKeyboardSelect(event, parcel, onSelect)}
    />
  );
}

export function InvestigationMap({
  candidates,
  confirmed,
  layers,
  selectedLayerKeys,
  selectedGeometryId,
  viewport,
  zoom,
  isLoading,
  onSelectParcel,
  onZoom,
}: {
  candidates: readonly ParcelFeatureViewModel[];
  confirmed: readonly ParcelFeatureViewModel[];
  layers: readonly MapLayerViewModel[];
  selectedLayerKeys: ReadonlySet<string>;
  selectedGeometryId: string | null;
  viewport: MapViewportViewModel;
  zoom: number;
  isLoading: boolean;
  onSelectParcel: (parcel: ParcelFeatureViewModel) => void;
  onZoom: (change: number) => void;
}) {
  const visibleLayers = layers.filter((layer) => selectedLayerKeys.has(layer.key));
  const showCandidates = selectedLayerKeys.has("parcel_candidates");
  const showConfirmed = selectedLayerKeys.has("confirmed_parcel");

  return (
    <section className={styles.mapPanel} aria-labelledby="investigation-map-title" aria-busy={isLoading}>
      <div className={styles.mapHeading}>
        <div>
          <p className={styles.panelKicker}>Spatial investigation surface</p>
          <h2 id="investigation-map-title">Evidence map</h2>
        </div>
        <div className={styles.mapMode} aria-label="Map mode">
          <span aria-hidden="true" /> Investigation
        </div>
      </div>

      <div className={styles.mapFrame} data-testid="investigation-map">
        <svg viewBox="0 0 760 500" role="group" aria-label="Synthetic parcel and evidence map. Parcel shapes are keyboard selectable.">
          <defs>
            <pattern id="demo-map-grid" width="38" height="38" patternUnits="userSpaceOnUse">
              <path d="M 38 0 L 0 0 0 38" fill="none" stroke="#c8d1ca" strokeWidth="0.7" />
            </pattern>
            <pattern id="partial-hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="12" stroke="#167e9b" strokeWidth="3" opacity="0.24" />
            </pattern>
            <filter id="selected-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#f6c65b" floodOpacity="0.9" />
            </filter>
          </defs>
          <rect width="760" height="500" fill="#e9eee9" />
          <rect width="760" height="500" fill="url(#demo-map-grid)" />
          <path d="M -20 88 C 160 64, 290 78, 780 18" className={styles.mapRoadWide} />
          <path d="M -20 88 C 160 64, 290 78, 780 18" className={styles.mapRoadCenter} />
          <path d="M 52 520 C 176 350, 292 335, 806 292" className={styles.mapRoadWide} />
          <path d="M 52 520 C 176 350, 292 335, 806 292" className={styles.mapRoadCenter} />
          <path d="M 630 -20 C 605 130, 642 302, 704 530" className={styles.mapLane} />

          {selectedLayerKeys.has("planning_reference") ? (
            <g data-testid="map-overlay-planning_reference" aria-label="Synthetic planning reference overlay">
              <path d="M 0 188 L 760 108 L 760 190 L 0 270 Z" fill="#d5893f" opacity="0.13" />
              <path d="M 0 228 L 760 148" stroke="#c4782f" strokeWidth="3" opacity="0.7" />
            </g>
          ) : null}
          {selectedLayerKeys.has("access_context") ? (
            <g data-testid="map-overlay-access_context" aria-label="Partial synthetic access context overlay">
              <path d="M 118 454 C 250 410, 330 356, 498 320" stroke="#167e9b" strokeWidth="8" strokeDasharray="14 9" fill="none" opacity="0.78" />
              <rect x="570" y="0" width="190" height="500" fill="url(#partial-hatch)" />
            </g>
          ) : null}
          {selectedLayerKeys.has("soil_history") ? (
            <g data-testid="map-overlay-soil_history" aria-label="Stale synthetic soil history overlay">
              <circle cx="520" cy="172" r="54" fill="#8d6e4a" opacity="0.14" />
              <circle cx="520" cy="172" r="54" fill="none" stroke="#8d6e4a" strokeWidth="3" strokeDasharray="8 8" />
            </g>
          ) : null}

          {showCandidates ? candidates.map((parcel) => (
            <ParcelPolygon key={parcel.geometryId} parcel={parcel} selectedGeometryId={selectedGeometryId} onSelect={onSelectParcel} />
          )) : null}
          {showConfirmed ? confirmed.map((parcel) => (
            <ParcelPolygon key={parcel.geometryId} parcel={parcel} selectedGeometryId={selectedGeometryId} onSelect={onSelectParcel} />
          )) : null}

          <g className={styles.mapLabels} aria-hidden="true">
            <text x="36" y="52">DEMO GRID · NORTH</text>
            <text x="470" y="456">SYNTHETIC REFERENCE SURFACE</text>
          </g>
        </svg>

        <div className={styles.mapControls} aria-label="Map viewport controls">
          <button type="button" onClick={() => onZoom(1)} aria-label="Zoom in">+</button>
          <button type="button" onClick={() => onZoom(-1)} aria-label="Zoom out">−</button>
        </div>
        <div className={styles.compass} aria-label="North is up"><span>N</span><i aria-hidden="true" /></div>
        <div className={styles.scaleBar} aria-hidden="true"><span />50 m</div>
        {isLoading ? (
          <div className={styles.loadingOverlay} role="status" aria-live="polite" data-testid="map-loading-state">
            <span className={styles.loadingSpinner} aria-hidden="true" />
            <strong>Loading synthetic observations…</strong>
            <small>No provider or network request is made.</small>
          </div>
        ) : null}
      </div>

      <div className={styles.mapFooter}>
        <span>EPSG:4326 · {viewport.centerLatitude.toFixed(4)}, {viewport.centerLongitude.toFixed(4)}</span>
        <span>Zoom {zoom} · Synthetic base grid</span>
      </div>
      <p className={styles.keyboardHint}>Keyboard: Tab to a parcel shape, then press Enter or Space to inspect it.</p>
      <MapLegend items={visibleLayers.map((layer) => ({
        layerKey: layer.key,
        title: layer.title,
        authority: layer.authority,
        observationStatus: layer.status,
        attribution: layer.attribution,
        color: layer.color,
        lineStyle: layer.lineStyle,
      }))} />
    </section>
  );
}
