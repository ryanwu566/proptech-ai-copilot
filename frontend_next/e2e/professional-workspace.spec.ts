import type { Page, Route } from "@playwright/test";
import { expect, test } from "./fixtures";

const CASE_ID = "11111111-1111-4111-8111-111111111111";
const WORKSPACE_ID = "22222222-2222-4222-8222-222222222222";
const PROPERTY_ID = "33333333-3333-4333-8333-333333333333";
const USER_ID = "44444444-4444-4444-8444-444444444444";
const PROPERTY_NODE_ID = "55555555-5555-4555-8555-555555555555";
const PARCEL_SET_ID = "66666666-6666-4666-8666-666666666666";
const MEMBER_A = "77777777-7777-4777-8777-777777777777";
const MEMBER_B = "88888888-8888-4888-8888-888888888888";
const MEMBER_C = "99999999-9999-4999-8999-999999999999";
const REF_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const REF_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const REF_C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const NOW = "2026-09-20T08:00:00Z";
const NEXT_CURSOR = `next.${"a".repeat(43)}`;

function accessToken(exp = 4_102_444_800): string {
  const header = Buffer.from(JSON.stringify({ alg: "ES256", typ: "JWT", kid: "workspace-e2e-key" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({
    sub: USER_ID,
    aud: "authenticated",
    role: "authenticated",
    iss: "https://slice8-auth.supabase.co/auth/v1",
    exp,
  })).toString("base64url");
  return `${header}.${payload}.test-signature`;
}

async function installSession(page: Page): Promise<string> {
  const token = accessToken();
  const session = {
    access_token: token,
    token_type: "bearer",
    expires_in: 3600,
    expires_at: 4_102_444_800,
    refresh_token: "workspace-e2e-refresh",
    user: {
      id: USER_ID,
      aud: "authenticated",
      role: "authenticated",
      email: "workspace@example.invalid",
      app_metadata: {},
      user_metadata: {},
      created_at: NOW,
    },
  };
  await page.addInitScript(({ serialized }) => {
    window.localStorage.setItem("sb-slice8-auth-auth-token", serialized);
  }, { serialized: JSON.stringify(session) });
  return token;
}

function propertyDto() {
  return {
    property_entity_id: PROPERTY_ID,
    workspace_id: WORKSPACE_ID,
    lifecycle_state: "unverified",
    display_label: "Test-only property context",
    confirmation_summary: {
      available: false,
      human_confirmed: false,
      confirmation_id: null,
      confirmed_at: null,
      confirmed_by: null,
      resolution_id: null,
    },
    version: 1,
    created_at: NOW,
    updated_at: NOW,
  };
}

function sourceDto() {
  return {
    source_id: "approved-source",
    source_type: "official",
    environment: "production",
    provider_id: "provider-id-must-not-leak",
    source_record_id: "source-record-id-must-not-leak",
    retrieved_at: NOW,
  };
}

function parcelNode(nodeId: string, referenceId: string, displayLabel: string) {
  return {
    node_id: nodeId,
    node_type: "parcel",
    record_id: referenceId,
    display_label: displayLabel,
    status: "observed",
    source: sourceDto(),
    valid_from: null,
    valid_to: null,
  };
}

function propertyGraphNode() {
  return {
    node_id: PROPERTY_NODE_ID,
    node_type: "property",
    record_id: PROPERTY_ID,
    display_label: "Test-only property context",
    status: null,
    source: null,
    valid_from: null,
    valid_to: null,
  };
}

function parcelMember(
  memberId: string,
  referenceId: string,
  position: number,
  reviewStatus: "candidate" | "case_selected" | "case_rejected",
) {
  return {
    parcel_set_member_id: memberId,
    parcel_identity_reference_id: referenceId,
    position,
    review_status: reviewStatus,
    created_at: NOW,
    updated_at: NOW,
  };
}

function parcelSetDto(overrides: Record<string, unknown> = {}) {
  return {
    parcel_set_id: PARCEL_SET_ID,
    workspace_id: WORKSPACE_ID,
    case_id: CASE_ID,
    status: "draft",
    version: 1,
    active_member_id: null,
    created_at: NOW,
    updated_at: NOW,
    reviewed_at: null,
    members: [],
    ...overrides,
  };
}

function evidenceItem() {
  return {
    evidence_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    workspace_id: WORKSPACE_ID,
    fact_type: "parcel.observation",
    value: { secret: "evidence-value-must-not-leak", normalized_identity: "normalized-identity-must-not-leak" },
    has_private_value_reference: false,
    value_schema: "parcel-observation-v1",
    source: sourceDto(),
    effective_from: null,
    effective_to: null,
    expires_at: null,
    coverage_status: "known",
    coverage: {},
    status: "available",
    quality_confidence: 0.9,
    quality_method: "bounded-test",
    quality_status: "passed",
    quality: {},
    license_status: "approved",
    license_reference: null,
    license: {},
    lineage: { actor: "actor-id-must-not-leak" },
    content_hash: "a".repeat(64),
    version: 1,
    supersedes_evidence_id: null,
    created_at: NOW,
  };
}

type ApprovedReadOptions = {
  workspaceStatus?: number;
  property?: Record<string, unknown>;
  graphNodes?: Record<string, unknown>[];
  evidence?: Record<string, unknown>[];
  parcelStatus?: number;
  parcelErrorCode?: "authentication_required" | "permission_denied" | "not_found" | "internal_error";
  parcel?: Record<string, unknown>;
  parcelBody?: string;
  parcelAbort?: boolean;
};

async function fulfillApprovedRead(
  route: Route,
  token: string,
  requestedPaths: string[],
  nextCursor: string | null = null,
  options: ApprovedReadOptions = {},
): Promise<void> {
  const request = route.request();
  const url = new URL(request.url());
  requestedPaths.push(url.pathname);
  expect(request.method()).toBe("GET");
  expect(request.headers().authorization).toBe(`Bearer ${token}`);
  expect(url.searchParams.has("access_token")).toBe(false);

  if (url.pathname === `/v1/workspaces/${WORKSPACE_ID}/context`) {
    if (options.workspaceStatus) {
      await route.fulfill({ status: options.workspaceStatus, json: { error: { code: options.workspaceStatus === 403 ? "permission_denied" : "not_found", message: "Unavailable.", request_id: "workspace-e2e", retryable: false } } });
      return;
    }
    await route.fulfill({ json: { status: "ok", workspace_id: WORKSPACE_ID, user_id: USER_ID, role: "member" } });
    return;
  }
  if (url.pathname === `/v1/properties/${PROPERTY_ID}`) {
    await route.fulfill({ json: options.property ?? propertyDto() });
    return;
  }
  if (url.pathname === `/v1/properties/${PROPERTY_ID}/graph`) {
    await route.fulfill({ json: {
      property: propertyDto(),
      nodes: options.graphNodes ?? [propertyGraphNode()],
      relations: [],
      as_of: null,
      next_cursor: nextCursor,
    } });
    return;
  }
  if (url.pathname === `/v1/properties/${PROPERTY_ID}/evidence`) {
    await route.fulfill({ json: { property: propertyDto(), evidence: options.evidence ?? [], next_cursor: nextCursor } });
    return;
  }
  if (url.pathname === `/v1/cases/${CASE_ID}/parcel-set`) {
    if (options.parcelAbort) {
      await route.abort("connectionfailed");
      return;
    }
    if (options.parcelBody !== undefined) {
      await route.fulfill({ status: options.parcelStatus ?? 200, contentType: "application/json", body: options.parcelBody });
      return;
    }
    if (options.parcelStatus && options.parcelStatus !== 200) {
      await route.fulfill({ status: options.parcelStatus, json: { error: {
        code: options.parcelErrorCode ?? (options.parcelStatus === 403 ? "permission_denied" : "not_found"),
        message: "Unavailable.",
        request_id: "workspace-e2e",
        retryable: options.parcelStatus >= 500,
      } } });
      return;
    }
    await route.fulfill({ json: options.parcel ?? parcelSetDto() });
    return;
  }
  await route.fulfill({ status: 404, json: { error: { code: "not_found", message: "Not found.", request_id: "workspace-e2e", retryable: false } } });
}

test("invalid case identifiers fail closed before authentication", async ({ page }) => {
  const response = await page.goto("/workspace/not-a-uuid");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "找不到這個頁面" })).toBeVisible();
  await expect(page.getByLabel("電子郵件")).toHaveCount(0);
});

