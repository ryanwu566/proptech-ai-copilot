"""Safe public contract for bounded satellite reference imagery."""

from __future__ import annotations

import base64
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
import weakref
import os
import threading
import contextvars
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from services.imagery_reference import CSRSR_MIN_YEAR, CSRSR_MAX_YEAR
from services.provider_cost_metrics import PROVIDER_COST_METRICS
from services.provider_request_cache import BoundedRequestCache
from services.anti_abuse import ensure_enabled, provider_operation


DATASET_ID = "COPERNICUS/S2_SR_HARMONIZED"
SOURCE_LABEL = "Sentinel-2 / Copernicus"
AOI_RADIUS_M = 500
WINDOW_DAYS = 90
CLOUD_FILTER_PERCENT = 35
MAX_IMAGE_REFERENCE_CHARS = 360_000
MAX_PROVIDER_IMAGE_BYTES = 250_000
MAX_RESPONSE_BYTES = 365_000
EXTERNAL_TIMEOUT_SECONDS = 8.0
SATELLITE_CONFIG_VERSION = "sentinel2-reference-v1-rgb-0-3000"
SATELLITE_CACHE_TTL_SECONDS = 300
SATELLITE_CACHE_MAX_ENTRIES = 16
SATELLITE_CACHE_MAX_BYTES = 4 * 1024 * 1024
_SATELLITE_CACHE = BoundedRequestCache(
    "satellite", ttl_seconds=SATELLITE_CACHE_TTL_SECONDS,
    max_entries=SATELLITE_CACHE_MAX_ENTRIES, max_bytes=SATELLITE_CACHE_MAX_BYTES,
)
# Taiwan live imagery is retained only while the same request is in flight.
# No completed image or failed result is cached or persisted.
_TAIWAN_SINGLE_FLIGHT = BoundedRequestCache("satellite", ttl_seconds=0, max_entries=16)
_TAIWAN_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="imagery-reference")
_TAIWAN_SLOTS = threading.BoundedSemaphore(1)
TAIWAN_CONFIG_VERSION = "taiwan-live-imagery-v1"
IMAGERY_PROVIDERS = frozenset({"nlsc_photo2", "csrsr_spot", "earth_engine"})
CONTEXT_DISCLAIMER = (
    "Visual context only; not real-time, cadastral or statutory evidence. "
    "Does not establish parcel boundaries, ownership, building legality, disaster safety or lawful land use."
)
DISCLAIMER = "Satellite reference imagery — not cadastral or statutory evidence."
LIMITATIONS = (
    "Cloud filtering and masking may leave residual cloud, haze, or incomplete coverage.",
    "SCL masking excludes cloud shadow (3), medium/high probability cloud (8/9), cirrus (10), and snow or ice (11).",
    "The median satellite reference composite may combine observations across the fixed 90-day window.",
    "The fixed 500 m radius context area is not a parcel boundary.",
)


class SatelliteReferenceResponse(BaseModel):
    status: Literal["available", "limited", "unavailable"]
    reason_code: str | None
    source: str
    dataset: str
    window_start: str | None
    window_end: str | None
    retrieval_time: str
    aoi_radius_m: int
    composite_method: str
    cloud_filter_percent: int | None
    image_reference: str | None = Field(default=None, max_length=MAX_IMAGE_REFERENCE_CHARS)
    attribution: str
    limitations: list[str]
    disclaimer: str
    provider: Literal["nlsc_photo2", "csrsr_spot", "earth_engine", "unknown"] = "unknown"
    source_type: Literal["orthophoto", "satellite"] | None = None
    dataset_or_layer: str = ""
    observation_date: str | None = None
    vintage: str | None = None
    date_precision: Literal["unknown", "year", "range", "day"] = "unknown"
    processing_method: str = ""
    center: dict[str, float] | None = None
    bbox: tuple[float, float, float, float] | None = None
    bbox_crs: Literal["EPSG:3857"] | None = None
    usage_restriction: str | None = None


@dataclass(frozen=True)
class SatelliteQuery:
    latitude: float
    longitude: float
    dataset: str
    window_start: str
    window_end: str
    aoi_radius_m: int
    cloud_filter_percent: int
    rgb_bands: tuple[str, str, str]
    excluded_scl_classes: tuple[int, ...]
    dimensions: tuple[int, int]
    image_format: str


