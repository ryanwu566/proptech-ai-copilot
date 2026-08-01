import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["zh-TW", "en", "ja", "ko"];
const MOBILE_WIDTHS = [360, 390, 430];

async function mockPilotApi(page: Page, options: { rejectAccess?: boolean; publication?: boolean } = {}) {
  let eventCount = 0;
  await page.route("**/client-errors", (route) => route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ status: "accepted", support_reference: "e2e-support-reference" }) }));
  await page.route("**/pilot/access", (route) => {
    if (options.rejectAccess) return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Pilot access is unavailable." }) });
    return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ session_id: "e2e-session", session_token: "e2e-session-token", mode: "closed_pilot", consent_version: "pilot-consent-v1" }) });
  });
  await page.route("**/pilot/sessions/*/consent", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted" }) }));
  await page.route("**/pilot/sessions/*/profile", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted" }) }));
  await page.route("**/pilot/sessions/*/events", async (route) => { eventCount += 1; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted", evidence_state: "complete" }) }); });
  await page.route("**/pilot/sessions/*/feedback", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted", publication_status: options.publication ? "private" : "private" }) }));
  await page.route("**/pilot/sessions/*/complete", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "completed", mode: "closed_pilot" }) }));
  return { eventCount: () => eventCount };
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

async function completeParticipantFlow(page: Page) {
  const pilot = page.getByTestId("closed-pilot");
  await pilot.locator("input").nth(0).fill("e2e-campaign");
  await pilot.locator("input").nth(1).fill("e2e-code");
  await pilot.locator("button").first().click();
  await expect(pilot.locator("input[type=checkbox]").first()).toBeVisible();
  const consent = pilot.locator("input[type=checkbox]");
  await consent.nth(0).check();
  await consent.nth(1).check();
  await consent.nth(2).check();
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
