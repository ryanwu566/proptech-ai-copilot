"""Static contracts for the runtime localization and journey surface cleanup."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8")


def test_runtime_copy_has_all_supported_locales_and_no_missing_keys():
    source = read("lib/runtime-copy.ts")
    assert '"zh-TW": zhTW' in source
    assert "en, ja, ko" in source
    assert "getRuntimeCopyCoverage" in source
    assert 'missing: RUNTIME_COPY_KEYS.filter' in source
    assert "...en" not in source
    for marker in ("const zhTW", "const en", "const ja", "const ko"):
        assert marker in source


def test_primary_customer_surfaces_use_runtime_copy():
    for relative in (
        "components/commute-livability-card.tsx",
        "components/location-insight.tsx",
        "components/property-finder.tsx",
        "components/loan-calculator.tsx",
        "components/onboarding-tour.tsx",
        "components/immersive-viewing-workspace.tsx",
        "components/case-manager.tsx",
        "components/case-comparison-panel.tsx",
        "components/property-case-readiness.tsx",
        "components/decision-report.tsx",
        "components/guided-journey/location-market-snapshot.tsx",
        "components/guided-journey/location-market-status-strip.tsx",
        "components/data-visualization/amenity-category-chart.tsx",
    ):
        source = read(relative)
        assert "useExperienceLocale" in source, relative
        assert "copy(" in source, relative


def test_valuation_and_map_surfaces_use_localized_runtime_copy():
    page = read("app/page.tsx")
    assert "ValuationPage" in page
    assert 'copy("valuation.title")' in page
    assert "MapInsight" in page
    assert 'copy("location.title")' in page or 'copy("location.map")' in page


def test_production_frontend_has_no_compatibility_marker_comments():
    forbidden = (
        "Compatibility markers",
        "Compatibility labels",
        "Static contracts retained",
        "Legacy accessibility contract",
        "Legacy flow marker",
        "Legacy trust contracts",
        "Legacy explicit-action contract",
        "Legacy boundary contract",
        "Legacy decision contract",
        "Legacy copy contracts",
        "Legacy source contracts",
        "Legacy test contracts",
        "Legacy navigation contracts",
        "Static contract markers",
    )
    for path in FRONTEND.rglob("*.tsx"):
        source = path.read_text(encoding="utf-8")
        assert not any(marker in source for marker in forbidden), path
    for path in FRONTEND.rglob("*.ts"):
        source = path.read_text(encoding="utf-8")
        assert not any(marker in source for marker in forbidden), path


def test_expert_tools_panel_is_not_mounted_in_guided_journey():
    journey = read("components/guided-journey/guided-property-journey.tsx")
    page = read("app/page.tsx")
    assert "JourneyExpertTools" not in journey
    assert "renderExpertTools" not in journey
    assert "renderExpertTools" not in page


def test_no_new_client_persistence_or_automatic_commute_lookup_was_added():
    commute = read("components/commute-livability-card.tsx")
    journey = read("components/guided-journey/guided-property-journey.tsx")
    assert "localStorage" not in commute
    assert "sessionStorage" not in commute
    assert "URLSearchParams" not in commute
    assert "commuteAddressLookup" in commute
    assert "onClick={lookupCommute}" in commute
    assert "commuteAddressLookup" not in journey


def test_locale_provider_exposes_copy_without_locale_storage():
    provider = read("components/experience-locale-provider.tsx")
    assert "translateRuntimeCopy" in provider
    assert "copy:" in provider
    assert "localStorage" not in provider
    assert "sessionStorage" not in provider
