"""Manually normalize a supplied PLVR ZIP/CSV and optionally write it to Postgres."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_import_service import OFFICIAL_SOURCE, is_sale_transaction_csv, normalize_rows, read_csv_rows


INSERT_SQL = """
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
"""


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit manual-import command interface."""

    parser = argparse.ArgumentParser(description="手動匯入官方 PLVR 買賣實價登錄 ZIP/CSV")
    parser.add_argument("--input", required=True, type=Path, help="本機 PLVR ZIP 或 CSV；不會自動下載")
    parser.add_argument("--city", default="", help="城市提示或篩選，例如台北市")
    parser.add_argument("--district", default="", help="只匯入指定行政區")
    parser.add_argument("--road", default="", help="只匯入指定路段")
    parser.add_argument("--limit", type=int, default=None, help="最多接受筆數")
    parser.add_argument("--dry-run", action="store_true", help="只解析與品質檢查，不寫入資料庫")
    parser.add_argument("--replace-scope", action="store_true", help="匯入前刪除指定 city/district/road 範圍的官方資料")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a safe manual import without downloading external data."""

    args = build_parser().parse_args(argv)
    if not args.input.exists():
        print(f"找不到輸入檔案：{args.input}")
        return 1
    if args.replace_scope and not any((args.city, args.district, args.road)):
        print("--replace-scope 必須搭配至少一個 --city、--district 或 --road，避免清除過大範圍。")
        return 1
    files, temporary = _candidate_files(args.input)
    try:
        candidates = [path for path in files if is_sale_transaction_csv(path)]
        if not candidates:
            print("找不到可辨識的買賣實價登錄主檔；已排除 schema、manifest、預售與租賃資料。")
            return 1
        all_rows: list[dict[str, str]] = []
        file_report: list[dict[str, Any]] = []
        for path in candidates:
            rows, encoding = read_csv_rows(path)
            all_rows.extend(rows)
            file_report.append({"file": path.name, "encoding": encoding, "rows": len(rows)})
        normalized, report = normalize_rows(
            all_rows,
            city_hint=args.city,
            city_filter=args.city,
            district_filter=args.district,
            road_filter=args.road,
            limit=args.limit,
        )
        report.update({"status": "dry_run" if args.dry_run else "ready", "source": OFFICIAL_SOURCE, "files": file_report})
        if args.dry_run:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
        if not database_url:
            print("未設定 VALUATION_DATABASE_URL；可先加上 --dry-run 檢查資料，不會寫入資料庫。")
            return 0
        written = _write_rows(database_url, normalized, report, args)
        report.update({"status": "completed", "written_rows": written})
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"PLVR 匯入未完成：{type(error).__name__}。請檢查輸入格式、schema 與資料庫連線。")
        return 1
    finally:
        temporary.cleanup() if temporary else None


def _candidate_files(input_path: Path) -> tuple[list[Path], tempfile.TemporaryDirectory[str] | None]:
    if input_path.suffix.lower() == ".csv":
        return [input_path], None
    if input_path.suffix.lower() != ".zip":
        return [], None
    temporary = tempfile.TemporaryDirectory(prefix="plvr_import_")
    with zipfile.ZipFile(input_path) as archive:
        archive.extractall(temporary.name)
    return list(Path(temporary.name).rglob("*.csv")), temporary


def _write_rows(database_url: str, rows: list[dict[str, Any]], report: dict[str, Any], args: argparse.Namespace) -> int:
    import psycopg

    with psycopg.connect(database_url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            if args.replace_scope:
                clauses, params = ["source = %s"], [OFFICIAL_SOURCE]
                for field in ("city", "district", "road"):
                    value = getattr(args, field)
                    if value:
                        clauses.append(f"{field} = %s")
                        params.append(value)
                cursor.execute(f"delete from real_price_transactions where {' and '.join(clauses)}", params)
            if rows:
                cursor.executemany(INSERT_SQL, rows)
            cursor.execute(
                """
                insert into valuation_import_runs (source_name, source_period, record_count, status, note)
                values (%s, %s, %s, %s, %s)
                """,
                [
                    OFFICIAL_SOURCE,
                    ",".join(report.get("periods", [])),
                    len(rows),
                    "completed",
                    json.dumps({"files": report.get("files", []), "exclusions": report.get("exclusion_reasons", {})}, ensure_ascii=False),
                ],
            )
    return len(rows)


if __name__ == "__main__":
    raise SystemExit(main())
