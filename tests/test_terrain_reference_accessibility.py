"""Accessibility and privacy checks for terrain reference presentation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = (ROOT / "frontend_next/components/terrain-risk-analysis.tsx").read_text(encoding="utf-8")
MATRIX = (ROOT / "frontend_next/components/data-visualization/terrain-status-matrix.tsx").read_text(encoding="utf-8")


def test_reference_control_is_keyboard_accessible_and_stateful() -> None:
    assert 'type="button"' in COMPONENT
    assert "disabled={!evidence.attachable}" in COMPONENT
    assert "focus:ring" in COMPONENT
    assert "風險資料來源與限制" in COMPONENT
    assert "各圖層獨立呈現" in MATRIX


def test_reference_ui_does_not_render_private_coordinates_or_raw_payload() -> None:
    rendered = COMPONENT.split("function TerrainRiskResults", 1)[1]
    for forbidden in ("raw_payload", "stack_trace", "SQL", "latitude", "longitude", "token", "secret"):
        assert forbidden not in rendered
        assert forbidden not in MATRIX
