// Cold-context production asset measurement. Only the owned loopback server's
// documents and static assets can reach the network; providers/APIs/prefetch cannot.
const { spawn } = require("node:child_process");
const { readFile } = require("node:fs/promises");
const { createRequire } = require("node:module");
const net = require("node:net");
const path = require("node:path");

function allowRequest(request, origin) {
  const url = new URL(request.url());
  if (url.origin !== origin || request.method() !== "GET") return false;
  if (/^\/api(?:\/|$)/.test(url.pathname)) return false;
  const headers = request.headers();
  if (headers["next-router-prefetch"] || headers.purpose === "prefetch" || headers["sec-purpose"]?.includes("prefetch")) return false;
  return url.pathname.startsWith("/_next/static/") || request.isNavigationRequest();
}

async function assertRouteView(page, routeName, width, rows) {
  const expectedPath = routeName === "/cases/[caseId]" ? "/cases/case-a/overview" : routeName.replace("[caseId]", "case-a");
  if (routeName === "/cases/[caseId]") {
    await page.waitForURL((url) => url.pathname === expectedPath, { timeout: 10_000 });
  }
  const actualPath = new URL(page.url()).pathname;
  if (actualPath !== expectedPath) {
    const error = new Error(`Unexpected route destination: ${routeName}`);
    error.observedRoute = actualPath.replace("/case-a", "/[caseId]");
    throw error;
  }
  const selectors = {
    ...Object.fromEntries(["/admin", ...["users", "usage", "providers", "limits", "operations", "audit"].map((section) => `/admin/${section}`)].map((route) => [route, '[data-testid="admin-shell"]'])),
    "/": "#main-content",
    "/login": "#consumer-email",
    "/signup": "#consumer-email",
    "/account": '#main-content section[aria-label]',
    "/preferences": "#main-content form",
    "/places": '[data-testid="place-card"]',
    "/compare": `[data-testid="compare-${width === 390 ? "mobile" : "desktop"}"]`,
    "/cases/[caseId]": '[data-testid="commercial-overview-workspace"]',
    "/cases/[caseId]/overview": '[data-testid="commercial-overview-workspace"]',
    "/cases/[caseId]/market": '[data-testid="market-price-workspace"]',
    "/cases/[caseId]/location": '[data-testid="show-location-map"]',
    "/cases/[caseId]/risk": '[data-testid="show-risk-map"]',
    "/cases/[caseId]/finance": '[data-testid="finance-price-basis"]',
    "/cases/[caseId]/report": '[data-testid="report-evidence"]',
    "/cases/[caseId]/scenarios": '[data-testid="scenario-comparison"]',
    "/cases/[caseId]/decision-room": '[data-testid="new-note-form"]',
    "/cases/[caseId]/commute-planner": '[data-testid="commute-destination"]',
  };
  const view = page.locator(selectors[routeName]);
  await view.waitFor({ state: "attached", timeout: 10_000 });
  if (routeName.startsWith("/cases/") && !routeName.endsWith("/report")) {
    const header = routeName.endsWith("/decision-room") ? '[data-testid="room-case-context"]' : routeName.endsWith("/commute-planner") ? '#main-content > header' : ".workspace-property-header";
    if (!(await page.locator(header).textContent()).includes(rows[0].title)) {
      throw new Error(`Saved fixture not hydrated: ${routeName}`);
    }
  }
}

async function selectPort() {
  const probe = net.createServer();
  await new Promise((resolve, reject) => { probe.once("error", reject); probe.listen(0, "127.0.0.1", resolve); });
  const port = probe.address().port;
  await new Promise((resolve) => probe.close(resolve));
  return port;
}

async function stop(server) {
  if (server.exitCode !== null || server.signalCode !== null) return;
  const exited = new Promise((resolve) => server.once("exit", resolve));
  server.kill();
  const timer = setTimeout(() => server.kill("SIGKILL"), 5000);
  try { await exited; } finally { clearTimeout(timer); }
}

