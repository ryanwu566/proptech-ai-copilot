"""Seed bundled valuation samples into a prepared Supabase/Postgres database."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRANSACTIONS_PATH = ROOT / "data" / "real_price_sample.csv"
COMMUNITIES_PATH = ROOT / "data" / "community_building_sample.csv"


def seed(database_url: str | None = None) -> int:
    """Seed sample rows only when an explicit backend database URL exists."""

    url = (database_url if database_url is not None else os.getenv("VALUATION_DATABASE_URL", "")).strip()
    if not url:
        print("未設定 VALUATION_DATABASE_URL，略過 Supabase/Postgres sample seed。")
        return 0
    try:
        import psycopg

        transactions = _read_csv(TRANSACTIONS_PATH)
        communities = _read_csv(COMMUNITIES_PATH)
        with psycopg.connect(url, connect_timeout=10, prepare_threshold=None) as connection:
            with connection.cursor() as cursor:
                cursor.execute("delete from real_price_transactions where source = %s", ["real_price_sample"])
                cursor.executemany(
                    """
                    insert into real_price_transactions (
                        transaction_period, city, district, road, address_text, building_type,
                        area_ping, building_age_years, floor, total_floor, unit_price_per_ping,
                        total_price, lat, lng, source, raw_note
                    ) values (
                        %(transaction_period)s, %(city)s, %(district)s, %(road)s, %(address_text)s,
                        %(building_type)s, %(area_ping)s, %(building_age_years)s, %(floor)s,
                        %(total_floor)s, %(unit_price_per_ping)s, %(total_price)s, %(lat)s, %(lng)s,
                        %(source)s, %(raw_note)s
                    )
                    """,
                    [_transaction_params(row) for row in transactions],
                )
                cursor.executemany(
                    """
                    insert into community_buildings (
                        community_id, community_name, city, district, road, address_pattern,
                        lat, lng, building_type, completed_year, total_floors, source, confidence
                    ) values (
                        %(community_id)s, %(community_name)s, %(city)s, %(district)s, %(road)s,
                        %(address_pattern)s, %(lat)s, %(lng)s, %(building_type)s, %(completed_year)s,
                        %(total_floors)s, %(source)s, %(confidence)s
                    )
                    on conflict (community_id) do update set
                        community_name = excluded.community_name,
                        city = excluded.city,
                        district = excluded.district,
                        road = excluded.road,
                        address_pattern = excluded.address_pattern,
                        lat = excluded.lat,
                        lng = excluded.lng,
                        building_type = excluded.building_type,
                        completed_year = excluded.completed_year,
                        total_floors = excluded.total_floors,
                        source = excluded.source,
                        confidence = excluded.confidence,
                        updated_at = now()
                    """,
                    communities,
                )
                cursor.execute(
                    """
                    insert into valuation_import_runs (source_name, source_period, record_count, status, note)
                    values (%s, %s, %s, %s, %s)
                    """,
                    ["real_price_sample", "sample", len(transactions), "completed", "Bundled sample seed; not full Taiwan data"],
                )
        print(f"已寫入 {len(transactions)} 筆展示交易與 {len(communities)} 筆社區索引。")
        return 0
    except Exception:
        print("Supabase/Postgres sample seed 未完成，請確認 schema、連線字串與網路權限。")
        return 1


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _transaction_params(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "address_text": row.get("address_text", ""),
        "total_floor": int(float(row.get("total_floor") or 0)) or None,
        "source": "real_price_sample",
        "raw_note": "Bundled demonstration comparable",
    }


if __name__ == "__main__":
    raise SystemExit(seed())
