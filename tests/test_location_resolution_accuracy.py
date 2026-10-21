"""P0 trusted-address regressions: controlled HTTP only, never live providers."""
from copy import deepcopy

import httpx
import pytest

from services import location_resolver as resolver


ADDRESS = "新北市新莊區中正路191號"
CONTROL = "臺北市信義區市府路1號"


def google_payload(address=ADDRESS, precision="ROOFTOP", partial=False):
    return {"status": "OK", "results": [{
        "formatted_address": address,
        "partial_match": partial,
        "geometry": {"location_type": precision, "location": {"lat": 25.0375, "lng": 121.5637}},
        "address_components": [
            {"long_name": "新北市", "types": ["administrative_area_level_1"]},
            {"long_name": "新莊區", "types": ["administrative_area_level_3"]},
            {"long_name": "中正路", "types": ["route"]},
            {"long_name": "191", "types": ["street_number"]},
        ] if address == ADDRESS else [],
    }]}


def tgos_payload(address=ADDRESS, match="完全比對"):
    return {"Info": [{"OutMatchType": match}], "AddressList": [{
        "FULL_ADDR": address, "X": 121.5637, "Y": 25.0375,
    }]}


@pytest.fixture
def providers(monkeypatch):
    state = {"google": google_payload(), "tgos": tgos_payload(), "calls": []}

    def get(url, *, params, **kwargs):
        name = "google" if url == resolver.GOOGLE_GEOCODING_URL else "tgos"
        state["calls"].append((name, deepcopy(params)))
        payload = state[name]
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(resolver.httpx, "get", get)
    state["google_provider"] = resolver.GoogleAddressProvider(api_key="test")
    state["tgos_provider"] = resolver.TgosAddressProvider(app_id="test", api_key="test")
    return state


def resolve(state, address=ADDRESS):
    return resolver.resolve_address(address, google_provider=state["google_provider"], tgos_provider=state["tgos_provider"])


def names(state):
    return [name for name, _ in state["calls"]]


def test_google_rooftop_stops_before_any_tgos_physical_call(providers):
    result = resolve(providers)
    assert (result["status"], result["source"], result["confidence"]) == ("resolved", "google", "high")
    assert names(providers) == ["google"]


def test_known_good_control_is_google_only(providers):
    providers["google"] = google_payload("110台灣台北市信義區市府路１號")
    assert resolve(providers, CONTROL)["source"] == "google"
    assert names(providers) == ["google"]


@pytest.mark.parametrize("precision,partial", [("ROOFTOP", True), ("APPROXIMATE", False), ("GEOMETRIC_CENTER", False), ("RANGE_INTERPOLATED", False), (None, False)])
def test_insufficient_google_precision_uses_one_strict_fallback(providers, precision, partial):
    providers["google"] = google_payload(precision=precision, partial=partial)
    assert resolve(providers)["source"] == "tgos"
    assert names(providers) == ["google", "tgos"]
    params = providers["calls"][1][1]
    assert params["oIsOnlyFullMatch"] == "true"
    assert params["oReturnMaxCount"] == "1"


@pytest.mark.parametrize("bad", ["新北市樹林區金寮里中正路191號", "臺北市新莊區中正路191號", "新北市新莊區中山路191號", "新北市新莊區中正路192號", "新北市新莊區中正路1191號", "新北市新莊區中正路191之1號"])
def test_google_structural_mismatch_is_rejected(providers, bad):
    providers["google"] = google_payload(bad)
    providers["tgos"] = {"AddressList": []}
    result = resolve(providers)
    assert (result["status"], result["confidence"]) == ("unresolved", "unknown")
    assert result["latitude"] is None
    assert names(providers) == ["google", "tgos"]


@pytest.mark.parametrize("component,value", [(0, "臺北市"), (1, "樹林區"), (2, "中山路"), (3, "192")])
def test_google_components_cannot_contradict_matching_formatted_address(providers, component, value):
    providers["google"]["results"][0]["address_components"][component]["long_name"] = value
    providers["tgos"] = {"AddressList": []}
    assert resolve(providers)["status"] == "unresolved"


def test_incident_tgos_cross_district_candidate_never_high(providers):
    providers["google"] = {"status": "ZERO_RESULTS"}
    providers["tgos"] = tgos_payload("238台灣新北市樹林區金寮里中正路191號")
    assert resolve(providers)["status"] == "unresolved"
    assert resolve(providers)["confidence"] == "unknown"
    assert names(providers) == ["google", "tgos", "google", "tgos"]


def test_tgos_fuzzy_metadata_is_rejected_even_with_matching_text(providers):
    providers["google"] = {"status": "ZERO_RESULTS"}
    providers["tgos"] = tgos_payload(match="模糊比對")
    assert resolve(providers)["status"] == "unresolved"


