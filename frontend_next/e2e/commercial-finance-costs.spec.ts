import { expect, test, type Page } from "@playwright/test";

const NOW = "2026-10-06T08:00:00.000Z";

function identityAnchor() {
  return {
    version: 1,
    scope: "journey_browser_anchor",
    journey_anchor_id: "journey-browser-77777777-2222-4333-8444-555555555555",
    address_input: "臺北市信義區信義路五段7號",
    normalized_address: "臺北市信義區信義路五段7號",
    coordinates: { latitude: 25.033, longitude: 121.5654 },
    administrative_location: { city: "臺北市", district: "信義區", village: null, village_code: null },
    location_status: "candidate",
    parcel: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
    building: { status: "unavailable", candidate_id: null, candidates: [], source_id: null, confidence: "unknown", limitations: [], confirmation: null },
    confidence: { level: "medium", domain: "address_spatial_correlation", basis: ["accepted_coordinates"], limitations: ["not_legal_identity"] },
    evidence: { sources: [], checked_at: NOW, limitations: [] },
    revalidation: { status: "current", conflicts: [] },
  };
}

function savedCase() {
  return {
    id: "finance-case",
    title: "信義路物件",
    createdAt: NOW,
    updatedAt: NOW,
    version: 1,
    workflowMode: "buying_wizard",
    activeWizardStep: "affordability",
    progress: 60,
    inputSummary: { city: "臺北市", district: "信義區", road: "信義路五段7號", propertyPrice: 1850 },
    data: {
      inputs: { city: "臺北市", district: "信義區", road: "信義路五段7號", building_type: "住宅大樓", area_ping: 0, building_age_years: 5, floor: 8 },
      propertyIdentityAnchor: identityAnchor(),
      journeyContext: {
        version: 1,
        propertyContext: { city: "臺北市", district: "信義區", road: "信義路五段7號", addressSummary: "臺北市信義區信義路五段7號", sourceLabel: "Saved case", selectionStatus: "selected", askingPriceWan: 1850 },
        priceBasis: "asking",
        activePriceWan: 1850,
      },
      taxOracle: {
        eligibility_status: "manual_review",
        risk_score: 80,
        signal_color: "yellow",
        hard_fail_rules: [],
        manual_review_rules: ["TX009"],
        missing_docs: ["戶籍資料"],
        reminder_timeline: [],
        rule_traces: [],
        ai_explanation: { headline: "", customer_script: "", source: "" },
        disclaimer: "初步檢查",
        case_input: { case_id: "private", client_name: "private", sold_self_occupied: false, residency_condition_met: false, purchase_within_reasonable_period: false, purchased_self_occupied: false, same_owner: false, land_value_available: false, required_docs_complete: false, enters_five_year_monitoring: false, exceptional_circumstances: false },
        official_rule_trace: { rule_version: "2026.1", jurisdiction: "TW", effective_date: "2026-01-01", source_name: "財政部", source_status: "available", calculation_kind: "deterministic", limitation: "初步" },
      },
    },
  };
}

const loanResponse = {
  property_price_wan: 1850, down_payment_ratio: 0.2, down_payment_wan: 370, loan_amount_wan: 1480,
  annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0, monthly_income_wan: null,
  monthly_payment: 56196, grace_period_monthly_payment: null, post_grace_monthly_payment: null,
  total_payment: 20230560, total_interest: 5430560, income_burden_ratio: null,
  affordability_level: "unknown", affordability_message: "未提供收入", sensitivity: [], disclaimer: "僅供試算",
};

const holdingResponse = {
  input: { property_price_wan: 1850, loan_monthly_payment: 56196, monthly_income_wan: null, area_ping: null, management_fee_per_ping: 80, repair_reserve_per_ping: 50, annual_home_tax_rate: 0.0012, annual_land_tax_rate: 0.001, annual_insurance: 3000, include_tax_estimate: true },
  property_price_wan: 1850, loan_monthly_payment: 56196, monthly_management_fee: 0, monthly_repair_reserve: 0,
  monthly_tax_estimate: 3392, annual_home_tax_estimate: 22200, annual_land_tax_estimate: 18500, monthly_insurance: 250,
  monthly_total_holding_cost: 59838, annual_total_holding_cost: 718056, income_burden_ratio: null,
  affordability_level: "unknown", affordability_message: "未提供收入",
  cost_breakdown: [
    { key: "loan", label: "房貸", monthly_amount: 56196 },
    { key: "management", label: "管理費", monthly_amount: 0 },
    { key: "repair_reserve", label: "修繕準備", monthly_amount: 0 },
    { key: "tax_estimate", label: "稅費", monthly_amount: 3392 },
    { key: "insurance", label: "保險", monthly_amount: 250 },
  ],
  disclaimer: "僅供試算",
};

