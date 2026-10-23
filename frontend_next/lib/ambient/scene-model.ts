/**
 * Ambient scenes are decorative backgrounds behind product pages. This model is the single source of truth for
 * which route gets which scene and for the shared REVEAL → FOCUS → LOCK → RESOLVE motion timing.
 * It carries no case data: a scene never reads, fetches or stores evidence.
 */
export const AMBIENT_VARIANTS = ["home", "overview", "market", "location", "risk", "finance", "decision", "compare", "report"] as const;
export type AmbientVariant = (typeof AMBIENT_VARIANTS)[number];

export const AMBIENT_PHASES = ["reveal", "focus", "lock", "resolve"] as const;
export type AmbientPhase = (typeof AMBIENT_PHASES)[number];

/** Offsets (ms from mount) at which each phase begins; the scene rests in RESOLVE afterwards. */
export const PHASE_START: Record<AmbientPhase, number> = { reveal: 0, focus: 700, lock: 2100, resolve: 3300 };

/**
 * The controller retains its wake capability, but photographic scenes all use null:
 * a single finite settle, with no periodic accents, scanning or loops.
 */
export type WakeRhythm = { count: number; every: readonly [number, number]; hold: number } | null;

export const WAKE: Record<AmbientVariant, WakeRhythm> = {
  home: null,
  overview: null,
  market: null,
  location: null,
  risk: null,
  finance: null,
  decision: null,
  compare: null,
  report: null,
};

/**
 * Case routes whose last path segment selects a scene. Photography sets the mood where place matters
 * (overview, market, location, risk); decision surfaces — Money, Decision Room, Report, Compare — stay plain paper.
 */
const CASE_SCENES: Record<string, AmbientVariant> = {
  overview: "overview",
  market: "market",
  location: "location",
  risk: "risk",
};

/** Home places its own scene inside the start section, so the route host returns null for "/". */
export function ambientVariantForPath(pathname: string | null | undefined): AmbientVariant | null {
  if (!pathname) return null;
  const path = pathname.replace(/\/+$/, "") || "/";
  const match = /^\/cases\/[^/]+\/([^/]+)$/.exec(path);
  return match ? CASE_SCENES[match[1]] ?? null : null;
}

/** The next wake index, never repeating the previous one when there is a choice. */
export function nextWake(previous: number, count: number, random = Math.random): number {
  if (count <= 1) return 0;
  const step = 1 + Math.floor(random() * (count - 1));
  return (previous < 0 ? Math.floor(random() * count) : previous + step) % count;
}

export function wakeDelay(rhythm: NonNullable<WakeRhythm>, random = Math.random): number {
  const [min, max] = rhythm.every;
  return Math.round(min + random() * (max - min));
}
