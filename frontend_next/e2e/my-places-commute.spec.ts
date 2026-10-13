import { expect, test, type Page } from "@playwright/test";
import { placesCopy } from "../lib/my-places-copy";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

const CASES = "proptech.savedCases.v1";
const PLACES = "proptech.my-places.v1";
const ROUTES = "proptech.case-commute.v1";
const locales = ["zh-TW", "en", "ja", "ko"] as const;
const widths = [390, 430, 1024, 1440];
async function overflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}
async function seed(page: Page) {
  const rows = [e9Case(), e9Case("case-b")];
  await page.addInitScript(({ key, rows }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(rows)); }, { key: CASES, rows });
  return JSON.stringify(rows);
}
for (const locale of locales) for (const width of widths) {
  test(`${locale} ${width}: explicit routes, persistence, stale evidence and property isolation`, async ({ page }, testInfo) => {
    const c = placesCopy[locale];
    await page.setViewportSize({ width, height: 900 });
    const original = await seed(page);
    const attempts: Array<Record<string, unknown>> = []; const automatic: string[] = [];
    const observed: string[] = [];
    page.on("request", (request) => { if (isProviderRequest(request, testInfo.project.use.baseURL!)) observed.push(request.url()); });
    await page.route("http://e2e.test/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/commute/route")) {
        const payload = route.request().postDataJSON(); attempts.push(payload);
        await new Promise((done) => setTimeout(done, 100));
        const unknown = payload.destination_address === "Unknown address";
        return route.fulfill({ json: { status: unknown ? "unresolved" : "resolved", source: "google_routes", mode: payload.mode, duration_min: unknown ? null : 24, duration_seconds: unknown ? null : 1440, distance_m: unknown ? null : 9800, checked_at: "2026-10-12T04:00:00.000Z", partial: false, fallback: false, reason_code: unknown ? "route_not_found" : "success", message: "provider message must not leak", disclaimer: "provider disclaimer must not leak" } });
      }
      if (/commute|geocod|location-insight|terrain|valuation|market/.test(path)) automatic.push(path);
      return route.fulfill({ status: 200, json: {} });
    });
    await page.goto("/places");
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByRole("heading", { name: c.places, exact: true })).toBeVisible();
    const labels = ["我的公司 / Work", "父母家 / 家族", "Unknown place / 미확인"];
    for (let i = 0; i < 3; i++) {
      await page.getByRole("button", { name: c.add, exact: true }).click();
      await expect(page.getByLabel(c.label, { exact: true })).toBeFocused();
      await page.getByLabel(c.label, { exact: true }).fill(labels[i]);
      await page.getByLabel(c.address, { exact: true }).fill(i === 2 ? "Unknown address" : `臺北車站 ${i}`);
      await page.getByLabel(c.trips, { exact: true }).fill(i === 0 ? "5" : "2");
      await page.getByRole("combobox", { name: c.mode, exact: true }).selectOption(i === 1 ? "walking" : "transit");
      await page.getByRole("button", { name: c.save, exact: true }).click();
    }
    await expect(page.getByTestId("place-card")).toHaveCount(3);
    await page.getByRole("button", { name: `${c.up}: ${labels[1]}`, exact: true }).click();
    await expect(page.getByTestId("place-card").first()).toContainText(labels[1]);
    await overflow(page);
    await page.reload();
    await expect(page.getByTestId("locale-switcher")).toHaveValue(locale);
    expect(attempts).toHaveLength(0);
    await page.goto("/cases/case-a/commute-planner");
    await expect(page.getByTestId("commute-destination")).toHaveCount(3);
    await expect(page.getByTestId("commute-destination").first()).toHaveAttribute("data-status", "NOT_CHECKED");
    expect(attempts).toHaveLength(0);
    await overflow(page);
    // Keyboard submit and synchronous lock: a second click cannot issue another batch.
    const calculate = page.getByRole("button", { name: c.calculate, exact: true });
    await calculate.focus(); await page.keyboard.press("Enter");
    await expect(page.locator('[data-status="LOADING"]')).toHaveCount(3);
    await expect(calculate).toBeDisabled();
    await expect(page.locator('[data-status="AVAILABLE"]')).toHaveCount(2);
    await expect(page.locator('[data-status="UNAVAILABLE"]')).toHaveCount(1);
    await expect(page.getByTestId("commute-destination").first().locator("time")).toHaveAttribute("dateTime", "2026-10-12T04:00:00.000Z");
    expect(attempts).toHaveLength(3);
    await expect(page.getByTestId("weekly-summary")).toContainText(c.hours.replace("{{h}}", "5").replace("{{m}}", "36"));
    await expect(page.getByTestId("weekly-summary")).toContainText(labels[2]);
    await expect(page.getByText("provider message must not leak")).toHaveCount(0);
    await overflow(page);
    await page.screenshot({ path: testInfo.outputPath(`${locale}-${width}.png`), fullPage: true });
    await page.reload();
    await expect(page.locator('[data-status="AVAILABLE"]')).toHaveCount(2);
    expect(attempts).toHaveLength(3);
    // Reopen, compare, report, overview, locale switches must stay read only.
    for (const path of ["/cases/case-a/overview", "/compare?cases=case-a,case-b", "/cases/case-a/report", "/cases/case-a/commute-planner"]) await page.goto(path);
    await expect(page.getByTestId("commute-destination")).toHaveCount(3);
    await page.getByTestId("locale-switcher").selectOption(locale === "en" ? "ja" : "en");
    await page.getByTestId("locale-switcher").selectOption(locale);
    expect(attempts).toHaveLength(3);
    await page.goto("/places");
    const work = page.getByTestId("place-card").filter({ hasText: labels[0] });
    await work.getByRole("button", { name: c.edit, exact: true }).click();
    await page.getByLabel(c.address, { exact: true }).fill("京都駅");
    await page.getByRole("button", { name: c.save, exact: true }).click();
    await page.goto("/cases/case-a/commute-planner");
    const changed = page.getByTestId("commute-destination").filter({ hasText: labels[0] });
    await expect(changed).toHaveAttribute("data-status", "STALE");
    await expect(changed).toContainText("臺北車站 0");
    await expect(page.getByTestId("weekly-summary")).toContainText(c.hours.replace("{{h}}", "1").replace("{{m}}", "36"));
    expect(attempts).toHaveLength(3);
    await changed.getByRole("button", { name: c.refreshOne, exact: true }).click();
    await expect(changed).toHaveAttribute("data-status", "AVAILABLE");
    expect(attempts).toHaveLength(4);
    await page.goto("/places");
    await page.getByTestId("place-card").filter({ hasText: labels[0] }).getByRole("button", { name: c.edit, exact: true }).click();
    await page.getByRole("combobox", { name: c.mode, exact: true }).selectOption("driving");
    await page.getByLabel(c.trips, { exact: true }).fill("0");
    await page.getByRole("button", { name: c.save, exact: true }).click();
    await page.goto("/cases/case-a/commute-planner");
    await expect(page.getByTestId("commute-destination").filter({ hasText: labels[0] })).toHaveAttribute("data-status", "STALE");
    await expect(page.getByTestId("commute-destination").filter({ hasText: labels[0] }).getByRole("button", { name: c.refreshOne, exact: true })).toBeDisabled();
    const family = page.getByTestId("commute-destination").filter({ hasText: labels[1] });
    await family.getByRole("checkbox").uncheck();
    await page.reload(); await expect(family.getByRole("checkbox")).not.toBeChecked();
    expect(attempts).toHaveLength(4);
    await page.getByRole("navigation", { name: c.switchProperty }).getByRole("link", { name: /B$/ }).click();
    await expect(page.locator('[data-status="NOT_CHECKED"]')).toHaveCount(3);
    expect(attempts).toHaveLength(4);
    await page.goto("/cases/case-a/commute-planner");
    await expect(page.locator('[data-status="STALE"]')).toHaveCount(1);
    expect(automatic).toEqual([]);
    expect(observed).toHaveLength(attempts.length);
    expect(await page.evaluate((key) => localStorage.getItem(key), CASES)).toBe(original);
    expect(await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).version, PLACES)).toBe(1);
    expect(await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).version, ROUTES)).toBe(1);
    await testInfo.attach("provider-attempts", { body: JSON.stringify({ explicit: attempts.length, automatic: automatic.length, classified: observed.length, attempts }), contentType: "application/json" });
  });
}

