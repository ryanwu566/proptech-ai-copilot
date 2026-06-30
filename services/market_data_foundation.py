"""Traceable Market Insight data contract and aggregate loader.

This module intentionally does not call external providers and does not fall
back to bundled mock data. Production Market Insight should only display
numbers when a traceable aggregate artifact exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal


BASE_DIR = Path(__file__).resolve().parents[1]
MARKET_AGGREGATE_PATH = BASE_DIR / "data" / "market" / "market_insight_aggregate.json"

DATA_STATUS_VALUES = ("available", "no_data", "unavailable", "incomplete", "invalid")
COVERAGE_STATUS_VALUES = ("nationwide", "partial", "unknown")
MarketDataStatus = Literal["available", "no_data", "unavailable", "incomplete", "invalid"]
MarketCoverageStatus = Literal["nationwide", "partial", "unknown"]

MARKET_DATA_CAVEAT = (
    "市場資料僅供區域行情背景參考；資料不足、尚未匯入或暫時不可用時，不代表價格較低、"
    "風險較低或適合購買。"
)
UNAVAILABLE_SUMMARY = "目前尚未接上可追溯的正式市場資料，暫不顯示平均單價、交易量、趨勢或 ESG 輔助分數。"


class MarketDataContractError(RuntimeError):
    """Raised when an aggregate artifact violates the public data contract."""


def market_unavailable_response(city: str = "", district: str = "") -> dict[str, Any]:
    """Build a safe unavailable response without mock metrics."""

    return {
        "city": city,
        "county": city,
        "district": district,
        "period": None,
        "average_unit_price": None,
        "avg_price_per_ping": None,
        "transaction_count": None,
        "transaction_volume": None,
        "trend": [],
        "livability_score": None,
        "esg_lite_score": None,
        "poi_breakdown": {},
        "sdg11_note": "",
        "summary": UNAVAILABLE_SUMMARY,
        "source_name": None,
        "source_updated_at": None,
        "coverage_status": "unknown",
        "data_status": "unavailable",
        "caveat": MARKET_DATA_CAVEAT,
        "disclaimer": MARKET_DATA_CAVEAT,
        "source_file_hash": None,
        "aggregation_method": None,
        "record_count": 0,
    }


def market_catalog_unavailable() -> dict[str, Any]:
    """Build a selector catalog response when no aggregate exists."""

    return {
        "regions": [],
        "data_status": "unavailable",
        "coverage_status": "unknown",
        "source_name": None,
        "source_updated_at": None,
        "caveat": MARKET_DATA_CAVEAT,
    }


def load_market_aggregate(path: Path | None = None) -> dict[str, Any] | None:
    """Load a traceable market aggregate artifact if one has been prepared."""

    aggregate_path = path or MARKET_AGGREGATE_PATH
    if not aggregate_path.exists():
        return None
    try:
        payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MarketDataContractError("Market aggregate artifact is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise MarketDataContractError("Market aggregate artifact must be a JSON object.")
    return payload


def list_market_regions(path: Path | None = None) -> dict[str, Any]:
    """Return available aggregate regions with safe metadata."""

    payload = load_market_aggregate(path)
    if payload is None:
        return market_catalog_unavailable()
    regions = [_normalize_region(record, payload) for record in _region_records(payload)]
    available_regions = [region for region in regions if region["data_status"] == "available"]
    return {
        "regions": [
            {
                "city": region["city"],
                "county": region["county"],
                "district": region["district"],
                "period": region["period"],
                "data_status": region["data_status"],
            }
            for region in available_regions
        ],
        "data_status": "available" if available_regions else "unavailable",
        "coverage_status": _coverage_status(payload.get("coverage_status")),
        "source_name": _optional_string(payload.get("source_name")),
        "source_updated_at": _optional_string(payload.get("source_updated_at")),
        "caveat": _optional_string(payload.get("caveat")) or MARKET_DATA_CAVEAT,
    }


def get_market_summary(city: str, district: str, path: Path | None = None) -> dict[str, Any]:
    """Return one market summary or a safe unavailable response."""

    payload = load_market_aggregate(path)
    if payload is None:
        return market_unavailable_response(city=city, district=district)
    for record in _region_records(payload):
        region = _normalize_region(record, payload)
        if region["city"] == city and region["district"] == district:
            return region if region["data_status"] == "available" else market_unavailable_response(city, district)
    return market_unavailable_response(city=city, district=district)


def build_market_region_record(record: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Public helper used by the importer and tests to enforce the contract."""

    return _normalize_region(record, metadata)


