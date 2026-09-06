import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import ts from "typescript";

const ROOT = new URL("../", import.meta.url);
const USER = "11111111-1111-4111-8111-111111111111";
const WORKSPACE = "22222222-2222-4222-8222-222222222222";
const RESOLUTION = "33333333-3333-4333-8333-333333333333";
const CANDIDATE = "44444444-4444-4444-8444-444444444444";
const PROPERTY = "55555555-5555-4555-8555-555555555555";
const DECISION = "66666666-6666-4666-8666-666666666666";
const EVIDENCE = "77777777-7777-4777-8777-777777777777";
const REFERENCE = "88888888-8888-4888-8888-888888888888";
const CONFIRMATION = "99999999-9999-4999-8999-999999999999";
const CASE = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const LINK = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const NODE_PROPERTY = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const NODE_ADDRESS = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const RELATION = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const NOW = "2026-09-06T00:00:00Z";
const PROJECT_URL = "https://slice9-auth.supabase.co";
const STORAGE_KEY = "sb-slice9-auth-auth-token";
const PUBLISHABLE_KEY = "sb_publishable_slice9_public_only";

function compile(relativePath, globals = {}) {
  const source = readFileSync(new URL(relativePath, ROOT), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    fileName: relativePath,
  }).outputText;
  const module = { exports: {} };
  const context = vm.createContext({ module, exports: module.exports, ...globals });
  vm.runInContext(output, context, { filename: relativePath });
  return module.exports;
}

function base64url(value) {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

function accessToken(exp, payload = {}, header = {}) {
  return `${base64url({ alg: "ES256", typ: "JWT", kid: "slice9-test-key", ...header })}.${base64url({ sub: USER, aud: "authenticated", role: "authenticated", iss: `${PROJECT_URL}/auth/v1`, exp, ...payload })}.signature`;
}

function legacyKey(role = "anon") {
  return `${base64url({ alg: "HS256", typ: "JWT" })}.${base64url({ role, iss: "supabase" })}.signature`;
}

function storage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
    values,
  };
}

function authHarness({ env = {}, initial = null, fetchImpl, setTimeoutImpl } = {}) {
  const localStorage = storage(initial === null ? {} : { [STORAGE_KEY]: JSON.stringify(initial) });
  const logs = [];
  const auth = compile("lib/vnext-auth-session.ts", {
    process: { env: { NEXT_PUBLIC_SUPABASE_URL: PROJECT_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: PUBLISHABLE_KEY, ...env } },
    window: {
      localStorage,
      setTimeout: setTimeoutImpl ?? setTimeout,
      clearTimeout,
    },
    fetch: fetchImpl ?? (async () => { throw new Error("unexpected fetch"); }),
    URL,
    AbortController,
    atob,
    console: { log: (...items) => logs.push(items), error: (...items) => logs.push(items), warn: (...items) => logs.push(items) },
  });
  return { auth, localStorage, logs };
}

function session(token, refresh = "slice9-refresh-token") {
  return {
    access_token: token,
    refresh_token: refresh,
    token_type: "bearer",
    expires_in: 3600,
    user: { id: USER, app_metadata: {}, user_metadata: {} },
  };
}

function response(body, ok = true) {
  return { ok, json: async () => body };
}

const source = (environment = "production") => ({
  source_id: "slice9-source",
  source_type: environment === "production" ? "official" : environment,
  environment,
  provider_id: "slice9-provider",
  source_record_id: "slice9-record",
  retrieved_at: NOW,
});

function candidate(environment = "production") {
  return {
    candidate_id: CANDIDATE,
    candidate_type: "address",
    normalized_identity: { address: "bounded observation" },
    display_identity: "Bounded candidate",
    source: source(environment),
    confidence: 1,
    confidence_method: "deterministic-ranking-v1",
    ranking_trace: { order: 1 },
    rank: 1,
    status: "plausible",
    coverage_status: "known",
    coverage: { scope: "fixture" },
    supporting_evidence_ids: [EVIDENCE],
    supporting_identity_reference_ids: [REFERENCE],
    possible_existing_property_entity_id: null,
    needs_human_confirmation: true,
  };
}

