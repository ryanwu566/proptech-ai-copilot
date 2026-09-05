import { expect, test, type Page, type Route } from "@playwright/test";

const USER = "11111111-1111-4111-8111-111111111111";
const WORKSPACE = "22222222-2222-4222-8222-222222222222";
const RESOLUTION = "33333333-3333-4333-8333-333333333333";
const CANDIDATE_ONE = "44444444-4444-4444-8444-444444444444";
const CANDIDATE_TWO = "55555555-5555-4555-8555-555555555555";
const PROPERTY = "66666666-6666-4666-8666-666666666666";
const DECISION = "77777777-7777-4777-8777-777777777777";
const CASE = "88888888-8888-4888-8888-888888888888";
const CONFIRMATION = "99999999-9999-4999-8999-999999999999";
const LINK = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const EVIDENCE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const NODE_PROPERTY = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const NODE_ADDRESS = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const RELATION = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const ATTEMPT = "ffffffff-ffff-4fff-8fff-ffffffffffff";
const NOW = "2026-09-05T02:00:00Z";

function source(environment: "test" | "production" = "test") {
  return { source_id: "synthetic-contract-source", source_type: environment === "test" ? "test" : "official", environment, provider_id: "synthetic-provider", source_record_id: "synthetic-record", retrieved_at: NOW };
}

function candidate(id: string, rank: number, confidence: number, coverage: "known" | "unknown") {
  return {
    candidate_id: id, candidate_type: rank === 1 ? "address" : "parcel", normalized_identity: { synthetic: `candidate-${rank}` },
    display_identity: `Synthetic Candidate ${rank === 1 ? "One" : "Two"}`, source: source(), confidence, confidence_method: "deterministic-ranking-v1",
    ranking_trace: { method: "synthetic" }, rank, status: "plausible", coverage_status: coverage,
    coverage: coverage === "unknown" ? { limitation: "coverage_not_reported" } : { scope: "synthetic" },
    supporting_evidence_ids: rank === 2 ? [EVIDENCE] : [], supporting_identity_reference_ids: [NODE_ADDRESS],
    possible_existing_property_entity_id: null, needs_human_confirmation: true,
  };
}

function resolution(mode: "ambiguous" | "confirmed" | "candidate_rejected" = "ambiguous", blocking = false) {
  const confirmed = mode === "confirmed";
  const candidateRejected = mode === "candidate_rejected";
  return {
    resolution_id: RESOLUTION, workspace_id: WORKSPACE, case_id: null, state: confirmed ? "confirmed" : "ambiguous",
    input: { kind: "address", value: { text: "Synthetic Road observation" } },
    normalized_input: { address: "synthetic road observation" }, normalization_version: "identity-normalization-v1",
    coverage_status: "partial", coverage: { attempt_count: 1 }, ambiguity: confirmed ? "none" : "multiple_candidates",
    needs_human_confirmation: !confirmed, candidates: [candidate(CANDIDATE_ONE, 1, 1, "known"), candidate(CANDIDATE_TWO, 2, 0.62, "unknown")],
    conflicts: [{ conflict_id: "12121212-1212-4121-8121-121212121212", left_candidate_id: CANDIDATE_ONE, right_candidate_id: CANDIDATE_TWO, related_identity_reference_id: null, related_evidence_id: EVIDENCE, related_property_entity_id: null, category: "provider_disagreement", severity: blocking ? "blocking" : "warning", state: "requires_review" }],
    provider_attempts: [{ attempt_id: ATTEMPT, order: 1, strategy_id: "synthetic-v1", source: source(), status: "unavailable", coverage_status: "unavailable", coverage: { scope: "unavailable" }, result_count: 0, error_category: "provider_unavailable", error_code: "provider_not_configured", retryable: true, started_at: NOW, completed_at: NOW }],
    decisions: confirmed ? [{ decision_id: DECISION, decision_type: "confirmed", candidate_id: CANDIDATE_TWO, property_entity_id: PROPERTY, reason_code: null, resolution_version_observed: 1, decision_version: 2, actor_user_id: USER, decided_at: NOW }] : candidateRejected ? [{ decision_id: DECISION, decision_type: "candidate_rejected", candidate_id: CANDIDATE_TWO, property_entity_id: null, reason_code: "not_same_property", resolution_version_observed: 1, decision_version: 2, actor_user_id: USER, decided_at: NOW }] : [],
    selected_candidate_id: confirmed ? CANDIDATE_TWO : null, confirmed_property_entity_id: confirmed ? PROPERTY : null,
    version: confirmed || candidateRejected ? 2 : 1, created_by: USER, created_at: NOW, updated_at: NOW,
  };
}

