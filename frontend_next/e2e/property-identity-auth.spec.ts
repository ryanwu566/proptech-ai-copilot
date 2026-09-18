import { expect, test, type Page, type Route } from "@playwright/test";

const USER = "11111111-1111-4111-8111-111111111111";
const WORKSPACE = "22222222-2222-4222-8222-222222222222";
const PROPERTY = "66666666-6666-4666-8666-666666666666";
const NOW = "2026-09-18T00:00:00Z";
const API = "http://e2e.test";
const AUTH = "https://slice8-auth.supabase.co";
const routePath = `/vnext/property-identity/${WORKSPACE}/${PROPERTY}`;

function token(exp = 4102444800, role = "authenticated") {
  const header = Buffer.from(JSON.stringify({ alg: "ES256", kid: "auth-e2e-key" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: USER, aud: "authenticated", role, iss: `${AUTH}/auth/v1`, exp })).toString("base64url");
  return `${header}.${payload}.synthetic`;
}

function session(accessToken = token()) {
  return { access_token: accessToken, refresh_token: "synthetic-refresh-token", token_type: "bearer", expires_in: 3600,
    expires_at: 4102444800, user: { id: USER, aud: "authenticated", role: "authenticated", email: "member@example.invalid",
      app_metadata: {}, user_metadata: {}, created_at: NOW } };
}

async function installSession(page: Page, accessToken = token()) {
  await page.addInitScript(({ value }) => localStorage.setItem("sb-slice8-auth-auth-token", JSON.stringify(value)), { value: session(accessToken) });
}

function property() {
  return { property_entity_id: PROPERTY, workspace_id: WORKSPACE, lifecycle_state: "active", display_label: "測試房產",
    confirmation_summary: { available: false, human_confirmed: false, confirmation_id: null, confirmed_at: null,
      confirmed_by: null, resolution_id: null }, version: 1, created_at: NOW, updated_at: NOW };
}

async function mockBackend(page: Page, options: { propertyStatus?: number; workspaceStatus?: number } = {}) {
  const requests: { url: string; authorization: string; method: string }[] = [];
  await page.route(`${API}/v1**`, async (route: Route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    requests.push({ url: request.url(), authorization: request.headers().authorization ?? "", method: request.method() });
    if (path === "/v1") return route.fulfill({ json: { status: "ok", principal: { user_id: USER }, features: { identity_v1: true, legacy_case_import_v1: false } } });
    if (path === `/v1/workspaces/${WORKSPACE}/context`) return route.fulfill(options.workspaceStatus
      ? { status: options.workspaceStatus, json: { error: { code: "permission_denied", message: "private backend detail", request_id: "auth-e2e", retryable: false } } }
      : { json: { status: "ok", workspace_id: WORKSPACE, user_id: USER, role: "member" } });
    if (path === `/v1/properties/${PROPERTY}`) return route.fulfill(options.propertyStatus
      ? { status: options.propertyStatus, json: { error: { code: "authentication_required", message: "private backend detail", request_id: "auth-e2e", retryable: false } } }
      : { json: property() });
    if (path === `/v1/properties/${PROPERTY}/graph`) return route.fulfill({ json: { property: property(), nodes: [], relations: [], as_of: null, next_cursor: null } });
    if (path === `/v1/properties/${PROPERTY}/evidence`) return route.fulfill({ json: { property: property(), evidence: [], next_cursor: null } });
    return route.abort();
  });
  return requests;
}

