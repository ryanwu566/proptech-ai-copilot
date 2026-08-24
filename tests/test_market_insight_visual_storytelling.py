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
    assert "尚無可用資料" in source or "viz.dataMetricNoData" in source
    assert "value !== null" in source
    assert "value || 0" not in source
    assert "value ?? 0" not in source
    assert "Number(value || 0)" not in source
    assert "parseFloat(value) || 0" not in source
    assert "尚無可用資料" in helper or "no_data" in helper


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
        assert "marketStateHasEvidence(status)" in source
        assert "data.length === 0" in source
        assert "role=\"img\"" in source
        assert "<title>" in source
        assert "<desc>" in source
        assert "tabIndex={0}" in source
        assert "recharts" not in source.lower()
        assert "chart.js" not in source.lower()
        assert "overflow-x-auto" not in source
        assert "min-w-[560px]" not in source
    helper = VISUAL_HELPER.read_text(encoding="utf-8")
    assert "selectChartLabelIndexes" in helper


def test_market_page_uses_conclusion_first_visual_disclosure() -> None:
    page = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
    section = page.split("function MarketInsight(", 1)[1].split("function LegacyMarketInsightOriginal", 1)[0]
    assert "buildMarketInsightVisualModel" in section
    assert "MarketInsightVisualResult" in section
    assert "if (!result) return null" not in section
    assert "resultState" not in section
    assert "as MarketResult" not in section
    assert "canonicalCounty" in section
    assert "canonicalDistrict" in section
    assert "setResult(undefined)" in section
    assert "querying" in section
    assert "MarketInsightEvidencePanel" in page
    visual_result = page.split("function MarketInsightVisualResult", 1)[1].split("function AegisCredit", 1)[0]
    assert "DataMetricCard" not in visual_result
    assert "TrendLineChart" in page
    assert "VolumeBarChart" in page
    assert "EvidenceSummary" in page
    assert "EvidenceDetails" in page


def test_non_available_states_keep_evidence_disclosure() -> None:
    page = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
    section = page.split("function MarketInsight(", 1)[1].split("function LegacyMarketInsightOriginal", 1)[0]
    helper = VISUAL_HELPER.read_text(encoding="utf-8")
    assert "EvidenceSummary items={visualModel.evidence}" in section
    assert "EvidenceDetails items={visualModel.evidence}" in section
    assert '"caveat"' in helper
    assert '"disclaimer"' in helper


def test_market_analysis_contract_is_deterministic_and_localized() -> None:
    helper = VISUAL_HELPER.read_text(encoding="utf-8")
    copy = (ROOT / "frontend_next" / "lib" / "market-insight-copy.ts").read_text(encoding="utf-8")
    page = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "buildMarketTrendStats" in helper
    assert ".slice(0, 6)" in helper
    assert "previous.average_unit_price > 0" in helper
    assert "Date(" not in helper
    assert "Math.random" not in helper
    for locale in ['"zh-TW"', "en:", "ja:", "ko:"]:
        assert locale in copy
    for state in ['"initial"', '"loading"', '"available"', '"no_data"', '"unavailable"', '"network_error"']:
        assert state in page
    assert "market_request_timeout" in page
    assert "market_request_connection_failed" in page
    assert "market_request_cors_failed" in page
    assert "forecast" not in helper.lower()
    assert "prediction" not in helper.lower()
