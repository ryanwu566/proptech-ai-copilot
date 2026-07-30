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
    ):
        source = read(relative)
        assert "useExperienceLocale" in source, relative
        assert "copy(" in source, relative


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
