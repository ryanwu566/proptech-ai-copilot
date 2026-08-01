from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_utf8(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_market_insight_snapshot_contract_is_safe_and_optional() -> None:
    source = read_utf8("frontend_next/lib/market-insight-snapshot.ts")
    assert "source_release_id" in source
    assert "generated_at" in source
    assert "raw" not in source.lower()
    assert "address" not in source.lower()
    assert "transaction_id" not in source


def test_market_evidence_panel_has_print_and_accessible_distribution_surfaces() -> None:
    source = read_utf8("frontend_next/components/data-visualization/market-insight-evidence-panel.tsx")
    for token in ("medianTotal", "periodChange", "yearOverYearChange", "priceDistribution", "buildingTypeDistribution", "ageBandDistribution", "data-testid=\"market-insight-print-report\"", "window.print", "sr-only"):
        assert token in source


def test_market_visual_model_does_not_invent_distribution_values() -> None:
    source = read_utf8("frontend_next/lib/market-insight-visualization.ts")
    assert "sanitizeMarketDistribution" in source
    assert "Array.isArray(result[field])" in source
    assert "return []" in source