def _region_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("regions")
    if not isinstance(records, list):
        raise MarketDataContractError("Market aggregate artifact must contain a regions list.")
    return [record for record in records if isinstance(record, dict)]


def _normalize_region(record: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    county = _required_string(record.get("county") or record.get("city"), "county")
    district = _required_string(record.get("district"), "district")
    period = _required_string(record.get("period"), "period")
    data_status = _data_status(record.get("data_status", metadata.get("data_status", "available")))
    coverage_status = _coverage_status(record.get("coverage_status", metadata.get("coverage_status", "unknown")))
    source_name = _required_string(record.get("source_name", metadata.get("source_name")), "source_name")
    source_updated_at = _required_string(
        record.get("source_updated_at", metadata.get("source_updated_at")),
        "source_updated_at",
    )
    caveat = _optional_string(record.get("caveat", metadata.get("caveat"))) or MARKET_DATA_CAVEAT
    source_file_hash = _optional_string(record.get("source_file_hash", metadata.get("source_file_hash")))
    aggregation_method = _optional_string(record.get("aggregation_method", metadata.get("aggregation_method")))
    record_count = _non_negative_int(record.get("record_count", metadata.get("record_count", 0)), "record_count")

    if data_status != "available":
        return {
            **market_unavailable_response(city=county, district=district),
            "period": period,
            "source_name": source_name,
            "source_updated_at": source_updated_at,
            "coverage_status": coverage_status,
            "data_status": data_status,
            "caveat": caveat,
            "disclaimer": caveat,
            "source_file_hash": source_file_hash,
            "aggregation_method": aggregation_method,
            "record_count": record_count,
        }

    average_unit_price = _positive_number(record.get("average_unit_price"), "average_unit_price")
    transaction_count = _non_negative_int(record.get("transaction_count"), "transaction_count")
    trend = _safe_trend(record.get("trend", []))
    livability_score = _optional_score(record.get("livability_score"))
    esg_lite_score = _optional_score(record.get("esg_lite_score"))

    return {
        "city": county,
        "county": county,
        "district": district,
        "period": period,
        "average_unit_price": average_unit_price,
        "avg_price_per_ping": average_unit_price,
        "transaction_count": transaction_count,
        "transaction_volume": transaction_count,
        "trend": trend,
        "livability_score": livability_score,
        "esg_lite_score": esg_lite_score,
        "poi_breakdown": _safe_score_map(record.get("poi_breakdown", {})),
        "sdg11_note": _optional_string(record.get("sdg11_note")) or "",
        "summary": _optional_string(record.get("summary")) or "已載入可追溯的行政區市場聚合資料。",
        "source_name": source_name,
        "source_updated_at": source_updated_at,
        "coverage_status": coverage_status,
        "data_status": data_status,
        "caveat": caveat,
        "disclaimer": caveat,
        "source_file_hash": source_file_hash,
        "aggregation_method": aggregation_method,
        "record_count": record_count,
    }


def _required_string(value: Any, field: str) -> str:
    text = _optional_string(value)
    if not text:
        raise MarketDataContractError(f"Market aggregate missing required field: {field}.")
    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _data_status(value: Any) -> MarketDataStatus:
    text = str(value).strip()
    if text not in DATA_STATUS_VALUES:
        raise MarketDataContractError("Market aggregate has an invalid data_status.")
    return text  # type: ignore[return-value]


def _coverage_status(value: Any) -> MarketCoverageStatus:
    text = str(value).strip()
    if text not in COVERAGE_STATUS_VALUES:
        raise MarketDataContractError("Market aggregate has an invalid coverage_status.")
    return text  # type: ignore[return-value]


def _positive_number(value: Any, field: str) -> float:
    number = float(value)
    if number <= 0:
        raise MarketDataContractError(f"Market aggregate field must be positive: {field}.")
    return number


def _non_negative_int(value: Any, field: str) -> int:
    number = int(value)
    if number < 0:
        raise MarketDataContractError(f"Market aggregate field must be non-negative: {field}.")
    return number


def _optional_score(value: Any) -> int | None:
    if value is None:
        return None
    score = round(float(value))
    return max(0, min(100, score))


def _safe_score_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    scores: dict[str, int] = {}
    for key, raw_score in value.items():
        label = _optional_string(key)
        if label:
            scores[label] = _optional_score(raw_score) or 0
    return scores


def _safe_trend(value: Any) -> list[float]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MarketDataContractError("Market aggregate trend must be a list when provided.")
    return [float(item) for item in value]