function failureDiagnostic(error, state) {
  const stages = ["input", "module_resolution", "fixture_loading", "build_id", "server_start", "server_readiness", "chromium_launch", "chromium_connect", "browser_context", "route_navigation", "route_view_validation", "route_networkidle", "route_assets", "process_cleanup"];
  const routes = ["/admin", ...["users", "usage", "providers", "limits", "operations", "audit"].map((section) => `/admin/${section}`), "/", "/login", "/signup", "/account", "/preferences", "/places", "/compare", "/cases/[caseId]", ...["overview", "market", "location", "risk", "finance", "report", "scenarios", "decision-room", "commute-planner"].map((section) => `/cases/[caseId]/${section}`)];
  const exceptionType = ["Error", "TypeError", "SyntaxError", "RangeError", "TimeoutError"].includes(error.name) ? error.name : "Error";
  const safeCodes = ["MODULE_NOT_FOUND", "ERR_REQUIRE_ESM", "ERR_UNKNOWN_FILE_EXTENSION", "ENOENT", "EACCES", "EADDRINUSE"];
  const reasons = new Map([
    ["Owned production server failed", "server_failed"],
    ["Owned production server readiness timeout", "server_readiness_timeout"],
    ["Production route measurement deadline exceeded", "timeout"],
    [`Unexpected route destination: ${state.route}`, "unexpected_destination"],
    [`Saved fixture not hydrated: ${state.route}`, "fixture_not_hydrated"],
    [`Incomplete route load: ${state.route}`, "incomplete_route_load"],
    [`Unstable route assets: ${state.route}`, "unstable_route_assets"],
  ]);
  return {
    failure_stage: stages.includes(state.stage) ? state.stage : "input", exception_type: exceptionType,
    current_route: routes.includes(state.route) ? state.route : null,
    ...(routes.includes(error.observedRoute) ? { observed_route: error.observedRoute } : {}),
    error_code: exceptionType === "TimeoutError" ? "timeout" : safeCodes.includes(error.code) ? error.code : reasons.get(error.message) || null,
  };
}

function setStage(state, stage) {
  state.stage = stage;
  const safe = failureDiagnostic({}, state);
  process.stderr.write(`ROUTE_ASSET_DIAGNOSTIC=${JSON.stringify({ failure_stage: safe.failure_stage, current_route: safe.current_route })}\n`);
}

async function withCleanup(action, cleanup, state) {
  let result;
  let failure;
  try { result = await action(); }
  catch (error) {
    failure = error;
    error.routeAssetDiagnostic ||= failureDiagnostic(error, state);
  }
  setStage(state, "process_cleanup");
  try { await cleanup(); }
  catch (error) {
    if (!failure) {
      failure = error;
      error.routeAssetDiagnostic ||= failureDiagnostic(error, state);
    }
  }
  if (failure) throw failure;
  return result;
}

async function measure(input) {
  const state = { stage: "input", route: null };
  try { return await measureRoutes(JSON.parse(input), state); }
  catch (error) {
    process.stderr.write(`ROUTE_ASSET_DIAGNOSTIC=${JSON.stringify(error.routeAssetDiagnostic || failureDiagnostic(error, state))}\n`);
    throw error;
  }
}

