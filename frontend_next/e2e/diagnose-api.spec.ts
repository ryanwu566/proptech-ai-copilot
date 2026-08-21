import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3000", viewport: { width: 1440, height: 900 } });

test("Diagnose V01 API path", async ({ page }) => {
  test.setTimeout(30000);
  const requests: string[] = [];
  const failures: string[] = [];
  const consoleErrors: string[] = [];

  page.on("request", (req) => {
    if (req.url().includes("location") || req.url().includes("8000")) {
      requests.push(`${req.method()} ${req.url()}`);
    }
  });
  page.on("requestfailed", (req) => failures.push(`FAILED: ${req.method()} ${req.url()} reason=${req.failure()?.errorText}`));
  page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  page.on("pageerror", (err) => consoleErrors.push(`PAGE_ERROR: ${err.message}`));

  await page.addInitScript(() => {
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  });

  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /五個步驟/ })).toBeVisible({ timeout: 10000 });

  // Navigate to location step
  await page.getByLabel(/位置與資料證據/).first().click();
  await page.waitForTimeout(1000);

  // Fill and analyze
  const input = page.locator("#location-insight-calculator input").first();
  await expect(input).toBeVisible({ timeout: 5000 });
  await input.fill("臺北市大安區忠孝東路四段45號");
  
  const btn = page.locator("#location-insight-calculator button", { hasText: /開始位置分析/ });
  const btnDisabled = await btn.isDisabled();
  console.log("BUTTON DISABLED:", btnDisabled);
  console.log("BUTTON TEXT:", await btn.textContent());
  
  await btn.click();
  console.log("CLICKED");

  // Wait for any network activity
  await page.waitForTimeout(8000);

  console.log("\n=== REQUESTS ===");
  requests.forEach((r) => console.log(r));
  console.log("\n=== FAILURES ===");
  failures.forEach((f) => console.log(f));
  console.log("\n=== CONSOLE ERRORS ===");
  consoleErrors.forEach((e) => console.log(e));
  console.log("\n=== REQUESTS COUNT:", requests.length, "FAILURES COUNT:", failures.length);

  // This test is diagnostic — always report what we found
  expect(requests.length + failures.length + consoleErrors.length).toBeGreaterThan(0);
});
