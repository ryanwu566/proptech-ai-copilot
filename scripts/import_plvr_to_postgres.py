"""Safely normalize one or more supplied PLVR ZIP/CSV files into Postgres."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_import_service import OFFICIAL_SOURCE, build_dedupe_key, city_from_filename, is_sale_transaction_csv, normalize_rows, read_csv_rows


STAGING_INSERT_SQL = """
insert into plvr_import_staging (
    transaction_period, city, district, road, address_text, building_type,
    area_ping, building_age_years, floor, total_floor, unit_price_per_ping,
    total_price, lat, lng, source, raw_note, dedupe_key
) values (
    %(transaction_period)s, %(city)s, %(district)s, %(road)s, %(address_text)s,
    %(building_type)s, %(area_ping)s, %(building_age_years)s, %(floor)s,
    %(total_floor)s, %(unit_price_per_ping)s, %(total_price)s, %(lat)s, %(lng)s,
    %(source)s, %(raw_note)s, %(dedupe_key)s
)
"""

CHUNK_UPSERT_SQL = """
with inserted as (
    insert into real_price_transactions (
        transaction_period, city, district, road, address_text, building_type,
        area_ping, building_age_years, floor, total_floor, unit_price_per_ping,
        total_price, lat, lng, source, raw_note, dedupe_key
    )
    select transaction_period, city, district, road, address_text, building_type,
           area_ping, building_age_years, floor, total_floor, unit_price_per_ping,
           total_price, lat, lng, source, raw_note, dedupe_key
    from plvr_import_staging
    on conflict (source, dedupe_key) where dedupe_key is not null do nothing
    returning city
)
select city, count(*) as inserted_rows from inserted group by city order by city
"""


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit, guarded manual-import command interface."""

    parser = argparse.ArgumentParser(description="安全匯入官方 PLVR 買賣實價登錄 ZIP、CSV 或資料夾")
    parser.add_argument("--input", required=True, type=Path, help="本機 PLVR ZIP、CSV 或資料夾；不會自動下載")
    parser.add_argument("--city", default="", help="單一城市篩選，例如台北市")
    parser.add_argument("--cities", default="", help="多城市篩選，以逗號分隔")
    parser.add_argument("--district", default="", help="單一行政區篩選")
    parser.add_argument("--districts", default="", help="多行政區篩選，以逗號分隔")
    parser.add_argument("--road", default="", help="只匯入指定路段")
    parser.add_argument("--since", default="", help="最早交易期間，格式 YYYY-MM")
    parser.add_argument("--until", default="", help="最晚交易期間，格式 YYYY-MM")
    parser.add_argument("--limit", type=int, default=None, help="最多接受筆數")
    parser.add_argument("--dry-run", action="store_true", help="只解析與品質檢查，不寫入資料庫")
    parser.add_argument("--replace-scope", action="store_true", help="匯入前刪除指定範圍的官方資料")
    parser.add_argument("--confirm-large-import", action="store_true", help="確認接受超過 10,000 筆的匯入")
    parser.add_argument("--chunk-size", type=int, default=200, help="每批寫入筆數，預設 200")
    parser.add_argument("--progress-every", type=int, default=100, help="至少每處理指定筆數顯示進度，預設 100")
    parser.add_argument("--statement-timeout", type=int, default=30, help="每個資料庫 statement timeout 秒數，預設 30")
    parser.add_argument("--max-write-rows", type=int, default=None, help="正式匯入最多寫入筆數，方便小範圍驗證")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a safe manual import without downloading external data."""

    args = build_parser().parse_args(argv)
    if not args.input.exists():
        print(f"找不到輸入檔案：{args.input}")
        return 1
    if not _valid_period(args.since) or not _valid_period(args.until):
        print("--since / --until 必須使用 YYYY-MM 格式。")
        return 1
    if args.chunk_size < 1 or args.progress_every < 1 or args.statement_timeout < 1:
        print("--chunk-size、--progress-every 與 --statement-timeout 必須大於 0。")
        return 1

    city_filters = _scope_values(args.city, args.cities)
    district_filters = _scope_values(args.district, args.districts)
    if args.input.is_dir() and not city_filters:
        print("資料夾批次匯入必須指定 --city 或 --cities，避免誤匯全台多年資料。")
        return 1
    if not city_filters:
        print("警告：未指定城市範圍；正式匯入前請使用 --city 或 --cities。")
        if not args.dry_run:
            return 1
    if args.replace_scope and not any((city_filters, district_filters, args.road)):
        print("--replace-scope 必須搭配城市、行政區或路段範圍，避免清除過大範圍。")
        return 1

    files, temporary_dirs = _candidate_files(args.input)
    try:
        candidates = sorted((path for path in files if is_sale_transaction_csv(path)), key=lambda path: str(path).lower())
        if not candidates:
            print("找不到可辨識的買賣實價登錄主檔；已排除 schema、manifest、預售與租賃資料。")
            return 1

        all_rows: list[dict[str, str]] = []
        file_report: list[dict[str, Any]] = []
        for path in candidates:
            rows, encoding = read_csv_rows(path)
            inferred_city = city_from_filename(path) or (city_filters[0] if len(city_filters) == 1 else "")
            for row in rows:
                row["__plvr_city_hint"] = inferred_city
            all_rows.extend(rows)
            file_report.append({"file": path.name, "encoding": encoding, "rows": len(rows), "city_hint": inferred_city})

        normalized, report = normalize_rows(
            all_rows,
            city_hint=city_filters[0] if len(city_filters) == 1 else "",
            city_filters=city_filters,
            district_filters=district_filters,
            road_filter=args.road,
            since=args.since,
            until=args.until,
            limit=args.limit,
        )
        normalized, batch_duplicates, batch_duplicates_by_city = _dedupe_batch(normalized)
        report["accepted_rows"] = len(normalized)
        report["accepted_rows_by_city"] = _city_counts(normalized)
        report["skipped_duplicate_rows"] = batch_duplicates
        report["skipped_duplicate_rows_by_city"] = batch_duplicates_by_city
        report.update(
            {
                "inserted_rows": 0,
                "inserted_rows_by_city": {},
                "updated_rows": 0,
                "source_periods": report.pop("periods", []),
                "source": OFFICIAL_SOURCE,
                "files": file_report,
                "files_processed": len(file_report),
                "city_scope": city_filters,
                "district_scope": district_filters,
                "road_scope": args.road,
                "current_db_records_before": None,
                "current_db_records_after": None,
                "estimated_growth": len(normalized),
                "status": "dry_run" if args.dry_run else "ready",
            }
        )

        if len(normalized) > 10_000 and not args.confirm_large_import:
            report["status"] = "blocked_large_import"
            print(json.dumps(report, ensure_ascii=False, indent=2))
            print("本次 accepted_rows 超過 10,000；請縮小範圍，或確認後加上 --confirm-large-import。")
            return 1
        if args.dry_run:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
        if not database_url:
            print("未設定 VALUATION_DATABASE_URL；可先加上 --dry-run 檢查資料，不會寫入資料庫。")
            return 0
        write_rows = normalized[: args.max_write_rows] if args.max_write_rows is not None else normalized
        report["write_rows"] = len(write_rows)
        write_report = _write_rows(database_url, write_rows, report, args, city_filters, district_filters)
        report.update(write_report)
        report["status"] = "completed"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"PLVR 匯入未完成：{type(error).__name__}。請檢查 migration、輸入格式與資料庫連線。")
        return 1
    finally:
        for temporary in temporary_dirs:
            temporary.cleanup()


def _candidate_files(input_path: Path) -> tuple[list[Path], list[tempfile.TemporaryDirectory[str]]]:
    """Expand a CSV, ZIP, or recursively scanned folder into candidate CSV files."""

    inputs = (
        sorted(
            (path for path in input_path.rglob("*") if path.is_file() and path.suffix.lower() in {".csv", ".zip"}),
            key=lambda path: str(path).lower(),
        )
        if input_path.is_dir()
        else [input_path]
    )
    files: list[Path] = []
    temporary_dirs: list[tempfile.TemporaryDirectory[str]] = []
    for source in inputs:
        if source.suffix.lower() == ".csv":
            files.append(source)
        elif source.suffix.lower() == ".zip":
            temporary = tempfile.TemporaryDirectory(prefix="plvr_import_")
            temporary_dirs.append(temporary)
            with zipfile.ZipFile(source) as archive:
                archive.extractall(temporary.name)
            files.extend(Path(temporary.name).rglob("*.csv"))
    return files, temporary_dirs


def _dedupe_batch(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates_by_city: Counter[str] = Counter()
    for row in rows:
        key = str(row["dedupe_key"])
        if key in seen:
            duplicates_by_city[str(row.get("city", ""))] += 1
            continue
        seen.add(key)
        unique.append(row)
    return unique, len(rows) - len(unique), dict(sorted(duplicates_by_city.items()))


def _city_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count normalized rows per city for transparent import reports."""

    return dict(sorted(Counter(str(row.get("city", "")) for row in rows).items()))


