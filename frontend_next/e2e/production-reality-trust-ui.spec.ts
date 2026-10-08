import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("http://e2e.test/**", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "deterministic unavailable provider" }),
  }));
  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });
});

test("shell uses neutral per-query data language instead of static service health", async ({ page }) => {
  await page.goto("/");
  await page.locator(".commercial-methods > summary").click();
  const footer = page.locator(".commercial-methods__panel");
  await expect(footer).toContainText("各來源限制");
  await expect(page.locator(".commercial-home__trust")).toContainText("未知不代表安全");
  await expect(footer).not.toContainText("服務狀態");
  await expect(footer).not.toContainText(/^可用$/);
});

test("neutral shell remains readable at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.locator(".commercial-methods > summary").click();
  const sidebar = page.locator(".commercial-methods__panel");
  await expect(sidebar).toBeVisible();
  await expect(sidebar).toContainText("各來源限制");
  expect(await sidebar.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
});
