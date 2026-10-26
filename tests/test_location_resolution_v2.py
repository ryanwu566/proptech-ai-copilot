"""Location V2 Gate L1-1: Google-first bounded candidates and administrative fail-closed.

Controlled HTTP only; no live Google/TGOS calls.
"""
from copy import deepcopy

from fastapi.testclient import TestClient
import httpx
import pytest

from backend.api_main import app
from services import location_resolver as resolver


INCIDENT = "新北市新莊區中正路191號"


def result(formatted, county, district, route, number, *, lat=25.0359, lng=121.4326, precision="ROOFTOP", postal="242", place_id="ChIJ-test_1"):
    components = [
        {"long_name": number, "types": ["street_number"]},
        {"long_name": route, "types": ["route"]},
        {"long_name": district, "types": ["administrative_area_level_3", "political"]},
        {"long_name": county, "types": ["administrative_area_level_1", "political"]},
        {"long_name": postal, "types": ["postal_code"]},
    ]
    return {
        "formatted_address": formatted, "partial_match": False, "place_id": place_id,
        "geometry": {"location_type": precision, "location": {"lat": lat, "lng": lng}},
        "address_components": components,
    }


CORRECT = result("242台灣新北市新莊區中正路191號", "新北市", "新莊區", "中正路", "191", postal="242", place_id="ChIJ-correct")
# The historical production incident: same road and number, wrong district.
WRONG_DISTRICT = result("238台灣新北市樹林區金寮里中正路191號", "新北市", "樹林區", "中正路", "191", lat=24.99, lng=121.42, postal="238", place_id="ChIJ-wrong")


@pytest.fixture
def providers(monkeypatch):
    state = {"google": {"status": "OK", "results": [CORRECT]}, "tgos": {"AddressList": []}, "calls": []}

    def get(url, *, params, **kwargs):
        name = "google" if url == resolver.GOOGLE_GEOCODING_URL else "tgos"
        state["calls"].append(name)
        payload = state[name]
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(200, json=deepcopy(payload), request=httpx.Request("GET", url))

    monkeypatch.setattr(resolver.httpx, "get", get)
    state["google_provider"] = resolver.GoogleAddressProvider(api_key="test")
    state["tgos_provider"] = resolver.TgosAddressProvider(app_id="test", api_key="test")
    return state


def resolve(state, address=INCIDENT):
    return resolver.resolve_address(address, google_provider=state["google_provider"], tgos_provider=state["tgos_provider"])


def test_correct_google_candidate_carries_bounded_normalized_evidence(providers):
    body = resolve(providers)
    assert (body["status"], body["source"], body["confidence"], body["resolution_reason"]) == ("resolved", "google", "high", "accepted")
    assert (body["county"], body["district"], body["postal_code"], body["place_id"]) == ("新北市", "新莊區", "242", "ChIJ-correct")
    assert body["candidates"] == [{
        "source": "google", "formatted_address": "242台灣新北市新莊區中正路191號", "latitude": 25.0359, "longitude": 121.4326,
        "county": "新北市", "district": "新莊區", "postal_code": "242", "place_id": "ChIJ-correct",
        "admin_check": "consistent", "confirmable": True, "block_reason": None,
    }]
    assert providers["calls"] == ["google"]
    assert set(body) == resolver.SAFE_RESPONSE_KEYS


def test_wrong_district_incident_is_visible_but_never_confirmable(providers):
    providers["google"] = {"status": "OK", "results": [WRONG_DISTRICT]}
    body = resolve(providers)
    assert (body["status"], body["confidence"], body["resolution_reason"]) == ("unresolved", "unknown", "administrative_mismatch")
    assert body["latitude"] is body["longitude"] is None
    [candidate] = body["candidates"]
    assert (candidate["district"], candidate["admin_check"], candidate["confirmable"], candidate["block_reason"]) == ("樹林區", "district_mismatch", False, "administrative_mismatch")
    # A strict TGOS fallback still gets its one chance; it found nothing here.
    assert providers["calls"] == ["google", "tgos"]


def test_structured_district_hidden_behind_matching_text_is_still_a_mismatch(providers):
    hidden = deepcopy(WRONG_DISTRICT)
    hidden["formatted_address"] = "新北市新莊區中正路191號"
    providers["google"] = {"status": "OK", "results": [hidden]}
    body = resolve(providers)
    assert body["resolution_reason"] == "administrative_mismatch"
    assert body["candidates"][0]["confirmable"] is False