function property() {
  return { property_entity_id: PROPERTY, workspace_id: WORKSPACE, lifecycle_state: "active", display_label: "Human-confirmed synthetic property", confirmation_summary: { available: true, human_confirmed: true, confirmation_id: CONFIRMATION, confirmed_at: NOW, confirmed_by: USER, resolution_id: RESOLUTION }, version: 1, created_at: NOW, updated_at: NOW };
}

function caseRecord(version: number, identityStatus: "unverified" | "confirmed") {
  return { case_id: CASE, workspace_id: WORKSPACE, purpose: "buy_due_diligence", status: "open", title: "Synthetic review Case", identity_status: identityStatus, assigned_member_id: null, version, opened_at: NOW, updated_at: NOW };
}

function error(code: string, message = "The request could not be completed.") {
  return { error: { code, message, request_id: "slice8-e2e-request", retryable: false } };
}

function syntheticToken(exp: number): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: USER, aud: "authenticated", role: "authenticated", exp })).toString("base64url");
  return `${header}.${payload}.synthetic`;
}

async function installSession(page: Page, expiresAt = 4102444800) {
  const session = { access_token: syntheticToken(expiresAt), token_type: "bearer", expires_in: 3600, expires_at: expiresAt, refresh_token: "synthetic-refresh", user: { id: USER, aud: "authenticated", role: "authenticated", email: "synthetic@example.invalid", app_metadata: {}, user_metadata: {}, created_at: NOW } };
  await page.addInitScript(({ key, serialized }) => window.localStorage.setItem(key, serialized), { key: "sb-slice8-auth-auth-token", serialized: JSON.stringify(session) });
}

async function routeContext(route: Route, role: "owner" | "admin" | "manager" | "member" | "viewer") {
  const path = new URL(route.request().url()).pathname;
  if (path === "/v1") return route.fulfill({ json: { status: "ok", principal: { user_id: USER }, features: { identity_v1: true, legacy_case_import_v1: false } } });
  if (path === `/v1/workspaces/${WORKSPACE}/context`) return route.fulfill({ json: { status: "ok", workspace_id: WORKSPACE, user_id: USER, role } });
  return false;
}

