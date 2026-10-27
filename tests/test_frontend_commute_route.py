"""Static frontend contracts for the commute route (Google Routes) card."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
API = (FRONTEND / "lib" / "api.ts").read_text(encoding="utf-8")
CARD = (FRONTEND / "components" / "commute-route-card.tsx").read_text(encoding="utf-8")
ROUTE_COPY = (FRONTEND / "lib" / "commute-route-copy.ts").read_text(encoding="utf-8")
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")

LOCALES = ("zh-TW", "en", "ja", "ko")
MOCK_KEYS = ("mockBanner", "simulatedSuffix", "mockNote", "sourceMock")


def _locale_block(locale: str) -> str:
    """The body of one locale's entry in the route copy catalogue."""
    opener = f'"{locale}": {{' if "-" in locale else f"  {locale}: {{"
    start = ROUTE_COPY.index(opener) + len(opener)
    return ROUTE_COPY[start:ROUTE_COPY.index("\n  },", start)]


def _copy_value(locale: str, key: str) -> str:
    match = re.search(rf'\b{key}: "((?:[^"\\]|\\.)*)"', _locale_block(locale))
    assert match, f"{locale}.{key} missing from commute route copy"
    return match.group(1)


def test_route_card_is_imported_and_rendered_by_location_insight() -> None:
    assert 'import { CommuteRouteCard } from "@/components/commute-route-card"' in LOCATION
    assert "<CommuteRouteCard" in LOCATION
    assert "result.resolved_location.latitude" in LOCATION
    assert "result.resolved_location.longitude" in LOCATION
    assert "result?.resolved_location && <CommuteRouteCard" in LOCATION


def test_api_client_exposes_bounded_commute_route_contract() -> None:
    assert "CommuteRouteResult" in API
    assert "CommuteRouteReasonCode" in API
    assert "CommuteRouteEvidence" in API
    assert "commuteRoute" in API
    assert '"/commute/route"' in API


def test_mock_result_is_unmistakably_non_live() -> None:
    # The card renders the mock banner, suffix, warning and source label for fallback results via localized copy.
    assert "commute-route-mock-banner" in CARD
    assert "result.fallback" in CARD
    assert 'copy("mockBanner")' in CARD
    assert 'copy("simulatedSuffix")' in CARD
    assert 'copy("mockNote")' in CARD
    assert 'copy(source === "mock" ? "sourceMock"' in CARD
    assert 'from "@/lib/commute-route-copy"' in CARD

    # zh-TW wording stays unmistakably non-live.
    assert "測試／展示模擬路線" in _copy_value("zh-TW", "mockBanner")
    assert "非 Google 實際結果" in _copy_value("zh-TW", "mockBanner")
    assert "測試／展示模擬路線" in _copy_value("zh-TW", "sourceMock")
    assert "非 Google 實際結果" in _copy_value("zh-TW", "sourceMock")
    assert _copy_value("zh-TW", "simulatedSuffix") == "（模擬）"
    assert "非即時 Google 路線結果" in _copy_value("zh-TW", "mockNote")

    # Every locale carries the same non-live labels.
    for locale in LOCALES:
        for key in MOCK_KEYS:
            assert _copy_value(locale, key).strip(), f"{locale}.{key} is empty"
    assert "not an actual Google result" in _copy_value("en", "mockBanner")
    assert "simulated" in _copy_value("en", "simulatedSuffix")
    assert "Google の実際の結果ではありません" in _copy_value("ja", "mockBanner")
    assert "실제 Google 결과가 아닙니다" in _copy_value("ko", "mockBanner")


def test_route_card_does_not_leak_sensitive_strings() -> None:
    for forbidden in ("api_key", "X-Goog-Api-Key", "GOOGLE_MAPS_API_KEY", "token", "secret", "polyline"):
        assert forbidden not in CARD
