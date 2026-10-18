import assert from "node:assert/strict";
import test from "node:test";
// @ts-expect-error Native TS runner extension.
const feature = await import("./transport.ts").catch(() => null);
const data = { schema_version: "admin-v1", section: "users", state: "empty", source: "wave_1a", window: "current_snapshot", as_of: "2026-10-13T00:00:00Z", reason: null, next_cursor: null, metrics: [], users: [], usage: [], providers: [], limits: [], operations: [], audit: [] };
function dependencies(fetcher: typeof fetch = async () => Response.json(data)) {
  return { base: "https://api.example.invalid", fetcher, session: async () => ({ status: "authenticated" as const, accessToken: "fixture-token" }), generation: () => 1, current: () => true, expire: async () => {} };
}

test("one authorized read uses only fixed admin path and private request options", async () => {
  assert.ok(feature);
  const requests: { url: string; options: RequestInit }[] = [];
  const deps = dependencies(async (url, options) => { requests.push({ url: String(url), options: options! }); return Response.json(data); });
  assert.equal((await feature.readAdmin(deps, "users")).state, "empty");
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "https://api.example.invalid/v1/admin/users");
  assert.equal(new Headers(requests[0].options.headers).get("Authorization"), "Bearer fixture-token");
  assert.equal(requests[0].options.cache, "no-store");
  assert.equal(requests[0].options.redirect, "error");
});

test("denial and dependency failure expose fixed errors and never raw bodies", async () => {
  assert.ok(feature);
  for (const [status, expected] of [[401, "authentication"], [403, "denied"], [503, "error"]] as const) {
    await assert.rejects(feature.readAdmin(dependencies(async () => new Response("private-api-key", { status })), "users"), { message: expected });
  }
  await assert.rejects(feature.readAdmin(dependencies(async () => new Response("x".repeat(262145))), "users"), { message: "error" });
});

test("missing sessions and stale responses cannot return privileged data", async () => {
  assert.ok(feature);
  let calls = 0;
  const deps = dependencies(async () => { calls++; return Response.json(data); });
  await assert.rejects(feature.readAdmin({ ...deps, session: async () => ({ status: "missing_session" as const }) }, "users"), { message: "authentication" });
  assert.equal(calls, 0);
  let current = true;
  await assert.rejects(feature.readAdmin({ ...deps, current: () => current, fetcher: async () => { current = false; return Response.json(data); } }, "users"), { message: "authentication" });
});

test("cursor and cancellation stay bounded", async () => {
  assert.ok(feature);
  await assert.rejects(feature.readAdmin(dependencies(), "users", "bad?cursor"), { message: "error" });
  const controller = new AbortController(); controller.abort();
  await assert.rejects(feature.readAdmin(dependencies(), "users", null, controller.signal), { message: "cancelled" });
});

test("session recovery settles before capturing the generation", async () => {
  assert.ok(feature);
  let generation = 0;
  const deps = { ...dependencies(), ready: async () => { generation = 1; }, generation: () => generation, current: (value: number) => value === 1 };
  assert.equal((await feature.readAdmin(deps, "users")).state, "empty");
});

test("abort during stuck session acquisition settles promptly", async () => {
  assert.ok(feature);
  const controller = new AbortController();
  const pending = feature.readAdmin({ ...dependencies(), session: () => new Promise(() => {}) }, "users", null, controller.signal);
  controller.abort();
  const result = await Promise.race([pending.catch((error: Error) => error.message), new Promise((resolve) => setTimeout(() => resolve("hung"), 100))]);
  assert.equal(result, "cancelled");
});

test("15-second deadline bounds stuck session acquisition", async (context) => {
  assert.ok(feature);
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const pending = feature.readAdmin({ ...dependencies(), session: () => new Promise(() => {}) }, "users");
  let result = "pending";
  void pending.then(() => { result = "loaded"; }).catch((error: Error) => { result = error.message; });
  context.mock.timers.tick(15_000);
  for (let index = 0; index < 10; index++) await Promise.resolve();
  assert.equal(result, "error");
  context.mock.timers.reset();
});

test("native browser fetch is called without adapter object as its receiver", async () => {
  assert.ok(feature);
  async function nativeLikeFetch(this: unknown): Promise<Response> {
    if (this !== undefined) throw new TypeError("Illegal invocation");
    return Response.json(data);
  }
  assert.equal((await feature.readAdmin(dependencies(nativeLikeFetch), "users")).state, "empty");
});