test("explicit rank-2 confirmation, bounded retry, property reads, and separate Case attachment", async ({ page }) => {
  await installSession(page);
  let confirmed = false;
  let confirmCalls = 0;
  const confirmKeys: string[] = [];
  let caseCalls = 0;
  let createCaseKey = "";
  let attachCalls = 0;
  const attachKeys: string[] = [];

  await page.route("http://e2e.test/v1**", async (route) => {
    if (await routeContext(route, "admin") !== false) return;
    const request = route.request(); const url = new URL(request.url()); const path = url.pathname;
    if (path === "/v1/property-resolutions" && request.method() === "POST") return route.fulfill({ status: 201, json: resolution() });
    if (path === `/v1/property-resolutions/${RESOLUTION}` && request.method() === "GET") return route.fulfill({ json: resolution(confirmed ? "confirmed" : "ambiguous") });
    if (path === `/v1/property-resolutions/${RESOLUTION}/confirm`) {
      confirmCalls += 1; confirmKeys.push(request.headers()["idempotency-key"] ?? "");
      expect(request.postDataJSON()).toMatchObject({ candidate_id: CANDIDATE_TWO, version: 1 });
      if (confirmCalls === 1) { await new Promise((resolve) => setTimeout(resolve, 180)); return route.abort("timedout"); }
      confirmed = true; return route.fulfill({ json: resolution("confirmed") });
    }
    if (path === `/v1/properties/${PROPERTY}` && request.method() === "GET") return route.fulfill({ json: property() });
    if (path === `/v1/properties/${PROPERTY}/graph`) return route.fulfill({ json: { property: property(), nodes: [{ node_id: NODE_PROPERTY, node_type: "property", record_id: PROPERTY, display_label: "Synthetic property", status: null, source: null, valid_from: null, valid_to: null }, { node_id: NODE_ADDRESS, node_type: "address", record_id: NODE_ADDRESS, display_label: "Synthetic address observation", status: "observed", source: source("production"), valid_from: NOW, valid_to: null }], relations: [{ relation_id: RELATION, from_node_id: NODE_PROPERTY, to_node_id: NODE_ADDRESS, relation_type: "property_address", direction: "directed", confidence: null, confidence_method: null, source: source("production"), evidence_id: EVIDENCE, status: "confirmed", valid_from: NOW, valid_to: null, supersedes_relation_id: null, created_at: NOW, confirmation_id: CONFIRMATION }], as_of: null, next_cursor: null } });
    if (path === `/v1/properties/${PROPERTY}/evidence`) return route.fulfill({ json: { property: property(), evidence: [{ evidence_id: EVIDENCE, workspace_id: WORKSPACE, fact_type: "address.observation", value: null, has_private_value_reference: true, value_schema: null, source: source("production"), effective_from: NOW, effective_to: null, expires_at: null, coverage_status: "unknown", coverage: { limitation: "not_verified" }, status: "unverified", quality_confidence: null, quality_method: null, quality_status: "not_checked", quality: { limitations: ["synthetic"] }, license_status: "unknown", license_reference: null, license: {}, lineage: {}, content_hash: "f".repeat(64), version: 1, supersedes_evidence_id: null, created_at: NOW }], next_cursor: null } });
    if (path === "/v1/cases" && request.method() === "POST") {
      caseCalls += 1; const key = request.headers()["idempotency-key"] ?? "";
      if (caseCalls === 1) createCaseKey = key; else expect(key).toBe(createCaseKey);
      return route.fulfill({ status: 201, json: caseRecord(caseCalls === 1 ? 1 : 2, "unverified") });
    }
    if (path === `/v1/cases/${CASE}/attach-resolution`) {
      attachCalls += 1; attachKeys.push(request.headers()["idempotency-key"] ?? "");
      if (attachCalls === 1) return route.fulfill({ status: 409, json: error("version_conflict", "The resource version has changed.") });
      expect(request.postDataJSON()).toEqual({ resolution_id: RESOLUTION, case_version: 2 });
      return route.fulfill({ json: { case: caseRecord(3, "confirmed"), link: { case_property_link_id: LINK, case_id: CASE, property_entity_id: PROPERTY, resolution_id: RESOLUTION, confirmation_id: CONFIRMATION, supersedes_case_property_link_id: null, attached_by: USER, attached_at: NOW } } });
    }
    return route.fulfill({ status: 404, json: error("not_found") });
  });

  await page.goto("/vnext/property-identity");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByLabel("Workspace UUID").fill(WORKSPACE);
  await page.getByTestId("load-workspace").click();
  await expect(page.getByTestId("workspace-role")).toContainText("admin");
  await page.getByRole("textbox", { name: "地址觀察", exact: true }).fill("Synthetic Road observation");
  await page.getByTestId("create-resolution").click();
  await expect(page.getByText(/存在歧義/)).toBeVisible();
  await expect(page.getByTestId("provider-unavailable")).toBeVisible();
  await expect(page.getByRole("radio", { name: /Synthetic Candidate One/ })).not.toBeChecked();
  await expect(page.getByRole("radio", { name: /Synthetic Candidate Two/ })).not.toBeChecked();
  await expect(page.getByText(/信心參考: 100%/)).toBeVisible();
  expect(confirmCalls).toBe(0);
  await page.getByRole("radio", { name: /Synthetic Candidate Two/ }).check();
  await expect(page.getByText(/信心參考: 62%/)).toBeVisible();
  const confirmButton = page.getByTestId("confirm-resolution");
  await expect(confirmButton).toBeDisabled();
  await page.getByLabel(/我已檢視所選候選/).check();
  await page.getByLabel(/我明確要以人工判斷/).check();
  await page.getByLabel("確認理由").fill("Human reviewed the synthetic source and limitations.");
  await expect(confirmButton).toBeEnabled();
  await confirmButton.dblclick();
  await expect(page.locator('[role="alert"]').filter({ hasText: "結果未知" })).toBeVisible();
  expect(confirmCalls).toBe(1);
  await confirmButton.click();
  await expect(page.getByText("Human-confirmed synthetic property")).toBeVisible();
  expect(confirmCalls).toBe(2);
  expect(confirmKeys[0]).toBe(confirmKeys[1]);
  expect(attachCalls).toBe(0);

  await page.getByRole("button", { name: "載入關係圖" }).click();
  await expect(page.getByText(/property address/)).toBeVisible();
  await page.getByRole("button", { name: "載入證據" }).click();
  await expect(page.getByText(/Private value present: yes \(reference not exposed\)/)).toBeVisible();

  await page.getByLabel("案件標題").fill("Synthetic review Case");
  await page.getByTestId("create-case").click();
  await expect(page.getByText("Identity: unverified")).toBeVisible();
  expect(attachCalls).toBe(0);
  await page.getByTestId("attach-case").click();
  await expect(page.locator('[role="alert"]').filter({ hasText: "案件已變更" })).toBeVisible();
  await expect(page.getByText("Version: 2")).toBeVisible();
  await page.getByTestId("attach-case").click();
  await expect(page.getByTestId("case-attached")).toBeVisible();
  expect(attachCalls).toBe(2);
  expect(attachKeys[0]).not.toBe(attachKeys[1]);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});

