"""Explicit release acceptance; no network access, retention or cutover."""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.import_plvr_to_postgres import CHUNK_UPSERT_SQL, STAGING_INSERT_SQL, _create_staging_table, _dedupe_batch, classify_import_readiness
from services.plvr_clean_shadow_rebuild import MANIFEST_SCHEMA_VERSION, build_artifact_requests, manifest_checksum, verify_artifact
from services.plvr_data_freshness import evaluate_plvr_freshness
from services.plvr_data_integrity import normalized_row_integrity_reason, taipei_as_of_date
from services.plvr_data_integrity import normalized_storage_key
from services.plvr_import_service import FILE_CITY_MAP, OFFICIAL_SOURCE, city_from_filename, normalize_rows, read_csv_rows


class UpdateBlocked(RuntimeError):
    def __init__(self, reason_code: str, *, exclusion_reasons: dict[str, int] | None = None):
        self.reason_code = reason_code
        self.exclusion_reasons = exclusion_reasons or {}
        super().__init__(reason_code)


@dataclass
class PreparedRelease:
    report: dict[str, Any]
    rows: list[dict[str, Any]]
    deadline: float


LEDGER_SQL = """create table if not exists plvr_update_releases (
    release_key text primary key, artifact_sha256 text not null, report_json text not null
)"""
STORAGE_FIELDS = (
    "transaction_period", "city", "district", "road", "address_text", "building_type",
    "area_ping", "building_age_years", "floor", "total_floor", "unit_price_per_ping",
    "total_price", "lat", "lng", "source", "raw_note", "dedupe_key",
)


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise UpdateBlocked("runtime_limit_exceeded")


