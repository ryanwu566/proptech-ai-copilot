import { test, expect } from "@playwright/test";

test("hosted public release smoke remains bounded and usable", async ({ page }) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const localhostRequests: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => { if (/https?:\/\/(localhost|127\.0\.0\.1)/i.test(request.url())) localhostRequests.push(request.url()); });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  await expect(page).not.toHaveTitle(/error/i);
  await page.goto("/privacy", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  await page.goto("/terms", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(localhostRequests).toEqual([]);
});
