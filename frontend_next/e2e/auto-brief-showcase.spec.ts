import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { buildDemoCases } from "../lib/workspace/demo-cases";
import { DEMO_CASE_A_ID, DEMO_CASE_B_ID } from "../lib/workspace/demo-case-ids";
import { autoBriefCopy } from "../lib/workspace/auto-brief-copy";
import { homeStartCopy } from "../lib/home-start-copy";
import { plotNearby } from "../lib/workspace/auto-brief-presentation";
import { isProviderRequest } from "./helpers/provider-request";

/**
 * Gate A1-3: "Watch complete example" plays Demo A's Auto Brief from the homepage with one click, through the
 * same state machine, stage and Brief as a real case, using saved demo snapshots only. Provider calls are
 * counted and must be exactly zero; the showcase never touches the visitor's own cases.
 */
const KEY = "proptech.savedCases.v1";
const A = DEMO_CASE_A_ID;
const LOCALES = ["zh-TW", "en", "ja", "ko"] as const;
type Locale = (typeof LOCALES)[number];
const SCENES = ["lockin", "market", "location", "risk", "money", "converge", "complete"];
/** Live data providers the showcase must never reach, at any moment. */
const PROVIDER_HOSTS = /googleapis\.com|maps\.google|google\.com\/maps|earthengine|tgos|ris\.gov\.tw|nlsc\.gov\.tw|data\.gov\.tw|tdx\.transportdata/i;
const RAW = /\b(lockin|completed_with_gaps|needs_input|no_data|provider_unavailable|partial_evidence|reused_saved|demo_snapshot|money_partial|demo_fixture|real_case)\b/;

async function prepare(page: Page, baseURL: string, { locale = "zh-TW", rows = [] as unknown[], reducedMotion = false }: { locale?: Locale; rows?: unknown[]; reducedMotion?: boolean } = {}) {
  if (reducedMotion) await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(({ key, rows, locale }) => {
    if (sessionStorage.getItem("showcase-seeded")) return;
    sessionStorage.setItem("showcase-seeded", "1");
    // A clean browser: no cases, no session, nothing but the chosen locale.
    if (rows.length) localStorage.setItem(key, JSON.stringify(rows)); else localStorage.removeItem(key);
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
  }, { key: KEY, rows, locale });
  const watch = { recording: false, calls: [] as string[], providers: [] as string[] };
  page.on("request", (request) => { if (PROVIDER_HOSTS.test(request.url())) watch.providers.push(request.url()); });
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (PROVIDER_HOSTS.test(request.url())) return route.abort();
    if (isProviderRequest(request, baseURL)) {
      if (watch.recording) watch.calls.push(`${request.method()} ${url.origin}${url.pathname}`);
      if (url.origin !== new URL(baseURL).origin) return route.abort();
    }
    return route.fallback();
  });
  return watch;
}

const panel = (page: Page) => page.getByTestId("auto-brief-panel");
const stage = (page: Page) => page.getByTestId("auto-brief-stage");

