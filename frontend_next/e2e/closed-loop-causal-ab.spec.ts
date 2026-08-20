import type { Page } from "@playwright/test";
import type {
  LoanCalculationResult,
  LocationInsightResult,
  MarketResult,
  PropertySearchResult,
  TerrainRiskResult,
  ValuationResult,
  ValuationTrendResult,
} from "../lib/api";
import { expect, test } from "./fixtures";

const PROPERTY = {
  city: "臺北市",
  district: "大安區",
  road: "和平東路二段",
  address: "臺北市大安區和平東路二段100號",
  buildingType: "住宅大樓",
  area: 30,
  age: 15,
  floor: 8,
  askingPrice: 2_000,
} as const;
const SELECTED_ADDRESS = `${PROPERTY.city}${PROPERTY.district}${PROPERTY.road}`;

const PROPERTY_SEARCH = Object.assign({
  summary: {
    matched_count: 12,
    city_count: 1,
    district_count: 1,
    road_count: 1,
    budget_min: 1_500,
    budget_max: 2_500,
    period_min: "2025-01",
    period_max: "2026-06",
    data_source_label: "Official PLVR contract fixture",
    message: "Official transaction matches are available.",
    disclaimer: "Historical transactions are reference evidence, not listings.",
  },
  district_suggestions: [{
    city: PROPERTY.city,
    district: PROPERTY.district,
    sample_count: 12,
    median_total_price: PROPERTY.askingPrice,
    median_unit_price_per_ping: 66.7,
    median_area_ping: PROPERTY.area,
    common_building_type: PROPERTY.buildingType,
    score: 88,
    reason: "Within the selected budget and area range.",
    p25_total_price: 1_850,
    p75_total_price: 2_200,
  }],
  road_suggestions: [{
    city: PROPERTY.city,
    district: PROPERTY.district,
    road: PROPERTY.road,
    sample_count: 12,
    median_total_price: PROPERTY.askingPrice,
    median_unit_price_per_ping: 66.7,
    median_area_ping: PROPERTY.area,
    common_building_type: PROPERTY.buildingType,
    score: 91,
    reason: "Same-road official evidence is available.",
    p25_total_price: 1_850,
    p75_total_price: 2_200,
  }],
  matched_transactions: [{
    transaction_period: "2026-06",
    city: PROPERTY.city,
    district: PROPERTY.district,
    road: PROPERTY.road,
    building_type: PROPERTY.buildingType,
    area_ping: PROPERTY.area,
    total_price: PROPERTY.askingPrice,
    unit_price_per_ping: 66.7,
    building_age_years: PROPERTY.age,
    floor: PROPERTY.floor,
    source_label: "Official PLVR OpenData",
  }],
  methodology: "Deterministic official transaction filter.",
  disclaimer: "Reference evidence only.",
} satisfies PropertySearchResult, {
  search_status: "available",
  search_reason_code: "OFFICIAL_MATCHES",
  result_origin: "official",
  is_actionable: true,
});

function locationResult(address: string = PROPERTY.address): LocationInsightResult {
  return {
    input: { address },
    resolved_location: { address_label: address, latitude: 25.026, longitude: 121.543, geocoding_confidence: "high" },
    radius_m: 800,
    location_score: 78,
    category_scores: { transit_score: 82, convenience_score: 80, education_score: 74, green_space_score: 70, medical_score: 76, risk_score: 40 },
    poi_summary: { transit_count: 4, convenience_count: 8, school_count: 3, park_count: 2, medical_count: 4, risk_facility_count: 1 },
    nearest_pois: [{ category: "transit", name: "Technology Building Station", distance_m: 420, source: "controlled-contract-fixture" }],
    strengths: ["Transit and daily services are represented."],
    weaknesses: ["Field verification remains required."],
    buyer_fit: { self_use_family: "Review", commuter: "Review", investor: "Review", elderly: "Review" },
    valuation_context: { supports_price_reasonableness: "unknown", explanation: "Location evidence does not determine price." },
    data_quality: { status: "good", missing_sources: [], warnings: [] },
    scoring_method: { weights: { transit: 0.25 }, explanation: "Deterministic category aggregation." },
    disclaimer: "Reference evidence only.",
  };
}

