"""Central Bank institution posted-rate references with mock fallback."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, Callable

import httpx

from services.mortgage_rate_service import _find_records, _to_float


SOURCE_URL = "https://cpx.cbc.gov.tw/api/OpenData/DataSet?set_id=9464&index=0"
NOTES = ["此為銀行牌告利率參考，不代表實際核貸條件", "實際利率仍依信用條件、擔保品、收入、負債比與銀行方案而定"]
CACHE_TTL_SECONDS = 3600
MOCK_ROWS = [
    {"bank_code": "0040000", "bank_name": "臺灣銀行", "rate_name": "指數房貸指標利率", "variable_rate": 1.72, "fixed_rate": None, "effective_date": "2026-05-01"},
    {"bank_code": "0050000", "bank_name": "臺灣土地銀行", "rate_name": "指數房貸指標利率", "variable_rate": 1.74, "fixed_rate": None, "effective_date": "2026-05-01"},
    {"bank_code": "0080000", "bank_name": "華南商業銀行", "rate_name": "基準利率", "variable_rate": 2.12, "fixed_rate": None, "effective_date": "2026-05-01"},
]
_CACHE: tuple[float, str, list[dict[str, Any]]] | None = None


def load_bank_rates(fetcher: Callable[[], Any] | None = None, force_refresh: bool = False) -> tuple[str, list[dict[str, Any]]]:
    """Load normalized posted rates once per hour."""

    global _CACHE
    now = time.monotonic()
    if fetcher is None and not force_refresh and _CACHE and now - _CACHE[0] < CACHE_TTL_SECONDS:
        return _CACHE[1], _CACHE[2]
    try:
        rows = normalize_bank_rates(fetcher() if fetcher else _fetch())
        if not rows:
            raise ValueError("empty")
        source = "central_bank_opendata"
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError):
        source, rows = "mock", MOCK_ROWS
    if fetcher is None:
        _CACHE = (now, source, rows)
    return source, rows


def list_institutions(fetcher: Callable[[], Any] | None = None) -> dict[str, Any]:
    source, rows = load_bank_rates(fetcher)
    institutions = sorted({(row["bank_code"], row["bank_name"]) for row in rows})
    return {"source": source, "institutions": [{"bank_code": code, "bank_name": name} for code, name in institutions], "updated_at": datetime.now(UTC).isoformat(), "notes": ["本資料為銀行牌告利率參考，不代表實際核貸利率"]}


def get_bank_mortgage_rates(bank_code: str, fetcher: Callable[[], Any] | None = None) -> dict[str, Any]:
    source, rows = load_bank_rates(fetcher)
    bank_rows = [row for row in rows if row["bank_code"] == bank_code]
    if not bank_rows:
        bank_rows = [row for row in MOCK_ROWS if row["bank_code"] == MOCK_ROWS[0]["bank_code"]]
        source = "mock"
    preferred = [row for row in bank_rows if any(term in row["rate_name"] for term in ("指數房貸", "房貸", "基準利率", "放款"))] or bank_rows
    items = [{**row, "rate_type": "index_mortgage" if "指數房貸" in row["rate_name"] else "reference_rate", "raw_rate_name": row["rate_name"]} for row in preferred]
    summary = next((item["variable_rate"] for item in items if item["variable_rate"] is not None), None)
    return {"source": source, "bank_code": items[0]["bank_code"], "bank_name": items[0]["bank_name"], "items": items, "summary_rate": summary, "summary_label": items[0]["rate_name"] if items else "未找到明確房貸牌告項目", "notes": NOTES, "fetched_at": datetime.now(UTC).isoformat()}


def normalize_bank_rates(payload: Any) -> list[dict[str, Any]]:
    rows = []
    for row in _find_records(payload):
        code = _pick(row, ("金融機構代號", "銀行代號", "機構代號", "bank_code"))
        name = _pick(row, ("金融機構名稱", "銀行名稱", "機構名稱", "bank_name"))
        rate_name = _pick(row, ("牌告利率名稱", "利率名稱", "項目", "rate_name"))
        if not code or not name or not rate_name:
            continue
        rows.append({"bank_code": code, "bank_name": name, "rate_name": rate_name, "fixed_rate": _pick_float(row, ("固定利率", "fixed_rate")), "variable_rate": _pick_float(row, ("機動利率", "variable_rate", "利率")), "effective_date": _pick(row, ("生效日期", "資料日期", "effective_date"))})
    return rows


def _fetch() -> Any:
    with httpx.Client(timeout=5.0) as client:
        response = client.get(SOURCE_URL, headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()


def _pick(row: dict[str, Any], names: tuple[str, ...]) -> str:
    for name in names:
        if name in row and str(row[name]).strip():
            return str(row[name]).strip()
    return ""


def _pick_float(row: dict[str, Any], names: tuple[str, ...]) -> float | None:
    return _to_float(_pick(row, names))
