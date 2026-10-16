import { test, expect } from "@playwright/test";
import { e9Case } from "../lib/workspace/e9-test-fixtures";

// These local-only views can also be checked against an unconfigured production build.
for (const width of [390, 430, 1024, 1440]) test(`saved-case navigation wraps unbroken local titles at ${width}`, async ({ page }, testInfo) => {
  await page.setViewportSize({ width, height: 900 });
  const rows = [{ ...e9Case(), title: "CaseTitle".repeat(12) }, e9Case("case-b")];
  await page.addInitScript((cases) => localStorage.setItem("proptech.savedCases.v1", JSON.stringify(cases)), rows);
  await page.goto("/cases?next=scenarios");
  await expect(page.getByRole("article")).toHaveCount(2);
  await expect(page.locator("main a[href='/cases/case-a/scenarios']")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (width === 390) await page.screenshot({ path: testInfo.outputPath("saved-cases-long-title.png") });
  await page.goto("/compare?cases=case-a,case-b");
  await expect(page.getByTestId("compare-report-handoff")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (width === 390) await page.screenshot({ path: testInfo.outputPath("compare-long-title.png") });
});
