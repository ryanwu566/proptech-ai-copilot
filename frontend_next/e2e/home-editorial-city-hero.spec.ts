import { expect, test } from "./fixtures";
import { isProviderRequest } from "./helpers/provider-request";

const viewports = [[1920, 1080], [1440, 900], [1366, 768], [1024, 768], [430, 932], [390, 844]] as const;
const imageSelector = '[data-testid="home-city-image"]';
const artSelector = '[data-testid="home-city-backdrop"]';

for (const [width, height] of viewports) {
  test(`editorial city preserves the Home form at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.goto("/");
    await expect(page.locator(".commercial-home [data-page-heading]")).toBeFocused();
    const image = page.locator(imageSelector);
    await expect(image).toHaveAttribute("alt", "");
    await expect(page.locator(artSelector)).toHaveAttribute("aria-hidden", "true");
    await expect(page.getByRole("img")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "開始物件評估", exact: true })).toBeVisible();
    const geometry = await page.evaluate(() => {
      const hero = document.querySelector(".commercial-home__start")!.getBoundingClientRect();
      const form = document.querySelector(".commercial-home__form")!.getBoundingClientRect();
      const input = document.querySelector("#commercial-address")!.getBoundingClientRect();
      return { hero: hero.width, form: form.width, input: input.width, overflow: document.documentElement.scrollWidth > innerWidth };
    });
    expect(geometry.form).toBeCloseTo(Math.min(780, geometry.hero), 0);
    expect(geometry.input).toBeGreaterThan(width >= 640 ? 600 : width - 40);
    expect(geometry.overflow).toBe(false);
    if (width >= 640) {
      await expect(image).toHaveAttribute("data-state", "ready");
      const src = await image.evaluate((img) => (img as HTMLImageElement).currentSrc);
      expect(src).toContain(width < 1200 ? "taipei-editorial-compact.webp" : "taipei-editorial-desktop.webp");
    } else {
      await expect(page.locator(artSelector)).toBeHidden();
    }
    await page.screenshot({ path: test.info().outputPath(`home-${width}x${height}.png`), animations: "disabled" });
  });
}

test("photograph reveals once in 720ms then stays still", async ({ page }) => {
  await page.goto("/");
  const image = page.locator(imageSelector);
  await expect(image).toHaveAttribute("data-state", "ready");
  const animation = await image.evaluate((img) => {
    const style = getComputedStyle(img);
    return { duration: style.animationDuration, iterations: style.animationIterationCount };
  });
  expect(animation).toEqual({ duration: "0.72s", iterations: "1" });
  await image.evaluate(async (img) => { await Promise.all(img.getAnimations().map((animation) => animation.finished)); });
  expect(await image.evaluate((img) => img.getAnimations().some((animation) => animation.playState === "running"))).toBe(false);
  await expect(page.locator(".commercial-home__form")).toHaveCSS("animation-name", "none");
});

test("reduced motion displays a static photograph immediately", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const image = page.locator(imageSelector);
  await expect(image).toHaveAttribute("data-state", "ready");
  await expect(image).toHaveCSS("animation-name", "none");
  await expect(image).toHaveCSS("opacity", "1");
  await expect(image).toHaveCSS("transform", "none");
});

test("late image does not delay typing or shift the form", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/images/home/taipei-editorial-*.webp", async (route) => { await gate; await route.continue(); });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const input = page.getByRole("textbox", { name: "物件地址", exact: true });
  await input.fill("臺北市大安區敦化南路二段");
  await expect(page.locator(imageSelector)).toHaveAttribute("data-state", "loading");
  await expect(page.locator(imageSelector)).toHaveCSS("animation-name", "none");
  await expect(page.locator(imageSelector)).toHaveCSS("opacity", "1");
  await expect(page.getByRole("button", { name: "開始物件評估", exact: true })).toBeEnabled();
  const before = await page.locator(".commercial-home__form").boundingBox();
  release();
  await expect(page.locator(imageSelector)).toHaveAttribute("data-state", "ready");
  expect(await page.locator(".commercial-home__form").boundingBox()).toEqual(before);
  await expect(input).toHaveValue("臺北市大安區敦化南路二段");
});

test("image failure preserves keyboard start and makes no provider calls", async ({ page }) => {
  await page.route("**/images/home/taipei-editorial-*.webp", (route) => route.abort("failed"));
  const calls: string[] = [];
  const baseURL = test.info().project.use.baseURL!;
  page.on("request", (request) => { if (isProviderRequest(request, baseURL)) calls.push(request.url()); });
  await page.goto("/");
  await expect(page.locator(imageSelector)).toHaveAttribute("data-state", "failed");
  await expect(page.locator(imageSelector)).toHaveCSS("opacity", "0");
  const input = page.getByRole("textbox", { name: "物件地址", exact: true });
  await input.focus();
  await input.fill("臺北市大安區敦化南路二段100號");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "開始物件評估", exact: true })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(input).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/cases\/[^/]+\/location$/);
  expect(calls).toEqual([]);
});

test("hero assets load only from the app origin without a runtime image service", async ({ page }) => {
  const urls: string[] = [];
  page.on("request", (request) => { if (request.resourceType() === "image") urls.push(request.url()); });
  await page.goto("/");
  await expect(page.locator(imageSelector)).toHaveAttribute("data-state", "ready");
  expect(urls.some((url) => url.includes("/images/home/taipei-editorial-desktop.webp"))).toBe(true);
  const origin = new URL(page.url()).origin;
  expect(urls.every((url) => new URL(url).origin === origin)).toBe(true);
  expect(urls.some((url) => url.includes("/_next/image"))).toBe(false);
  await expect(page.locator(imageSelector)).toHaveAttribute("fetchpriority", "low");
});