def prepare_release(manifest_path: Path, artifact_id: str, *, cities: list[str], since: str,
    until: str, as_of: date | None = None, max_bytes: int = 256 * 1024 * 1024,
    max_rows: int = 100_000, max_seconds: int = 240) -> PreparedRelease:
    if not (1 <= max_bytes <= 512 * 1024 * 1024 and 1 <= max_rows <= 500_000 and 1 <= max_seconds <= 600):
        raise UpdateBlocked("resource_limit_invalid")
    deadline = time.monotonic() + max_seconds
    as_of = taipei_as_of_date(as_of)
    period = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
    cities = sorted({city.strip().replace("臺", "台") for city in cities})
    if not cities or set(cities) - set(FILE_CITY_MAP.values()):
        raise UpdateBlocked("city_scope_invalid")
    if not period.fullmatch(since) or not period.fullmatch(until) or since > until or until > as_of.strftime("%Y-%m"):
        raise UpdateBlocked("period_scope_invalid")
    if not manifest_path.is_file() or manifest_path.stat().st_size > 2 * 1024 * 1024:
        raise UpdateBlocked("artifact_manifest_invalid")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
            raise UpdateBlocked("artifact_manifest_invalid")
        if manifest.get("manifest_sha256") != manifest_checksum(manifest):
            raise UpdateBlocked("artifact_manifest_checksum_mismatch")
        entries = [entry for entry in manifest["artifacts"] if entry.get("artifact_id") == artifact_id]
        if len(entries) != 1:
            raise UpdateBlocked("artifact_identity_missing_or_ambiguous")
        entry = entries[0]
        kind, release = entry.get("kind"), str(entry.get("release") or "")
        options = {"season": {"seasons": [release]}, "history": {"histories": [release]}, "current": {"current_release": release}}
        request = build_artifact_requests(**options[kind])[0]
        if request.artifact_id != artifact_id or request.download_source != entry.get("download_source") or request.local_filename != entry.get("local_filename"):
            raise UpdateBlocked("source_identity_mismatch")
        if kind in {"current", "history"} and datetime.strptime(release, "%Y%m%d").date() > as_of:
            raise UpdateBlocked("source_release_in_future")
        if kind == "season":
            release_year, release_quarter = int(release[:3]) + 1911, int(release[-1])
            current_quarter = (as_of.month - 1) // 3 + 1
            if (release_year, release_quarter) > (as_of.year, current_quarter):
                raise UpdateBlocked("source_release_in_future")
        if entry.get("verification_status") != "VERIFIED" or not re.fullmatch(r"[a-fA-F0-9]{64}", str(entry.get("sha256") or "")):
            raise UpdateBlocked("artifact_not_verified")
        source = manifest_path.parent / request.local_filename
        if not source.is_file() or source.stat().st_size > max_bytes:
            raise UpdateBlocked("artifact_size_exceeded")
        # Bound decompression before the shared verifier calls ZipFile.testzip().
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            if len(infos) > 256 or sum(info.file_size for info in infos) > max_bytes * 2:
                raise UpdateBlocked("archive_expansion_limit_exceeded")
            for info in infos:
                member = PurePosixPath(info.filename.replace("\\", "/"))
                if member.is_absolute() or ".." in member.parts or info.flag_bits & 1:
                    raise UpdateBlocked("unsafe_zip_member")
        verified = verify_artifact(source, expected_sha256=entry["sha256"], allow_partial_city_scope=True)
        if verified["verification_status"] != "VERIFIED":
            raise UpdateBlocked(verified["reason_code"])
        covered = {city.replace("臺", "台") for city in verified["coverage_cities"]}
        if set(cities) - covered:
            raise UpdateBlocked("requested_city_members_missing")
        _check_deadline(deadline)
        raw: list[dict[str, str]] = []
        with tempfile.TemporaryDirectory(prefix="plvr_update_") as temp, zipfile.ZipFile(source) as archive:
            selected = [info for info in archive.infolist() if city_from_filename(Path(PurePosixPath(info.filename).name)) in cities]
            basenames = [PurePosixPath(info.filename).name.lower() for info in selected]
            if len(basenames) != len(set(basenames)):
                raise UpdateBlocked("duplicate_city_member")
            for info in selected:
                _check_deadline(deadline)
                target = Path(temp) / PurePosixPath(info.filename).name
                target.write_bytes(archive.read(info))
                file_rows, _ = read_csv_rows(target)
                if len(raw) + len(file_rows) > max_rows:
                    raise UpdateBlocked("row_limit_exceeded")
                for row in file_rows:
                    row["__plvr_city_hint"] = city_from_filename(target)
                raw.extend(file_rows)
        rows, quality = normalize_rows(raw, city_filters=cities, since=since, until=until, as_of=as_of)
        rows, duplicates, _ = _dedupe_batch(rows)
        filtered = sum(count for reason, count in quality["exclusion_reasons"].items() if reason.startswith("filtered_"))
        gate = classify_import_readiness({**quality, "read_rows": quality["read_rows"] - filtered,
            "excluded_rows": quality["excluded_rows"] - filtered, "accepted_rows": len(rows),
            "skipped_duplicate_rows": duplicates, "city_scope": cities, "is_dry_run": False})
        intentional_exclusions = {"non_building_transaction", "filtered_city", "filtered_district", "filtered_road", "filtered_before_since", "filtered_after_until"}
        unsafe = set(quality["exclusion_reasons"]) - intentional_exclusions
        invalid_metrics = sum(any(not math.isfinite(float(row[field])) or float(row[field]) <= 0 for field in ("area_ping", "total_price", "unit_price_per_ping")) for row in rows)
        if invalid_metrics:
            quality["exclusion_reasons"]["invalid_normalized_metric"] = invalid_metrics
            unsafe.add("invalid_normalized_metric")
        if gate["quality_status"] != "pass" or unsafe or any(normalized_row_integrity_reason(row, as_of=as_of) for row in rows):
            raise UpdateBlocked("release_acceptance_failed", exclusion_reasons=quality["exclusion_reasons"])
        _check_deadline(deadline)
    except UpdateBlocked:
        raise
    except Exception:
        raise UpdateBlocked("artifact_manifest_or_parse_invalid") from None
    checked = datetime.now(UTC)
    newest = max(row["transaction_period"] for row in rows)
    identity = json.dumps([artifact_id, cities, since, until], ensure_ascii=True, separators=(",", ":"))
    report = {"schema_version": "plvr-provider-update-v1", "capability": "plvr_update", "status": "dry_run",
        "reason_code": "release_acceptance_passed", "test_mode": "offline", "source": OFFICIAL_SOURCE,
        "artifact_id": artifact_id, "artifact_sha256": entry["sha256"].lower(),
        "manifest_sha256": manifest["manifest_sha256"], "source_release": release,
        "source_url": request.download_source, "coverage_cities": cities, "since": since, "until": until,
        "release_key": hashlib.sha256(identity.encode()).hexdigest(), "accepted_rows": len(rows),
        "read_rows": quality["read_rows"], "excluded_rows": quality["excluded_rows"],
        "filtered_rows": filtered, "quality_excluded_rows": quality["excluded_rows"] - filtered,
        "exclusion_reasons": quality["exclusion_reasons"],
        "batch_duplicate_rows": duplicates, "inserted_rows": 0, "newest_transaction_period": newest,
        "imported_at": None, "checked_at": checked.isoformat(), "retention_applied": False,
        "freshness": _freshness(len(rows), newest, None, checked, as_of)}
    return PreparedRelease(report, rows, deadline)


