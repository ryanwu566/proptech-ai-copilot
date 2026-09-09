import type { MapLayerViewModel } from "@/lib/vnext-map-preview/contract";
import { ObservationStatusBadge } from "./status-badge";
import styles from "./map-workspace.module.css";

export function LayerControls({
  layers,
  selectedLayerKeys,
  onToggle,
}: {
  layers: readonly MapLayerViewModel[];
  selectedLayerKeys: ReadonlySet<string>;
  onToggle: (layerKey: string) => void;
}) {
  return (
    <section className={styles.controlPanel} aria-labelledby="layer-control-title">
      <div className={styles.panelHeading}>
        <div>
          <p className={styles.panelKicker}>Investigation controls</p>
          <h2 id="layer-control-title">Layers</h2>
        </div>
        <span className={styles.countLabel}>{selectedLayerKeys.size} visible</span>
      </div>
      <p className={styles.panelIntro}>Turn evidence views on or off. Layer visibility changes presentation only.</p>
      <div className={styles.layerList}>
        {layers.map((layer) => (
          <label className={styles.layerRow} key={layer.key} data-testid={`layer-control-${layer.key}`}>
            <input
              type="checkbox"
              checked={selectedLayerKeys.has(layer.key)}
              onChange={() => onToggle(layer.key)}
            />
            <span className={styles.layerControlCopy}>
              <span className={styles.layerTitleLine}>
                <span className={styles.layerSwatch} style={{ "--layer-color": layer.color } as React.CSSProperties} aria-hidden="true" />
                <strong>{layer.title}</strong>
              </span>
              <span className={styles.layerMeta}>{layer.category} · {layer.sourceLabel}</span>
              <ObservationStatusBadge status={layer.status} />
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}
