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
 * After RESOLVE a scene may "wake" one of its relationships at a time. `count` is how many distinct
 * relationships take turns, `every` the random interval range between wakes, and `hold` how long a wake lasts.
 * `null` means the scene stays still once resolved.
 */
export type WakeRhythm = { count: number; every: readonly [number, number]; hold: number } | null;

export const WAKE: Record<AmbientVariant, WakeRhythm> = {
  home: null,
  overview: { count: 4, every: [11000, 15000], hold: 3200 },
  market: { count: 2, every: [12000, 16000], hold: 3600 },
  location: { count: 3, every: [8000, 12000], hold: 3600 },
  risk: { count: 2, every: [12000, 16000], hold: 4000 },
  finance: { count: 2, every: [12000, 16000], hold: 3600 },
  decision: { count: 1, every: [12000, 16000], hold: 4200 },
  compare: { count: 4, every: [12000, 16000], hold: 3200 },
  report: null,
};

/** Case routes whose last path segment selects a scene; other case routes (evidence, scenarios, planning…) stay plain. */
const CASE_SCENES: Record<string, AmbientVariant> = {
  overview: "overview",
  market: "market",
  location: "location",
  risk: "risk",
  finance: "finance",
  "decision-room": "decision",
  report: "report",
};

/** Home places its own scene inside the start section, so the route host returns null for "/". */
export function ambientVariantForPath(pathname: string | null | undefined): AmbientVariant | null {
  if (!pathname) return null;
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/compare") return "compare";
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
