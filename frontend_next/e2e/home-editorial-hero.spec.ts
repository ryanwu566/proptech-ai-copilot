import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

/** The Home city photograph (AmbientScene variant="home") is decorative only: the start UI stays usable and uncovered, and the photo settles. */
const START = { "zh-TW": "開始物件評估", en: "Start property review", ja: "物件の検討を開始", ko: "부동산 검토 시작" } as const;
const ADDRESS_LABEL = { "zh-TW": "物件地址", en: "Property address", ja: "物件住所", ko: "부동산 주소" } as const;
const HERO = /\/brand\/home\/home-hero-taipei-/;

const noOverflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
/** The control is the topmost element at its own centre, so the photograph never intercepts it. */
const onTop = (page: Page, name: string) => page.getByRole("button", { name, exact: true }).evaluate((element) => {
  const box = element.getBoundingClientRect();
  return element.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2));
});

async function openHome(page: Page) {
  await page.goto("/");
  await expect(page.locator(".commercial-home [data-page-heading]")).toBeFocused();
}

for (const [width, height, source] of [[1440, 900, "home-hero-taipei-desktop"], [390, 844, "home-hero-taipei-mobile"], [1920, 1080, "home-hero-taipei-desktop"], [1024, 768, "home-hero-taipei-desktop"], [430, 932, "home-hero-taipei-mobile"]] as const) {
  test(`${width}x${height} hero is decorative, local, settled and leaves the start usable`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await openHome(page);
    const hero = page.locator(".commercial-home-hero");
    await expect(hero).toHaveAttribute("aria-hidden", "true");
    await expect(hero.locator("img")).toHaveAttribute("alt", "");
    await expect(hero).toHaveAttribute("data-ambient-scene", "home");
    await expect(hero).toHaveAttribute("data-phase", /reveal|focus|lock|resolve/);
    await expect(hero).toHaveCSS("opacity", width < 768 ? "0.62" : "1");
    // Same-origin bundled derivative; no remote image dependency.
    const current = new URL(await hero.locator("img").evaluate((image: HTMLImageElement) => image.currentSrc));
    expect(current.origin).toBe(new URL(page.url()).origin);
    expect(current.pathname).toContain(source);
    expect(await noOverflow(page)).toBe(true);
    expect(await onTop(page, START["zh-TW"])).toBe(true);
    // Explicit mobile regression: absolute photograph overlaps the Hero heading;
    // it cannot become a band in normal flow below the address/CTA controls.
    await expect(hero).toHaveCSS("position", "absolute");
    const photoBox = await hero.boundingBox();
    const headingBox = await page.locator(".commercial-home [data-page-heading]").boundingBox();
    expect(photoBox!.y).toBeLessThan(headingBox!.y + headingBox!.height);
    expect(photoBox!.y + photoBox!.height).toBeGreaterThan(headingBox!.y);
    // Motion is one-shot: a single ~2% settle of the photograph that ends still. Nothing loops and nothing else moves.
    const running = await page.evaluate(() => document.getAnimations().filter((animation) => animation.playState === "running").map((animation) => {
      const timing = animation.effect!.getComputedTiming();
      return { photo: (animation.effect as KeyframeEffect).target instanceof HTMLImageElement, iterations: timing.iterations, duration: Number(timing.duration) };
    }));
    for (const animation of running) expect(animation).toEqual({ photo: true, iterations: 1, duration: 26000 });
    await hero.locator("img").evaluate((image) => image.getAnimations().forEach((animation) => animation.finish()));
    await expect(hero.locator("img")).toHaveCSS("transform", /^(none|matrix\(1, 0, 0, 1, 0, 0\))$/);
    const folder = path.resolve(process.cwd(), "../.local/photo-ambient/screenshots");
    await mkdir(folder, { recursive: true });
    await page.screenshot({ path: path.join(folder, `home-${width}x${height}.png`) });
  });
}

test("Home start works before and without the photograph", async ({ page }) => {
  await page.route(HERO, (route) => route.abort());
  await openHome(page);
  const address = page.getByRole("textbox", { name: ADDRESS_LABEL["zh-TW"], exact: true });
  await address.fill("臺北市信義區市府路1號");
  await address.press("Tab");
  await expect(page.getByRole("button", { name: START["zh-TW"], exact: true })).toBeFocused();
  await expect(page.locator(".commercial-home-hero")).not.toHaveAttribute("data-phase", /.*/);
  await expect(page.getByRole("button", { name: "開始導覽", exact: true })).toBeVisible();
  await page.getByRole("button", { name: START["zh-TW"], exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/[A-Za-z0-9_-]+\/location$/);
});

test("reduced motion shows the settled photograph without a reveal", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route(HERO, async (route) => { await new Promise((resolve) => setTimeout(resolve, 800)); await route.continue(); });
  await openHome(page);
  const hero = page.locator(".commercial-home-hero");
  await expect(hero).toHaveAttribute("data-phase", "resolve");
  await expect(hero).toHaveCSS("opacity", "1");
  await expect(hero.locator("img")).toHaveCSS("transform", "none");
  expect(await hero.evaluate((element) => element.getAnimations({ subtree: true }).length)).toBe(0);
});

for (const locale of ["en", "ja", "ko"] as const) {
  test(`${locale} Home keeps the start above the photograph`, async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await openHome(page);
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.getByRole("textbox", { name: ADDRESS_LABEL[locale], exact: true })).toBeVisible();
    expect(await onTop(page, START[locale])).toBe(true);
    expect(await noOverflow(page)).toBe(true);
  });
}