test("in-flight result stays bound to its old destination and no later routes run after editing", async ({ page }) => {
  await seed(page);
  const now = "2026-10-12T04:00:00.000Z";
  await page.addInitScript(({ key, now }) => localStorage.setItem(key, JSON.stringify({ version: 1, places: [1, 2].map((i) => ({ id: `p${i}`, label: `Place ${i}`, category: "custom", address: `Address ${i}`, transportMode: "walking", weeklyTrips: 5, priority: "important", createdAt: now, updatedAt: now })) })), { key: PLACES, now });
  let count = 0; let release!: () => void;
  const paused = new Promise<void>((done) => { release = done; });
  await page.route("**/commute/route", async (route) => { count++; await paused; await route.fulfill({ json: { status: "resolved", source: "google_routes", mode: "walking", duration_min: 20, duration_seconds: 1200, distance_m: 1000, checked_at: now, partial: false, fallback: false, reason_code: "success" } }); });
  await page.goto("/cases/case-a/commute-planner");
  await page.getByRole("button", { name: placesCopy["zh-TW"].calculate, exact: true }).click();
  await expect.poll(() => count).toBe(1);
  await page.evaluate((key) => { const data = JSON.parse(localStorage.getItem(key)!); data.places[0].address = "Changed address"; localStorage.setItem(key, JSON.stringify(data)); window.dispatchEvent(new StorageEvent("storage", { key })); }, PLACES);
  await expect(page.getByTestId("commute-destination").first()).toContainText("Changed address");
  release();
  await expect(page.getByTestId("commute-destination").first()).toHaveAttribute("data-status", "STALE");
  expect(count).toBe(1);
  await expect(page.getByTestId("weekly-summary")).toContainText("未知目的地: 2");
});

