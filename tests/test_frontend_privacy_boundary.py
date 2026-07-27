from pathlib import Path


ROOT = Path(__file__).parents[1]


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
