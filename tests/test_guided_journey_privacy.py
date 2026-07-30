"""Privacy and trust contracts for the runtime-only journey state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")
LOCATION_HELPER = (ROOT / "frontend_next/lib/location-market-journey.ts").read_text(encoding="utf-8")
JOURNEY_DIR = ROOT / "frontend_next/components/guided-journey"
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
LOCATION_STAGE = (ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx").read_text(encoding="utf-8")


def test_pure_helper_has_no_data_or_storage_boundary() -> None:
    for forbidden in ("fetch(", "api.", "localStorage", "sessionStorage", "document.cookie", "URLSearchParams", "Date.now", "latitude", "longitude", "raw", "address"):
        assert forbidden not in HELPER.lower()
    assert "getJourneyStepForTool" in HELPER
    assert "addVisitedJourneyStep" in HELPER


def test_journey_components_do_not_expose_sensitive_runtime_data() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in JOURNEY_DIR.glob("*.tsx")).lower()
    for forbidden in ("localstorage", "sessionstorage", "document.cookie", "urlsearchparams", "raw json", "provider payload", "coordinates", "sql", "credential", "token", "exception", "stack trace"):
        assert forbidden not in source


def test_home_journey_keeps_conservative_product_boundaries() -> None:
    journey_section = PAGE.split("function renderJourneyStep", 1)[1].split("return <AppShell", 1)[0]
    for forbidden in ("最佳物件", "AI 幫你決定", "投資排名", "推薦購買", "winner"):
        assert forbidden not in journey_section
    for key in ("trust.referenceOnly", "trust.noPurchase", "trust.loanEstimate", "trust.taxInfo"):
        affordability_stage = (ROOT / "frontend_next/components/guided-journey/affordability-decision-stage.tsx").read_text(encoding="utf-8")
        assert f't("{key}")' in journey_section or f't("{key}")' in PAGE or f't("{key}")' in LOCATION_STAGE or f't("{key}")' in affordability_stage or key in LOCATION_HELPER
    assert 't("journey.location.next")' in LOCATION_STAGE
    assert 't("trust.noPurchase")' in journey_section or 't("trust.noPurchase")' in PAGE or 't("trust.noPurchase")' in LOCATION_STAGE or 't("trust.noPurchase")' in affordability_stage


def test_no_new_persistence_or_automatic_analysis_is_added() -> None:
    journey_section = PAGE.split("function renderJourneyStep", 1)[1].split("function Dashboard", 1)[0]
    assert "api." not in journey_section
    assert "fetch(" not in journey_section
    assert "localStorage" not in journey_section
    assert "URLSearchParams" not in journey_section
    assert "saveCase(" not in journey_section
    assert "setItem(" in PAGE.split("const openViewingFlow", 1)[1].split("function renderJourneyStep", 1)[0]