function resolution(confirmed = false) {
  return {
    resolution_id: RESOLUTION,
    workspace_id: WORKSPACE,
    case_id: null,
    state: confirmed ? "confirmed" : "ambiguous",
    input: { kind: "address", value: { text: "bounded observation" } },
    normalized_input: { address: "bounded observation" },
    normalization_version: "identity-normalization-v1",
    coverage_status: "known",
    coverage: { scope: "fixture" },
    ambiguity: confirmed ? "none" : "multiple_candidates",
    needs_human_confirmation: !confirmed,
    candidates: [candidate()],
    conflicts: [],
    provider_attempts: [],
    decisions: confirmed ? [{
      decision_id: DECISION,
      decision_type: "confirmed",
      candidate_id: CANDIDATE,
      property_entity_id: PROPERTY,
      reason_code: null,
      resolution_version_observed: 1,
      decision_version: 2,
      actor_user_id: USER,
      decided_at: NOW,
    }] : [],
    selected_candidate_id: confirmed ? CANDIDATE : null,
    confirmed_property_entity_id: confirmed ? PROPERTY : null,
    version: confirmed ? 2 : 1,
    created_by: USER,
    created_at: NOW,
    updated_at: NOW,
  };
}

function property() {
  return {
    property_entity_id: PROPERTY,
    workspace_id: WORKSPACE,
    lifecycle_state: "active",
    display_label: "Human-confirmed property",
    confirmation_summary: {
      available: true,
      human_confirmed: true,
      confirmation_id: CONFIRMATION,
      confirmed_at: NOW,
      confirmed_by: USER,
      resolution_id: RESOLUTION,
    },
    version: 1,
    created_at: NOW,
    updated_at: NOW,
  };
}

function graph() {
  return {
    property: property(),
    nodes: [
      { node_id: NODE_PROPERTY, node_type: "property", record_id: PROPERTY, display_label: "Property", status: null, source: null, valid_from: null, valid_to: null },
      { node_id: NODE_ADDRESS, node_type: "address", record_id: REFERENCE, display_label: "Address", status: "observed", source: source(), valid_from: NOW, valid_to: null },
    ],
    relations: [{ relation_id: RELATION, from_node_id: NODE_PROPERTY, to_node_id: NODE_ADDRESS, relation_type: "property_address", direction: "directed", confidence: null, confidence_method: null, source: source(), evidence_id: EVIDENCE, status: "confirmed", valid_from: NOW, valid_to: null, supersedes_relation_id: null, created_at: NOW, confirmation_id: CONFIRMATION }],
    as_of: null,
    next_cursor: null,
  };
}

function evidencePage() {
  return {
    property: property(),
    evidence: [{ evidence_id: EVIDENCE, workspace_id: WORKSPACE, fact_type: "address.observation", value: null, has_private_value_reference: true, value_schema: null, source: source(), effective_from: NOW, effective_to: null, expires_at: null, coverage_status: "unknown", coverage: { limitation: "not verified" }, status: "unverified", quality_confidence: null, quality_method: null, quality_status: "not_checked", quality: {}, license_status: "unknown", license_reference: null, license: {}, lineage: {}, content_hash: "f".repeat(64), version: 1, supersedes_evidence_id: null, created_at: NOW }],
    next_cursor: null,
  };
}

function attachment() {
  return {
    case: { case_id: CASE, workspace_id: WORKSPACE, purpose: "buy_due_diligence", status: "open", title: "Case", identity_status: "confirmed", assigned_member_id: null, version: 2, opened_at: NOW, updated_at: NOW },
    link: { case_property_link_id: LINK, case_id: CASE, property_entity_id: PROPERTY, resolution_id: RESOLUTION, confirmation_id: CONFIRMATION, supersedes_case_property_link_id: null, attached_by: USER, attached_at: NOW },
  };
}