function terrainResult(address: string = PROPERTY.address): TerrainRiskResult {
  const hazard = (key: string) => ({ key, label: key, status: "available" as const, level: "low" as const, matched: false, distance_m: 800, value: null, explanation: "No match in the controlled contract fixture." });
  return {
    input: { address },
    resolved_location: { address_label: address, latitude: 25.026, longitude: 121.543, geocoding_confidence: "high", geocoding_source: "provided_coordinates" },
    overall: { level: "low", label: "Controlled terrain reference", summary: "Available layers require professional review.", confidence: "medium" },
    terrain: { status: "available", slope_value: 2, slope_class: "gentle", elevation_m: 20, explanation: "Controlled provider contract fixture." },
    hazards: {
      landslide: hazard("landslide"),
      debris_flow: hazard("debris_flow"),
      flood: hazard("flood"),
      geological_sensitivity: hazard("geological_sensitivity"),
      liquefaction: hazard("liquefaction"),
      active_fault: hazard("active_fault"),
    },
    risk_factors: [],
    missing_sources: [],
    recommended_checks: ["Confirm official layers and inspect the site."],
    map_layers: [],
    data_quality: { status: "good", warnings: [], checked_at: "2026-08-20T00:00:00Z" },
    disclaimer: "Terrain evidence is reference-only.",
  };
}

function valuationResult(mid: number = 2_100, area: number = PROPERTY.area): ValuationResult {
  const unit = Number((mid / area).toFixed(2));
  const comparables = [0, 1, 2].map((index) => ({
    transaction_period: `2026-0${6 - index}`,
    city: PROPERTY.city,
    district: PROPERTY.district,
    road: PROPERTY.road,
    building_type: PROPERTY.buildingType,
    area_ping: area + index,
    unit_price_per_ping: unit + index,
    total_price: mid + index * 50,
    building_age_years: PROPERTY.age + index,
    distance_m: index * 100,
    similarity_score: 0.9 - index * 0.05,
    weight: 1,
    note: "Official same-road comparable.",
    source: "official_plvr_opendata" as const,
    source_label: "Official PLVR OpenData",
  }));
  return Object.assign({
    source: "postgres" as const,
    data_status: {
      active_source: "postgres" as const,
      is_demo_data: false,
      is_full_taiwan: true,
      data_composition: "official" as const,
      official_records_count: 120,
      sample_records_count: 0,
      coverage: { cities: [PROPERTY.city], districts: [PROPERTY.district], roads_count: 1, records_count: 120 },
      last_updated: "2026-08-19",
      update_frequency_note: "Updated by official release cadence.",
      source_note: "Official PLVR contract fixture.",
      user_message: "Official evidence is available.",
      freshness_status: "fresh" as const,
      freshness_reason_code: "CURRENT_RELEASE",
      freshness_as_of: "2026-08-19",
      latest_import_at: "2026-08-19T00:00:00Z",
      latest_import_age_days: 1,
      newest_effective_period_lag_months: 1,
      operator_attention_required: false,
      freshness_user_message: "Current release.",
    },
    data_composition: "official" as const,
    estimate_data_composition: "official" as const,
    estimate_source_label: "Official PLVR OpenData",
    candidate_pool_size: 12,
    official_same_road_count: 12,
    official_same_district_count: 12,
    sample_same_road_count: 0,
    sample_same_district_count: 0,
    estimate_level: "road" as const,
    matched_community: null,
    confidence_reason: "Three or more official same-road comparables.",
    source_details: { file: "official-contract-fixture", nature: "official", complete_real_price_registry: true, formal_appraisal: false, bank_appraisal: false, future_adapter: "none" },
    estimate_total_price: mid,
    estimate_unit_price_per_ping: unit,
    price_range: { low: mid - 150, mid, high: mid + 150 },
    unit_price_distribution: { weighted_mean: unit, weighted_median: unit, p25: unit - 5, p75: unit + 5 },
    confidence: "high" as const,
    confidence_score: 88,
    comparables,
    valuation_explanation: { sample_count: 3, same_road_count: 3, same_district_count: 3, same_city_count: 3, same_building_type_count: 3, nearest_distance_m: 0, average_area_difference_ping: 1, average_age_difference_years: 1, average_similarity_score: 0.85, method: "Official comparable weighting." },
    methodology: ["Official comparable weighting"],
    disclaimer: "This is not a formal appraisal.",
  }, {
    valuation_status: "available",
    valuation_reason_code: "OFFICIAL_COMPARABLES",
    result_origin: "official",
    is_actionable: true,
  }) as ValuationResult;
}

