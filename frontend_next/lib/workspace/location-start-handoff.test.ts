import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
import { LocationStartHandoff } from "./location-start-handoff.ts";
// @ts-expect-error Native TS runner extension.
import { acquireLocationResolution } from "./location-confirmation.ts";

const address = "臺北市信義區市府路1號";
const spatial = { status: "resolved", source: "google", confidence: "high", latitude: 25.0375, longitude: 121.5637, formatted_address: address };

test("a hung lookup times out once, aborts transport and ignores a late success", async () => {
  let signal: AbortSignal | undefined;
  let release!: (value: unknown) => void;
  let calls = 0;
  const result = await acquireLocationResolution(address, (requestSignal: AbortSignal) => {
    calls++; signal = requestSignal;
    return new Promise((resolve) => { release = resolve; });
  }, { timeoutMs: 10 });
  assert.deepEqual(result, { kind: "blocked", reason: "unavailable" });
  assert.equal(signal?.aborted, true);
  release(spatial);
  assert.equal(calls, 1);
});

test("an explicit Start shares one acquisition across repeated submits and reads, without confirming identity", async () => {
  const handoff = new LocationStartHandoff();
  let calls = 0;
  const acquire = () => acquireLocationResolution(address, async () => { calls++; return spatial; });
  assert.equal(handoff.read("new-case", address), undefined);
  const first = handoff.begin("new-case", address, acquire);
  assert.equal(handoff.begin("new-case", address, acquire), first);
  assert.equal(handoff.read("new-case", address), first);
  const result = await first;
  assert.equal(result.kind, "candidate");
  assert.equal(result.candidate.county, null);
  assert.equal(result.candidate.district, null);
  assert.equal(calls, 1);
  assert.equal(handoff.read("new-case", "another address"), undefined);
  assert.equal(handoff.read("other-case", address), undefined);
  handoff.discard("new-case");
  assert.equal(handoff.read("new-case", address), undefined);
  assert.equal(calls, 1);
});

test("temporary handoffs expire and are bounded; reading never acquires provider data", async () => {
  let now = 0;
  const handoff = new LocationStartHandoff(() => now, 100, 2);
  const acquire = () => acquireLocationResolution(address, async () => spatial);
  await handoff.begin("one", address, acquire);
  await handoff.begin("two", address, acquire);
  await handoff.begin("three", address, acquire);
  assert.equal(handoff.read("one", address), undefined);
  assert.ok(handoff.read("two", address));
  now = 101;
  assert.equal(handoff.read("two", address), undefined);
  assert.equal(handoff.read("three", address), undefined);
});

test("HTTP failures remain distinct without rejecting or persisting an unconfirmed handoff", async () => {
  for (const [status, reason] of [[429, "capacity_unavailable"], [503, "provider_unavailable"]] as const) {
    const handoff = new LocationStartHandoff();
    assert.deepEqual(await handoff.begin("new-case", address, () => acquireLocationResolution(address, async () => { throw Object.assign(new Error("safe"), { status }); })), { kind: "blocked", reason });
  }
  assert.deepEqual(await acquireLocationResolution(address, async () => ({ ...spatial, latitude: null })), { kind: "blocked", reason: "missing_coordinates" });
  assert.deepEqual(await acquireLocationResolution(address, async () => { throw new TypeError("network"); }), { kind: "blocked", reason: "unavailable" });
});
