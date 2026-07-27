from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
VISUAL_DIR = FRONTEND / "components" / "data-visualization"


def test_valuation_visual_model_reuses_trust_boundary_and_blocks_invalid_values() -> None:
    helper = (FRONTEND / "lib" / "valuation-visualization.ts").read_text(encoding="utf-8")
    state = (FRONTEND / "lib" / "valuation-result-state.ts").read_text(encoding="utf-8")

    assert "getValuationDisplayState" in helper
    assert "getValuationTrendDisplayState" in helper
    assert 'display.kind === "available"' in helper
    assert "display.actionable" in helper
    assert "Number.isFinite" in helper
    assert "monthly_series" in helper
    assert "forecast" not in helper.lower()
    assert 'kind: "available"' in state
    assert "?? 0" not in helper
    assert "|| 0" not in helper


def test_valuation_charts_are_accessible_responsive_and_dependency_free() -> None:
    files = [
        VISUAL_DIR / "valuation-price-range-band.tsx",
        VISUAL_DIR / "valuation-distribution-chart.tsx",
        VISUAL_DIR / "valuation-trend-chart.tsx",
    ]
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert 'role="img"' in source
        assert "<title>" in source
        assert "<desc>" in source
        assert "h-auto w-full" in source
        assert "max-w-full" in source
        assert "overflow-x-auto" not in source
        assert "min-w-[560px]" not in source
        assert "recharts" not in source.lower()
        assert "chart.js" not in source.lower()


def test_valuation_evidence_is_compact_and_collapsed() -> None:
    panel = (VISUAL_DIR / "valuation-visual-panel.tsx").read_text(encoding="utf-8")
    evidence = (VISUAL_DIR / "valuation-evidence-summary.tsx").read_text(encoding="utf-8")
    helper = (FRONTEND / "lib" / "valuation-visualization.ts").read_text(encoding="utf-8")
    page = (FRONTEND / "app" / "page.tsx").read_text(encoding="utf-8")

    assert "ValuationEvidenceSummary" in panel
    assert "<details" in evidence
    assert "<summary" in evidence
    assert "methodology" in helper
    assert "official_records_count" in helper
    assert "ValuationVisualPanel" in page
    assert "ValuationResultBoundary" in page
    assert 'title="查看完整可比成交"' in page


def test_valuation_visuals_do_not_add_storage_or_sensitive_output() -> None:
    paths = [
        FRONTEND / "lib" / "valuation-visualization.ts",
        VISUAL_DIR / "valuation-visual-panel.tsx",
        VISUAL_DIR / "valuation-evidence-summary.tsx",
        VISUAL_DIR / "valuation-price-range-band.tsx",
        VISUAL_DIR / "valuation-distribution-chart.tsx",
        VISUAL_DIR / "valuation-trend-chart.tsx",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for forbidden in (
        "localstorage",
        "sessionstorage",
        "document.cookie",
        "urlsearchparams",
        "raw_payload",
        "provider_payload",
        "latitude",
        "longitude",
        "station_uid",
        "token",
        "sql",
    ):
        assert forbidden not in combined