test("email and password sign-in creates an official session before live review loads", async ({ page }) => {
  const requests = await mockBackend(page);
  const accessToken = token();
  const consoleMessages: string[] = [];
  const bearerDestinations: string[] = [];
  page.on("console", (message) => consoleMessages.push(message.text()));
  page.on("request", (request) => {
    if (request.headers().authorization === `Bearer ${accessToken}`) bearerDestinations.push(request.url());
  });
  await page.route(`${AUTH}/auth/v1/**`, async (route) => {
    if (new URL(route.request().url()).searchParams.get("grant_type") === "password") {
      expect(route.request().postDataJSON()).toMatchObject({ email: "member@example.invalid", password: "correct-password" });
      expect(route.request().headers().apikey).toBe("sb_publishable_slice8_e2e_public_only");
      return route.fulfill({ json: session(accessToken) });
    }
    return route.fulfill({ status: 204 });
  });
  await page.goto(routePath);
  await expect(page.getByLabel("電子郵件")).toBeVisible();
  await expect(page.getByLabel("密碼")).toBeVisible();
  expect(requests).toHaveLength(0);
  await page.getByLabel("電子郵件").fill("member@example.invalid");
  await page.getByLabel("密碼").fill("correct-password");
  await page.getByRole("button", { name: "登入" }).click();
  await expect(page.getByTestId("identity-status-summary")).toBeVisible();
  expect(requests.map((request) => request.url)).toEqual(expect.arrayContaining([`${API}/v1`, `${API}/v1/workspaces/${WORKSPACE}/context`, `${API}/v1/properties/${PROPERTY}`]));
  expect(requests.every((request) => request.authorization === `Bearer ${accessToken}`)).toBe(true);
  expect(bearerDestinations.length).toBeGreaterThan(0);
  expect(bearerDestinations.every((url) => url.startsWith(`${API}/v1`))).toBe(true);
  expect(await page.locator("body").textContent()).not.toContain(accessToken);
  expect(consoleMessages.join(" ")).not.toContain(accessToken);
  await page.getByRole("button", { name: "登出" }).click();
  await expect(page.getByLabel("電子郵件")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("sb-slice8-auth-auth-token"))).toBeNull();
});

test("stored valid session restores the live review without signing in again", async ({ page }) => {
  await installSession(page);
  const requests = await mockBackend(page);
  await page.goto(routePath);
  await expect(page.getByTestId("identity-status-summary")).toBeVisible();
  await expect(page.getByLabel("電子郵件")).toHaveCount(0);
  expect(requests.length).toBeGreaterThan(2);
});

test("privileged-looking stored session is rejected before any backend call", async ({ page }) => {
  await installSession(page, token(4102444800, "service_role"));
  const requests = await mockBackend(page);
  await page.route(`${AUTH}/auth/v1/**`, (route) => route.fulfill({ status: 204 }));
  await page.goto(routePath);
  await expect(page.getByLabel("電子郵件")).toBeVisible();
  expect(requests).toHaveLength(0);
});

test("a second tab signing in opens the authorized review in the first tab", async ({ page }) => {
  await mockBackend(page);
  await page.goto(routePath);
  await expect(page.getByLabel("電子郵件")).toBeVisible();
  const second = await page.context().newPage();
  await mockBackend(second);
  await second.route(`${AUTH}/auth/v1/**`, (route) => route.fulfill({ json: session() }));
  await second.goto(routePath);
  await second.getByLabel("電子郵件").fill("member@example.invalid");
  await second.getByLabel("密碼").fill("correct-password");
  await second.getByRole("button", { name: "登入" }).click();
  await expect(second.getByTestId("identity-status-summary")).toBeVisible();
  await expect(page.getByTestId("identity-status-summary")).toBeVisible();
});

test("existing session restores review; backend 401 expires it without a retry", async ({ page }) => {
  await installSession(page);
  const requests = await mockBackend(page, { propertyStatus: 401 });
  await page.route(`${AUTH}/auth/v1/**`, (route) => route.fulfill({ status: 204 }));
  await page.goto(routePath);
  await expect(page.getByText("登入已逾期")).toBeVisible();
  await expect(page.getByLabel("電子郵件")).toBeVisible();
  await expect(page.getByTestId("identity-status-summary")).toHaveCount(0);
  expect(requests.filter((request) => request.url === `${API}/v1/properties/${PROPERTY}`)).toHaveLength(1);
});

test("unauthorized workspace and generic auth failures expose no internal messages", async ({ page }) => {
  await installSession(page);
  await mockBackend(page, { workspaceStatus: 403 });
  await page.goto(routePath);
  await expect(page.getByText("無法查看這個工作空間或房產。")).toBeVisible();
  await expect(page.getByTestId("identity-status-summary")).toHaveCount(0);
  await page.evaluate(() => localStorage.clear());
  const signedOut = await page.context().newPage();
  await signedOut.route(`${AUTH}/auth/v1/**`, (route) => route.fulfill({ status: 400, json: { error: "invalid_grant", error_description: "SECRET RAW AUTH ERROR" } }));
  await signedOut.goto(routePath);
  await signedOut.getByLabel("電子郵件").fill("unknown@example.invalid");
  await signedOut.getByLabel("密碼").fill("wrong-password");
  await signedOut.getByRole("button", { name: "登入" }).click();
  await expect(signedOut.getByText("登入失敗，請確認帳號資訊後再試。")).toBeVisible();
  await expect(signedOut.getByText("SECRET RAW AUTH ERROR")).toHaveCount(0);
});
