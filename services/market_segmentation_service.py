"""Read-only PLVR market segmentation and evidence-based comparables.

V1 deliberately reads the existing ``real_price_transactions`` table. It does
not create derived data, require coordinates, or produce a synthetic similarity
score. Unknown age and floor values remain unknown and are reported as coverage.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
import math
import os
from typing import Any, Protocol

from services.plvr_data_integrity import (
    canonical_region_storage_keys,
    current_transaction_period,
    is_publishable_transaction_period,
)
from services.taiwan_admin_registry import normalize_market_region


OFFICIAL_SOURCE = "official_plvr_opendata"
SOURCE_LABEL = "Official PLVR OpenData"
FLOOR_POSITION_RULE = (
    "Known only when floor > 0, total_floor > 0, and floor <= total_floor; "
    "low <= 0.33, middle > 0.33 and < 0.67, high >= 0.67."
)
AGE_CAVEAT = (
    "Building age is an approximate imported field calculated using the import-year semantics. "
    "Values <= 0 are unknown, never new-building evidence."
)
HIGH_VALUE_CAVEAT = (
    "High-value residential transactions is a product-defined proxy using the displayed total-price "
    "threshold and residential building-type labels; it is not an official government classification."
)
GENERAL_CAVEAT = (
    "Historical transaction evidence is for market decision support only; it is not an appraisal, "
    "a lending decision, a purchase recommendation, or a transaction guarantee."
)
LOW_SAMPLE_THRESHOLD = 10
COMPARABLE_SUFFICIENT_COUNT = 5


BUILDING_TYPE_ALIASES = {
    "住宅大樓(11層含以上有電梯)": "住宅大樓",
    "住宅大樓(11層含以上)": "住宅大樓",
    "住宅大樓": "住宅大樓",
    "華廈(10層含以下有電梯)": "華廈",
    "華廈": "華廈",
    "公寓(5樓含以下無電梯)": "公寓",
    "公寓": "公寓",
    "透天": "透天厝",
    "透天厝": "透天厝",
    "套房(1房1廳1衛)": "套房",
    "套房": "套房",
    "店面(店鋪)": "店面",
    "店面": "店面",
    "其他": "其他/未分類",
    "未分類": "其他/未分類",
    "其他/未分類": "其他/未分類",
}
RESIDENTIAL_PROXY_BUILDING_TYPES = frozenset({"住宅大樓", "華廈", "公寓", "透天厝", "套房"})


def normalize_segment_building_type(value: Any) -> str:
    """Normalize only documented PLVR labels; preserve unfamiliar source labels."""

    raw = str(value or "").strip()
    return BUILDING_TYPE_ALIASES.get(raw, raw or "其他/未分類")


def classify_floor_position(floor: Any, total_floor: Any) -> str | None:
    """Classify a valid known floor using the public deterministic V1 rule."""

    try:
        floor_value = int(floor)
        total_value = int(total_floor)
    except (TypeError, ValueError, OverflowError):
        return None
    if floor_value <= 0 or total_value <= 0 or floor_value > total_value:
        return None
    ratio = floor_value / total_value
    if ratio <= 0.33:
        return "low"
    if ratio < 0.67:
        return "middle"
    return "high"


def percentile(values: list[float], fraction: float) -> float | None:
    """Continuous percentile equivalent used by tests for SQL result semantics."""

    clean = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    position = (len(clean) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    return clean[lower] + (clean[upper] - clean[lower]) * (position - lower)


class MarketSegmentationRepository(Protocol):
    def segment(self, filters: dict[str, Any]) -> dict[str, Any]: ...

    def comparables(self, filters: dict[str, Any], limit: int) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class PostgresMarketSegmentationRepository:
    database_url: str
    connect_timeout: int = 5
    as_of: date | datetime | None = None

    def segment(self, filters: dict[str, Any]) -> dict[str, Any]:
        params = _query_params(filters, as_of=self.as_of)
        with _read_only_cursor(self) as cursor:
            cursor.execute(SEGMENT_SQL, params)
            return dict(cursor.fetchone() or {})

    def comparables(self, filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        params = {**_query_params(filters, as_of=self.as_of), "limit": max(1, min(int(limit), 10))}
        with _read_only_cursor(self) as cursor:
            cursor.execute(COMPARABLES_SQL, params)
            return [dict(row) for row in cursor.fetchall()]

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout,
            prepare_threshold=None,
            row_factory=dict_row,
        )


@contextmanager
def _read_only_cursor(repository: PostgresMarketSegmentationRepository):
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("set transaction read only")
            cursor.execute("set local statement_timeout = '20s'")
            yield cursor


def get_market_segment(
    filters: dict[str, Any],
    repository: MarketSegmentationRepository | None = None,
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Return one truthful segment result or a safe unavailable state."""

    normalized = _normalized_filters(filters, as_of=as_of)
    repo = repository or _repository_from_env(as_of=as_of)
    if repo is None:
        return _unavailable_segment(normalized, "market_segmentation_runtime_not_configured")
    try:
        raw = repo.segment(normalized)
    except Exception:
        return _unavailable_segment(normalized, "market_segmentation_query_failed")
    return _segment_result(normalized, raw)


