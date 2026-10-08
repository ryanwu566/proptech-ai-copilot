import { expect, test } from "./fixtures";
import { openMethod } from "./helpers/commercial-navigation";
import { compareSavedCases } from "../lib/case-comparison";
import { compactCaseData, type SavedCase, type SavedCaseData } from "../lib/case-storage";

const dataStatus = {
  active_source: "postgres", is_demo_data: false, is_full_taiwan: true, data_composition: "official",
  official_records_count: 3, sample_records_count: 0,
  coverage: { cities: ["臺北市"], districts: ["大安區"], roads_count: 1, records_count: 3 },
  last_updated: "2026-09-01", update_frequency_note: "", source_note: "", user_message: "",
  freshness_status: "fresh", freshness_reason_code: "current", freshness_as_of: "2026-09-01",
  latest_import_at: "2026-09-01T00:00:00Z", latest_import_age_days: 1,
  newest_effective_period_lag_months: 1, operator_attention_required: false, freshness_user_message: "",
};

function holdingResult(payload: Record<string, number>) {
  const loan = payload.loan_monthly_payment;
  const monthlyTotal = loan + 1_000;
  return {
    input: { property_price_wan: payload.property_price, loan_monthly_payment: loan, monthly_income_wan: null, area_ping: null, management_fee_per_ping: 0, repair_reserve_per_ping: 0, annual_home_tax_rate: 0, annual_land_tax_rate: 0, annual_insurance: 0, include_tax_estimate: true },
    property_price_wan: payload.property_price, loan_monthly_payment: loan,
    monthly_management_fee: 0, monthly_repair_reserve: 0, monthly_tax_estimate: 1_000,
    annual_home_tax_estimate: 12_000, annual_land_tax_estimate: 0, monthly_insurance: 0,
    monthly_total_holding_cost: monthlyTotal, annual_total_holding_cost: monthlyTotal * 12,
    income_burden_ratio: null, affordability_level: "unknown", affordability_message: "Income not provided.",
    cost_breakdown: [{ key: "loan", label: "Mortgage", monthly_amount: loan }, { key: "tax", label: "Tax", monthly_amount: 1_000 }],
    disclaimer: "Reference only.",
  };
}

test("saved comparisons retain a bounded trusted valuation without persisted comparables", () => {
  const comparable = {
    transaction_period: "2026-01", city: "Taipei", district: "Daan", road: "Xinyi Road",
    building_type: "Apartment", area_ping: 30, unit_price_per_ping: 70, total_price: 2_100,
    building_age_years: 10, distance_m: 100, similarity_score: 90, weight: 1,
    note: "official", source: "official_plvr_opendata", source_label: "PLVR",
  };
  const valuation = {
    valuation_status: "available", valuation_reason_code: "official_result_available",
    result_origin: "official", is_actionable: true, source: "postgres", data_status: dataStatus,
    data_composition: "official", estimate_data_composition: "official", estimate_source_label: "Official PLVR",
    candidate_pool_size: 3, official_same_road_count: 3, official_same_district_count: 3,
    sample_same_road_count: 0, sample_same_district_count: 0, estimate_level: "road", matched_community: null,
    confidence_reason: "Enough evidence.", source_details: {}, estimate_total_price: 2_100,
    estimate_unit_price_per_ping: 70, price_range: { low: 1_900, mid: 2_100, high: 2_300 },
    unit_price_distribution: { weighted_mean: 70, weighted_median: 70, p25: 65, p75: 75 },
    confidence: "high", confidence_score: 90, comparables: [comparable, comparable, comparable],
    valuation_explanation: { sample_count: 3, same_road_count: 3, same_district_count: 3, same_city_count: 3,
      same_building_type_count: 3, nearest_distance_m: 100, average_area_difference_ping: 1,
      average_age_difference_years: 1, average_similarity_score: 90, method: "Official comparables." },
    methodology: [], disclaimer: "Reference only.",
  };
  const inputs = { city: "Taipei", district: "Daan", road: "Xinyi Road", building_type: "Apartment", area_ping: 30, building_age_years: 10, floor: 8 };
  const compacted = compactCaseData({ inputs, valuation } as unknown as SavedCaseData);
  const reopened = compactCaseData(compacted);
  const saved = (id: string): SavedCase => ({
    id, title: `Case ${id}`, createdAt: "2026-09-27T00:00:00Z", updatedAt: "2026-09-27T00:00:00Z",
    version: 1, workflowMode: "buying_wizard", activeWizardStep: "report", progress: 100,
    inputSummary: { city: "Taipei", district: "Daan", road: "Xinyi Road", propertyPrice: 2_100 },
    data: reopened,
  });

  expect(reopened.valuation?.comparables).toEqual([]);
  expect(reopened.valuationEvidence?.transferable).toBe(true);
  const compared = compareSavedCases([saved("a"), saved("b")]);
  expect(compared.cases[0].valuationTrusted).toBe(true);
  expect(compared.cases[0].valuationMid).toBe(2_100);
});

