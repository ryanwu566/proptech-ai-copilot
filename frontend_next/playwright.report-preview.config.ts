import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.REPORT_PREVIEW_PORT ?? "3103");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "decision-report-preview.spec.ts",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: join(tmpdir(), "proptech-track-c-report-preview"),
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "chromium-report", use: { ...devices["Desktop Chrome"] } }],
});
