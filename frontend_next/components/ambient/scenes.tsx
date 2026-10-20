import type { AmbientVariant } from "@/lib/ambient/scene-model";

/** Bundled editorial photographs only. No case data, inferred status, labels or decorative diagrams. */
type PhotoScene = { desktop: string; mobile: string };
const photo = (name: string): PhotoScene => ({
  desktop: `/brand/ambient/ambient-${name}-desktop`,
  mobile: `/brand/ambient/ambient-${name}-mobile`,
});

// Home supplies its existing approved responsive picture as children.
// Compare and Report share one neutral neighbourhood, never competing case photos.
export const SCENES: Record<AmbientVariant, PhotoScene | null> = {
  home: null,
  market: photo("market"),
  location: photo("location"),
  risk: photo("risk"),
  overview: photo("overview"),
  finance: photo("finance"),
  decision: photo("decision"),
  compare: photo("overview"),
  report: photo("overview"),
};
