import type { MapLegendItemViewModel } from "@/lib/vnext-map-preview/contract";
import { ObservationStatusBadge } from "./status-badge";
import styles from "./map-workspace.module.css";

export function MapLegend({ items }: { items: readonly MapLegendItemViewModel[] }) {
  return (
    <section className={styles.legend} aria-labelledby="map-legend-title" data-testid="map-legend">
      <div className={styles.legendHeading}>
        <h3 id="map-legend-title">Visible evidence</h3>
        <span>{items.length} layers</span>
      </div>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item.layerKey} data-testid={`legend-${item.layerKey}`}>
              <span
                className={`${styles.legendLine} ${styles[`line_${item.lineStyle}`]}`}
                style={{ "--layer-color": item.color } as React.CSSProperties}
                aria-hidden="true"
              />
              <span className={styles.legendCopy}>
                <strong>{item.title}</strong>
                <small>{item.attribution}</small>
              </span>
              <ObservationStatusBadge status={item.observationStatus} />
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.emptyLegend}>No layers are visible. This does not mean no features, no constraints, or no risk.</p>
      )}
      <p className={styles.legendAttribution}>Authority: Synthetic · Attribution is shown per observation</p>
    </section>
  );
}
