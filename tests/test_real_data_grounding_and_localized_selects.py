"""Regression checks for truthful surface states and locale-aware selectors."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_structured_option_layer_has_stable_values_and_all_supported_locales() -> None:
    source = read("frontend_next/lib/structured-options.ts")
    labels = json.loads((ROOT / "frontend_next/lib/taiwan-admin-labels.json").read_text(encoding="utf-8"))
    assert any(entry["value"] == "臺北市" and entry["labels"]["en"] == "Taipei City" for entry in labels["entries"])
    assert any(entry["value"] == "大安區" and entry["labels"]["en"] == "Daan District" for entry in labels["entries"])
    assert 'value: "住宅大樓"' in source
    assert "getLocalizedCountyLabel" in source
    assert "getLocalizedDistrictLabel" in source
    assert "getLocalizedBuildingTypeLabel" in source
    assert "localizeStructuredSelects" in source
    for locale in ('"zh-TW"', "en", "ja", "ko"):
        assert locale in source


def test_selector_localization_preserves_option_values_without_storage_or_api() -> None:
    source = read("frontend_next/lib/structured-options.ts")
    assert "option.dataset.stableValue" in source
    assert "option.value = stableValue" in source
    assert "if (!stableValue) return" in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "fetch(" not in source
    assert "api." not in source


def test_property_finder_and_market_use_localized_labels_with_stable_values() -> None:
    finder = read("frontend_next/components/property-finder.tsx")
    page = read("frontend_next/app/page.tsx")
    assert "BUILDING_TYPE_OPTIONS.map" in finder
    assert 'value={option.value}' in finder
    assert "getLocalizedBuildingTypeLabel" in finder
    assert "getLocalizedCountyLabel(item, locale)" in page
    assert "getLocalizedDistrictLabel(item, locale)" in page
    assert "value={item}" in page


def test_source_and_truth_state_are_explicit_on_data_heavy_surfaces() -> None:
    page = read("frontend_next/app/page.tsx")
    valuation = read("frontend_next/components/data-visualization/valuation-visual-panel.tsx")
    assert "getLocalizedSourceLabel" in page
    assert 'getLocalizedStateLabel("heuristic"' in page
    assert 'getLocalizedStateLabel("reference_only"' in page
    assert "getLocalizedStateLabel(\"source_backed\"" in valuation
    assert "valuation.emptyDetail" in valuation
    assert "SUPABASE" not in valuation


def test_existing_truth_boundaries_and_shared_surfaces_remain_wired() -> None:
    terrain = read("frontend_next/components/terrain-risk-analysis.tsx")
    holding = read("frontend_next/components/holding-cost-calculator.tsx")
    page = read("frontend_next/app/page.tsx")
    assert "getSurfaceCopy" in terrain
    assert "getSurfaceCopy" in holding
    assert "LegacyAegisCredit" in page
    assert "LegacyTaxOracle" in page
    assert "localizeStructuredSelects(document, locale)" in page
    assert "MutationObserver" in page


def test_no_new_locale_persistence_or_locale_triggered_api_call() -> None:
    page = read("frontend_next/app/page.tsx")
    helper = read("frontend_next/lib/structured-options.ts")
    assert "localStorage.setItem" not in helper
    assert "sessionStorage.setItem" not in helper
    assert "window.history" not in helper
    assert "useEffect(() => {\n    let applying" in page
    assert "[locale]" in page
    assert "api." not in helper
