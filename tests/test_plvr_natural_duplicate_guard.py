"""Regression tests for the PLVR natural-key duplicate guard."""

from __future__ import annotations

from scripts.import_plvr_to_postgres import CHUNK_DUPLICATE_INSPECTION_SQL, CHUNK_UPSERT_SQL
from services.plvr_import_service import build_dedupe_key


def transaction(**overrides: object) -> dict[str, object]:
    """Return one normalized official transaction."""
    row: dict[str, object] = {
        "source": "official_plvr_opendata",
        "city": "台南市",
        "district": "中西區",
        "transaction_period": "2025-06",
        "address_text": "民生路二段100號",
        "road": "民生路二段",
        "building_type": "住宅大樓",
        "area_ping": 30.12,
        "total_price": 1800.0,
        "unit_price_per_ping": 59.76,
    }
    row.update(overrides)
    return row


def test_upsert_checks_natural_key_before_insert() -> None:
    compact = " ".join(CHUNK_UPSERT_SQL.split())

    assert "natural_rank > 1 or exists" in compact
    assert "from real_price_transactions existing" in compact
    assert "where not is_natural_duplicate and not is_dedupe_key_duplicate" in compact


def test_natural_key_is_independent_from_old_or_serial_based_dedupe_key() -> None:
    natural_section = CHUNK_UPSERT_SQL.split("as is_natural_duplicate", maxsplit=1)[0]

    assert "existing.transaction_period = staged.transaction_period" in natural_section
    assert "existing.address_text" in natural_section
    assert "existing.road" in natural_section
    assert "existing.building_type" in natural_section
    assert "existing.total_price" in natural_section
    assert "existing.dedupe_key = staged.dedupe_key" not in natural_section
    assert "transaction_id" not in natural_section


def test_natural_key_normalizes_city_text_and_numeric_precision() -> None:
    compact = " ".join(CHUNK_UPSERT_SQL.split())

    assert "replace(regexp_replace(coalesce(existing.city, ''), '\\s+', '', 'g'), '臺', '台')" in compact
    assert "round(coalesce(existing.area_ping, 0), 2)" in compact
    assert "round(coalesce(existing.total_price, 0), 2)" in compact
    assert "round(coalesce(existing.unit_price_per_ping, 0), 2)" in compact


def test_natural_guard_allows_different_address_price_or_period() -> None:
    sql = " ".join(CHUNK_UPSERT_SQL.split())

    assert "existing.address_text" in sql
    assert "existing.total_price" in sql
    assert "existing.transaction_period" in sql


def test_dry_run_inspection_uses_same_natural_guard() -> None:
    for fragment in (
        "natural_rank > 1",
        "existing.transaction_period = staged.transaction_period",
        "existing.address_text",
        "existing.total_price",
        "existing.unit_price_per_ping",
    ):
        assert fragment in CHUNK_DUPLICATE_INSPECTION_SQL


def test_dedupe_v2_remains_cross_city_safe_and_stable() -> None:
    base = transaction()
    same = transaction(city="臺南市")
    other_city = transaction(city="台中市")

    assert build_dedupe_key(base, "SERIAL-1") == build_dedupe_key(same, "SERIAL-1")
    assert build_dedupe_key(base, "SERIAL-1") != build_dedupe_key(other_city, "SERIAL-1")
