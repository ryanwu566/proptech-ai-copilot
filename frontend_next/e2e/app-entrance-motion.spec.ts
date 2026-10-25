import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

const LAYER = "[data-app-entrance]";

test.setTimeout(60_000);

async function seed(page: Page) {
  await page.addInitScript((rows) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale: "en" }));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, [e9Case()]);
}

function watchErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  return errors;
}

/** Holds the whole sequence at one moment so assertions do not race a 1.8s animation. */
const holdAt = (page: Page, time: number) => page.locator(LAYER).evaluate((layer, at) => {
  for (const animation of layer.getAnimations({ subtree: true })) { animation.pause(); animation.currentTime = at; }
}, time);
const resume = (page: Page) => page.locator(LAYER).evaluate((layer) => layer.getAnimations({ subtree: true }).forEach((animation) => animation.play()));

test("a fresh document load plays the entrance over an already-rendered app, then removes it", async ({ page }) => {
  const errors = watchErrors(page);
  const response = await page.goto("/privacy", { waitUntil: "commit" });
  expect(await response!.text()).toContain('data-app-entrance="" aria-hidden="true"');
  await page.locator(LAYER).waitFor({ state: "attached" });
  await holdAt(page, 300);
  const layer = page.locator(LAYER);
  await expect(page.locator("main").first()).toBeAttached();
  const box = await layer.boundingBox();
  const viewport = page.viewportSize()!;
  expect(box).toEqual({ x: 0, y: 0, width: viewport.width, height: viewport.height });
  const timing = await layer.evaluate((node) => node.getAnimations({ subtree: true }).map((animation) => {
    const computed = animation.effect!.getComputedTiming();
    return { end: Number(computed.endTime), iterations: computed.iterations };
  }));
  expect(Math.max(...timing.map((item) => item.end))).toBeCloseTo(1800, 0);
  expect(timing.every((item) => item.iterations === 1)).toBe(true);
  await resume(page);
  await expect(layer).toHaveCount(0, { timeout: 5_000 });
  expect(await page.evaluate(() => document.getAnimations().filter((animation) => animation.playState === "running" && (animation.effect as KeyframeEffect | null)?.target?.closest?.("[data-app-entrance]")).length)).toBe(0);
  expect(errors).toEqual([]);
});

test("the entrance is aria-hidden and never takes a click or focus; a key press fast-forwards it", async ({ page }) => {
  await page.goto("/privacy", { waitUntil: "commit" });
  await page.locator(LAYER).waitFor({ state: "attached" });
  await holdAt(page, 500);
  const layer = page.locator(LAYER);
  await expect(layer).toHaveAttribute("aria-hidden", "true");
  expect(await layer.evaluate((node) => getComputedStyle(node).pointerEvents)).toBe("none");
  const hit = await layer.evaluate((node) => {
    const points = [[0.5, 0.5], [0.1, 0.1], [0.9, 0.9]].map(([x, y]) => document.elementFromPoint(innerWidth * x, innerHeight * y));
    return points.some((element) => element && node.contains(element));
  });
  expect(hit).toBe(false);
  expect(await layer.locator("a, button, input, [tabindex]").count()).toBe(0);
  await page.waitForLoadState("load");
  // The sequence is held, so only intent can end it. Retried because hydration attaches the listener.
  await expect.poll(async () => {
    await page.keyboard.press("Tab");
    return layer.count();
  }, { timeout: 10_000 }).toBe(0);
  expect(await page.evaluate((selector) => Boolean(document.activeElement?.closest(selector)), LAYER)).toBe(false);
});

test("a pointer press during the opening ends it at once instead of waiting out the sequence", async ({ page }) => {
  await page.goto("/privacy", { waitUntil: "load" });
  const layer = page.locator(LAYER);
  if (await layer.count()) {
    await holdAt(page, 300);
    await expect.poll(async () => {
      await page.mouse.down({ button: "left" });
      await page.mouse.up({ button: "left" });
      return layer.count();
    }, { timeout: 10_000 }).toBe(0);
  }
  await expect(layer).toHaveCount(0);
});

test("Home's start content settles in behind the opening once, and stays still on in-app return", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("proptech_onboarding_seen", "true"));
  await page.goto("/", { waitUntil: "commit" });
  await page.locator(LAYER).waitFor({ state: "attached" });
  await page.waitForLoadState("domcontentloaded");
  const layered = () => page.evaluate(() => document.getAnimations()
    .filter((animation) => (animation as CSSAnimation).animationName === "home-arrive")
    .map((animation) => ({ end: Number(animation.effect!.getComputedTiming().endTime), iterations: animation.effect!.getComputedTiming().iterations })));
  const during = await layered();
  // Heading, address form, then the example and secondary entries together.
  expect(during.length).toBe(4);
  for (const item of during) { expect(item.iterations).toBe(1); expect(item.end).toBeLessThanOrEqual(1800); }
  await expect(page.locator(LAYER)).toHaveCount(0, { timeout: 5_000 });
  expect(await layered()).toEqual([]);
  await expect(page.locator(".commercial-home__start > header")).toHaveCSS("opacity", "1");
  await expect(page.locator(".commercial-home__start > header")).toHaveCSS("transform", "none");
  // In-app return to Home: no entrance, so no layering.
  await page.locator('a[href="/cases"]').first().click();
  await expect(page).toHaveURL(/\/cases$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator(".commercial-home__start > header")).toBeVisible();
  expect(await layered()).toEqual([]);
});

