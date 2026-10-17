import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { emptyDecisionRoom } from "../lib/decision-room-store";

const API = "http://e2e.test";
const AUTH = "https://slice8-auth.supabase.co";
const USER = "11111111-1111-4111-8111-111111111111";
const ID = "22222222-2222-4222-8222-222222222222";
const KEY = "proptech.savedCases.v1";
const ROOM = "proptech.decisionRoom.v1.case-a";
const saved = { ...e9Case(), historicalExtra: { source: "original", state: "failed", checked_at: "2026-09-01T00:00:00Z" } };
const room = { ...emptyDecisionRoom("case-a"), notes: [{ id: "note1", date: "2026-10-10", text: "Original authored viewing notes" }] };
const encoded = (v: object) => Buffer.from(JSON.stringify(v)).toString("base64url");
const token = `${encoded({ alg: "ES256", kid: "fixture" })}.${encoded({ sub: USER, aud: "authenticated", role: "authenticated", iss: `${AUTH}/auth/v1`, exp: 4102444800 })}.synthetic`;
const session = { access_token: token, refresh_token: "synthetic-refresh", token_type: "bearer", expires_in: 3600, expires_at: 4102444800,
  user: { id: USER, email: "person@example.invalid", aud: "authenticated", role: "authenticated", app_metadata: {}, user_metadata: {}, created_at: "2026-10-13T00:00:00Z" } };
function cloud(role = "owner") {
  return { id: ID, owner_id: USER, role, revision: 1, title: saved.title, notes: "", created_at: saved.createdAt, updated_at: saved.updatedAt,
    snapshot: saved, user_authored: { decision_room: room }, members: {}, sharing: role === "owner" ? "private" : "members_only",
    monitoring: { cadence: "off", refresh_policy: "manual_only", execution_status: "not_configured", delivery_status: "not_configured" } };
}
async function setup(page: Page, options: { failure?: number; role?: string; noLocal?: boolean; noAuth?: boolean; malformedDate?: boolean; multipleLocal?: boolean } = {}) {
  const requests: { path: string; method: string; body: unknown }[] = [];
  let value = cloud(options.role); let conflict = false;
  if (options.malformedDate) value = { ...value, user_authored: { decision_room: { ...room, notes: [{ id: "note1", date: { original: "unknown" }, text: "Historical note with unknown date" }] } } } as unknown as ReturnType<typeof cloud>;
  await page.addInitScript(({ local, notes, auth, noLocal, noAuth }) => {
    if (!noLocal) { localStorage.setItem("proptech.savedCases.v1", local); localStorage.setItem("proptech.decisionRoom.v1.case-a", notes); }
    if (!noAuth) localStorage.setItem("sb-slice8-auth-auth-token", JSON.stringify(auth));
  }, { local: JSON.stringify(options.multipleLocal ? [saved, e9Case("case-b")] : [saved]), notes: JSON.stringify(room), auth: session, noLocal: options.noLocal, noAuth: options.noAuth });
  await page.route(`${AUTH}/auth/v1/**`, route => route.fulfill({ json: route.request().url().includes("/user") ? session.user : {} }));
  await page.route(`${API}/**`, route => {
    const request = route.request(); const path = new URL(request.url()).pathname;
    requests.push({ path, method: request.method(), body: request.postDataJSON() });
    if (!path.startsWith("/v1/saved-cases")) return route.fulfill({ status: 500, json: { error: "unexpected provider call" } });
    expect(request.headers().authorization).toBe(`Bearer ${token}`);
    if (request.method() !== "GET") expect(request.headers()["idempotency-key"]).toMatch(/^[A-Za-z0-9._:-]{16,128}$/);
    if (options.failure) return route.fulfill({ status: options.failure, json: { error: { details: { reason_code: "persistence_pending" }, message: "RAW SECRET" } } });
    if (request.method() === "PATCH") {
      if (conflict) return route.fulfill({ status: 409, json: { error: { code: "version_conflict" } } });
      value = { ...value, ...request.postDataJSON(), revision: value.revision + 1 };
      return route.fulfill({ json: value });
    }
    if (request.method() === "PUT") {
      const body = request.postDataJSON();
      if (path.endsWith("/membership")) {
        const members: Record<string, string> = { ...value.members };
        if (body.role === null) delete members[body.member_id]; else members[body.member_id] = body.role;
        value = { ...value, members, sharing: Object.keys(members).length ? "members_only" : "private", revision: value.revision + 1 };
      } else value = { ...value, monitoring: { ...value.monitoring, cadence: body.cadence }, revision: value.revision + 1 };
      return route.fulfill({ json: value });
    }
    if (request.method() === "POST") return route.fulfill({ status: 201, json: value });
    if (path.endsWith("/activity")) return route.fulfill({ json: [{ revision: 1, actor_id: USER, kind: "case_imported", occurred_at: saved.updatedAt }] });
    return route.fulfill({ json: path === "/v1/saved-cases" ? [value] : value });
  });
  return { requests, conflict: () => { conflict = true; value = { ...value, revision: 2, title: "Changed on another device", notes: "Remote notes" }; } };
}

