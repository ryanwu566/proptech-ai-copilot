import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "property-compare-preview.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  outputDir: "test-results/compare-preview",
  use: {
    baseURL: "http://127.0.0.1:3104",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "compare-chromium", use: { ...devices["Desktop Chrome"] } }],
});
