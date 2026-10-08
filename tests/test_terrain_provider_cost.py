"""Deterministic physical-call baselines and terrain provider reuse contracts."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from services.adapters.nlsc_gateway_adapter import NlscGatewayAdapter
from services.provider_request_cache import BoundedRequestCache
from services.provider_cost_metrics import PROVIDER_COST_METRICS
from services.terrain_risk_providers import ArdswcSlopeHazardProvider, GeologyCloudProvider, NlscTerrainProvider
from services.terrain_risk_providers.ardswc_slope_hazard_provider import TileCoord


EMPTY_FEATURES = b'{"type":"FeatureCollection","features":[]}'


def test_ardswc_reuses_retrieval_and_decode_baseline_was_one_http_two_decodes():
    calls = {"http": 0, "decode": 0}

    def fetch(url, timeout):
        calls["http"] += 1
        return b"cost-baseline-tile"

    def decode(payload, tile):
        calls["decode"] += 1
        return []

    provider = ArdswcSlopeHazardProvider(http_get=fetch, decoder=decode)
    for _ in range(2):
        result = provider._query_mvt_layer("debris_flow", [TileCoord(14, 9876, 5678)], 25, 121, 100)
        assert result["status"] == "available"
        assert result["level"] == "unknown"
    assert calls == {"http": 1, "decode": 1}


def test_liquefaction_reuses_three_classification_calls_baseline_was_six():
    calls = []
    provider = GeologyCloudProvider(http_get=lambda url, timeout: calls.append(url) or EMPTY_FEATURES)
    for _ in range(2):
        result = provider.analyze(25, 121, 500, area_hint="臺北市")["liquefaction"]
        assert result["status"] == "available"
        assert result["matched"] is False
        assert result["level"] == "unknown"
    assert len(calls) == 3


def test_numeric_nlsc_reuses_gateway_point_call_baseline_was_two():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"status": "available", "source": "NLSC", "slope_value": 0,
                                         "slope_class": "gentle", "elevation_m": 0})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        gateway = NlscGatewayAdapter(client=client, environ={"NLSC_GATEWAY_BASE_URL": "https://gateway.example.tw",
                                                          "NLSC_GATEWAY_CLIENT_TOKEN": "test-only-token-123"})
        provider = NlscTerrainProvider(gateway=gateway)
        for _ in range(2):
            result = provider.analyze(25, 121, 500)
            assert result["status"] == "available"
            assert result["slope_value"] == 0
    assert len(calls) == 1


def test_ardswc_concurrent_tile_miss_shares_retrieval_and_decode():
    started, release, coalesced = threading.Event(), threading.Event(), threading.Event()
    calls = {"http": 0, "decode": 0}

    def fetch(url, timeout):
        calls["http"] += 1
        started.set()
        assert release.wait(3)
        return b"tile"

    def decode(payload, tile):
        calls["decode"] += 1
        return []

    provider = ArdswcSlopeHazardProvider(http_get=fetch, decoder=decode)
    provider._tile_cache.metrics = CoalescingProbe(coalesced)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(provider._fetch_and_decode_tile, "debris_flow", TileCoord(14, 1, 1), None)
        assert started.wait(3)
        second = executor.submit(provider._fetch_and_decode_tile, "debris_flow", TileCoord(14, 1, 1), None)
        try:
            assert coalesced.wait(3)
        finally:
            release.set()
        assert first.result() == second.result() == []
    assert calls == {"http": 1, "decode": 1}


class CoalescingProbe:
    def __init__(self, event):
        self.event = event

    def record(self, capability, event):
        PROVIDER_COST_METRICS.record(capability, event)
        if event == "coalesced":
            self.event.set()


def test_liquefaction_concurrent_query_shares_three_calls():
    started, release, coalesced = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def fetch(url, timeout):
        calls.append(url)
        if len(calls) == 1:
            started.set()
            assert release.wait(3)
        return EMPTY_FEATURES

    provider = GeologyCloudProvider(http_get=fetch)
    provider._query_cache.metrics = CoalescingProbe(coalesced)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(provider.analyze, 25, 121, 500, "臺北市")
        assert started.wait(3)
        second = executor.submit(provider.analyze, 25, 121, 500, "臺北市")
        try:
            assert coalesced.wait(3)
        finally:
            release.set()
        assert first.result()["liquefaction"] == second.result()["liquefaction"]
    assert len(calls) == 3


def test_liquefaction_partial_failure_retries_without_poisoning_cache():
    baseline = PROVIDER_COST_METRICS.snapshot()
    calls = []

    def fetch(url, timeout):
        calls.append(url)
        if len(calls) == 2:
            raise httpx.ReadTimeout("offline failure")
        return EMPTY_FEATURES

    provider = GeologyCloudProvider(http_get=fetch)
    first = provider.analyze(25, 121, 500, "臺北市")["liquefaction"]
    assert first["status"] == "limited"
    assert first["level"] == "unknown"
    assert len(first["value"]["query_errors"]) == 1
    assert provider.analyze(25, 121, 500, "臺北市")["liquefaction"]["status"] == "available"
    assert provider.analyze(25, 121, 500, "臺北市")["liquefaction"]["status"] == "available"
    assert len(calls) == 6
    final = PROVIDER_COST_METRICS.snapshot()
    assert final.get(("liquefaction", "physical_calls"), 0) - baseline.get(("liquefaction", "physical_calls"), 0) == 6
    assert final.get(("liquefaction", "provider_timeout"), 0) - baseline.get(("liquefaction", "provider_timeout"), 0) == 1
    assert final.get(("liquefaction", "provider_success"), 0) - baseline.get(("liquefaction", "provider_success"), 0) == 5


def test_ardswc_decode_failure_does_not_retain_malformed_tile():
    baseline = PROVIDER_COST_METRICS.snapshot()
    calls = {"http": 0, "decode": 0}

    def fetch(url, timeout):
        calls["http"] += 1
        return b"malformed" if calls["http"] == 1 else b"valid"

    def decode(payload, tile):
        calls["decode"] += 1
        if payload == b"malformed":
            raise ValueError("bad tile")
        return []

    provider = ArdswcSlopeHazardProvider(http_get=fetch, decoder=decode)
    args = ("debris_flow", [TileCoord(14, 1, 1)], 25, 121, 100)
    assert provider._query_mvt_layer(*args)["status"] == "error"
    assert provider._query_mvt_layer(*args)["status"] == "available"
    assert provider._query_mvt_layer(*args)["status"] == "available"
    assert calls == {"http": 2, "decode": 2}
    final = PROVIDER_COST_METRICS.snapshot()
    assert final.get(("ardswc", "provider_failure"), 0) - baseline.get(("ardswc", "provider_failure"), 0) == 1
    assert final.get(("ardswc", "provider_success"), 0) - baseline.get(("ardswc", "provider_success"), 0) == 1


def test_liquefaction_exact_inputs_area_and_contract_invalidate(monkeypatch):
    from services.terrain_risk_providers import geologycloud_provider as module

    calls = []
    provider = GeologyCloudProvider(http_get=lambda url, timeout: calls.append(url) or EMPTY_FEATURES)
    for latitude, longitude, radius, area in [(25, 121, 500, "臺北市"), (25.000000001, 121, 500, "臺北市"),
                                            (25, 121.000000001, 500, "臺北市"), (25, 121, 501, "臺北市"),
                                            (25, 121, 500, "新北市")]:
        assert provider.analyze(latitude, longitude, radius, area)["liquefaction"]["status"] == "available"
    assert len(calls) == 15
    monkeypatch.setattr(module, "QUERY_CONTRACT_VERSION", "updated-test-contract")
    provider.analyze(25, 121, 500, "臺北市")
    assert len(calls) == 18


def test_ardswc_tile_version_and_provider_url_invalidate(monkeypatch):
    from services.terrain_risk_providers import ardswc_slope_hazard_provider as module

    calls = []
    provider = ArdswcSlopeHazardProvider(http_get=lambda url, timeout: calls.append(url) or b"tile", decoder=lambda *_: [])
    args = ("debris_flow", [TileCoord(14, 1, 1)], 25, 121, 100)
    provider._query_mvt_layer(*args)
    monkeypatch.setattr(module, "DATASET_VERSION", "updated-test-vintage")
    provider._query_mvt_layer(*args)
    monkeypatch.setitem(module.MVT_LAYERS["debris_flow"], "url", "https://new-provider.example.tw/{z}/{x}/{y}")
    provider._query_mvt_layer(*args)
    assert len(calls) == 3


def test_liquefaction_cache_expiry_eviction_and_result_isolation():
    now = [0.0]
    calls = []
    provider = GeologyCloudProvider(http_get=lambda url, timeout: calls.append(url) or EMPTY_FEATURES)
    provider._query_cache = BoundedRequestCache("liquefaction", 300, 1, clock=lambda: now[0])
    first = provider.analyze(25, 121, 500, "臺北市")
    first["liquefaction"]["status"] = "error"
    assert provider.analyze(25, 121, 500, "臺北市")["liquefaction"]["status"] == "available"
    assert len(calls) == 3
    now[0] = 300
    provider.analyze(25, 121, 500, "臺北市")
    assert len(calls) == 6
    provider.analyze(25, 121, 501, "臺北市")
    provider.analyze(25, 121, 500, "臺北市")
    assert len(calls) == 12


def test_numeric_nlsc_failure_retries_exact_inputs_and_keeps_fetch_time(monkeypatch):
    from services.terrain_risk_providers import base

    calls = []
    baseline = PROVIDER_COST_METRICS.snapshot()
    clock = ["2026-01-01T00:00:00+00:00"]
    monkeypatch.setattr(base, "utc_now", lambda: clock[0])

    def handler(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"status": "available", "source": "NLSC", "slope_value": 0,
                                         "slope_class": "gentle", "elevation_m": 0})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = NlscTerrainProvider(gateway=NlscGatewayAdapter(client=client, environ={
            "NLSC_GATEWAY_BASE_URL": "https://gateway.example.tw", "NLSC_GATEWAY_CLIENT_TOKEN": "test-only-token-123"}))
        assert provider.analyze(25, 121, 500)["status"] == "unavailable"
        first = provider.analyze(25, 121, 500)
        clock[0] = "2026-01-01T00:00:30+00:00"
        assert provider.analyze(25, 121, 500)["source"]["fetched_at"] == first["source"]["fetched_at"]
        assert len(calls) == 2
        assert provider.analyze(25.000000001, 121, 500)["status"] == "available"
        assert provider.analyze(25, 121.000000001, 500)["status"] == "available"
        assert provider.analyze(25, 121, 501)["status"] == "available"
        assert len(calls) == 5
        final = PROVIDER_COST_METRICS.snapshot()
        assert final.get(("nlsc", "provider_failure"), 0) - baseline.get(("nlsc", "provider_failure"), 0) == 1
        assert final.get(("nlsc", "provider_success"), 0) - baseline.get(("nlsc", "provider_success"), 0) == 4
        assert provider.analyze(25, 121, 500.0)["status"] == "unavailable"
        assert len(calls) == 5


def test_ardswc_cached_tile_keeps_fetch_time_and_rematches_exact_point(monkeypatch):
    from services.terrain_risk_providers import base

    clock = ["2026-01-01T00:00:00+00:00"]
    monkeypatch.setattr(base, "utc_now", lambda: clock[0])
    calls = []
    polygon = {"id": 1, "geometry": {"type": "Polygon", "coordinates": [
        [[120.999, 24.999], [121.001, 24.999], [121.001, 25.001], [120.999, 25.001], [120.999, 24.999]]
    ]}, "properties": {}}
    provider = ArdswcSlopeHazardProvider(http_get=lambda url, timeout: calls.append(url) or b"tile", decoder=lambda *_: [polygon])
    tiles = [TileCoord(14, 1, 1)]
    first = provider._query_mvt_layer("debris_affect", tiles, 25, 121, 100)
    assert first["matched"] is True
    clock[0] = "2026-01-01T00:01:00+00:00"
    second = provider._query_mvt_layer("debris_affect", tiles, 25.01, 121.01, 100)
    assert second["matched"] is False
    assert second["level"] == "unknown"
    assert second["source"]["fetched_at"] == first["source"]["fetched_at"]
    assert len(calls) == 1


def test_numeric_nlsc_concurrent_query_coalesces_and_expiry_version_invalidate(monkeypatch):
    from services.terrain_risk_providers import nlsc_terrain_provider as module

    started, release, coalesced = threading.Event(), threading.Event(), threading.Event()
    now = [0.0]
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            started.set()
            assert release.wait(3)
        return httpx.Response(200, json={"status": "available", "source": "NLSC", "slope_value": 0,
                                         "slope_class": "gentle", "elevation_m": 0})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = NlscTerrainProvider(gateway=NlscGatewayAdapter(client=client, environ={
            "NLSC_GATEWAY_BASE_URL": "https://gateway.example.tw", "NLSC_GATEWAY_CLIENT_TOKEN": "test-only-token-123"}))
        provider._query_cache = BoundedRequestCache("nlsc", 60, 2, clock=lambda: now[0])
        provider._query_cache.metrics = CoalescingProbe(coalesced)
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(provider.analyze, 25, 121, 500)
            assert started.wait(3)
            second = executor.submit(provider.analyze, 25, 121, 500)
            try:
                assert coalesced.wait(3)
            finally:
                release.set()
            assert first.result() == second.result()
        assert len(calls) == 1
        now[0] = 60
        provider.analyze(25, 121, 500)
        assert len(calls) == 2
        monkeypatch.setattr(module, "QUERY_CONTRACT_VERSION", "new-contract-version")
        provider.analyze(25, 121, 500)
        assert len(calls) == 3
        provider._gateway._base_url = "https://other-gateway.example.tw"
        provider.analyze(25, 121, 500)
        assert len(calls) == 4
        assert calls[-1].startswith("https://other-gateway.example.tw/")


@pytest.mark.parametrize("max_entries,max_bytes", [(1, 1024 * 1024), (256, 1)])
def test_ardswc_tile_cache_bounds_eviction_and_expiry(max_entries, max_bytes):
    now = [0.0]
    calls = []
    provider = ArdswcSlopeHazardProvider(http_get=lambda url, timeout: calls.append(url) or b"tile", decoder=lambda *_: [])
    provider._tile_cache = BoundedRequestCache("ardswc", 600, max_entries, max_bytes=max_bytes, clock=lambda: now[0])
    first, second = TileCoord(14, 1, 1), TileCoord(14, 2, 2)
    provider._fetch_and_decode_tile("debris_flow", first, None)
    provider._fetch_and_decode_tile("debris_flow", second, None)
    provider._fetch_and_decode_tile("debris_flow", first, None)
    assert len(calls) == 3
    now[0] = 600
    provider._fetch_and_decode_tile("debris_flow", first, None)
    assert len(calls) == 4


def test_default_instances_share_warm_process_caches(monkeypatch):
    from services.terrain_risk_providers import ardswc_slope_hazard_provider as ardswc
    from services.terrain_risk_providers import geologycloud_provider as geology
    from services.terrain_risk_providers import nlsc_terrain_provider as nlsc

    calls = {"ardswc": 0, "liquefaction": 0, "nlsc": 0}

    def tile_fetch(*args):
        calls["ardswc"] += 1
        return b"tile"

    def geology_fetch(*args):
        calls["liquefaction"] += 1
        return EMPTY_FEATURES

    def gateway_fetch(request):
        calls["nlsc"] += 1
        return httpx.Response(200, json={"status": "available", "source": "NLSC", "slope_value": 0,
                                         "slope_class": "gentle", "elevation_m": 0})

    monkeypatch.setattr(ardswc, "_DECODED_TILE_CACHE", BoundedRequestCache("ardswc", 600, 256, max_bytes=16 * 1024 * 1024))
    monkeypatch.setattr(geology, "_QUERY_CACHE", BoundedRequestCache("liquefaction", 300, 64))
    monkeypatch.setattr(nlsc, "_QUERY_CACHE", BoundedRequestCache("nlsc", 60, 64))
    monkeypatch.setattr(ArdswcSlopeHazardProvider, "_http_get", staticmethod(tile_fetch))
    monkeypatch.setattr(ArdswcSlopeHazardProvider, "_decode_mvt", lambda *_: [])
    monkeypatch.setattr(ardswc, "_optional_decoder_available", lambda: True)
    monkeypatch.setattr(GeologyCloudProvider, "_fetch", geology_fetch)
    with httpx.Client(transport=httpx.MockTransport(gateway_fetch)) as client:
        gateway = NlscGatewayAdapter(client=client, environ={"NLSC_GATEWAY_BASE_URL": "https://gateway.example.tw",
                                                          "NLSC_GATEWAY_CLIENT_TOKEN": "test-only-token-123"})
        monkeypatch.setattr(nlsc, "NlscGatewayAdapter", lambda: gateway)
        for _ in range(2):
            assert ArdswcSlopeHazardProvider()._query_mvt_layer("debris_flow", [TileCoord(14, 1, 1)], 25, 121, 100)["status"] == "available"
            assert GeologyCloudProvider().analyze(25, 121, 500, "臺北市")["liquefaction"]["status"] == "available"
            assert NlscTerrainProvider().analyze(25, 121, 500)["status"] == "available"
    assert calls == {"ardswc": 1, "liquefaction": 3, "nlsc": 1}
