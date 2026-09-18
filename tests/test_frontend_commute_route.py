"""Static frontend contracts for the commute route (Google Routes) card."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
API = (FRONTEND / "lib" / "api.ts").read_text(encoding="utf-8")
CARD = (FRONTEND / "components" / "commute-route-card.tsx").read_text(encoding="utf-8")
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")


def test_route_card_is_imported_and_rendered_by_location_insight() -> None:
    # P0: the card must actually be mounted in a real user-facing parent.
    assert 'import { CommuteRouteCard } from "@/components/commute-route-card"' in LOCATION
    assert "<CommuteRouteCard" in LOCATION
    # It must receive the already-resolved property coordinates from existing state.
    assert "result.resolved_location.latitude" in LOCATION
    assert "result.resolved_location.longitude" in LOCATION
    # Gated on a resolved location so it never mounts without coordinates.
    assert "result?.resolved_location && <CommuteRouteCard" in LOCATION


def test_api_client_exposes_commute_route() -> None:
    assert "CommuteRouteResult" in API
    assert "commuteRoute" in API
    assert '"/commute/route"' in API


def test_mock_result_is_unmistakably_non_live() -> None:
    # A mock/fallback result must carry a strong adjacent indicator, not just a source label.
    assert "commute-route-mock-banner" in CARD
    assert "示範估算" in CARD
    assert "非即時 Google 路線結果" in CARD
    # The duration field itself is annotated when fallback.
    assert "（非即時）" in CARD
    assert "result.fallback" in CARD


def test_route_card_does_not_leak_sensitive_strings() -> None:
    for forbidden in ("api_key", "X-Goog-Api-Key", "GOOGLE_MAPS_API_KEY", "token", "secret", "polyline"):
        assert forbidden not in CARD