def _freshness(count: int, newest: str, imported: str | None, checked: datetime, as_of: date) -> dict[str, Any]:
    now = datetime.combine(as_of, checked.timetz())
    result = evaluate_plvr_freshness(official_records_count=count, latest_import_status="completed",
        last_updated=imported or now, newest_effective_period=newest, provider_available=True, now=now)
    if imported is None:
        result["latest_import_at"] = None
        result["latest_import_age_days"] = None
    result["basis"] = "accepted_import_and_transaction_period" if imported else "dry_run_transaction_period_projection"
    return result


def _completed(prepared: PreparedRelease, inserted: int) -> dict[str, Any]:
    report = dict(prepared.report)
    imported = datetime.now(UTC)
    report.update(status="completed", reason_code="release_accepted", imported_at=imported.isoformat(), inserted_rows=inserted)
    report["freshness"] = _freshness(len(prepared.rows), report["newest_transaction_period"], imported.isoformat(), imported, imported.date())
    return report


def _duplicate(prior: tuple, report: dict[str, Any]) -> dict[str, Any]:
    if prior[0] != report["artifact_sha256"]:
        raise UpdateBlocked("release_checksum_conflict")
    accepted = json.loads(prior[1])
    checked = datetime.now(UTC)
    accepted["freshness"] = _freshness(accepted["accepted_rows"], accepted["newest_transaction_period"], accepted["imported_at"], checked, checked.date())
    return {**accepted, "checked_at": checked.isoformat(), "status": "duplicate_release", "reason_code": "release_already_accepted", "inserted_rows": 0}


def import_release(prepared: PreparedRelease, *, fixture_db: Path | None = None, database_url: str | None = None) -> dict[str, Any]:
    _check_deadline(prepared.deadline)
    try:
        if fixture_db:
            return _import_fixture(prepared, fixture_db)
        if not database_url:
            raise UpdateBlocked("configuration_required")
        return _import_postgres(prepared, database_url)
    except UpdateBlocked:
        raise
    except Exception:
        raise UpdateBlocked("import_transaction_failed") from None