function mutation(base, mutate) {
  const value = structuredClone(base);
  mutate(value);
  return value;
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

let passed = 0;
async function check(name, action) {
  try {
    await action();
    passed += 1;
  } catch (error) {
    error.message = `${name}: ${error.message}`;
    throw error;
  }
}

const future = Math.floor(Date.now() / 1000) + 3600;
const expired = Math.floor(Date.now() / 1000) - 60;

await check("current Supabase session shape and derived key", async () => {
  const token = accessToken(future);
  const { auth, localStorage } = authHarness({ initial: session(token) });
  assert.deepEqual(plain(await auth.getVNextAccessToken()), { status: "authenticated", accessToken: token });
  assert.ok(localStorage.values.has(STORAGE_KEY));
});

await check("expired access token rotates both tokens and preserves session fields", async () => {
  const next = accessToken(future);
  const { auth, localStorage, logs } = authHarness({
    initial: session(accessToken(expired)),
    fetchImpl: async () => response({ access_token: next, refresh_token: "slice9-rotated-token", expires_in: 3600 }),
  });
  assert.deepEqual(plain(await auth.getVNextAccessToken()), { status: "authenticated", accessToken: next });
  const stored = JSON.parse(localStorage.values.get(STORAGE_KEY));
  assert.equal(stored.refresh_token, "slice9-rotated-token");
  assert.equal(stored.user.id, USER);
  assert.deepEqual(logs, []);
});

await check("same-realm refresh is single-flight", async () => {
  let calls = 0;
  const next = accessToken(future);
  const { auth } = authHarness({
    initial: session(accessToken(expired)),
    fetchImpl: async () => { calls += 1; await new Promise((resolve) => setTimeout(resolve, 5)); return response({ access_token: next, refresh_token: "slice9-rotated-token", expires_in: 3600 }); },
  });
  const results = await Promise.all([auth.getVNextAccessToken(), auth.getVNextAccessToken()]);
  assert.equal(calls, 1);
  assert.equal(results[0].accessToken, next);
  assert.equal(results[1].accessToken, next);
});

await check("newer session is not overwritten by stale refresh", async () => {
  let release;
  const pendingResponse = new Promise((resolve) => { release = resolve; });
  const newer = accessToken(future, { session_id: "newer" });
  const { auth, localStorage } = authHarness({ initial: session(accessToken(expired)), fetchImpl: () => pendingResponse });
  const pending = auth.getVNextAccessToken();
  await Promise.resolve();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session(newer, "newer-refresh-token")));
  release(response({ access_token: accessToken(future, { session_id: "stale" }), refresh_token: "stale-refresh-token", expires_in: 3600 }));
  assert.deepEqual(plain(await pending), { status: "authenticated", accessToken: newer });
  assert.equal(JSON.parse(localStorage.values.get(STORAGE_KEY)).refresh_token, "newer-refresh-token");
});

await check("signed-out removal is not resurrected", async () => {
  let release;
  const pendingResponse = new Promise((resolve) => { release = resolve; });
  const { auth, localStorage } = authHarness({ initial: session(accessToken(expired)), fetchImpl: () => pendingResponse });
  const pending = auth.getVNextAccessToken();
  await Promise.resolve();
  localStorage.removeItem(STORAGE_KEY);
  release(response({ access_token: accessToken(future), refresh_token: "rotated-refresh-token", expires_in: 3600 }));
  assert.deepEqual(plain(await pending), { status: "missing_session" });
  assert.equal(localStorage.values.has(STORAGE_KEY), false);
});

for (const [name, raw] of [["corrupt JSON", "{"], ["non-session JSON", JSON.stringify({ access_token: "x" })]]) {
  await check(name, async () => {
    let calls = 0;
    const { auth, localStorage } = authHarness({ fetchImpl: async () => { calls += 1; throw new Error("should not run"); } });
    localStorage.setItem(STORAGE_KEY, raw);
    assert.deepEqual(plain(await auth.getVNextAccessToken()), { status: "missing_session" });
    assert.equal(calls, 0);
  });
}

for (const [name, fetchImpl] of [
  ["invalid refresh token response", async () => response({}, false)],
  ["malformed refresh response", async () => response({ access_token: "malformed", refresh_token: "rotated-refresh-token", expires_in: 3600 })],
]) {
  await check(name, async () => {
    const { auth, logs } = authHarness({ initial: session(accessToken(expired)), fetchImpl });
    assert.deepEqual(plain(await auth.getVNextAccessToken()), { status: "missing_session" });
    assert.deepEqual(logs, []);
  });
}

await check("refresh timeout fails closed", async () => {
  const fetchImpl = (_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener("abort", () => reject(new Error("aborted"))));
  const { auth } = authHarness({ initial: session(accessToken(expired)), fetchImpl, setTimeoutImpl: (callback) => { queueMicrotask(callback); return 1; } });
  assert.deepEqual(plain(await auth.getVNextAccessToken()), { status: "missing_session" });
});

