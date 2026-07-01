"""Contracts for Property Case Financial Decision Lab v1."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINANCIALS = ROOT / "frontend_next/lib/property-case-financials.ts"
COMMAND_CENTER = ROOT / "frontend_next/components/property-case-command-center.tsx"
CASE_MODEL = ROOT / "frontend_next/lib/property-case.ts"
VIEWING_DECISION_PANEL = ROOT / "frontend_next/components/viewing-decision-panel.tsx"
DECISION_REPORT = ROOT / "frontend_next/components/decision-report.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_financial_lab_static_boundaries() -> None:
    financials = read(FINANCIALS)
    command_center = read(COMMAND_CENTER)
    combined = financials + command_center

    for text in (
        "FundingMode",
        "loan_amount",
        "down_payment",
        "monthlyResidual",
        "postPurchaseCash",
        "ltvRatio",
        "userValueGap",
        "buildPropertyCaseFinancialScenarios",
    ):
        assert text in combined

    for forbidden in (
        "fetch(",
        "api.",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "URLSearchParams",
        "location.search",
        "/market-insights",
        "/commute",
        "/terrain",
    ):
        assert forbidden not in command_center


def test_financial_lab_ui_and_print_summary_exist() -> None:
    source = read(COMMAND_CENTER)

    for text in (
        "財務資料與決策試算",
        "總承諾金額",
        "每月房貸",
        "購屋後現金",
        "情境比較",
        "不代表核貸、估價、稅務、法律、投資或購買建議",
        "財務試算：月付",
    ):
        assert text in source


def test_case_model_round_trips_financial_lab_fields_without_raw_data() -> None:
    source = read(CASE_MODEL)

    for field in (
        "funding_mode",
        "funding_value",
        "estimated_buyer_costs",
        "renovation_reserve",
        "available_liquid_cash",
        "monthly_ownership_reserve",
        "other_monthly_debt",
    ):
        assert field in source

    for forbidden in ("raw payload", "provider raw", "token", "secret", "database URL"):
        assert forbidden not in source


def test_financial_helper_runtime_rules_with_node() -> None:
    script = r"""
const vm = require('vm');
const fs = require('fs');
const ts = require('./frontend_next/node_modules/typescript');
const source = fs.readFileSync('frontend_next/lib/property-case-financials.ts', 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const sandbox = { console, Number, Object, String, Map, Set, exports: {}, require };
vm.createContext(sandbox);
vm.runInContext(js, sandbox);
const { buildPropertyCaseFinancialAnalysis, buildPropertyCaseFinancialScenarios } = sandbox.exports;
const base = {
  listingPrice: 2000,
  userEstimatedValue: 1900,
  fundingMode: 'loan_amount',
  fundingValue: 1600,
  annualInterestRate: 0,
  loanYears: 20,
  estimatedBuyerCosts: 80,
  renovationReserve: 120,
  availableLiquidCash: 650,
  monthlyHouseholdIncome: 160000,
  monthlyFixedObligations: 30000,
  monthlyOwnershipReserve: 10000,
};
const result = buildPropertyCaseFinancialAnalysis(base);
if (result.loanAmount.value !== 1600) throw new Error('loan amount mode failed');
if (result.downPayment.value !== 400) throw new Error('down payment derivation failed');
if (result.totalCommitment.value !== 2200) throw new Error('total commitment failed');
if (result.cashNeeded.value !== 600) throw new Error('cash needed failed');
if (result.monthlyPayment.value !== Math.round(1600 * 10000 / (20 * 12))) throw new Error('zero-rate payment failed');
if (result.monthlyBurden.value !== result.monthlyPayment.value + 10000) throw new Error('monthly burden failed');
if (result.monthlyResidual.value !== 160000 - 30000 - result.monthlyBurden.value) throw new Error('monthly residual failed');
if (result.postPurchaseCash.value !== 50) throw new Error('post purchase cash failed');
if (Math.round(result.ltvRatio.value * 100) !== 80) throw new Error('ltv failed');
if (result.userValueGap.value !== 100) throw new Error('user value gap failed');

const downPaymentMode = buildPropertyCaseFinancialAnalysis({ ...base, fundingMode: 'down_payment', fundingValue: 500 });
if (downPaymentMode.downPayment.value !== 500 || downPaymentMode.loanAmount.value !== 1500) throw new Error('down payment mode failed');

const tooHigh = buildPropertyCaseFinancialAnalysis({ ...base, fundingValue: 3000 });
if (tooHigh.downPayment.value !== null || tooHigh.loanAmount.value !== null) throw new Error('funding over price should be unavailable');
if (!tooHigh.warnings.length) throw new Error('funding warning missing');

const incomplete = buildPropertyCaseFinancialAnalysis({ ...base, estimatedBuyerCosts: null });
if (incomplete.cashNeeded.status === 'available') throw new Error('missing costs should not become zero');

const scenarios = buildPropertyCaseFinancialScenarios(base, [
  { scenarioName: 'Scenario A', optionalListingPrice: 2100, optionalAnnualInterestRate: null, optionalEstimatedBuyerCosts: null, optionalRenovationReserve: null, optionalMonthlyHouseholdIncome: null, optionalMonthlyFixedObligations: null, optionalMonthlyOwnershipReserve: null },
]);
if (scenarios.length !== 1) throw new Error('scenario count failed');
if (scenarios[0].listingPrice.value !== 2100) throw new Error('scenario listing override failed');
if (scenarios[0].monthlyHouseholdIncome === 0) throw new Error('unexpected fake scenario data');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr


def test_viewing_decision_files_not_rewired_to_financial_lab() -> None:
    combined = read(VIEWING_DECISION_PANEL) + read(DECISION_REPORT)

    assert "property-case-financials" not in combined
    assert "Financial Decision Lab" not in combined