def test_wrong_first_result_does_not_hide_a_correct_second_result(providers):
    providers["google"] = {"status": "OK", "results": [WRONG_DISTRICT, CORRECT]}
    body = resolve(providers)
    assert (body["status"], body["district"], body["place_id"]) == ("resolved", "新莊區", "ChIJ-correct")
    assert [candidate["district"] for candidate in body["candidates"]] == ["新莊區"]
    assert providers["calls"] == ["google"]


def test_multiple_plausible_candidates_require_a_choice_and_are_never_cached(monkeypatch, providers):
    # A user who omits the county: two counties share the district name 信義區.
    taipei = result("110台灣臺北市信義區市府路1號", "臺北市", "信義區", "市府路", "1", lat=25.0375, lng=121.5637, postal="110", place_id="ChIJ-taipei")
    keelung = result("201台灣基隆市信義區市府路1號", "基隆市", "信義區", "市府路", "1", lat=25.13, lng=121.75, postal="201", place_id="ChIJ-keelung")
    providers["google"] = {"status": "OK", "results": [taipei, keelung]}
    body = resolve(providers, "信義區市府路1號")
    assert (body["status"], body["resolution_reason"], body["confidence"]) == ("ambiguous", "multiple_candidates", "unknown")
    assert body["latitude"] is None
    assert [(c["county"], c["admin_check"], c["confirmable"]) for c in body["candidates"]] == [("臺北市", "county_unverified", True), ("基隆市", "county_unverified", True)]
    assert providers["calls"] == ["google"]


def test_ambiguous_and_mismatch_results_are_not_cached_by_the_shared_resolver(monkeypatch):
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json={"status": "OK", "results": [deepcopy(WRONG_DISTRICT)]}, request=httpx.Request("GET", url))

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fixture-only")
    monkeypatch.delenv("TGOS_APP_ID", raising=False)
    monkeypatch.delenv("TGOS_API_KEY", raising=False)
    monkeypatch.setattr(resolver.httpx, "get", get)
    resolver._RESOLVED_ADDRESS_CACHE.clear()
    try:
        client = TestClient(app)
        for _ in range(2):
            body = client.post("/location/resolve", json={"address": INCIDENT}).json()
            assert body["resolution_reason"] == "administrative_mismatch"
            assert body["candidates"][0]["confirmable"] is False
        # Search again is an explicit, new geocode: a blocked result is never reused.
        assert calls == [resolver.GOOGLE_GEOCODING_URL] * 2
    finally:
        resolver._RESOLVED_ADDRESS_CACHE.clear()


def test_mismatch_then_strict_tgos_full_match_recovers(providers):
    providers["google"] = {"status": "OK", "results": [WRONG_DISTRICT]}
    providers["tgos"] = {"Info": [{"OutMatchType": "完全比對"}], "AddressList": [{"FULL_ADDR": INCIDENT, "X": 121.4326, "Y": 25.0359, "COUNTY": "新北市", "TOWN": "新莊區"}]}
    body = resolve(providers)
    assert (body["status"], body["source"], body["district"]) == ("resolved", "tgos", "新莊區")
    assert body["candidates"][0]["source"] == "tgos"


def test_low_precision_candidate_is_blocked_with_its_own_reason(providers):
    low = deepcopy(CORRECT)
    low["geometry"]["location_type"] = "APPROXIMATE"
    providers["google"] = {"status": "OK", "results": [low]}
    body = resolve(providers)
    assert (body["status"], body["resolution_reason"]) == ("unresolved", "low_precision")
    assert body["candidates"][0]["block_reason"] == "low_precision"


def test_provider_failure_is_retryable_unavailable_without_candidates(providers):
    providers["google"] = httpx.ConnectError("down")
    providers["tgos"] = httpx.ConnectError("down")
    body = resolve(providers)
    assert (body["status"], body["resolution_reason"], body["candidates"]) == ("unavailable", "unavailable", [])


def test_candidate_list_is_bounded(providers):
    providers["google"] = {"status": "OK", "results": [deepcopy(WRONG_DISTRICT) for _ in range(9)]}
    body = resolve(providers)
    assert len(body["candidates"]) <= resolver.MAX_GOOGLE_CANDIDATES
    assert providers["calls"].count("google") == 1


def test_geocoding_stays_zh_tw_for_canonical_identity(providers, monkeypatch):
    seen = []
    original = resolver.httpx.get

    def spy(url, *, params, **kwargs):
        seen.append(params.get("language"))
        return original(url, params=params, **kwargs)

    monkeypatch.setattr(resolver.httpx, "get", spy)
    resolve(providers)
    assert seen[0] == "zh-TW"
