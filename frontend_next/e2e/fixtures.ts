import { test as base, expect } from "@playwright/test";

const mockGoogleHealth = {
  google_key_configured: false,
  geocoding_enabled: false,
  places_enabled: false,
  last_error: "",
  mode: "mock",
  safe_message: "Map provider status is unavailable.",
};

const daxiRoads = [
  "三元一街", "三元三街", "三元二街", "三層老街", "三民路", "中央路", "中山路", "中庄下崁", "中庄街", "中正東路",
  "中正路", "中華路", "仁一街", "仁三街", "仁二街", "仁和一街", "仁和七街", "仁和三街", "仁和九街", "仁和二街",
  "仁和五街", "仁和八街", "仁和六街", "仁和東街", "仁和西街", "仁和路", "仁善一街", "仁善七街", "仁善三街", "仁善二街",
];

const districts: Record<string, string[]> = {
  "桃園市": ["大溪區", "桃園區"],
  "新北市": ["永和區", "板橋區"],
  "臺北市": ["大安區", "信義區"],
  "基隆市": ["七堵區", "中正區"],
  "屏東縣": ["林邊鄉", "屏東市"],
  "澎湖縣": ["馬公市"],
};

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const diagnostics: string[] = [];
    page.on("console", (message) => { if (message.type() === "error" || message.type() === "warning") diagnostics.push(`console:${message.type()}:${message.text()}`); });
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
    await page.route("**/taxoracle/sources", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ source_status: "configured", rule_version: "compatibility-screening-v1", source_name: "official rule metadata" }) }));
    await page.route("**/taxoracle/analyze", async (route) => {
      const payload = route.request().postDataJSON();
      const failed = ["sold_self_occupied", "residency_condition_met", "purchase_within_reasonable_period", "purchased_self_occupied", "same_owner", "land_value_available", "required_docs_complete"].filter((key) => payload[key] === false).length;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ eligibility_status: failed ? "manual_review" : "eligible", risk_score: failed * 15, signal_color: failed ? "yellow" : "green", hard_fail_rules: [], manual_review_rules: [], missing_docs: [], reminder_timeline: [], rule_traces: [], ai_explanation: { headline: "Example", customer_script: "", source: "deterministic" }, disclaimer: "Preliminary reference only.", case_input: payload, official_rule_trace: { rule_version: "compatibility-screening-v1", jurisdiction: "TW", effective_date: null, source_name: "official rule metadata", source_status: "configured", calculation_kind: "preliminary_screening", limitation: "Professional review required." }, tax_output_boundary: "preliminary_screening_only" }) });
    });
    await page.route("**/holding-cost/calculate", async (route) => {
      const payload = route.request().postDataJSON();
      const price = Number(payload.property_price ?? 0);
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ property_price_wan: price, monthly_total_holding_cost: Math.round(price * 0.0012), annual_total_holding_cost: Math.round(price * 0.0144), monthly_management_fee: 0, monthly_repair_reserve: 0, monthly_tax_estimate: Math.round(price * 0.0012), annual_home_tax_estimate: 0, annual_land_tax_estimate: 0, monthly_insurance: 0, loan_monthly_payment: 0, income_burden_ratio: null, affordability_level: "unknown", affordability_message: "Reference only", cost_breakdown: [], disclaimer: "Reference only.", input: payload }) });
    });
    await page.route("**/map/google-health", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockGoogleHealth) }));
    await page.route("**/roads/cities**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ cities: Object.keys(districts), message: "Road directory available." }) }));
    await page.route("**/roads/districts**", async (route) => {
      const city = new URL(route.request().url()).searchParams.get("city") ?? "";
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city, districts: districts[city] ?? [], message: "Districts available." }) });
    });
    await page.route("**/roads/roads**", async (route) => {
      const url = new URL(route.request().url());
      const city = url.searchParams.get("city") ?? "";
      const district = url.searchParams.get("district") ?? "";
      const roads = city === "桃園市" && district === "大溪區" ? daxiRoads : ["中山路", "中正路", "和平路"];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city, district, roads, message: "Roads available." }) });
    });
    await use(page);
    if (testInfo.status !== testInfo.expectedStatus) await testInfo.attach("runtime-diagnostics", { body: diagnostics.join("\n") || "no captured runtime diagnostics", contentType: "text/plain" });
  },
});

export { expect };