test("an unauthenticated workspace route reuses the existing VNext auth gate", async ({ page }) => {
  await page.goto(`/workspace/${CASE_ID}`);
  await expect(page.getByRole("heading", { name: "登入後查看房產識別" })).toBeVisible();
  await expect(page.getByLabel("電子郵件")).toBeVisible();
  await expect(page.getByLabel("密碼")).toBeVisible();
  await expect(page.getByRole("button", { name: "登入" })).toBeVisible();
});

test("missing property context renders a bounded shell without backend reads", async ({ page }) => {
  await installSession(page);
  const backendRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).hostname === "e2e.test") backendRequests.push(request.url());
  });
  await page.goto(`/workspace/${CASE_ID}`);

  await expect(page.getByRole("heading", { level: 1, name: "Professional Workspace" })).toBeVisible();
  await expect(page.getByText(CASE_ID, { exact: true })).toBeVisible();
  await expect(page.getByText("Case details are not available from an approved read contract.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Map Canvas" })).toContainText("NOT_AVAILABLE");
  await expect(page.getByRole("complementary", { name: "Evidence Rail" })).toContainText("PARTIAL");
  await expect(page.getByRole("region", { name: "Task Panel" })).toContainText("NOT_AVAILABLE");
  await expect(page.getByRole("region", { name: "Copilot" })).toContainText("NOT_AVAILABLE");
  await expect(page.getByRole("region", { name: "Activity Timeline" })).toContainText("NOT_AVAILABLE");
  expect(backendRequests).toEqual([]);
});

