"""Static contracts for the rule-based risk summary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIB = (ROOT / "frontend_next" / "lib" / "risk-summary.ts").read_text(encoding="utf-8")
PANEL = (ROOT / "frontend_next" / "components" / "risk-summary-panel.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
HTML = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next" / "lib" / "runtime-copy.ts").read_text(encoding="utf-8")


def test_risk_summary_has_explicit_rule_based_signals_and_weights() -> None:
    for signal in ('"green"', '"yellow"', '"red"', '"unknown"'):
        assert signal in LIB
    for threshold in ("score >= 75", "score >= 55", "valuationScore * 0.25", "priceScore * 0.25", "loanScore * 0.15", "holdingScore * 0.15", "locationScore * 0.15", "completenessScore * 0.05"):
        assert threshold in LIB
    assert "completedCoreModules >= 2" in LIB
    assert "api." not in LIB


def test_price_and_burden_rules_are_explicit() -> None:
    # (a) Business logic rules remain intact in risk-summary.ts
    for rule in ("valuation.price_range.low * 0.95", "valuation.price_range.high * 1.05", "0.3", "0.4", "0.35", "0.45", "location.location_score >= 75", "location.location_score < 55"):
        assert rule in LIB
    for status in ("undervalued", "reasonable", "overpriced"):
        assert status in LIB
    assert "supports_price_reasonableness" in LIB

    # (a) risk-summary.ts uses riskSummary.* semantic keys for display strings
    risk_summary_keys_in_lib = [
        "riskSummary.priceUnknown", "riskSummary.priceUndervalued",
        "riskSummary.priceOverpriced", "riskSummary.priceReasonable",
        "riskSummary.burdenHealthy", "riskSummary.burdenCaution", "riskSummary.burdenHigh",
        "riskSummary.locationGood", "riskSummary.locationMedium", "riskSummary.locationLow",
        "riskSummary.titleLoan", "riskSummary.titleHolding", "riskSummary.titleLocation",
        "riskSummary.titlePrice", "riskSummary.titleConfidence",
        "riskSummary.missingValuation", "riskSummary.missingPrice",
        "riskSummary.missingLoan", "riskSummary.missingHolding",
        "riskSummary.missingLocation", "riskSummary.missingTrend",
        "riskSummary.nextGreen", "riskSummary.nextYellow", "riskSummary.nextRed",
    ]
    for key in risk_summary_keys_in_lib:
        assert key in LIB, f"risk-summary.ts must reference semantic key {key}"

    # (b) runtime-copy.ts has all required riskSummary.* keys in all 4 locales
    required_copy_keys = [
        "riskSummary.labelGreen", "riskSummary.labelYellow", "riskSummary.labelRed", "riskSummary.labelUnknown",
        "riskSummary.suggestionGreen", "riskSummary.suggestionYellow", "riskSummary.suggestionRed", "riskSummary.suggestionUnknown",
        "riskSummary.priceUnknown", "riskSummary.priceUndervalued", "riskSummary.priceOverpriced", "riskSummary.priceReasonable",
        "riskSummary.priceUnknownExplanation", "riskSummary.priceUndervaluedExplanation", "riskSummary.priceOverpricedExplanation", "riskSummary.priceReasonableExplanation",
        "riskSummary.burdenHealthy", "riskSummary.burdenCaution", "riskSummary.burdenHigh",
        "riskSummary.locationGood", "riskSummary.locationMedium", "riskSummary.locationLow",
        "riskSummary.riskFacilityWarning",
        "riskSummary.nextGreen", "riskSummary.nextYellow", "riskSummary.nextRed", "riskSummary.nextOverpriced", "riskSummary.nextLocation",
    ]
    for key in required_copy_keys:
        occurrences = RUNTIME_COPY.count(f'"{key}"')
        assert occurrences >= 4, f"riskSummary key {key} must appear in all 4 locales (found {occurrences})"


def test_risk_panel_and_workspace_integration_exist() -> None:
    for text in ("risk.heading", "risk.priceReasonableness", "risk.positiveFactors", "risk.riskFactors", "risk.missingChecks", "risk.nextSteps"):
        assert text in PANEL
    assert "RiskSummaryPanel" in WORKSPACE
    assert "buildRiskSummary" in WORKSPACE
    assert "min-w-0" in PANEL
    assert "overflow-hidden" in PANEL
    assert 'id="risk-summary"' in PANEL


def test_html_summary_contains_risk_summary_and_disclaimer() -> None:
    for text in ("風險總評 / 開價合理性", "補查清單", "下一步建議", "主要加分", "主要風險", "不代表正式鑑價、銀行核貸或投資建議"):
        assert text in HTML


def test_risk_summary_does_not_claim_black_box_or_formal_advice() -> None:
    combined = f"{LIB}\n{PANEL}"
    assert "black-box" not in combined.lower()
    assert "正式鑑價、銀行核貸或投資建議" in PANEL or 'copy("risk.boundary")' in PANEL