test("internal navigation between home, cases and workspace sections never replays the entrance", async ({ page }) => {
  await seed(page);
  const errors = watchErrors(page);
  await page.goto("/cases/case-a/overview");
  await expect(page.locator(LAYER)).toHaveCount(0, { timeout: 5_000 });
  await page.evaluate((selector) => {
    const marker = window as unknown as { __sameDocument: boolean; __entranceReplays: number };
    marker.__sameDocument = true;
    marker.__entranceReplays = 0;
    new MutationObserver((records) => {
      for (const record of records) for (const node of record.addedNodes) {
        if (node instanceof Element && (node.matches(selector) || node.querySelector(selector))) marker.__entranceReplays += 1;
      }
    }).observe(document.body, { childList: true, subtree: true });
  }, LAYER);
  const header = page.locator("header").first();
  await header.locator('a[href="/compare"]').first().click();
  await expect(page).toHaveURL(/\/compare/);
  await header.locator('a[href="/cases"]').first().click();
  await expect(page).toHaveURL(/\/cases$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/compare/);
  await page.goBack();
  await expect(page).toHaveURL(/\/cases\/case-a\/overview/);
  await page.locator(".commercial-brand").click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator(LAYER)).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as { __sameDocument?: boolean }).__sameDocument)).toBe(true);
  expect(await page.evaluate(() => (window as unknown as { __entranceReplays: number }).__entranceReplays)).toBe(0);
  expect(errors).toEqual([]);
});

test("a hard refresh plays it again because it is a new document", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.locator(LAYER)).toHaveCount(0, { timeout: 5_000 });
  const response = await page.reload({ waitUntil: "commit" });
  expect(await response!.text()).toContain("data-app-entrance");
  await expect(page.locator(LAYER)).toHaveCount(0, { timeout: 5_000 });
});

test("reduced motion skips every movement and lifts the layer in under 200ms", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors = watchErrors(page);
  await page.goto("/privacy", { waitUntil: "commit" });
  await page.locator(LAYER).waitFor({ state: "attached" }).catch(() => undefined);
  const animations = await page.locator(LAYER).evaluate((layer) => layer.getAnimations({ subtree: true }).map((animation) => ({
    end: Number(animation.effect!.getComputedTiming().endTime),
    self: (animation.effect as KeyframeEffect).target === layer,
  }))).catch(() => [] as { end: number; self: boolean }[]);
  expect(animations.every((item) => item.self && item.end <= 200)).toBe(true);
  await expect(page.locator(LAYER)).toHaveCount(0, { timeout: 3_000 });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  expect(await page.evaluate(() => document.getAnimations().filter((animation) => (animation as CSSAnimation).animationName === "home-arrive").length)).toBe(0);
  expect(errors).toEqual([]);
});

test("the entrance triggers no provider or data requests", async ({ page, baseURL }) => {
  const requests: string[] = [];
  page.on("request", (request) => { if (isProviderRequest(request, baseURL!)) requests.push(request.url()); });
  const assets: string[] = [];
  page.on("request", (request) => { if (["image", "media", "font"].includes(request.resourceType())) assets.push(request.url()); });
  await page.goto("/privacy", { waitUntil: "commit" });
  await expect(page.locator(LAYER)).toHaveCount(0, { timeout: 5_000 });
  expect(requests).toEqual([]);
  expect(assets.filter((url) => /entrance/i.test(url))).toEqual([]);
});

for (const width of [390, 430, 1024, 1440]) {
  test(`entrance composition fits a ${width}px viewport without scroll or overflow`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: width < 600 ? 844 : 900 });
    await page.goto("/privacy", { waitUntil: "commit" });
    await page.locator(LAYER).waitFor({ state: "attached" });
    await page.waitForLoadState("domcontentloaded");
    await holdAt(page, 620);
    const stage = await page.locator(`${LAYER} > div`).boundingBox();
    expect(stage!.x).toBeGreaterThanOrEqual(16);
    expect(stage!.x + stage!.width).toBeLessThanOrEqual(width - 16);
    expect(await page.evaluate(() => [scrollX, scrollY])).toEqual([0, 0]);
    await page.screenshot({ path: testInfo.outputPath(`entrance-${width}.png`) });
    await resume(page);
    await expect(page.locator(LAYER)).toHaveCount(0, { timeout: 5_000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