async function startShowcase(page: Page, watch: { recording: boolean }, locale: Locale = "zh-TW") {
  await page.goto("/");
  const cta = page.getByTestId("complete-example-start");
  await expect(cta).toHaveText(homeStartCopy[locale].completeExample);
  watch.recording = true;
  await cta.click();
  // One click: installed, opened and playing; the one-time flag is consumed so a refresh never replays.
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/location$`));
  await expect(stage(page)).toHaveAttribute("data-showcase", "on");
}

async function skipToEnd(page: Page) {
  await page.getByTestId("auto-brief-skip").click();
  await expect(stage(page)).toHaveAttribute("data-scene", "complete");
}

test("clean browser: one click plays the full showcase in order, from saved evidence, with zero provider calls", async ({ page, baseURL }) => {
  test.setTimeout(150_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const watch = await prepare(page, baseURL!);
  const c = autoBriefCopy["zh-TW"];
  await page.goto("/");
  // The real address journey stays primary; the example is the secondary action.
  await expect(page.locator("form.commercial-home__form button[type=submit]")).toHaveClass(/ds-button--primary/);
  await expect(page.getByTestId("complete-example-start")).toHaveClass(/ds-button--secondary/);
  await startShowcase(page, watch);
  await expect(page.getByTestId("auto-brief-demo-note")).toHaveText(c.demoNote);
  await expect(page).not.toHaveURL(/login|signup/);

  const demo = buildDemoCases("zh-TW")[0];
  const groups = plotNearby(demo.data.nearbyFacilities).groups.map((row) => row.group);
  const seen: Array<{ scene: string; at: number }> = [];
  const started = Date.now();
  while (Date.now() - started < 90_000) {
    const scene = await stage(page).getAttribute("data-scene");
    if (scene && seen.at(-1)?.scene !== scene) {
      seen.push({ scene, at: Date.now() - started });
      await expect(page.getByTestId("auto-brief-narration")).toHaveText(c[`narr_${scene as "market"}`]);
      if (scene === "lockin") await expect(page.getByTestId("auto-brief-scene-lockin")).toContainText(demo.data.propertyIdentityAnchor!.normalized_address);
      if (scene === "market") await expect(page.getByTestId("auto-brief-market-state")).toHaveText(c.market_available);
      if (scene === "location") {
        await expect(page.getByTestId("auto-brief-poi-legend").locator("li")).toHaveCount(groups.length);
        await expect(page.getByTestId("auto-brief-demographics")).toContainText("6,842");
      }
      if (scene === "risk") await expect(page.getByTestId("auto-brief-risk-layers").locator(".ds-role-success")).toHaveCount(0);
      if (scene === "money") await expect(page.getByTestId("auto-brief-scene-money")).toContainText(c.moneyPayment);
      // The rail never shows a chapter that has not been presented yet as finished.
      if (scene === "market") await expect(page.getByTestId("auto-brief-step-risk")).toHaveAttribute("data-status", "pending");
    }
    if (scene === "complete") break;
    await page.waitForTimeout(200);
  }
  expect(seen.map((row) => row.scene)).toEqual(SCENES);
  const story = seen.at(-1)!.at;
  expect(story, "showcase length").toBeGreaterThan(40_000);
  expect(story, "showcase length").toBeLessThan(75_000);

  const completion = page.getByTestId("auto-brief-completion");
  await expect(completion).toHaveAttribute("data-ending", "completed_with_gaps");
  await expect(page.getByTestId("auto-brief-digest")).toContainText(c.digestQuestions);
  for (const id of ["view-brief", "compare", "report", "replay", "analyze-own"]) await expect(page.getByTestId(`auto-brief-${id}`)).toBeVisible();
  await expect(page.getByTestId("auto-brief-step-risk")).toHaveAttribute("data-status", "partial");
  expect(await panel(page).innerText()).not.toMatch(RAW);
  expect(watch.calls).toEqual([]);
  expect(watch.providers).toEqual([]);
});

test("replay is deterministic, real cases are never touched, refresh never replays, and every handoff works", async ({ page, baseURL }) => {
  const real = [e9Case("real-1"), e9Case("real-2")];
  const watch = await prepare(page, baseURL!, { locale: "en", rows: real });
  await startShowcase(page, watch, "en");
  await skipToEnd(page);
  const first = await page.getByTestId("auto-brief-completion").innerText();
  const stored = () => page.evaluate((key) => JSON.parse(localStorage.getItem(key)!) as Array<{ id: string }>, KEY);
  const rows = await stored();
  expect(rows.map((row) => row.id).sort()).toEqual([A, DEMO_CASE_B_ID, "real-1", "real-2"].sort());
  for (const row of real) expect(rows.find((item) => item.id === row.id)).toEqual(row);
  for (let replay = 0; replay < 2; replay += 1) {
    await page.getByTestId("auto-brief-replay").click();
    await expect(stage(page)).toHaveAttribute("data-scene", "lockin");
    await skipToEnd(page);
    expect(await page.getByTestId("auto-brief-completion").innerText()).toBe(first);
    expect(await stored()).toEqual(rows);
  }
  // Refresh shows the saved result: no replay, no acquisition.
  await page.reload();
  await expect(stage(page)).toHaveAttribute("data-scene", "complete");
  await expect(panel(page)).toHaveAttribute("data-run-status", "completed_with_gaps");
  // Opening the example again from Home keeps the same demo rows (no duplicates).
  await page.goto("/");
  await page.getByTestId("complete-example-start").click();
  await expect(stage(page)).toHaveAttribute("data-showcase", "on");
  await skipToEnd(page);
  expect(await stored()).toEqual(rows);

  await page.getByTestId("auto-brief-compare").click();
  await expect(page).toHaveURL(new RegExp(`/compare\\?cases=${A},${DEMO_CASE_B_ID}$`));
  await expect(page.getByTestId("compare-desktop")).toBeVisible();
  await page.goBack();
  await page.getByTestId("auto-brief-report").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/report$`));
  await expect(page.getByTestId("report-evidence")).toBeVisible();
  await page.goBack();
  await page.getByTestId("auto-brief-view-brief").click();
  await expect(page.getByTestId("commercial-overview-workspace")).toBeVisible();
  await page.goBack();
  await page.getByTestId("auto-brief-analyze-own").click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("#commercial-address")).toBeVisible();
  expect(watch.calls).toEqual([]);
  expect(watch.providers).toEqual([]);
});

