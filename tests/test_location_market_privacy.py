"""Static privacy contracts for the runtime-only location market workspace."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = list((ROOT / "frontend_next/components/guided-journey").glob("location-market-*.tsx")) + [
    ROOT / "frontend_next/components/data-visualization/amenity-category-chart.tsx",
    ROOT / "frontend_next/components/data-visualization/terrain-status-matrix.tsx",
    ROOT / "frontend_next/lib/location-market-journey.ts",
]


def test_phase_two_components_do_not_add_client_storage_or_url_state() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in FILES)
    for forbidden in ("localStorage", "sessionStorage", "URLSearchParams", "location.search", "location.hash", "document.cookie", "Date.now", "fetch("):
        assert forbidden not in source


def test_context_and_visual_outputs_exclude_sensitive_provider_fields() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in FILES)
    for forbidden in ("latitude", "longitude", "coordinates", "raw_payload", "raw provider payload", "SQL", "credential", "token", "stack trace", "request body"):
        assert forbidden not in source


def test_explicit_transfer_language_is_present_without_automatic_analysis() -> None:
    stage = (ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx").read_text(encoding="utf-8")
    assert "按下後才會開啟對應分析" in (ROOT / "frontend_next/components/guided-journey/location-market-tool-selector.tsx").read_text(encoding="utf-8")
    assert "只切換到價格分析" in stage
    assert "自動影響估價" in stage
