"""Safe public contract for bounded satellite reference imagery."""

from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import multiprocessing
import threading
import time
from typing import Any, Callable, Literal, Protocol, cast

from pydantic import BaseModel, Field


DATASET_ID = "COPERNICUS/S2_SR_HARMONIZED"
SOURCE_LABEL = "Sentinel-2 / Copernicus"
AOI_RADIUS_M = 500
WINDOW_DAYS = 90
CLOUD_FILTER_PERCENT = 35
MAX_IMAGE_REFERENCE_CHARS = 360_000
MAX_PROVIDER_IMAGE_BYTES = 250_000
MAX_RESPONSE_BYTES = 365_000
EXTERNAL_TIMEOUT_SECONDS = 8.0
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
    window_start: str
    window_end: str
    retrieval_time: str
    aoi_radius_m: int
    composite_method: str
    cloud_filter_percent: int
    image_reference: str | None = Field(default=None, max_length=MAX_IMAGE_REFERENCE_CHARS)
    attribution: str
    limitations: list[str]
    disclaimer: str


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
    scene_count: int
    image_bytes: bytes | None


class SatelliteAdapter(Protocol):
    def fetch(self, query: SatelliteQuery) -> SatelliteAdapterResult: ...


class EarthEngineCredentialUnavailable(RuntimeError):
    """Application Default Credentials or Earth Engine initialization failed."""


class EarthEngineProviderError(RuntimeError):
    """The bounded Earth Engine query failed."""


class EarthEngineProviderTimeout(EarthEngineProviderError):
    """The bounded Earth Engine operation exceeded its total time limit."""


class EarthEngineImageGenerationError(RuntimeError):
    """The bounded provider image could not be generated or downloaded."""


def feature_enabled(value: str) -> bool:
    return value.strip().lower() == "true"


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
    )


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


def _process_entry(send_connection, target: Callable[..., Any], args: tuple[Any, ...]) -> None:
    """Run one operation and return only an allowlisted result or safe failure category."""

    try:
        send_connection.send(("ok", target(*args)))
    except EarthEngineCredentialUnavailable:
        send_connection.send(("credential_unavailable", None))
    except EarthEngineProviderTimeout:
        send_connection.send(("provider_timeout", None))
    except EarthEngineImageGenerationError:
        send_connection.send(("image_generation_failed", None))
    except EarthEngineProviderError:
        send_connection.send(("provider_error", None))
    except BaseException:
        send_connection.send(("provider_error", None))
    finally:
        send_connection.close()


def _stop_process(process: multiprocessing.Process) -> None:
    """Ensure a provider child is no longer executing before returning."""

    if process.is_alive():
        process.terminate()
    process.join(timeout=0.25)
    if process.is_alive() and hasattr(process, "kill"):
        process.kill()
        process.join(timeout=0.25)
    if process.is_alive():
        raise EarthEngineProviderError("Earth Engine worker could not be stopped")
    process.close()


def _run_in_terminated_process(
    target: Callable[..., Any],
    args: tuple[Any, ...],
    *,
    timeout_seconds: float,
) -> Any:
    """Run a picklable callable within a hard, terminating process deadline."""

    if timeout_seconds <= 0:
        raise EarthEngineProviderTimeout("Earth Engine operation timed out")
    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_process_entry,
        args=(send_connection, target, args),
        daemon=True,
    )
    deadline = time.monotonic() + timeout_seconds
    try:
        process.start()
        send_connection.close()
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not receive_connection.poll(remaining):
            raise EarthEngineProviderTimeout("Earth Engine operation timed out")
        try:
            outcome, payload = receive_connection.recv()
        except EOFError as exc:
            raise EarthEngineProviderError("Earth Engine worker exited without a result") from exc
    finally:
        send_connection.close()
        receive_connection.close()
        if process.pid is not None:
            _stop_process(process)

    if outcome == "ok":
        return payload
    if outcome == "credential_unavailable":
        raise EarthEngineCredentialUnavailable("Application Default Credentials are unavailable")
    if outcome == "provider_timeout":
        raise EarthEngineProviderTimeout("Earth Engine operation timed out")
    if outcome == "image_generation_failed":
        raise EarthEngineImageGenerationError("Earth Engine thumbnail generation failed")
    raise EarthEngineProviderError("Earth Engine query failed")


MAX_CONCURRENT_PROVIDER_PROCESSES = 2
MAX_QUEUED_PROVIDER_REQUESTS = 2
_PROCESS_STOP_GRACE_SECONDS = 0.5
_PROVIDER_PROCESS_SLOTS = threading.BoundedSemaphore(value=MAX_CONCURRENT_PROVIDER_PROCESSES)
_PROVIDER_REQUEST_SLOTS = threading.BoundedSemaphore(
    value=MAX_CONCURRENT_PROVIDER_PROCESSES + MAX_QUEUED_PROVIDER_REQUESTS
)
_PROVIDER_EXECUTOR = ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_PROVIDER_PROCESSES,
    thread_name_prefix="earth-engine-reference",
)


