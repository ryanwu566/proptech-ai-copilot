import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

/** Ambient scenes are decorative: behind the UI, inert, layout-neutral, local, calm and pausable. */
const KEY = "proptech.savedCases.v1";
const ROUTES = {
  overview: "/cases/case-a/overview",
  market: "/cases/case-a/market",
  location: "/cases/case-a/location",
  risk: "/cases/case-a/risk",
  finance: "/cases/case-a/finance",
  decision: "/cases/case-a/decision-room",
  compare: "/compare?cases=case-a,case-b",
  report: "/cases/case-a/report",
} as const;
const VIEWPORTS = [[1920, 1080], [1440, 900], [1366, 768], [1024, 768], [430, 932], [390, 844]] as const;
const SCENE = "[data-ambient-scene]";

async function seed(page: Page) {
  await page.addInitScript(({ rows, key }) => { if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(rows)); }, { rows: [e9Case(), e9Case("case-b")], key: KEY });
}
async function open(page: Page, path: string) {
  await page.goto(path);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
}

/** Samples a grid across the scene's box: the topmost element is never the scene, so it cannot take a click. */
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
/** Layout with the scene removed from rendering matches layout with it. */
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

for (const [variant, path] of Object.entries(ROUTES)) {
  test(`${variant} scene sits behind the page at every validation viewport`, async ({ page }) => {
    await seed(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await open(page, path);
    const scene = page.locator(SCENE);
    await expect(scene).toHaveCount(1);
    await expect(scene).toHaveAttribute("data-ambient-scene", variant);
    await expect(scene).toHaveAttribute("aria-hidden", "true");
    await expect(scene).toHaveCSS("pointer-events", "none");
    await expect(scene).toHaveCSS("z-index", "-1");
    await expect(scene).toHaveAttribute("data-phase", "resolve", { timeout: 6000 });
    // Geometry only: nothing in a scene can load a remote resource.
    expect(await scene.evaluate((element) => element.querySelectorAll("img, image, use, iframe, video, source, foreignObject, a, text").length)).toBe(0);
    for (const [width, height] of VIEWPORTS) {
      await page.setViewportSize({ width, height });
      const label = `${variant} ${width}x${height}`;
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), label).toBe(true);
      expect(await sceneNeverOnTop(page), label).toEqual([]);
      expect(await layoutNeutral(page), label).toBe(true);
      const artboard = width < 768 ? "mobile" : "desktop";
      expect(await scene.evaluate((element, which) => [...element.querySelectorAll("svg")].filter((svg) => getComputedStyle(svg).display !== "none").map((svg) => svg.getAttribute("class") ?? "").every((name) => name.includes(which)), artboard), label).toBe(true);
    }
  });
}

test("scenes make no network requests while they reveal and wake", async ({ page }) => {
  test.setTimeout(60_000);
  await seed(page);
  for (const path of [ROUTES.location, ROUTES.market, ROUTES.compare]) {
    await open(page, path);
    await expect(page.locator(SCENE)).toHaveAttribute("data-phase", "resolve", { timeout: 6000 });
    await page.waitForLoadState("networkidle");
    const requests: string[] = [];
    const record = (request: { url(): string }) => requests.push(request.url());
    page.on("request", record);
    // Location wakes 8–12s after RESOLVE; the others are only watched while resting.
    if (path === ROUTES.location) await expect(page.locator(SCENE)).toHaveAttribute("data-wake", /\d/, { timeout: 14000 });
    else await page.waitForTimeout(3000);
    page.off("request", record);
    expect(requests, path).toEqual([]);
  }
});

test("reduced motion shows the resolved scene at once with nothing moving", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await seed(page);
  await open(page, ROUTES.risk);
  const scene = page.locator(SCENE);
  await expect(scene).toHaveAttribute("data-resolve", "", { timeout: 1500 });
  await expect(scene).toHaveCSS("opacity", /^0\.\d+$/);
  expect(await scene.evaluate((element) => element.getAnimations({ subtree: true }).filter((animation) => animation.playState === "running").length)).toBe(0);
  // The amber unresolved zone is in its final, visible state rather than lost with the motion.
  expect(await scene.evaluate((element) => [...element.querySelectorAll("svg path")].some((path) => getComputedStyle(path).stroke === "rgb(183, 121, 31)" && Number(getComputedStyle(path).opacity) > 0.9))).toBe(true);
});

test("a hidden tab pauses the scene and skips wakes until it is visible again", async ({ page }) => {
  await page.clock.install();
  await seed(page);
  await open(page, ROUTES.location);
  const scene = page.locator(SCENE);
  const wakeWithin = async (ms: number) => {
    for (let elapsed = 0; elapsed < ms; elapsed += 250) {
      await page.clock.runFor(250);
      if (await scene.getAttribute("data-wake") !== null) return true;
    }
    return false;
  };
  await page.clock.runFor(4000);
  await expect(scene).toHaveAttribute("data-phase", "resolve");
  expect(await wakeWithin(13000)).toBe(true);
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(scene).toHaveAttribute("data-paused", "");
  await expect(scene).not.toHaveAttribute("data-wake", /.*/);
  expect(await wakeWithin(30000)).toBe(false);
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(scene).not.toHaveAttribute("data-paused", /.*/);
  expect(await wakeWithin(13000)).toBe(true);
});

test("routes without a scene stay plain and print never shows one", async ({ page }) => {
  await seed(page);
  for (const path of ["/cases", "/cases/case-a/scenarios"]) {
    await page.goto(path);
    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.locator(SCENE)).toHaveCount(0);
  }
  await open(page, ROUTES.report);
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(SCENE)).toBeHidden();
});
