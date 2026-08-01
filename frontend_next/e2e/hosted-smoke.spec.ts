import { test, expect } from "@playwright/test";

test("hosted public release smoke remains bounded and usable", async ({ page }) => {
  const testName = test.info().title;
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const localhostRequests: string[] = [];
  const failedResponses: string[] = [];
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const location = message.location();
    const path = location.url ? new URL(location.url).pathname : "unknown";
    consoleErrors.push(`${message.text()} @ ${path}`);
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    const requestUrl = new URL(request.url());
    const pageUrl = new URL(page.url());
    const requestIsLocal = /^(localhost|127\.0\.0\.1)$/i.test(requestUrl.hostname);
    const pageIsRemote = pageUrl.protocol.startsWith("http") && !/^(localhost|127\.0\.0\.1)$/i.test(pageUrl.hostname);
    if (requestIsLocal && pageIsRemote) localhostRequests.push(`${request.method()} ${requestUrl.origin}${requestUrl.pathname}`);
  });
  page.on("response", (response) => {
    if (response.status() < 400) return;
    const url = new URL(response.url());
    failedResponses.push(`${testName} | ${response.request().method()} ${url.origin}${url.pathname} | ${response.status()}`);
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  await expect(page).not.toHaveTitle(/error/i);
  await page.goto("/privacy", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  await page.goto("/terms", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
  expect(failedResponses).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(localhostRequests).toEqual([]);
});
