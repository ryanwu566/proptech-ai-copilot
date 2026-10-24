import { expect, test, type Page } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { isProviderRequest } from "./helpers/provider-request";

test.beforeEach(() => { test.setTimeout(90_000); });

// Unlocated, so destination maps never load tiles; the shell contract is about navigation alone.
async function seed(page: Page, locale = "zh-TW") {
  const saved = e9Case();
  saved.data = { inputs: saved.data.inputs };
  await page.addInitScript(({ saved, locale }) => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
    localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, { saved, locale });
}

async function trackProviders(page: Page, baseURL: string) {
  const calls: string[] = [];
  await page.route("**/*", (route) => {
    if (isProviderRequest(route.request(), baseURL)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  return calls;
}

const rail = (page: Page) => page.locator("[data-case-rail] .workspace-navigation");

test("rail navigation stays in one document and one case frame, across snapshot and standalone routes, with zero provider calls", async ({ page, baseURL }) => {
  await seed(page);
  const calls = await trackProviders(page, baseURL!);
  await page.goto("/cases/case-a/overview");
  await expect(page.locator("[data-case-frame]")).toHaveCount(1);
  await expect(page.getByTestId("case-pulse")).toBeVisible();
  await page.evaluate(() => {
    (window as Window & { shellMarker?: string }).shellMarker = "same-document";
    (window as Window & { caseNodes?: Element[] }).caseNodes = ["[data-case-frame]", "[data-case-rail]", ".workspace-property-header", "[data-testid='case-pulse']"].map((selector) => document.querySelector(selector)!);
  });
  const address = (await page.getByRole("banner", { name: "目前物件" }).locator("strong").first().innerText()).trim();
  for (const [label, path] of [["案件報告", "report"], ["價格與市場", "market"], ["風險與環境", "risk"], ["購屋決策室", "decision-room"], ["物件總覽", "overview"]] as const) {
    // Hover first: with prefetch off, hovering a destination must not load or request anything.
    await rail(page).getByRole("link", { name: label, exact: true }).hover();
    await rail(page).getByRole("link", { name: label, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/cases/case-a/${path}$`));
    await expect(rail(page).locator("[aria-current='page']")).toHaveText(label);
    await expect(page.locator("[data-case-frame]")).toHaveCount(1);
    await expect(page.locator(".workspace-navigation")).toHaveCount(1);
    // The same case identity is in the same place on every route.
    await expect(page.locator(".workspace-property-header strong").first()).toHaveText(address);
    expect(await page.evaluate(() => (window as Window & { shellMarker?: string }).shellMarker)).toBe("same-document");
    expect(await page.evaluate(() => (window as Window & { caseNodes?: Element[] }).caseNodes?.map((node) => node.isConnected)), "case frame, rail, case bar and pulse retain their DOM nodes").toEqual([true, true, true, true]);
  }
  expect(calls).toEqual([]);
});

test("route content reveals only on in-app navigation and not at all under reduced motion", async ({ page }) => {
  await seed(page);
  await page.goto("/cases/case-a/overview");
  const content = page.locator("[data-case-route-content]");
  // First load renders still.
  expect(await content.evaluate((node) => getComputedStyle(node).animationName)).toBe("none");
  await rail(page).getByRole("link", { name: "價格與市場", exact: true }).click();
  await expect(page).toHaveURL(/\/market$/);
  expect(await content.evaluate((node) => getComputedStyle(node).animationName)).not.toBe("none");

  await page.emulateMedia({ reducedMotion: "reduce" });
  await rail(page).getByRole("link", { name: "風險與環境", exact: true }).click();
  await expect(page).toHaveURL(/\/risk$/);
  expect(await content.evaluate((node) => getComputedStyle(node).animationName)).toBe("none");
});

for (const width of [390, 430]) test(`at ${width}px the rail is one strip with the current section in view and no page overflow`, async ({ page }) => {
  await seed(page);
  await page.setViewportSize({ width, height: 900 });
  for (const path of ["overview", "finance", "decision-room", "report"]) {
    await page.goto(`/cases/case-a/${path}`);
    const current = rail(page).locator("[aria-current='page']");
    await expect(current).toBeVisible();
    await expect(current).toBeInViewport({ ratio: 0.9 });
    const box = (await current.boundingBox())!;
    expect(box.height).toBeGreaterThanOrEqual(44);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});

for (const width of [390, 430]) test(`English frame at ${width}px contains its scroll strips`, async ({ page }) => {
  await seed(page, "en");
  await page.setViewportSize({ width, height: 900 });
  for (const route of ["/", "/cases/case-a/overview", "/cases/case-a/decision-room"]) {
    await page.goto(route);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator("main").first()).toBeVisible();
    const layout = await page.evaluate(() => ({
      width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
      regions: [".commercial-global-header", "[data-case-rail]", "[data-ambient-scene]", ".workspace-property-header"].map((selector) => {
        const node = document.querySelector<HTMLElement>(selector);
        if (!node) return { selector };
        const before = node.style.display;
        node.style.display = "none";
        const without = document.documentElement.scrollWidth;
        node.style.display = before;
        return { selector, without, width: node.clientWidth, scrollWidth: node.scrollWidth };
      }),
      overflow: [...document.querySelectorAll("body *")].filter((node) => {
        const rect = node.getBoundingClientRect();
        return rect.width && rect.right > innerWidth + 1 && !node.closest("[data-case-rail], .commercial-global-header__inner");
      }).slice(0, 10).map((node) => ({ tag: node.tagName, class: node.className, right: node.getBoundingClientRect().right, text: node.textContent?.slice(0, 70) })),
    }));
    expect(layout.scrollWidth, `${route}: ${JSON.stringify(layout)}`).toBeLessThanOrEqual(width);
  }
});

test("resizing to a phone keeps the selected section in view", async ({ page }) => {
  await seed(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/cases/case-a/finance");
  await expect(rail(page).locator("[aria-current='page']")).toBeVisible();
  for (const width of [390, 430, 720]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(rail(page).locator("[aria-current='page']")).toBeInViewport({ ratio: 0.9 });
  }
});
