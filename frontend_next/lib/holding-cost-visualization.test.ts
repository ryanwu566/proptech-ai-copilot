import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { buildHoldingCostVisualModel } from "./holding-cost-visualization.ts";

test("holding-cost summary uses canonical monthly and annual TWD presentation", () => {
  const result = {
    input: { property_price_wan: 1_850, loan_monthly_payment: 60_752, monthly_income_wan: null, area_ping: null, management_fee_per_ping: 0, repair_reserve_per_ping: 0, annual_home_tax_rate: 0, annual_land_tax_rate: 0, annual_insurance: 0, include_tax_estimate: true },
    property_price_wan: 1_850,
    loan_monthly_payment: 60_752,
    monthly_management_fee: 0,
    monthly_repair_reserve: 0,
    monthly_tax_estimate: 0,
    annual_home_tax_estimate: 0,
    annual_land_tax_estimate: 0,
    monthly_insurance: 0,
    monthly_total_holding_cost: 60_752,
    annual_total_holding_cost: 729_024,
    income_burden_ratio: null,
    affordability_level: "unknown",
    affordability_message: "未提供月收入",
    cost_breakdown: [{ key: "loan", label: "房貸", monthly_amount: 60_752 }],
    disclaimer: "試算",
  } as const;

  const model = buildHoldingCostVisualModel(result as never);
  assert.match(model.summary, /NT\$60,752／月/);
  assert.match(model.summary, /NT\$729,024／年/);
  assert.equal(model.evidence.find((item) => item.key === "loan_payment")?.value, "NT$60,752／月");
});

test("a legitimate zero holding-cost result remains available instead of looking missing", () => {
  const zeroResult = {
    input: { property_price_wan: 1_850, loan_monthly_payment: 0, monthly_income_wan: 10, area_ping: 26, management_fee_per_ping: 0, repair_reserve_per_ping: 0, annual_home_tax_rate: 0, annual_land_tax_rate: 0, annual_insurance: 0, include_tax_estimate: false },
    property_price_wan: 1_850,
    loan_monthly_payment: 0,
    monthly_management_fee: 0,
    monthly_repair_reserve: 0,
    monthly_tax_estimate: 0,
    annual_home_tax_estimate: 0,
    annual_land_tax_estimate: 0,
    monthly_insurance: 0,
    monthly_total_holding_cost: 0,
    annual_total_holding_cost: 0,
    income_burden_ratio: 0,
    affordability_level: "comfortable",
    affordability_message: "依目前輸入為零",
    cost_breakdown: [{ key: "loan", label: "房貸", monthly_amount: 0 }],
    disclaimer: "試算",
  };

  const model = buildHoldingCostVisualModel(zeroResult as never);
  assert.equal(model.state, "available");
  assert.match(model.summary, /NT\$0／月/);
  assert.equal(model.breakdown[0]?.percentage, null);
});
