import type { ParcelFeatureViewModel } from "@/lib/vnext-map-preview/contract";
import styles from "./map-workspace.module.css";

function ParcelCard({
  parcel,
  isSelected,
  onSelect,
}: {
  parcel: ParcelFeatureViewModel;
  isSelected: boolean;
  onSelect: (parcel: ParcelFeatureViewModel) => void;
}) {
  const isCandidate = parcel.relationship === "candidate";
  return (
    <button
      type="button"
      className={`${styles.parcelCard} ${isSelected ? styles.parcelCardSelected : ""}`}
      onClick={() => onSelect(parcel)}
      aria-pressed={isSelected}
      data-testid={`parcel-card-${parcel.geometryId}`}
    >
      <span className={styles.parcelCardTop}>
        <span className={isCandidate ? styles.candidateMark : styles.confirmedMark} aria-hidden="true" />
        <span>
          <strong>{parcel.label}</strong>
          <small>{isCandidate ? "Candidate · inspect only" : "Reviewed · working geometry"}</small>
        </span>
        <span className={styles.inspectLabel}>{isSelected ? "Inspecting" : "Inspect"}</span>
      </span>
      <span className={styles.parcelDetails}>
        <span>{parcel.areaLabel}</span>
        {parcel.confidenceLabel ? <span>{parcel.confidenceLabel}</span> : null}
      </span>
    </button>
  );
}

export function ParcelReviewList({
  candidates,
  confirmed,
  selectedGeometryId,
  onSelect,
}: {
  candidates: readonly ParcelFeatureViewModel[];
  confirmed: readonly ParcelFeatureViewModel[];
  selectedGeometryId: string | null;
  onSelect: (parcel: ParcelFeatureViewModel) => void;
}) {
  return (
    <section className={styles.parcelReview} id="parcel-review" aria-labelledby="parcel-review-title">
      <div className={styles.panelHeading}>
        <div>
          <p className={styles.panelKicker}>Identity boundary</p>
          <h2 id="parcel-review-title">Parcel review</h2>
        </div>
        <span className={styles.countLabel}>{candidates.length} candidates</span>
      </div>
      <p className={styles.panelIntro}>Selection sets the inspection focus. It does not confirm or attach a parcel.</p>
      <div className={styles.parcelGroup}>
        <h3>Current candidates</h3>
        {candidates.map((parcel) => (
          <ParcelCard key={parcel.geometryId} parcel={parcel} isSelected={selectedGeometryId === parcel.geometryId} onSelect={onSelect} />
        ))}
      </div>
      <div className={styles.parcelGroup}>
        <h3>Separate reviewed geometry</h3>
        {confirmed.map((parcel) => (
          <ParcelCard key={parcel.geometryId} parcel={parcel} isSelected={selectedGeometryId === parcel.geometryId} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}
