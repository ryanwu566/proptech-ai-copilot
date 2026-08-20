"""Static contracts for the localized map and location search surface."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
MAP = (ROOT / "frontend_next/components/map/geo-map.tsx").read_text(encoding="utf-8")
SEARCH = (ROOT / "frontend_next/lib/map-search.ts").read_text(encoding="utf-8")
RUNTIME = (ROOT / "frontend_next/lib/runtime-copy.ts").read_text(encoding="utf-8")
RUNTIME_OVERRIDES = (ROOT / "frontend_next/lib/runtime-copy-overrides.ts").read_text(encoding="utf-8")
EXPERIENCE_OVERRIDES = (ROOT / "frontend_next/lib/experience-i18n-overrides.ts").read_text(encoding="utf-8")
DECISION_PANEL = (ROOT / "frontend_next/components/viewing-decision-panel.tsx").read_text(encoding="utf-8")
DECISION_REPORT = (ROOT / "frontend_next/components/decision-report.tsx").read_text(encoding="utf-8")


def _map_insight() -> str:
    return PAGE.split("function MapInsight()", 1)[1].split("function LegacyMapInsight()", 1)[0]


def test_multilingual_search_normalization_covers_script_and_romanized_aliases() -> None:
    assert "normalizeTaiwanPlaceQuery" in SEARCH
    for alias in ("new\\s+taipei", "taipei", "daan", "banqiao", "タイペイ", "다안구", "반차오"):
        assert alias in SEARCH
    assert "locale: ExperienceLocale" in SEARCH
    assert "normalizeTaiwanPlaceQuery(normalized, locale)" not in _map_insight()
    assert "normalizeTaiwanPlaceQuery(next, locale)" in _map_insight()


def test_map_is_localized_without_changing_provider_tile_urls() -> None:
    for key in ("map.baseStandard", "map.baseLight", "map.baseSatellite", "map.selected", "map.distance", "map.rating"):
        assert key in RUNTIME
        assert key in RUNTIME_OVERRIDES
    assert 'copy("map.baseStandard")' in MAP
    assert 'copy("map.selected")' in MAP
    assert "tile.openstreetmap.org" in MAP
    assert "basemaps.cartocdn.com" in MAP
    assert "server.arcgisonline.com" in MAP


def test_mobile_map_first_and_desktop_side_panel_are_explicit() -> None:
    component = _map_insight()
    assert "h-[min(72vh,720px)]" in component
    assert "min-h-[520px]" in component
    assert "xl:grid-cols-[minmax(0,1fr)_380px]" in component
    assert '<details open className=' in component
    assert "xl:hidden" in component
    assert "min-w-0" in component
    assert "overflow-x-auto" not in component


def test_map_address_first_progress_partial_state_and_single_geocode_flow() -> None:
    component = _map_insight()
    assert 'testId="map-analysis-progress"' in component
    assert 'data-testid="map-partial-notice"' in component
    assert 'data-testid="map-advanced-settings"' in PAGE
    assert 'setProgress("waiting")' in component
    assert 'setProgress("rendering")' in component
    assert component.count("api.mapSearch(") == 1
    assert "api.mapNearby(found.center" in component
    assert "api.mapSearch(found" not in component


def test_locale_switching_does_not_add_storage_or_locale_triggered_search() -> None:
    component = _map_insight()
    assert "localStorage" not in component
    assert "sessionStorage" not in component
    assert "location.search" not in component
    assert "location.hash" not in component
    assert "setLocale" not in component
    effect = component.split("useEffect(() =>", 1)[1].split("}, []);", 1)[0]
    assert "api.mapGoogleHealth" in effect
    assert "api.roadCities" in effect
    assert "api.mapSearch" not in effect


def test_shared_surfaces_have_localized_runtime_entry_points() -> None:
    for key in ("location.title", "commute.title", "loan.title", "tax.title", "case.title"):
        assert key in RUNTIME_OVERRIDES
    for key in ("page.terrain", "journey.location.title", "trust.referenceOnly"):
        assert key in EXPERIENCE_OVERRIDES
    assert "function TerrainRiskPage()" in PAGE
    assert "function History()" not in PAGE


def test_viewing_decision_logic_and_components_remain_untouched() -> None:
    assert "api.commute" not in DECISION_PANEL.lower()
    assert "api.map" not in DECISION_REPORT.lower()
