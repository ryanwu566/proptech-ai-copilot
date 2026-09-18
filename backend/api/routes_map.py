"""Map Insight Lite API routes backed only by bundled mock data."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.map_service import get_google_health, get_map_insight, get_nearby_places, list_poi_categories, list_regions, search_location
from services.rate_limit import DEFAULT_LIMIT, DEFAULT_WINDOW_SECONDS, FixedWindowRateLimiter


router = APIRouter(prefix="/map", tags=["map-insight"])
logger = logging.getLogger("proptech.observability")

PUBLIC_MAP_RATE_LIMIT_REQUESTS_ENV = "PUBLIC_MAP_RATE_LIMIT_REQUESTS"
PUBLIC_MAP_RATE_LIMIT_WINDOW_SECONDS_ENV = "PUBLIC_MAP_RATE_LIMIT_WINDOW_SECONDS"


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _build_map_rate_limiter() -> FixedWindowRateLimiter:
    return FixedWindowRateLimiter(
        limit=_positive_int_env(PUBLIC_MAP_RATE_LIMIT_REQUESTS_ENV, DEFAULT_LIMIT),
        window_seconds=_positive_int_env(PUBLIC_MAP_RATE_LIMIT_WINDOW_SECONDS_ENV, DEFAULT_WINDOW_SECONDS),
    )


# One shared, process-local budget for the three public provider-backed routes.
_MAP_RATE_LIMITER = _build_map_rate_limiter()


def _enforce_map_rate_limit(request: Request) -> None:
    """Limit the direct transport peer before provider work.

    Render starts Uvicorn with --no-proxy-headers. The ASGI client host is
    therefore a coarse peer key, not a proven end-user identity. Ignore all
    forwarded IP headers; no proxy trust range is configured here.
    """

    try:
        host = request.client.host if request.client else "unknown"
        decision = _MAP_RATE_LIMITER.check(f"map:{host}")
        rejected = not decision.allowed
        retry_after = str(decision.retry_after_seconds) if rejected else ""
    except Exception:
        logger.warning(
            "rate_limiter_failed_open boundary=map correlation_id=%s",
            getattr(request.state, "correlation_id", "unknown"),
        )
        return
    if rejected:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please retry later.",
            headers={"Retry-After": retry_after},
        )


class MapQuery(BaseModel):
    """Text query accepted by mock map search and insight endpoints."""

    query: str


class NearbyQuery(BaseModel):
    """Nearby POI query centered on a WGS84 coordinate."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_m: int = Field(default=800, ge=100, le=5000)
    categories: list[str] = Field(default_factory=lambda: ["transport", "school", "park", "medical", "shopping", "food"])
    language_code: str = "zh-TW"


@router.get("/regions")
def get_regions() -> list[dict[str, Any]]:
    """Return available mock map regions."""

    return list_regions()


@router.get("/poi-categories")
def get_poi_categories() -> list[dict[str, str]]:
    """Return supported mock POI categories."""

    return list_poi_categories()


@router.get("/google-health")
def get_map_google_health() -> dict[str, Any]:
    """Return a safe Google integration status without exposing credentials."""

    return get_google_health()


@router.post("/search")
def post_map_search(request: MapQuery, http_request: Request) -> dict[str, Any]:
    """Resolve a mock address, district, or road query."""

    _enforce_map_rate_limit(http_request)
    return search_location(request.query)


@router.post("/insight")
def post_map_insight(request: MapQuery, http_request: Request) -> dict[str, Any]:
    """Return map center, POI layers, and livability summary."""

    _enforce_map_rate_limit(http_request)
    result = get_map_insight(request.query)
    if result is None:
        raise HTTPException(status_code=404, detail="找不到符合的 Map Insight 展示資料。")
    return result


@router.post("/nearby")
def post_map_nearby(request: NearbyQuery, http_request: Request) -> dict[str, Any]:
    """Return normalized nearby amenities with automatic mock fallback."""

    _enforce_map_rate_limit(http_request)
    return get_nearby_places(request.lat, request.lng, request.radius_m, request.categories, request.language_code)
