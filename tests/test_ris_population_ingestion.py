from __future__ import annotations

import copy
from contextlib import contextmanager
from datetime import date
import io
import json
from pathlib import Path

import pytest

from services.ris_population_archive import (
    RisArchiveVerificationError,
    archive_month,
)


ROOT = Path(__file__).resolve().parents[1]
EN_FIXTURE = ROOT / "tests/fixtures/ris_odrp014_sample.json"
ZH_FIXTURE = ROOT / "tests/fixtures/ris_odrp014_sample_zh.json"


class NotFound(Exception):
    def __init__(self) -> None:
        self.response = {
            "Error": {"Code": "404"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }


class MemoryR2:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, object]] = {}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        if Key not in self.store:
            raise NotFound()
        obj = self.store[Key]
        body = obj["Body"]
        assert isinstance(body, bytes)
        return {"ContentLength": len(body), "Metadata": obj["Metadata"]}

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: dict[str, str],
    ) -> dict[str, str]:
        del Bucket
        self.store[Key] = {
            "Body": Body,
            "ContentType": ContentType,
            "Metadata": dict(Metadata),
        }
        return {"ETag": "mock"}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, io.BytesIO]:
        del Bucket
        body = self.store[Key]["Body"]
        assert isinstance(body, bytes)
        return {"Body": io.BytesIO(body)}


def _archive_fixture(path: Path, yyymm: str) -> MemoryR2:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _archive_payload(payload, yyymm)


def _archive_payload(payload: dict[str, dict], yyymm: str) -> MemoryR2:
    pages = {int(name.rsplit("_", 1)[1]): page for name, page in payload.items()}
    client = MemoryR2()
    archive_month(
        yyymm,
        lambda _url, page: copy.deepcopy(pages[page]),
        client,
        "bucket",
    )
    return client


class Result:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class FakeConnection:
    def __init__(self, *, fail_batch: int | None = None) -> None:
        self.rows: dict[tuple[str, str], dict[str, object]] = {}
        self.fail_batch = fail_batch
        self.batch_count = 0
        self.transaction_started = False
        self.transaction_active = False
        self.committed = False
        self.rolled_back = False
        self.advisory_lock: tuple[int, int] | None = None
        self.batch_sizes: list[int] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    @contextmanager
    def transaction(self):
        self.transaction_started = True
        self.transaction_active = True
        snapshot = copy.deepcopy(self.rows)
        try:
            yield
        except Exception:
            self.rows = snapshot
            self.rolled_back = True
            raise
        else:
            self.committed = True
        finally:
            self.transaction_active = False

    def execute(self, sql: str, params: tuple[object, ...]) -> Result:
        normalized = " ".join(sql.lower().split())
        if "pg_advisory_xact_lock" in normalized:
            assert self.transaction_active
            self.advisory_lock = (int(params[0]), int(params[1]))
            return Result([])
        if normalized.startswith("select district_code"):
            yyymm = str(params[0])
            return Result([(code,) for month, code in self.rows if month == yyymm])
        raise AssertionError(f"unexpected SQL: {normalized}")

    def cursor(self) -> "FakeConnection":
        return self

    def executemany(self, sql: str, params: list[dict[str, object]]) -> None:
        assert self.transaction_active
        assert "on conflict (statistic_yyymm, district_code) do update" in " ".join(
            sql.lower().split()
        )
        self.batch_count += 1
        if self.fail_batch == self.batch_count:
            raise RuntimeError("synthetic batch failure")
        self.batch_sizes.append(len(params))
        for row in params:
            key = (str(row["statistic_yyymm"]), str(row["district_code"]))
            self.rows[key] = dict(row)


def _prepared_rows(count: int, yyymm: str = "11507") -> list[dict[str, object]]:
    return [
        {
            "statistic_yyymm": yyymm,
            "statistic_month": "2026-07" if yyymm == "11507" else "2026-04",
            "district_code": f"code-{index:05d}",
            "site_id": "臺北市大安區",
            "village": f"里-{index}",
            "household_count": 1,
            "total_population": 2,
            "male_population": 1,
            "female_population": 1,
            "age_0_14": 0,
            "age_15_64": 2,
            "age_65_plus": 0,
            "child_ratio": 0.0,
            "working_age_ratio": 1.0,
            "elderly_ratio": 0.0,
            "average_household_size": 2.0,
            "audit_reasons": ["source mismatch"] if index == 0 else [],
        }
        for index in range(count)
    ]


def test_verified_english_archive_is_adapted_and_normalized() -> None:
    from services.ris_population_ingestion import prepare_archive_month

    prepared = prepare_archive_month(_archive_fixture(EN_FIXTURE, "11507"), "bucket", "11507")

    assert prepared.statistic_yyymm == "11507"
    assert prepared.statistic_month == date(2026, 7, 1)
    assert prepared.rows_source == prepared.rows_normalized == 3
    assert len(prepared.rows) == 3
    assert prepared.rows[0]["statistic_month"] == date(2026, 7, 1)


def test_verified_chinese_archive_uses_existing_schema_adapter() -> None:
    from services.ris_population_ingestion import prepare_archive_month

    prepared = prepare_archive_month(_archive_fixture(ZH_FIXTURE, "11504"), "bucket", "11504")

    assert prepared.statistic_yyymm == "11504"
    assert prepared.statistic_month == date(2026, 4, 1)
    assert prepared.rows_source == prepared.rows_normalized == 3
    assert all(row["district_code"] for row in prepared.rows)


