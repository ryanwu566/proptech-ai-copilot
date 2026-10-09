"""Deterministic Satellite generation budgets; never contact Earth Engine."""

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from services import satellite_reference as satellite


NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolated_cache():
    cache = getattr(satellite, "_SATELLITE_CACHE", None)
    if cache is not None:
        cache.clear()
    yield
    if cache is not None:
        cache.clear()


class Adapter:
    def __init__(self):
        self.calls = []
        self.error = None

    def fetch(self, query):
        self.calls.append(query)
        if self.error:
            raise self.error
        return satellite.SatelliteAdapterResult(b"\xff\xd8bounded-jpeg\xff\xd9")


async def request(adapter=None, **overrides):
    return await satellite.fetch_satellite_reference(**{
        "latitude": 25.0375, "longitude": 121.5645, "now": NOW,
        "adapter": adapter, **overrides,
    })


def test_repeated_success_reuses_generation_and_original_retrieval_time():
    adapter = Adapter()
    first = asyncio.run(request(adapter))
    second = asyncio.run(request(adapter, now=NOW + timedelta(seconds=10)))
    assert first.status == second.status == "available"
    assert second.retrieval_time == first.retrieval_time
    assert len(adapter.calls) == 1


def test_concurrent_requests_share_one_generation_without_blocking_event_loop(monkeypatch):
    class Manager:
        def __init__(self):
            self.calls = 0

        async def fetch(self, **_kwargs):
            self.calls += 1
            await asyncio.sleep(0.025)
            return b"jpeg"

    manager = Manager()
    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", lambda: manager)

    async def journey():
        # More waiters than the default executor's workers cannot starve generation.
        responses = await asyncio.wait_for(asyncio.gather(*(request() for _ in range(64))), timeout=1)
        repeated = await request()
        return responses, repeated

    responses, repeated = asyncio.run(journey())
    assert all(result.status == "available" for result in [*responses, repeated])
    assert manager.calls == 1


def test_failure_does_not_become_a_success_cache_hit():
    adapter = Adapter()
    adapter.error = satellite.EarthEngineProviderTimeout("bounded timeout")
    failed = asyncio.run(request(adapter))
    adapter.error = None
    recovered = asyncio.run(request(adapter))
    assert failed.status == "unavailable" and failed.reason_code == "provider_timeout"
    assert recovered.status == "available"
    assert len(adapter.calls) == 2


def test_logical_requests_and_physical_generation_metrics_separate_cache_reuse():
    from services.provider_cost_metrics import PROVIDER_COST_METRICS

    before = PROVIDER_COST_METRICS.snapshot()
    adapter = Adapter()
    asyncio.run(request(adapter))
    asyncio.run(request(adapter))
    after = PROVIDER_COST_METRICS.snapshot()
    for event, expected in {"logical_requests": 2, "physical_calls": 1,
                            "cache_hit": 1, "avoided_operations": 1}.items():
        key = ("satellite", event)
        assert after.get(key, 0) - before.get(key, 0) == expected


def test_property_date_and_configuration_changes_require_new_generation(monkeypatch):
    adapter = Adapter()
    asyncio.run(request(adapter))
    asyncio.run(request(adapter, latitude=25.0376))
    asyncio.run(request(adapter, now=NOW + timedelta(days=1)))
    monkeypatch.setattr(satellite, "DATASET_ID", "new-dataset-version")
    asyncio.run(request(adapter))
    assert len(adapter.calls) == 4


def test_cached_response_is_not_mutable_shared_evidence():
    adapter = Adapter()
    first = asyncio.run(request(adapter))
    first.limitations.clear()
    first.status = "unavailable"
    second = asyncio.run(request(adapter))
    assert second.status == "available"
    assert second.limitations
    assert len(adapter.calls) == 1


def test_material_satellite_query_inputs_have_distinct_keys():
    query = satellite._fixed_query(25.0375, 121.5645, NOW)
    changes = {
        "latitude": 25.0376, "longitude": 121.5646, "dataset": "other",
        "window_start": "2026-06-21", "window_end": "2026-09-21",
        "aoi_radius_m": 501, "cloud_filter_percent": 36,
        "rgb_bands": ("B3", "B4", "B2"), "excluded_scl_classes": (3, 8),
        "dimensions": (256, 256), "image_format": "png",
    }
    for field, value in changes.items():
        assert query != replace(query, **{field: value})


def test_provider_identity_does_not_reuse_recycled_object_ids_or_retain_credentials():
    import gc
    import weakref

    adapter = Adapter()
    reference = weakref.ref(adapter)
    key = satellite._ProviderIdentity(adapter)
    assert key == satellite._ProviderIdentity(adapter)
    del adapter
    gc.collect()
    assert reference() is None
    assert key != satellite._ProviderIdentity(Adapter())


def test_entry_and_byte_bounds_evict_completed_images(monkeypatch):
    from services.provider_request_cache import BoundedRequestCache

    clock = [0.0]
    cache = BoundedRequestCache("satellite", ttl_seconds=300, max_entries=2,
                                max_bytes=1600, clock=lambda: clock[0])
    monkeypatch.setattr(satellite, "_SATELLITE_CACHE", cache)
    adapter = Adapter()
    # Metadata plus JPEG exceeds 800 bytes; the byte budget retains at most one.
    asyncio.run(request(adapter))
    asyncio.run(request(adapter, latitude=25.038))
    asyncio.run(request(adapter))
    assert len(adapter.calls) == 3
    clock[0] = 301
    asyncio.run(request(adapter))
    assert len(adapter.calls) == 4


def test_cache_contract_bounds_are_strict_and_only_embedded_images_are_reused():
    assert satellite.SATELLITE_CACHE_TTL_SECONDS == 300
    assert satellite.SATELLITE_CACHE_MAX_ENTRIES == 16
    assert satellite.SATELLITE_CACHE_MAX_BYTES == 4 * 1024 * 1024
    available = satellite.build_response(status="available", reason_code=None,
                                         image_reference="data:image/jpeg;base64,/9j/2Q==", now=NOW)
    assert satellite._cacheable_response(available)
    assert not satellite._cacheable_response(available.model_copy(update={"status": "limited"}))
    assert not satellite._cacheable_response(available.model_copy(update={"image_reference": "https://provider.test/?token=secret"}))


def test_optional_manager_initialization_failure_stays_unavailable(monkeypatch):
    def fail():
        raise RuntimeError("provider credential must remain private")

    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", fail)
    result = asyncio.run(request())
    assert result.status == "unavailable"
    assert result.reason_code == "provider_error"
    assert "credential" not in result.model_dump_json()


def test_manager_capacity_rejection_is_not_counted_as_physical_generation(monkeypatch):
    from services.earth_engine_worker_pool import EarthEngineWorkerManager, MAX_ADMITTED_REQUESTS
    from services.provider_cost_metrics import PROVIDER_COST_METRICS

    manager = EarthEngineWorkerManager()
    manager._state = "available"
    for _ in range(MAX_ADMITTED_REQUESTS):
        assert manager._admission_slots.acquire(blocking=False)
    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", lambda: manager)
    before = PROVIDER_COST_METRICS.snapshot().get(("satellite", "physical_calls"), 0)
    result = asyncio.run(request())
    after = PROVIDER_COST_METRICS.snapshot().get(("satellite", "physical_calls"), 0)
    assert result.status == "unavailable"
    assert result.reason_code == "provider_error"
    assert after - before == 0