test("pause holds the showcase on the current scene; resume continues the story", async ({ page, baseURL }) => {
  const watch = await prepare(page, baseURL!, { locale: "ja" });
  await startShowcase(page, watch, "ja");
  await expect(stage(page)).toHaveAttribute("data-scene", "lockin");
  await page.getByTestId("auto-brief-pause").click();
  await expect(page.getByTestId("auto-brief-pause")).toHaveText(autoBriefCopy.ja.resume);
  await page.waitForTimeout(4_500);
  await expect(stage(page)).toHaveAttribute("data-scene", "lockin");
  await page.getByTestId("auto-brief-pause").click();
  await expect(stage(page)).toHaveAttribute("data-scene", "market", { timeout: 6_000 });
  expect(watch.calls).toEqual([]);
});

test("reduced motion: the complete example as fast state cards, all evidence kept, no animation", async ({ page, baseURL }) => {
  const watch = await prepare(page, baseURL!, { locale: "ko", reducedMotion: true });
  await startShowcase(page, watch, "ko");
  await expect(stage(page)).toHaveAttribute("data-motion", "off");
  await expect(stage(page)).toHaveAttribute("data-scene", "complete");
  const running = () => stage(page).evaluate((root) => root.getAnimations({ subtree: true }).filter((animation) => animation.playState === "running").length);
  expect(await running()).toBe(0);
  for (const id of ["market", "location", "risk", "money"]) {
    await page.getByTestId(`auto-brief-review-${id}`).click();
    await expect(stage(page)).toHaveAttribute("data-scene", id);
    expect(await running()).toBe(0);
  }
  await expect(page.getByTestId("auto-brief-scene-money")).toContainText(autoBriefCopy.ko.moneyPayment);
  await page.getByTestId("auto-brief-review-location").click();
  await expect(page.getByTestId("auto-brief-demographics")).toBeVisible();
  expect(watch.calls).toEqual([]);
});

test("keyboard: start from Home, control the showcase and land on the result without focus theft", async ({ page, baseURL }) => {
  const watch = await prepare(page, baseURL!, { locale: "en" });
  await page.goto("/");
  watch.recording = true;
  await page.getByTestId("complete-example-start").focus();
  await page.keyboard.press("Enter");
  await expect(stage(page)).toHaveAttribute("data-showcase", "on");
  const skip = page.getByTestId("auto-brief-skip");
  // Focus moves once, to a live control; scenes never move it.
  await expect(page.locator("[data-auto-brief-control]:focus")).toHaveCount(1);
  await expect(stage(page)).toHaveAttribute("data-scene", /lockin|market/);
  await skip.focus();
  await page.keyboard.press("Enter");
  await expect(stage(page)).toHaveAttribute("data-scene", "complete");
  await expect(page.getByTestId("auto-brief-view-brief")).toBeFocused();
  await page.getByTestId("auto-brief-review-location").focus();
  await page.keyboard.press("Enter");
  await expect(stage(page)).toHaveAttribute("data-scene", "location");
  expect(watch.calls).toEqual([]);
});

for (const locale of LOCALES) {
  test(`${locale}: localized showcase at 390 / 430 / 1024 / 1440 without overflow or raw keys`, async ({ page, baseURL }) => {
    const c = autoBriefCopy[locale];
    await page.setViewportSize({ width: 390, height: 844 });
    const watch = await prepare(page, baseURL!, { locale });
    await startShowcase(page, watch, locale);
    await expect(page.getByTestId("auto-brief-demo-note")).toHaveText(c.demoNote);
    await expect(page.getByTestId("auto-brief-narration")).toHaveText(c.narr_lockin);
    await skipToEnd(page);
    await expect(page.getByTestId("auto-brief-narration")).toHaveText(c.narr_complete);
    await expect(page.getByTestId("auto-brief-view-brief")).toHaveText(c.viewBrief);
    await expect(page.getByTestId("auto-brief-compare")).toHaveText(c.compareDemo);
    await expect(page.getByTestId("auto-brief-report")).toHaveText(c.openReport);
    await expect(page.getByTestId("auto-brief-replay")).toHaveText(c.replay);
    await expect(page.getByTestId("auto-brief-analyze-own")).toHaveText(c.analyzeOwn);
    for (const width of [390, 430, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const scene of ["complete", "location", "risk", "money"]) {
        if (scene !== "complete") { await page.getByTestId(`auto-brief-review-${scene}`).click(); await expect(stage(page)).toHaveAttribute("data-scene", scene); }
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        expect(overflow, `${locale} ${width} ${scene}`).toBeLessThanOrEqual(0);
      }
      await page.getByTestId("auto-brief-back").click();
    }
    const text = await panel(page).innerText();
    expect(text).not.toMatch(RAW);
    if (locale === "en") expect(text.replace(/[㐀-鿿]+/g, "")).not.toMatch(/[぀-ヿ가-힯]/);
    expect(watch.calls).toEqual([]);
    expect(watch.providers).toEqual([]);
  });
}