for (const role of ["viewer", "member", "manager", "owner", "admin"] as const) {
  test(`${role} confirmation presentation follows workspace context`, async ({ page }) => {
    await installSession(page);
    await page.route("http://e2e.test/v1**", async (route) => {
      if (await routeContext(route, role) !== false) return;
      const path = new URL(route.request().url()).pathname;
      if (path === `/v1/property-resolutions/${RESOLUTION}`) return route.fulfill({ json: resolution() });
      return route.fulfill({ status: 404, json: error("not_found") });
    });
    await page.goto("/vnext/property-identity");
    await page.getByLabel("解析 ID").fill(RESOLUTION);
    await page.getByTestId("open-resolution").click();
    await expect(page.getByTestId("workspace-role")).toContainText(role);
    const confirm = page.getByTestId("confirm-resolution");
    if (role === "owner" || role === "admin") await expect(confirm).toBeVisible();
    else await expect(confirm).toHaveCount(0);
  });
}

test("blocking conflict disables confirmation and malformed DTO fails closed", async ({ page }) => {
  await installSession(page);
  let malformed = false;
  await page.route("http://e2e.test/v1**", async (route) => {
    if (await routeContext(route, "owner") !== false) return;
    const path = new URL(route.request().url()).pathname;
    if (path === `/v1/property-resolutions/${RESOLUTION}`) return route.fulfill({ json: malformed ? { ...resolution(), state: "verified" } : resolution("ambiguous", true) });
    return route.fulfill({ status: 404, json: error("not_found") });
  });
  await page.goto("/vnext/property-identity");
  await page.getByLabel("解析 ID").fill(RESOLUTION);
  await page.getByTestId("open-resolution").click();
  await expect(page.getByText(/存在阻擋衝突/)).toBeVisible();
  await page.getByRole("radio", { name: /Synthetic Candidate Two/ }).check();
  await page.getByLabel(/我已檢視所選候選/).check();
  await page.getByLabel(/我明確要以人工判斷/).check();
  await page.getByLabel("確認理由").fill("Explicit human review of blocking evidence.");
  await expect(page.getByTestId("confirm-resolution")).toBeDisabled();
  malformed = true;
  await page.getByTestId("open-resolution").click();
  await expect(page.locator('[role="alert"]').filter({ hasText: "失敗關閉" })).toBeVisible();
});

test("cross-workspace not-found remains generic", async ({ page }) => {
  await installSession(page);
  await page.route("http://e2e.test/v1**", async (route) => {
    if (new URL(route.request().url()).pathname === "/v1") return routeContext(route, "viewer");
    return route.fulfill({ status: 404, json: error("not_found", "The requested resource was not found.") });
  });
  await page.goto("/vnext/property-identity");
  await page.getByLabel("解析 ID").fill("abababab-abab-4bab-8bab-abababababab");
  await page.getByTestId("open-resolution").click();
  const hidden = page.locator('[role="alert"]').filter({ hasText: "無權查看" });
  await expect(hidden).toBeVisible();
  await expect(hidden).not.toContainText("workspace");
});

