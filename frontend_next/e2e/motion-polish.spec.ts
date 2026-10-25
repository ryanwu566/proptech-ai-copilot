import { mkdir } from "node:fs/promises";
import path from "node:path";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

const A = "proptech-demo-a";
const shots = path.resolve(process.cwd(), "../.local/motion-polish");
const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
// CSS-module keyframes are hashed in production builds ("_x1y2_case-settle"); compare the authored name.
const animation = (locator: Locator) => locator.evaluate((node) => ({ name: getComputedStyle(node).animationName.split("_").pop(), delay: getComputedStyle(node).animationDelay }));
const handoff = (page: Page) => page.getByTestId("case-workflow-handoff").getByRole("link").first();

function guard(page: Page, baseURL: string) {
  const calls: string[] = [];
  return page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  }).then(() => calls);
}

async function seed(page: Page) {
  await page.addInitScript((row) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row]));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, e9Case());
}

/** Layout shifts recorded from now on; transforms and opacity never count. */
async function watchShifts(page: Page) {
  await page.evaluate(() => {
    const target = window as Window & { motionShift?: number };
    target.motionShift = 0;
    new PerformanceObserver((list) => { for (const entry of list.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[]) if (!entry.hadRecentInput) target.motionShift! += entry.value; }).observe({ type: "layout-shift" });
  });
}

test("stage navigation settles the route's blocks in sequence; direct load and reduced motion stay still", async ({ page, baseURL }) => {
  await seed(page);
  const calls = await guard(page, baseURL!);
  await page.goto("/cases/case-a/market");
  const blocks = page.locator("[data-case-route-content] > main > :first-child > *");
  await expect(blocks.first()).toBeVisible();
  expect((await animation(blocks.first())).name).toBe("none");

  await watchShifts(page);
  await handoff(page).click();
  await expect(page).toHaveURL(/\/location$/);
  const content = page.locator("[data-case-route-content]");
  expect((await animation(content)).name).toBe("case-fade");
  const delays = await blocks.evaluateAll((nodes) => nodes.slice(0, 5).map((node) => [getComputedStyle(node).animationName.split("_").pop(), getComputedStyle(node).animationDelay]));
  expect(delays.slice(0, 4)).toEqual([["case-settle", "0s"], ["case-settle", "0.04s"], ["case-settle", "0.08s"], ["case-settle", "0.12s"]]);
  if (delays[4]) expect(delays[4]).toEqual(["case-settle", "0.12s"]);
  // The rail indicator grows into the new section; the content is interactive throughout.
  expect((await animation(page.locator("[data-case-rail] [aria-current='page']"))).name).toBe("rail-current");
  await page.waitForTimeout(700);
  expect(await page.evaluate(() => (window as Window & { motionShift?: number }).motionShift)).toBeLessThan(0.01);

  await page.emulateMedia({ reducedMotion: "reduce" });
  await handoff(page).click();
  await expect(page).toHaveURL(/\/risk$/);
  expect((await animation(content)).name).toBe("none");
  expect((await animation(blocks.first())).name).toBe("none");
  expect((await animation(page.locator("[data-case-rail] [aria-current='page']"))).name).toBe("none");
  expect(calls).toEqual([]);
});

test("entering the Brief, decision groups arrive attention → known → unknown", async ({ page, baseURL }) => {
  await seed(page);
  const calls = await guard(page, baseURL!);
  await page.goto("/cases/case-a/finance");
  await handoff(page).click();
  await expect(page).toHaveURL(/\/overview$/);
  const groups = page.locator("[data-route-enter] [class*='decisionGroup']");
  await expect(groups.first()).toBeVisible();
  const timing = await groups.evaluateAll((nodes) => nodes.slice(0, 3).map((node) => [getComputedStyle(node).animationName.split("_").pop(), getComputedStyle(node).animationDelay]));
  expect(timing).toEqual([["brief-group", "0.12s"], ["brief-group", "0.16s"], ["brief-group", "0.2s"]]);
  expect(calls).toEqual([]);
});