test("nullable valuation response stays inside the valuation section", async ({ page }) => {
  await page.unroute("**/valuation/**");
  await page.route("**/valuation/data-status", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(dataStatus) }));
  await page.route("**/valuation/trend", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
    source: "official_plvr_opendata", trend_status: "no_data", trend_reason_code: "insufficient_evidence", is_actionable: false,
    data_scope: "none", raw_period_min: null, raw_period_max: null, effective_period_min: null, effective_period_max: null,
    excluded_future_period_count: 0, excluded_out_of_window_count: 0, period_min: null, period_max: null,
    sample_count: 0, road_sample_count: 0, district_sample_count: 0, monthly_series: [], yearly_series: [],
    recent_median_unit_price: null, trend_annualized_rate: null, volatility: null, confidence_level: "unknown",
    confidence_reason: "Insufficient evidence.", scenario_forecast: { conservative: [], base: [], optimistic: [] }, methodology: [], disclaimer: "",
  }) }));
  await page.route("**/valuation/estimate", (route) => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify({
      valuation_status: "no_data", valuation_reason_code: "official_comparables_insufficient", result_origin: "official", is_actionable: false,
      source: "postgres", data_status: dataStatus, data_composition: "official", estimate_data_composition: "official",
      estimate_source_label: "Official PLVR", candidate_pool_size: 2, official_same_road_count: 2, official_same_district_count: 0,
      sample_same_road_count: 0, sample_same_district_count: 0, estimate_level: "none", matched_community: null,
      confidence_reason: "Insufficient evidence.", source_details: {}, estimate_total_price: null, estimate_unit_price_per_ping: null,
      price_range: { low: null, mid: null, high: null }, unit_price_distribution: { weighted_mean: null, weighted_median: null, p25: null, p75: null },
      confidence: null, confidence_score: null, comparables: [],
      valuation_explanation: { sample_count: 2, same_road_count: 2, same_district_count: 2, same_city_count: 2, same_building_type_count: 2, nearest_distance_m: null, average_area_difference_ping: null, average_age_difference_years: null, average_similarity_score: null, method: "Insufficient evidence." },
      methodology: [], disclaimer: "No valuation produced.",
    }),
  }));
  await page.goto("/");
  await openMethod(page, "房價估算");
  const calculator = page.locator("#valuation-calculator");
  await calculator.locator("select").nth(2).selectOption("中山路");
  await calculator.getByRole("button", { name: /估算房價/ }).click();

  await expect(page.getByText("官方成交證據不足，無法提供估價。")).toBeVisible();
  await expect(page.locator("#main-content")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新查看官方成交條件" })).toBeVisible();
});

test("manual 3.0376 wan monthly payment sends canonical 30,376 TWD", async ({ page }) => {
  let capturedPayment: number | undefined;
  await page.route("**/holding-cost/calculate", async (route) => {
    const payload = route.request().postDataJSON() as Record<string, number>;
    capturedPayment = payload.loan_monthly_payment;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(holdingResult(payload)) });
  });
  await page.goto("/");
  await openMethod(page, "Aegis-Credit");
  const holding = page.locator("#holding-cost-calculator");
  await holding.getByLabel("每月貸款支出（萬元）").fill("3.0376");
  await holding.getByRole("button", { name: "計算持有成本" }).click();

  await expect.poll(() => capturedPayment).toBe(30_376);
  await expect(holding).toContainText("30,376");
});

test("loan TWD prefill is displayed in wan and submitted without double conversion", async ({ page }) => {
  let capturedPayment: number | undefined;
  await page.route("**/loan/calculate", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
    property_price_wan: 1_000, down_payment_ratio: 0.2, down_payment_wan: 200, loan_amount_wan: 800,
    annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0, monthly_income_wan: null,
    monthly_payment: 30_376, grace_period_monthly_payment: null, post_grace_monthly_payment: null,
    total_payment: 10_935_360, total_interest: 2_935_360, income_burden_ratio: null,
    affordability_level: "unknown", affordability_message: "Income not provided.", sensitivity: [], disclaimer: "Reference only.",
  }) }));
  await page.route("**/holding-cost/calculate", async (route) => {
    const payload = route.request().postDataJSON() as Record<string, number>;
    capturedPayment = payload.loan_monthly_payment;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(holdingResult(payload)) });
  });
  await page.goto("/");
  await openMethod(page, "Aegis-Credit");
  await page.getByRole("button", { name: "計算貸款月付" }).click();
  const loanResult = page.getByTestId("loan-result");
  await expect(loanResult).toBeVisible();
  await expect(loanResult).toContainText("30,376");
  await loanResult.getByRole("button", { name: /持有成本/ }).click();
  const holding = page.locator("#holding-cost-calculator");
  await expect(holding.getByLabel("每月貸款支出（萬元）")).toHaveValue("3.0376");
  await holding.getByRole("button", { name: "計算持有成本" }).click();

  await expect.poll(() => capturedPayment).toBe(30_376);
});

test("holding monthly-payment input states ten-thousand NTD in every locale", async ({ page }) => {
  await page.goto("/");
  await openMethod(page, "Aegis-Credit");
  const locale = page.getByTestId("locale-switcher");
  for (const [value, label] of [
    ["zh-TW", "每月貸款支出（萬元）"],
    ["en", "Monthly loan payment (ten-thousand NTD)"],
    ["ja", "月々のローン支出（万NTD）"],
    ["ko", "월 대출 지출(만 NTD)"],
  ] as const) {
    await locale.selectOption(value);
    await expect(page.locator("#holding-cost-calculator").getByLabel(label)).toBeVisible();
  }
});
