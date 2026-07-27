from pathlib import Path


ROOT = Path(__file__).parents[1]
VISUAL_HELPER = ROOT / "frontend_next" / "lib" / "market-insight-visualization.ts"
VISUAL_DIR = ROOT / "frontend_next" / "components" / "data-visualization"


def test_visual_model_is_pure_and_filters_invalid_history() -> None:
    source = VISUAL_HELPER.read_text(encoding="utf-8")
    assert "buildMarketInsightVisualModel" in source
    assert "sanitizeMarketHistory" in source
    assert "Number.isFinite" in source
    assert "point.average_unit_price" in source
    assert "point.transaction_count" in source
    assert "if (!period" in source
    assert "Date.now" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source


def test_metric_card_never_falls_back_to_zero() -> None:
    source = (VISUAL_DIR / "data-metric-card.tsx").read_text(encoding="utf-8")
    helper = VISUAL_HELPER.read_text(encoding="utf-8")
    assert "尚無可用資料" in source
    assert "value !== null" in source
    assert "value || 0" not in source
    assert "value ?? 0" not in source
    assert "Number(value || 0)" not in source
    assert "parseFloat(value) || 0" not in source
    assert "尚無可用資料" in helper


def test_visual_components_use_safe_evidence_allowlist() -> None:
    helper = VISUAL_HELPER.read_text(encoding="utf-8")
    details = (VISUAL_DIR / "evidence-details.tsx").read_text(encoding="utf-8")
    allowed = ["source_name", "source_updated_at", "period", "transaction_count", "record_count", "coverage_status", "data_status", "aggregation_method"]
    for field in allowed:
        assert field in helper
    for forbidden in ["raw_payload", "database_url", "latitude", "longitude", "station_uid", "token", "sql", "stack_trace"]:
        assert forbidden not in helper.lower()
        assert forbidden not in details.lower()
    assert "<details" in details
    assert "<summary" in details


def test_charts_have_safe_empty_states_and_no_chart_dependency() -> None:
    trend = (VISUAL_DIR / "trend-line-chart.tsx").read_text(encoding="utf-8")
    volume = (VISUAL_DIR / "volume-bar-chart.tsx").read_text(encoding="utf-8")
    for source in [trend, volume]:
        assert "status !== \"available\"" in source
        assert "data.length < 2" in source
        assert "role=\"img\"" in source
        assert "<title>" in source
        assert "<desc>" in source
        assert "recharts" not in source.lower()
        assert "chart.js" not in source.lower()


def test_market_page_uses_conclusion_first_visual_disclosure() -> None:
    page = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
    section = page.split("function MarketInsight(", 1)[1].split("function LegacyTextMarketInsight", 1)[0]
    assert "buildMarketInsightVisualModel" in section
    assert "MarketInsightVisualResult" in section
    assert "DataMetricCard" in page
    assert "TrendLineChart" in page
    assert "VolumeBarChart" in page
    assert "EvidenceSummary" in page
    assert "EvidenceDetails" in page
