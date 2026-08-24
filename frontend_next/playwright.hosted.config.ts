import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.HOSTED_FRONTEND_URL;
if (!baseURL) throw new Error("HOSTED_FRONTEND_URL is required for hosted Playwright only.");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: true,
  grep: /@hosted/,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL, trace: "retain-on-failure", screenshot: "only-on-failure", video: "retain-on-failure" },
  projects: [
    { name: "chromium-zh-TW", use: { ...devices["Desktop Chrome"], locale: "zh-TW" } },
    { name: "chromium-en", use: { ...devices["Desktop Chrome"], locale: "en-US" } },
    { name: "chromium-ja", use: { ...devices["Desktop Chrome"], locale: "ja-JP" } },
    { name: "chromium-ko", use: { ...devices["Desktop Chrome"], locale: "ko-KR" } },
    { name: "chrome", use: { ...devices["Desktop Chrome"], channel: "chrome" } },
    { name: "mobile-360", use: { ...devices["Galaxy S8"], viewport: { width: 360, height: 740 } } },
    { name: "mobile-390", use: { ...devices["iPhone 12"], viewport: { width: 390, height: 844 } } },
    { name: "mobile-430", use: { ...devices["iPhone 14 Pro Max"], viewport: { width: 430, height: 932 } } },
  ],
});
