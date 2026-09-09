import { defineConfig, devices } from "@playwright/test";

const productionTarget = process.env.SPATIAL_PREVIEW_E2E_TARGET === "production";
const externalServer = process.env.SPATIAL_PREVIEW_EXTERNAL_SERVER === "1";
const port = productionTarget ? 3103 : 3102;
const nextMode = productionTarget ? "start" : "dev";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "spatial-map-preview.spec.ts",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 30_000,
  expect: { timeout: 7_000 },
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    ...devices["Desktop Chrome"],
  },
  projects: [
    { name: productionTarget ? "production-exclusion-chromium" : "development-preview-chromium" },
  ],
  webServer: externalServer ? undefined : {
    command: `node node_modules/next/dist/bin/next ${nextMode} --hostname 127.0.0.1 --port ${port}`,
    url: productionTarget
      ? `http://127.0.0.1:${port}/`
      : `http://127.0.0.1:${port}/dev/spatial-map-preview`,
    timeout: 120_000,
    reuseExistingServer: false,
    stdout: "pipe",
    stderr: "pipe",
  },
});
