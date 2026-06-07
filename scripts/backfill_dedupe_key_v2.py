"""Safely backfill PLVR dedupe_key v2 values in PostgreSQL.

The tool is dry-run by default. Existing official transaction rows do not keep
the original PLVR serial number, so keys are rebuilt with the importer shared
helper using only fields persisted in ``real_price_transactions``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_import_service import OFFICIAL_SOURCE, build_dedupe_key


@dataclass(frozen=True)
class BackfillCandidate:
    """One official row whose stored key differs from its rebuilt v2 key."""

    row_id: int
    old_key: str | None
    new_key: str
    city: str
    period: str


def parse_period(value: str) -> str:
    """Validate and normalize a YYYY-MM CLI period."""
    if not value:
        return ""
    parts = value.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise argparse.ArgumentTypeError("期間格式必須為 YYYY-MM")
    try:
        month = int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("期間格式必須為 YYYY-MM") from exc
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("月份必須介於 01 到 12")
    return value


def split_csv(value: str) -> list[str]:
    """Split and normalize comma-separated city filters."""
    return [normalize_city(item.strip()) for item in value.split(",") if item.strip()]


def normalize_city(value: str) -> str:
    """Use the same traditional-character city equivalence as the importer."""
    return value.replace("臺", "台").strip()


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(description="安全重建官方 PLVR dedupe_key v2（預設 dry-run）")
    parser.add_argument("--cities", default="", help='城市清單，例如 "台北市,新北市"')
    parser.add_argument("--since", type=parse_period, default="", help="起始交易期間 YYYY-MM")
    parser.add_argument("--until", type=parse_period, default="", help="結束交易期間 YYYY-MM")
    parser.add_argument("--limit", type=int, default=10000, help="最多掃描筆數，預設 10000")
    parser.add_argument("--chunk-size", type=int, default=200, help="更新 chunk 大小，預設 200")
    parser.add_argument("--dry-run", action="store_true", help="只產生報告，不更新資料")
    parser.add_argument("--confirm-update", action="store_true", help="明確允許更新 dedupe_key")
    return parser


def make_report(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], list[BackfillCandidate]]:
    """Build a dry-run report and safe update candidate list."""
    official_rows = [row for row in rows if row.get("source") == OFFICIAL_SOURCE]
    rows_by_city: Counter[str] = Counter()
    rows_by_period: Counter[str] = Counter()
    new_key_counts: Counter[str] = Counter()
    candidates: list[BackfillCandidate] = []
    already_v2 = 0

    rebuilt: list[tuple[dict[str, Any], str]] = []
    for row in official_rows:
        city = normalize_city(str(row.get("city") or ""))
        period = str(row.get("transaction_period") or "")
        rows_by_city[city] += 1
        rows_by_period[period] += 1
        normalized_row = {**row, "city": city, "source": OFFICIAL_SOURCE}
        new_key = build_dedupe_key(normalized_row)
        rebuilt.append((normalized_row, new_key))
        new_key_counts[new_key] += 1

    duplicate_keys = {key for key, count in new_key_counts.items() if count > 1}
    samples: list[dict[str, Any]] = []
    collision_rows = 0
    for row, new_key in rebuilt:
        raw_old_key = row.get("dedupe_key")
        old_key = str(raw_old_key) if raw_old_key is not None else None
        if old_key == new_key:
            already_v2 += 1
            continue
        if len(samples) < 5:
            samples.append(
                {
                    "id": row.get("id"),
                    "city": row.get("city"),
                    "period": row.get("transaction_period"),
                    "old_key": old_key or "",
                    "new_key": new_key,
                }
            )
        if new_key in duplicate_keys:
            collision_rows += 1
            continue
        candidates.append(
            BackfillCandidate(
                row_id=int(row["id"]),
                old_key=old_key,
                new_key=new_key,
                city=str(row.get("city") or ""),
                period=str(row.get("transaction_period") or ""),
            )
        )

    report = {
        "rows_scanned": len(official_rows),
        "rows_needing_update": len(official_rows) - already_v2,
        "rows_already_v2": already_v2,
        "updated_rows": 0,
        "potential_duplicate_groups_after_v2": len(duplicate_keys),
        "rows_skipped_due_to_potential_duplicates": collision_rows,
        "rows_by_city": dict(sorted(rows_by_city.items())),
        "rows_by_period": dict(sorted(rows_by_period.items())),
        "sample_old_new_keys": samples,
        "status": "dry_run",
        "key_reconstruction_note": (
            "既有資料未保存官方編號；本工具使用 importer 共用的 dedupe_key v2 "
            "函式與資料表現有欄位重建，可能撞 key 的群組不會更新。"
        ),
    }
    return report, candidates


def _where_clause(cities: list[str], since: str, until: str) -> tuple[str, list[Any]]:
    """Build the official-only query scope."""
    clauses = ["source = %s"]
    params: list[Any] = [OFFICIAL_SOURCE]
    if cities:
        clauses.append("replace(city, '臺', '台') = any(%s)")
        params.append(cities)
    if since:
        clauses.append("transaction_period >= %s")
        params.append(since)
    if until:
        clauses.append("transaction_period <= %s")
        params.append(until)
    return " and ".join(clauses), params


def run_backfill(
    database_url: str,
    *,
    cities: list[str],
    since: str,
    until: str,
    limit: int,
    chunk_size: int,
    will_update: bool,
) -> dict[str, Any]:
    """Scan official rows and optionally update collision-free keys in chunks."""
    import psycopg
    from psycopg.rows import dict_row

    where_sql, params = _where_clause(cities, since, until)
    select_sql = f"""
        select id, transaction_period, city, district, address_text, building_type,
               area_ping, total_price, unit_price_per_ping, source, dedupe_key
        from real_price_transactions
        where {where_sql}
        order by id
        limit %s
    """
    params.append(limit)

    with psycopg.connect(
        database_url,
        connect_timeout=10,
        prepare_threshold=None,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(select_sql, params)
            rows = list(cursor.fetchall())

        report, candidates = make_report(rows)
        if not will_update:
            return report

        # A key already owned by another official row is unsafe to update.
        safe_candidates: list[BackfillCandidate] = []
        existing_conflicts = 0
        for start in range(0, len(candidates), chunk_size):
            chunk = candidates[start : start + chunk_size]
            keys = [candidate.new_key for candidate in chunk]
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select dedupe_key
                    from real_price_transactions
                    where source = %s and dedupe_key = any(%s)
                    """,
                    (OFFICIAL_SOURCE, keys),
                )
                existing_keys = {str(row["dedupe_key"]) for row in cursor.fetchall()}
            existing_conflicts += len([candidate for candidate in chunk if candidate.new_key in existing_keys])
            safe_candidates.extend(candidate for candidate in chunk if candidate.new_key not in existing_keys)

        updated = 0
        for start in range(0, len(safe_candidates), chunk_size):
            chunk = safe_candidates[start : start + chunk_size]
            end = start + len(chunk)
            print(f"Updating rows {start + 1}-{end} / {len(safe_candidates)}...", flush=True)
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.executemany(
                        """
                        update real_price_transactions
                        set dedupe_key = %s
                        where id = %s and source = %s and dedupe_key is not distinct from %s
                        """,
                        [
                            (candidate.new_key, candidate.row_id, OFFICIAL_SOURCE, candidate.old_key)
                            for candidate in chunk
                        ],
                    )
                    updated += cursor.rowcount if cursor.rowcount >= 0 else len(chunk)

        report["updated_rows"] = updated
        report["rows_skipped_due_to_existing_v2_key"] = existing_conflicts
        report["status"] = "completed"
        return report


def main(argv: list[str] | None = None) -> int:
    """Run the CLI safely; dry-run wins over confirm-update."""
    args = build_parser().parse_args(argv)
    if args.limit <= 0 or args.chunk_size <= 0:
        print("limit 與 chunk-size 必須大於 0。")
        return 2
    if args.since and args.until and args.since > args.until:
        print("since 不可晚於 until。")
        return 2

    database_url = os.getenv("VALUATION_DATABASE_URL", "").strip()
    if not database_url:
        print("未設定 VALUATION_DATABASE_URL；未掃描或更新任何資料。")
        return 0

    will_update = bool(args.confirm_update and not args.dry_run)
    report = run_backfill(
        database_url,
        cities=split_csv(args.cities),
        since=args.since,
        until=args.until,
        limit=args.limit,
        chunk_size=args.chunk_size,
        will_update=will_update,
    )
    if args.confirm_update and args.dry_run:
        report["status"] = "dry_run"
        report["warning"] = "--dry-run 與 --confirm-update 同時提供，已依安全規則維持 dry-run。"
    elif not args.confirm_update:
        report["status"] = "dry_run"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
