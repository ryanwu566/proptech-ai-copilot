"""Privacy and runtime-only contracts for Phase 3 state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next/lib/price-affordability-journey.ts").read_text(encoding="utf-8")
STAGE_DIR = ROOT / "frontend_next/components/guided-journey"


def test_price_affordability_helper_is_pure_and_runtime_only() -> None:
    for forbidden in ("fetch(", "api.", "localStorage", "sessionStorage", "document.cookie", "URLSearchParams", "Date.now", "latitude", "longitude", "raw payload", "provider", "token", "credential", "sql"):
        assert forbidden not in HELPER.lower()


def test_phase3_components_do_not_persist_or_expose_provider_details() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in STAGE_DIR.glob("price-*tsx"))
    source += "\n" + (STAGE_DIR / "affordability-decision-stage.tsx").read_text(encoding="utf-8")
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "URLSearchParams", "raw payload", "provider raw", "coordinates", "token", "secret", "stack trace", "SQL"):
        assert forbidden.lower() not in source.lower()


def test_missing_data_is_not_rendered_as_zero_or_success() -> None:
    missing = (STAGE_DIR / "journey-missing-data-panel.tsx").read_text(encoding="utf-8")
    snapshot = (STAGE_DIR / "affordability-decision-snapshot.tsx").read_text(encoding="utf-8")
    assert "title" in missing
    assert 't("state.partial.heading")' in (STAGE_DIR / "price-decision-stage.tsx").read_text(encoding="utf-8")
    assert 't("state.partial.heading")' in (STAGE_DIR / "affordability-decision-stage.tsx").read_text(encoding="utf-8")
    assert '|| 0' not in snapshot
    assert '|| 0' not in snapshot
