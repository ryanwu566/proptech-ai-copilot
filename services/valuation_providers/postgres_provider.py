"""Lazy Supabase/Postgres valuation provider with safe failure behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any


UPDATE_FREQUENCY_NOTE = "正式實價登錄資料應由後台排程維護，不在 Render runtime 執行下載或 ETL。"
USER_MESSAGE = "使用者不需要下載資料；估價資料由系統後台資料庫維護。"


class PostgresValuationProvider:
    """Query a prepared Postgres valuation index without runtime ETL."""

    source = "postgres"
    is_full_taiwan = False
    _availability_cache: dict[str, tuple[float, bool]] = {}
    availability_cache_seconds = 60

    def __init__(self, database_url: str, connect_timeout: int = 3) -> None:
        self.database_url = database_url
        self.connect_timeout = connect_timeout
        self.is_demo_data = True
        self._last_status: dict[str, Any] | None = None
        self.last_query_metadata: dict[str, Any] = {}

    def available(self) -> bool:
        """Test connectivity only when provider selection is first requested."""

        cached = self._availability_cache.get(self.database_url)
        if cached and time.monotonic() - cached[0] < self.availability_cache_seconds:
            return cached[1]
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select 1 from real_price_transactions limit 1")
                    cursor.fetchone()
            result = True
        except Exception:
            result = False
        self._availability_cache[self.database_url] = (time.monotonic(), result)
        return result

    def load_transactions(self) -> tuple[dict[str, Any], ...]:
        """Return a small recent sample for compatibility, never the full table."""

        return tuple(self.query_comparables({}))

    def query_comparables(self, request: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
        """Return a district candidate pool so the service can enforce road scope."""

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    if request.get("city") and request.get("district"):
                        sql, params = _comparable_query(request, "district", max(limit, 200))
                        cursor.execute(sql, params)
                        rows = cursor.fetchall()
                        self.last_query_metadata = _query_metadata(request, "district_pool", len(rows))
                        return [_normalize_row(dict(row)) for row in rows]
                    for scope in ("road", "district", "city", "all"):
                        sql, params = _comparable_query(request, scope, limit)
                        cursor.execute(sql, params)
                        rows = cursor.fetchall()
                        if len(rows) >= 3 or scope == "all":
                            self.last_query_metadata = _query_metadata(request, scope, len(rows))
                            return [_normalize_row(dict(row)) for row in rows]
            return []
        except Exception as error:
            self.last_query_metadata = {
                **_query_metadata(request, "district_pool" if request.get("district") else "fallback", 0),
                "query_status": "failed",
                "safe_error": type(error).__name__,
            }
            return []

    def match_community(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Return a probable database community match when user input supports it."""

        address = str(request.get("address_text", "")).strip()
        if not address:
            return None
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        select community_id, community_name, city, district, road, address_pattern,
                               lat, lng, building_type, completed_year, total_floors, source, confidence
                        from community_buildings
                        where city = %s and district = %s and road = %s
                          and (%s ilike '%%' || community_name || '%%'
                               or %s ilike '%%' || address_pattern || '%%')
                        order by updated_at desc
                        limit 1
                        """,
                        [request.get("city", ""), request.get("district", ""), request.get("road", ""), address, address],
                    )
                    row = cursor.fetchone()
            return dict(row) if row else None
        except Exception:
            return None

    def data_status(self) -> dict[str, Any]:
        """Summarize indexed coverage and official/sample composition."""

        if self._last_status:
            return self._last_status
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        select count(*) as records_count,
                               count(distinct city) as cities_count,
                               count(distinct district) as districts_count,
                               count(distinct (city, district, road)) as roads_count,
                               count(*) filter (where source = 'official_plvr_opendata') as official_records_count,
                               count(*) filter (where source in ('sample', 'real_price_sample', 'community_building_sample')) as sample_records_count
                        from real_price_transactions
                        """
                    )
                    summary = dict(cursor.fetchone())
                    cursor.execute("select distinct city from real_price_transactions order by city")
                    cities = [row["city"] for row in cursor.fetchall()]
                    cursor.execute("select distinct district from real_price_transactions order by district")
                    districts = [row["district"] for row in cursor.fetchall()]
                    cursor.execute(
                        """
                        select imported_at from valuation_import_runs
                        where status = 'completed'
                        order by imported_at desc limit 1
                        """
                    )
                    last_run = cursor.fetchone()
            official_count = int(summary.get("official_records_count") or 0)
            sample_count = int(summary.get("sample_records_count") or 0)
            self.is_demo_data = official_count == 0
            composition = "mixed" if official_count and sample_count else "official" if official_count else "sample"
            last_updated = last_run.get("imported_at") if last_run else None
            if isinstance(last_updated, datetime):
                last_updated = last_updated.astimezone(UTC).isoformat()
            self._last_status = {
                "active_source": self.source,
                "is_demo_data": self.is_demo_data,
                "is_full_taiwan": False,
                "data_composition": composition,
                "official_records_count": official_count,
                "sample_records_count": sample_count,
                "coverage": {
                    "cities": cities,
                    "districts": districts,
                    "roads_count": int(summary.get("roads_count") or 0),
                    "records_count": int(summary.get("records_count") or 0),
                },
                "last_updated": last_updated,
                "update_frequency_note": UPDATE_FREQUENCY_NOTE,
                "source_note": _source_note(composition),
                "user_message": USER_MESSAGE,
            }
            return self._last_status
        except Exception:
            return {
                "active_source": self.source,
                "is_demo_data": True,
                "is_full_taiwan": False,
                "data_composition": "sample",
                "official_records_count": 0,
                "sample_records_count": 0,
                "coverage": {"cities": [], "districts": [], "roads_count": 0, "records_count": 0},
                "last_updated": None,
                "update_frequency_note": UPDATE_FREQUENCY_NOTE,
                "source_note": "Supabase/Postgres 暫時無法使用，系統會安全切換至下一個估價資料來源。",
                "user_message": USER_MESSAGE,
            }

    def estimate(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """Compatibility entry point returning prepared comparable candidates."""

        return self.query_comparables(request)

    def get_data_status(self) -> dict[str, Any]:
        """Compatibility alias for provider consumers."""

        return self.data_status()

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.database_url, connect_timeout=self.connect_timeout, row_factory=dict_row)