async function installCase(page: Page) {
  await page.addInitScript(({ row }) => {
    if (!window.localStorage.getItem("proptech.savedCases.v1")) window.localStorage.setItem("proptech.savedCases.v1", JSON.stringify([row]));
    window.localStorage.setItem("proptech_onboarding_seen", "true");
    window.localStorage.setItem("proptech_onboarding_version", "2");
  }, { row: savedCase() });
}

test.beforeEach(async ({ page }) => {
  await installCase(page);
  await page.route("**/loan/calculate", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(loanResponse) }));
  await page.route("**/holding-cost/calculate", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(holdingResponse) }));
});

test("Finance route calculates loan and holding costs while keeping affordability unassessed", async ({ page }) => {
  await page.goto("/cases/finance-case/finance");

  await expect(page.getByRole("heading", { level: 1, name: "資金與持有成本" })).toBeVisible();
  await expect(page.getByTestId("finance-price-basis")).toContainText("1,850 萬元");
  await expect(page.getByTestId("finance-price-basis")).toContainText("沿用案件價格");
  await page.getByTestId("calculate-loan").click();
  await expect(page.getByTestId("loan-summary")).toContainText("NT$56,196／月");
  await expect(page.getByTestId("loan-summary")).toContainText("1,480 萬元");
  await expect(page.getByTestId("affordability-status")).toContainText("未評估（未提供月收入）");

  await page.getByTestId("calculate-holding").click();
  const breakdown = page.getByTestId("holding-breakdown");
  await expect(breakdown).toContainText("管理費");
  await expect(breakdown).toContainText("尚未估算（缺少坪數）");
  await expect(breakdown.getByRole("row", { name: /管理費/ })).not.toContainText("NT$0");
  await expect(page.getByTestId("holding-summary")).toContainText("已估算成本小計");
});

test("Finance save persists a bounded snapshot and reopens it as saved evidence", async ({ page }) => {
  await page.goto("/cases/finance-case/finance");
  await page.getByTestId("calculate-loan").click();
  await page.getByTestId("calculate-holding").click();
  await page.getByTestId("finance-save").click();
  await expect(page.getByTestId("finance-save-status")).toContainText("已儲存財務假設與摘要");

  const stored = await page.evaluate(() => JSON.parse(window.localStorage.getItem("proptech.savedCases.v1") ?? "[]")[0].data);
  expect(stored.financeEvidence.version).toBe(1);
  expect(stored.financeEvidence.loan.monthly_payment_twd).toBe(56196);
  expect(stored.financeEvidence.holding.breakdown.find((row: { key: string }) => row.key === "management").monthly_amount_twd).toBeNull();
  expect(stored.loan).toBeUndefined();
  expect(stored.holdingCost).toBeUndefined();
  expect(stored.taxOracle).toBeUndefined();
  expect(JSON.stringify(stored.financeEvidence)).not.toContain("rule_traces");
  expect(JSON.stringify(stored.financeEvidence)).not.toContain("risk_score");

  await page.reload();
  await expect(page.getByTestId("freshness-status")).toContainText("已儲存的計算摘要");
  await expect(page.getByTestId("loan-summary")).toContainText("NT$56,196／月");
});

test("holding failure remains local and preserves a valid loan result", async ({ page }) => {
  await page.unroute("**/holding-cost/calculate");
  await page.route("**/holding-cost/calculate", (route) => route.fulfill({ status: 503, body: "unavailable" }));
  await page.goto("/cases/finance-case/finance");
  await page.getByTestId("calculate-loan").click();
  await page.getByTestId("calculate-holding").click();

  await expect(page.getByTestId("holding-error")).toContainText("持有成本暫時無法完成");
  await expect(page.getByTestId("loan-summary")).toContainText("NT$56,196／月");
});