test("mount, sign-in restoration and preview never auto-upload; confirmation preserves raw local evidence and notes", async ({ page }) => {
  const h = await setup(page); await page.goto("/cases");
  await expect(page.getByTestId("cloud-cases-panel")).toBeVisible();
  expect(h.requests).toEqual([]);
  await page.getByLabel("選擇要保存的本機案件").selectOption("case-a");
  await page.getByRole("button", { name: "預覽保存到帳號", exact: true }).click();
  await expect(page.getByRole("button", { name: "確認儲存到我的帳號" })).toBeVisible();
  expect(h.requests).toEqual([]);
  await page.getByRole("button", { name: "確認儲存到我的帳號" }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("已儲存 Cloud 快照");
  const uploads = h.requests.filter(r => r.method === "POST");
  expect(uploads).toHaveLength(1);
  expect(uploads[0].body).toMatchObject({ snapshot: saved, user_authored: { decision_room: room }, explicit_consent: true });
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(JSON.stringify([saved]));
  expect(await page.evaluate(key => localStorage.getItem(key), ROOM)).toBe(JSON.stringify(room));
  expect(h.requests.every(r => r.path.startsWith("/v1/saved-cases"))).toBe(true);
  const entries = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage).filter(([key]) => key !== "sb-slice8-auth-auth-token")));
  expect(JSON.stringify(entries)).not.toMatch(/synthetic-refresh|synthetic|Bearer/);
});

