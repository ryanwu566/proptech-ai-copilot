import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import ts from "typescript";
import { webcrypto } from "node:crypto";

function harness({ code = 200, late = false, jsonLate = false, payload = [], session = "authenticated" } = {}) {
  let current = true, expired = 0, requests = 0, release, generation = 1;
  const calls = [];
  const wait = new Promise(resolve => { release = resolve; });
  const auth = { getVNextAccessToken: async () => ({ status: session, accessToken: "fixture-token" }), getVNextSessionGeneration: () => generation,
    isVNextSessionGenerationCurrent: value => current && value === generation, expireVNextSession: async () => { expired++; } };
  const contract = { validCloudSummary: value => !!value, validCloudCase: value => !!value, validActivity: value => !!value };
  const module = { exports: {} };
  const source = ts.transpileModule(readFileSync(new URL("../lib/cloud-case-client.ts", import.meta.url), "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  vm.runInNewContext(source, { module, exports: module.exports, AbortSignal, crypto: webcrypto, TextEncoder, navigator: { onLine: true },
    require: name => name === "@/lib/api" ? { API_BASE: "https://api.example.invalid" } : name.includes("contract") ? contract : auth,
    fetch: async (url, options) => {
      requests++; calls.push({ url, ...options }); assert.match(url, /\/v1\/saved-cases/); assert.equal(options.credentials, "omit"); assert.equal(options.redirect, "error"); assert.equal(options.cache, "no-store");
      assert.equal(options.headers.Authorization, "Bearer fixture-token");
      if (late) await wait;
      return { status: code, ok: code >= 200 && code < 300, json: async () => { if (jsonLate) await wait; return payload; } };
    },
  });
  return { client: module.exports.cloudCases, calls, requests: () => requests, expired: () => expired, change: () => { current = false; release(); }, replace: () => { generation++; current = true; } };
}

test("constructing the client never uploads or reads cases", () => assert.equal(harness().requests(), 0));
test("account-change guard cancels upload before sending selected local data", async () => {
  const h = harness();
  const result = await h.client.create({ snapshot: {}, user_authored: {}, import_key: "test", explicit_consent: true }, () => false);
  assert.equal(result.status, "sign_in_required"); assert.equal(h.requests(), 0);
});
test("missing auth cannot send case data", async () => { const h = harness({ session: "missing_session" }); assert.equal((await h.client.list("owned")).status, "sign_in_required"); assert.equal(h.requests(), 0); });
for (const [code, status] of [[401, "sign_in_required"], [403, "forbidden"], [404, "forbidden"], [409, "conflict"], [422, "invalid"], [500, "unavailable"]]) test(`maps ${code} to a bounded safe status`, async () => {
  const h = harness({ code }); assert.equal((await h.client.list("owned")).status, status);
});
test("persistence pending is honest and contains no raw exception", async () => {
  const h = harness({ code: 503, payload: { error: { details: { reason_code: "persistence_pending" }, message: "SECRET" } } });
  const result = await h.client.list("owned"); assert.equal(result.status, "persistence_pending"); assert.ok(!JSON.stringify(result).includes("SECRET"));
});
for (const stage of ["late", "jsonLate"]) test(`discards old account data after logout during ${stage}`, async () => {
  const h = harness({ [stage]: true }); const result = h.client.list("owned");
  await new Promise(resolve => setTimeout(resolve, 0)); h.change();
  assert.equal((await result).status, "sign_in_required"); assert.equal(h.expired(), 0);
});
test("a late 401 cannot expire the new session", async () => {
  const h = harness({ late: true, code: 401 }); const result = h.client.list("owned");
  await new Promise(resolve => setTimeout(resolve, 0)); h.change();
  assert.equal((await result).status, "sign_in_required"); assert.equal(h.expired(), 0);
});

test("all four commands send bounded opaque keys; retries reuse keys without automatic requests", async () => {
  const h = harness(); const row = { id: "case-a", revision: 1 };
  const actions = [
    () => h.client.create({ snapshot: {}, user_authored: {}, import_key: "local", explicit_consent: true }),
    () => h.client.metadata(row, "Title", "Notes"),
    () => h.client.membership(row, "member", "viewer"),
    () => h.client.monitoring(row, "daily"),
  ];
  for (const action of actions) {
    assert.equal((await action()).status, "ready"); await action();
    const [first, retry] = h.calls.slice(-2);
    assert.match(first.headers["Idempotency-Key"], /^[A-Za-z0-9._:-]{16,128}$/);
    assert.equal(first.headers["Idempotency-Key"], retry.headers["Idempotency-Key"]);
  }
  assert.equal(h.requests(), 8);
  await h.client.open(row.id);
  assert.equal(h.calls.at(-1).headers["Idempotency-Key"], undefined);
});

test("command identities change with body, revision, case, account and bounded cache eviction", async () => {
  const h = harness(); const row = { id: "case-a", revision: 1 };
  const key = () => h.calls.at(-1).headers["Idempotency-Key"];
  await h.client.metadata(row, "Title", "Notes"); const original = key();
  await h.client.metadata(row, "Title", "Different"); assert.notEqual(key(), original);
  await h.client.metadata({ ...row, revision: 2 }, "Title", "Notes"); assert.notEqual(key(), original);
  await h.client.metadata({ ...row, id: "case-b" }, "Title", "Notes"); assert.notEqual(key(), original);
  h.replace(); await h.client.metadata(row, "Title", "Notes"); assert.notEqual(key(), original);
  const replacement = key();
  for (let i = 0; i < 64; i++) await h.client.metadata(row, "Title", `Notes ${i}`);
  await h.client.metadata(row, "Title", "Notes"); assert.notEqual(key(), replacement);
});