function trendResult(): ValuationTrendResult {
  const point = (period: string, median: number) => ({ period, median_unit_price_per_ping: median, p25_unit_price_per_ping: median - 5, p75_unit_price_per_ping: median + 5, transaction_count: 6 });
  const scenario = (growth: number) => [6, 12, 36].map((horizon_months) => ({ horizon_months, projected_unit_price_per_ping: 70, projected_total_price: 2_100, growth_rate_used: growth, explanation: "Controlled trend contract fixture." }));
  return Object.assign({
    source: "official_plvr_opendata" as const,
    data_scope: "road" as const,
    raw_period_min: "2026-05",
    raw_period_max: "2026-06",
    effective_period_min: "2026-05",
    effective_period_max: "2026-06",
    excluded_future_period_count: 0,
    excluded_out_of_window_count: 0,
    period_min: "2026-05",
    period_max: "2026-06",
    sample_count: 12,
    road_sample_count: 12,
    district_sample_count: 12,
    monthly_series: [point("2026-05", 68), point("2026-06", 70)],
    yearly_series: [{ year: "2026", median_unit_price_per_ping: 69, transaction_count: 12, yoy_change_percent: null }],
    recent_median_unit_price: 70,
    trend_annualized_rate: 0.02,
    volatility: 0.01,
    confidence_level: "medium" as const,
    confidence_reason: "Two controlled official periods.",
    scenario_forecast: { conservative: scenario(0), base: scenario(0.02), optimistic: scenario(0.04) },
    methodology: ["Official period aggregation"],
    disclaimer: "Trend scenarios are not forecasts.",
  }, { trend_status: "available", trend_reason_code: "OFFICIAL_PERIODS", is_actionable: true }) as ValuationTrendResult;
}

function loanResult(price = 2_000, income = 12, monthlyPayment = 60_000): LoanCalculationResult {
  const burden = monthlyPayment / (income * 10_000);
  return {
    property_price_wan: price,
    down_payment_ratio: 0.2,
    down_payment_wan: price * 0.2,
    loan_amount_wan: price * 0.8,
    annual_interest_rate: 2.2,
    loan_years: 30,
    grace_period_years: 0,
    monthly_income_wan: income,
    monthly_payment: monthlyPayment,
    grace_period_monthly_payment: null,
    post_grace_monthly_payment: null,
    total_payment: monthlyPayment * 360,
    total_interest: monthlyPayment * 360 - price * 8_000,
    income_burden_ratio: burden,
    affordability_level: burden <= 0.35 ? "manageable" : "tight",
    affordability_message: burden <= 0.35 ? "Controlled contract: manageable burden." : "Controlled contract: tight burden.",
    sensitivity: [
      { annual_interest_rate: 2.0, monthly_payment: monthlyPayment - 2_000, total_interest: 4_000_000, difference_from_base: -2_000 },
      { annual_interest_rate: 2.2, monthly_payment: monthlyPayment, total_interest: 5_000_000, difference_from_base: 0 },
      { annual_interest_rate: 2.5, monthly_payment: monthlyPayment + 3_000, total_interest: 6_000_000, difference_from_base: 3_000 },
    ],
    disclaimer: "Controlled response generated from the backend loan contract.",
  };
}