test("partial or malformed workspace context fails closed without backend reads", async ({ page }) => {
  await installSession(page);
  const backendRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).hostname === "e2e.test") backendRequests.push(request.url());
  });
  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=not-a-uuid`);

  const contextHeader = page.getByRole("banner", { name: "Workspace context" });
  await expect(contextHeader.getByRole("alert")).toContainText("must both be supplied as valid UUIDs");
  await expect(contextHeader).toContainText("WorkspaceNot loaded");
  await expect(contextHeader).toContainText("PropertyEntityNot loaded");
  await expect(page.getByRole("complementary", { name: "Evidence Rail" })).toContainText("NOT_AVAILABLE");
  expect(backendRequests).toEqual([]);
});

test("validated workspace and property context uses only approved reads and keeps empty evidence empty", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  const directDataApiRequests: string[] = [];
  const approvedRequests: Array<{ method: string; pathname: string; hostname: string }> = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.hostname === "e2e.test") approvedRequests.push({ method: request.method(), pathname: url.pathname, hostname: url.hostname });
    if (url.hostname.endsWith(".supabase.co") && url.pathname.startsWith("/rest/v1")) {
      directDataApiRequests.push(request.url());
    }
  });
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  await expect(page.getByRole("heading", { level: 1, name: "Professional Workspace" })).toBeVisible();
  await expect(page.getByRole("banner", { name: "Workspace context" })).toContainText(WORKSPACE_ID);
  await expect(page.getByRole("banner", { name: "Workspace context" })).toContainText(PROPERTY_ID);
  await expect(page.getByRole("banner", { name: "Workspace context" })).toContainText("Test-only property context");
  await expect(page.getByRole("complementary", { name: "Evidence Rail" })).toContainText("AVAILABLE");
  await expect(page.getByText("No evidence items were returned by the approved evidence interface.")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Workspace modules" })).toBeVisible();

  await expect(page.getByRole("button", { name: /Parcel\/GIS.*PARTIAL/ })).toBeVisible();
  const emptyParcelCanvas = page.getByRole("region", { name: "Map Canvas" });
  await expect(emptyParcelCanvas).toContainText("DRAFT");
  await expect(emptyParcelCanvas).toContainText("Version 1");
  await expect(emptyParcelCanvas).toContainText("Parcel review set loaded; no members are currently recorded.");
  for (const moduleName of ["Building", "Planning", "Market", "Listings", "Title/Documents", "CRM", "Decision"]) {
    await expect(page.getByRole("button", { name: new RegExp(`${moduleName}.*NOT_AVAILABLE`) })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: /Identity.*AVAILABLE/ })).toBeVisible();
  await expect(page.getByText("NOT_AVAILABLE — approved interfaces do not provide a module-specific freshness summary.")).toBeVisible();
  await expect(page.getByText("NOT_AVAILABLE — no durable professional task or next-step contract exists.")).toBeVisible();
  await page.getByRole("button", { name: /Planning.*NOT_AVAILABLE/ }).click();
  await expect(page.getByRole("region", { name: "Module Detail" })).toContainText("No planning, zoning, or redevelopment backend contract is available.");
  await expect(page.getByText("NOT_AVAILABLE — approved interfaces do not provide a module-specific freshness summary.")).toBeVisible();

  expect(new Set(requestedPaths)).toEqual(new Set([
    `/v1/workspaces/${WORKSPACE_ID}/context`,
    `/v1/properties/${PROPERTY_ID}`,
    `/v1/properties/${PROPERTY_ID}/graph`,
    `/v1/properties/${PROPERTY_ID}/evidence`,
    `/v1/cases/${CASE_ID}/parcel-set`,
  ]));
  await expect(page.locator("body")).not.toContainText(token);
  expect(new URL(page.url()).searchParams.has("access_token")).toBe(false);
  expect(directDataApiRequests).toEqual([]);
  expect(approvedRequests.filter((request) => request.pathname.endsWith("/parcel-set"))).toEqual([{
    method: "GET",
    pathname: `/v1/cases/${CASE_ID}/parcel-set`,
    hostname: "e2e.test",
  }]);
  expect(approvedRequests.every((request) => request.method === "GET")).toBe(true);
  expect(requestedPaths.indexOf(`/v1/workspaces/${WORKSPACE_ID}/context`)).toBeLessThan(requestedPaths.indexOf(`/v1/properties/${PROPERTY_ID}`));
  expect(requestedPaths.indexOf(`/v1/properties/${PROPERTY_ID}`)).toBeLessThan(requestedPaths.indexOf(`/v1/cases/${CASE_ID}/parcel-set`));
});

test("workspace denial prevents PropertyEntity and Parcel Set reads", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => (
    fulfillApprovedRead(route, token, requestedPaths, null, { workspaceStatus: 403 })
  ));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  await expect(page.getByRole("banner", { name: "Workspace context" }).getByRole("alert")).toContainText("not available to this account");
  expect(requestedPaths).toEqual([`/v1/workspaces/${WORKSPACE_ID}/context`]);
});

test("PropertyEntity workspace mismatch prevents graph Evidence and Parcel Set reads", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    property: { ...propertyDto(), workspace_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee" },
  }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  await expect(page.getByRole("banner", { name: "Workspace context" }).getByRole("alert")).toContainText("could not be loaded");
  expect(requestedPaths).toEqual([
    `/v1/workspaces/${WORKSPACE_ID}/context`,
    `/v1/properties/${PROPERTY_ID}`,
  ]);
});

test("feature unavailable or 404 remains ambiguous and is not an empty parcel set", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    parcelStatus: 404,
    parcelErrorCode: "not_found",
  }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const canvas = page.getByRole("region", { name: "Map Canvas" });
  await expect(canvas).toContainText("PARCEL_SET_NOT_AVAILABLE");
  await expect(canvas).toContainText("The approved Case Parcel Set interface did not return an available set.");
  await expect(canvas).not.toContainText("no members are currently recorded");
  await expect(page.getByRole("button", { name: /Parcel\/GIS.*NOT_AVAILABLE/ })).toBeVisible();
});

test("Parcel Set permission denial is not converted to unavailable or empty", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    parcelStatus: 403,
    parcelErrorCode: "permission_denied",
  }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const canvas = page.getByRole("region", { name: "Map Canvas" });
  await expect(canvas).toContainText("PARCEL_SET_DENIED");
  await expect(canvas).toContainText("The Case Parcel Set read was denied.");
  await expect(canvas).not.toContainText("PARCEL_SET_NOT_AVAILABLE");
  await expect(canvas).not.toContainText("no members are currently recorded");
});

for (const scenario of [
  { name: "403 with not_found code", parcelStatus: 403, parcelErrorCode: "not_found" as const },
  { name: "404 with permission_denied code", parcelStatus: 404, parcelErrorCode: "permission_denied" as const },
]) {
  test(`Parcel Set permission denial takes precedence for ${scenario.name}`, async ({ page }) => {
    const token = await installSession(page);
    const requestedPaths: string[] = [];
    await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
      parcelStatus: scenario.parcelStatus,
      parcelErrorCode: scenario.parcelErrorCode,
    }));

    await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

    const canvas = page.getByRole("region", { name: "Map Canvas" });
    await expect(canvas).toContainText("PARCEL_SET_DENIED");
    await expect(canvas).not.toContainText("PARCEL_SET_NOT_AVAILABLE");
  });
}

for (const scenario of [
  { name: "malformed DTO", parcel: parcelSetDto({ version: 0 }) },
  { name: "Case mismatch", parcel: parcelSetDto({ case_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee" }) },
  { name: "Workspace mismatch", parcel: parcelSetDto({ workspace_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee" }) },
]) {
  test(`Parcel Set ${scenario.name} fails closed`, async ({ page }) => {
    const token = await installSession(page);
    const requestedPaths: string[] = [];
    await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
      parcel: scenario.parcel,
    }));

    await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

    const canvas = page.getByRole("region", { name: "Map Canvas" });
    await expect(canvas).toContainText("PARCEL_SET_INVALID_RESPONSE");
    await expect(canvas).not.toContainText("no members are currently recorded");
    await expect(canvas).not.toContainText(PARCEL_SET_ID);
  });
}

test("Parcel Set malformed JSON fails closed", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    parcelBody: "{",
  }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const canvas = page.getByRole("region", { name: "Map Canvas" });
  await expect(canvas).toContainText("PARCEL_SET_INVALID_RESPONSE");
  await expect(canvas).not.toContainText("no members are currently recorded");
  await expect(canvas).not.toContainText(PARCEL_SET_ID);
});

test("Parcel Set infrastructure failure is not converted to an empty state", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, { parcelAbort: true }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const canvas = page.getByRole("region", { name: "Map Canvas" });
  await expect(canvas).toContainText("PARCEL_SET_ERROR");
  await expect(canvas).not.toContainText("no members are currently recorded");
});

test("Parcel Set session failure remains distinct", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    parcelStatus: 401,
    parcelErrorCode: "authentication_required",
  }));
  await page.route("https://slice8-auth.supabase.co/auth/v1/**", (route) => route.fulfill({ status: 204 }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  await expect.poll(() => requestedPaths.filter((path) => path.endsWith("/parcel-set")).length).toBe(1);
  await expect(page.getByRole("region", { name: "Map Canvas" })).toHaveCount(0);
  await expect(page.locator("form")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("PARCEL_SET_NOT_AVAILABLE");
  await expect(page.locator("body")).not.toContainText("no members are currently recorded");
});

test("loaded parcel review states remain Case-local and graph cross-reference fails closed", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  const members = [
    parcelMember(MEMBER_A, REF_A, 1, "candidate"),
    parcelMember(MEMBER_B, REF_B, 5, "case_selected"),
    parcelMember(MEMBER_C, REF_C, 9, "case_rejected"),
  ];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, NEXT_CURSOR, {
    parcel: parcelSetDto({ status: "case_reviewed", version: 4, active_member_id: MEMBER_A, reviewed_at: NOW, members }),
    graphNodes: [
      propertyGraphNode(),
      parcelNode("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", REF_B, "Exact parcel label"),
      parcelNode("ffffffff-ffff-4fff-8fff-ffffffffffff", REF_C, "Duplicate parcel label A"),
      parcelNode("12121212-1212-4121-8121-121212121212", REF_C, "Duplicate parcel label B"),
    ],
  }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const canvas = page.getByRole("region", { name: "Map Canvas" });
  await expect(canvas.getByLabel("Readiness: PARTIAL")).toBeVisible();
  await expect(canvas.getByRole("heading", { level: 3, name: "Parcel review set" })).toBeVisible();
  await expect(canvas).toContainText("CASE REVIEWED");
  await expect(canvas).toContainText("Version 4");
  const candidates = canvas.getByRole("list", { name: "Parcel candidates" });
  await expect(candidates.getByRole("listitem")).toHaveCount(3);

  const candidate = candidates.getByRole("listitem").filter({ hasText: REF_A });
  await expect(candidate).toContainText("CANDIDATE");
  await expect(candidate).toContainText("Active review focusYes");
  await expect(candidate).toContainText("Reference not present in the loaded PropertyEntity graph page.");

  const selected = candidates.getByRole("listitem").filter({ hasText: REF_B });
  await expect(selected).toContainText("CASE_SELECTED");
  await expect(selected).toContainText("Active review focusNo");
  await expect(selected).toContainText("Also present in the currently loaded PropertyEntity graph page.");
  await expect(selected).toContainText("Exact parcel label");
  await expect(selected).toContainText("approved-source / production");

  const rejected = candidates.getByRole("listitem").filter({ hasText: REF_C });
  await expect(rejected).toContainText("CASE_REJECTED");
  await expect(rejected).toContainText("Cross-reference ambiguous; approved metadata is unavailable.");
  await expect(canvas).not.toContainText("Duplicate parcel label A");
  await expect(canvas).not.toContainText("Duplicate parcel label B");

  await expect(canvas).toContainText("Additional graph records are available; parcel cross-reference may be incomplete.");
  await expect(canvas).toContainText("Case parcel review state does not confirm canonical Property Identity or legal parcel boundaries.");
  await expect(canvas).toContainText("Case-to-Property binding is not available from an approved read in this workspace slice.");
  await expect(page.getByRole("banner", { name: "Workspace context" })).toContainText("Case details are not available from an approved read contract.");
});

test("active review focus summary stays Case-local when graph metadata is available", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    parcel: parcelSetDto({
      active_member_id: MEMBER_A,
      members: [parcelMember(MEMBER_A, REF_A, 1, "case_selected")],
    }),
    graphNodes: [
      propertyGraphNode(),
      parcelNode("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", REF_A, "Graph label is not Case-local truth"),
    ],
  }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const canvas = page.getByRole("region", { name: "Map Canvas" });
  const activeFocus = canvas.getByText("Active review focus (Case-local)", { exact: true }).locator("..");
  await expect(activeFocus).toContainText(REF_A);
  await expect(activeFocus).not.toContainText("Graph label is not Case-local truth");
});

test("Parcel investigation renders no geometry and leaks no hidden graph Evidence or credential data", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  const outbound: Array<{ method: string; url: string }> = [];
  page.on("request", (request) => outbound.push({ method: request.method(), url: request.url() }));
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    parcel: parcelSetDto({ members: [parcelMember(MEMBER_A, REF_A, 1, "case_selected")] }),
    graphNodes: [propertyGraphNode(), parcelNode("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", REF_A, "Safe parcel label")],
    evidence: [evidenceItem()],
  }));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const canvas = page.getByRole("region", { name: "Map Canvas" });
  await expect(canvas).toContainText("Geometry");
  await expect(canvas).toContainText("NOT_AVAILABLE");
  await expect(canvas).toContainText("No approved parcel geometry is available in this slice.");
  await expect(canvas.locator(".leaflet-container, svg, canvas, [data-testid*='marker']")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(token);
  for (const hidden of [
    "source-record-id-must-not-leak",
    "provider-id-must-not-leak",
    "evidence-value-must-not-leak",
    "normalized-identity-must-not-leak",
    "actor-id-must-not-leak",
  ]) {
    await expect(page.locator("body")).not.toContainText(hidden);
  }
  const apiRequests = outbound.filter(({ url }) => new URL(url).hostname === "e2e.test");
  expect(apiRequests.every(({ method }) => method === "GET")).toBe(true);
  expect(outbound.some(({ url }) => /nlsc|tile|provider/i.test(new URL(url).hostname))).toBe(false);
  expect(outbound.some(({ url }) => new URL(url).hostname.endsWith(".supabase.co") && new URL(url).pathname.startsWith("/rest/v1"))).toBe(false);
});

test("loaded Parcel GIS remains keyboard-safe and responsive on mobile and tablet", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => fulfillApprovedRead(route, token, requestedPaths, null, {
    parcel: parcelSetDto({ members: [parcelMember(MEMBER_A, REF_A, 1, "candidate")] }),
  }));

  for (const viewport of [{ width: 390, height: 844 }, { width: 820, height: 1180 }]) {
    await page.setViewportSize(viewport);
    await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);
    const parcelButton = page.getByRole("button", { name: /Parcel\/GIS.*PARTIAL/ });
    await parcelButton.focus();
    await expect(parcelButton).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(parcelButton).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("region", { name: "Module Detail" })).toContainText("Parcel/GIS");
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  }
});

test("paginated graph and evidence reads disclose that the loaded records are partial", async ({ page }) => {
  const token = await installSession(page);
  const requestedPaths: string[] = [];
  await page.route("http://e2e.test/v1/**", (route) => (
    fulfillApprovedRead(route, token, requestedPaths, NEXT_CURSOR)
  ));

  await page.goto(`/workspace/${CASE_ID}?workspaceId=${WORKSPACE_ID}&propertyId=${PROPERTY_ID}`);

  const evidenceRail = page.getByRole("complementary", { name: "Evidence Rail" });
  await expect(evidenceRail).toContainText("Additional evidence records are available.");
  await expect(evidenceRail.getByLabel("Readiness: PARTIAL")).toBeVisible();

  const identityModule = page.getByRole("button", { name: "Identity Readiness: PARTIAL" });
  await expect(identityModule).toBeVisible();
  await identityModule.click();

  const moduleDetail = page.getByRole("region", { name: "Module Detail" });
  await expect(moduleDetail.getByLabel("Readiness: PARTIAL")).toBeVisible();
  await expect(moduleDetail).toContainText("Loaded page: 1 node · 0 relations. Additional graph records are available.");
  await expect(page.getByRole("region", { name: "Map Canvas" })).toContainText("Additional graph records are available; parcel cross-reference may be incomplete.");
});

test("workspace landmarks remain usable on a narrow viewport", async ({ page }) => {
  await installSession(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/workspace/${CASE_ID}`);

  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Workspace modules" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Module Detail" })).toBeVisible();
  await page.getByRole("button", { name: /Parcel\/GIS.*NOT_AVAILABLE/ }).focus();
  await expect(page.getByRole("button", { name: /Parcel\/GIS.*NOT_AVAILABLE/ })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});

test("the consumer homepage does not expose the professional workspace", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#main-content")).toBeVisible();
  await expect(page.getByRole("link", { name: /Professional Workspace/i })).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});