@dataclass(frozen=True)
class SatelliteAdapterResult:
    image_bytes: bytes


class SatelliteAdapter(Protocol):
    def fetch(self, query: SatelliteQuery) -> SatelliteAdapterResult: ...


class _ProviderIdentity:
    """Instance identity without retaining provider state or recycled-ID hits."""
    def __init__(self, provider) -> None:
        self._id = id(provider)
        self._reference = weakref.ref(provider)

    def __hash__(self) -> int:
        return self._id

    def __eq__(self, other) -> bool:
        if not isinstance(other, _ProviderIdentity):
            return NotImplemented
        provider = self._reference()
        return provider is not None and provider is other._reference()


class EarthEngineCredentialUnavailable(RuntimeError):
    """Application Default Credentials are unavailable."""


class EarthEngineFeatureDisabled(RuntimeError):
    """The optional Earth Engine capability is disabled."""


class EarthEngineInitializationUnavailable(RuntimeError):
    """Earth Engine client initialization failed after credentials were obtained."""


class EarthEngineProviderError(RuntimeError):
    """The bounded Earth Engine query failed."""


class EarthEngineProviderTimeout(EarthEngineProviderError):
    """The bounded Earth Engine operation exceeded its total time limit."""


class EarthEngineImageGenerationError(RuntimeError):
    """The bounded provider image could not be generated or downloaded."""


def feature_enabled(value: str) -> bool:
    return value.strip().lower() == "true"


def selected_imagery_provider() -> str:
    """An operator-controlled finite selector; never a request parameter."""
    configured = os.getenv("SATELLITE_REFERENCE_PROVIDER", "nlsc_photo2").strip().lower()
    return configured if configured in IMAGERY_PROVIDERS else "unknown"


def build_response(
    *,
    status: Literal["available", "limited", "unavailable"],
    reason_code: str | None,
    image_reference: str | None = None,
    now: datetime | None = None,
) -> SatelliteReferenceResponse:
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    window_end = checked_at.date()
    window_start = window_end - timedelta(days=WINDOW_DAYS)
    return SatelliteReferenceResponse(
        status=status,
        reason_code=reason_code,
        source=SOURCE_LABEL,
        dataset=DATASET_ID,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        retrieval_time=checked_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        aoi_radius_m=AOI_RADIUS_M,
        composite_method="Median satellite reference composite using Sentinel-2 B4/B3/B2 across the fixed 90-day window.",
        cloud_filter_percent=CLOUD_FILTER_PERCENT,
        image_reference=image_reference,
        attribution="Contains modified Copernicus Sentinel data processed by Google Earth Engine.",
        limitations=list(LIMITATIONS),
        disclaimer=DISCLAIMER,
        provider="earth_engine", source_type="satellite", dataset_or_layer=DATASET_ID,
        date_precision="range",
        processing_method="Sentinel-2 90-day median RGB composite with SCL cloud masking",
    )