def test_archive_checksum_failure_never_opens_database_connection() -> None:
    from services.ris_population_ingestion import ingest_archive_month

    client = _archive_fixture(EN_FIXTURE, "11507")
    page_key = "raw/ris/population/2026-07/page-001.json"
    client.store[page_key]["Body"] = client.store[page_key]["Body"] + b"corrupt"
    connection_opened = False

    def connection_factory() -> FakeConnection:
        nonlocal connection_opened
        connection_opened = True
        return FakeConnection()

    with pytest.raises(RisArchiveVerificationError):
        ingest_archive_month(client, "bucket", "11507", connection_factory)

    assert connection_opened is False


def test_archive_pagination_failure_never_opens_database_connection() -> None:
    from services.ris_population_ingestion import RisPopulationIngestionError, ingest_archive_month

    client = _archive_fixture(EN_FIXTURE, "11507")
    key = "raw/ris/population/2026-07/page-002.json"
    payload = json.loads(client.store[key]["Body"])
    payload["page"] = "1"
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    from services.ris_population_archive import sha256_hex

    client.store[key]["Body"] = body
    client.store[key]["Metadata"]["sha256"] = sha256_hex(body)
    manifest_key = "raw/ris/population/2026-07/manifest.json"
    manifest = json.loads(client.store[manifest_key]["Body"])
    manifest["page_files"][1]["byte_size"] = len(body)
    manifest["page_files"][1]["sha256"] = sha256_hex(body)
    manifest_body = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    client.store[manifest_key]["Body"] = manifest_body
    client.store[manifest_key]["Metadata"]["sha256"] = sha256_hex(manifest_body)
    opened = False

    def connection_factory() -> FakeConnection:
        nonlocal opened
        opened = True
        return FakeConnection()

    with pytest.raises(RisPopulationIngestionError, match="page number"):
        ingest_archive_month(client, "bucket", "11507", connection_factory)
    assert opened is False


def test_normalization_failure_never_opens_database_connection() -> None:
    from services.ris_population_dataset import RisNormalizationError
    from services.ris_population_ingestion import ingest_archive_month

    payload = json.loads(EN_FIXTURE.read_text(encoding="utf-8"))
    payload["page_1"]["responseData"][0]["household_no"] = "-1"
    client = _archive_payload(payload, "11507")
    opened = False

    def connection_factory() -> FakeConnection:
        nonlocal opened
        opened = True
        return FakeConnection()

    with pytest.raises(RisNormalizationError, match="negative"):
        ingest_archive_month(client, "bucket", "11507", connection_factory)
    assert opened is False


def test_ingestion_uses_transaction_scoped_namespaced_lock_and_500_row_batches() -> None:
    from services.ris_population_ingestion import (
        RIS_ADVISORY_LOCK_NAMESPACE,
        prepare_normalized_month,
        ingest_prepared_month,
    )

    connection = FakeConnection()
    prepared = prepare_normalized_month(_prepared_rows(1001), rows_source=1001)

    report = ingest_prepared_month(connection, prepared, batch_size=500)

    assert connection.advisory_lock == (RIS_ADVISORY_LOCK_NAMESPACE, 11507)
    assert connection.batch_sizes == [500, 500, 1]
    assert connection.committed is True
    assert report["inserted"] == 1001
    assert report["updated"] == 0
    assert report["audit_flagged"] == 1
    assert report["status"] == "VERIFIED"


def test_rerun_is_idempotent_and_updates_all_existing_rows() -> None:
    from services.ris_population_ingestion import ingest_prepared_month, prepare_normalized_month

    connection = FakeConnection()
    prepared = prepare_normalized_month(_prepared_rows(3), rows_source=3)

    first = ingest_prepared_month(connection, prepared)
    changed_rows = _prepared_rows(3)
    changed_rows[0]["village"] = "updated village"
    changed_rows[0]["total_population"] = 3
    second = ingest_prepared_month(
        connection,
        prepare_normalized_month(changed_rows, rows_source=3),
    )

    assert len(connection.rows) == 3
    assert first["inserted"] == 3 and first["updated"] == 0
    assert second["inserted"] == 0 and second["updated"] == 3
    assert connection.rows[("11507", "code-00000")]["audit_reasons_json"] == '["source mismatch"]'
    assert connection.rows[("11507", "code-00000")]["village"] == "updated village"
    assert connection.rows[("11507", "code-00000")]["total_population"] == 3


def test_different_months_may_reuse_district_code() -> None:
    from services.ris_population_ingestion import ingest_prepared_month, prepare_normalized_month

    connection = FakeConnection()
    july = prepare_normalized_month(_prepared_rows(1, "11507"), rows_source=1)
    april_rows = _prepared_rows(1, "11504")
    april = prepare_normalized_month(april_rows, rows_source=1)

    ingest_prepared_month(connection, july)
    ingest_prepared_month(connection, april)

    assert len(connection.rows) == 2


def test_duplicate_business_key_is_rejected_before_transaction() -> None:
    from services.ris_population_ingestion import RisPopulationIngestionError, prepare_normalized_month

    rows = _prepared_rows(2)
    rows[1]["district_code"] = rows[0]["district_code"]

    with pytest.raises(RisPopulationIngestionError, match="duplicate"):
        prepare_normalized_month(rows, rows_source=2)


def test_batch_error_rolls_back_entire_month() -> None:
    from services.ris_population_ingestion import ingest_prepared_month, prepare_normalized_month

    connection = FakeConnection(fail_batch=2)
    prepared = prepare_normalized_month(_prepared_rows(501), rows_source=501)

    with pytest.raises(RuntimeError, match="synthetic batch failure"):
        ingest_prepared_month(connection, prepared, batch_size=500)

    assert connection.rolled_back is True
    assert connection.rows == {}