def get_market_segment_comparables(
    filters: dict[str, Any],
    limit: int = 8,
    repository: MarketSegmentationRepository | None = None,
    *,
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Return deduplicated comparable facts with transparent deltas and no score."""

    normalized = _normalized_filters(filters, as_of=as_of)
    clean_limit = max(1, min(int(limit), 10))
    repo = repository or _repository_from_env(as_of=as_of)
    if repo is None:
        return _unavailable_comparables(normalized, "market_segmentation_runtime_not_configured")
    try:
        rows = repo.comparables(normalized, clean_limit)
    except Exception:
        return _unavailable_comparables(normalized, "market_comparables_query_failed")
    comparables = [_public_comparable(row, normalized) for row in rows]
    state = "no_data" if not comparables else "low_sample" if len(comparables) < COMPARABLE_SUFFICIENT_COUNT else "available"
    if comparables and any(row["age_difference_years"] is None or row["floor_position"] is None for row in comparables):
        state = "partial" if len(comparables) >= COMPARABLE_SUFFICIENT_COUNT else "low_sample"
    return {
        "state": state,
        "data_status": state,
        "county": normalized["county"],
        "district": normalized["district"],
        "filters_applied": _public_filters(normalized),
        "comparable_count": len(comparables),
        "comparables": comparables,
        "ordering_method": (
            "Exact canonical county/district and normalized building type, requested area/age/floor filters, "
            "then absolute area delta, known age delta, floor-position relationship, recent period, and stable row id."
        ),
        "dedupe_method": "dedupe_key when nonblank; otherwise the local transaction row id",
        "opaque_similarity_score": False,
        "coordinates_required": False,
        "source": SOURCE_LABEL,
        "caveats": _caveats(normalized),
    }


def _segment_result(filters: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    matching = _int(raw.get("matching_transaction_count"))
    base_count = _int(raw.get("base_transaction_count"))
    eligible_count = _int(raw.get("eligible_transaction_count"))
    unknown_age = _int(raw.get("unknown_age_count"))
    unknown_floor = _int(raw.get("unknown_floor_count"))
    state = "no_data" if matching == 0 else "low_sample" if matching < LOW_SAMPLE_THRESHOLD else "available"
    if matching >= LOW_SAMPLE_THRESHOLD and (
        (_age_filter_applied(filters) and unknown_age > 0)
        or (filters.get("floor_position") and unknown_floor > 0)
    ):
        state = "partial"
    distribution = raw.get("building_type_distribution")
    if not isinstance(distribution, list):
        distribution = []
    return {
        "state": state,
        "data_status": state,
        "county": filters["county"],
        "district": filters["district"],
        "segment_identity": _segment_identity(filters),
        "matching_transaction_count": matching,
        "eligible_transaction_count": eligible_count,
        "base_transaction_count": base_count,
        "excluded_transaction_count": max(0, eligible_count - matching),
        "known_age_count": _int(raw.get("known_age_count")),
        "unknown_age_count": unknown_age,
        "known_floor_count": _int(raw.get("known_floor_count")),
        "unknown_floor_count": unknown_floor,
        "average_unit_price_per_ping": _number(raw.get("average_unit_price_per_ping")),
        "median_unit_price_per_ping": _number(raw.get("median_unit_price_per_ping")),
        "p25_unit_price_per_ping": _number(raw.get("p25_unit_price_per_ping")),
        "p75_unit_price_per_ping": _number(raw.get("p75_unit_price_per_ping")),
        "average_total_price_wan": _number(raw.get("average_total_price_wan")),
        "period_min": _text(raw.get("period_min")),
        "period_max": _text(raw.get("period_max")),
        "filters_applied": _public_filters(filters),
        "building_type_distribution": _safe_distribution(distribution),
        "floor_position_rule": FLOOR_POSITION_RULE,
        "source": SOURCE_LABEL,
        "source_updated_at": _date_text(raw.get("source_updated_at")),
        "sample_state": state,
        "caveats": _caveats(filters),
    }


def _unavailable_segment(filters: dict[str, Any], reason_code: str) -> dict[str, Any]:
    return {
        "state": "unavailable",
        "data_status": "unavailable",
        "reason_code": reason_code,
        "county": filters.get("county", ""),
        "district": filters.get("district", ""),
        "segment_identity": _segment_identity(filters),
        "matching_transaction_count": None,
        "eligible_transaction_count": None,
        "base_transaction_count": None,
        "excluded_transaction_count": None,
        "known_age_count": None,
        "unknown_age_count": None,
        "known_floor_count": None,
        "unknown_floor_count": None,
        "average_unit_price_per_ping": None,
        "median_unit_price_per_ping": None,
        "p25_unit_price_per_ping": None,
        "p75_unit_price_per_ping": None,
        "average_total_price_wan": None,
        "period_min": None,
        "period_max": None,
        "filters_applied": _public_filters(filters),
        "building_type_distribution": [],
        "floor_position_rule": FLOOR_POSITION_RULE,
        "source": SOURCE_LABEL,
        "source_updated_at": None,
        "sample_state": "unavailable",
        "caveats": _caveats(filters),
    }


def _unavailable_comparables(filters: dict[str, Any], reason_code: str) -> dict[str, Any]:
    return {
        "state": "unavailable",
        "data_status": "unavailable",
        "reason_code": reason_code,
        "county": filters.get("county", ""),
        "district": filters.get("district", ""),
        "filters_applied": _public_filters(filters),
        "comparable_count": None,
        "comparables": [],
        "ordering_method": "Transparent evidence ordering only",
        "dedupe_method": "dedupe_key when nonblank; otherwise the local transaction row id",
        "opaque_similarity_score": False,
        "coordinates_required": False,
        "source": SOURCE_LABEL,
        "caveats": _caveats(filters),
    }


def _normalized_filters(filters: dict[str, Any], *, as_of: date | datetime | None = None) -> dict[str, Any]:
    normalized_region = normalize_market_region(str(filters.get("county") or ""), str(filters.get("district") or ""))
    if not normalized_region.valid or not normalized_region.district:
        raise ValueError("invalid county/district")
    period_from, period_to = _period_window(filters, as_of=as_of)
    area_min = float(filters.get("area_min_ping", 30))
    area_max = float(filters.get("area_max_ping", 40))
    if not (0 < area_min < area_max <= 500):
        raise ValueError("invalid area range")
    age_min = filters.get("age_min_years")
    age_max = filters.get("age_max_years")
    age_min = float(age_min) if age_min is not None else None
    age_max = float(age_max) if age_max is not None else None
    if age_min is not None and age_min < 0:
        raise ValueError("invalid age minimum")
    if age_max is not None and age_max <= 0:
        raise ValueError("invalid age maximum")
    if age_min is not None and age_max is not None and age_min > age_max:
        raise ValueError("invalid age range")
    floor_position = str(filters.get("floor_position") or "").strip()
    if floor_position not in {"", "low", "middle", "high"}:
        raise ValueError("invalid floor position")
    threshold = float(filters.get("high_value_threshold_wan", 3000))
    if not 1 <= threshold <= 100_000:
        raise ValueError("invalid high-value threshold")
    target_area = filters.get("target_area_ping")
    target_age = filters.get("target_age_years")
    raw_building_type = str(filters.get("building_type") or "").strip()
    return {
        "county": normalized_region.county,
        "district": normalized_region.district,
        "period_from": period_from,
        "period_to": period_to,
        "period_months": int(filters.get("period_months") or 36),
        "building_type": normalize_segment_building_type(raw_building_type) if raw_building_type else "",
        "area_min_ping": area_min,
        "area_max_ping": area_max,
        "age_min_years": age_min,
        "age_max_years": age_max,
        "known_age_only": bool(filters.get("known_age_only")) or age_min is not None or age_max is not None,
        "floor_position": floor_position,
        "high_value_only": bool(filters.get("high_value_only")),
        "high_value_threshold_wan": threshold,
        "target_area_ping": float(target_area) if target_area is not None else (area_min + area_max) / 2,
        "target_age_years": float(target_age) if target_age is not None and float(target_age) > 0 else (
            (age_min + age_max) / 2 if age_min is not None and age_max is not None else None
        ),
    }


def _period_window(filters: dict[str, Any], *, as_of: date | datetime | None = None) -> tuple[str, str]:
    ceiling = current_transaction_period(as_of)
    explicit_from = str(filters.get("period_from") or "").strip()
    explicit_to = str(filters.get("period_to") or "").strip()
    if explicit_from or explicit_to:
        if not explicit_from or not explicit_to:
            raise ValueError("period_from and period_to are required together")
        if not is_publishable_transaction_period(explicit_from, as_of=as_of) or not is_publishable_transaction_period(explicit_to, as_of=as_of):
            raise ValueError("invalid or future period")
        if explicit_from > explicit_to:
            raise ValueError("invalid period range")
        return explicit_from, explicit_to
    months = int(filters.get("period_months") or 36)
    if not 1 <= months <= 120:
        raise ValueError("invalid period window")
    return _shift_month(ceiling, -(months - 1)), ceiling


def _query_params(filters: dict[str, Any], *, as_of: date | datetime | None = None) -> dict[str, Any]:
    normalized = _normalized_filters(filters, as_of=as_of)
    return {
        "canonical_keys": list(canonical_region_storage_keys()),
        "period_from": normalized["period_from"],
        "period_to": normalized["period_to"],
        "county": normalized["county"].replace("臺", "台"),
        "district": normalized["district"].strip().replace("臺", "台"),
        "building_type": normalized["building_type"],
        "area_min_ping": normalized["area_min_ping"],
        "area_max_ping": normalized["area_max_ping"],
        "age_min_years": normalized["age_min_years"],
        "age_max_years": normalized["age_max_years"],
        "known_age_only": normalized["known_age_only"],
        "floor_position": normalized["floor_position"],
        "high_value_only": normalized["high_value_only"],
        "high_value_threshold_wan": normalized["high_value_threshold_wan"],
        "target_area_ping": normalized["target_area_ping"],
        "target_age_years": normalized["target_age_years"],
    }


def _public_filters(filters: dict[str, Any]) -> dict[str, Any]:
    return {key: filters.get(key) for key in (
        "county", "district", "period_from", "period_to", "building_type", "area_min_ping", "area_max_ping",
        "age_min_years", "age_max_years", "known_age_only", "floor_position", "high_value_only",
        "high_value_threshold_wan",
    )}


def _segment_identity(filters: dict[str, Any]) -> str:
    parts = [
        f"{filters.get('county', '')}{filters.get('district', '')}",
        str(filters.get("building_type") or "all building types"),
        f"{_compact_number(filters.get('area_min_ping'))}–{_compact_number(filters.get('area_max_ping'))} ping",
    ]
    if _age_filter_applied(filters):
        parts.append("known approximate age only")
    if filters.get("floor_position"):
        parts.append(f"{filters['floor_position']} floor position")
    if filters.get("high_value_only"):
        parts.append(f"high-value proxy >= {_compact_number(filters.get('high_value_threshold_wan'))} wan")
    return " · ".join(parts)


def _age_filter_applied(filters: dict[str, Any]) -> bool:
    return bool(filters.get("known_age_only")) or filters.get("age_min_years") is not None or filters.get("age_max_years") is not None


def _caveats(filters: dict[str, Any]) -> list[str]:
    result = [GENERAL_CAVEAT]
    if _age_filter_applied(filters):
        result.append(AGE_CAVEAT)
    if filters.get("floor_position"):
        result.append(FLOOR_POSITION_RULE)
    if filters.get("high_value_only"):
        result.append(HIGH_VALUE_CAVEAT)
    return result


def _public_comparable(row: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
    age = _positive_number(row.get("building_age_years"))
    target_age = filters.get("target_age_years")
    floor_position = _text(row.get("floor_position"))
    period = _text(row.get("transaction_period")) or ""
    return {
        "transaction_period": period,
        "county": _text(row.get("county")) or filters["county"],
        "district": _text(row.get("district")) or filters["district"],
        "road": _text(row.get("road")) or "",
        "location_display": _text(row.get("road")) or "",
        "building_type": _text(row.get("normalized_building_type")) or "其他/未分類",
        "raw_building_type": _text(row.get("raw_building_type")) or "",
        "area_ping": _number(row.get("area_ping")),
        "floor": _positive_int_or_none(row.get("floor")),
        "total_floor": _positive_int_or_none(row.get("total_floor")),
        "floor_position": floor_position,
        "approximate_building_age_years": age,
        "total_price_wan": _number(row.get("total_price")),
        "unit_price_per_ping": _number(row.get("unit_price_per_ping")),
        "area_difference_ping": _number(row.get("area_difference_ping")),
        "age_difference_years": round(abs(age - float(target_age)), 2) if age is not None and target_age is not None else None,
        "floor_position_relationship": (
            "same" if filters.get("floor_position") and floor_position == filters.get("floor_position")
            else "known" if floor_position else "unknown"
        ),
        "period_recency_months": _period_recency_months(period, filters["period_to"]),
        "source": SOURCE_LABEL,
    }


def _period_recency_months(period: str, reference_period: str) -> int | None:
    try:
        year, month = (int(part) for part in period.split("-"))
        reference_year, reference_month = (int(part) for part in reference_period.split("-"))
        return max(0, (reference_year - year) * 12 + reference_month - month)
    except (TypeError, ValueError):
        return None


def _repository_from_env(*, as_of: date | datetime | None = None) -> PostgresMarketSegmentationRepository | None:
    database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
    return PostgresMarketSegmentationRepository(database_url, as_of=as_of) if database_url else None


def _safe_distribution(value: list[Any]) -> list[dict[str, Any]]:
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        category = _text(item.get("category"))
        if not category:
            continue
        raw_values = item.get("raw_values") if isinstance(item.get("raw_values"), list) else []
        result.append({
            "category": category,
            "count": _int(item.get("count")),
            "raw_values": [text for raw in raw_values if (text := _text(raw))],
        })
    return result


def _shift_month(period: str, offset: int) -> str:
    year, month = (int(part) for part in period.split("-"))
    total = year * 12 + month - 1 + offset
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return _text(value)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return round(number, 2) if math.isfinite(number) else None


def _positive_number(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError, OverflowError):
        return 0


def _positive_int_or_none(value: Any) -> int | None:
    number = _int(value)
    return number if number > 0 else None


def _compact_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "?"
    return str(int(number)) if number.is_integer() else f"{number:g}"


_NORMALIZED_CANDIDATE_CTE = """
with request as (
  select %(canonical_keys)s::text[] as canonical_keys,
         %(period_from)s::varchar(7) as period_from,
         %(period_to)s::varchar(7) as period_to,
         %(county)s::text as county,
         %(district)s::text as district,
         %(building_type)s::text as building_type,
         %(area_min_ping)s::numeric as area_min_ping,
         %(area_max_ping)s::numeric as area_max_ping,
         %(age_min_years)s::numeric as age_min_years,
         %(age_max_years)s::numeric as age_max_years,
         %(known_age_only)s::boolean as known_age_only,
         %(floor_position)s::text as floor_position,
         %(high_value_only)s::boolean as high_value_only,
         %(high_value_threshold_wan)s::numeric as high_value_threshold_wan,
         %(target_area_ping)s::numeric as target_area_ping,
         %(target_age_years)s::numeric as target_age_years
),
candidate as (
  select transaction.id, transaction.transaction_period,
         replace(trim(transaction.city), '臺', '台') as county,
         trim(transaction.district) as district,
         trim(transaction.road) as road,
         trim(transaction.building_type) as raw_building_type,
         case
           when trim(transaction.building_type) in ('住宅大樓(11層含以上有電梯)', '住宅大樓(11層含以上)', '住宅大樓') then '住宅大樓'
           when trim(transaction.building_type) in ('華廈(10層含以下有電梯)', '華廈') then '華廈'
           when trim(transaction.building_type) in ('公寓(5樓含以下無電梯)', '公寓') then '公寓'
           when trim(transaction.building_type) in ('透天', '透天厝') then '透天厝'
           when trim(transaction.building_type) in ('套房(1房1廳1衛)', '套房') then '套房'
           when trim(transaction.building_type) in ('店面(店鋪)', '店面') then '店面'
           when trim(transaction.building_type) in ('其他', '未分類', '') then '其他/未分類'
           else trim(transaction.building_type)
         end as normalized_building_type,
         transaction.area_ping, transaction.building_age_years,
         transaction.floor, transaction.total_floor,
         case
           when transaction.floor > 0 and transaction.total_floor > 0 and transaction.floor <= transaction.total_floor then
             case
               when transaction.floor::numeric / transaction.total_floor <= 0.33 then 'low'
               when transaction.floor::numeric / transaction.total_floor < 0.67 then 'middle'
               else 'high'
             end
           else null
         end as floor_position,
         transaction.unit_price_per_ping, transaction.total_price,
         transaction.dedupe_key, transaction.imported_at,
         request.target_area_ping, request.target_age_years
  from real_price_transactions transaction
  cross join request
  where transaction.source = 'official_plvr_opendata'
    and transaction.transaction_period ~ '^\\d{4}-(0[1-9]|1[0-2])$'
    and transaction.transaction_period between request.period_from and request.period_to
    and transaction.unit_price_per_ping > 0
    and transaction.unit_price_per_ping <= 500
    and transaction.total_price > 0
    and transaction.area_ping > 0
    and (
      replace(regexp_replace(trim(transaction.city), '\\s+', '', 'g'), '臺', '台') || '|' ||
      replace(regexp_replace(trim(transaction.district), '\\s+', '', 'g'), '臺', '台')
    ) = any(request.canonical_keys)
    and replace(trim(transaction.city), '臺', '台') = request.county
    and replace(regexp_replace(trim(transaction.district), '\\s+', '', 'g'), '臺', '台') = request.district
),
base_filtered as (
  select candidate.*
  from candidate
  cross join request
  where (request.building_type = '' or candidate.normalized_building_type = request.building_type)
    and candidate.area_ping >= request.area_min_ping
    and candidate.area_ping < request.area_max_ping
    and (
      not request.high_value_only
      or (
        candidate.normalized_building_type in ('住宅大樓', '華廈', '公寓', '透天厝', '套房')
        and candidate.total_price >= request.high_value_threshold_wan
      )
    )
),
matched as (
  select base_filtered.*
  from base_filtered
  cross join request
  where (
      not request.known_age_only
      or (
        base_filtered.building_age_years > 0
        and (request.age_min_years is null or base_filtered.building_age_years >= request.age_min_years)
        and (request.age_max_years is null or base_filtered.building_age_years <= request.age_max_years)
      )
    )
    and (request.floor_position = '' or base_filtered.floor_position = request.floor_position)
)
"""


SEGMENT_SQL = _NORMALIZED_CANDIDATE_CTE + """
select
  (select count(*)::integer from candidate) as eligible_transaction_count,
  (select count(*)::integer from base_filtered) as base_transaction_count,
  count(*)::integer as matching_transaction_count,
  (select count(*) filter (where building_age_years > 0)::integer from base_filtered) as known_age_count,
  (select count(*) filter (where building_age_years <= 0)::integer from base_filtered) as unknown_age_count,
  (select count(*) filter (where floor_position is not null)::integer from base_filtered) as known_floor_count,
  (select count(*) filter (where floor_position is null)::integer from base_filtered) as unknown_floor_count,
  round(avg(unit_price_per_ping)::numeric, 2) as average_unit_price_per_ping,
  round(percentile_cont(0.5) within group (order by unit_price_per_ping)::numeric, 2) as median_unit_price_per_ping,
  round(percentile_cont(0.25) within group (order by unit_price_per_ping)::numeric, 2) as p25_unit_price_per_ping,
  round(percentile_cont(0.75) within group (order by unit_price_per_ping)::numeric, 2) as p75_unit_price_per_ping,
  round(avg(total_price)::numeric, 2) as average_total_price_wan,
  min(transaction_period) as period_min,
  max(transaction_period) as period_max,
  (select max(imported_at)::date from candidate) as source_updated_at,
  coalesce((
    select jsonb_agg(
      jsonb_build_object('category', distribution.normalized_building_type, 'count', distribution.count, 'raw_values', distribution.raw_values)
      order by distribution.count desc, distribution.normalized_building_type
    )
    from (
      select normalized_building_type, count(*)::integer as count,
             array_agg(distinct raw_building_type order by raw_building_type) as raw_values
      from candidate
      group by normalized_building_type
    ) distribution
  ), '[]'::jsonb) as building_type_distribution
from matched
"""


COMPARABLES_SQL = _NORMALIZED_CANDIDATE_CTE + """
, deduplicated as (
  select matched.*,
         row_number() over (
           partition by coalesce(nullif(trim(matched.dedupe_key), ''), 'row:' || matched.id::text)
           order by matched.transaction_period desc, matched.id desc
         ) as dedupe_rank
  from matched
)
select transaction_period, county, district, road, raw_building_type, normalized_building_type,
       area_ping, building_age_years, floor, total_floor, floor_position,
       unit_price_per_ping, total_price,
       round(abs(area_ping - target_area_ping)::numeric, 2) as area_difference_ping
from deduplicated
where dedupe_rank = 1
order by
  abs(area_ping - target_area_ping) asc,
  case
    when target_age_years is null then 0
    when building_age_years > 0 then abs(building_age_years - target_age_years)
    else 100000
  end asc,
  case when floor_position is null then 1 else 0 end asc,
  transaction_period desc,
  id desc
limit %(limit)s
"""
