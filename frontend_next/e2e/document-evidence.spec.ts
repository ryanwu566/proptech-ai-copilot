import { expect, test } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";
import { documentEvidenceCopy } from "../lib/workspace/document-evidence-copy";
import { isProviderRequest } from "./helpers/provider-request";
import { openWorkspaceTools } from "./helpers/commercial-navigation";

for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
  test(`${locale}: mobile keyboard provenance, stable references and no provider calls`, async ({ page, baseURL }) => {
    const calls: string[] = [];
    await page.route("**/*", async route => {
      if (isProviderRequest(route.request(), baseURL!)) { calls.push(new URL(route.request().url()).pathname); return route.abort(); }
      return route.continue();
    });
    await page.addInitScript(({ rows, locale }) => {
      if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
      localStorage.setItem("proptech.locale.v1", JSON.stringify({ version: 1, locale }));
    }, { rows: [e9Case(), e9Case("case-b")], locale });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/cases/case-a/evidence");
    const copy = documentEvidenceCopy[locale];
    await expect(page.getByRole("heading", { name: copy.title, exact: true })).toBeVisible();
    const before = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
    const reference = page.locator('[data-testid="document-evidence-page"] [data-citation-id] a').first();
    const href = await reference.getAttribute("href"); expect(href).toContain("/cases/case-a/evidence#ec1.");
    await reference.focus(); await page.keyboard.press("Enter");
    const selected = page.locator(`details[id="${href!.split("#")[1]}"]`);
    await expect(selected).toBeVisible();
    await expect(selected).toContainText(copy.provenance);
    await expect(selected).toContainText(copy.unverified);
    const affected = selected.getByRole("navigation", { name: copy.decision });
    await expect(affected.getByRole("link").first()).toHaveAttribute("href", "/cases/case-a/decision-room#saved-evidence");
    const summary = selected.locator("summary"); await summary.focus(); await page.keyboard.press("Space");
    await expect(selected).not.toHaveAttribute("open", "");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(before);
    await page.reload(); await expect(page.locator("details[open]").first()).toBeVisible();
    expect(await page.locator('[data-citation-id] a').first().getAttribute("href")).toBe(href);
    await selected.getByRole("navigation", { name: copy.decision }).getByRole("link").first().click();
    await expect(page.getByTestId("saved-evidence")).toBeVisible();
    await page.getByTestId("saved-evidence").getByRole("link", { name: copy.nav, exact: true }).click();
    await expect(page.getByRole("heading", { name: copy.title, exact: true })).toBeVisible();
    await page.goto(`/cases/case-b/evidence${href!.slice(href!.indexOf("#"))}`);
    await expect(page.getByRole("alert").filter({ hasText: copy.missing })).toBeVisible();
    expect(await page.locator('[data-citation-id]').first().getAttribute("data-citation-id")).toContain("case-b");
    await page.goto("/cases/case-a/report");
    await expect(page.getByTestId("report-citation-references")).toBeVisible();
    const reportCitation = page.locator('[data-testid="report-evidence"] [data-citation-id] a').first();
    await reportCitation.focus(); await page.keyboard.press("Enter");
    expect(await reportCitation.getAttribute("href")).toMatch(/^#report-ec1\./);
    await page.emulateMedia({ media: "print" });
    await expect(page.getByTestId("report-citation-references")).toBeVisible();
    expect(calls).toEqual([]);
  });
}

test("desktop evidence navigation and malformed case diagnostics", async ({ page }) => {
  await page.addInitScript(rows => { if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows)); }, [e9Case()]);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/cases/case-a/overview");
  await openWorkspaceTools(page);
  await page.getByRole("link", { name: "證據與引用", exact: true }).click();
  await expect(page.getByTestId("document-evidence-page")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.evaluate(() => localStorage.setItem("proptech.savedCases.v1", "{bad"));
  await page.reload(); await expect(page.getByRole("alert").filter({ hasText: "無法安全讀取保存證據" })).toBeVisible();
  await expect(page.getByTestId("evidence-detail")).toHaveCount(0);
});

test("missing sources stay unresolved, markup stays text and locale changes keep references without providers", async ({ page, baseURL }) => {
  const rows = [e9Case()];
  rows[0].data.marketInsight!.freshness_status = "stale";
  rows[0].title = '<img src=x onerror="window.wave5Executed=true">';
  const calls: string[] = [];
  await page.route("**/*", async route => {
    if (isProviderRequest(route.request(), baseURL!)) { calls.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  await page.addInitScript(rows => {
    if (!localStorage.getItem("proptech.savedCases.v1")) localStorage.setItem("proptech.savedCases.v1", JSON.stringify(rows));
  }, rows);
  await page.goto("/cases/case-a/evidence");
  await expect(page.getByTestId("evidence-detail").first()).toBeVisible();
  const stale = page.locator('details[id$=".market-total"]');
  await stale.locator("summary").click();
  await expect(stale).toContainText("1,850");
  await expect(stale.locator('[data-evidence-state="stale"]')).toBeVisible();
  await expect(page.locator('[data-citation-id$=".valuation-estimate"]')).toHaveCount(0);
  const reference = page.locator('[data-citation-id] a').first();
  const href = (await reference.getAttribute("href"))!;
  const before = await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"));
  for (const locale of ["en", "ja", "ko", "zh-TW"] as const) {
    await page.getByTestId("locale-switcher").selectOption(locale);
    await expect(page.getByRole("heading", { name: documentEvidenceCopy[locale].title, exact: true })).toBeVisible();
    await expect(reference).toHaveAttribute("href", href);
  }
  expect(await page.evaluate(() => localStorage.getItem("proptech.savedCases.v1"))).toBe(before);
  await page.goto("/cases/case-a/report");
  await expect(page.getByTestId("report-evidence")).toContainText(rows[0].title);
  await expect(page.getByTestId("report-evidence").locator("img")).toHaveCount(0);
  await expect(page.locator('[data-citation-id$=".valuation-estimate"]')).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as Record<string, unknown>).wave5Executed)).toBeUndefined();
  await page.evaluate(() => localStorage.setItem("proptech.savedCases.v1", "[]"));
  await page.goto(href);
  await expect(page.getByRole("status").filter({ hasText: documentEvidenceCopy["zh-TW"].empty })).toBeVisible();
  await expect(page.getByTestId("evidence-detail")).toHaveCount(0);
  expect(calls).toEqual([]);
});
