"""Safe public contract for bounded satellite reference imagery."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
from typing import Literal, Protocol

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
    image_bytes: bytes


class SatelliteAdapter(Protocol):
    def fetch(self, query: SatelliteQuery) -> SatelliteAdapterResult: ...


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


def _get_earth_engine_worker_manager():
    """Import lazily to avoid starting or importing worker machinery at module load."""

    from services.earth_engine_worker_pool import get_earth_engine_worker_manager

    return get_earth_engine_worker_manager()


async def fetch_satellite_reference(
    *,
    latitude: float,
    longitude: float,
    adapter: SatelliteAdapter | None = None,
    now: datetime | None = None,
    timeout_seconds: float = EXTERNAL_TIMEOUT_SECONDS,
) -> SatelliteReferenceResponse:
    deadline = time.monotonic() + timeout_seconds
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    query = _fixed_query(latitude, longitude, checked_at)

    try:
        if adapter is None:
            image_bytes = await _get_earth_engine_worker_manager().fetch(
                latitude=latitude,
                longitude=longitude,
                window_start=query.window_start,
                window_end=query.window_end,
                deadline=deadline,
            )
            provider_result = SatelliteAdapterResult(image_bytes=image_bytes)
        else:
            provider_result = adapter.fetch(query)
    except EarthEngineProviderTimeout:
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
        return build_response(status="unavailable", reason_code="provider_error", now=checked_at)
    except Exception:
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
    return response
