"""Regression coverage for authoritative PLVR clean-shadow rebuilds."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import ssl
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from services.plvr_clean_shadow_rebuild import (
    ArtifactRequest,
    HttpMetadata,
    ReadOnlyProductionRepository,
    acquire_artifacts,
    build_artifact_requests,
    build_clean_shadow,
    load_clean_rows,
    manifest_checksum,
    reconcile_shadow_rows,
    replacement_readiness_gate,
    sha256_file,
    source_identity,
    source_row_hash,
    _official_tls_context,
)
from services.plvr_import_service import FILE_CITY_MAP, build_dedupe_key
from services.taiwan_admin_registry import iter_taiwan_regions


ROOT = Path(__file__).resolve().parents[1]
HEADERS = [
    "鄉鎮市區",
    "交易標的",
    "土地位置建物門牌",
    "交易年月日",
    "移轉層次",
    "總樓層數",
    "建物型態",
    "建築完成年月",
    "建物移轉總面積平方公尺",
    "總價元",
    "單價元平方公尺",
    "編號",
    "移轉編號",
]


class FakeTransport:
    def __init__(self, payload: bytes, *, final_url: str = "https://plvr.land.moi.gov.tw/file.zip") -> None:
        self.payload = payload
        self.final_url = final_url
        self.fail_after: int | None = None

    def probe(self, _url: str, *, timeout: int) -> HttpMetadata:
        assert timeout > 0
        return HttpMetadata(200, self.final_url, "application/zip", len(self.payload))

    def download(self, _url: str, target: Path, *, timeout: int, max_bytes: int) -> HttpMetadata:
        assert timeout > 0
        assert len(self.payload) <= max_bytes
        if self.fail_after is not None:
            target.write_bytes(self.payload[: self.fail_after])
            raise RuntimeError("simulated transport failure")
        target.write_bytes(self.payload)
        return HttpMetadata(200, self.final_url, "application/zip", len(self.payload))


def test_official_tls_context_keeps_certificate_and_hostname_verification() -> None:
    context = _official_tls_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def _region_by_normalized_city() -> dict[str, str]:
    result: dict[str, str] = {}
    for region in iter_taiwan_regions():
        result.setdefault(region.county.replace("臺", "台"), region.district)
    return result


def _row(city: str, district: str, serial: str, **overrides: str) -> dict[str, str]:
    values = {
        "鄉鎮市區": district,
        "交易標的": "房地(土地+建物)",
        "土地位置建物門牌": f"{city}{district}中山路1號",
        "交易年月日": "1140105",
        "移轉層次": "八層",
        "總樓層數": "十五層",
        "建物型態": "住宅大樓",
        "建築完成年月": "1000101",
        "建物移轉總面積平方公尺": "99.17",
        "總價元": "24000000",
        "單價元平方公尺": "242008",
        "編號": serial,
        "移轉編號": f"T-{serial}",
    }
    values.update(overrides)
    return values


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    return text.getvalue().encode("utf-8-sig")


def _official_zip(
    *,
    extra_rows: dict[str, list[dict[str, str]]] | None = None,
    omit_codes: set[str] | None = None,
) -> bytes:
    regions = _region_by_normalized_city()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        manifest_rows = []
        for code, city in FILE_CITY_MAP.items():
            if code in (omit_codes or set()):
                continue
            filename = f"{code}_lvr_land_a.csv"
            rows = [_row(city, regions[city.replace("臺", "台")], f"ID-{code}")]
            rows.extend((extra_rows or {}).get(code, []))
            archive.writestr(filename, _csv_bytes(rows))
            manifest_rows.append((filename, "schema-main.csv", f"{city} sale"))
        manifest = io.StringIO(newline="")
        writer = csv.writer(manifest)
        writer.writerow(("name", "schema", "description"))
        writer.writerows(manifest_rows)
        archive.writestr("manifest.csv", manifest.getvalue().encode("utf-8-sig"))
        archive.writestr("schema-main.csv", b"name,description\n")
        archive.writestr(
            "build_time.xml",
            "<lvr_land><lvr_time>official test release</lvr_time></lvr_land>".encode(),
        )
        archive.writestr("a_lvr_land_a_park.csv", b"not,a,sale,main\n")
        archive.writestr("a_lvr_land_b.csv", b"not,a,sale,main\n")
    return buffer.getvalue()


def _acquire(
    tmp_path: Path,
    payload: bytes,
    *,
    transport: FakeTransport | None = None,
    expected_sha: str = "",
) -> tuple[Path, Path, dict[str, object]]:
    raw = tmp_path / "raw"
    manifest = raw / "source_manifest.json"
    requests = build_artifact_requests(seasons=["114S4"])
    result = acquire_artifacts(
        requests,
        destination=raw,
        manifest_path=manifest,
        download=True,
        expected_sha256={requests[0].artifact_id: expected_sha} if expected_sha else {},
        transport=transport or FakeTransport(payload),
        retrieved_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    return raw, manifest, result


def _build(tmp_path: Path, payload: bytes, **kwargs: object) -> tuple[Path, dict[str, object]]:
    _raw, manifest, acquired = _acquire(tmp_path, payload)
    assert acquired["artifacts"][0]["verification_status"] == "VERIFIED"
    processed = tmp_path / "processed"
    shadow = processed / "clean-shadow.sqlite3"
    report = build_clean_shadow(
        manifest,
        shadow,
        since="2025-01",
        until="2025-12",
        as_of=date(2025, 12, 31),
        normalized_at=datetime(2026, 8, 11, tzinfo=UTC),
        allowed_shadow_root=processed,
        **kwargs,
    )
    return shadow, report


def test_only_allowlisted_https_artifact_source_is_accepted(tmp_path: Path) -> None:
    request = ArtifactRequest(
        "bad", "season", "114S4", "https://example.com/file.zip", "bad.zip"
    )
    result = acquire_artifacts(
        [request],
        destination=tmp_path / "raw",
        manifest_path=tmp_path / "raw" / "manifest.json",
        download=True,
        transport=FakeTransport(_official_zip(), final_url="https://example.com/file.zip"),
    )

    assert result["artifacts"][0]["source_status"] == "UNAVAILABLE_AUTHORITATIVE"
    assert result["artifacts"][0]["reason_code"] == "source_not_authoritative"


def test_verified_official_artifact_records_hash_and_safe_relative_filename(tmp_path: Path) -> None:
    payload = _official_zip()
    _raw, manifest_path, result = _acquire(tmp_path, payload)
    entry = result["artifacts"][0]

    assert entry["source_status"] == "FOUND_AUTHORITATIVE"
    assert entry["verification_status"] == "VERIFIED"
    assert entry["sha256"] == __import__("hashlib").sha256(payload).hexdigest()
    assert entry["sale_main_file_count"] == 22
    assert not Path(entry["local_filename"]).is_absolute()
    assert result["manifest_sha256"] == manifest_checksum(json.loads(manifest_path.read_text(encoding="utf-8")))


def test_sha_mismatch_rejects_artifact_and_removes_partial(tmp_path: Path) -> None:
    payload = _official_zip()
    raw, _manifest, result = _acquire(tmp_path, payload, expected_sha="0" * 64)

    assert result["artifacts"][0]["verification_status"] == "REJECTED"
    assert result["artifacts"][0]["reason_code"] == "artifact_sha256_mismatch"
    assert not (raw / "season-114S4.zip").exists()
    assert not list(raw.glob("*.partial-*"))


def test_partial_download_is_rejected_without_artifact_file(tmp_path: Path) -> None:
    payload = _official_zip()
    transport = FakeTransport(payload)
    transport.fail_after = 100
    raw, _manifest, result = _acquire(tmp_path, payload, transport=transport)

    assert result["artifacts"][0]["verification_status"] == "REJECTED"
    assert result["artifacts"][0]["reason_code"] == "artifact_transport_unavailable"
    assert not (raw / "season-114S4.zip").exists()
    assert not list(raw.glob("*.partial-*"))


def test_existing_artifact_cannot_be_overwritten_without_matching_manifest_hash(tmp_path: Path) -> None:
    payload = _official_zip()
    raw, manifest, first = _acquire(tmp_path, payload)
    target = raw / "season-114S4.zip"
    target.write_bytes(b"different")
    second = acquire_artifacts(
        build_artifact_requests(seasons=["114S4"]),
        destination=raw,
        manifest_path=manifest,
        download=True,
        transport=FakeTransport(payload),
        retrieved_at=datetime(2026, 8, 11, tzinfo=UTC),
    )

    assert first["artifacts"][0]["verification_status"] == "VERIFIED"
    assert second["artifacts"][0]["reason_code"] == "overwrite_checksum_mismatch"
    assert target.read_bytes() == b"different"


def test_partial_city_artifact_is_not_verified(tmp_path: Path) -> None:
    _raw, _manifest, result = _acquire(tmp_path, _official_zip(omit_codes={"z"}))

    assert result["artifacts"][0]["verification_status"] == "REJECTED"
    assert result["artifacts"][0]["reason_code"] == "expected_city_members_missing"


def test_incremental_artifact_can_be_verified_with_partial_city_scope(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    manifest = raw / "source_manifest.json"
    requests = build_artifact_requests(histories=["20260701"])

    result = acquire_artifacts(
        requests,
        destination=raw,
        manifest_path=manifest,
        download=True,
        transport=FakeTransport(_official_zip(omit_codes={"z"})),
        retrieved_at=datetime(2026, 8, 11, tzinfo=UTC),
    )

    artifact = result["artifacts"][0]
    assert artifact["verification_status"] == "VERIFIED"
    assert artifact["source_status"] == "PARTIAL_AUTHORITATIVE"
    assert artifact["coverage_status"] == "PARTIAL"
    assert artifact["missing_cities"] == [FILE_CITY_MAP["z"]]


def test_source_row_identity_is_deterministic_and_bound_to_artifact() -> None:
    raw = {"編號": "A-1", "移轉編號": "T-1", "交易年月日": "1140105"}
    first = source_row_hash(
        raw,
        artifact_sha256="a" * 64,
        official_transaction_id="A-1",
        official_transfer_id="T-1",
    )
    second = source_row_hash(
        dict(reversed(list(raw.items()))),
        artifact_sha256="a" * 64,
        official_transaction_id="A-1",
        official_transfer_id="T-1",
    )

    assert first == second
    assert first != source_row_hash(
        raw,
        artifact_sha256="b" * 64,
        official_transaction_id="A-1",
        official_transfer_id="T-1",
    )
    assert source_identity(
        city="臺北市", official_transaction_id="A-1", official_transfer_id="T-1", row_hash=first
    ) == source_identity(
        city="台北市", official_transaction_id="A-1", official_transfer_id="T-1", row_hash=first
    )


def test_every_accepted_row_has_artifact_row_and_official_identity(tmp_path: Path) -> None:
    shadow, report = _build(tmp_path, _official_zip())

    assert report["accepted_transaction_rows"] == 22
    assert report["lineage"]["rows_with_artifact_hash"] == 22
    assert report["lineage"]["rows_with_source_row_hash"] == 22
    assert report["lineage"]["rows_with_official_id"] == 22
    with sqlite3.connect(shadow) as connection:
        assert connection.execute("select count(*) from shadow_source_rows").fetchone()[0] == 22


def test_artifact_city_and_valid_district_are_canonicalized(tmp_path: Path) -> None:
    shadow, report = _build(tmp_path, _official_zip())

    assert report["invariants"]["canonical_invalid_geography"] == 0
    with sqlite3.connect(shadow) as connection:
        city = connection.execute(
            "select city from shadow_transactions where source_filename = 'a_lvr_land_a.csv'"
        ).fetchone()[0]
    assert city == "臺北市"


def test_artifact_city_conflict_is_rejected_instead_of_operator_override(tmp_path: Path) -> None:
    regions = _region_by_normalized_city()
    conflict = _row("桃園市", regions["桃園市"], "CONFLICT")
    _shadow, report = _build(tmp_path, _official_zip(extra_rows={"a": [conflict]}))

    assert report["accepted_transaction_rows"] == 22
    assert report["exclusion_reasons"]["invalid_city_district_pair"] == 1


def test_future_row_is_forensic_but_not_publishable(tmp_path: Path) -> None:
    regions = _region_by_normalized_city()
    future = _row("台北市", regions["台北市"], "FUTURE", 交易年月日="1150101")
    shadow, report = _build(tmp_path, _official_zip(extra_rows={"a": [future]}))

    assert report["accepted_transaction_rows"] == 22
    assert report["exclusion_reasons"]["future_transaction_period"] == 1
    assert report["invariants"]["publishable_future_rows"] == 0
    with sqlite3.connect(shadow) as connection:
        forensic = connection.execute(
            "select count(*) from shadow_source_rows where reason_code = ?",
            ("future_transaction_period",),
        ).fetchone()[0]
    assert forensic == 1


def test_presale_rent_and_helper_members_never_enter_shadow(tmp_path: Path) -> None:
    shadow, report = _build(tmp_path, _official_zip())

    assert report["raw_rows_read"] == 22
    with sqlite3.connect(shadow) as connection:
        files = {row[0] for row in connection.execute("select distinct source_filename from shadow_source_rows")}
    assert all(name.lower().endswith("_lvr_land_a.csv") for name in files)


def test_business_duplicates_are_separate_from_source_identity(tmp_path: Path) -> None:
    regions = _region_by_normalized_city()
    duplicate = _row("台北市", regions["台北市"], "ID-a")
    _shadow, report = _build(tmp_path, _official_zip(extra_rows={"a": [duplicate]}))

    assert report["business_duplicates"] == 1
    assert report["duplicate_source_identities"] == 1
    assert report["accepted_transaction_rows"] == 22


def test_shadow_aggregate_reuses_market_average_semantics(tmp_path: Path) -> None:
    regions = _region_by_normalized_city()
    second = _row(
        "台北市",
        regions["台北市"],
        "SECOND",
        土地位置建物門牌=f"台北市{regions['台北市']}中山路2號",
        單價元平方公尺="302500",
        總價元="30000000",
    )
    shadow, _report = _build(tmp_path, _official_zip(extra_rows={"a": [second]}))
    with sqlite3.connect(shadow) as connection:
        values = connection.execute(
            """
            select average_unit_price, transaction_count
            from shadow_market_aggregates
            where county = '臺北市' and period = '2025-01'
            """
        ).fetchone()
        direct = connection.execute(
            """
            select round(avg(unit_price_per_ping), 2), count(*)
            from shadow_transactions
            where city = '臺北市' and transaction_period = '2025-01'
            """
        ).fetchone()
    assert values == direct
    assert values[1] == 2


def test_recent_unsettled_period_keeps_replacement_gate_closed(tmp_path: Path) -> None:
    _shadow, report = _build(tmp_path, _official_zip())

    assert report["coverage"]["complete_through"] == "2025-11"
    assert report["coverage"]["partial"] > 0
    assert report["gate"] == "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"


def test_missing_artifact_prevents_complete_coverage(tmp_path: Path) -> None:
    raw, manifest_path, result = _acquire(tmp_path, _official_zip())
    missing = {
        **result["artifacts"][0],
        "artifact_id": "missing",
        "sequence": 2,
        "local_filename": "missing.zip",
        "verification_status": "REJECTED",
        "source_status": "UNAVAILABLE_AUTHORITATIVE",
    }
    result["artifacts"].append(missing)
    result["manifest_sha256"] = manifest_checksum(result)
    manifest_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    processed = tmp_path / "processed"
    report = build_clean_shadow(
        manifest_path,
        processed / "shadow.sqlite3",
        since="2025-01",
        until="2025-12",
        as_of=date(2025, 12, 31),
        allowed_shadow_root=processed,
    )

    assert raw.exists()
    assert report["artifacts"]["rejected_or_missing"] == 1
    assert report["coverage"]["complete"] == 0
    assert report["gate"] == "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"


def test_official_dedupe_key_match_is_authoritative() -> None:
    clean = _clean_reconciliation_row()
    production = {**clean, "dedupe_key": clean["business_dedupe_key"]}
    result = reconcile_shadow_rows([clean], [production], as_of_period="2025-12")

    assert result["production"]["authoritative_matches"] == 1
    assert result["production"]["production_only"] == 0


def test_official_id_proves_corrupt_geography_and_duplicate() -> None:
    clean = _clean_reconciliation_row()
    corrupt = {
        **clean,
        "id": 1,
        "city": "台南市",
        "dedupe_key": "",
    }
    corrupt["dedupe_key"] = build_dedupe_key(corrupt, clean["official_transaction_id"])
    duplicate = {**corrupt, "id": 2}
    result = reconcile_shadow_rows([clean], [corrupt, duplicate], as_of_period="2025-12")

    assert result["production"]["geography_corrupt_matches"] == 1
    assert result["production"]["provable_duplicates"] == 1
    assert result["clean"]["present_but_production_corrupt"] == 1


def test_natural_facts_without_identity_remain_probable() -> None:
    clean = _clean_reconciliation_row()
    production = {**clean, "dedupe_key": "legacy-unverifiable"}
    result = reconcile_shadow_rows([clean], [production], as_of_period="2025-12")

    assert result["production"]["probable_duplicates"] == 1
    assert result["production"]["authoritative_matches"] == 0


def test_production_row_not_in_clean_source_is_reported() -> None:
    clean = _clean_reconciliation_row()
    production = {**clean, "address_text": "different", "dedupe_key": "not-found"}
    result = reconcile_shadow_rows([clean], [production], as_of_period="2025-12")

    assert result["production"]["production_only"] == 1
    assert result["clean"]["missing_from_production"] == 1


def test_future_production_row_is_never_matched_as_publishable() -> None:
    clean = _clean_reconciliation_row()
    production = {
        **clean,
        "transaction_period": "2026-10",
        "dedupe_key": clean["business_dedupe_key"],
    }
    result = reconcile_shadow_rows([clean], [production], as_of_period="2025-12")

    assert result["production"]["future_anomalies"] == 1
    assert result["production"]["authoritative_matches"] == 0


def test_shadow_target_contains_no_production_business_table(tmp_path: Path) -> None:
    shadow, _report = _build(tmp_path, _official_zip())
    with sqlite3.connect(shadow) as connection:
        names = {row[0] for row in connection.execute("select name from sqlite_master where type = 'table'")}

    assert "real_price_transactions" not in names
    assert "market_district_period_aggregates" not in names
    assert "shadow_transactions" in names


def test_production_repository_contract_is_select_only() -> None:
    sql = " ".join(ReadOnlyProductionRepository.TRANSACTION_SQL.lower().split())

    assert sql.startswith("select ")
    for token in ("insert ", "update ", "delete ", "truncate ", "drop ", "alter ", "create "):
        assert token not in sql


def test_readiness_requires_reconciliation_even_with_complete_source() -> None:
    report = {
        "artifacts": {"rejected_or_missing": 0},
        "coverage": {"complete_percent": 100},
        "lineage": {"rows_missing_artifact_hash": 0, "rows_missing_source_row_hash": 0},
        "source_identity_conflicts": 0,
    }

    assert replacement_readiness_gate(report, None) == "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"


def test_shadow_checksum_is_stable_for_same_source_and_as_of(tmp_path: Path) -> None:
    payload = _official_zip()
    first_path, first = _build(tmp_path / "first", payload)
    second_path, second = _build(tmp_path / "second", payload)

    assert first_path.exists() and second_path.exists()
    assert first["shadow_dataset_sha256"] == second["shadow_dataset_sha256"]


def test_published_artifact_manifest_has_only_safe_official_metadata() -> None:
    path = ROOT / "artifacts" / "plvr_source_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert len(payload["artifacts"]) == 17
    assert ":\\" not in serialized
    for forbidden in ("password", "client_secret", "api_key", "access_token", "database_url"):
        assert forbidden not in serialized
    for artifact in payload["artifacts"]:
        assert artifact["download_source"].startswith("https://plvr.land.moi.gov.tw/")
        assert len(artifact["sha256"]) == 64
        assert artifact["verification_status"] == "VERIFIED"
        assert Path(artifact["local_filename"]).name == artifact["local_filename"]


def test_published_shadow_summary_remains_fail_closed() -> None:
    path = ROOT / "docs" / "plvr-clean-shadow-summary-v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["gate"] == "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    assert payload["production_reconciliation"]["status"] == "UNAVAILABLE_ROW_LEVEL_RUNTIME"
    assert payload["lineage"]["publishable_future_rows"] == 0
    assert payload["lineage"]["publishable_future_aggregates"] == 0
    assert payload["production_safety"]["production_writes"] == 0


def _clean_reconciliation_row() -> dict[str, object]:
    row: dict[str, object] = {
        "source_identity": "official-clean-1",
        "source_row_hash": "row-clean-1",
        "official_transaction_id": "OFFICIAL-1",
        "official_transfer_id": "TRANSFER-1",
        "transaction_period": "2025-01",
        "city": "臺北市",
        "district": "中正區",
        "road": "中山路",
        "address_text": "臺北市中正區中山路1號",
        "building_type": "住宅大樓",
        "area_ping": 30.0,
        "total_price": 2400.0,
        "unit_price_per_ping": 80.0,
        "source": "official_plvr_opendata",
    }
    row["business_dedupe_key"] = build_dedupe_key(row, "OFFICIAL-1")
    return row