function marketResult(): MarketResult {
  return {
    city: PROPERTY.city,
    county: PROPERTY.city,
    district: PROPERTY.district,
    period: "2026-06",
    average_unit_price: 70,
    avg_price_per_ping: 70,
    transaction_count: 20,
    transaction_volume: 20,
    record_count: 20,
    summary: "Official district transactions are available.",
    source_name: "Official PLVR OpenData aggregate",
    source_updated_at: "2026-08-19",
    coverage_status: "covered",
    data_status: "available",
    caveat: "District aggregate reference only.",
    disclaimer: "Market evidence is not a purchase recommendation.",
    history: [
      { period: "2026-06", average_unit_price: 70, transaction_count: 20 },
      { period: "2026-05", average_unit_price: 68, transaction_count: 18 },
    ],
    sample_status: "sufficient",
    freshness_status: "current",
    price_distribution: [{ label: "60-80", count: 20 }],
    building_type_distribution: [{ label: PROPERTY.buildingType, count: 20 }],
    age_band_distribution: [{ label: "10-20", count: 20 }],
  };
}

function demoResults() {
  return {
    inputs: { city: PROPERTY.city, district: PROPERTY.district, road: PROPERTY.road, building_type: PROPERTY.buildingType, area_ping: PROPERTY.area, building_age_years: PROPERTY.age, floor: PROPERTY.floor },
    propertySearch: PROPERTY_SEARCH,
    locationInsight: locationResult(),
    terrainRisk: terrainResult(),
    valuation: valuationResult(),
    trend: trendResult(),
    loan: loanResult(),
  };
}

async function useEnglish(page: Page) {
  await page.locator("header select").selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
}

async function openJourney(page: Page, locale: "en" | "zh-TW" = "en") {
  await page.goto("/");
  if (locale === "en") await useEnglish(page);
  await expect(page.locator("#journey-stage-property")).toBeVisible();
}

async function hydrateJourney(page: Page) {
  await openJourney(page);
  await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("proptech:guided-demo-result", { detail })), demoResults());
}

async function goToStep(page: Page, step: "property" | "location" | "price" | "affordability" | "decision") {
  await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail })), step);
  await expect(page.locator(`#journey-stage-${step}`)).toBeVisible();
}

async function registerJourneyApis(page: Page) {
  await page.route("**/roads/cities**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ cities: [PROPERTY.city], message: "Available" }) }));
  await page.route("**/roads/districts**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: PROPERTY.city, districts: [PROPERTY.district], message: "Available" }) }));
  await page.route("**/roads/roads**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ city: PROPERTY.city, district: PROPERTY.district, roads: [PROPERTY.road], message: "Available" }) }));
  await page.route("**/valuation/data-status", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(valuationResult().data_status) }));
  await page.route("**/valuation/property-search", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(PROPERTY_SEARCH) }));
  await page.route("**/location/insight", async (route) => {
    const payload = route.request().postDataJSON() as { address?: string };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(locationResult(payload.address || PROPERTY.address)) });
  });
  await page.route("**/valuation/estimate", async (route) => {
    const payload = route.request().postDataJSON() as { area_ping?: number };
    const area = Number(payload.area_ping || PROPERTY.area);
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(valuationResult(area === 35 ? 2_400 : 2_100, area)) });
  });
  await page.route("**/valuation/trend", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(trendResult()) }));
  await page.route("**/market-insights/query", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(marketResult()) }));
  await page.route("**/loan/calculate", async (route) => {
    const payload = route.request().postDataJSON() as { property_price?: number; monthly_income?: number };
    const price = Number(payload.property_price || 0);
    const income = Number(payload.monthly_income || 12);
    const payment = price >= 2_600 ? 82_000 : price >= 2_100 ? 65_000 : 60_000;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(loanResult(price, income, payment)) });
  });
}