test("duplicate destinations use one provider attempt per explicit batch; malformed evidence stays unknown", async ({ page }, testInfo) => {
  await seed(page);
  const now = "2026-10-12T04:00:00.000Z";
  await page.addInitScript(({ key, now }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify({ version: 1, places: [1, 2].map((i) => ({ id: `p${i}`, label: `Same route ${i}`, category: "custom", address: "Same address", transportMode: "walking", weeklyTrips: i, priority: "important", createdAt: now, updatedAt: now })) })); }, { key: PLACES, now });
  let count = 0;
  await page.route("**/commute/route", async (route) => { count++; await route.fulfill({ json: { status: "resolved", source: "google_routes", mode: "walking", duration_min: 20, duration_seconds: 1200, distance_m: 1000, checked_at: now, partial: false, fallback: false, reason_code: count === 1 ? "invalid_reason" : "success" } }); });
  await page.goto("/cases/case-a/commute-planner");
  const c = placesCopy["zh-TW"];
  expect(count).toBe(0);
  await page.getByRole("button", { name: c.calculate, exact: true }).click();
  await expect(page.locator('[data-status="UNAVAILABLE"]')).toHaveCount(2);
  expect(count).toBe(1);
  await expect(page.getByTestId("weekly-summary")).toContainText("未知目的地: 2");
  await page.getByRole("button", { name: c.refresh, exact: true }).click();
  await expect(page.locator('[data-status="AVAILABLE"]')).toHaveCount(2);
  expect(count).toBe(2);
  await expect(page.getByTestId("weekly-summary")).toContainText("2 小時 0 分");
  await page.reload();
  await expect(page.locator('[data-status="AVAILABLE"]')).toHaveCount(2);
  expect(count).toBe(2);
  await testInfo.attach("provider-attempts", { body: JSON.stringify({ explicit: count, automatic: 0 }), contentType: "application/json" });
});

