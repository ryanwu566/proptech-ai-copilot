export const PROFILE_KEY = "proptech.preferenceProfile.v1";
export const PROFILE_EVENT = "proptech:preference-profile-updated";
export const METRICS = ["price", "cash", "size", "age", "floor", "transit", "commute", "risk"] as const;
export const RISK_KEYS = ["terrain", "flood", "landslide", "debris_flow", "liquefaction", "geological_sensitivity", "active_fault"] as const;
export type Priority = "must" | "nice" | "veto";
type BaseRule = { id: string; priority: Priority; rationale: string };
export type NumericRule = BaseRule & { metric: "price" | "cash" | "size" | "age" | "floor" | "transit"; min: number | null; max: number | null };
export type CommuteRule = BaseRule & { metric: "commute"; destination: string; mode: "driving" | "transit" | "walking"; max: number };
export type RiskRule = BaseRule & { metric: "risk"; risk: typeof RISK_KEYS[number]; requirement: "documented" | "versioned" | "no_match" };
export type PreferenceRule = NumericRule | CommuteRule | RiskRule;
export type PreferenceProfile = { version: 1; revision: number; updatedAt: string; name: string; rationale: string; rules: PreferenceRule[] };
export type ProfileRead = { status: "ready" | "empty" | "corrupt" | "unsupported" | "unavailable"; profile: PreferenceProfile | null };
type LocalStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const text = (v: unknown, limit: number): v is string => typeof v === "string" && v.length <= limit;
const number = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 1e9;
export function normalizeProfile(value: unknown): PreferenceProfile | null {
  if (!object(value) || value.version !== 1 || !Number.isSafeInteger(value.revision) || (value.revision as number) < 1 || !text(value.updatedAt, 40) || !Number.isFinite(Date.parse(value.updatedAt)) || !text(value.name, 80) || !text(value.rationale, 2000) || !Array.isArray(value.rules) || value.rules.length > 12) return null;
  const rules: PreferenceRule[] = []; const ids = new Set<string>();
  for (const r of value.rules) {
    if (!object(r) || !text(r.id, 80) || !/^[\w-]+$/.test(r.id) || ids.has(r.id) || !["must", "nice", "veto"].includes(String(r.priority)) || !text(r.rationale, 500)) return null;
    ids.add(r.id);
    const base: BaseRule = { id: r.id, priority: r.priority as Priority, rationale: r.rationale };
    if (r.metric === "commute") {
      if (!text(r.destination, 200) || !r.destination.trim() || !["driving", "transit", "walking"].includes(String(r.mode)) || !number(r.max)) return null;
      rules.push({ ...base, metric: "commute", destination: r.destination.trim(), mode: r.mode as CommuteRule["mode"], max: r.max });
    } else if (r.metric === "risk") {
      if (!RISK_KEYS.includes(r.risk as RiskRule["risk"]) || !["documented", "versioned", "no_match"].includes(String(r.requirement))) return null;
      rules.push({ ...base, metric: "risk", risk: r.risk as RiskRule["risk"], requirement: r.requirement as RiskRule["requirement"] });
    } else {
      if (!["price", "cash", "size", "age", "floor", "transit"].includes(String(r.metric)) || !(r.min === null || number(r.min)) || !(r.max === null || number(r.max)) || r.min === null && r.max === null || r.min !== null && r.max !== null && (r.min as number) > (r.max as number)) return null;
      rules.push({ ...base, metric: r.metric as NumericRule["metric"], min: r.min as number | null, max: r.max as number | null });
    }
  }
  return { version: 1, revision: value.revision as number, updatedAt: value.updatedAt, name: value.name, rationale: value.rationale, rules };
}
export function emptyProfile(): PreferenceProfile { return { version: 1, revision: 1, updatedAt: new Date().toISOString(), name: "", rationale: "", rules: [] }; }
/** No case-storage dependency. Writes occur only through explicit user actions. */
export function createProfileStore(storage: LocalStorage) {
  function read(): ProfileRead {
    try {
      const raw = storage.getItem(PROFILE_KEY);
      if (raw === null) return { status: "empty", profile: null };
      if (raw.length > 24000) return { status: "corrupt", profile: null };
      let value: unknown;
      try { value = JSON.parse(raw); } catch { return { status: "corrupt", profile: null }; }
      if (object(value) && value.version !== 1) return { status: "unsupported", profile: null };
      const profile = normalizeProfile(value);
      return { status: profile ? "ready" : "corrupt", profile };
    } catch { return { status: "unavailable", profile: null }; }
  }
  return {
    read,
    save(value: unknown, expected: PreferenceProfile | null): { status: "saved" | "invalid" | "blocked" | "conflict" | "unavailable"; profile?: PreferenceProfile } {
      const current = read();
      if (!["ready", "empty"].includes(current.status)) return { status: "blocked" };
      // Compare content as well as revision: deletion/recreation may reuse revision 1.
      if (JSON.stringify(current.profile) !== JSON.stringify(expected)) return { status: "conflict" };
      if (!object(value)) return { status: "invalid" };
      const profile = normalizeProfile({ ...value, revision: (expected?.revision ?? 0) + 1, updatedAt: new Date().toISOString() });
      if (!profile) return { status: "invalid" };
      try { storage.setItem(PROFILE_KEY, JSON.stringify(profile)); return { status: "saved", profile }; }
      catch { return { status: "unavailable" }; }
    },
    clear(): { status: "cleared" | "unavailable" } {
      try { storage.removeItem(PROFILE_KEY); return { status: "cleared" }; } catch { return { status: "unavailable" }; }
    },
  };
}
