import { expect, test, type Page } from "@playwright/test";

const API = "http://e2e.test";
const USER = "11111111-1111-4111-8111-111111111111";
const NOW = "2026-10-13T00:00:00Z";
const sections = ["overview", "users", "usage", "providers", "limits", "operations", "audit"];

for (const width of [390, 430, 1024, 1440]) {
test(`account command requires a review and retries with an identical key after an uncertain result at ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  await session(page); await backend(page);
  const commands: unknown[] = [];
  await page.route(`${API}/v1/admin/accounts/**`, async (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ json: snapshot('users').users[0] });
    commands.push(route.request().postDataJSON());
    return route.fulfill({ status: commands.length === 1 ? 503 : 200, json: {} });
  });
  await page.goto('/admin/users');
  await page.getByTestId('locale-switcher').selectOption('en');
  await page.getByLabel('Account UUID', { exact: true }).fill(USER);
  await page.getByRole('button', { name: 'Look up', exact: true }).click();
  await page.getByLabel('Reason (required, up to 500 characters)', { exact: true }).fill('Investigating an\nabuse report');
  await page.getByRole('button', { name: 'Review change', exact: true }).click();
  await noOverflow(page);
  expect(commands).toHaveLength(0);
  await expect(page.getByRole('heading', { name: 'Review change' })).toBeFocused();
  await page.getByRole('button', { name: 'Confirm command', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Outcome unconfirmed' })).toBeVisible();
  await page.getByRole('button', { name: 'Retry same command', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Change saved and audited.' })).toBeVisible();
  expect(commands).toHaveLength(2); expect(commands[0]).toEqual(commands[1]);
  expect(commands[0]).toMatchObject({ field: 'status', value: 'suspended', reason: 'Investigating an abuse report' });
  expect(commands[0]).not.toHaveProperty('target');
});

test(`quota editor shows shared scope, bounds values, and reviews before saving at ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  await session(page); await backend(page);
  const commands: unknown[] = [];
  await page.route(`${API}/v1/admin/quota-policy**`, (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ json: ['authenticated','anonymous'].map((principal_class) => ({ principal_class, request_hour: 100, operation_hour: 40, operation_day: 200 })) });
    commands.push(route.request().postDataJSON()); return route.fulfill({ json: {} });
  });
  await page.goto('/admin/usage');
  await page.getByTestId('locale-switcher').selectOption('en');
  await page.getByRole('button', { name: 'Load quota policy' }).click();
  await expect(page.getByText('Applies to PostgreSQL shared principal quotas.', { exact: false })).toBeVisible();
  await page.getByLabel('Requests per UTC hour', { exact: true }).fill('800');
  await page.getByLabel('Reason (required, up to 500 characters)', { exact: true }).fill('Adjust verified allowance');
  await page.getByRole('button', { name: 'Review change', exact: true }).click();
  await noOverflow(page);
  expect(commands).toHaveLength(0);
  await page.getByRole('button', { name: 'Confirm command', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Change saved and audited.' })).toBeVisible();
  expect(commands[0]).toMatchObject({ principal_class: 'authenticated', request_hour: 800, operation_hour: 40, operation_day: 200 });
});
}
function snapshot(section: string) {
  return { schema_version: "admin-v1", section, state: "partial", source: "wave_1b", window: "last_24h", as_of: NOW, reason: "waiting_for_1b", next_cursor: section === "audit" ? "next" : null,
    metrics: [{ key: "requests", value: null, state: "unknown", source: "wave_1b", window: "last_24h" }, { key: "http_429", value: 0, state: "known", source: "wave_1b", window: "last_24h" }],
    users: [{ user_id: USER, status: "active", platform_role: "consumer", created_at: NOW, last_activity: null, usage_requests: null, email: "private@example.invalid", jwt: "private-jwt" }],
    usage: ["unknown", "not_applicable", "known"].map((state, index) => ({ capability: ["routes", "geocoding", "places"][index], provider: null, requests: 0, provider_attempts: null, admitted: 0, rejected: null, http_429: null, http_5xx: null, latency_ms: null, quota_consumed: null, cache_hit: 0, cost: { state, amount: state === "known" ? 2.5 : null, currency: state === "known" ? "USD" : null } })),
    providers: [{ capability: "routes", configuration: "configured", status: "not_checked", freshness: "unknown", checked_at: null, last_success: null, last_failure: null, disabled: false, quota_evidence: "unavailable" }],
    limits: [{ capability: "routes", audience: "all_peers", requests: 10, window_seconds: 60, operations: 120, operation_window_seconds: 3600, concurrency: 2, enabled: true }],
    operations: [{ key: "backup", state: "unavailable", source: "external", value: null, commit_sha: null }],
    audit: [{ timestamp: NOW, actor: USER, event_type: "admin_read", target_type: "admin", outcome: "success", reason_code: "authorized", before_state: { status: 'active', platform_role: 'consumer' }, after_state: { status: 'suspended', platform_role: 'consumer' }, metadata: { api_key: "private-provider-key" } }],
  };
}
async function session(page: Page) {
  const accessToken = `${Buffer.from(JSON.stringify({ alg: "ES256", kid: "fixture" })).toString("base64url")}.${Buffer.from(JSON.stringify({ sub: USER, aud: "authenticated", role: "authenticated", iss: "https://slice8-auth.supabase.co/auth/v1", exp: 4102444800 })).toString("base64url")}.synthetic`;
  await page.addInitScript((value) => localStorage.setItem("sb-slice8-auth-auth-token", JSON.stringify(value)), {
    access_token: accessToken, refresh_token: "synthetic-refresh", token_type: "bearer", expires_in: 3600, expires_at: 4102444800,
    user: { id: USER, aud: "authenticated", role: "authenticated", app_metadata: {}, user_metadata: { platform_role: "platform_admin" }, created_at: NOW },
  });
}
async function backend(page: Page, options: { status?: number; state?: string; delay?: number } = {}) {
  const calls: string[] = [];
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.origin === API || (url.hostname === "127.0.0.1" && !url.pathname.startsWith("/api/"))) return route.fallback();
    throw new Error(`Unexpected external provider request: ${url.hostname}`);
  });
  await page.route(`${API}/**`, async (route) => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith("/v1/admin/")) {
      if (url.pathname === "/performance/metrics" || url.pathname === "/client-errors") return route.fulfill({ status: 204 });
      throw new Error(`Unexpected provider/API request: ${url.pathname}`);
    }
    calls.push(url.pathname + url.search);
    if (options.delay) await new Promise((resolve) => setTimeout(resolve, options.delay));
    const section = url.pathname.split("/").at(-1)!;
    if (options.status) return route.fulfill({ status: options.status, json: { error: { message: "private-error-secret" } } });
    const result = snapshot(section);
    if (options.state) Object.assign(result, { state: options.state, users: [], audit: [], usage: [], metrics: [], next_cursor: null });
    if (url.search) result.next_cursor = null;
    return route.fulfill({ json: result });
  });
  return calls;
}
async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

test("anonymous and normal user see safe gates on direct nested navigation", async ({ page }) => {
  const calls = await backend(page, { status: 403 });
  await page.goto("/admin/audit");
  await expect(page.getByTestId("admin-gate")).toBeVisible();
  expect(calls).toHaveLength(0);
  await session(page);
  await page.reload();
  await expect(page.getByTestId("admin-gate")).toContainText("403");
  await expect(page.getByTestId("admin-table")).toHaveCount(0);
  expect(calls).toHaveLength(1);
  expect(await page.locator("body").textContent()).not.toContain("private-error-secret");
});

for (const width of [390, 430, 1024, 1440]) for (const locale of ["zh-TW", "en", "ja", "ko"]) {
  test(`operator overview and responsive tables ${locale} at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await session(page);
    const calls = await backend(page);
    await page.goto("/admin");
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByTestId("admin-metrics")).toBeVisible();
    await noOverflow(page);
    const unknown = { "zh-TW": "未知", en: "Unknown", ja: "不明", ko: "알 수 없음" }[locale];
    await expect(page.getByTestId("admin-metrics")).toContainText(unknown!);
    for (const section of sections.slice(1)) {
      await page.getByTestId(`admin-nav-${section}`).click();
      await page.waitForURL(`**/admin/${section}`);
      await expect(page.getByTestId(`admin-nav-${section}`)).toHaveAttribute("aria-current", "page");
      await expect(page.getByTestId("admin-table")).toBeVisible();
      await noOverflow(page);
    }
    expect(calls).toHaveLength(7);
    const text = await page.locator("main").textContent();
    expect(text).not.toContain('platform_role:');
    for (const privateValue of ["private@example.invalid", "private-jwt", "private-provider-key"]) expect(text).not.toContain(privateValue);
  });
}

test("manual refresh, keyboard focus and audit pagination make bounded requests", async ({ page }) => {
  await session(page);
  const calls = await backend(page);
  await page.goto("/admin/audit");
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("admin-table")).toBeVisible();
  const refresh = page.getByTestId("admin-refresh");
  await refresh.focus();
  await expect(refresh).toBeFocused();
  const outline = await refresh.evaluate((el) => getComputedStyle(el).outlineStyle);
  expect(outline).not.toBe("none");
  await page.keyboard.press("Enter");
  await expect.poll(() => calls.length).toBe(2);
  await expect(refresh).toBeEnabled();
  await page.getByRole("button", { name: "Next page" }).click();
  await expect.poll(() => calls.length).toBe(3);
  expect(calls[2]).toBe("/v1/admin/audit?cursor=next");
  await page.waitForTimeout(1500);
  expect(calls).toHaveLength(3);
});

for (const state of ["empty", "unavailable"]) test(`${state} has a distinct state and no fake records`, async ({ page }) => {
  await session(page); await backend(page, { state });
  await page.goto("/admin/users");
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("admin-state")).toContainText(state === "empty" ? "No records" : "Unavailable");
  await expect(page.locator("tbody tr")).toHaveCount(0);
});

test("loading and error states are visible without raw backend error details", async ({ page }) => {
  await session(page); await backend(page, { status: 503, delay: 1000 });
  await page.goto("/admin/users");
  await expect(page.getByTestId("admin-loading")).toBeVisible();
  await expect(page.getByTestId("admin-error")).toBeVisible();
  expect(await page.locator("body").textContent()).not.toContain("private-error-secret");
});

test("provider unobserved status and server cost states are truthful", async ({ page }) => {
  await session(page); await backend(page);
  await page.goto("/admin/providers");
  await page.getByTestId("locale-switcher").selectOption("en");
  await expect(page.getByTestId("admin-table")).toContainText("Not checked");
  await expect(page.getByTestId("admin-table")).toContainText("Unknown");
  await page.getByTestId("admin-nav-usage").click();
  await expect(page.getByTestId("admin-table")).toContainText("Not applicable");
  await expect(page.getByTestId("admin-table")).toContainText("$2.50");
});

for (const event of ["SIGNED_OUT", "SIGNED_IN"]) test(`${event} removes already displayed privileged rows`, async ({ page }) => {
  await session(page); const calls = await backend(page);
  await page.goto("/admin/users");
  await expect(page.getByTestId("admin-table")).toContainText(USER);
  await page.evaluate((event) => {
    const channel = new BroadcastChannel("sb-slice8-auth-auth-token");
    const session = JSON.parse(localStorage.getItem("sb-slice8-auth-auth-token")!);
    if (event === "SIGNED_IN") session.user.id = "22222222-2222-4222-8222-222222222222";
    channel.postMessage({ event, session: event === "SIGNED_OUT" ? null : session });
    channel.close();
  }, event);
  await expect(page.getByTestId("admin-gate")).toBeVisible();
  await expect(page.getByTestId("admin-table")).toHaveCount(0);
  expect(calls).toHaveLength(1);
});

test("sign-out during a delayed read cannot restore privileged rows", async ({ page }) => {
  await session(page); const calls = await backend(page, { delay: 1200 });
  await page.goto("/admin/users");
  await expect.poll(() => calls.length).toBe(1);
  await page.evaluate(() => {
    const channel = new BroadcastChannel("sb-slice8-auth-auth-token");
    channel.postMessage({ event: "SIGNED_OUT", session: null }); channel.close();
  });
  await expect(page.getByTestId("admin-gate")).toBeVisible();
  await page.waitForTimeout(1600);
  await expect(page.getByTestId("admin-table")).toHaveCount(0);
});