def _source_note(composition: str) -> str:
    if composition == "official":
        return "目前使用官方 PLVR OpenData 匯入資料，尚非全台完整資料。"
    if composition == "mixed":
        return "目前使用官方 PLVR OpenData 與展示樣本混合資料，尚非全台完整資料。"
    return "目前使用 Supabase/Postgres 展示樣本，尚非全台完整資料。"


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ("area_ping", "unit_price_per_ping", "total_price", "building_age_years", "floor"):
        result[key] = float(result.get(key) or 0)
    result["lat"] = float(result["lat"]) if result.get("lat") is not None else None
    result["lng"] = float(result["lng"]) if result.get("lng") is not None else None
    return result


def _comparable_query(request: dict[str, Any], scope: str, limit: int) -> tuple[str, list[Any]]:
    clauses: list[str] = ["(source <> 'official_plvr_opendata' or transaction_period <= %s)"]
    scope_params: list[Any] = [datetime.now(UTC).strftime("%Y-%m")]
    for field in ("city", "district", "road"):
        if field == "district" and scope not in {"road", "district"}:
            continue
        if field == "road" and scope != "road":
            continue
        if field == "city" and scope == "all":
            continue
        if request.get(field):
            if field == "city":
                clauses.append("replace(trim(city), '臺', '台') = %s")
                scope_params.append(_normalize_city(str(request[field])))
            elif field == "district":
                clauses.append("trim(district) = %s")
                scope_params.append(str(request[field]).strip())
            else:
                clauses.append(f"{field} = %s")
                scope_params.append(request[field])
    where = f"where {' and '.join(clauses)}" if clauses else ""
    sql = f"""
        select id, transaction_period, city, district, road, address_text,
               building_type, area_ping, building_age_years, floor, total_floor,
               unit_price_per_ping, total_price, lat, lng, source, imported_at, raw_note
        from real_price_transactions
        {where}
        order by
            case when road = %s then 0 else 1 end,
            case when district = %s then 0 else 1 end,
            case when building_type = %s then 0 else 1 end,
            abs(area_ping - %s),
            abs(building_age_years - %s),
            case when %s::double precision is not null and %s::double precision is not null
                 then power(coalesce(lat, %s) - %s, 2) + power(coalesce(lng, %s) - %s, 2)
                 else 0 end,
            transaction_period desc
        limit {max(1, min(int(limit), 200))}
    """
    ranking_params = [
        request.get("road", ""),
        request.get("district", ""),
        request.get("building_type", ""),
        float(request.get("area_ping", 0) or 0),
        float(request.get("building_age_years", 0) or 0),
        request.get("lat"),
        request.get("lng"),
        request.get("lat"),
        request.get("lat"),
        request.get("lng"),
        request.get("lng"),
    ]
    return sql, [*scope_params, *ranking_params]


def _normalize_city(value: str) -> str:
    return value.strip().replace("臺", "台")


def _query_metadata(request: dict[str, Any], scope: str, rows: int) -> dict[str, Any]:
    """Return safe query diagnostics without connection details."""

    return {
        "provider_active": "postgres",
        "candidate_pool_size": rows,
        "query_scope": scope,
        "requested_city": request.get("city", ""),
        "requested_district": request.get("district", ""),
        "requested_road": request.get("road", ""),
        "db_rows_returned": rows,
        "query_status": "ok",
    }
