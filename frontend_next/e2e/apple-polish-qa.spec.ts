import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { overviewViewCopy } from "../lib/workspace/overview-presentation";
import { isProviderRequest } from "./helpers/provider-request";

const locales = ["zh-TW", "en", "ja", "ko"] as const;
const output = path.resolve(process.cwd(), "../.local/apple-polish/screenshots");
const routes = ["/", "/cases/case-a/overview", "/cases/case-a/location", "/cases/case-a/risk", "/cases/case-a/finance", "/cases/case-a/decision-room", "/cases/case-a/report", "/compare?cases=case-a,case-b"];

for (const locale of locales) {
  test(`${locale}: overview presentation and responsive route QA`, async ({ page, baseURL }) => {
    test.setTimeout(180_000);
    const rows = [e9Case(), e9Case("case-b")];
    await page.addInitScript(({ rows, locale }) => {
      localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
      localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
      localStorage.setItem("proptech_onboarding_seen", "true");
      localStorage.setItem("proptech_onboarding_version", "2");
    }, { rows, locale });
    const providers: string[] = [];
    await page.route("**/*", (route) => {
      if (/\.tile\.openstreetmap\.org\//.test(route.request().url())) return route.fulfill({ status: 204, body: "" });
      if (isProviderRequest(route.request(), baseURL!)) { providers.push(route.request().url()); return route.abort(); }
      return route.continue();
    });
    await mkdir(output, { recursive: true });
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.locator("main").first()).toBeVisible();
      if (route.endsWith("/overview")) {
        const copy = overviewViewCopy[locale];
        const view = page.getByTestId("commercial-overview-workspace");
        await expect(view.getByRole("heading", { level: 1 })).toHaveText(copy.title);
        await expect(view.getByRole("heading", { name: copy.decisionTitle, exact: true })).toBeVisible();
        await expect(view.getByTestId("overview-finance-summary")).toContainText(copy.unassessed);
        if (locale !== "zh-TW") {
          await expect(view.getByTestId("overview-market-summary")).toContainText("NT$24,800,000");
          await expect(view.getByTestId("overview-finance-summary")).not.toContainText("尚未評估");
        }
      }
      for (const width of [390, 430, 1024, 1440, 720]) {
        // A 1440px screen at 200% browser zoom has a 720 CSS-pixel layout viewport.
        await page.setViewportSize({ width, height: width === 720 ? 450 : 900 });
        await page.evaluate(() => scrollTo(0, 0));
        if (route.startsWith("/cases/")) await expect(page.locator("[data-case-rail] [aria-current='page']")).toBeInViewport({ ratio: 0.9 });
        const overflowing = await page.evaluate(() => {
          if (document.documentElement.scrollWidth <= innerWidth) return [];
          return [...document.querySelectorAll("body *")].filter((node) => {
            const rect = node.getBoundingClientRect();
            return rect.width && rect.right > innerWidth + 1 && !node.closest("[data-case-rail], .commercial-global-header__inner, .ds-table-wrap");
          }).slice(0, 12).map((node) => ({ tag: node.tagName, class: node.className, text: node.textContent?.slice(0, 80), right: node.getBoundingClientRect().right }));
        });
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${locale} ${route} ${width}: ${JSON.stringify(overflowing)}`).toBe(true);
        if (locale === "zh-TW" || route.endsWith("/overview")) await page.screenshot({ path: path.join(output, `${locale}-${route.split("/").pop()?.split("?")[0] || "home"}-${width === 720 ? "zoom200" : width}.png`) });
      }
    }
    expect(providers).toEqual([]);
  });
}

test("reduced motion and transparency keep case chrome and content still and opaque", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript((saved) => {
    localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
    localStorage.setItem("proptech_onboarding_seen", "true");
  }, e9Case());
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }, { name: "prefers-reduced-transparency", value: "reduce" }] });
  await page.goto("/cases/case-a/overview");
  await expect(page.getByTestId("commercial-overview-workspace")).toBeVisible();
  await page.locator("[data-case-rail] a[href$='/risk']").click();
  await expect(page).toHaveURL(/\/risk$/);
  const chrome = page.locator(".workspace-property-header");
  await expect(chrome).toHaveCSS("backdrop-filter", "none");
  await expect(chrome).toHaveCSS("background-color", "rgb(246, 247, 249)");
  expect(await page.locator("[data-case-content]").evaluate((node) => node.getAnimations({ subtree: true }).filter((animation) => animation.playState === "running").length)).toBe(0);
});