def _earth_engine_fetch(project: str, query: SatelliteQuery) -> SatelliteAdapterResult:
    from services.adapters.earth_engine_adapter import EarthEngineSatelliteAdapter

    return EarthEngineSatelliteAdapter(project=project).fetch(query)


def _bounded_earth_engine_fetch(
    project: str,
    query: SatelliteQuery,
    deadline: float,
) -> SatelliteAdapterResult:
    """Bound queueing plus execution to one total deadline and two provider workers."""

    remaining = deadline - time.monotonic()
    if remaining <= _PROCESS_STOP_GRACE_SECONDS:
        raise EarthEngineProviderTimeout("Earth Engine operation timed out")
    if not _PROVIDER_PROCESS_SLOTS.acquire(timeout=remaining - _PROCESS_STOP_GRACE_SECONDS):
        raise EarthEngineProviderTimeout("Earth Engine operation timed out")
    try:
        remaining = deadline - time.monotonic()
        if remaining <= _PROCESS_STOP_GRACE_SECONDS:
            raise EarthEngineProviderTimeout("Earth Engine operation timed out")
        return cast(
            SatelliteAdapterResult,
            _run_in_terminated_process(
                _earth_engine_fetch,
                (project, query),
                timeout_seconds=remaining - _PROCESS_STOP_GRACE_SECONDS,
            ),
        )
    finally:
        _PROVIDER_PROCESS_SLOTS.release()


async def _await_bounded_earth_engine_fetch(
    project: str,
    query: SatelliteQuery,
    timeout_seconds: float,
) -> SatelliteAdapterResult:
    """Bound submissions before they enter the runtime's shared thread queue."""

    if not _PROVIDER_REQUEST_SLOTS.acquire(blocking=False):
        raise EarthEngineProviderError("Earth Engine request capacity is unavailable")
    deadline = time.monotonic() + timeout_seconds
    worker = asyncio.wrap_future(
        _PROVIDER_EXECUTOR.submit(
            _bounded_earth_engine_fetch,
            project,
            query,
            deadline,
        ),
        loop=asyncio.get_running_loop(),
    )
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        try:
            await worker
        except Exception:
            pass
        raise
    finally:
        _PROVIDER_REQUEST_SLOTS.release()


async def fetch_satellite_reference(
    *,
    latitude: float,
    longitude: float,
    project: str,
    adapter: SatelliteAdapter | None = None,
    now: datetime | None = None,
    timeout_seconds: float = EXTERNAL_TIMEOUT_SECONDS,
) -> SatelliteReferenceResponse:
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    query = _fixed_query(latitude, longitude, checked_at)

    try:
        if adapter is None:
            provider_result = await _await_bounded_earth_engine_fetch(
                project,
                query,
                timeout_seconds,
            )
        else:
            provider_result = adapter.fetch(query)
    except EarthEngineProviderTimeout:
        return build_response(status="unavailable", reason_code="provider_timeout", now=checked_at)
    except EarthEngineCredentialUnavailable:
        return build_response(status="unavailable", reason_code="credential_unavailable", now=checked_at)
    except EarthEngineImageGenerationError:
        return build_response(status="unavailable", reason_code="image_generation_failed", now=checked_at)
    except EarthEngineProviderError:
        return build_response(status="unavailable", reason_code="provider_error", now=checked_at)
    except Exception:
        return build_response(status="unavailable", reason_code="provider_error", now=checked_at)

    if provider_result.scene_count <= 0:
        return build_response(
            status="unavailable",
            reason_code="no_usable_imagery_in_window",
            now=checked_at,
        )
    if not provider_result.image_bytes or len(provider_result.image_bytes) > MAX_PROVIDER_IMAGE_BYTES:
        return build_response(
            status="unavailable",
            reason_code="image_generation_failed",
            now=checked_at,
        )

    image_reference = "data:image/jpeg;base64," + base64.b64encode(provider_result.image_bytes).decode("ascii")
    status: Literal["available", "limited"] = "limited" if provider_result.scene_count == 1 else "available"
    reason_code = "limited_observation_coverage" if status == "limited" else None
    response = build_response(
        status=status,
        reason_code=reason_code,
        image_reference=image_reference,
        now=checked_at,
    )
    if len(response.model_dump_json().encode("utf-8")) > MAX_RESPONSE_BYTES:
        return build_response(
            status="unavailable",
            reason_code="image_generation_failed",
            now=checked_at,
        )
    return response
