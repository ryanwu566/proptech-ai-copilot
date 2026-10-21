import type { LocationCandidateResult } from "./location-confirmation";

/** A short-lived handoff from an explicit Home submit, never a persisted identity or provider cache. */
export class LocationStartHandoff {
  private entries = new Map<string, { address: string; expires: number; result: Promise<LocationCandidateResult> }>();
  private clock: () => number;
  private ttlMs: number;
  private maxEntries: number;

  constructor(clock = Date.now, ttlMs = 120_000, maxEntries = 4) {
    this.clock = clock;
    this.ttlMs = ttlMs;
    this.maxEntries = maxEntries;
  }

  private expire() {
    for (const [key, entry] of this.entries) if (entry.expires <= this.clock()) this.entries.delete(key);
  }

  begin(caseId: string, address: string, acquire: () => Promise<LocationCandidateResult>): Promise<LocationCandidateResult> {
    const existing = this.read(caseId, address);
    if (existing) return existing;
    const result = Promise.resolve().then(acquire).catch((): LocationCandidateResult => ({ kind: "blocked", reason: "unavailable" }));
    this.entries.delete(caseId);
    this.entries.set(caseId, { address, expires: this.clock() + this.ttlMs, result });
    while (this.entries.size > this.maxEntries) this.entries.delete(this.entries.keys().next().value!);
    return result;
  }

  /** Reading/reopening can only adopt existing work; it never initiates a request. */
  read(caseId: string, address: string): Promise<LocationCandidateResult> | undefined {
    this.expire();
    const entry = this.entries.get(caseId);
    return entry?.address === address ? entry.result : undefined;
  }

  discard(caseId: string) { this.entries.delete(caseId); }
}

export const locationStartHandoff = new LocationStartHandoff();
