import { expect, test } from "@playwright/test";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { overviewViewCopy } from "../lib/workspace/overview-presentation";
import { isProviderRequest } from "./helpers/provider-request";

const locales = ["zh-TW", "en", "ja", "ko"] as const;
const output = path.resolve(process.cwd(), "../.local/apple-polish/screenshots");
const routes = ["/", "/cases/case-a/overview", "/cases/case-a/location", "/cases/case-a/risk", "/cases/case-a/finance", "/cases/case-a/decision-room", "/cases/case-a/report", "/compare?cases=case-a,case-b"];

for (const locale of locales) {
  test(`${locale}: Location controls fit the system-font fallback at every width`, async ({ page, baseURL }) => {
    await page.addInitScript(({ saved, locale }) => {
      localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
      localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
      localStorage.setItem("proptech_onboarding_seen", "true");
      localStorage.setItem("proptech_onboarding_version", "2");
    }, { saved: e9Case(), locale });
    const providers: string[] = [];
    await page.route("**/*", route => {
      if (isProviderRequest(route.request(), baseURL!)) { providers.push(route.request().url()); return route.abort(); }
      return route.continue();
    });
    await page.goto("/cases/case-a/location");
    // Exercise the supported fallback used when the preferred OS fonts are absent.
    await page.evaluate(() => document.documentElement.style.setProperty("--font-sans", "system-ui"));
    for (const width of [390, 430, 720, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => innerWidth)).toBe(width);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${locale}, ${width}px`).toBe(true);
      const destination = page.getByTestId("commute-route-card").getByRole("textbox");
      expect((await destination.boundingBox())!.width, "the address input must remain usable").toBeGreaterThanOrEqual(120);
      const transit = page.getByTestId("commute-transit-context-state").locator("..").getByRole("button");
      await expect(transit).toBeEnabled();
      expect(await transit.evaluate(button => {
        const box = button.getBoundingClientRect(), card = button.parentElement!.parentElement!.getBoundingClientRect();
        return box.left >= card.left && box.right <= card.right;
      })).toBe(true);
    }
    expect(providers).toEqual([]);
  });
}

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
        await expect(view.getByRole("heading", { level: 1 })).toHaveCSS("font-weight", "600");
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
        const zoom = width === 720 ? await page.context().newCDPSession(page) : null;
        if (zoom) {
          await zoom.send("Emulation.setDeviceMetricsOverride", { width: 720, height: 450, deviceScaleFactor: 2, mobile: false, screenWidth: 1440, screenHeight: 900 });
          await expect.poll(() => page.evaluate(() => `${innerWidth}:${devicePixelRatio}`)).toBe("720:2");
        }
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
        if (locale === "zh-TW" || route.endsWith("/overview")) {
          const target = path.join(output, `${locale}-${route.split("/").pop()?.split("?")[0] || "home"}-${width === 720 ? "zoom200" : width}.png`);
          if (zoom) {
            await page.evaluate(async () => { await document.fonts.ready; });
            const capture = await zoom.send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false });
            const shot = Buffer.from(capture.data, "base64");
            await writeFile(target, shot);
            expect([shot.readUInt32BE(16), shot.readUInt32BE(20)]).toEqual([1440, 900]);
          } else await page.screenshot({ path: target });
        }
        await zoom?.detach();
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

for (const locale of locales) {
  test(`${locale}: complete Demo Cases retain one frame and three physical Report core pages`, async ({ page, baseURL }, testInfo) => {
    test.setTimeout(120_000);
    await page.addInitScript((locale) => {
      localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
      localStorage.setItem("proptech_onboarding_seen", "true");
      localStorage.setItem("proptech_onboarding_version", "2");
    }, locale);
    const providers: string[] = [];
    await page.route("**/*", (route) => {
      if (isProviderRequest(route.request(), baseURL!)) { providers.push(route.request().url()); return route.abort(); }
      return route.continue();
    });
    await page.goto("/");
    await page.getByTestId("complete-example-start").click();
    await expect(page).toHaveURL(/\/cases\/proptech-demo-a\/overview$/);
    const frame = await page.locator("[data-case-frame]").elementHandle();
    const notice = await page.getByTestId("demo-case-notice").elementHandle();
    await page.locator("[data-case-rail] a[href$='/report']").click();
    await expect(page.getByTestId("report-core-page-3")).toBeVisible();
    expect(await frame!.evaluate(node => node.isConnected)).toBe(true);
    expect(await notice!.evaluate(node => node.isConnected)).toBe(true);
    await expect(page.getByTestId("demo-case-notice")).toHaveCount(1);
    await expect(page.getByTestId("demo-case-notice")).toBeVisible();
    const stored = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
    await page.emulateMedia({ media: "print" });
    await expect(page.getByTestId("demo-case-notice")).toBeHidden();
    const footer = (await page.getByTestId("core-next-steps").locator("p").last().innerText()).replace(/\s+/g, "");
    const pdfPages = (pdf: Buffer) => (pdf.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) ?? []).length;
    const pdfPath = testInfo.outputPath(`demo-${locale}-a4.pdf`);
    const total = pdfPages(await page.pdf({ path: pdfPath, preferCSSPageSize: true, printBackground: true }));
    const auditPath = `${pdfPath}.audit.json`;
    const audit = spawnSync("python", ["-X", "utf8", "-c", "import pymupdf as fitz,json,sys; d=fitz.open(sys.argv[1]); json.dump([{'text':p.get_text(),'clipped':any(b[0]<-1 or b[2]>p.rect.width+1 or b[1]<-1 or b[3]>p.rect.height+1 for b in p.get_text('blocks'))} for p in d],open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)", pdfPath, auditPath], { encoding: "utf8", windowsHide: true });
    expect(audit.status, audit.stderr).toBe(0);
    const sheets = JSON.parse(await readFile(auditPath, "utf8")) as { text: string; clipped: boolean }[];
    expect(sheets.every(sheet => !sheet.clipped), "no PDF text extends beyond a physical sheet").toBe(true);
    expect(sheets[2].text.replace(/\s+/g, ""), "the complete checklist footer stays on page three").toContain(footer);
    await testInfo.attach("demo-pdf-text-audit", { path: auditPath, contentType: "application/json" });
    const cumulative: number[] = [];
    for (const hidden of [["report-core-page-2", "report-core-page-3"], ["report-core-page-3"], []]) {
      await page.evaluate((hidden) => {
        document.getElementById("demo-print-measure")?.remove();
        const style = document.createElement("style"); style.id = "demo-print-measure";
        style.textContent = [...hidden, "report-appendix", "report-citation-references"].map(id => `[data-testid="${id}"] { display: none !important; }`).join("\n");
        document.head.append(style);
      }, hidden);
      cumulative.push(pdfPages(await page.pdf({ preferCSSPageSize: true, printBackground: true })));
    }
    expect(cumulative).toEqual([1, 2, 3]);
    expect(total).toBeGreaterThan(3);
    expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(stored);
    expect(providers).toEqual([]);
    await testInfo.attach("demo-a4-pages", { body: JSON.stringify({ locale, cumulative, total, appendixStartsOn: cumulative[2] + 1 }), contentType: "application/json" });
  });
}
