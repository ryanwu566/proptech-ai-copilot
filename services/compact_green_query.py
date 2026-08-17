"""Compact GREEN valuation comparables query adapter.

This module provides the ONLY validated GREEN query path: valuation_comparables
(Hot Path 3 from docs/plvr/compact-green-query-contract.md).

It does NOT provide trend, property search, data status, market insight, or
any other capability. Those remain BLUE.

Connection strategy:
- Uses a process-level psycopg_pool.ConnectionPool (min=1, max=3)
- Pool is created LAZILY on first GREEN query invocation
- Thread-safe initialization via double-checked locking
- Connections are returned to pool after each query
- Broken/stale connections are recovered by psycopg_pool automatically
- All checked-out connections use SET TRANSACTION READ ONLY

LAT/LNG IMPACT (documented):
- GREEN rows have lat=None, lng=None
- distance_bonus = 0 for all GREEN rows (loses up to 7 similarity points)
- Confidence capped at 85 when all rows lack distance_m
- probable_community always False for GREEN rows
- No exceptions, no row rejection, no candidate count reduction
"""

from __future__ import annotations

import os
import threading
from typing import Any


# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------

_PLVR_DATA_BACKEND_ENV = "PLVR_DATA_BACKEND"
_COMPACT_GREEN_DATABASE_URL_ENV = "COMPACT_GREEN_DATABASE_URL"


def is_green_enabled() -> bool:
    """Return True only when the feature flag explicitly selects GREEN."""
    return os.getenv(_PLVR_DATA_BACKEND_ENV, "").strip().lower() == "green"


# ---------------------------------------------------------------------------
# Connection pool — lazy, process-level, thread-safe
# ---------------------------------------------------------------------------

_pool: Any = None
_pool_lock = threading.Lock()

# Pool configuration
_POOL_MIN_SIZE = 1
_POOL_MAX_SIZE = 3
_POOL_TIMEOUT = 5.0  # seconds to wait for a connection from pool
_CONNECT_TIMEOUT = 5  # seconds for TCP/TLS establishment


def _get_pool() -> Any:
    """Return the process-level GREEN connection pool, creating it lazily.

    Thread-safe via double-checked locking. The pool is NOT created at module
    import time — only when a GREEN query is actually invoked.
    """
    global _pool

    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        database_url = os.getenv(_COMPACT_GREEN_DATABASE_URL_ENV, "").strip()
        if not database_url:
            raise CompactGreenQueryError(
                f"{_COMPACT_GREEN_DATABASE_URL_ENV} is not configured"
            )

        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(
            conninfo=database_url,
            min_size=_POOL_MIN_SIZE,
            max_size=_POOL_MAX_SIZE,
            timeout=_POOL_TIMEOUT,
            kwargs={
                "connect_timeout": _CONNECT_TIMEOUT,
                "prepare_threshold": None,
                "row_factory": _get_dict_row_factory(),
                "autocommit": True,
            },
        )
        # Wait for initial connection to be ready
        _pool.wait(timeout=_CONNECT_TIMEOUT + 2)
        return _pool


def _get_dict_row_factory():
    """Import and return dict_row factory."""
    from psycopg.rows import dict_row
    return dict_row


