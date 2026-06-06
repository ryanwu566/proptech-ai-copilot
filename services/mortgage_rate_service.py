"""Central Bank OpenData mortgage-rate reference with a safe mock fallback."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any, Callable

import httpx


SOURCE_URL = "https://cpx.cbc.gov.tw/api/OpenData/DataSet?set_id=10359&index=0"
SOURCE_NAME = "中央銀行 OpenData：五大銀行存放款利率歷史月資料"
NOTES = ["本資料為月資料，非即時核貸利率", "實際房貸利率仍依銀行、信用條件、擔保品與方案而定"]
MOCK_REFERENCE_RATE = 2.185
CACHE_TTL_SECONDS = 3600
_CACHE: tuple[float, dict[str, Any]] | None = None


def get_latest_mortgage_rate(
    fetcher: Callable[[], Any] | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Fetch and cache the latest official monthly reference, or return mock data."""

    global _CACHE
    now = time.monotonic()
    if fetcher is None and not force_refresh and _CACHE and now - _CACHE[0] < CACHE_TTL_SECONDS:
        return _CACHE[1]
    try:
        payload = fetcher() if fetcher else _fetch_central_bank()
        result = parse_latest_rate(payload)
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError):
        result = _fallback_result()
    if fetcher is None:
        _CACHE = (now, result)
    return result


def parse_latest_rate(payload: Any) -> dict[str, Any]:
    """Normalize common Central Bank OpenData JSON wrappers and rate fields."""

    records = _find_records(payload)
    if not records:
        raise ValueError("央行 OpenData 未回傳可解析資料。")
    latest = max(records, key=lambda row: _period_sort_key(_find_period(row)))
    period = _normalize_period(_find_period(latest))
    available_fields = list(latest.keys())
    preferred = [key for key in available_fields if any(term in key for term in ("指數房貸", "房貸月指", "房貸"))]
    reference_rate = _first_numeric(latest, preferred) or _first_rate_like_numeric(latest)
    if reference_rate is None:
        raise ValueError("央行 OpenData 未找到可用利率欄位。")
    return _result("central_bank_opendata", period, reference_rate, available_fields)


def _fetch_central_bank() -> Any:
    with httpx.Client(timeout=5.0) as client:
        response = client.get(SOURCE_URL, headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()


def _find_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("data", "Data", "records", "Records", "result", "Result"):
            if key in payload:
                found = _find_records(payload[key])
                if found:
                    return found
        for value in payload.values():
            found = _find_records(value)
            if found:
                return found
    return []


def _find_period(row: dict[str, Any]) -> str:
    for key, value in row.items():
        if any(term in key.lower() for term in ("period", "date", "month", "年月", "期別", "資料時間")):
            return str(value)
    return ""


def _normalize_period(value: str) -> str:
    numbers = re.findall(r"\d+", value)
    if len(numbers) >= 2:
        year = int(numbers[0])
        if year < 1911:
            year += 1911
        return f"{year:04d}-{int(numbers[1]):02d}"
    return value or datetime.now(UTC).strftime("%Y-%m")


def _period_sort_key(value: str) -> tuple[int, ...]:
    return tuple(int(item) for item in re.findall(r"\d+", value)) or (0,)


def _first_numeric(row: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _to_float(row.get(key))
        if value is not None:
            return value
    return None


def _first_rate_like_numeric(row: dict[str, Any]) -> float | None:
    keys = [key for key in row if any(term in key for term in ("利率", "率", "Rate", "rate"))]
    return _first_numeric(row, keys)


def _to_float(value: Any) -> float | None:
    try:
        cleaned = str(value).replace("%", "").replace(",", "").strip()
        return float(cleaned) if cleaned else None
    except (TypeError, ValueError):
        return None


def _fallback_result() -> dict[str, Any]:
    return _result("mock", datetime.now(UTC).strftime("%Y-%m"), MOCK_REFERENCE_RATE, [])


def _result(source: str, period: str, rate: float, fields: list[str]) -> dict[str, Any]:
    return {
        "source": source,
        "source_name": SOURCE_NAME,
        "period": period,
        "reference_rate": round(float(rate), 4),
        "rate_type": "五大銀行房貸相關月資料",
        "available_fields": fields,
        "notes": NOTES,
        "fetched_at": datetime.now(UTC).isoformat(),
    }
