import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.HOSTED_FRONTEND_URL;
if (!baseURL) throw new Error("HOSTED_FRONTEND_URL is required for RIS hosted acceptance.");

export default defineConfig({
  testDir: "./e2e",
  testMatch: /ris-hosted-acceptance\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  forbidOnly: false,
  retries: 0,
  timeout: 60000,
  reporter: [["list"]],
  use: {
    baseURL,
    locale: "zh-TW",
    trace: "off",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [{ name: "chromium-zh-TW", use: { ...devices["Desktop Chrome"], locale: "zh-TW" } }],
});
