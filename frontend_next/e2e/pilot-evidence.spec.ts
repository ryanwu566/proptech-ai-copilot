import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["zh-TW", "en", "ja", "ko"];
const MOBILE_WIDTHS = [360, 390, 430];

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

async function openPilot(page: Page, locale = "en", options: { rejectAccess?: boolean; publication?: boolean } = {}) {
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
  if (locale !== "zh-TW") await page.getByRole("combobox").selectOption(locale);
  await page.getByRole("button", { name: "Join closed pilot" }).first().click();
  await expect(page.getByTestId("closed-pilot")).toBeVisible();
  return { errors, api };
}

async function completeParticipantFlow(page: Page, publication = false) {
  const pilot = page.getByTestId("closed-pilot");
  await pilot.locator("input").nth(0).fill("e2e-campaign");
  await pilot.locator("input").nth(1).fill("e2e-code");
  await pilot.locator("button").first().click();
  await expect(pilot.locator("input[type=checkbox]").first()).toBeVisible();
  const consent = pilot.locator("input[type=checkbox]");
  await consent.nth(0).check();
  await consent.nth(1).check();
  await consent.nth(2).check();
  if (publication) await consent.nth(3).check();
  await pilot.locator("button").first().click();
  await expect(pilot.locator("input").first()).toBeVisible();
  await pilot.locator("button").first().click();
  for (let index = 0; index < 3; index += 1) {
    await expect(pilot.locator("button").first()).toBeVisible();
    await pilot.locator("button").first().click();
  }
  await expect(pilot.locator("textarea")).toBeVisible();
  await pilot.locator("textarea").fill("bounded e2e feedback");
  await pilot.locator("button").first().click();
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
  await pilot.locator("input").nth(0).fill("invalid");
  await pilot.locator("input").nth(1).fill("invalid");
  await pilot.locator("button").first().click();
  await expect(pilot.getByRole("alert")).toBeVisible();
  expect(await pilot.locator("input[type=checkbox]").count()).toBe(0);
  expect(errors.filter((item) => !item.includes("status of 404"))).toEqual([]);
});

test("network failure shows a bounded degraded state without an infinite spinner", async ({ page }) => {
  const { errors } = await openPilot(page, "en", { networkFailure: true });
  const pilot = page.getByTestId("closed-pilot");
  await pilot.locator("input").nth(0).fill("network-failure");
  await pilot.locator("input").nth(1).fill("bounded-code");
  await pilot.locator("button").first().click();
  await expect(pilot.getByRole("alert")).toBeVisible();
  expect(await pilot.locator("button").first().isEnabled()).toBe(true);
  expect(errors.filter((item) => !item.includes("net::ERR_FAILED"))).toEqual([]);
});

test("publication remains private until approval and disappears after revocation", async ({ page }) => {
  const { errors } = await openPilot(page, "en", { publication: true });
  await completeParticipantFlow(page, true);
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
    expect(errors).toEqual([]);
  });
}
