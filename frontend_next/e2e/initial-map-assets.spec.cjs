const { test, expect } = require("@playwright/test");
const { execFile } = require("node:child_process");
const { readdirSync, readFileSync } = require("node:fs");
const path = require("node:path");
const { allowRequest, assertRouteView } = require("../../scripts/measure_route_assets.cjs");
const { e9Case } = require("../lib/workspace/e9-test-fixtures.ts");

const frontendRoot = path.resolve(__dirname, "..");
const rows = [e9Case("case-a"), e9Case("case-b")];
const mapMarkers = ["Map container is already initialized", "risk-property-marker", "server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"];
let mapFiles;

test.beforeAll(() => {
  const staticRoot = path.join(frontendRoot, ".next/static");
  const scripts = readdirSync(staticRoot, { recursive: true }).filter((file) => file.endsWith(".js"))
    .map((file) => ({ file: `static/${file.replaceAll("\\", "/")}`, source: readFileSync(path.join(staticRoot, file), "utf8") }));
  // Resolve actual emitted chunks, without depending on build-specific hashes.
  for (const marker of mapMarkers) expect(scripts.some(({ source }) => source.includes(marker)), `Missing map bundle marker: ${marker}`).toBe(true);
  mapFiles = new Set(scripts.filter(({ source }) => mapMarkers.some((marker) => source.includes(marker))).map(({ file }) => file));
});

test("cold route measurement excludes unrevealed map chunks from both initial asset graphs", async () => {
  test.setTimeout(240_000);
  const output = await new Promise((resolve, reject) => {
    const child = execFile(process.execPath, [path.resolve(frontendRoot, "../scripts/measure_route_assets.cjs")], { windowsHide: true }, (error, stdout, stderr) => {
      if (error) reject(new Error(`Route measurement failed: ${stderr}`, { cause: error }));
      else resolve(stdout);
    });
    child.stdin.end(JSON.stringify({ frontend_root: frontendRoot, routes: ["/cases/[caseId]/location", "/cases/[caseId]/risk"] }));
  });
  const evidence = JSON.parse(output);
  for (const section of ["location", "risk"]) {
    const entry = evidence.routes[`/cases/[caseId]/${section}`];
    expect(entry.status).toBe("measured");
    expect(entry.navigation_paths).toEqual([`/cases/case-a/${section}`]);
    expect(entry.samples_per_viewport).toBe(2);
    expect(entry.viewports).toEqual([390, 1440]);
    expect(entry.client_files.length).toBeGreaterThan(0);
    expect(entry.client_files.filter((file) => mapFiles.has(file))).toEqual([]);
  }
});

for (const section of ["location", "risk"]) {
  test(`${section} initial validation hydrates saved context without clicks, map chunks, or provider requests`, async ({ page, baseURL }) => {
    const providerRequests = [];
    const staticFiles = new Set();
    await page.addInitScript((saved) => {
      localStorage.setItem("proptech.savedCases.v1", JSON.stringify(saved));
      localStorage.setItem("proptech_onboarding_seen", "true");
      window.mapRevealClicks = 0;
      document.addEventListener("click", (event) => {
        if (event.target.closest('[data-testid="show-location-map"], [data-testid="show-risk-map"]')) window.mapRevealClicks++;
      }, true);
    }, rows);
    await page.route("**/*", (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin !== baseURL || /^\/api(?:\/|$)/.test(url.pathname)) providerRequests.push(request.url());
      return allowRequest(request, baseURL) ? route.continue() : route.abort();
    });
    page.on("response", (response) => {
      const url = new URL(response.url());
      if (url.origin === baseURL && url.pathname.startsWith("/_next/static/")) staticFiles.add(decodeURIComponent(url.pathname).replace("/_next/", ""));
    });
    await page.goto(`/cases/case-a/${section}`, { waitUntil: "networkidle" });
    await assertRouteView(page, `/cases/[caseId]/${section}`, 1280, rows);
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId(`show-${section}-map`)).toBeVisible();
    await expect(page.locator(".leaflet-container")).toHaveCount(0);
    expect(await page.evaluate(() => window.mapRevealClicks)).toBe(0);
    expect(providerRequests).toEqual([]);
    expect([...staticFiles].filter((file) => mapFiles.has(file))).toEqual([]);
  });

  test(`${section} loads its Leaflet map after an explicit reveal click`, async ({ page }) => {
    await page.addInitScript((saved) => {
      localStorage.setItem("proptech.savedCases.v1", JSON.stringify(saved));
      localStorage.setItem("proptech_onboarding_seen", "true");
    }, rows);
    await page.route("https://*.tile.openstreetmap.org/**", (route) => route.fulfill({ status: 204 }));
    await page.goto(`/cases/case-a/${section}`);
    await expect(page.getByTestId(`show-${section}-map`)).toBeVisible();
    await expect(page.locator(".leaflet-container")).toHaveCount(0);
    await page.getByTestId(`show-${section}-map`).click();
    await expect(page.locator(".leaflet-container")).toBeVisible();
    if (section === "risk") await expect(page.getByTestId("risk-property-marker")).toBeVisible();
  });
}
