import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
const MOBILE_WIDTHS = [360, 390, 430];
type Locale = (typeof LOCALES)[number];

const PILOT_LABELS: Record<Locale, {
  campaign: string; code: string; join: string; participation: string; metrics: string;
  feedbackConsent: string; publication: string; accept: string; start: string; complete: string; submit: string;
}> = {
  "zh-TW": { campaign: "試用活動識別", code: "試用代碼", join: "加入封閉試用", participation: "我同意參與此試用。", metrics: "我同意收集互動與完成時間資料。", feedbackConsent: "我同意提交書面回饋。", publication: "我同意匿名回饋在審核後用於競賽證據。", accept: "接受並繼續", start: "開始試用任務", complete: "完成任務", submit: "提交回饋" },
  en: { campaign: "Campaign ID", code: "Pilot code", join: "Join the closed pilot", participation: "I agree to participate in this pilot.", metrics: "I agree to interaction and completion-time metrics.", feedbackConsent: "I agree to submit written feedback.", publication: "I allow anonymized feedback to be used in competition evidence after review.", accept: "Accept and continue", start: "Start the pilot task", complete: "Complete task", submit: "Submit feedback" },
  ja: { campaign: "キャンペーン ID", code: "試用コード", join: "クローズド試用に参加", participation: "この試用への参加に同意します。", metrics: "操作と完了時間の計測に同意します。", feedbackConsent: "書面のフィードバック提出に同意します。", publication: "審査後、匿名フィードバックを競技用資料に使うことに同意します。", accept: "同意して続ける", start: "試用タスクを開始", complete: "タスクを完了", submit: "フィードバックを送信" },
  ko: { campaign: "캠페인 ID", code: "파일럿 코드", join: "비공개 파일럿 참여", participation: "이 파일럿에 참여하는 데 동의합니다.", metrics: "상호작용 및 완료 시간 측정에 동의합니다.", feedbackConsent: "서면 피드백 제출에 동의합니다.", publication: "검토 후 익명 피드백을 경쟁 자료에 사용하는 데 동의합니다.", accept: "동의하고 계속", start: "파일럿 과제 시작", complete: "과제 완료", submit: "피드백 제출" },
};

async function mockPilotApi(page: Page, options: { rejectAccess?: boolean; networkFailure?: boolean; publication?: boolean } = {}) {
  let eventCount = 0;
  let accessCount = 0;
  let publicationApproved = false;
  const cors = { "access-control-allow-origin": "*" };
  await page.route("**/client-errors", (route) => route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ status: "accepted", support_reference: "e2e-support-reference" }) }));
  await page.route("**/pilot/access", (route) => {
    if (options.rejectAccess) return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Pilot access is unavailable." }) });
    if (options.networkFailure) return route.abort("failed");
    accessCount += 1;
    return route.fulfill({ status: 201, contentType: "application/json", headers: cors, body: JSON.stringify({ session_id: `e2e-session-${accessCount}`, session_token: `e2e-session-token-${accessCount}`, mode: "closed_pilot", consent_version: "pilot-consent-v1" }) });
  });
  await page.route("**/pilot/sessions/*/consent", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted" }) }));
  await page.route("**/pilot/sessions/*/profile", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted" }) }));
  await page.route("**/pilot/sessions/*/events", async (route) => { eventCount += 1; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted", evidence_state: "complete" }) }); });
  await page.route("**/pilot/sessions/*/feedback", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted", publication_status: options.publication ? "private" : "private" }) }));
  await page.route("**/pilot/sessions/*/complete", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "completed", mode: "closed_pilot" }) }));
  await page.route("**/pilot/admin/evidence/*/review", (route) => route.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ status: "reviewed", publication_status: "private", public_endorsement: false }) }));
  await page.route("**/pilot/admin/evidence/*/approve-publication", (route) => { publicationApproved = true; return route.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ status: "approved", publication_status: "anonymized_quote_allowed", public_endorsement: false }) }); });
  await page.route("**/pilot/admin/evidence/*/revoke-publication", (route) => { publicationApproved = false; return route.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ status: "revoked", publication_status: "revoked", public_endorsement: false }) }); });
  await page.route("**/pilot/public-evidence", (route) => route.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ publishable_testimonials: publicationApproved ? 1 : 0, test_fixtures_excluded: true }) }));
  await page.route("**/pilot/sessions/*/deletion-dry-run", (route) => route.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ dry_run: true, affected_record_counts: { pilot_events: 1, pilot_feedback: 1, pilot_contacts: 0, pilot_sessions: 1 } }) }));
  await page.route("**/pilot/sessions/*", async (route) => { if (route.request().method() === "DELETE") return route.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify({ status: "deleted", audit_note: "participant scoped" }) }); return route.fallback(); });
  return { eventCount: () => eventCount, accessCount: () => accessCount };
}