test("latest persisted frequency and selection prevent a paid request before storage events arrive", async ({ page }, testInfo) => {
  await seed(page);
  const now = "2026-10-13T00:00:00.000Z";
  await page.addInitScript(({ key, now }) => localStorage.setItem(key, JSON.stringify({ version: 1, places: [1, 2].map((i) => ({ id: `p${i}`, label: `Place ${i}`, category: "custom", address: `Address ${i}`, transportMode: "walking", weeklyTrips: 5, priority: "important", createdAt: now, updatedAt: now })) })), { key: PLACES, now });
  let attempts = 0;
  await page.route("**/commute/route", (route) => { attempts++; return route.fulfill({ json: {} }); });
  await page.goto("/cases/case-a/commute-planner");
  const calculate = page.getByRole("button", { name: placesCopy["zh-TW"].calculate, exact: true });
  await expect(calculate).toBeEnabled();
  await calculate.evaluate((button, { placesKey, routesKey }) => {
    const data = JSON.parse(localStorage.getItem(placesKey)!);
    data.places[0].weeklyTrips = 0;
    localStorage.setItem(placesKey, JSON.stringify(data));
    localStorage.setItem(routesKey, JSON.stringify({ version: 1, routes: [], selections: { "case-a": ["p1"] } }));
    (button as HTMLButtonElement).click();
  }, { placesKey: PLACES, routesKey: ROUTES });
  await expect(calculate).toBeDisabled();
  await expect(page.getByTestId("commute-destination").nth(1).getByRole("checkbox")).not.toBeChecked();
  expect(attempts).toBe(0);
  await testInfo.attach("provider-attempts", { body: JSON.stringify({ explicit: 0, automatic: 0 }), contentType: "application/json" });
});

test("storage read failures are visible", async ({ page }) => {
  await seed(page);
  await page.addInitScript(() => {
    const read = Storage.prototype.getItem;
    Storage.prototype.getItem = function (key) { if (key === "proptech.my-places.v1") throw new Error("blocked"); return read.call(this, key); };
  });
  await page.goto("/places");
  await expect(page.locator("#main-content").getByRole("alert")).toContainText(placesCopy["zh-TW"].storageError);
  await expect(page.getByRole("button", { name: placesCopy["zh-TW"].add, exact: true })).toBeDisabled();
  await page.goto("/cases/case-a/commute-planner");
  await expect(page.locator("#main-content").getByRole("alert")).toContainText(placesCopy["zh-TW"].storageError);
});

test("storage write failures are visible and preserve authored destinations", async ({ page }) => {
  const original = await seed(page);
  const c = placesCopy["zh-TW"];
  await page.goto("/places");
  await page.getByRole("button", { name: c.add, exact: true }).click();
  await page.getByLabel(c.label, { exact: true }).fill("Authored label / 原文");
  await page.getByLabel(c.address, { exact: true }).fill("Authored address");
  await page.evaluate(() => {
    const write = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) { if (key === "proptech.my-places.v1") throw new Error("quota"); write.call(this, key, value); };
  });
  await page.getByRole("button", { name: c.save, exact: true }).click();
  await expect(page.locator("#main-content").getByRole("alert")).toContainText(c.storageError);
  await expect(page.getByLabel(c.label, { exact: true })).toHaveValue("Authored label / 原文");
  expect(await page.evaluate((key) => localStorage.getItem(key), PLACES)).toBeNull();
  expect(await page.evaluate((key) => localStorage.getItem(key), CASES)).toBe(original);
});

test("current case navigation reaches the read-only planner", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-a/overview");
  await page.getByRole("link", { name: placesCopy["zh-TW"].planner, exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/case-a\/commute-planner$/);
  await expect(page.getByRole("heading", { name: placesCopy["zh-TW"].planner, exact: true })).toBeVisible();
});

test("visible keyboard focus and connected labels across locales and widths", async ({ page }, testInfo) => {
  const providers: string[] = [];
  page.on("request", (request) => { if (isProviderRequest(request, testInfo.project.use.baseURL!)) providers.push(request.url()); });
  await page.goto("/places");
  for (const locale of locales) for (const width of widths) {
    const c = placesCopy[locale];
    await page.setViewportSize({ width, height: 900 });
    await page.getByTestId("locale-switcher").selectOption(locale);
    const add = page.getByRole("button", { name: c.add, exact: true });
    await expect(add).toBeEnabled();
    await add.focus(); await page.keyboard.press("Tab"); await page.keyboard.press("Shift+Tab");
    await expect(add).toBeFocused();
    expect(await add.evaluate((element) => getComputedStyle(element).outlineWidth)).toBe("3px");
    await page.keyboard.press("Enter");
    const label = page.getByLabel(c.label, { exact: true });
    await expect(label).toBeFocused();
    await overflow(page);
    await page.getByRole("button", { name: c.cancel, exact: true }).click();
  }
  expect(providers).toEqual([]);
});
