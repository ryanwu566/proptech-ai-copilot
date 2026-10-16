import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
const feature = await import("./model.ts").catch(() => null);
const snapshot = () => ({ schema_version: "admin-v1", section: "overview", state: "partial", source: "wave_1b", window: "last_24h", as_of: "2026-10-13T00:00:00Z", reason: null, next_cursor: null,
  metrics: [{ key: "requests", state: "unknown", value: null, source: "wave_1b", window: "last_24h" }], users: [], usage: [], providers: [], limits: [], operations: [], audit: [] });

test("unknown survives parsing and renders differently from known zero", () => {
  const result = feature?.parseSnapshot(snapshot(), "overview");
  assert.equal(result?.metrics[0].value, null);
  assert.equal(feature?.metricValue(result?.metrics[0], "en"), "Unknown");
  assert.equal(feature?.metricValue({ key: "requests", source: "wave_1b", window: "last_24h", state: "known", value: 0 }, "en"), "0");
});

test("malformed truth, wrong section and oversized rows are rejected", () => {
  assert.ok(feature);
  for (const value of [{ ...snapshot(), section: "users" }, { ...snapshot(), metrics: [{ ...snapshot().metrics[0], value: 0 }] },
    { ...snapshot(), users: Array(51).fill({}) }, { ...snapshot(), as_of: "bad" }, { ...snapshot(), next_cursor: "a".repeat(129) }]) {
    assert.throws(() => feature.parseSnapshot(value, "overview"));
  }
});

test("cost states are distinct and require a server-provided currency estimate", () => {
  assert.ok(feature);
  assert.equal(feature.costValue({ state: "unknown", amount: null, currency: null }, "en"), "Unknown");
  assert.equal(feature.costValue({ state: "not_applicable", amount: null, currency: null }, "en"), "Not applicable");
  assert.match(feature.costValue({ state: "known", amount: 0, currency: "USD" }, "en"), /0/);
  assert.throws(() => feature.parseSnapshot({ ...snapshot(), usage: [{ capability: "routes", cost: { state: "unknown", amount: 0, currency: "USD" } }] }, "overview"));
});

test("privacy projection drops extra fields and rejects arbitrary audit strings", () => {
  assert.ok(feature);
  const result = feature.parseSnapshot({ ...snapshot(), password: "private", users: [{ user_id: "11111111-1111-4111-8111-111111111111", status: "active", platform_role: "consumer", created_at: null, last_activity: null, usage_requests: null, email: "private" }] }, "overview");
  assert.ok(!JSON.stringify(result).includes("private"));
  assert.throws(() => feature.parseSnapshot({ ...snapshot(), audit: [{ timestamp: "2026-10-13T00:00:00Z", actor: null, event_type: "secret-provider-token", target_type: "admin", outcome: "success", reason_code: "authorized" }] }, "overview"));
});

test("four locale catalogues preserve operational distinctions", async () => {
  // @ts-expect-error Native TS runner extension.
  const { adminCopy } = await import("./copy.ts");
  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    assert.ok(adminCopy[locale].title);
    assert.notEqual(adminCopy[locale].unknown, adminCopy[locale].unavailable);
    assert.notEqual(adminCopy[locale].empty, adminCopy[locale].error);
    assert.notEqual(adminCopy[locale].not_checked, adminCopy[locale].available);
  }
});

test("operational timestamps preserve time of day and UTC timezone in four locales", () => {
  assert.ok(feature);
  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    const first = feature.adminTimestamp?.("2026-10-13T01:02:03Z", locale);
    const second = feature.adminTimestamp?.("2026-10-13T01:02:04Z", locale);
    assert.ok(first?.includes("UTC"));
    assert.notEqual(first, second);
  }
});

test("auth identity transitions clear records on account switch and sign-out", () => {
  assert.ok(feature);
  const first = "11111111-1111-4111-8111-111111111111";
  const second = "22222222-2222-4222-8222-222222222222";
  assert.equal(feature.sessionTransition?.(null, "SIGNED_IN", first).revoke, false);
  assert.equal(feature.sessionTransition?.(first, "SIGNED_IN", second).revoke, true);
  assert.equal(feature.sessionTransition?.(first, "SIGNED_IN", first).revoke, false);
  assert.equal(feature.sessionTransition?.(first, "SIGNED_OUT", null).revoke, true);
});