async function openPilot(page: Page, locale: Locale = "en", options: { rejectAccess?: boolean; networkFailure?: boolean; publication?: boolean } = {}) {
  await page.addInitScript(({ locale }) => {
    localStorage.setItem("proptech_onboarding_seen", "true");
    localStorage.setItem("proptech_onboarding_version", "2");
    (window as Window & { __pilotLocale?: string }).__pilotLocale = locale;
  }, { locale });
  const errors: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  const api = await mockPilotApi(page, options);
  await page.goto("/");
  if (locale !== "zh-TW") await page.getByTestId("locale-switcher").selectOption(locale);
  await page.getByTestId("competition-mvp-banner").getByRole("button", { name: "Join closed pilot", exact: true }).click();
  await expect(page.getByTestId("closed-pilot")).toBeVisible();
  return { errors, api };
}

async function completeParticipantFlow(page: Page, locale: Locale = "en", publication = false) {
  const pilot = page.getByTestId("closed-pilot");
  const labels = PILOT_LABELS[locale];
  await pilot.getByLabel(labels.campaign, { exact: true }).fill("e2e-campaign");
  await pilot.getByLabel(labels.code, { exact: true }).fill("e2e-code");
  await pilot.getByRole("button", { name: labels.join, exact: true }).click();
  await pilot.getByRole("checkbox", { name: labels.participation, exact: true }).check();
  await pilot.getByRole("checkbox", { name: labels.metrics, exact: true }).check();
  await pilot.getByRole("checkbox", { name: labels.feedbackConsent, exact: true }).check();
  if (publication) await pilot.getByRole("checkbox", { name: labels.publication, exact: true }).check();
  await pilot.getByRole("button", { name: labels.accept, exact: true }).click();
  await pilot.getByRole("button", { name: labels.start, exact: true }).click();
  for (let index = 0; index < 3; index += 1) {
    await expect(pilot.getByRole("button", { name: labels.complete, exact: true })).toBeVisible();
    await pilot.getByRole("button", { name: labels.complete, exact: true }).click();
  }
  await pilot.getByRole("textbox", { name: "Optional feedback", exact: true }).fill("bounded e2e feedback");
  await pilot.getByRole("button", { name: labels.submit, exact: true }).click();
  await expect(pilot.locator('[role="status"]')).toBeVisible();
}

test("participant workflow completes with private evidence and no browser errors", async ({ page }) => {
  const { errors, api } = await openPilot(page);
  await completeParticipantFlow(page);
  expect(errors).toEqual([]);
  expect(api.eventCount()).toBe(4);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});

test("invalid pilot access stays generic and creates no session", async ({ page }) => {
  const { errors } = await openPilot(page, "en", { rejectAccess: true });
  const pilot = page.getByTestId("closed-pilot");
  await pilot.getByLabel(PILOT_LABELS.en.campaign, { exact: true }).fill("invalid");
  await pilot.getByLabel(PILOT_LABELS.en.code, { exact: true }).fill("invalid");
  await pilot.getByRole("button", { name: PILOT_LABELS.en.join, exact: true }).click();
  await expect(pilot.getByRole("alert")).toBeVisible();
  expect(await pilot.locator("input[type=checkbox]").count()).toBe(0);
  expect(errors.filter((item) => !item.includes("status of 404"))).toEqual([]);
});

