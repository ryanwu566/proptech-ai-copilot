from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VISUAL_HELPER = ROOT / "frontend_next" / "lib" / "market-insight-visualization.ts"
EVIDENCE_PANEL = ROOT / "frontend_next" / "components" / "data-visualization" / "market-insight-evidence-panel.tsx"


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_direct_query_metric_contract_keeps_units_and_sources_distinct() -> None:
    source = read_utf8(VISUAL_HELPER)
    assert "MARKET_METRIC_PRESENTATION_CONTRACT" in source
    assert 'sourceField: "average_unit_price"' in source
    assert 'unit: "wan_ntd_per_ping"' in source
    assert 'sourceField: "median_unit_price_ntd_sqm"' in source
    assert 'unit: "ntd_per_square_meter"' in source
    assert 'converted: false' in source
    assert 'sourceFields: ["transaction_count", "transaction_volume"]' in source
    assert 'periodScope: "result.period"' in source


def test_evidence_panel_only_renders_supported_metrics_and_metadata() -> None:
    source = read_utf8(EVIDENCE_PANEL)
    assert 'averageDirect: "平均單價（萬元／坪）"' in source
    assert "getMarketMetricPresentation(result)" in source
    assert "presentation.averageUnitPrice !== null" in source
    assert "presentation.medianUnitPrice !== null" in source
    assert "presentation.medianTotalPrice !== null" in source
    assert "presentation.inclusionCount !== null" in source
    assert "presentation.exclusionCount !== null" in source
    assert "presentation.sampleStatus &&" in source
    assert "presentation.freshnessStatus &&" in source
    assert "hasDistributions &&" in source
    assert '|| "unknown"' not in source


def test_history_uses_api_points_and_explicit_units() -> None:
    source = read_utf8(EVIDENCE_PANEL)
    assert "model.history.map" in source
    assert "point.average_unit_price" in source
    assert "point.transaction_count" in source
    assert 'historyAverage: "平均單價（萬元／坪）"' in source
    assert 'historyCount: "交易筆數（筆）"' in source


def test_market_page_does_not_repeat_generic_metrics_or_unknown_sample() -> None:
    page = read_utf8(ROOT / "frontend_next" / "app" / "page.tsx")
    section = page.split("function MarketInsightVisualResult", 1)[1].split("function AegisCredit", 1)[0]
    assert "DataMetricCard" not in section
    assert 'result.sample_status ?? "unknown"' not in section
    assert 'model.freshness !== "unknown"' in section


def test_presentation_does_not_synthesize_advanced_metrics() -> None:
    source = read_utf8(VISUAL_HELPER)
    forbidden = (
        "medianUnitPrice: result.average_unit_price",
        "medianTotalPrice: result.average_unit_price",
        "inclusionCount: result.transaction_count",
        "exclusionCount: 0",
        'sampleStatus: "sufficient"',
    )
    for expression in forbidden:
        assert expression not in source