@pytest.mark.parametrize("fields,accepted", [
    ({"COUNTY": "新北市", "TOWN": "新莊區", "ROAD": "中正路", "NUMBER": "191號"}, True),
    ({"ROAD": "中正路192號"}, False),
    ({"COUNTY": "新北市", "TOWN": "樹林區"}, False),
    ({"NUMBER": "192號"}, False),
    ({"ROAD": "中山路"}, False),
    ({"NUMBER": "191"}, True),
])
def test_tgos_structured_fields_must_all_agree(providers, fields, accepted):
    providers["google"] = {"status": "ZERO_RESULTS"}
    providers["tgos"]["AddressList"][0].update(fields)
    assert (resolve(providers)["status"] == "resolved") is accepted


@pytest.mark.parametrize("google,tgos,expected", [
    ({"status": "ZERO_RESULTS"}, {"AddressList": []}, "unresolved"),
    (httpx.TimeoutException("secret"), httpx.TimeoutException("secret"), "unavailable"),
    (httpx.TimeoutException("secret"), tgos_payload(), "resolved"),
])
def test_failure_and_unavailable_fallback_statuses(providers, google, tgos, expected):
    providers.update(google=google, tgos=tgos)
    assert resolve(providers)["status"] == expected
    assert names(providers) == ["google", "tgos"]


@pytest.mark.parametrize("latitude,longitude", [(35.68, 139.76), (True, 121.56), (25.03, None)])
def test_coordinates_must_be_finite_taiwan_numbers(providers, latitude, longitude):
    providers["google"]["results"][0]["geometry"]["location"] = {"lat": latitude, "lng": longitude}
    providers["tgos"] = {"AddressList": []}
    assert resolve(providers)["confidence"] == "unknown"


@pytest.mark.parametrize("supplied,returned,accepted", [
    ("台北市 信義區，市府路１號", "110臺灣臺北市信義區市府路1號", True),
    ("新莊區中正路191號", ADDRESS, True),
    ("中正路191號", ADDRESS, True),
    ("臺北市信義區信義路四段10巷2弄3號", "臺北市信義區信義路4段10巷2弄3號", True),
    ("臺北市信義區信義路四段10巷2弄3號", "臺北市信義區信義路三段10巷2弄3號", False),
    ("臺北市信義區信義路四段10巷2弄3號", "臺北市信義區信義路四段11巷2弄3號", False),
    ("臺北市信義區信義路四段10巷2弄3號", "臺北市信義區信義路四段10巷3弄3號", False),
    ("臺北市信義區信義路四段10巷2弄3號", "臺北市信義區信義路10巷2弄3號", False),
    ("新北市新莊區中正路191之1號", "新北市新莊區中正路191-1號", True),
    (ADDRESS, "191號", False),
    ("not an address", ADDRESS, False),
    ("花蓮縣吉安鄉仁里五街1號", "花蓮縣吉安鄉五街1號", False),
    ("花蓮縣吉安鄉仁里五街1號", "花蓮縣吉安鄉仁里五街1號", True),
    ("花蓮縣吉安鄉五街1號", "花蓮縣吉安鄉仁里五街1號", False),
    ("新北市新莊區中正路191-號", ADDRESS, False),
    ("新北市新莊區中正路191之號", ADDRESS, False),
])
def test_bounded_structural_comparison(providers, supplied, returned, accepted):
    providers["google"] = google_payload(returned)
    providers["tgos"] = {"AddressList": []}
    assert (resolve(providers, supplied)["status"] == "resolved") is accepted


@pytest.mark.parametrize("accepted", [True, False])
def test_only_validated_results_enter_versioned_cache(providers, monkeypatch, accepted):
    cache = resolver._RESOLVED_ADDRESS_CACHE
    cache.clear()
    tgos = providers["tgos_provider"]
    tgos.cache_namespace = object()
    monkeypatch.setattr(resolver, "_get_google_provider", lambda: providers["google_provider"])
    monkeypatch.setattr(resolver, "_get_tgos_provider", lambda: tgos)
    if not accepted:
        providers["google"] = google_payload(precision="APPROXIMATE")
        providers["tgos"] = tgos_payload("新北市樹林區中正路191號")
    try:
        first = resolver.resolve_address(ADDRESS)
        assert resolver.resolve_address(ADDRESS) == first
        assert len(providers["calls"]) == (1 if accepted else 4)
        assert first["confidence"] == ("high" if accepted else "unknown")
        if accepted:
            monkeypatch.setattr(resolver, "ADDRESS_RESOLVER_VERSION", "test-other-semantics")
            resolver.resolve_address(ADDRESS)
            assert names(providers) == ["google", "google"]
    finally:
        cache.clear()
