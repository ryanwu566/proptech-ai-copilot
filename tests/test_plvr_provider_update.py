"""Run the real operator command against local artifacts and disposable SQLite."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path
from urllib.parse import quote, urlparse

import pytest

from services.plvr_clean_shadow_rebuild import build_artifact_requests, manifest_checksum


ROOT = Path(__file__).resolve().parents[1]
HEADERS = ["鄉鎮市區", "交易標的", "土地位置建物門牌", "交易年月日", "建物移轉總面積平方公尺", "總價元", "編號"]


def artifact(tmp_path, *, release="20261001", dates=("1150901",), extra=None, first_row_override=None, kind="current"):
    options = {"current": {"current_release": release}, "season": {"seasons": [release]}}
    request = build_artifact_requests(**options[kind])[0]
    source = tmp_path / request.local_filename
    content = io.StringIO(newline="")
    writer = csv.writer(content)
    writer.writerow(HEADERS)
    for index, value in enumerate(dates):
        row = ["大安區", "房地(土地+建物)", f"台北市大安區測試路{index + 1}號", value, "100", "20000000", f"id-{index}"]
        if index == 0 and first_row_override:
            row[first_row_override[0]] = first_row_override[1]
        writer.writerow(row)
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("a_lvr_land_a.csv", content.getvalue().encode("utf-8-sig"))
        archive.writestr("manifest.csv", "name,schema\na_lvr_land_a.csv,schema-main.csv\n")
        archive.writestr("schema-main.csv", "name,description\n")
        if extra:
            archive.writestr(*extra)
    entry = {
        "artifact_id": request.artifact_id, "kind": request.kind, "release": request.release,
        "download_source": request.download_source, "local_filename": source.name,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_status": "PARTIAL_AUTHORITATIVE", "verification_status": "VERIFIED",
    }
    manifest = {"schema_version": "plvr-authoritative-artifact-manifest-v1", "artifacts": [entry]}
    manifest["manifest_sha256"] = manifest_checksum(manifest)
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, request.artifact_id, source


def run_update(manifest, artifact_id, *args, env=None):
    process_env = dict(os.environ)
    for key in ("VALUATION_DATABASE_URL", "PLVR_UPDATE_DATABASE_URL", "PLVR_UPDATE_ENVIRONMENT"):
        process_env.pop(key, None)
    process_env.update(env or {})
    process_env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/update_valuation_data.py"), "--manifest", str(manifest),
         "--artifact-id", artifact_id, "--city", "台北市", "--since", "2023-11", "--until", "2026-10", "--as-of-date", "2026-10-08", *args],
        cwd=ROOT, env=process_env, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )


def test_dry_run_verifies_parses_and_preserves_three_freshness_fields(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path, dates=("1140101",))
    result = run_update(manifest, artifact_id, "--dry-run")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "dry_run"
    assert report["accepted_rows"] == 1
    assert report["source_release"] == "20261001"
    assert report["newest_transaction_period"] == "2025-01"
    assert report["imported_at"] is None
    assert report["freshness"]["freshness_status"] == "stale"
    assert report["retention_applied"] is False
    assert not list(tmp_path.glob("*.sqlite"))


def test_fixture_import_and_duplicate_release_do_not_refresh_acceptance_time(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path)
    database = tmp_path / "fixture.sqlite"
    first = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert first.returncode == 0, first.stderr
    second = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert second.returncode == 0, second.stderr
    a, b = json.loads(first.stdout), json.loads(second.stdout)
    assert a["status"] == "completed"
    assert b["status"] == "duplicate_release"
    assert a["imported_at"] == b["imported_at"]
    with sqlite3.connect(database) as connection:
        assert connection.execute("select count(*) from real_price_transactions").fetchone()[0] == 1
        assert connection.execute("select count(*) from plvr_update_releases").fetchone()[0] == 1


@pytest.mark.parametrize("dates", [("1150901", "9990101"), ("invalid",), ("1151101",)])
def test_failed_acceptance_cannot_write_or_accept_any_rows(tmp_path, dates):
    manifest, artifact_id, _ = artifact(tmp_path, dates=dates)
    database = tmp_path / "fixture.sqlite"
    result = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "blocked"
    assert not database.exists()


def test_acceptance_ledger_failure_rolls_back_transaction_rows(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path)
    database = tmp_path / "fixture.sqlite"
    initial = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert initial.returncode == 0, initial.stderr
    with sqlite3.connect(database) as connection:
        connection.execute("create trigger reject_acceptance before insert on plvr_update_releases begin select raise(abort, 'failure'); end")
    manifest, artifact_id, _ = artifact(tmp_path, release="20261008", dates=("1150801",))
    failed = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert failed.returncode == 2
    assert json.loads(failed.stdout)["reason_code"] == "import_transaction_failed"
    with sqlite3.connect(database) as connection:
        assert connection.execute("select count(*) from real_price_transactions").fetchone()[0] == 1
        assert connection.execute("select count(*) from plvr_update_releases").fetchone()[0] == 1


def test_release_identity_cannot_silently_change_checksum(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path)
    database = tmp_path / "fixture.sqlite"
    assert run_update(manifest, artifact_id, "--import", "--fixture-db", str(database)).returncode == 0
    manifest, artifact_id, _ = artifact(tmp_path, dates=("1150801",))
    result = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason_code"] == "release_checksum_conflict"


@pytest.mark.parametrize("change, reason", [("archive", "artifact_sha256_mismatch"), ("manifest", "artifact_manifest_checksum_mismatch"), ("url", "source_identity_mismatch")])
def test_provenance_tampering_is_rejected_before_import(tmp_path, change, reason):
    manifest, artifact_id, source = artifact(tmp_path)
    if change == "archive":
        source.write_bytes(source.read_bytes() + b"tampered")
    else:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["artifacts"][0]["download_source"] = "https://example.invalid/untrusted.zip"
        if change == "url":
            data["manifest_sha256"] = manifest_checksum(data)
        manifest.write_text(json.dumps(data), encoding="utf-8")
    result = run_update(manifest, artifact_id, "--dry-run")
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason_code"] == reason


def test_import_preserves_old_rows_and_requires_separate_retention(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path, dates=("1150101",))
    database = tmp_path / "fixture.sqlite"
    assert run_update(manifest, artifact_id, "--import", "--fixture-db", str(database)).returncode == 0
    with sqlite3.connect(database) as connection:
        connection.execute("update real_price_transactions set transaction_period = '2020-01'")
    manifest, artifact_id, _ = artifact(tmp_path, release="20261008", dates=("1150901",))
    result = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert result.returncode == 0
    assert json.loads(result.stdout)["retention_applied"] is False
    with sqlite3.connect(database) as connection:
        assert connection.execute("select count(*) from real_price_transactions where transaction_period = '2020-01'").fetchone()[0] == 1


def test_production_import_requires_explicit_environment_and_never_prints_credentials(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path)
    secret = "postgresql://private:do-not-print@localhost/private"
    result = run_update(manifest, artifact_id, "--import", env={"PLVR_UPDATE_DATABASE_URL": secret})
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason_code"] == "configuration_required"
    assert secret not in result.stdout + result.stderr


def test_dry_run_never_connects_even_if_production_credentials_exist(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path)
    result = run_update(manifest, artifact_id, "--dry-run", env={"PLVR_UPDATE_DATABASE_URL": "invalid-secret", "PLVR_UPDATE_ENVIRONMENT": "production-market-import"})
    assert result.returncode == 0, result.stderr
    assert "invalid-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("args, reason", [(('--max-rows', '1'), 'row_limit_exceeded'), (('--max-bytes', '10'), 'artifact_size_exceeded')])
def test_resource_limits_block_whole_release_without_truncating(tmp_path, args, reason):
    manifest, artifact_id, _ = artifact(tmp_path, dates=("1150901", "1150902"))
    result = run_update(manifest, artifact_id, "--dry-run", *args)
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason_code"] == reason


def test_unsafe_archive_member_is_rejected(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path, extra=("../escape.csv", "content"))
    result = run_update(manifest, artifact_id, "--dry-run")
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason_code"] == "unsafe_zip_member"


@pytest.mark.parametrize("release,as_of,until", [("999S4", "2026-10-08", "2026-10"), ("115S4", "2026-08-08", "2026-08")])
def test_future_seasonal_release_cannot_label_valid_transaction_rows(tmp_path, release, as_of, until):
    manifest, artifact_id, _ = artifact(tmp_path, release=release, kind="season", dates=("1150701",))
    result = run_update(manifest, artifact_id, "--dry-run", "--as-of-date", as_of, "--until", until)
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason_code"] == "source_release_in_future"


@pytest.mark.parametrize("release", ["114S4", "115S4"])
def test_historical_and_current_quarter_seasonal_identity_preserved(tmp_path, release):
    manifest, artifact_id, _ = artifact(tmp_path, release=release, kind="season")
    result = run_update(manifest, artifact_id, "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["source_release"] == release


def test_transaction_window_filtering_has_separate_audit_count(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path, dates=("1090101", "1150901"))
    result = run_update(manifest, artifact_id, "--dry-run")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["read_rows"] == 2
    assert report["accepted_rows"] == 1
    assert report.get("filtered_rows") == 1
    assert report.get("quality_excluded_rows") == 0


@pytest.mark.parametrize("column,value,reason", [(4, "0", "invalid_area"), (5, "0", "invalid_total_price"), (5, "99999999999", "abnormal_unit_price"), (0, "", "missing_location"), (4, "nan", "invalid_normalized_metric")])
def test_one_corrupt_building_row_blocks_whole_scope_even_below_warning_threshold(tmp_path, column, value, reason):
    manifest, artifact_id, _ = artifact(tmp_path, dates=("1150901",) * 5, first_row_override=(column, value))
    database = tmp_path / "fixture.sqlite"
    result = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["reason_code"] == "release_acceptance_failed"
    assert report.get("exclusion_reasons", {}).get(reason) == 1
    assert not database.exists()


def test_intentional_nonbuilding_exclusion_retains_accepted_building_rows(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path, dates=("1150901",) * 5, first_row_override=(1, "土地"))
    result = run_update(manifest, artifact_id, "--dry-run")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["accepted_rows"] == 4
    assert report["exclusion_reasons"] == {"non_building_transaction": 1}


def test_duplicate_release_freshness_is_recomputed_without_touching_import_time(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path)
    database = tmp_path / "fixture.sqlite"
    initial = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert initial.returncode == 0, initial.stderr
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("select report_json from plvr_update_releases").fetchone()[0])
        payload["imported_at"] = "2020-01-01T00:00:00+00:00"
        connection.execute("update plvr_update_releases set report_json = ?", (json.dumps(payload),))
    duplicate = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert duplicate.returncode == 0, duplicate.stderr
    report = json.loads(duplicate.stdout)
    assert report["imported_at"] == "2020-01-01T00:00:00+00:00"
    assert report["freshness"]["freshness_status"] == "stale"


def test_fixture_natural_duplicate_guard_matches_importer_when_official_id_changes(tmp_path):
    manifest, artifact_id, _ = artifact(tmp_path)
    database = tmp_path / "fixture.sqlite"
    assert run_update(manifest, artifact_id, "--import", "--fixture-db", str(database)).returncode == 0
    manifest, artifact_id, source = artifact(tmp_path, release="20261008")
    with zipfile.ZipFile(source) as archive:
        members = {info.filename: archive.read(info) for info in archive.infolist()}
    members["a_lvr_land_a.csv"] = members["a_lvr_land_a.csv"].replace(b"id-0", b"new-official-id")
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    payload["manifest_sha256"] = manifest_checksum(payload)
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = run_update(manifest, artifact_id, "--import", "--fixture-db", str(database))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["inserted_rows"] == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("select count(*) from real_price_transactions").fetchone()[0] == 1


@pytest.fixture
def plvr_postgres_fixture_url():
    import psycopg

    target = os.getenv("PLVR_UPDATE_TEST_URL")
    if not target or os.getenv("PLVR_UPDATE_TEST_DISPOSABLE") != "1":
        pytest.skip("explicit disposable loopback PostgreSQL fixture required")
    parsed = urlparse(target)
    assert parsed.scheme in {"postgres", "postgresql"}
    assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    assert parsed.path.startswith("/plvr_update_test")
    schema = "plvr_update_fixture_" + uuid.uuid4().hex
    with psycopg.connect(target, autocommit=True) as connection:
        connection.execute(psycopg.sql.SQL("create schema {}").format(psycopg.sql.Identifier(schema)))
    query = parsed.query + ("&" if parsed.query else "") + "options=" + quote("-csearch_path=" + schema)
    try:
        yield parsed._replace(query=query).geturl()
    finally:
        with psycopg.connect(target, autocommit=True) as connection:
            connection.execute(psycopg.sql.SQL("drop schema {} cascade").format(psycopg.sql.Identifier(schema)))


@pytest.mark.external_database
def test_postgres_import_rolls_back_all_chunks_when_final_acceptance_fails(tmp_path, plvr_postgres_fixture_url):
    import psycopg

    target = plvr_postgres_fixture_url
    with psycopg.connect(target, autocommit=True) as connection:
        connection.execute((ROOT / "database/valuation_schema.sql").read_text(encoding="utf-8"))
    env = {"PLVR_UPDATE_DATABASE_URL": target, "PLVR_UPDATE_ENVIRONMENT": "production-market-import"}
    manifest, artifact_id, _ = artifact(tmp_path)
    first = run_update(manifest, artifact_id, "--import", env=env)
    assert first.returncode == 0, first.stdout + first.stderr
    duplicate = run_update(manifest, artifact_id, "--import", env=env)
    assert duplicate.returncode == 0, duplicate.stdout + duplicate.stderr
    assert json.loads(duplicate.stdout)["status"] == "duplicate_release"
    with psycopg.connect(target, autocommit=True) as connection:
        connection.execute("create function reject_plvr_acceptance() returns trigger language plpgsql as $$ begin raise exception 'fixture acceptance failure'; end $$")
        connection.execute("create trigger reject_acceptance before insert on plvr_update_releases for each row execute function reject_plvr_acceptance()")
    manifest, artifact_id, _ = artifact(tmp_path, release="20261008", dates=("1150801",) * 201)
    failed = run_update(manifest, artifact_id, "--import", env=env)
    assert failed.returncode == 2
    assert json.loads(failed.stdout)["reason_code"] == "import_transaction_failed"
    with psycopg.connect(target, autocommit=True) as connection:
        assert connection.execute("select count(*) from real_price_transactions").fetchone()[0] == 1
        assert connection.execute("select count(*) from plvr_update_releases").fetchone()[0] == 1
        assert connection.execute("select count(*) from valuation_import_runs").fetchone()[0] == 1
        connection.execute("drop trigger reject_acceptance on plvr_update_releases")
    recovered = run_update(manifest, artifact_id, "--import", env=env)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert json.loads(recovered.stdout)["inserted_rows"] == 201
    with psycopg.connect(target) as connection:
        assert connection.execute("select count(*) from real_price_transactions").fetchone()[0] == 202
        assert connection.execute("select count(*) from plvr_update_releases").fetchone()[0] == 2
        assert connection.execute("select count(*) from valuation_import_runs").fetchone()[0] == 2
