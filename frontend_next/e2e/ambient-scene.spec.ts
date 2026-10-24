import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const KEY = "proptech.savedCases.v1";
const ROUTES = {
  market: "/cases/case-a/market",
  location: "/cases/case-a/location",
  risk: "/cases/case-a/risk",
  overview: "/cases/case-a/overview",
} as const;
// Decision surfaces stay plain paper.
const PLAIN = ["/cases/case-a/finance", "/cases/case-a/decision-room", "/cases/case-a/report", "/compare?cases=case-a,case-b"] as const;
const VIEWPORTS = [[1440, 900], [390, 844], [1920, 1080], [1024, 768], [430, 932]] as const;
const SCENE = "[data-ambient-scene]";
const screenshots = path.resolve(process.cwd(), "../.local/photo-ambient/screenshots");

async function seed(page: Page) {
  // Existing foreground Leaflet maps are unrelated to the ambient layer. Keep their
  // basemap requests inside the test, as the focused Risk suite already does.
  await page.route("https://*.tile.openstreetmap.org/**", (route) => route.fulfill({ status: 204, body: "" }));
  await page.addInitScript(({ rows, key }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(rows)); }, { rows: [e9Case(), e9Case("case-b")], key: KEY });
}
async function open(page: Page, route: string) {
  await page.goto(route);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
}
const layoutNeutral = (page: Page) => page.evaluate((selector) => {
  const scene = document.querySelector<HTMLElement>(selector)!;
  const heading = document.querySelector("h1")!;
  const measure = () => [document.documentElement.scrollHeight, document.documentElement.scrollWidth, ...Object.values(heading.getBoundingClientRect().toJSON())].join("|");
  const shown = measure();
  scene.style.display = "none";
  const hidden = measure();
  scene.style.display = "";
  return shown === hidden;
}, SCENE);
const sceneNeverOnTop = (page: Page) => page.locator(SCENE).evaluate((scene) => {
  const box = scene.getBoundingClientRect();
  const hits: string[] = [];
  for (let x = 0.05; x < 1; x += 0.15) for (let y = 0.05; y < 1; y += 0.15) {
    const point = [box.left + box.width * x, Math.min(window.innerHeight - 1, box.top + box.height * y)] as const;
    const top = document.elementFromPoint(point[0], point[1]);
    if (top && scene.contains(top)) hits.push(point.join(","));
  }
  return hits;
});

for (const [variant, route] of Object.entries(ROUTES)) {
  test(`${variant} photograph is responsive, local and behind usable content`, async ({ page }) => {
    await seed(page);
    const imageRequests: string[] = [];
    page.on("request", (request) => { if (request.resourceType() === "image") imageRequests.push(request.url()); });
    await page.setViewportSize({ width: 1440, height: 900 });
    await open(page, route);
    const scene = page.locator(SCENE);
    await expect(scene).toHaveCount(1);
    await expect(scene).toHaveAttribute("data-ambient-scene", variant);
    await expect(scene).toHaveAttribute("aria-hidden", "true");
    await expect(scene).toHaveCSS("pointer-events", "none");
    await expect(scene).toHaveCSS("z-index", "-1");
    await expect(scene).toHaveAttribute("data-phase", "resolve", { timeout: 7000 });
    await expect(scene.locator("img")).toHaveAttribute("alt", "");
    expect(await scene.locator("svg, canvas, iframe, video, a, text").count()).toBe(0);
    const family = variant;
    await mkdir(screenshots, { recursive: true });
    for (const [width, height] of VIEWPORTS) {
      await page.setViewportSize({ width, height });
      const label = `${variant} ${width}x${height}`;
      const kind = width < 768 ? "mobile" : "desktop";
      await expect.poll(() => scene.locator("img").evaluate((image: HTMLImageElement, expected) => image.complete && image.naturalWidth > 0 && image.currentSrc.includes(expected), `ambient-${family}-${kind}.avif`)).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), label).toBe(true);
      expect(await sceneNeverOnTop(page), label).toEqual([]);
      expect(await layoutNeutral(page), label).toBe(true);
      await scene.locator("img").evaluate((image) => image.getAnimations().forEach((animation) => animation.finish()));
      await page.screenshot({ path: path.join(screenshots, `${variant}-${width}x${height}.png`) });
    }
    const origin = new URL(page.url()).origin;
    expect(imageRequests.filter((url) => new URL(url).origin !== origin && !new URL(url).hostname.endsWith(".tile.openstreetmap.org")), "no external decorative image request").toEqual([]);
    const sources = await scene.locator("img, source").evaluateAll((elements) => elements.map((element) => element.getAttribute("src") ?? element.getAttribute("srcset") ?? ""));
    expect(sources.every((source) => source.startsWith("/brand/ambient/"))).toBe(true);
    // Real navigation remains clickable through the decorative photograph.
    await page.getByRole("link", { name: /PropTech/i }).first().click();
    await expect(page).toHaveURL("/");
  });
}

