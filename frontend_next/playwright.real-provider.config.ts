import { defineConfig, devices } from "@playwright/test";

if (!process.env.REAL_PROVIDER_API_BASE_URL) {
  throw new Error("REAL_PROVIDER_API_BASE_URL is required for real-provider Playwright only.");
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: true,
  grep: /@real-provider/,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:${process.env.E2E_PORT ?? "3100"}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "real-provider-chromium", use: { ...devices["Desktop Chrome"] } }],
});
