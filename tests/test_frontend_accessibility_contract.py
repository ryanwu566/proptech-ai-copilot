from pathlib import Path


ROOT = Path(__file__).parents[1]
VISUAL_DIR = ROOT / "frontend_next" / "components" / "data-visualization"


def test_visual_charts_expose_accessible_names_and_text_summary() -> None:
    trend = (VISUAL_DIR / "trend-line-chart.tsx").read_text(encoding="utf-8")
    volume = (VISUAL_DIR / "volume-bar-chart.tsx").read_text(encoding="utf-8")
    for source in [trend, volume]:
        assert 'role="img"' in source
        assert "aria-label" in source
        assert "<title>" in source
        assert "<desc>" in source
        assert "textSummary" in trend or "文字摘要" in volume


def test_evidence_details_and_status_are_keyboard_and_screen_reader_friendly() -> None:
    details = (VISUAL_DIR / "evidence-details.tsx").read_text(encoding="utf-8")
    badge = (VISUAL_DIR / "data-status-badge.tsx").read_text(encoding="utf-8")
    assert "<details" in details
    assert "<summary" in details
    assert 'role="status"' in badge
    assert "aria-label" in badge
    assert "hover" not in details.lower()


def test_metric_and_chart_layouts_keep_mobile_safe_minimums() -> None:
    trend = (VISUAL_DIR / "trend-line-chart.tsx").read_text(encoding="utf-8")
    volume = (VISUAL_DIR / "volume-bar-chart.tsx").read_text(encoding="utf-8")
    empty = (VISUAL_DIR / "chart-empty-state.tsx").read_text(encoding="utf-8")
    assert "min-h-[320px]" in trend
    assert "min-h-[320px]" in volume
    assert "min-h-[320px]" in empty