async function measureRoutes({ frontend_root: frontendRoot, routes }, state) {
  setStage(state, "module_resolution");
  const localRequire = createRequire(path.join(frontendRoot, "package.json"));
  const { chromium } = localRequire("playwright");
  // Populate saved route views without revealing maps: only cold initial assets count.
  setStage(state, "fixture_loading");
  const { e9Case } = localRequire("./lib/workspace/e9-test-fixtures.ts");
  const rows = [e9Case("case-a"), e9Case("case-b")];
  setStage(state, "build_id");
  const buildId = (await readFile(path.join(frontendRoot, ".next/BUILD_ID"), "utf8")).trim();
  const port = await selectPort();
  const origin = `http://127.0.0.1:${port}`;
  const environment = Object.fromEntries(["PATH", "SystemRoot", "SYSTEMROOT", "HOME", "USERPROFILE", "LOCALAPPDATA", "TEMP", "TMP"]
    .filter((key) => process.env[key]).map((key) => [key, process.env[key]]));
  setStage(state, "server_start");
  const server = spawn(process.execPath, [path.join(frontendRoot, "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", String(port)], {
    cwd: frontendRoot, env: { ...environment, NODE_ENV: "production", NEXT_TELEMETRY_DISABLED: "1" },
    stdio: ["ignore", "pipe", "pipe"], windowsHide: true,
  });
  let failure;
  let ready = false;
  let outputTail = "";
  server.once("error", (error) => { failure = error; });
  server.stdout.on("data", (chunk) => {
    outputTail = (outputTail + chunk.toString()).slice(-128);
    if (outputTail.includes("Ready in")) ready = true;
  });
  server.stderr.on("data", () => {});
  let browser;
  let browserServer;
  const measurementTimer = setTimeout(() => {
    failure = new Error("Production route measurement deadline exceeded");
    if (browserServer) void browserServer.close().catch(() => {});
    else server.kill();
  }, 210_000);
  return await withCleanup(async () => {
    setStage(state, "server_readiness");
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      if (failure || server.exitCode !== null) throw new Error("Owned production server failed");
      if (ready) {
        try { if ((await fetch(`${origin}/_next/static/${encodeURIComponent(buildId)}/_buildManifest.js`)).ok) break; } catch {}
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    if (!ready || Date.now() >= deadline) throw new Error("Owned production server readiness timeout");
    setStage(state, "chromium_launch");
    browserServer = await chromium.launchServer({ headless: true });
    process.stderr.write(`ROUTE_ASSET_BROWSER_PID=${browserServer.process().pid}\n`);
    setStage(state, "chromium_connect");
    browser = await chromium.connect(browserServer.wsEndpoint());
    const results = {};
    for (const routeName of routes) {
      state.route = routeName;
      if (failure) throw failure;
      const navigationPath = routeName.replace("[caseId]", "case-a") + (routeName === "/compare" ? "?cases=case-a,case-b" : "");
      const union = new Set();
      const navigationPaths = new Set();
      for (const width of [390, 1440]) {
        let previous;
        for (let sample = 0; sample < 2; sample++) {
          setStage(state, "browser_context");
          const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: "block", locale: "en-US", reducedMotion: "reduce" });
          await withCleanup(async () => {
            await context.addInitScript((saved) => {
              localStorage.setItem("proptech.savedCases.v1", JSON.stringify(saved));
              localStorage.setItem("proptech.my-places.v1", JSON.stringify({ version: 1, places: [{
                id: "budget-place", label: "Synthetic workplace", category: "work", address: "Synthetic destination",
                transportMode: "transit", weeklyTrips: 5, priority: "important",
                createdAt: "2026-10-13T00:00:00.000Z", updatedAt: "2026-10-13T00:00:00.000Z",
              }] }));
              localStorage.setItem("proptech_onboarding_seen", "true");
              localStorage.setItem("proptech_onboarding_version", "2");
              localStorage.setItem("proptech_onboarding_state", JSON.stringify({ version: "3", status: "completed" }));
            }, rows);
            await context.route("**/*", (route) => {
              const request = route.request();
              return allowRequest(request, origin) ? route.continue() : route.abort();
            });
            const page = await context.newPage();
            const assets = new Set();
            const assetFailures = [];
            page.on("pageerror", () => assetFailures.push("client_runtime_error"));
            page.on("response", (response) => {
              const url = new URL(response.url());
              if (url.origin === origin && url.pathname.startsWith("/_next/static/")) {
                if (!response.ok()) assetFailures.push(url.pathname);
                else assets.add(decodeURIComponent(url.pathname).replace("/_next/", ""));
              }
            });
            page.on("requestfailed", (request) => {
              if (new URL(request.url()).pathname.startsWith("/_next/static/")) assetFailures.push(request.url());
            });
            setStage(state, "route_navigation");
            const response = await page.goto(origin + navigationPath, { waitUntil: "networkidle", timeout: 30_000 });
            setStage(state, "route_view_validation");
            await assertRouteView(page, routeName, width, rows);
            setStage(state, "route_networkidle");
            await page.waitForTimeout(500);
            await page.waitForLoadState("networkidle");
            setStage(state, "route_assets");
            if (!response?.ok() || !assets.size || assetFailures.length) throw new Error(`Incomplete route load: ${routeName}`);
            navigationPaths.add(new URL(page.url()).pathname);
            const sorted = [...assets].sort();
            if (previous && JSON.stringify(previous) !== JSON.stringify(sorted)) throw new Error(`Unstable route assets: ${routeName}`);
            previous = sorted;
            sorted.forEach((asset) => union.add(asset));
          }, () => context.close(), state);
        }
      }
      results[routeName] = { status: "measured", client_files: [...union].sort(), samples_per_viewport: 2, viewports: [390, 1440], navigation_paths: [...navigationPaths].sort() };
    }
    return { routes: results, network_policy: "owned-loopback-documents-and-static-only", fixture: "synthetic-e9-saved-cases", metric: "unique-uncompressed-static-file-bytes" };
  }, async () => {
    clearTimeout(measurementTimer);
    try {
      try { if (browser) await browser.close(); } finally { if (browserServer) await browserServer.close(); }
    } finally { await stop(server); }
  }, state);
}

async function main() {
  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  process.stdout.write(JSON.stringify(await measure(input)) + "\n");
}

if (require.main === module) main().catch(() => { process.exitCode = 1; });
module.exports = { allowRequest, assertRouteView, failureDiagnostic, withCleanup };
