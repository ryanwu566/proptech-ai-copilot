"""Provider-neutral route/lifecycle tests: synthetic adapters, never provider calls."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import api_main
from services import satellite_reference as satellite


@pytest.fixture(autouse=True)
def imagery_profile(monkeypatch):
    monkeypatch.delenv("SATELLITE_REFERENCE_PROVIDER", raising=False)
    monkeypatch.delenv("CSRSR_SPOT_NONCOMMERCIAL_USE", raising=False)
    monkeypatch.delenv("ANTI_ABUSE_SATELLITE_DISABLED", raising=False)
    monkeypatch.setattr(satellite, "_get_earth_engine_worker_manager", lambda: pytest.fail("EE resolved in Taiwan mode"))
    satellite.clear_satellite_reference_cache()
    yield
    satellite.clear_satellite_reference_cache()


class Adapter:
    def __init__(self, provider="nlsc_photo2", error=None):
        self.calls = []
        self.provider = provider
        self.error = error

    def fetch(self, query):
        self.calls.append(query)
        if self.error:
            raise self.error
        return SimpleNamespace(
            image_bytes=b"synthetic-validated-jpeg", provider=self.provider,
            source_type="orthophoto" if self.provider == "nlsc_photo2" else "satellite",
            source="NLSC PHOTO2" if self.provider == "nlsc_photo2" else "CSRSR SPOT",
            dataset_or_layer="PHOTO2" if self.provider == "nlsc_photo2" else "SP2025NC_3857",
            processing_method="Bounded WMS reference" if self.provider == "nlsc_photo2" else "Annual WMTS mosaic crop",
            attribution="Source attribution", limitations=("Context only",),
            bbox=(13519488.0, 2879559.0, 13520591.0, 2880668.0),
            vintage=None if self.provider == "nlsc_photo2" else "2025", observation_date=None,
            date_precision="unknown" if self.provider == "nlsc_photo2" else "year",
            usage_restriction=None if self.provider == "nlsc_photo2" else "Non-commercial / competition use only",
        )


def request(adapter=None, **kwargs):
    return satellite.fetch_satellite_reference(latitude=25.03557, longitude=121.45258,
        imagery_adapter=adapter, **kwargs)


def test_default_orthophoto_unknown_vintage_not_retrieval_date():
    result = asyncio.run(request(Adapter(), now=datetime(2026, 10, 30, tzinfo=timezone.utc)))
    assert result.provider == "nlsc_photo2" and result.source_type == "orthophoto"
    assert result.status == "limited" and result.reason_code == "vintage_unknown"
    assert result.image_reference.startswith("data:image/jpeg;base64,")
    assert result.observation_date is result.vintage is None
    assert result.window_start is result.window_end is result.cloud_filter_percent is None
    assert result.date_precision == "unknown" and result.retrieval_time.startswith("2026-10-30")
    assert result.bbox_crs == "EPSG:3857" and result.center == {"latitude": 25.03557, "longitude": 121.45258}
    assert "Sentinel" not in result.model_dump_json() and "SCL" not in result.model_dump_json()


def test_csrsr_requires_explicit_competition_gate(monkeypatch):
    monkeypatch.setenv("SATELLITE_REFERENCE_PROVIDER", "csrsr_spot")
    adapter = Adapter("csrsr_spot")
    blocked = asyncio.run(request(adapter))
    assert blocked.status == "unavailable" and blocked.reason_code == "licensing_not_accepted"
    assert adapter.calls == []
    monkeypatch.setenv("CSRSR_SPOT_NONCOMMERCIAL_USE", "true")
    result = asyncio.run(request(adapter))
    assert result.provider == "csrsr_spot" and result.source_type == "satellite"
    assert result.date_precision == "year" and result.vintage == "2025" and result.observation_date is None
    assert result.cloud_filter_percent is None and result.window_start is None
    assert "Non-commercial" in result.usage_restriction


def test_unknown_provider_has_no_fallback(monkeypatch):
    monkeypatch.setenv("SATELLITE_REFERENCE_PROVIDER", "https://attacker.invalid")
    adapter = Adapter()
    result = asyncio.run(request(adapter))
    assert result.status == "unavailable" and result.reason_code == "configuration_error"
    assert result.provider == "unknown" and not adapter.calls
    assert "attacker" not in result.model_dump_json()


def test_no_completed_taiwan_image_cache():
    adapter = Adapter()
    first = asyncio.run(request(adapter))
    second = asyncio.run(request(adapter))
    assert first.image_reference and second.image_reference
    assert len(adapter.calls) == 2


def test_duplicate_inflight_only_is_coalesced():
    import threading
    import time
    entered = threading.Event()
    class Slow(Adapter):
        def fetch(self, query):
            entered.set()
            time.sleep(0.03)
            return super().fetch(query)
    adapter = Slow()
    async def journey():
        return await asyncio.gather(*(request(adapter) for _ in range(8)))
    results = asyncio.run(journey())
    assert len(adapter.calls) == 1 and entered.is_set()
    assert all(result.image_reference for result in results)


def test_provider_error_redacts_details():
    result = asyncio.run(request(Adapter(error=RuntimeError("private_key=not-public"))))
    assert result.status == "unavailable" and result.image_reference is None
    assert "not-public" not in result.model_dump_json()


@pytest.mark.parametrize("provider", ["nlsc_photo2", "csrsr_spot", "unsupported"])
def test_non_ee_lifespan_never_resolves_ee(monkeypatch, provider):
    monkeypatch.setenv("SATELLITE_REFERENCE_PROVIDER", provider)
    monkeypatch.setenv("EARTH_ENGINE_SATELLITE_REFERENCE_V1", "true")
    monkeypatch.setattr(api_main, "_get_earth_engine_worker_manager", lambda: pytest.fail("EE startup resolved"))
    with TestClient(api_main.app) as client:
        assert client.get("/health").status_code == 200


def test_route_shape_and_additive_response(monkeypatch):
    adapter = Adapter()
    monkeypatch.setattr(satellite, "_configured_imagery_adapter", lambda *_: adapter)
    with TestClient(api_main.app) as client:
        result = client.post("/terrain/satellite-reference", json={"latitude": 25.03, "longitude": 121.45})
        assert result.status_code == 200 and result.json()["source_type"] == "orthophoto"
        assert client.post("/terrain/satellite-reference", json={"latitude": 25.03, "longitude": 121.45, "layer": "evil"}).status_code == 422


def test_satellite_kill_switch_is_preserved(monkeypatch):
    from services.anti_abuse import AbuseRejected
    monkeypatch.setenv("ANTI_ABUSE_SATELLITE_DISABLED", "true")
    adapter = Adapter()
    with pytest.raises(AbuseRejected):
        asyncio.run(request(adapter))
    assert not adapter.calls


def test_configuration_and_passive_observations_use_selected_provider():
    from services.provider_config_contract import configuration_status
    from services.provider_observability import ProviderObservations, observe_response
    assert configuration_status("satellite", {}) == {"SATELLITE_REFERENCE_PROVIDER": "present"}
    assert configuration_status("satellite", {"SATELLITE_REFERENCE_PROVIDER": "bad"}) == {"SATELLITE_REFERENCE_PROVIDER": "invalid-contract"}
    csrsr = configuration_status("satellite", {"SATELLITE_REFERENCE_PROVIDER": "csrsr_spot"})
    assert csrsr["CSRSR_SPOT_NONCOMMERCIAL_USE"] == "invalid-contract"
    assert csrsr["CSRSR_SPOT_YEAR"] == "present"
    result = asyncio.run(request(Adapter()))
    from services import provider_observability
    old = provider_observability.provider_observations
    provider_observability.provider_observations = ProviderObservations()
    try:
        observe_response("satellite", result.model_dump())
        record = provider_observability.provider_observations.snapshot()["satellite"]
        assert record["source"] == "nlsc_photo2" and record["reason_code"] == "vintage_unknown"
        assert record["freshness"] == "unknown" and "image_reference" not in record
    finally:
        provider_observability.provider_observations = old


def test_timeout_keeps_physical_slot_until_worker_finishes():
    import threading
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    class Slow(Adapter):
        def fetch(self, query):
            entered.set()
            release.wait(1)
            try:
                return super().fetch(query)
            finally:
                finished.set()
    adapter = Slow()
    async def journey():
        first = await request(adapter, timeout_seconds=0.05)
        assert entered.is_set() and first.reason_code == "provider_timeout"
        second = await request(Adapter())
        assert second.reason_code == "provider_capacity_exhausted"
    try:
        asyncio.run(journey())
    finally:
        release.set()
        assert finished.wait(1)


def test_provider_configuration_is_names_only_and_does_not_open_local_guards():
    from services.selfhost_secret_files import validate_nonsecret_env, validate_local_guards, SecretRefused
    validate_nonsecret_env("SATELLITE_REFERENCE_PROVIDER=nlsc_photo2\nCSRSR_SPOT_YEAR=2025\nCSRSR_SPOT_NONCOMMERCIAL_USE=false\n")
    with pytest.raises(SecretRefused):
        validate_nonsecret_env("ANTI_ABUSE_SATELLITE_DISABLED=false\n")
    # Merely selecting a public provider never makes an incomplete protected
    # Professor profile acceptable or activates paid capabilities.
    with pytest.raises(SecretRefused):
        validate_local_guards({"SATELLITE_REFERENCE_PROVIDER": "nlsc_photo2"})


@pytest.mark.parametrize("year,checked_year", [("2026", 2026), ("2026", 2030), ("2025", 2024), ("1995", 2026)])
def test_csrsr_invalid_or_future_year_never_admits_adapter(monkeypatch, year, checked_year):
    from services.provider_config_contract import configuration_status
    monkeypatch.setenv("SATELLITE_REFERENCE_PROVIDER", "csrsr_spot")
    monkeypatch.setenv("CSRSR_SPOT_NONCOMMERCIAL_USE", "true")
    monkeypatch.setenv("CSRSR_SPOT_YEAR", year)
    monkeypatch.setattr(satellite, "_configured_imagery_adapter", lambda *_: pytest.fail("adapter constructed"))
    monkeypatch.setattr(satellite, "provider_operation", lambda *_ , **__: pytest.fail("operation admitted"))
    adapter = Adapter("csrsr_spot")
    result = asyncio.run(request(adapter, now=datetime(checked_year, 10, 30, tzinfo=timezone.utc)))
    assert result.status == "unavailable" and result.reason_code == "configuration_error"
    assert result.image_reference is None and not adapter.calls
    if year != "2025":
        assert configuration_status("satellite", {"SATELLITE_REFERENCE_PROVIDER": "csrsr_spot", "CSRSR_SPOT_YEAR": year})["CSRSR_SPOT_YEAR"] == "invalid-contract"