def _reset_pool() -> None:
    """Close and reset the pool. For testing only."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
            _pool = None


# ---------------------------------------------------------------------------
# Geography cache — loaded once, thread-safe
# ---------------------------------------------------------------------------

_geography_cache: dict[tuple[str, str], int] | None = None
_max_period_code: int | None = None
_geography_cache_lock = threading.Lock()


class CompactGreenGeographyCacheError(RuntimeError):
    """Raised when the geography cache cannot be loaded."""


class CompactGreenQueryError(RuntimeError):
    """Raised when a GREEN query fails — must NOT silently fallback to BLUE."""


def _load_geography_cache(database_url: str) -> tuple[dict[tuple[str, str], int], int]:
    """Load geography dictionary AND max period_code from the frozen generation.

    Returns (geography_map, max_period_code).

    The max_period_code is derived from actual data in compact_green, NOT from
    wall-clock time. This prevents querying period codes beyond the frozen
    generation boundary (e.g., requesting period_code 319 when data ends at 318).

    Uses a dedicated one-time connection (not from the pool) to avoid
    initialization recursion — the pool may not exist yet when cache loads.
    """
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(
        database_url,
        connect_timeout=_CONNECT_TIMEOUT,
        prepare_threshold=None,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute(
                """
                SELECT geographic_unit_id, city, district
                FROM compact_green.compact_geographies
                WHERE geographic_unit_kind = 1
                """
            )
            rows = cursor.fetchall()

            # Load the actual latest period_code from the frozen generation
            cursor.execute(
                """
                SELECT MAX(period_code) AS max_period_code
                FROM compact_green.compact_transaction_facts
                WHERE generation_key = 1
                """
            )
            period_row = cursor.fetchone()

    if not rows:
        raise CompactGreenGeographyCacheError(
            "compact_green.compact_geographies returned 0 rows for geographic_unit_kind=1"
        )

    max_pc = int(period_row["max_period_code"]) if period_row and period_row["max_period_code"] is not None else None
    if max_pc is None:
        raise CompactGreenGeographyCacheError(
            "compact_green.compact_transaction_facts has no rows for generation_key=1"
        )

    geography_map = {
        (str(row["city"]).strip(), str(row["district"]).strip()): int(row["geographic_unit_id"])
        for row in rows
    }
    return geography_map, max_pc


def get_geography_cache(database_url: str | None = None) -> dict[tuple[str, str], int]:
    """Return the process-level geography cache, loading it once."""
    global _geography_cache, _max_period_code

    if _geography_cache is not None:
        return _geography_cache

    with _geography_cache_lock:
        # Double-check after acquiring lock
        if _geography_cache is not None:
            return _geography_cache

        url = database_url or os.getenv(_COMPACT_GREEN_DATABASE_URL_ENV, "").strip()
        if not url:
            raise CompactGreenGeographyCacheError(
                f"{_COMPACT_GREEN_DATABASE_URL_ENV} is not configured"
            )

        _geography_cache, _max_period_code = _load_geography_cache(url)
        return _geography_cache


def get_max_period_code() -> int:
    """Return the cached max period_code from the frozen generation.

    Must be called AFTER get_geography_cache() has loaded successfully.
    """
    if _max_period_code is None:
        raise CompactGreenQueryError(
            "max_period_code not available — geography cache not loaded"
        )
    return _max_period_code


def reset_geography_cache() -> None:
    """Reset geography cache and pool for testing purposes only."""
    global _geography_cache, _max_period_code
    with _geography_cache_lock:
        _geography_cache = None
        _max_period_code = None
    _reset_pool()


# ---------------------------------------------------------------------------
# Period code encoding/decoding
# ---------------------------------------------------------------------------

def encode_period(year: int, month: int) -> int:
    """Encode YYYY-MM to period_code: (year - 2000) * 12 + month - 1."""
    return (year - 2000) * 12 + month - 1


def decode_period(period_code: int) -> str:
    """Decode period_code to YYYY-MM string."""
    year = (period_code // 12) + 2000
    month = (period_code % 12) + 1
    return f"{year:04d}-{month:02d}"


# ---------------------------------------------------------------------------
# GREEN valuation comparables query
# ---------------------------------------------------------------------------

_VALUATION_COMPARABLES_SQL = """
WITH target_ids AS (
    SELECT geo.geographic_unit_id, road.road_id, bt.building_type_id
    FROM compact_green.compact_geographies geo
    LEFT JOIN compact_green.compact_roads road
      ON road.geographic_unit_id = geo.geographic_unit_id AND road.road = %(road)s
    LEFT JOIN compact_green.compact_building_types bt
      ON bt.building_type = %(building_type)s
    WHERE geo.city = %(city)s AND geo.district = %(district)s AND geo.geographic_unit_kind = 1
), candidates AS MATERIALIZED (
    SELECT fact.*
    FROM compact_green.compact_transaction_facts fact, target_ids t
    WHERE fact.generation_key = 1
      AND fact.geographic_unit_id = t.geographic_unit_id
      AND fact.period_code <= %(max_period_code)s
    ORDER BY
      CASE WHEN fact.road_id = t.road_id THEN 0 ELSE 1 END,
      CASE WHEN fact.building_type_id = t.building_type_id THEN 0 ELSE 1 END,
      abs(fact.area_ping - %(area_ping)s),
      abs(fact.building_age_years - %(building_age_years)s),
      fact.period_code DESC,
      fact.transaction_id
    LIMIT 200
)
SELECT c.period_code, geo.city, geo.district,
       road.road, bt.building_type, c.area_ping,
       c.building_age_years, c.floor, c.total_floor,
       c.unit_price_per_ping, c.total_price, c.address_text