def _write_rows(
    database_url: str,
    rows: list[dict[str, Any]],
    report: dict[str, Any],
    args: argparse.Namespace,
    city_filters: list[str],
    district_filters: list[str],
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(
        database_url,
        connect_timeout=10,
        prepare_threshold=None,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"set statement_timeout = '{int(args.statement_timeout)}s'")
            before = _database_counts(cursor)
            if args.replace_scope:
                clauses, params = ["source = %s"], [OFFICIAL_SOURCE]
                if city_filters:
                    clauses.append("replace(city, '臺', '台') = any(%s)")
                    params.append([item.replace("臺", "台") for item in city_filters])
                if district_filters:
                    clauses.append("district = any(%s)")
                    params.append(district_filters)
                if args.road:
                    clauses.append("road = %s")
                    params.append(args.road)
                cursor.execute(f"delete from real_price_transactions where {' and '.join(clauses)}", params)

            backfilled = _backfill_scope_dedupe(cursor, city_filters, district_filters, args.road)
            cursor.execute(
                """
                create temporary table if not exists plvr_import_staging (
                    transaction_period varchar(7), city text, district text, road text,
                    address_text text, building_type text, area_ping numeric(12, 2),
                    building_age_years numeric(8, 2), floor integer, total_floor integer,
                    unit_price_per_ping numeric(14, 2), total_price numeric(16, 2),
                    lat double precision, lng double precision, source text, raw_note text,
                    dedupe_key text
                ) on commit preserve rows
                """
            )
            connection.commit()
            inserted = 0
            inserted_by_city: Counter[str] = Counter()
            skipped = int(report.get("skipped_duplicate_rows", 0))
            skipped_by_city: Counter[str] = Counter(report.get("skipped_duplicate_rows_by_city", {}))
            processed = 0
            print(
                f"Starting batch write: total={len(rows)}, chunk_size={args.chunk_size}, "
                f"progress_every={args.progress_every}, statement_timeout={args.statement_timeout}s",
                flush=True,
            )
            for chunk_index, chunk in enumerate(_chunks(rows, args.chunk_size), start=1):
                start = processed + 1
                end = processed + len(chunk)
                try:
                    with connection.transaction():
                        cursor.execute("truncate table plvr_import_staging")
                        cursor.executemany(STAGING_INSERT_SQL, chunk)
                        cursor.execute(CHUNK_UPSERT_SQL)
                        inserted_rows = cursor.fetchall()
                        chunk_inserted_by_city = Counter(
                            {str(row["city"]): int(row["inserted_rows"]) for row in inserted_rows}
                        )
                        chunk_inserted = sum(chunk_inserted_by_city.values())
                    inserted += chunk_inserted
                    inserted_by_city.update(chunk_inserted_by_city)
                    skipped += len(chunk) - chunk_inserted
                    chunk_by_city = Counter(str(row.get("city", "")) for row in chunk)
                    skipped_by_city.update(chunk_by_city - chunk_inserted_by_city)
                    processed = end
                    print(
                        f"Writing rows {start}-{end} / {len(rows)}... "
                        f"inserted={inserted}, updated={backfilled}, skipped_duplicate={skipped}",
                        flush=True,
                    )
                except Exception as error:
                    safe_reason = _safe_error_reason(error)
                    print(
                        f"Chunk {chunk_index} failed at rows {start}-{end} / {len(rows)}: "
                        f"{type(error).__name__}: {safe_reason}. This chunk was rolled back.",
                        flush=True,
                    )
                    raise
            after = _database_counts(cursor)
            run_values = {
                "source_name": OFFICIAL_SOURCE,
                "source_period": ",".join(report.get("source_periods", [])),
                "record_count": inserted,
                "city_scope": ",".join(city_filters),
                "district_scope": ",".join(district_filters),
                "road_scope": args.road,
                "input_file_count": report.get("files_processed", 0),
                "read_rows": report.get("read_rows", 0),
                "accepted_rows": report.get("accepted_rows", 0),
                "inserted_rows": inserted,
                "updated_rows": backfilled,
                "skipped_duplicate_rows": skipped,
                "excluded_rows": report.get("excluded_rows", 0),
                "status": "completed",
                "note": json.dumps({"files": report.get("files", []), "exclusions": report.get("exclusion_reasons", {})}, ensure_ascii=False),
            }
            cursor.execute(
                """
                insert into valuation_import_runs (
                    source_name, source_period, record_count, city_scope, district_scope, road_scope,
                    input_file_count, read_rows, accepted_rows, inserted_rows, updated_rows,
                    skipped_duplicate_rows, excluded_rows, status, note
                ) values (
                    %(source_name)s, %(source_period)s, %(record_count)s, %(city_scope)s, %(district_scope)s,
                    %(road_scope)s, %(input_file_count)s, %(read_rows)s, %(accepted_rows)s, %(inserted_rows)s,
                    %(updated_rows)s, %(skipped_duplicate_rows)s, %(excluded_rows)s, %(status)s, %(note)s
                )
                """,
                run_values,
            )
    return {
        "inserted_rows": inserted,
        "inserted_rows_by_city": dict(sorted(inserted_by_city.items())),
        "updated_rows": backfilled,
        "skipped_duplicate_rows": skipped,
        "skipped_duplicate_rows_by_city": dict(sorted(skipped_by_city.items())),
        "current_db_records_before": before["records_count"],
        "current_db_records_after": after["records_count"],
        "current_db_official_before": before["official_records_count"],
        "current_db_official_after": after["official_records_count"],
        "estimated_growth": inserted,
    }


def _database_counts(cursor: Any) -> dict[str, int]:
    cursor.execute(
        """
        select count(*) as records_count,
               count(*) filter (where source = 'official_plvr_opendata') as official_records_count
        from real_price_transactions
        """
    )
    row = cursor.fetchone()
    if isinstance(row, dict):
        return {key: int(row.get(key) or 0) for key in ("records_count", "official_records_count")}
    return {"records_count": int(row[0] or 0), "official_records_count": int(row[1] or 0)}


def _backfill_scope_dedupe(cursor: Any, city_filters: list[str], district_filters: list[str], road: str) -> int:
    """Backfill one stable key per existing official transaction without deleting duplicates."""

    clauses, params = ["source = %s", "dedupe_key is null"], [OFFICIAL_SOURCE]
    if city_filters:
        clauses.append("replace(city, '臺', '台') = any(%s)")
        params.append([item.replace("臺", "台") for item in city_filters])
    if district_filters:
        clauses.append("district = any(%s)")
        params.append(district_filters)
    if road:
        clauses.append("road = %s")
        params.append(road)
    cursor.execute(
        f"""
        select id, source, city, district, address_text, transaction_period,
               building_type, area_ping, total_price, unit_price_per_ping
        from real_price_transactions
        where {' and '.join(clauses)}
        order by id
        """,
        params,
    )
    seen: set[str] = set()
    updated = 0
    for row in cursor.fetchall():
        item = dict(row)
        key = build_dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        cursor.execute("update real_price_transactions set dedupe_key = %s where id = %s", [key, item["id"]])
        updated += 1
    return updated


def _chunks(rows: list[dict[str, Any]], size: int):
    """Yield stable write chunks without copying the full import again."""

    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _safe_error_reason(error: Exception) -> str:
    """Return a concise database error without connection details."""

    message = " ".join(str(error).split())
    return message[:240] if message else "database statement failed"


def _scope_values(single: str, multiple: str) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in [single, *multiple.split(",")] if item.strip()))


def _valid_period(value: str) -> bool:
    return not value or bool(re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value))


if __name__ == "__main__":
    raise SystemExit(main())
