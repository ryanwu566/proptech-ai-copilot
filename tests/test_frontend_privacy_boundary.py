"""Static privacy contracts for release readiness and market visuals."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readiness_ui_has_no_storage_or_network_side_effects() -> None:
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "frontend_next/lib/release-readiness.ts",
            "frontend_next/components/release-readiness-notice.tsx",
        )
    )
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "URLSearchParams", "fetch(", "process.env"):
        assert forbidden not in source


def test_inventory_names_storage_and_sensitive_data_boundaries() -> None:
    inventory = (ROOT / "docs/privacy_and_storage_inventory.md").read_text(encoding="utf-8")
    for marker in ("localStorage", "sessionStorage", "coordinates", "provider payload", "proptech:saved-cases", "share"):
        assert marker in inventory
    assert "secret" in inventory.lower()


def test_visual_layer_does_not_expose_raw_provider_or_location_data() -> None:
    files = [
        ROOT / "frontend_next" / "lib" / "market-insight-visualization.ts",
        *sorted((ROOT / "frontend_next" / "components" / "data-visualization").glob("*.tsx")),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files).lower()
    for forbidden in ["raw_payload", "provider_payload", "latitude", "longitude", "stationuid", "station_uid", "token", "credential", "stack trace", "sql"]:
        assert forbidden not in combined


def test_visual_layer_has_no_browser_persistence_or_case_transfer() -> None:
    page = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
    visual = page.split("function MarketInsightVisualResult", 1)[1].split("function LegacyTextMarketInsight", 1)[0]
    assert "localStorage" not in visual
    assert "sessionStorage" not in visual
    assert "document.cookie" not in visual
    assert "URLSearchParams" not in visual
    assert "setCase" not in visual
