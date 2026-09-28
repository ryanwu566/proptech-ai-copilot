"""Static frontend contracts for the commute route (Google Routes) card."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
API = (FRONTEND / "lib" / "api.ts").read_text(encoding="utf-8")
CARD = (FRONTEND / "components" / "commute-route-card.tsx").read_text(encoding="utf-8")
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")


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
    assert "commute-route-mock-banner" in CARD
    assert "測試／展示模擬路線" in CARD
    assert "非 Google 實際結果" in CARD
    assert "（模擬）" in CARD
    assert "result.fallback" in CARD


def test_route_card_does_not_leak_sensitive_strings() -> None:
    for forbidden in ("api_key", "X-Goog-Api-Key", "GOOGLE_MAPS_API_KEY", "token", "secret", "polyline"):
        assert forbidden not in CARD