test("Compare columns enter together, revealed rows fade in, and only selectable cases lift", async ({ page, baseURL }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => localStorage.setItem("proptech_onboarding_seen", "true"));
  const calls = await guard(page, baseURL!);
  await page.goto("/");
  await page.getByTestId("complete-example-start").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));
  await page.getByTestId("demo-compare").click();
  await expect(page).toHaveURL(/\/compare\?cases=/);
  const heads = page.getByTestId("compare-desktop").locator("thead th");
  await expect(heads.first()).toBeVisible();
  const columns = await heads.evaluateAll((nodes) => nodes.map((node) => `${getComputedStyle(node).animationName.split("_").pop()} ${getComputedStyle(node).animationDelay} ${getComputedStyle(node).animationDuration}`));
  expect(new Set(columns)).toEqual(new Set(["compare-settle 0s 0.36s"]));

  // A row that "show all" reveals fades in like the rest of its area.
  const hiddenId = await page.getByTestId("compare-desktop").locator("tbody tr[hidden]").first().getAttribute("data-testid");
  expect(hiddenId).toBeTruthy();
  await page.getByTestId("compare-fields-toolbar").getByRole("button").first().click();
  const revealed = page.getByTestId(hiddenId!);
  await expect(revealed).toBeVisible();
  expect((await animation(revealed)).name).toBe("compare-fade");

  const card = page.locator("label:has(input[type='checkbox'])").first();
  await card.hover();
  await expect(card).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, -1)");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(card).toHaveCSS("transform", "none");
  expect(calls).toEqual([]);
});

test("the Report lands as one sheet on screen, prints still, and its primary action lifts only on hover", async ({ page, baseURL }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => localStorage.setItem("proptech_onboarding_seen", "true"));
  const calls = await guard(page, baseURL!);
  await page.goto("/");
  await page.getByTestId("complete-example-start").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));
  await page.goto(`/cases/${A}/report`);
  const sheet = page.getByTestId("report-evidence");
  await expect(sheet).toBeVisible();
  expect((await animation(sheet)).name).toBe("report-sheet");
  for (const id of ["report-executive", "report-core-page-2", "report-core-page-3"]) await expect(page.getByTestId(id)).toBeVisible();

  const print = page.getByTestId("report-controls").locator(".ds-button--primary");
  await print.hover();
  await expect(print).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, -1)");
  await page.mouse.move(0, 0);
  await print.focus();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  await expect(print).toBeFocused();
  await expect(print).toHaveCSS("outline-style", "solid");
  await expect(print).toHaveCSS("transform", "none");

  await page.emulateMedia({ media: "print" });
  expect((await animation(sheet)).name).toBe("none");
  expect(calls).toEqual([]);
});

for (const width of [390, 430, 1024, 1440]) test(`at ${width}px the complete journey keeps every surface in view with no overflow or provider call`, async ({ page, baseURL }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width, height: 900 });
  await page.addInitScript(() => localStorage.setItem("proptech_onboarding_seen", "true"));
  const calls = await guard(page, baseURL!);
  await mkdir(shots, { recursive: true });
  const capture = async (name: string) => {
    await page.waitForTimeout(650);
    expect(await noOverflow(page), `${name} overflows at ${width}px`).toBe(true);
    await page.screenshot({ path: path.join(shots, `${name}-${width}.png`) });
  };
  await page.goto("/");
  await capture("home");
  await page.getByTestId("complete-example-start").click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/overview$`));
  for (const section of ["market", "risk"]) {
    await page.locator(`[data-case-rail] a[href$='/${section}']`).click();
    await expect(page).toHaveURL(new RegExp(`/${section}$`));
    await expect(page.locator("[data-case-rail] [aria-current='page']")).toBeInViewport({ ratio: 0.9 });
    await capture(section);
  }
  await page.locator("[data-case-rail] a[href$='/overview']").click();
  await expect(page.getByTestId("commercial-overview-workspace")).toBeVisible();
  await capture("brief");
  await page.getByTestId("demo-compare").click();
  await expect(page).toHaveURL(/\/compare\?cases=/);
  await expect(page.getByTestId(width < 768 ? "compare-mobile" : "compare-desktop")).toBeVisible();
  await capture("compare");
  await page.getByTestId("compare-report-handoff").getByRole("link").first().click();
  await expect(page).toHaveURL(new RegExp(`/cases/${A}/report$`));
  await expect(page.getByTestId("report-core-page-3")).toBeVisible();
  await capture("report");
  expect(calls).toEqual([]);
});