def _taiwan_response(provider, latitude, longitude, checked_at, *, reason_code=None, result=None):
    """Do not substitute retrieval time, cloud metadata or EE dates for source facts."""
    known = provider in {"nlsc_photo2", "csrsr_spot"}
    is_photo = provider == "nlsc_photo2"
    source = "NLSC PHOTO2 / 國土測繪中心" if is_photo else "CSRSR SPOT / 中央大學太遙中心" if known else "Unconfigured imagery provider"
    layer = "PHOTO2" if is_photo else ""  # An annual layer is only confirmed by capabilities.
    method = "On-demand bounded WMS orthophoto reference" if is_photo else "Bounded annual WMTS satellite mosaic reference" if known else "Unavailable"
    limitations = [
        "Visual context does not change the risk score or establish hazard safety.",
        "A 500 m context radius defines the bounding box; it is not a legal parcel boundary.",
        "Retrieval time is not the imagery observation date.",
    ]
    if is_photo:
        limitations.append("The PHOTO2 source vintage is unknown; different areas may have different acquisition dates.")
    if provider == "csrsr_spot":
        limitations.append("Annual mosaic reference; the year is not a single acquisition date. Non-commercial / competition use only.")
    if result is not None:
        source, layer, method = result.source, result.dataset_or_layer, result.processing_method
        limitations.extend(result.limitations)
    return SatelliteReferenceResponse(
        status="unavailable" if result is None else "limited" if is_photo else "available",
        reason_code=reason_code if result is None else "vintage_unknown" if is_photo else None,
        provider=provider, source_type=("orthophoto" if is_photo else "satellite") if known else None,
        source=source, dataset=layer, dataset_or_layer=layer,
        window_start=None, window_end=None, cloud_filter_percent=None,
        observation_date=result.observation_date if result else None,
        vintage=result.vintage if result else None,
        date_precision=result.date_precision if result else "unknown",
        retrieval_time=checked_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        aoi_radius_m=AOI_RADIUS_M, composite_method=method, processing_method=method,
        center={"latitude": latitude, "longitude": longitude},
        bbox=result.bbox if result else None, bbox_crs="EPSG:3857" if result else None,
        image_reference="data:image/jpeg;base64," + base64.b64encode(result.image_bytes).decode("ascii") if result else None,
        attribution=result.attribution if result else source if known else "",
        limitations=limitations, disclaimer=CONTEXT_DISCLAIMER,
        usage_restriction=result.usage_restriction if result else "Non-commercial / competition use only" if provider == "csrsr_spot" else None,
    )


def _configured_imagery_adapter(provider, year):
    # Importing/constructing a Taiwan adapter never imports EE or discovers ADC.
    from services.imagery_providers import NLSCOrthophotoAdapter, CSRSRSpotAdapter
    if provider == "nlsc_photo2":
        return NLSCOrthophotoAdapter()
    return CSRSRSpotAdapter(year=year, noncommercial_use=True)


async def _fetch_taiwan_reference(latitude, longitude, provider, adapter, checked_at, deadline):
    def unavailable(reason):
        return _taiwan_response(provider, latitude, longitude, checked_at, reason_code=reason)

    if provider == "unknown":
        return unavailable("configuration_error")
    year = None
    if provider == "csrsr_spot":
        if not feature_enabled(os.getenv("CSRSR_SPOT_NONCOMMERCIAL_USE", "")):
            return unavailable("licensing_not_accepted")
        raw_year = os.getenv("CSRSR_SPOT_YEAR", "2025")
        if len(raw_year) != 4 or not raw_year.isascii() or not raw_year.isdigit():
            return unavailable("configuration_error")
        year = int(raw_year)
        if not CSRSR_MIN_YEAR <= year <= min(CSRSR_MAX_YEAR, checked_at.year):
            return unavailable("configuration_error")
    # A stable config key deduplicates production requests. Weak instance identity
    # isolates injected adapters without retaining their state after completion.
    identity = _ProviderIdentity(adapter) if adapter is not None else None
    key = (TAIWAN_CONFIG_VERSION, provider, year, latitude, longitude, identity)

    async def generate():
        return await _generate_taiwan_reference(
            provider, year, adapter, latitude, longitude, checked_at, deadline,
        )
    try:
        response = await asyncio.wait_for(_TAIWAN_SINGLE_FLIGHT.async_run(
            key, generate, cacheable=lambda _: False,
        ), timeout=max(0, deadline - time.monotonic()))
    except asyncio.TimeoutError:
        return unavailable("provider_timeout")
    return response.model_copy(deep=True)


