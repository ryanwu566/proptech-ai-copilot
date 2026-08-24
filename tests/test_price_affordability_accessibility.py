"""Accessibility and responsive contracts for Phase 3 journey stages."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE_DIR = ROOT / "frontend_next/components/guided-journey"


def read(name: str) -> str:
    return (STAGE_DIR / name).read_text(encoding="utf-8")


def test_phase3_stages_use_headings_and_native_controls() -> None:
    price = read("price-decision-stage.tsx")
    affordability = read("affordability-decision-stage.tsx")
    selector = read("affordability-tool-selector.tsx")
    for source in (price, affordability, selector):
        assert 'type="button"' in source
        assert "aria-labelledby" in source or "aria-label" in source
        assert "min-w-0" in source
    assert "hidden={activeSecondaryTool !== \"holding\"}" in affordability
    assert "aria-hidden={activeSecondaryTool !== \"holding\"}" in affordability
    assert "hidden={activeSecondaryTool !== \"tax\"}" in affordability
    assert "aria-hidden={activeSecondaryTool !== \"tax\"}" in affordability


def test_price_workspace_and_missing_data_have_accessible_structure() -> None:
    price = read("price-decision-stage.tsx")
    assert 'aria-labelledby="price-decision-workspace-heading"' in price
    assert 'id="price-decision-workspace-heading"' in price
    assert 'data-testid="price-decision-workspace"' in price
    assert "JourneyMissingDataPanel" in price
    assert 't("journey.price.title")' in price
    assert 'onClick={onContinueToAffordability}' in price
    assert 'type="button"' in price
