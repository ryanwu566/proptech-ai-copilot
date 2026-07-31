import { test as base, expect } from "@playwright/test";

const mockGoogleHealth = {
  google_key_configured: false,
  geocoding_enabled: false,
  places_enabled: false,
  last_error: "",
  mode: "mock",
  safe_message: "Map provider status is unavailable.",
};

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const diagnostics: string[] = [];
    page.on("console", (message) => { if (message.type() === "error" || message.type() === "warning") diagnostics.push(`console:${message.type()}`); });
    page.on("pageerror", (error) => diagnostics.push(`pageerror:${error.message}`));
    page.on("request", (request) => { const path = new URL(request.url()).pathname; if (path.startsWith("/roads/") || path.startsWith("/map/")) diagnostics.push(`request:${path}`); });
    page.on("requestfailed", (request) => diagnostics.push(`requestfailed:${new URL(request.url()).pathname}`));
    page.on("response", (response) => { if (response.status() >= 500) diagnostics.push(`response:${response.status()}:${new URL(response.url()).pathname}`); });
    await page.addInitScript(() => {
      window.localStorage.setItem("proptech_onboarding_seen", "true");
      window.localStorage.setItem("proptech_onboarding_version", "2");
    });
    await page.route("**/map/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable", data_status: "unavailable", source: "mock", matched: false }) }));
    await page.route("**/location/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable", data_status: "unavailable" }) }));
    await page.route("**/market-insights/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable", data_status: "unavailable", coverage_status: "unknown", regions: [] }) }));
    await page.route("**/valuation/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable", data_status: "unavailable" }) }));
    await page.route("**/tax/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable" }) }));
    await page.route("**/loan/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable" }) }));
    await page.route("**/holding-cost/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "unavailable" }) }));
    await page.route("**/map/google-health", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockGoogleHealth) }));
    await page.route("**/roads/cities**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ cities: ["臺北市", "新北市"], message: "Road directory available." }) }));
    await page.route("**/roads/districts**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: "臺北市", districts: ["信義區", "大安區"], message: "Districts available." }) }));
    await page.route("**/roads/roads**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: "臺北市", district: "信義區", roads: ["市府路", "和平東路二段"], message: "Roads available." }) }));
    await use(page);
    if (testInfo.status !== testInfo.expectedStatus) await testInfo.attach("runtime-diagnostics", { body: diagnostics.join("\n") || "no captured runtime diagnostics", contentType: "text/plain" });
  },
});

export { expect };