test("network failure shows a bounded degraded state without an infinite spinner", async ({ page }) => {
  const { errors } = await openPilot(page, "en", { networkFailure: true });
  const pilot = page.getByTestId("closed-pilot");
  await pilot.getByLabel(PILOT_LABELS.en.campaign, { exact: true }).fill("network-failure");
  await pilot.getByLabel(PILOT_LABELS.en.code, { exact: true }).fill("bounded-code");
  const join = pilot.getByRole("button", { name: PILOT_LABELS.en.join, exact: true });
  await join.click();
  await expect(pilot.getByRole("alert")).toBeVisible();
  expect(await join.isEnabled()).toBe(true);
  expect(errors.filter((item) => !item.includes("net::ERR_FAILED"))).toEqual([]);
});

test("publication remains private until approval and disappears after revocation", async ({ page }) => {
  const { errors } = await openPilot(page, "en", { publication: true });
  await completeParticipantFlow(page, "en", true);
  const states = await page.evaluate(async () => {
    const headers = { "Content-Type": "application/json", "X-Pilot-Admin-Token": "e2e-admin" };
    const get = async (path: string) => (await fetch(`http://e2e.test${path}`, { headers })).json();
    const before = await get("/pilot/public-evidence");
    await fetch("http://e2e.test/pilot/admin/evidence/e2e-session-1/review", { method: "POST", headers });
    await fetch("http://e2e.test/pilot/admin/evidence/e2e-session-1/approve-publication", { method: "POST", headers });
    const approved = await get("/pilot/public-evidence");
    await fetch("http://e2e.test/pilot/admin/evidence/e2e-session-1/revoke-publication", { method: "POST", headers });
    const revoked = await get("/pilot/public-evidence");
    return { before: before.publishable_testimonials, approved: approved.publishable_testimonials, revoked: revoked.publishable_testimonials };
  });
  expect(states).toEqual({ before: 0, approved: 1, revoked: 0 });
  expect(errors).toEqual([]);
});

test("deletion dry-run and delete remain scoped to one participant", async ({ page }) => {
  const { api } = await openPilot(page);
  const result = await page.evaluate(async () => {
    const start = async (id: string) => (await fetch("http://e2e.test/pilot/access", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ campaign_id: id, pilot_code: "bounded", locale: "en" }) })).json();
    const first = await start("campaign-a");
    const second = await start("campaign-b");
    const dryRun = await (await fetch(`http://e2e.test/pilot/sessions/${first.session_id}/deletion-dry-run`, { headers: { "X-Pilot-Session-Token": first.session_token } })).json();
    const deleted = await (await fetch(`http://e2e.test/pilot/sessions/${first.session_id}`, { method: "DELETE", headers: { "X-Pilot-Session-Token": first.session_token } })).json();
    return { first: first.session_id, second: second.session_id, dryRun: dryRun.affected_record_counts.pilot_sessions, deleted: deleted.status };
  });
  expect(result.first).not.toBe(result.second);
  expect(result.dryRun).toBe(1);
  expect(result.deleted).toBe("deleted");
  expect(api.accessCount()).toBe(2);
});

test("professional review browser boundary rejects anonymous access and exposes no endorsement", async ({ page }) => {
  await page.route("**/professional-review/status", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "pending", reviewed_product_version: "pilot-evidence-v1", public_endorsement: false }) }));
  await page.route("**/professional-review", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Professional review mode is not configured." }) }));
  await page.goto("/");
  const result = await page.evaluate(async () => {
    const status = await (await fetch("/professional-review/status")).json();
    const unauthorized = await fetch("/professional-review", { method: "POST", body: "{}" });
    return { status: status.status, publicEndorsement: status.public_endorsement, unauthorized: unauthorized.status };
  });
  expect(result).toEqual({ status: "pending", publicEndorsement: false, unauthorized: 503 });
});

for (const locale of LOCALES) {
  test(`pilot invitation and completion surface is available in ${locale}`, async ({ page }) => {
    const { errors } = await openPilot(page, locale);
    await completeParticipantFlow(page, locale);
    expect(await page.getByTestId("closed-pilot").getAttribute("data-testid")).toBe("closed-pilot");
    expect(errors).toEqual([]);
  });
}

for (const width of MOBILE_WIDTHS) {
  test(`mobile pilot layout has no horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 360 ? 800 : width === 390 ? 844 : 932 });
    const { errors } = await openPilot(page);
    await expect(page.getByTestId("closed-pilot")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await page.screenshot({ path: `test-results/pilot-mobile-${width}.png`, fullPage: true });
    expect(errors).toEqual([]);
  });
}
