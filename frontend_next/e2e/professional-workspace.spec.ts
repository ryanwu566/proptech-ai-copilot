import type { Page, Route } from "@playwright/test";
import { expect, test } from "./fixtures";

const CASE_ID = "11111111-1111-4111-8111-111111111111";
const WORKSPACE_ID = "22222222-2222-4222-8222-222222222222";
const PROPERTY_ID = "33333333-3333-4333-8333-333333333333";
const USER_ID = "44444444-4444-4444-8444-444444444444";
const PROPERTY_NODE_ID = "55555555-5555-4555-8555-555555555555";
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

async function fulfillApprovedRead(
  route: Route,
  token: string,
  requestedPaths: string[],
  nextCursor: string | null = null,
): Promise<void> {
  const request = route.request();
  const url = new URL(request.url());
  requestedPaths.push(url.pathname);
  expect(request.method()).toBe("GET");
  expect(request.headers().authorization).toBe(`Bearer ${token}`);
  expect(url.searchParams.has("access_token")).toBe(false);

  if (url.pathname === `/v1/workspaces/${WORKSPACE_ID}/context`) {
    await route.fulfill({ json: { status: "ok", workspace_id: WORKSPACE_ID, user_id: USER_ID, role: "member" } });
    return;
  }
  if (url.pathname === `/v1/properties/${PROPERTY_ID}`) {
    await route.fulfill({ json: propertyDto() });
    return;
  }
  if (url.pathname === `/v1/properties/${PROPERTY_ID}/graph`) {
    await route.fulfill({ json: {
      property: propertyDto(),
      nodes: [{
        node_id: PROPERTY_NODE_ID,
        node_type: "property",
        record_id: PROPERTY_ID,
        display_label: "Test-only property context",
        status: null,
        source: null,
        valid_from: null,
        valid_to: null,
      }],
      relations: [],
      as_of: null,
      next_cursor: nextCursor,
    } });
    return;
  }
  if (url.pathname === `/v1/properties/${PROPERTY_ID}/evidence`) {
    await route.fulfill({ json: { property: propertyDto(), evidence: [], next_cursor: nextCursor } });
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
  page.on("request", (request) => {
    const url = new URL(request.url());
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

  for (const moduleName of ["Parcel/GIS", "Building", "Planning", "Market", "Listings", "Title/Documents", "CRM", "Decision"]) {
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
  ]));
  await expect(page.locator("body")).not.toContainText(token);
  expect(new URL(page.url()).searchParams.has("access_token")).toBe(false);
  expect(directDataApiRequests).toEqual([]);
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
