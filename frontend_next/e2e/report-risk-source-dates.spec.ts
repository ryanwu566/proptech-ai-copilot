import { expect, test } from "@playwright/test";
import { reportRiskCase } from "./fixtures/report-risk-case";
import { isProviderRequest } from "./helpers/provider-request";
import { documentEvidenceCopy } from "../lib/workspace/document-evidence-copy";

const unknown = { "zh-TW": "未知／未保存", en: "Unknown / not preserved", ja: "不明・未保存", ko: "알 수 없음 / 미저장" };
const formatted = { "zh-TW": "2026年8月20日", en: "Aug 20, 2026", ja: "2026/08/20", ko: "2026. 8. 20." };
const pages = (pdf: Buffer) => (pdf.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) ?? []).length;

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
  for (const variant of ["unavailable", "vintage", "iso", "mixed"] as const) {
    test(`saved Risk Report renders ${variant} source dates (${locale})`, async ({ page, baseURL }, testInfo) => {
      test.setTimeout(90_000);
      const values = { unavailable: ["未提供"], vintage: ["113年度（官方公開 MVT）"], iso: ["2026-08-20"], mixed: ["未提供", "113年度（官方公開 MVT）", "2026-08-20"] }[variant];
      const saved = reportRiskCase(values);
      const errors: string[] = []; const providers: string[] = [];
      page.on("pageerror", error => errors.push(`${error.name}: ${error.message}`));
      page.on("console", message => { if (message.type() === "error" && /Invalid time value|RangeError/.test(message.text())) errors.push(message.text()); });
      await page.route("**/*", async route => {
        if (isProviderRequest(route.request(), baseURL!)) { providers.push(route.request().url()); return route.abort(); }
        await route.continue();
      });
      await page.addInitScript(({ saved, locale }) => {
        localStorage.setItem("proptech.savedCases.v1", JSON.stringify([saved]));
        localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
      }, { saved, locale });
      await page.goto(`/cases/${saved.id}/report`);
      // Surfaces the original RangeError directly, rather than only a missing-element timeout.
      try { await expect(async () => {
        expect(errors, "Report must not throw for source vintages").toEqual([]);
        await expect(page.getByTestId("report-core-page-3")).toBeVisible();
      }).toPass({ timeout: 10_000 }); } finally {
        await testInfo.attach("render-errors", { body: JSON.stringify(errors), contentType: "application/json" });
      }
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      const references = page.getByTestId("report-citation-references");
      const risk = references.locator('li[id$="risk-flood"]');
      const updated = risk.getByText(documentEvidenceCopy[locale].updated, { exact: true }).locator("xpath=following-sibling::dd[1]");
      await expect(updated).toHaveText(variant === "iso" ? formatted[locale] : variant === "vintage" ? "113年度（官方公開 MVT）" : unknown[locale]);
      await expect(risk.locator('[data-evidence-state="unknown"]')).toHaveCount(1);
      if (variant === "mixed") {
        await expect(references.locator('li[id$="risk-landslide"]')).toContainText("113年度（官方公開 MVT）");
        await expect(page.getByTestId("report-appendix")).toContainText("2026-08-20");
        await expect(page.getByTestId("report-appendix")).toContainText("113年度（官方公開 MVT）");
        // Exercise the real print button and synchronous beforeprint guard.
        await page.evaluate(() => { window.print = () => { window.dispatchEvent(new Event("beforeprint")); }; });
        await page.getByTestId("report-controls").getByRole("button", { name: /PDF/ }).click();
        await expect(page.locator('main[data-print-blocked="false"]')).toHaveCount(1);
        await page.emulateMedia({ media: "print" });
        await page.pdf({ path: testInfo.outputPath(`risk-${locale}.pdf`), preferCSSPageSize: true, printBackground: true });
        const cumulative: number[] = [];
        for (const hidden of [
          ['[data-testid="report-core-page-2"]', '[data-testid="report-core-page-3"]'],
          ['[data-testid="report-core-page-3"]'],
          [],
        ]) {
          await page.evaluate(hidden => {
            document.getElementById("risk-print-measure")?.remove();
            const style = document.createElement("style"); style.id = "risk-print-measure";
            style.textContent = [...hidden, '[data-testid="report-appendix"]', '[data-testid="report-citation-references"]'].map(s => `${s} { display: none !important; }`).join("\n"); document.head.append(style);
          }, hidden);
          cumulative.push(pages(await page.pdf({ preferCSSPageSize: true, printBackground: true })));
        }
        expect(cumulative, "three core pages; appendix starts on page four").toEqual([1, 2, 3]);
        expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(JSON.stringify([saved]));
        await page.goto(`/cases/${saved.id}/evidence`);
        await expect(page.locator("html")).toHaveAttribute("lang", locale);
        await expect(page.locator('[data-citation-id]').first()).toBeVisible();
        const detail = page.locator('details[id$="risk-landslide"]');
        await detail.locator("summary").click();
        await expect(detail).toContainText("113年度（官方公開 MVT）");
      }
      expect(errors, "no Report/Evidence or print exception").toEqual([]);
      expect(providers, "saved Report/Evidence and printing make zero provider requests").toEqual([]);
      await testInfo.attach("provider-requests", { body: JSON.stringify(providers), contentType: "application/json" });
    });
  }
}
