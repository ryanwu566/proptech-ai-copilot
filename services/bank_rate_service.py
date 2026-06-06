"""Central Bank institution posted-rate references with a resilient fallback."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any, Callable, Iterable

import httpx

from services.mortgage_rate_service import _to_float


SOURCE_URL = "https://cpx.cbc.gov.tw/api/OpenData/DataSet?set_id=9464&index=0"
NOTES = [
    "資料為中央銀行 OpenData 牌告利率參考，非即時房貸報價。",
    "實際利率仍依銀行、信用條件、擔保品與方案而定。",
]
CACHE_TTL_SECONDS = 3600
MORTGAGE_TERMS = ("指數房貸", "房貸", "房屋貸款", "基準利率", "放款", "擔保放款")

_BANKS = [
    ("0040000", "臺灣銀行", 1.72),
    ("0050000", "臺灣土地銀行", 1.74),
    ("0060000", "合作金庫商業銀行", 1.76),
    ("0070000", "第一商業銀行", 1.78),
    ("0080000", "華南商業銀行", 1.80),
    ("0090000", "彰化商業銀行", 1.82),
    ("0170000", "兆豐國際商業銀行", 1.79),
    ("0120000", "台北富邦商業銀行", 1.88),
    ("0130000", "國泰世華商業銀行", 1.90),
    ("8080000", "玉山商業銀行", 1.86),
    ("8120000", "台新國際商業銀行", 1.92),
    ("8070000", "永豐商業銀行", 1.89),
    ("8220000", "中國信託商業銀行", 1.91),
]
MOCK_ROWS = [
    {
        "bank_code": code,
        "bank_name": name,
        "rate_name": "指數型房貸參考利率",
        "variable_rate": rate,
        "fixed_rate": None,
        "effective_date": "2026-05-01",
    }
    for code, name, rate in _BANKS
]
_CACHE: tuple[float, str, list[dict[str, Any]]] | None = None

FIELD_ALIASES = {
    "bank_code": ("金融機構代號", "銀行代號", "機構代號", "bank_code"),
    "bank_name": ("金融機構名稱", "銀行名稱", "機構名稱", "bank_name"),
    "rate_name": ("牌告利率名稱", "利率名稱", "項目名稱", "項目", "rate_name"),
    "fixed_rate": ("固定利率", "fixed_rate"),
    "variable_rate": ("機動利率", "浮動利率", "利率", "variable_rate"),
    "effective_date": ("生效日期", "資料日期", "effective_date"),
}
NUMBERED_FIELDS = {
    "0": "effective_date",
    "1": "bank_code",
    "2": "bank_name",
    "3": "rate_name",
    "4": "rate_name",
    "10": "effective_date",
    "12": "fixed_rate",
    "13": "variable_rate",
}


def load_bank_rates(
    fetcher: Callable[[], Any] | None = None,
    force_refresh: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    """Load normalized posted rates once per hour."""

    global _CACHE
    now = time.monotonic()
    if fetcher is None and not force_refresh and _CACHE and now - _CACHE[0] < CACHE_TTL_SECONDS:
        return _CACHE[1], _CACHE[2]
    try:
        rows = normalize_bank_rates(fetcher() if fetcher else _fetch())
        if not rows:
            raise ValueError("No usable bank-rate records")
        source = "central_bank_opendata"
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError):
        source, rows = "mock", MOCK_ROWS
    if fetcher is None:
        _CACHE = (now, source, rows)
    return source, rows


def list_institutions(fetcher: Callable[[], Any] | None = None) -> dict[str, Any]:
    """Return unique institutions from OpenData or the broad fallback list."""

    source, rows = load_bank_rates(fetcher)
    institutions = sorted({(row["bank_code"], row["bank_name"]) for row in rows})
    return {
        "source": source,
        "institution_count": len(institutions),
        "institutions": [{"bank_code": code, "bank_name": name} for code, name in institutions],
        "updated_at": datetime.now(UTC).isoformat(),
        "notes": NOTES,
    }


def get_bank_mortgage_rates(bank_code: str, fetcher: Callable[[], Any] | None = None) -> dict[str, Any]:
    """Return mortgage-related posted rates for one institution."""

    source, rows = load_bank_rates(fetcher)
    bank_rows = [row for row in rows if row["bank_code"] == bank_code]
    if not bank_rows:
        bank_rows = [row for row in MOCK_ROWS if row["bank_code"] == MOCK_ROWS[0]["bank_code"]]
        source = "mock"
    mortgage_rows = [row for row in bank_rows if any(term in row["rate_name"] for term in MORTGAGE_TERMS)]
    preferred = mortgage_rows or bank_rows
    items = [
        {
            **row,
            "rate_type": "index_mortgage" if "指數房貸" in row["rate_name"] else "reference_rate",
            "raw_rate_name": row["rate_name"],
        }
        for row in preferred
    ]
    summary = next((item["variable_rate"] for item in items if item["variable_rate"] is not None), None)
    summary_label = items[0]["rate_name"] if mortgage_rows else "未找到明確房貸牌告項目"
    return {
        "source": source,
        "bank_code": items[0]["bank_code"],
        "bank_name": items[0]["bank_name"],
        "items": items,
        "summary_rate": summary,
        "summary_label": summary_label,
        "notes": NOTES,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def normalize_bank_rates(payload: Any) -> list[dict[str, Any]]:
    """Normalize list, nested JSON, and CBC ``Data.value`` string records."""

    rows: list[dict[str, Any]] = []
    for raw in _walk_records(payload):
        row = _expand_value_record(raw)
        code = _pick(row, FIELD_ALIASES["bank_code"])
        name = _pick(row, FIELD_ALIASES["bank_name"])
        rate_name = _pick(row, FIELD_ALIASES["rate_name"])
        if not code or not name or not rate_name:
            continue
        rows.append(
            {
                "bank_code": code,
                "bank_name": name,
                "rate_name": rate_name,
                "fixed_rate": _pick_float(row, FIELD_ALIASES["fixed_rate"]),
                "variable_rate": _pick_float(row, FIELD_ALIASES["variable_rate"]),
                "effective_date": _pick(row, FIELD_ALIASES["effective_date"]),
            }
        )
    return rows


def _walk_records(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _walk_records(item)
    elif isinstance(value, dict):
        if any(not isinstance(item, (dict, list)) for item in value.values()):
            yield value
        for item in value.values():
            if isinstance(item, (dict, list)):
                yield from _walk_records(item)


def _expand_value_record(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("value")
    if value is None and isinstance(row.get("Data"), dict):
        value = row["Data"].get("value")
    if not isinstance(value, str):
        return row
    return {**row, **_parse_value_string(value)}


def _parse_value_string(value: str) -> dict[str, str]:
    """Parse CBC's numbered-label comma string into normalized aliases."""

    tokens = [token.strip() for token in re.split(r"[,;|\n\r\t]+", value) if token.strip()]
    parsed: dict[str, str] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        inline = re.match(r"^(\d{1,2})([^:=：]+?)[:=：](.+)$", token)
        if inline:
            number, label, content = inline.groups()
            _store_numbered(parsed, number, label, content)
            index += 1
            continue
        label_match = re.match(r"^(\d{1,2})(.+)$", token)
        if label_match and index + 1 < len(tokens):
            number, label = label_match.groups()
            _store_numbered(parsed, number, label, tokens[index + 1])
            index += 2
            continue
        index += 1
    return parsed


def _store_numbered(parsed: dict[str, str], number: str, label: str, value: str) -> None:
    parsed[label.strip()] = value.strip()
    normalized = NUMBERED_FIELDS.get(number)
    if normalized:
        parsed[normalized] = value.strip()


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
