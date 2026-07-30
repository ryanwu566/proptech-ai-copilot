"""Static accessibility contracts for the Phase 2 workspace."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx",
    ROOT / "frontend_next/components/guided-journey/journey-property-context-header.tsx",
    ROOT / "frontend_next/components/guided-journey/location-market-status-strip.tsx",
    ROOT / "frontend_next/components/guided-journey/location-market-tool-selector.tsx",
    ROOT / "frontend_next/components/guided-journey/location-market-snapshot.tsx",
    ROOT / "frontend_next/components/data-visualization/amenity-category-chart.tsx",
    ROOT / "frontend_next/components/data-visualization/terrain-status-matrix.tsx",
]


def read_all() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FILES)


def test_controls_have_native_button_semantics_and_focus() -> None:
    source = read_all()
    assert source.count('type="button"') >= 5
    assert "focus:ring-2" in source
    assert "aria-pressed" in source
    assert "aria-labelledby" in source


def test_hidden_secondary_tools_are_not_exposed_to_assistive_technology() -> None:
    source = read_all()
    assert 'hidden={activeTool !== "commute"}' in source
    assert 'aria-hidden={activeTool !== "commute"}' in source
    assert 'hidden={activeTool !== "terrain"}' in source
    assert 'aria-hidden={activeTool !== "terrain"}' in source
    assert 'hidden={activeTool !== "market"}' in source
    assert 'aria-hidden={activeTool !== "market"}' in source
    assert "autoFocus" not in source
    assert "keyboard trap" not in source.lower()


def test_charts_have_text_alternatives_and_mobile_safe_layout() -> None:
    source = read_all()
    assert 'role="img"' in source
    assert 't("evidence.summaryDescription")' in source
    assert "overflow-x-auto" not in source
    assert "min-w-[560px]" not in source
    assert "min-w-[620px]" not in source
