"""Safely inspect or prune official PLVR rows outside a rolling retention window."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Any

OFFICIAL_SOURCE = "official_plvr_opendata"
DEFAULT_KEEP_YEARS = 5
WARNING = "只處理超出保留期間的官方 PLVR；不會刪除展示樣本、社區資料或匯入紀錄。"


def build_parser() -> argparse.ArgumentParser:
    """Build the guarded retention command interface."""

    parser = argparse.ArgumentParser(description="安全盤點或清理 rolling 5 年外的官方 PLVR 資料")
    parser.add_argument("--before", default="", help="刪除早於此 YYYY-MM 的官方資料")
    parser.add_argument("--keep-years", type=int, default=DEFAULT_KEEP_YEARS, help="保留年數，預設 5")
    parser.add_argument("--cities", default="", help="限定城市，以逗號分隔")
    parser.add_argument("--source", default=OFFICIAL_SOURCE, help="固定為 official_plvr_opendata")
    parser.add_argument("--dry-run", action="store_true", help="只盤點，不刪除；未確認刪除時亦為預設模式")
    parser.add_argument("--confirm-delete", action="store_true", help="明確確認刪除符合條件的官方 PLVR")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a dry-run by default and delete only after explicit confirmation."""

    args = build_parser().parse_args(argv)
    if args.source != OFFICIAL_SOURCE:
        print("安全限制：--source 只允許 official_plvr_opendata。")
        return 1
    if args.keep_years < 1:
        print("--keep-years 必須大於 0。")
        return 1
    cutoff = args.before or retention_cutoff_period(args.keep_years)
    if not _valid_period(cutoff):
        print("--before 必須使用 YYYY-MM 格式。")
        return 1

    database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
    if not database_url:
        print("未設定 VALUATION_DATABASE_URL；無法盤點資料庫，但不會刪除任何資料。")
        return 0

    cities = normalize_cities(args.cities)
    will_delete = bool(args.confirm_delete and not args.dry_run)
    try:
        report = inspect_and_prune(database_url, cutoff, cities, will_delete)
    except Exception as error:
        print(f"PLVR 保留策略檢查未完成：{type(error).__name__}。未刪除任何資料。")
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def retention_cutoff_period(keep_years: int, current_period: str | None = None) -> str:
    """Return the first retained month for an inclusive rolling-year window."""

    current = current_period or datetime.now(UTC).strftime("%Y-%m")
    year, month = map(int, current.split("-"))
    total = year * 12 + month - 1 - (keep_years * 12 - 1)
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def normalize_city(value: str) -> str:
    """Normalize common Taiwan city glyph variants."""

    return value.strip().replace("臺", "台")


def normalize_cities(value: str) -> list[str]:
    """Return unique normalized cities from a comma-separated string."""

    return list(dict.fromkeys(normalize_city(item) for item in value.split(",") if item.strip()))


def inspect_and_prune(database_url: str, cutoff: str, cities: list[str], will_delete: bool) -> dict[str, Any]:
    """Inspect matching official rows and optionally delete them in one transaction."""

    import psycopg
    from psycopg.rows import dict_row

    clauses = [
        "source = %s",
        "transaction_period ~ '^\\d{4}-(0[1-9]|1[0-2])$'",
        "transaction_period < %s",
    ]
    params: list[Any] = [OFFICIAL_SOURCE, cutoff]
    if cities:
        clauses.append("replace(trim(city), '臺', '台') = any(%s)")
        params.append(cities)
    where = " and ".join(clauses)

    with psycopg.connect(
        database_url,
        connect_timeout=10,
        prepare_threshold=None,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"select count(*) as matched_rows from real_price_transactions where {where}",
                params,
            )
            matched_rows = int(cursor.fetchone()["matched_rows"] or 0)
            cursor.execute(
                f"""
                select replace(trim(city), '臺', '台') as city, count(*) as rows
                from real_price_transactions where {where}
                group by replace(trim(city), '臺', '台') order by city
                """,
                params,
            )
            rows_by_city = {str(row["city"]): int(row["rows"]) for row in cursor.fetchall()}
            cursor.execute(
                f"""
                select transaction_period as period, count(*) as rows
                from real_price_transactions where {where}
                group by transaction_period order by transaction_period
                """,
                params,
            )
            rows_by_period = {str(row["period"]): int(row["rows"]) for row in cursor.fetchall()}
            deleted_rows = 0
            if will_delete and matched_rows:
                cursor.execute(f"delete from real_price_transactions where {where}", params)
                deleted_rows = int(cursor.rowcount or 0)

    return {
        "cutoff_period": cutoff,
        "matched_rows": matched_rows,
        "rows_by_city": rows_by_city,
        "rows_by_period": rows_by_period,
        "will_delete": will_delete,
        "deleted_rows": deleted_rows,
        "status": "deleted" if will_delete else "dry_run",
        "warning": WARNING,
    }


def _valid_period(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value))


if __name__ == "__main__":
    raise SystemExit(main())