test("full happy path carries one property through all five steps", async ({ page }) => {
  await registerJourneyApis(page);
  await openJourney(page);
  const timings: Record<string, number> = {};

  let started = Date.now();
  await page.getByRole("button", { name: "Search viewing options" }).click();
  const transactionDisclosure = page.locator("#property-finder details").filter({ hasText: "transaction samples" });
  await transactionDisclosure.locator("summary").click();
  await transactionDisclosure.getByRole("button", { name: "View nearby livability" }).click();
  timings.step1 = Date.now() - started;
  await expect(page.locator("#journey-stage-location")).toBeVisible();
  await expect(page.getByTestId("journey-property-context").first()).toContainText(PROPERTY.road);

  started = Date.now();
  await page.locator("#location-insight-calculator").getByRole("button", { name: "Start location analysis" }).click();
  await expect(page.getByTestId("location-result")).toContainText(SELECTED_ADDRESS);
  await page.locator("#journey-stage-location").getByRole("button", { name: "Review price evidence", exact: true }).click();
  timings.step2 = Date.now() - started;

  const valuation = page.locator("#valuation-calculator");
  await expect(valuation.locator("input[type=number]").nth(0)).toHaveValue("30");
  await expect(valuation.locator("input[type=number]").nth(1)).toHaveValue("15");
  await expect(valuation.locator("input[type=number]").nth(2)).toHaveValue("8");
  started = Date.now();
  await valuation.getByRole("button", { name: "Estimate price" }).click();
  await expect(page.getByTestId("valuation-result").first()).toBeVisible();
  await page.getByRole("button", { name: /Valuation midpoint/ }).click();
  await expect(page.getByTestId("journey-active-price")).toContainText("2,100");
  await page.locator("#journey-stage-price").getByRole("button", { name: "Review funding and holding costs", exact: true }).click();
  timings.step3 = Date.now() - started;

  started = Date.now();
  const loan = page.locator("#loan-calculator");
  await loan.getByLabel("Monthly income (TWD ten-thousands, optional)").fill("12");
  await loan.getByRole("button", { name: "Calculate monthly payment" }).click();
  await expect(page.getByTestId("loan-result")).toContainText("65,000");
  await page.locator("#journey-stage-affordability").getByRole("button", { name: "Review the viewing decision summary", exact: true }).click();
  timings.step4 = Date.now() - started;

  started = Date.now();
  await expect(page.getByTestId("decision-evidence-synthesis")).toBeVisible();
  await expect(page.getByTestId("decision-property-address")).toContainText(PROPERTY.road);
  await expect(page.getByTestId("decision-evidence-location")).toContainText(SELECTED_ADDRESS);
  await expect(page.getByTestId("decision-price-basis")).toContainText("Valuation midpoint: 2,100");
  await expect(page.getByTestId("decision-monthly-payment")).toContainText("65,000");
  timings.step5Render = Date.now() - started;
  console.info(`[closed-loop-warm-step-ms] ${JSON.stringify(timings)}`);
});

test("price-only A/B clears stale affordability and preserves location and terrain", async ({ page }) => {
  await registerJourneyApis(page);
  await hydrateJourney(page);
  await goToStep(page, "decision");
  const locationEvidence = page.getByTestId("decision-evidence-location");
  await expect(locationEvidence).toContainText(PROPERTY.address);
  await expect(locationEvidence).toContainText("Controlled terrain reference");
  await expect(page.getByTestId("decision-monthly-payment")).toContainText("60,000");

  await goToStep(page, "price");
  await page.getByTestId("journey-manual-price").fill("2600");
  await page.getByRole("button", { name: "Use manual price" }).click();
  await expect(page.getByTestId("journey-active-price")).toContainText("2,600");
  await goToStep(page, "affordability");
  await expect(page.getByTestId("affordability-price-context")).toContainText("2,600");
  await expect(page.getByTestId("loan-result")).toHaveCount(0);
  await page.locator("#loan-calculator").getByLabel("Monthly income (TWD ten-thousands, optional)").fill("12");
  await page.locator("#loan-calculator").getByRole("button", { name: "Calculate monthly payment" }).click();
  await expect(page.getByTestId("loan-result")).toContainText("82,000");

  await goToStep(page, "decision");
  await expect(locationEvidence).toContainText(PROPERTY.address);
  await expect(locationEvidence).toContainText("Controlled terrain reference");
  await expect(page.getByTestId("decision-price-basis")).toContainText("Manual override: 2,600");
  await expect(page.getByTestId("decision-monthly-payment")).toContainText("82,000");
});