test("failed upload retains byte-identical local copies and shows pending persistence honestly", async ({ page }) => {
  const h = await setup(page, { failure: 503 }); await page.goto("/cases");
  await page.getByLabel("選擇要保存的本機案件").selectOption("case-a");
  await page.getByRole("button", { name: "預覽保存到帳號", exact: true }).click();
  await page.getByRole("button", { name: "確認儲存到我的帳號" }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("Cloud 儲存尚未啟用");
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(JSON.stringify([saved]));
  expect(await page.evaluate(key => localStorage.getItem(key), ROOM)).toBe(JSON.stringify(room));
  expect(h.requests).toHaveLength(1);
  await expect(page.getByTestId("cloud-case-detail")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText("RAW SECRET");
});

test("preview invalidates if local evidence changes before confirmation", async ({ page }) => {
  const h = await setup(page); await page.goto("/cases");
  await page.getByLabel("選擇要保存的本機案件").selectOption("case-a");
  await page.getByRole("button", { name: "預覽保存到帳號", exact: true }).click();
  await expect(page.getByRole("button", { name: "確認儲存到我的帳號" })).toBeVisible();
  await page.evaluate(key => { const rows = JSON.parse(localStorage.getItem(key)!); rows[0].title = "Edited in another tab"; localStorage.setItem(key, JSON.stringify(rows)); }, KEY);
  await page.getByRole("button", { name: "確認儲存到我的帳號" }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("版本衝突");
  expect(h.requests).toEqual([]);
});

test("changing local selection discards a pending preview hash", async ({ page }) => {
  const h = await setup(page, { multipleLocal: true });
  await page.addInitScript(() => {
    const digest = crypto.subtle.digest.bind(crypto.subtle); let first = true;
    crypto.subtle.digest = async (...args: Parameters<typeof digest>) => {
      if (first) {
        first = false; Reflect.set(window, "previewHashPending", true);
        await new Promise<void>(resolve => window.addEventListener("test:release-preview", () => resolve(), { once: true }));
      }
      return digest(...args);
    };
  });
  await page.goto("/cases");
  await page.getByLabel("選擇要保存的本機案件").selectOption("case-a");
  await page.getByRole("button", { name: "預覽保存到帳號", exact: true }).click();
  await page.waitForFunction(() => Reflect.get(window, "previewHashPending") === true);
  await page.getByLabel("選擇要保存的本機案件").selectOption("case-b");
  await page.evaluate(() => window.dispatchEvent(new Event("test:release-preview")));
  await expect(page.getByRole("button", { name: "確認儲存到我的帳號" })).toHaveCount(0);
  await page.getByRole("button", { name: "預覽保存到帳號", exact: true }).click();
  await expect(page.getByRole("heading", { name: "確認上傳：案件 B" })).toBeVisible();
  expect(h.requests).toEqual([]);
});

test("a second device can reopen cloud evidence and sync status without providers or local writes", async ({ page }) => {
  const h = await setup(page, { noLocal: true }); await page.goto("/cases");
  await page.getByRole("button", { name: "讀取我的 Cloud 案件" }).click();
  await page.getByRole("button", { name: /案件 A · Cloud · owner/ }).click();
  await expect(page.getByTestId("cloud-case-detail")).toBeVisible();
  await page.getByText("檢視原始證據與筆記（不重新分析）").click();
  await expect(page.locator("pre")).toContainText("Original authored viewing notes");
  await page.getByRole("button", { name: "讀取最新版本", exact: true }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("已手動檢查最新版本");
  expect(h.requests.map(r => r.method)).toEqual(["GET", "GET", "GET"]);
  expect(h.requests.every(r => r.path.startsWith("/v1/saved-cases"))).toBe(true);
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBeNull();
});

test("conflict keeps authored drafts, disables blind retry, and requires reading latest revision", async ({ page }) => {
  const h = await setup(page); await page.goto("/cases");
  await page.getByRole("button", { name: "讀取我的 Cloud 案件" }).click();
  await page.getByRole("button", { name: /案件 A · Cloud · owner/ }).click();
  await page.getByLabel("Cloud 使用者筆記", { exact: true }).fill("My unsaved draft"); h.conflict();
  await page.getByRole("button", { name: "儲存 Cloud 使用者資料" }).click();
  await expect(page.getByLabel("Cloud 使用者筆記", { exact: true })).toHaveValue("My unsaved draft");
  await expect(page.getByRole("button", { name: "儲存 Cloud 使用者資料" })).toBeDisabled();
  await page.getByRole("button", { name: "讀取最新版本", exact: true }).click();
  await expect(page.getByTestId("cloud-case-detail")).toContainText("Remote notes");
  await expect(page.getByLabel("Cloud 使用者筆記", { exact: true })).toHaveValue("My unsaved draft");
  await expect(page.getByLabel("Cloud 標題", { exact: true })).toHaveValue("Changed on another device");
  await expect(page.getByRole("button", { name: "儲存 Cloud 使用者資料" })).toBeEnabled();
  expect(h.requests.filter(r => r.method === "PATCH")).toHaveLength(1);
});

test("monitoring, membership and refresh preserve unrelated authored drafts", async ({ page }) => {
  await setup(page); await page.goto("/cases");
  await page.getByRole("button", { name: "讀取我的 Cloud 案件" }).click();
  await page.getByRole("button", { name: /案件 A · Cloud · owner/ }).click();
  const note = page.getByLabel("Cloud 使用者筆記", { exact: true });
  await note.fill("Keep my authored draft");
  await page.getByLabel("檢查頻率", { exact: true }).selectOption("daily");
  await page.getByRole("button", { name: "儲存監控偏好" }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("監控偏好已儲存");
  await expect(note).toHaveValue("Keep my authored draft");
  await page.getByLabel("成員 Auth UUID", { exact: true }).fill(ID);
  await page.getByRole("button", { name: "授權成員", exact: true }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("成員授權已更新");
  await expect(note).toHaveValue("Keep my authored draft");
  await page.getByRole("button", { name: `撤銷 ${ID}`, exact: true }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("成員存取權已撤銷");
  await expect(note).toHaveValue("Keep my authored draft");
  await page.getByRole("button", { name: "讀取最新版本", exact: true }).click();
  await expect(note).toHaveValue("Keep my authored draft");
});

test("malformed historical note dates remain readable without crashing or changing evidence", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await setup(page, { malformedDate: true }); await page.goto("/cases");
  await page.getByRole("button", { name: "讀取我的 Cloud 案件" }).click();
  await page.getByRole("button", { name: /案件 A · Cloud · owner/ }).click();
  await expect(page.getByRole("region", { name: "Cloud 歷史快照摘要" })).toContainText("Historical note with unknown date");
  expect(errors).toEqual([]);
});

test("switching Cloud cases clears the previous recipient and defaults sharing to viewer", async ({ page }) => {
  const h = await setup(page);
  const second = { ...cloud(), id: "33333333-3333-4333-8333-333333333333", title: "Cloud case B" };
  await page.route(`${API}/v1/saved-cases?*`, route => route.fulfill({ json: [cloud(), second] }));
  await page.route(`${API}/v1/saved-cases/${second.id}`, route => route.fulfill({ json: second }));
  await page.goto("/cases");
  await page.getByRole("button", { name: "讀取我的 Cloud 案件" }).click();
  await page.getByRole("button", { name: /案件 A · Cloud · owner/ }).click();
  await page.getByLabel("成員 Auth UUID", { exact: true }).fill(ID);
  await page.getByLabel("案件權限", { exact: true }).selectOption("editor");
  await page.getByRole("button", { name: "讀取最新版本", exact: true }).click();
  await expect(page.getByLabel("成員 Auth UUID", { exact: true })).toHaveValue(ID);
  await expect(page.getByLabel("案件權限", { exact: true })).toHaveValue("editor");
  await page.getByRole("button", { name: /Cloud case B · Cloud · owner/ }).click();
  await expect(page.getByLabel("成員 Auth UUID", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("案件權限", { exact: true })).toHaveValue("viewer");
  await expect(page.getByRole("button", { name: "授權成員", exact: true })).toBeDisabled();
  expect(h.requests.filter(r => r.method !== "GET")).toEqual([]);
});

for (const role of ["editor", "viewer"]) test(`${role} boundaries, monitoring status and mobile offline state`, async ({ page, context }) => {
  const h = await setup(page, { role }); await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/cases");
  await page.getByRole("button", { name: "讀取受邀案件" }).click();
  await page.getByRole("button", { name: new RegExp(`案件 A · Cloud · ${role}`) }).click();
  await expect(page.getByRole("button", { name: "授權成員", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "儲存監控偏好" })).toBeDisabled();
  await expect(page.getByLabel("Cloud 使用者筆記", { exact: true }))[role === "viewer" ? "toBeDisabled" : "toBeEnabled"]();
  await expect(page.getByTestId("cloud-case-detail")).toContainText("排程執行與 email／SMS 通知尚未配置");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const before = h.requests.length; await context.setOffline(true);
  await expect(page.getByTestId("cloud-status")).toContainText("目前離線");
  await expect(page.getByRole("button", { name: "讀取最新版本", exact: true })).toBeDisabled();
  await context.setOffline(false);
  await expect(page.getByRole("button", { name: "讀取最新版本", exact: true })).toBeEnabled();
  expect(h.requests).toHaveLength(before);
});

test("unsigned migration requires login and sends no case payload", async ({ page }) => {
  const h = await setup(page, { noAuth: true }); await page.goto("/cases");
  await page.getByLabel("選擇要保存的本機案件").selectOption("case-a");
  await page.getByRole("button", { name: "預覽保存到帳號", exact: true }).click();
  await page.getByRole("button", { name: "確認儲存到我的帳號" }).click();
  await expect(page.getByTestId("cloud-status")).toContainText("請登入帳號");
  expect(h.requests).toEqual([]);
});

test("logout in another tab clears Cloud data and discards a late open response", async ({ page, context }) => {
  await setup(page); await page.goto("/cases");
  await page.getByRole("button", { name: "讀取我的 Cloud 案件" }).click();
  let started!: () => void; let release!: () => void;
  const pending = new Promise<void>(resolve => { started = resolve; });
  const released = new Promise<void>(resolve => { release = resolve; });
  await page.route(`${API}/v1/saved-cases/${ID}`, async route => { started(); await released; await route.fulfill({ json: cloud() }); });
  await page.getByRole("button", { name: /案件 A · Cloud · owner/ }).click();
  await pending;
  const account = await context.newPage();
  await account.route(`${AUTH}/auth/v1/**`, route => route.fulfill({ json: route.request().url().includes("/user") ? session.user : {} }));
  await account.route(`${API}/v1/account`, route => route.fulfill({ json: { user_id: USER, status: "active", platform_role: "consumer", created_at: saved.createdAt, updated_at: saved.updatedAt } }));
  await account.goto("/account"); await account.getByTestId("locale-switcher").selectOption("en");
  await expect(account.getByTestId("account-status")).toHaveText("Active");
  await account.getByRole("button", { name: "Sign out of this device" }).click();
  await expect(account.getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
  expect(await account.evaluate(() => localStorage.getItem("sb-slice8-auth-auth-token"))).toBeNull();
  await expect(page.getByTestId("cloud-status")).toContainText("帳號狀態已變更");
  const response = page.waitForResponse(`${API}/v1/saved-cases/${ID}`);
  release();
  await (await response).finished();
  await expect(page.getByTestId("cloud-cases-panel")).toHaveAttribute("aria-busy", "false");
  await expect(page.getByTestId("cloud-case-detail")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /案件 A · Cloud · owner/ })).toHaveCount(0);
  expect(await page.evaluate(key => localStorage.getItem(key), KEY)).toBe(JSON.stringify([saved]));
  await account.close();
});