def _import_fixture(prepared: PreparedRelease, path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=5) as connection:
        connection.execute("begin immediate")
        connection.execute(LEDGER_SQL)
        connection.execute("create table if not exists real_price_transactions (" + ",".join(f"{field} {'real' if field in {'area_ping', 'total_price', 'unit_price_per_ping'} else 'text'}" for field in STORAGE_FIELDS) + ", unique(source, dedupe_key))")
        prior = connection.execute("select artifact_sha256, report_json from plvr_update_releases where release_key = ?", (prepared.report["release_key"],)).fetchone()
        if prior:
            return _duplicate(prior, prepared.report)
        inserted = 0
        def natural_key(row: dict[str, Any]) -> tuple:
            return tuple(normalized_storage_key(row[field]) for field in ("source", "city", "district", "transaction_period", "address_text", "road", "building_type")) + tuple(round(float(row[field]), 2) for field in ("area_ping", "total_price", "unit_price_per_ping"))
        existing = {natural_key(dict(zip(STORAGE_FIELDS, row))) for row in connection.execute("select " + ",".join(STORAGE_FIELDS) + " from real_price_transactions")}
        for row in prepared.rows:
            _check_deadline(prepared.deadline)
            key = natural_key(row)
            if key in existing:
                continue
            inserted += connection.execute("insert or ignore into real_price_transactions (" + ",".join(STORAGE_FIELDS) + ") values (" + ",".join("?" for _ in STORAGE_FIELDS) + ")", tuple(row[field] for field in STORAGE_FIELDS)).rowcount
            existing.add(key)
        report = _completed(prepared, inserted)
        report["test_mode"] = "fixture_import"
        connection.execute("insert into plvr_update_releases values (?, ?, ?)", (report["release_key"], report["artifact_sha256"], json.dumps(report)))
        _check_deadline(prepared.deadline)
        return report


def _import_postgres(prepared: PreparedRelease, database_url: str) -> dict[str, Any]:
    import psycopg
    with psycopg.connect(database_url, connect_timeout=10, prepare_threshold=None) as connection:
        with connection.cursor() as cursor:
            cursor.execute("set local statement_timeout = '30s'")
            cursor.execute("set local lock_timeout = '5s'")
            cursor.execute("select pg_try_advisory_xact_lock(730514081)")
            if not cursor.fetchone()[0]:
                raise UpdateBlocked("import_already_running")
            cursor.execute(LEDGER_SQL)
            cursor.execute("select artifact_sha256, report_json from plvr_update_releases where release_key = %s", (prepared.report["release_key"],))
            prior = cursor.fetchone()
            if prior:
                return _duplicate(prior, prepared.report)
            _create_staging_table(cursor)
            inserted = 0
            for start in range(0, len(prepared.rows), 200):
                _check_deadline(prepared.deadline)
                chunk = prepared.rows[start:start + 200]
                cursor.execute("truncate plvr_import_staging")
                cursor.executemany(STAGING_INSERT_SQL, chunk)
                cursor.execute(CHUNK_UPSERT_SQL)
                outcomes = cursor.fetchall()
                if sum(int(row[1]) + int(row[2]) + int(row[3]) for row in outcomes) != len(chunk):
                    raise UpdateBlocked("database_acceptance_count_mismatch")
                inserted += sum(int(row[1]) for row in outcomes)
            report = _completed(prepared, inserted)
            report["test_mode"] = "operator_import"
            cursor.execute("insert into plvr_update_releases values (%s, %s, %s)", (report["release_key"], report["artifact_sha256"], json.dumps(report)))
            cursor.execute("""insert into valuation_import_runs (source_name, source_period, record_count, city_scope, input_file_count, read_rows, accepted_rows, inserted_rows, skipped_duplicate_rows, excluded_rows, status, note)
                values (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, 'completed', %s)""",
                (OFFICIAL_SOURCE, report["newest_transaction_period"], len(prepared.rows), ",".join(report["coverage_cities"]), report["read_rows"], report["accepted_rows"], inserted, len(prepared.rows) - inserted + report["batch_duplicate_rows"], report["excluded_rows"], json.dumps({"release_key": report["release_key"], "source_release": report["source_release"], "artifact_sha256": report["artifact_sha256"]})))
            _check_deadline(prepared.deadline)
            return report