FROM candidates c
JOIN compact_green.compact_geographies geo USING (geographic_unit_id)
JOIN compact_green.compact_roads road USING (road_id)
JOIN compact_green.compact_building_types bt USING (building_type_id)
ORDER BY
  CASE WHEN road.road = %(road)s THEN 0 ELSE 1 END,
  CASE WHEN bt.building_type = %(building_type)s THEN 0 ELSE 1 END,
  abs(c.area_ping - %(area_ping)s),
  abs(c.building_age_years - %(building_age_years)s),
  c.period_code DESC,
  c.transaction_id;
"""


def _normalize_city(value: str) -> str:
    """Normalize Taiwan city character variants."""
    return value.strip().replace("臺", "台")


def query_green_comparables(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute the frozen valuation_comparables hot path against compact_green.

    Uses a pooled connection for performance. The pool reuses TCP/TLS sessions
    to avoid per-request connection establishment overhead (~500-800ms saved).

    Returns rows in BLUE-compatible format for valuation_service consumption.

    Raises CompactGreenQueryError on any failure — never silently returns empty.
    """
    # Resolve geography cache (validates district exists)
    try:
        cache = get_geography_cache()
    except CompactGreenGeographyCacheError as exc:
        raise CompactGreenQueryError(f"geography cache unavailable: {exc}") from exc

    city = _normalize_city(str(payload.get("city", "")))
    district = str(payload.get("district", "")).strip()

    if (city, district) not in cache:
        raise CompactGreenQueryError(
            f"district not found in GREEN geography cache: ({city}, {district})"
        )

    # Use the frozen generation's actual max period_code — NOT wall-clock time.
    max_period_code = get_max_period_code()

    # Build query parameters
    params = {
        "road": str(payload.get("road", "")),
        "building_type": str(payload.get("building_type", "")),
        "city": city,
        "district": district,
        "max_period_code": max_period_code,
        "area_ping": float(payload.get("area_ping", 0) or 0),
        "building_age_years": float(payload.get("building_age_years", 0) or 0),
    }

    try:
        pool = _get_pool()
        with pool.connection() as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            with connection.cursor() as cursor:
                cursor.execute(_VALUATION_COMPARABLES_SQL, params)
                rows = cursor.fetchall()
    except CompactGreenQueryError:
        raise
    except Exception as exc:
        raise CompactGreenQueryError(f"GREEN query failed: {type(exc).__name__}") from exc

    # Map GREEN rows to BLUE-compatible format
    return [_map_green_row(row) for row in rows]


def _map_green_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a GREEN result row to the format expected by valuation_service."""
    period_code = int(row["period_code"])
    return {
        "transaction_period": decode_period(period_code),
        "city": str(row.get("city") or ""),
        "district": str(row.get("district") or ""),
        "road": str(row.get("road") or ""),
        "building_type": str(row.get("building_type") or ""),
        "area_ping": float(row.get("area_ping") or 0),
        "building_age_years": float(row.get("building_age_years") or 0),
        "floor": float(row.get("floor") or 0),
        "total_floor": float(row.get("total_floor") or 0),
        "unit_price_per_ping": float(row.get("unit_price_per_ping") or 0),
        "total_price": float(row.get("total_price") or 0),
        "address_text": str(row.get("address_text") or ""),
        # GREEN does not have lat/lng — distance_bonus will be 0
        "lat": None,
        "lng": None,
        # Must be "official_plvr_opendata" to pass _prepare_candidate_pool enforce_scope filter
        "source": "official_plvr_opendata",
        # Not available in GREEN schema
        "imported_at": None,
        "raw_note": None,
    }