test("disabled feature never exposes a working identity form", async ({ page }) => {
  await installSession(page);
  await page.route("http://e2e.test/v1", (route) => route.fulfill({ json: { status: "ok", principal: { user_id: USER }, features: { identity_v1: false, legacy_case_import_v1: true } } }));
  await page.goto("/vnext/property-identity");
  await expect(page.getByText(/尚未在後端開放/)).toBeVisible();
  await expect(page.getByTestId("create-resolution")).toHaveCount(0);
});

test("missing session blocks BFF traffic and expired session refreshes through public Auth", async ({ page }) => {
  let bffCalls = 0;
  await page.route("http://e2e.test/v1", (route) => { bffCalls += 1; return route.fulfill({ json: { status: "ok", principal: { user_id: USER }, features: { identity_v1: true, legacy_case_import_v1: false } } }); });
  await page.goto("/vnext/property-identity");
  await expect(page.getByText(/Supabase 登入工作階段/)).toBeVisible();
  expect(bffCalls).toBe(0);

  const refreshedToken = syntheticToken(4102444800);
  let refreshCalls = 0;
  await installSession(page, 1);
  await page.route(/^https:\/\/slice8-auth\.supabase\.co\/auth\/v1\/token/, async (route) => {
    refreshCalls += 1;
    expect(new URL(route.request().url()).searchParams.get("grant_type")).toBe("refresh_token");
    expect(route.request().headers().apikey).toBe("sb_publishable_slice8_e2e_public_only");
    expect(route.request().postDataJSON()).toEqual({ refresh_token: "synthetic-refresh" });
    return route.fulfill({ json: { access_token: refreshedToken, refresh_token: "synthetic-rotated", expires_in: 3600 } });
  });
  await page.reload();
  await expect.poll(() => refreshCalls).toBe(1);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByTestId("load-workspace")).toBeVisible();
  expect(bffCalls).toBe(1);
  const storedShape = await page.evaluate(() => {
    const raw = window.localStorage.getItem("sb-slice8-auth-auth-token");
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null || !("access_token" in value) || !("refresh_token" in value) || typeof value.access_token !== "string" || typeof value.refresh_token !== "string") return null;
    const encoded = value.access_token.split(".")[1].replaceAll("-", "+").replaceAll("_", "/");
    const decoded: unknown = JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, "=")));
    return { tokenLength: value.access_token.length, refreshLength: value.refresh_token.length, decoded };
  });
  expect(storedShape).toMatchObject({ tokenLength: expect.any(Number), refreshLength: expect.any(Number), decoded: { exp: 4102444800 } });
});

test("explicit candidate rejection survives server refresh with candidate history", async ({ page }) => {
  await installSession(page);
  let rejected = false;
  await page.route("http://e2e.test/v1**", async (route) => {
    if (await routeContext(route, "owner") !== false) return;
    const request = route.request(); const path = new URL(request.url()).pathname;
    if (path === `/v1/property-resolutions/${RESOLUTION}/reject`) {
      expect(request.postDataJSON()).toEqual({ candidate_id: CANDIDATE_TWO, version: 1, reason_code: "not_same_property" });
      rejected = true; return route.fulfill({ json: resolution("candidate_rejected") });
    }
    if (path === `/v1/property-resolutions/${RESOLUTION}`) return route.fulfill({ json: resolution(rejected ? "candidate_rejected" : "ambiguous") });
    return route.fulfill({ status: 404, json: error("not_found") });
  });
  await page.goto("/vnext/property-identity");
  await page.getByLabel("解析 ID").fill(RESOLUTION);
  await page.getByTestId("open-resolution").click();
  await page.getByRole("radio", { name: /Synthetic Candidate Two/ }).check();
  await page.getByTestId("reject-resolution").click();
  await expect(page.getByText(/candidate rejected/)).toBeVisible();
  await expect(page.getByText("Synthetic Candidate Two")).toBeVisible();
});