test("income-only A/B preserves property, location, valuation and replaces affordability", async ({ page }) => {
  await registerJourneyApis(page);
  await hydrateJourney(page);
  await goToStep(page, "affordability");
  await expect(page.getByTestId("loan-result")).toContainText("tight burden");
  const loan = page.locator("#loan-calculator");
  await loan.getByLabel("Monthly income (TWD ten-thousands, optional)").fill("20");
  await expect(page.getByTestId("loan-result")).toHaveCount(0);
  await loan.getByRole("button", { name: "Calculate monthly payment" }).click();
  await expect(page.getByTestId("loan-result")).toContainText("manageable burden");

  await goToStep(page, "decision");
  await expect(page.getByTestId("decision-property-address")).toContainText(PROPERTY.road);
  await expect(page.getByTestId("decision-evidence-location")).toContainText(PROPERTY.address);
  await expect(page.getByTestId("decision-evidence-price")).toContainText("2,100");
  await expect(page.getByTestId("decision-monthly-payment")).toContainText("60,000");
});

test("address change invalidates location, terrain, market, valuation and affordability", async ({ page }) => {
  await registerJourneyApis(page);
  await hydrateJourney(page);
  await goToStep(page, "location");
  const address = page.locator("#location-insight-calculator").getByLabel("Property address");
  await expect(page.getByTestId("location-result")).toContainText(SELECTED_ADDRESS);
  await page.locator("section[aria-labelledby=location-market-tools-heading]").getByRole("button", { name: /Market Insight/ }).click();
  await page.getByTestId("market-insight-search-button").click();
  await expect(page.getByTestId("market-insight-available")).toContainText("2026-06");
  const addressB = "臺北市信義區市府路1號";
  await address.fill(addressB);
  await expect(page.getByTestId("location-result")).toHaveCount(0);

  await goToStep(page, "decision");
  await expect(page.getByTestId("decision-property-address")).toContainText(addressB);
  await expect(page.getByTestId("decision-evidence-location")).not.toContainText(PROPERTY.address);
  await expect(page.getByTestId("decision-evidence-location")).not.toContainText("Controlled terrain reference");
  await expect(page.getByTestId("decision-evidence-location")).not.toContainText("2026-06");
  await expect(page.getByTestId("decision-evidence-price")).not.toContainText("2,100");
  await expect(page.getByTestId("decision-monthly-payment")).not.toContainText("60,000");
});

test("A to B to A requires fresh location evidence on every address", async ({ page }) => {
  await registerJourneyApis(page);
  await openJourney(page);
  await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("proptech:guided-demo-result", { detail })), {
    ...demoResults(), terrainRisk: undefined, valuation: undefined, trend: undefined, loan: undefined,
  });
  await goToStep(page, "location");
  const calculator = page.locator("#location-insight-calculator");
  const address = calculator.getByLabel("Property address");
  const analyze = calculator.getByRole("button", { name: "Start location analysis" });
  let calls = 0;
  page.on("request", (request) => { if (new URL(request.url()).pathname.endsWith("/location/insight")) calls += 1; });

  await analyze.click();
  await expect(page.getByTestId("location-result")).toContainText(SELECTED_ADDRESS);
  const addressB = "臺北市信義區市府路1號";
  await address.fill(addressB);
  await expect(page.getByTestId("location-result")).toHaveCount(0);
  await analyze.click();
  await expect(page.getByTestId("location-result")).toContainText(addressB);
  await address.fill(PROPERTY.address);
  await expect(page.getByTestId("location-result")).toHaveCount(0);
  await analyze.click();
  await expect(page.getByTestId("location-result")).toContainText(PROPERTY.address);
  expect(calls).toBe(3);
});

