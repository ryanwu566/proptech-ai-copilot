from pathlib import Path


ROOT = Path(__file__).parents[1]
COMPETITION = ROOT / "frontend_next/components/competition-taxoracle-demo.tsx"
PRESENTATION = ROOT / "frontend_next/lib/taxoracle-presentation.ts"
HOLDING = ROOT / "frontend_next/components/data-visualization/holding-cost-visual-panel.tsx"
CHART = ROOT / "frontend_next/components/data-visualization/holding-cost-breakdown-chart.tsx"


def test_central_presentation_contract_covers_all_locales_and_canonical_outcomes():
    source = PRESENTATION.read_text(encoding="utf-8")
    for locale in ('"zh-TW"', "en:", "ja:", "ko:"):
        assert locale in source
    for key in ("eligible", "not_eligible", "manual_review", "formatOutcome", "formatCurrency"):
        assert key in source


def test_customer_demo_does_not_render_internal_keys_or_raw_result_dump():
    source = COMPETITION.read_text(encoding="utf-8")
    assert "Object.entries(taxCase)" not in source
    assert "key}=" not in source
    assert "Risk score:" not in source
    assert "<pre" not in source
    assert "formatOutcome" in source
    assert "DetailDisclosure" in source


def test_holding_cost_has_currency_period_and_preserves_server_result():
    for path in (COMPETITION, HOLDING, CHART):
        source = path.read_text(encoding="utf-8")
        assert "formatCurrency" in source
    source = COMPETITION.read_text(encoding="utf-8")
    assert "holdingMeaning" in source
    assert "holdingMonthly" in source
    assert "holdingAnnual" in source


def test_primary_ui_never_labels_numeric_result_as_risk_score():
    for path in (COMPETITION, HOLDING):
        source = path.read_text(encoding="utf-8")
        assert "Risk score:" not in source
