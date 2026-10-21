import assert from "node:assert/strict";
import { test } from "node:test";
// @ts-expect-error Node's native test runner uses source extensions.
import { createSessionStatusAdapter, authSessionStorageKey, type SessionEntryState } from "./auth-session-status.ts";

const tick = () => new Promise(resolve => setTimeout(resolve, 10));
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}
function harness(stored = false, read: () => Promise<boolean> = async () => true) {
  let loads = 0;
  const events = new EventTarget();
  const adapter = createSessionStatusAdapter({
    hasStoredSession: () => stored,
    loadSessionReader: async () => { loads++; return read; },
    subscribeStorage: listener => { events.addEventListener("storage", listener); return () => events.removeEventListener("storage", listener); },
    subscribeExpired: listener => { events.addEventListener("expired", listener); return () => events.removeEventListener("expired", listener); },
    deadlineMs: 50,
  });
  const states: SessionEntryState[] = [];
  const stop = adapter.observe(state => states.push(state));
  return { adapter, states, stop, loads: () => loads, events, store: (value: boolean) => { stored = value; events.dispatchEvent(new Event("storage")); } };
}
test("anonymous shared routes do not load a session reader or SDK", async () => {
  const h = harness(); await tick();
  assert.deepEqual(h.states, ["anonymous"]); assert.equal(h.loads(), 0); h.stop();
});
test("stored session stays pending until the existing validator finishes", async () => {
  const validation = deferred<boolean>(); const h = harness(true, () => validation.promise);
  await tick(); assert.deepEqual(h.states, ["pending"]);
  validation.resolve(true); await tick();
  assert.deepEqual(h.states, ["pending", "authenticated"]); h.stop();
});
test("a storage hint never counts as authenticated", async () => {
  const h = harness(true, async () => false); await tick();
  assert.deepEqual(h.states, ["pending", "anonymous"]); h.stop();
});
test("in-memory SDK state is validated even without persisted storage", async () => {
  const h = harness(); h.adapter.publish(async () => true); await tick();
  assert.equal(h.states.at(-1), "authenticated"); assert.equal(h.loads(), 0); h.stop();
});
test("a new observer restores an existing in-memory session without anonymous flash", async () => {
  const h = harness(); h.stop(); h.adapter.publish(async () => true);
  const states: SessionEntryState[] = []; const stop = h.adapter.observe(state => states.push(state));
  assert.deepEqual(states, ["pending"]); await tick();
  assert.deepEqual(states, ["pending", "authenticated"]); stop();
});
test("cross-tab sign in and sign out update the entry", async () => {
  let active = true; const h = harness(false, async () => active);
  h.store(true); await tick(); assert.equal(h.states.at(-1), "authenticated");
  active = false; h.store(false); await tick(); assert.equal(h.states.at(-1), "anonymous"); h.stop();
});
test("expiration invalidates a late successful restoration", async () => {
  const validation = deferred<boolean>(); const h = harness(true, () => validation.promise);
  await tick(); h.events.dispatchEvent(new Event("expired"));
  validation.resolve(true); await tick();
  assert.equal(h.states.at(-1), "anonymous"); assert.equal(h.states.includes("authenticated"), false); h.stop();
});
test("a newer auth change wins over a stale read", async () => {
  const validation = deferred<boolean>(); const h = harness(true, () => validation.promise);
  await tick(); h.adapter.publish(async () => false); await tick();
  validation.resolve(true); await tick();
  assert.equal(h.states.at(-1), "anonymous"); assert.equal(h.states.includes("authenticated"), false); h.stop();
});
test("unmount cancels all entry updates", async () => {
  const validation = deferred<boolean>(); const h = harness(true, () => validation.promise);
  await tick(); h.stop(); validation.resolve(true); h.store(true); h.adapter.publish(async () => true); await tick();
  assert.deepEqual(h.states, ["pending"]);
});
test("a stalled reader becomes neutral unknown, never anonymous", async () => {
  const h = harness(true, () => new Promise(() => {}));
  await new Promise(resolve => setTimeout(resolve, 70));
  assert.deepEqual(h.states, ["pending", "unknown"]); h.stop();
});
test("reader loading failure remains neutral", async () => {
  const h = harness(true, async () => { throw new Error("offline"); }); await tick();
  assert.deepEqual(h.states, ["pending", "unknown"]); h.stop();
});
test("SDK reads are deferred beyond the SDK callback", async () => {
  const h = harness(); let insideCallback = true;
  h.adapter.publish(async () => { assert.equal(insideCallback, false); return true; });
  insideCallback = false; await tick(); assert.equal(h.states.at(-1), "authenticated"); h.stop();
});
test("blocked storage stays pending until validated, rather than assuming signed out", async () => {
  const validation = deferred<boolean>(); const states: SessionEntryState[] = [];
  const adapter = createSessionStatusAdapter({
    hasStoredSession: () => { throw new Error("storage disabled"); },
    loadSessionReader: async () => () => validation.promise,
    subscribeStorage: () => () => {}, subscribeExpired: () => () => {},
  });
  const stop = adapter.observe(state => states.push(state)); await tick();
  assert.deepEqual(states, ["pending"]); validation.resolve(true); await tick();
  assert.deepEqual(states, ["pending", "authenticated"]); stop();
});
test("failed SDK chunk loading leaves a neutral entry", async () => {
  const states: SessionEntryState[] = [];
  const adapter = createSessionStatusAdapter({
    hasStoredSession: () => true,
    loadSessionReader: async () => { throw new Error("chunk unavailable"); },
    subscribeStorage: () => () => {}, subscribeExpired: () => () => {},
  });
  const stop = adapter.observe(state => states.push(state)); await tick();
  assert.deepEqual(states, ["pending", "unknown"]); stop();
});
test("storage key follows the configured project, including local development", () => {
  assert.equal(authSessionStorageKey("https://slice8-auth.supabase.co"), "sb-slice8-auth-auth-token");
  assert.equal(authSessionStorageKey("http://127.0.0.1:54321"), "sb-127-auth-token");
  assert.equal(authSessionStorageKey("bad"), null);
});