test("area-only change preserves location and terrain while requiring a fresh valuation", async ({ page }) => {
  await registerJourneyApis(page);
  await hydrateJourney(page);
  await goToStep(page, "location");
  const calculator = page.locator("#location-insight-calculator");
  await calculator.getByLabel("Area (ping, optional)").fill("35");
  await expect(page.getByTestId("location-result")).toContainText(PROPERTY.address);
  await expect(page.getByTestId("journey-property-context").first()).toContainText("35 Ping");

  await goToStep(page, "price");
  await expect(page.getByTestId("valuation-result")).toHaveCount(0);
  await expect(page.locator("#valuation-calculator input[type=number]").first()).toHaveValue("35");
  await page.locator("#valuation-calculator").getByRole("button", { name: "Estimate price" }).click();
  await expect(page.getByTestId("valuation-result").first()).toContainText("2,400");
  await goToStep(page, "decision");
  await expect(page.getByTestId("decision-evidence-location")).toContainText(PROPERTY.address);
  await expect(page.getByTestId("decision-evidence-location")).toContainText("Controlled terrain reference");
  await expect(page.getByTestId("decision-evidence-price")).toContainText("2,400");
});

test("saved case round-trip restores journey identity, evidence and selected price basis", async ({ page }) => {
  await registerJourneyApis(page);
  await hydrateJourney(page);
  await goToStep(page, "decision");
  await page.getByRole("button", { name: /New case/ }).click();
  await page.getByRole("button", { name: "Save case", exact: true }).click();

  await goToStep(page, "location");
  await page.locator("#location-insight-calculator").getByLabel("Property address").fill("臺北市信義區市府路1號");
  await goToStep(page, "decision");
  await expect(page.getByTestId("decision-property-address")).toContainText("市府路1號");
  await page.getByRole("button", { name: /Saved cases/ }).click();
  await page.getByRole("button", { name: "Load", exact: true }).click();
  await expect(page.getByTestId("decision-property-address")).toContainText(PROPERTY.road);
  await expect(page.getByTestId("decision-evidence-location")).toContainText(SELECTED_ADDRESS);
  await expect(page.getByTestId("decision-monthly-payment")).toContainText("60,000");
});

test("390px closed loop has no page-level overflow and renders decision evidence", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await registerJourneyApis(page);
  await hydrateJourney(page);
  await goToStep(page, "decision");
  await expect(page.getByTestId("decision-evidence-synthesis")).toBeVisible();
  const dimensions = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, body: document.body.scrollWidth, root: document.documentElement.scrollWidth }));
  expect(dimensions.body).toBeLessThanOrEqual(dimensions.viewport + 1);
  expect(dimensions.root).toBeLessThanOrEqual(dimensions.viewport + 1);
});

test("all four locales remain coherent across the complete decision evidence surface", async ({ page }) => {
  await registerJourneyApis(page);
  await hydrateJourney(page);
  await goToStep(page, "decision");
  const synthesis = page.getByTestId("decision-evidence-synthesis");
  for (const [locale, title, basis] of [
    ["zh-TW", "五步驟證據摘要", "開價"],
    ["en", "Five-step evidence summary", "Asking price"],
    ["ja", "5ステップの根拠要約", "売出価格"],
    ["ko", "5단계 근거 요약", "매도 희망가"],
  ] as const) {
    await page.locator("header select").selectOption(locale);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(synthesis.getByRole("heading", { name: title })).toBeVisible();
    await expect(page.getByTestId("decision-price-basis")).toContainText(basis);
    await expect(synthesis).not.toContainText(/journey\.|state\.|trust\./);
  }
});