@provider_operation("satellite")
async def _generate_taiwan_reference(provider, year, adapter, latitude, longitude, checked_at, deadline):
    from services.imagery_reference import ImageryQuery, ImageryProviderError

    def unavailable(reason):
        return _taiwan_response(provider, latitude, longitude, checked_at, reason_code=reason)

    # A timed-out caller cannot release this physical-work slot while a bounded
    # transport is still unwinding. No unbounded executor queue is admitted.
    if deadline <= time.monotonic():
        return unavailable("provider_timeout")
    if not _TAIWAN_SLOTS.acquire(blocking=False):
        return unavailable("provider_capacity_exhausted")
    try:
        selected_adapter = adapter if adapter is not None else _configured_imagery_adapter(provider, year)
        query = ImageryQuery(latitude=latitude, longitude=longitude, deadline=deadline)
        context = contextvars.copy_context()
        future = _TAIWAN_EXECUTOR.submit(context.run, selected_adapter.fetch, query)
        future.add_done_callback(lambda _: _TAIWAN_SLOTS.release())
    except Exception:
        _TAIWAN_SLOTS.release()
        return unavailable("configuration_error")
    wrapped = asyncio.wrap_future(future)
    wrapped.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
    try:
        result = await asyncio.wait_for(asyncio.shield(wrapped), timeout=max(0, deadline - time.monotonic()))
        if (result.provider != provider or result.source_type != ("orthophoto" if provider == "nlsc_photo2" else "satellite")
                or not result.image_bytes or len(result.image_bytes) > MAX_PROVIDER_IMAGE_BYTES):
            return unavailable("image_generation_failed")
        response = _taiwan_response(provider, latitude, longitude, checked_at, result=result)
        if time.monotonic() >= deadline:
            return unavailable("provider_timeout")
        if len(response.model_dump_json().encode("utf-8")) > MAX_RESPONSE_BYTES:
            return unavailable("image_generation_failed")
    except (asyncio.TimeoutError, TimeoutError):
        PROVIDER_COST_METRICS.record("satellite", "provider_timeout", provider=provider)
        return unavailable("provider_timeout")
    except ImageryProviderError as error:
        timeout = error.reason_code == "timeout"
        PROVIDER_COST_METRICS.record("satellite", "provider_timeout" if timeout else "provider_failure", provider=provider)
        return unavailable("provider_timeout" if timeout else error.reason_code)
    except Exception:
        PROVIDER_COST_METRICS.record("satellite", "provider_failure", provider=provider)
        return unavailable("provider_error")
    PROVIDER_COST_METRICS.record("satellite", "provider_success", provider=provider)
    return response


def _fixed_query(latitude: float, longitude: float, checked_at: datetime) -> SatelliteQuery:
    window_end = checked_at.date()
    window_start = window_end - timedelta(days=WINDOW_DAYS)
    return SatelliteQuery(
        latitude=latitude,
        longitude=longitude,
        dataset=DATASET_ID,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        aoi_radius_m=AOI_RADIUS_M,
        cloud_filter_percent=CLOUD_FILTER_PERCENT,
        rgb_bands=("B4", "B3", "B2"),
        excluded_scl_classes=(3, 8, 9, 10, 11),
        dimensions=(512, 512),
        image_format="jpg",
    )


def _get_earth_engine_worker_manager():
    """Import lazily to avoid starting or importing worker machinery at module load."""

    from services.earth_engine_worker_pool import get_earth_engine_worker_manager

    return get_earth_engine_worker_manager()


async def fetch_satellite_reference(
    *,
    latitude: float,
    longitude: float,
    adapter: SatelliteAdapter | None = None,
    imagery_adapter=None,
    now: datetime | None = None,
    timeout_seconds: float = EXTERNAL_TIMEOUT_SECONDS,
) -> SatelliteReferenceResponse:
    deadline = time.monotonic() + timeout_seconds
    ensure_enabled("satellite")
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    provider = selected_imagery_provider()
    if provider != "earth_engine":
        return await _fetch_taiwan_reference(
            latitude, longitude, provider, imagery_adapter, checked_at, deadline,
        )
    query = _fixed_query(latitude, longitude, checked_at)
    try:
        manager = _get_earth_engine_worker_manager() if adapter is None else None
    except Exception:
        PROVIDER_COST_METRICS.record("satellite", "provider_failure")
        return build_response(status="unavailable", reason_code="provider_error", now=checked_at)
    # Production's manager captures one fixed project at startup. Its lifecycle
    # clears this cache before reconfiguration; weak identities isolate adapters.
    key = (SATELLITE_CONFIG_VERSION, _ProviderIdentity(adapter if adapter is not None else manager),
           getattr(manager, "state", None), query)
    async def generate() -> SatelliteReferenceResponse:
        if deadline <= time.monotonic():
            return build_response(status="unavailable", reason_code="provider_timeout", now=checked_at)
        return await _generate_reference(query, adapter, manager, checked_at, deadline)

    # Native async waiters do not occupy executor threads. The worker manager
    # retains its original absolute deadline and bounded process containment.
    try:
        response = await asyncio.wait_for(_SATELLITE_CACHE.async_run(
            key, generate, cacheable=_cacheable_response,
            size_of=lambda value: len(value.model_dump_json().encode("utf-8")),
        ), timeout=max(0, deadline - time.monotonic()))
    except asyncio.TimeoutError:
        return build_response(status="unavailable", reason_code="provider_timeout", now=checked_at)
    return response.model_copy(deep=True)