for (const [name, env] of [
  ["wrong Supabase URL", { NEXT_PUBLIC_SUPABASE_URL: "https://example.com" }],
  ["HTTP production URL", { NEXT_PUBLIC_SUPABASE_URL: "http://slice9-auth.supabase.co" }],
  ["missing publishable key", { NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "" }],
  ["service legacy JWT key", { NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: legacyKey("service_role") }],
]) {
  await check(name, async () => {
    const { auth } = authHarness({ env, initial: session(accessToken(future)) });
    assert.deepEqual(plain(await auth.getVNextAccessToken()), { status: "configuration_error" });
  });
}

await check("legacy anon JWT browser key remains supported", async () => {
  const token = accessToken(future);
  const { auth } = authHarness({ env: { NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: legacyKey() }, initial: session(token) });
  assert.deepEqual(plain(await auth.getVNextAccessToken()), { status: "authenticated", accessToken: token });
});

const contract = compile("lib/vnext-identity-contract.ts");
const rejects = (parser, value) => assert.throws(() => parser(value), (error) => error?.name === "VNextContractError");

await check("valid Stage 1 DTOs parse", () => {
  assert.equal(contract.parsePropertyResolution(resolution()).needs_human_confirmation, true);
  assert.equal(contract.parsePropertyResolution(resolution(true)).state, "confirmed");
  assert.equal(contract.parsePropertyGraph(graph()).relations[0].status, "confirmed");
  assert.equal(contract.parsePropertyEvidence(evidencePage()).evidence[0].status, "unverified");
  assert.equal(contract.parseCaseAttachment(attachment()).case.identity_status, "confirmed");
});

const resolutionMutations = [
  ["missing required field", (value) => { delete value.workspace_id; }],
  ["unknown enum", (value) => { value.state = "verified"; }],
  ["wrong UUID", (value) => { value.resolution_id = "not-a-uuid"; }],
  ["cross-bound candidate reference", (value) => { value.conflicts = [{ conflict_id: LINK, left_candidate_id: CANDIDATE, right_candidate_id: PROPERTY, related_identity_reference_id: null, related_evidence_id: null, related_property_entity_id: null, category: "provider_disagreement", severity: "warning", state: "open" }]; }],
  ["invalid confirmed demo source", (value) => { value.candidates[0].source = source("demo"); }],
  ["invalid confirmed coverage", (value) => { value.candidates[0].coverage_status = "unknown"; }],
  ["confirmed candidate without evidence", (value) => { value.candidates[0].supporting_evidence_ids = []; }],
];
for (const [name, mutate] of resolutionMutations) {
  await check(name, () => rejects(contract.parsePropertyResolution, mutation(name.startsWith("invalid confirmed") || name.startsWith("confirmed candidate") ? resolution(true) : resolution(), mutate)));
}

await check("prototype-like JSON key", () => {
  const value = resolution();
  value.normalized_input = JSON.parse('{"__proto__":{"polluted":true}}');
  rejects(contract.parsePropertyResolution, value);
});

await check("invalid confirmation summary", () => rejects(contract.parseProperty, mutation(property(), (value) => { value.confirmation_summary.confirmed_by = null; })));
await check("wrong evidence workspace", () => rejects(contract.parsePropertyEvidence, mutation(evidencePage(), (value) => { value.evidence[0].workspace_id = CASE; })));
await check("unexpected evidence state", () => rejects(contract.parsePropertyEvidence, mutation(evidencePage(), (value) => { value.evidence[0].status = "available"; value.evidence[0].has_private_value_reference = false; })));
await check("malformed graph cursor", () => rejects(contract.parsePropertyGraph, mutation(graph(), (value) => { value.next_cursor = "unsigned-cursor"; })));
await check("dangling graph relation", () => rejects(contract.parsePropertyGraph, mutation(graph(), (value) => { value.relations[0].to_node_id = CASE; })));
await check("test source cannot assert confirmed relation", () => rejects(contract.parsePropertyGraph, mutation(graph(), (value) => { value.relations[0].source = source("test"); })));
await check("cross-bound Case attachment", () => rejects(contract.parseCaseAttachment, mutation(attachment(), (value) => { value.link.case_id = PROPERTY; })));

process.stdout.write(`VNext frontend hardening: ${passed} passed\n`);
