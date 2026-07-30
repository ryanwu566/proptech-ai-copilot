"""Regression contracts for runtime locale coverage on the primary journey."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"

SURFACES = (
    "components/sidebar.tsx",
    "components/hero-intro.tsx",
    "components/app-shell.tsx",
    "components/topbar.tsx",
    "components/guided-journey/guided-property-journey.tsx",
    "components/guided-journey/journey-stepper.tsx",
    "components/guided-journey/journey-stage.tsx",
    "components/guided-journey/journey-navigation.tsx",
    "components/guided-journey/journey-progress-summary.tsx",
    "components/guided-journey/journey-expert-tools.tsx",
    "components/guided-journey/journey-tool-card.tsx",
    "components/guided-journey/location-market-stage.tsx",
    "components/guided-journey/location-market-tool-selector.tsx",
    "components/guided-journey/price-decision-stage.tsx",
    "components/guided-journey/affordability-decision-stage.tsx",
    "components/guided-journey/decision-case-stage.tsx",
    "components/guided-journey/journey-property-context-header.tsx",
    "components/guided-journey/journey-decision-context-header.tsx",
)


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8")


def without_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"//[^\n]*", "", source)


def test_all_supported_locale_journey_copy_is_present_and_consumed_at_render_time():
    resources = read("lib/experience-i18n.ts")
    journey = read("lib/guided-journey.ts")
    mounted = read("components/guided-journey/guided-property-journey.tsx")
    for locale_marker in ('"zh-TW"', "en:", "ja:", "ko:"):
        assert locale_marker in resources
    for key in (
        "journey.title", "journey.description", "journey.current", "journey.progressTitle",
        "journey.mobileSummary", "journey.statusCurrent", "journey.statusVisited",
        "journey.statusNotVisited", "journey.finish", "journey.property.title",
        "journey.location.title", "journey.price.title", "journey.affordability.title",
        "journey.decision.title", "trust.referenceOnly", "trust.valuationDemo",
    ):
        assert resources.count(f'"{key}"') == 4, key
    assert "getJourneyStepCopy" in journey
    stable_definitions = journey.split("export const JOURNEY_STEPS", 1)[1].split("const JOURNEY_COPY_KEYS", 1)[0]
    assert "title:" not in without_comments(stable_definitions)
    assert "question:" not in without_comments(stable_definitions)
    assert "description:" not in without_comments(stable_definitions)
    assert "getJourneyStepCopy(activeStep, t)" in mounted


def test_locale_consistency_guard_rejects_unapproved_cjk_in_primary_surfaces():
    offenders = []
    for relative in SURFACES:
        source = without_comments(read(relative))
        for line_number, line in enumerate(source.splitlines(), 1):
            stable_identifier_line = relative == "components/sidebar.tsx" and ("export type AppPage" in line or "page:" in line or "onNavigate(\"儀表板\")" in line)
            user_data_line = relative.endswith("location-market-stage.tsx") and "sourceLabel:" in line
            if not stable_identifier_line and not user_data_line and re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", line):
                offenders.append(f"{relative}:{line_number}: {line.strip()}")
    assert not offenders, "untranslated customer-facing CJK: " + " | ".join(offenders)


def test_sidebar_hero_and_accessibility_copy_use_active_locale():
    sidebar = read("components/sidebar.tsx")
    hero = read("components/hero-intro.tsx")
    stepper = read("components/guided-journey/journey-stepper.tsx")
    progress = read("components/guided-journey/journey-progress-summary.tsx")
    navigation = read("components/guided-journey/journey-navigation.tsx")
    for source in (sidebar, hero, stepper, progress, navigation):
        assert "useExperienceLocale" in source
        assert "t(" in source
    assert "aria-label={t(" in sidebar
    assert "aria-label={`${copy.title}" in stepper
    assert "journey.progressCount" in progress
    assert "journey.finish" in navigation


def test_render_contract_has_language_specific_journey_evidence():
    resources = read("lib/experience-i18n.ts")
    expected = (
        "Organize the viewing decision in five steps",
        "5つのステップで内見判断を整理",
        "다섯 단계로 방문 판단 정리",
        "用五個步驟整理看房資訊",
    )
    for text in expected:
        assert text in resources
    for forbidden in ("fetch(", "localStorage", "sessionStorage", "document.cookie"):
        assert forbidden not in read("components/experience-locale-provider.tsx")
    assert "setLocale" in read("components/locale-switcher.tsx")


def test_read_aloud_uses_localized_safe_summary_and_voice_allowlist_is_unchanged():
    topbar = read("components/topbar.tsx")
    speech = read("components/read-aloud-controls.tsx")
    voice = read("lib/voice-input.ts")
    assert "createSafeSpeechSummary" in topbar
    assert "locale" in topbar
    assert "summary.visibleText" in speech
    assert "parseVoiceCommand" in read("components/voice-input-controls.tsx")
    assert "fetch(" not in voice
    assert "save" in voice.lower() and "delete" in voice.lower() and "export" in voice.lower()


def test_stable_journey_ids_and_business_boundaries_are_not_translated():
    journey = read("lib/guided-journey.ts")
    page = read("app/page.tsx")
    for value in ('"property"', '"location"', '"price"', '"affordability"', '"decision"', '"property-finder"', '"location-insight"', '"valuation"', '"loan"', '"viewing-decision"'):
        assert value in journey
    assert "ViewingDecisionPanel" in page
    assert "api." not in read("components/voice-input-controls.tsx")
