import type { TerrainRiskResult } from "@/lib/api";
import { buildTerrainReferenceEvidence, type TerrainReferenceState } from "@/lib/terrain-reference-evidence";

// Pure, side-effect-free terrain safety classification for the decision/risk
// gate. It intentionally REUSES the existing terrain reference evidence state
// machine (buildTerrainReferenceEvidence) and the provider's overall.level; it
// does NOT introduce new provider mapping, hazard scoring, or numeric risk
// values. Provider/source semantics live in terrain-reference-evidence.ts and
// the backend terrain services and are not changed here.

export type TerrainSafetyClass =
  | "known_low" // sufficient evidence, known low risk -> positive may proceed
  | "known_high" // sufficient evidence, known high risk -> risk clarification
  | "caution" // some evidence but not an all-clear (medium / partial / limited / no_match)
  | "incomplete" // unknown / unavailable / error / not_assessed / absent -> uncertainty
  | "absent"; // no terrain input provided at all

// Reference states that represent materially incomplete evidence. Mirrors the
// BLOCKING_STATES concept in terrain-reference-evidence.ts (kept local to avoid
// changing that module's export surface / provider semantics).
const INCOMPLETE_REFERENCE_STATES = new Set<TerrainReferenceState>([
  "unknown",
  "unavailable",
  "error",
  "not_assessed",
]);

// Reference states that carry some evidence yet are insufficient for an
// unrestricted all-clear.
const CAUTION_REFERENCE_STATES = new Set<TerrainReferenceState>([
  "partial",
  "limited",
  "no_match",
]);

export function classifyTerrainSafety(result?: TerrainRiskResult | null): TerrainSafetyClass {
  if (!result) return "absent";

  const referenceStatus = buildTerrainReferenceEvidence(result).status;
  const level = result.overall?.level;
  const dataQuality = result.data_quality?.status;

  // Known material risk takes priority over completeness: if the provider
  // actually determined a high hazard level with usable data, treat as known
  // high regardless of individual layer gaps.
  if (level === "high" && dataQuality !== "unavailable" && !INCOMPLETE_REFERENCE_STATES.has(referenceStatus)) {
    return "known_high";
  }

  // Materially incomplete evidence -> uncertainty (never "safe").
  if (
    dataQuality === "unavailable"
    || level === "unknown"
    || INCOMPLETE_REFERENCE_STATES.has(referenceStatus)
  ) {
    return "incomplete";
  }

  // Some evidence, but not an unrestricted all-clear.
  if (level === "medium" || dataQuality === "limited" || CAUTION_REFERENCE_STATES.has(referenceStatus)) {
    return "caution";
  }

  // Sufficient evidence and known low risk (referenceStatus === "available",
  // level low, data quality good).
  if (level === "low" && referenceStatus === "available") {
    return "known_low";
  }

  // Anything not positively established as low-and-available is treated as
  // caution: never silently all-clear.
  return "caution";
}

// True only when terrain evidence positively supports an all-clear reading.
export function terrainAllowsAllClear(result?: TerrainRiskResult | null): boolean {
  return classifyTerrainSafety(result) === "known_low";
}

// True when terrain is materially incomplete (uncertainty) or entirely absent.
export function terrainIsMateriallyIncomplete(result?: TerrainRiskResult | null): boolean {
  const klass = classifyTerrainSafety(result);
  return klass === "incomplete" || klass === "absent";
}
