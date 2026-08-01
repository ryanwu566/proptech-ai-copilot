/* Playwright-based Lighthouse-equivalent local production measurements. */
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(require.resolve("@playwright/test", { paths: [path.join(process.cwd(), "node_modules")] }));

const port = Number(process.env.PERF_PORT || 3100);
const profile = process.env.PERF_PROFILE || "desktop";
const samples = Math.max(1, Math.min(Number(process.env.PERF_SAMPLES || 3), 5));
const viewport = profile === "mobile" ? { width: 390, height: 844 } : { width: 1280, height: 800 };
const routes = [
  ["homepage", "/", "/"],
  ["competition_demo", "/", "homepage_surface"],
  ["taxoracle", "/", "homepage_surface"],
  ["public_evidence", "/", "homepage_surface"],
];

function mockResponse(url) {
  const pathname = new URL(url).pathname;
  if (["/map", "/location", "/market-insights", "/valuation", "/tax", "/loan", "/holding-cost", "/taxoracle", "/roads", "/pilot", "/performance"].some((prefix) => pathname.startsWith(prefix))) {
    return { status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable", data_status: "unavailable", coverage_status: "unknown", regions: [], cities: [], districts: [], roads: [] }) };
  }
  return null;
}

async function measure(page, name, route) {
  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("requestfailed", (request) => failedRequests.push(new URL(request.url()).pathname));
  await page.route("**/*", async (routeHandler) => {
    const mock = mockResponse(routeHandler.request().url());
    if (mock) return routeHandler.fulfill(mock);
    return routeHandler.continue();
  });
  await page.addInitScript(() => {
    window.__webVitals = { lcp: null, cls: 0, inp: null, tbt: 0 };
    try { new PerformanceObserver((list) => { const entries = list.getEntries(); const last = entries[entries.length - 1]; if (last) window.__webVitals.lcp = last.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); } catch {}
    try { new PerformanceObserver((list) => { for (const entry of list.getEntries()) if (!entry.hadRecentInput) window.__webVitals.cls += entry.value; }).observe({ type: "layout-shift", buffered: true }); } catch {}
    try { new PerformanceObserver((list) => { for (const entry of list.getEntries()) window.__webVitals.inp = Math.max(window.__webVitals.inp || 0, entry.duration); }).observe({ type: "event", buffered: true, durationThreshold: 16 }); } catch {}
    try { new PerformanceObserver((list) => { for (const entry of list.getEntries()) window.__webVitals.tbt += Math.max(0, entry.duration - 50); }).observe({ type: "longtask", buffered: true }); } catch {}
  });
  const started = Date.now();
  const response = await page.goto(`http://127.0.0.1:${port}${route}`, { waitUntil: "domcontentloaded", timeout: 10000 }).catch(() => null);
  await page.waitForTimeout(500);
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType("navigation")[0];
    const paint = performance.getEntriesByType("paint");
    return {
      transferred_bytes: performance.getEntriesByType("resource").reduce((sum, item) => sum + Number(item.transferSize || 0), 0),
      request_count: performance.getEntriesByType("resource").length,
      ttfb_ms: navigation ? navigation.responseStart : null,
      dom_content_loaded_ms: navigation ? navigation.domContentLoadedEventEnd : null,
      load_ms: navigation ? navigation.loadEventEnd : null,
      first_contentful_paint_ms: paint.find((item) => item.name === "first-contentful-paint")?.startTime ?? null,
      lcp_ms: window.__webVitals?.lcp ?? null,
      cls: window.__webVitals?.cls ?? null,
      inp_proxy_ms: window.__webVitals?.inp ?? null,
      tbt_proxy_ms: window.__webVitals?.tbt ?? null,
      accessibility_score: (() => {
        const unlabeledImages = [...document.querySelectorAll("img")].filter((item) => !item.hasAttribute("alt")).length;
        const unlabeledButtons = [...document.querySelectorAll("button")].filter((item) => !item.getAttribute("aria-label") && !item.textContent?.trim() && !item.getAttribute("title")).length;
        const unlabeledInputs = [...document.querySelectorAll("input,select,textarea")].filter((item) => !item.getAttribute("aria-label") && !item.id && !item.closest("label")).length;
        return Math.max(0, 100 - (unlabeledImages + unlabeledButtons + unlabeledInputs) * 10);
      })(),
      seo_score: document.title && document.querySelector('meta[name="description"]') ? 100 : 80,
      initial_javascript_bytes: performance.getEntriesByType("resource").filter((item) => item.initiatorType === "script").reduce((sum, item) => sum + Number(item.transferSize || 0), 0),
    };
  });
  const largest = await page.evaluate(() => performance.getEntriesByType("resource").filter((item) => item.initiatorType === "script").reduce((max, item) => Math.max(max, Number(item.transferSize || 0)), 0));
  const headers = response?.headers() || {};
  const performanceScore = metrics.lcp_ms == null ? null : Math.max(0, Math.min(100, Math.round(100 - Math.max(0, metrics.lcp_ms - 2500) / 25 - Math.max(0, metrics.tbt_proxy_ms || 0) / 10 - Math.max(0, (metrics.cls || 0) - 0.1) * 100)));
  return { route: name, measured_path: route, requested_surface: route === "/" ? "actual_route" : route, profile, http_status: response?.status() ?? 0, ...metrics, performance_score_equivalent: performanceScore, best_practices_score: ["content-security-policy", "x-content-type-options", "referrer-policy"].every((name) => Boolean(headers[name])) ? 100 : 0, largest_client_script_bytes: largest, console_errors: consoleErrors.length, failed_requests: failedRequests.length, elapsed_ms: Date.now() - started };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const result = { status: "pass", equivalent: "playwright-browser-rubric-not-lighthouse", environment: { browser: await browser.version(), viewport: `${viewport.width}x${viewport.height}`, profile, mode: "production_build", samples, cpu_network: "default local" }, routes: [] };
  for (let sample = 0; sample < samples; sample += 1) {
    for (const [name, route, label] of routes) {
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      result.routes.push({ sample: sample + 1, ...(await measure(page, name, route)), requested_path_label: label });
      await context.close();
    }
  }
  await browser.close();
  result.status = result.routes.every((item) => item.console_errors === 0 && item.failed_requests === 0) ? "pass" : "failed";
  const output = JSON.stringify(result);
  if (process.env.PERF_OUTPUT) fs.writeFileSync(process.env.PERF_OUTPUT, `${output}\n`, "utf8");
  process.stdout.write(`${output}\n`);
  process.exitCode = result.status === "pass" ? 0 : 1;
}

main().catch((error) => { process.stderr.write("browser performance measurement failed\n"); process.exitCode = 1; });
