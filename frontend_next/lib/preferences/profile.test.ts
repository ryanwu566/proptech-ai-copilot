import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
const feature = await import("./profile.ts").catch(() => null);
const profile = () => ({ version: 1, revision: 1, updatedAt: "2026-10-12T03:00:00Z", name: "Household", rationale: "Need room for work", rules: [{ id: "r1", metric: "size", priority: "must", min: 30, max: null, rationale: "" }] });
test("strict versioned profile preserves zero and rejects ambiguous or unbounded inputs", () => {
  assert.ok(feature?.normalizeProfile(profile()));
  const p = profile(); p.rules[0].min = 0;
  const rule = feature?.normalizeProfile(p)?.rules[0];
  assert.equal(rule && "min" in rule ? rule.min : undefined, 0);
  for (const invalid of [{ ...p, version: 2 }, { ...p, revision: 0 }, { ...p, updatedAt: "bad" }, { ...p, rules: [{ ...p.rules[0], metric: "neighborhood_ethnicity" }] }, { ...p, rules: [{ ...p.rules[0], min: 40, max: 30 }] }, { ...p, rules: [{ ...p.rules[0], min: null, max: null }] }, { ...p, rules: [p.rules[0], p.rules[0]] }, { ...p, rationale: "x".repeat(2001) }]) assert.equal(feature?.normalizeProfile(invalid), null);
  assert.equal("score" in (feature?.normalizeProfile({ ...p, score: 99 }) ?? {}), false);
});
test("local store isolates cases, blocks corrupt/future data and detects stale revisions", () => {
  const data = new Map([["proptech.savedCases.v1", "CASE_BYTES"]]);
  const storage = { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => { data.set(k, v); }, removeItem: (k: string) => { data.delete(k); } };
  const repo = feature?.createProfileStore(storage);
  assert.equal(repo?.read().status, "empty");
  assert.equal(repo?.save(profile(), null).status, "saved");
  assert.equal(repo?.read().profile?.revision, 1);
  assert.equal(repo?.save(profile(), null).status, "conflict");
  assert.equal(data.get("proptech.savedCases.v1"), "CASE_BYTES");
  data.set("proptech.preferenceProfile.v1", "{broken");
  assert.equal(repo?.read().status, "corrupt");
  assert.equal(repo?.save(profile(), null).status, "blocked");
  data.set("proptech.preferenceProfile.v1", '{"version":2}');
  assert.equal(repo?.read().status, "unsupported");
  assert.equal(repo?.save(profile(), null).status, "blocked");
  assert.equal(repo?.clear().status, "cleared");
  assert.equal(data.get("proptech.savedCases.v1"), "CASE_BYTES");
});
test("read and write denial are disclosed, never treated as success or empty", () => {
  const denied = feature?.createProfileStore({ getItem() { throw Error("denied"); }, setItem() { throw Error("quota"); }, removeItem() { throw Error("denied"); } });
  assert.equal(denied?.read().status, "unavailable");
  assert.equal(denied?.save(profile(), null).status, "blocked");
  assert.equal(denied?.clear().status, "unavailable");
  const quota = feature?.createProfileStore({ getItem: () => null, setItem() { throw Error("quota"); }, removeItem() {} });
  assert.equal(quota?.save(profile(), null).status, "unavailable");
});
test("delete/recreate cannot overwrite a different household with a reused revision", () => {
  let raw: string | null = null;
  const repo = feature?.createProfileStore({ getItem: () => raw, setItem: (_k: string, v: string) => { raw = v; }, removeItem: () => { raw = null; } });
  repo?.save(profile(), null);
  const before = repo?.read().profile;
  repo?.clear(); repo?.save({ ...profile(), name: "New household" }, null);
  assert.equal(repo?.save(profile(), before ?? null).status, "conflict");
  assert.equal(repo?.read().profile?.name, "New household");
});