test("saved Property A finance evidence becomes stale after the case price changes", async ({ page }) => {
  await page.goto("/cases/finance-case/finance");
  await page.getByTestId("calculate-loan").click();
  await page.getByTestId("finance-save").click();
  await page.evaluate(() => {
    const key = "proptech.savedCases.v1";
    const rows = JSON.parse(window.localStorage.getItem(key) ?? "[]");
    rows[0].data.journeyContext.activePriceWan = 1900;
    rows[0].data.journeyContext.propertyContext.askingPriceWan = 1900;
    rows[0].inputSummary.propertyPrice = 1900;
    window.localStorage.setItem(key, JSON.stringify(rows));
  });
  await page.reload();

  await expect(page.getByTestId("finance-price-basis")).toContainText("1,900 萬元");
  await expect(page.getByTestId("freshness-status")).toContainText("需重新計算");
  await expect(page.getByTestId("loan-summary")).toContainText("NT$56,196／月");
});

test("Tax evidence is contextual and preliminary", async ({ page }) => {
  await page.goto("/cases/finance-case/finance");
  const tax = page.getByTestId("tax-summary");
  await expect(tax).toContainText("稅務條件初步檢查");
  await expect(tax).toContainText("需專業複核");
  await expect(tax).toContainText("不是主管機關核定、個人稅務紀錄或稅務／法律意見");
  await expect(tax).not.toContainText("TX009");
  await expect(tax).not.toContainText("deterministic");
});

test("Finance route has no document overflow at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/cases/finance-case/finance");

  await expect(page.getByTestId("finance-workspace")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  await expect(page.getByTestId("calculate-loan")).toHaveCSS("min-height", "44px");
});

test("ordinary income submits and a later edit rejects an in-flight loan response", async ({ page }) => {
  await page.goto("/cases/finance-case/finance");
  const loanForm = page.getByTestId("loan-form");
  await loanForm.getByLabel("每月收入").fill("12");
  await page.getByTestId("calculate-loan").click();
  await expect(page.getByTestId("loan-summary")).toContainText("NT$56,196／月");

  await page.unroute("**/loan/calculate");
  await page.route("**/loan/calculate", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 400));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(loanResponse) });
  });
  await page.getByTestId("calculate-loan").click();
  await loanForm.getByLabel("年利率").fill("3.1");
  await page.waitForTimeout(500);
  await expect(page.getByTestId("freshness-status")).toContainText("條件已變更");
  await expect(page.getByTestId("loan-summary")).toContainText("待重新計算");
});

test("saved non-default assumptions and finance-only area reopen without dropping loan evidence", async ({ page }) => {
  const customLoan = { ...loanResponse, annual_interest_rate: 2.65, loan_years: 25, monthly_income_wan: 15, income_burden_ratio: 0.37464 };
  const customHolding = { ...holdingResponse, input: { ...holdingResponse.input, monthly_income_wan: 15, area_ping: 26, management_fee_per_ping: 90 }, income_burden_ratio: 0.39892 };
  await page.unroute("**/loan/calculate");
  await page.unroute("**/holding-cost/calculate");
  await page.route("**/loan/calculate", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(customLoan) }));
  await page.route("**/holding-cost/calculate", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(customHolding) }));
  await page.goto("/cases/finance-case/finance");

  const loanForm = page.getByTestId("loan-form");
  await loanForm.getByLabel("年利率").fill("2.65");
  await loanForm.getByLabel("貸款年期").fill("25");
  await loanForm.getByLabel("每月收入").fill("15");
  await page.getByTestId("calculate-loan").click();
  const holdingForm = page.getByTestId("holding-form");
  await holdingForm.getByLabel("坪數").fill("26");
  await holdingForm.getByLabel("每月收入").fill("15");
  await holdingForm.getByLabel("每坪管理費").fill("90");
  await page.getByTestId("calculate-holding").click();
  await page.getByTestId("finance-save").click();
  await page.reload();

  await expect(page.getByTestId("freshness-status")).toContainText("已儲存的計算摘要");
  await expect(page.getByTestId("loan-form").getByLabel("年利率")).toHaveValue("2.65");
  await expect(page.getByTestId("loan-form").getByLabel("貸款年期")).toHaveValue("25");
  await expect(page.getByTestId("holding-form").getByLabel("坪數")).toHaveValue("26");
  await expect(page.getByTestId("holding-form").getByLabel("每坪管理費")).toHaveValue("90");
  await page.getByTestId("calculate-holding").click();
  await expect(page.getByTestId("loan-summary")).toContainText("NT$56,196／月");
});