test("photography settles once, then stays still with no provider or animation requests", async ({ page }) => {
  await seed(page);
  await open(page, ROUTES.location);
  const scene = page.locator(SCENE);
  await expect(scene).toHaveAttribute("data-phase", "resolve", { timeout: 7000 });
  await page.waitForLoadState("networkidle");
  const animations = await scene.locator("img").evaluate((image) => image.getAnimations().map((animation) => ({ duration: animation.effect!.getComputedTiming().duration, iterations: animation.effect!.getComputedTiming().iterations })));
  expect(animations).toEqual([{ duration: 32000, iterations: 1 }]);
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await page.clock.install();
  await page.clock.runFor(40_000);
  await scene.locator("img").evaluate((image) => image.getAnimations().forEach((animation) => animation.finish()));
  await expect(scene).not.toHaveAttribute("data-wake", /.*/);
  expect(requests).toEqual([]);
  await expect(scene.locator("img")).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, 0)");
});

test("every scene resolves statically under reduced motion and stays hidden in print", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await seed(page);
  for (const route of Object.values(ROUTES)) {
    await open(page, route);
    const scene = page.locator(SCENE);
    await expect(scene).toHaveAttribute("data-resolve", "");
    await expect(scene.locator("img")).toHaveCSS("transform", "none");
    expect(await scene.evaluate((element) => element.getAnimations({ subtree: true }).length)).toBe(0);
    await page.emulateMedia({ media: "print", reducedMotion: "reduce" });
    await expect(scene).toBeHidden();
    await page.emulateMedia({ media: "screen", reducedMotion: "reduce" });
  }
});

test("hidden tabs and offscreen scenes freeze the photograph and resume without replay", async ({ page }) => {
  await seed(page);
  await open(page, ROUTES.risk);
  const scene = page.locator(SCENE);
  await expect(scene).toHaveAttribute("data-phase", "resolve", { timeout: 7000 });
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(scene).toHaveAttribute("data-paused", "");
  await expect(scene.locator("img")).toHaveCSS("animation-play-state", "paused");
  // A paused CSS property can precede the animation timeline's committed pause by one frame.
  const time = await scene.locator("img").evaluate(async (image) => {
    const animation = image.getAnimations()[0];
    await animation.ready;
    return Number(animation.currentTime);
  });
  await page.waitForTimeout(250);
  expect(await scene.locator("img").evaluate((image) => Number(image.getAnimations()[0].currentTime))).toBeCloseTo(time, 0);
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(scene).not.toHaveAttribute("data-paused", /.*/);
  await expect(scene.locator("img")).toHaveCSS("animation-play-state", "running");
  await expect.poll(() => scene.locator("img").evaluate((image) => Number(image.getAnimations()[0].currentTime))).toBeGreaterThan(time);
  await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
  await expect(scene).toHaveAttribute("data-paused", "");
  const offscreenTime = await scene.locator("img").evaluate(async (image) => {
    const animation = image.getAnimations()[0];
    await animation.ready;
    return Number(animation.currentTime);
  });
  expect(offscreenTime).toBeGreaterThanOrEqual(time);
  await page.waitForTimeout(100);
  expect(await scene.locator("img").evaluate((image) => Number(image.getAnimations()[0].currentTime))).toBeCloseTo(offscreenTime, 0);
  await page.evaluate(() => scrollTo(0, 0));
  await expect(scene).not.toHaveAttribute("data-paused", /.*/);
  await expect.poll(() => scene.locator("img").evaluate((image) => Number(image.getAnimations()[0].currentTime))).toBeGreaterThan(offscreenTime);
  await expect(scene).not.toHaveAttribute("data-wake", /.*/);
});

test("delayed or failed photographs never move content or prevent use", async ({ page }) => {
  await seed(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/brand/ambient/**", async (route) => { await gate; await route.continue(); });
  await page.goto(ROUTES.market, { waitUntil: "domcontentloaded" });
  const heading = page.getByRole("heading", { level: 1 }).first();
  await expect(heading).toBeVisible();
  const before = await heading.boundingBox();
  await expect(page.locator(SCENE)).not.toHaveAttribute("data-phase", /.*/);
  release();
  await expect(page.locator(SCENE)).toHaveAttribute("data-phase", "resolve", { timeout: 7000 });
  expect(await heading.boundingBox()).toEqual(before);
  await page.unroute("**/brand/ambient/**");
  await page.route("**/brand/ambient/**", (route) => route.abort());
  await open(page, ROUTES.location);
  await expect(page.locator(SCENE)).not.toHaveAttribute("data-phase", /.*/);
  expect(await layoutNeutral(page)).toBe(true);
  await page.getByRole("link", { name: /PropTech/i }).first().click();
  await expect(page).toHaveURL("/");
});

test("routes without an ambient scene stay plain", async ({ page }) => {
  await seed(page);
  for (const route of ["/cases", "/cases/case-a/scenarios", ...PLAIN]) {
    await page.goto(route);
    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.locator(SCENE)).toHaveCount(0);
  }
});

test("returning through a plain route cross-fades an already revealed scene", async ({ page }) => {
  await seed(page);
  await open(page, ROUTES.overview);
  await expect(page.locator(SCENE)).not.toHaveAttribute("data-continuity", /.*/);
  await page.locator("[data-case-rail] a[href$='/finance']").click();
  await expect(page).toHaveURL(/\/finance$/);
  await expect(page.locator(SCENE)).toHaveCount(0);
  await page.locator("[data-case-rail] a[href$='/overview']").click();
  await expect(page).toHaveURL(/\/overview$/);
  await expect(page.locator(SCENE)).toHaveAttribute("data-continuity", "true");
  await expect(page.locator(SCENE).locator("img")).toHaveCSS("animation-name", "none");
});