def clear_satellite_reference_cache() -> None:
    """Invalidate completed imagery when the fixed provider lifecycle changes."""
    _SATELLITE_CACHE.clear()
    _TAIWAN_SINGLE_FLIGHT.clear()


def _cacheable_response(response: SatelliteReferenceResponse) -> bool:
    # Only downloaded embedded imagery is reused: no signed provider URLs or
    # credentials survive generation, and URL expiration cannot break a hit.
    return (response.status == "available" and response.reason_code is None
            and bool(response.image_reference)
            and response.image_reference.startswith("data:image/jpeg;base64,"))


@provider_operation("satellite")
async def _generate_reference(
    query: SatelliteQuery, adapter: SatelliteAdapter | None, manager,
    checked_at: datetime, deadline: float,
) -> SatelliteReferenceResponse:

    try:
        if adapter is None:
            # The manager counts only actual worker generation dispatches,
            # after admission and slot acquisition have succeeded.
            image_bytes = await manager.fetch(
                latitude=query.latitude,
                longitude=query.longitude,
                window_start=query.window_start,
                window_end=query.window_end,
                deadline=deadline,
            )
            provider_result = SatelliteAdapterResult(image_bytes=image_bytes)
        else:
            PROVIDER_COST_METRICS.record("satellite", "physical_calls")
            provider_result = await asyncio.to_thread(adapter.fetch, query)
    except EarthEngineProviderTimeout:
        PROVIDER_COST_METRICS.record("satellite", "provider_timeout")
        return build_response(status="unavailable", reason_code="provider_timeout", now=checked_at)
    except EarthEngineFeatureDisabled:
        return build_response(status="unavailable", reason_code="feature_disabled", now=checked_at)
    except EarthEngineCredentialUnavailable:
        return build_response(status="unavailable", reason_code="credential_unavailable", now=checked_at)
    except EarthEngineInitializationUnavailable:
        return build_response(status="unavailable", reason_code="provider_error", now=checked_at)
    except EarthEngineImageGenerationError:
        return build_response(status="unavailable", reason_code="image_generation_failed", now=checked_at)
    except EarthEngineProviderError:
        PROVIDER_COST_METRICS.record("satellite", "provider_failure")
        return build_response(status="unavailable", reason_code="provider_error", now=checked_at)
    except Exception:
        PROVIDER_COST_METRICS.record("satellite", "provider_failure")
        return build_response(status="unavailable", reason_code="provider_error", now=checked_at)

    if not provider_result.image_bytes or len(provider_result.image_bytes) > MAX_PROVIDER_IMAGE_BYTES:
        return build_response(
            status="unavailable",
            reason_code="image_generation_failed",
            now=checked_at,
        )

    image_reference = "data:image/jpeg;base64," + base64.b64encode(provider_result.image_bytes).decode("ascii")
    response = build_response(
        status="available",
        reason_code=None,
        image_reference=image_reference,
        now=checked_at,
    )
    response_too_large = len(response.model_dump_json().encode("utf-8")) > MAX_RESPONSE_BYTES
    if time.monotonic() >= deadline:
        return build_response(
            status="unavailable",
            reason_code="provider_timeout",
            now=checked_at,
        )
    if response_too_large:
        return build_response(
            status="unavailable",
            reason_code="image_generation_failed",
            now=checked_at,
        )
    PROVIDER_COST_METRICS.record("satellite", "provider_success")
    return response
