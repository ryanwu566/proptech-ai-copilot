"""Lazy Supabase/Postgres valuation provider with safe failure behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any


DATA_QUALITY_NOTE = (
    "資料庫可能含歷史或未來期別，但估價與趨勢分析會自動排除超出分析窗口、"
    "晚於目前月份或異常的交易期間。"
)
RETENTION_POLICY_YEARS = 3
RETENTION_NOTE = (
    "本系統採 rolling 3 年官方實價登錄資料策略；每季更新後可先 dry-run 盤點，"
    "再由維護者確認清理超出保留期間的官方資料。"
)
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

    def query_trend_rows(self, request: dict[str, Any], limit: int = 10_000) -> list[dict[str, Any]]:
        """Return an official district pool; the trend service applies period quality rules."""

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        r"""
                        select transaction_period, city, district, road, building_type,
                               area_ping, building_age_years, unit_price_per_ping, total_price,
                               source
                        from real_price_transactions
                        where source = 'official_plvr_opendata'
                          and replace(trim(city), '臺', '台') = %s
                          and trim(district) = %s
                          and unit_price_per_ping > 0
                          and area_ping > 0
                        order by transaction_period desc
                        limit %s
                        """,
                        [
                            _normalize_city(str(request.get("city", ""))),
                            str(request.get("district", "")).strip(),
                            max(1, min(int(limit), 20_000)),
                        ],
                    )
                    return [_normalize_row(dict(row)) for row in cursor.fetchall()]
        except Exception:
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
            current_period = datetime.now(UTC).strftime("%Y-%m")
            trend_window_start = _shift_month(current_period, -35)
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        r"""
                        select count(*) as records_count,
                               count(distinct city) as cities_count,
                               count(distinct district) as districts_count,
                               count(distinct (city, district, road)) as roads_count,
                               count(*) filter (where source = 'official_plvr_opendata') as official_records_count,
                               count(*) filter (where source in ('sample', 'real_price_sample', 'community_building_sample')) as sample_records_count,
                               min(transaction_period) filter (where source = 'official_plvr_opendata') as raw_official_period_min,
                               max(transaction_period) filter (where source = 'official_plvr_opendata') as raw_official_period_max,
                               min(transaction_period) filter (
                                   where source = 'official_plvr_opendata'
                                     and transaction_period ~ '^\d{4}-(0[1-9]|1[0-2])$'
                                     and transaction_period between %s and %s
                               ) as effective_trend_period_min,
                               max(transaction_period) filter (
                                   where source = 'official_plvr_opendata'
                                     and transaction_period ~ '^\d{4}-(0[1-9]|1[0-2])$'
                                     and transaction_period between %s and %s
                               ) as effective_trend_period_max,
                               count(*) filter (
                                   where source = 'official_plvr_opendata'
                                     and transaction_period ~ '^\d{4}-(0[1-9]|1[0-2])$'
                                     and transaction_period > %s
                               ) as excluded_future_period_count,
                               count(*) filter (
                                   where source = 'official_plvr_opendata'
                                     and transaction_period ~ '^\d{4}-(0[1-9]|1[0-2])$'
                                     and transaction_period < %s
                               ) as excluded_too_old_period_count
                        from real_price_transactions
                        """,
                        [trend_window_start, current_period, trend_window_start, current_period, current_period, trend_window_start],
                    )
                    summary = dict(cursor.fetchone())
                    cursor.execute("select distinct city from real_price_transactions order by city")
                    cities = [row["city"] for row in cursor.fetchall()]
                    cursor.execute("select distinct district from real_price_transactions order by district")
                    districts = [row["district"] for row in cursor.fetchall()]
                    cursor.execute(
                        """
                        select imported_at, status, city_scope, district_scope, road_scope,
                               inserted_rows, skipped_duplicate_rows
                        from valuation_import_runs
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
                "official_period_min": summary.get("raw_official_period_min"),
                "official_period_max": summary.get("raw_official_period_max"),
                "raw_official_period_min": summary.get("raw_official_period_min"),
                "raw_official_period_max": summary.get("raw_official_period_max"),
                "effective_trend_period_min": summary.get("effective_trend_period_min"),
                "effective_trend_period_max": summary.get("effective_trend_period_max"),
                "excluded_future_period_count": int(summary.get("excluded_future_period_count") or 0),
                "excluded_too_old_period_count": int(summary.get("excluded_too_old_period_count") or 0),
                "data_quality_note": DATA_QUALITY_NOTE,
                "retention_policy_years": RETENTION_POLICY_YEARS,
                "retention_cutoff_period": trend_window_start,
                "records_outside_retention_count": int(summary.get("excluded_too_old_period_count") or 0),
                "oldest_effective_period": summary.get("effective_trend_period_min"),
                "newest_effective_period": summary.get("effective_trend_period_max"),
                "retention_note": RETENTION_NOTE,
                "official_coverage_note": _official_coverage_note(cities, districts),
                "latest_import_status": last_run.get("status") if last_run else None,
                "latest_import_scope": _latest_import_scope(last_run),
                "latest_import_inserted_rows": int(last_run.get("inserted_rows") or 0) if last_run else 0,
                "latest_import_skipped_duplicates": int(last_run.get("skipped_duplicate_rows") or 0) if last_run else 0,
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
                "official_period_min": None,
                "official_period_max": None,
                "raw_official_period_min": None,
                "raw_official_period_max": None,
                "effective_trend_period_min": None,
                "effective_trend_period_max": None,
                "excluded_future_period_count": 0,
                "excluded_too_old_period_count": 0,
                "data_quality_note": DATA_QUALITY_NOTE,
                "retention_policy_years": RETENTION_POLICY_YEARS,
                "retention_cutoff_period": _shift_month(datetime.now(UTC).strftime("%Y-%m"), -35),
                "records_outside_retention_count": 0,
                "oldest_effective_period": None,
                "newest_effective_period": None,
                "retention_note": RETENTION_NOTE,
                "official_coverage_note": "目前無法讀取官方資料涵蓋範圍。",
                "latest_import_status": None,
                "latest_import_scope": "",
                "latest_import_inserted_rows": 0,
                "latest_import_skipped_duplicates": 0,
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

        return psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout,
            prepare_threshold=None,
            row_factory=dict_row,
        )


def _source_note(composition: str) -> str:
    if composition == "official":
        return "目前使用官方 PLVR OpenData 匯入資料，尚非全台完整資料。"
    if composition == "mixed":
        return "目前使用官方 PLVR OpenData 與展示樣本混合資料，尚非全台完整資料。"
    return "目前使用 Supabase/Postgres 展示樣本，尚非全台完整資料。"


def _latest_import_scope(last_run: dict[str, Any] | None) -> str:
    if not last_run:
        return ""
    return " / ".join(
        value for value in (last_run.get("city_scope"), last_run.get("district_scope"), last_run.get("road_scope")) if value
    )


def _official_coverage_note(cities: list[str], districts: list[str]) -> str:
    city_text = "、".join(cities) if cities else "尚無城市"
    district_text = "、".join(districts) if districts else "尚無行政區"
    return f"目前官方資料涵蓋 {city_text} 的部分區域（{district_text}），尚非完整雙北一年或全台資料。"


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


def _shift_month(period: str, offset: int) -> str:
    """Return a YYYY-MM period shifted by a number of months."""

    year, month = map(int, period.split("-"))
    total = year * 12 + month - 1 + offset
    return f"{total // 12:04d}-{total % 12 + 1:02d}"
