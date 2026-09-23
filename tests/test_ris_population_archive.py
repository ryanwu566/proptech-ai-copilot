"""Tests for RIS raw archival to R2 using a mock S3/R2 client (offline)."""

from __future__ import annotations

import builtins
import io
import json
import os
from pathlib import Path

import pytest

import scripts.archive_ris_population_raw as archive_cli
from scripts.archive_ris_population_raw import (
    build_r2_client,
    load_checkpoint,
    run_archive,
    write_checkpoint_atomic,
)

from services.ris_population_archive import (
    KEY_PREFIX,
    MANIFEST_SCHEMA_VERSION,
    RisArchiveImmutabilityError,
    RisArchiveVerificationError,
    archive_month,
    build_manifest,
    build_page_artifacts,
    classify_schema_style,
    collect_raw_pages,
    put_object_immutable,
    serialize_page,
    serialize_manifest,
    sha256_hex,
    verify_object,
)
from services.ris_population_provider import (
    RESPONSE_CODE_NO_MORE_DATA,
    RisPaginationError,
    RisResponseCodeError,
)


# --- mock R2/S3 client ---------------------------------------------------

class NotFound(Exception):
    """Mimics a boto3 not-found: carries a 404 response payload."""

    def __init__(self) -> None:
        super().__init__("not found")
        self.response = {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}}


class MockR2:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}
        self.put_calls = 0

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.store:
            raise NotFound()
        obj = self.store[Key]
        return {"ContentLength": len(obj["Body"]), "Metadata": obj["Metadata"]}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str, Metadata: dict) -> dict:
        self.put_calls += 1
        self.store[Key] = {"Body": Body, "ContentType": ContentType, "Metadata": dict(Metadata)}
        return {"ETag": '"mock"'}

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        obj = self.store[Key]
        return {"Body": io.BytesIO(obj["Body"])}


class CorruptingGetR2(MockR2):
    def get_object(self, *, Bucket: str, Key: str) -> dict:
        obj = self.store[Key]
        return {"Body": io.BytesIO(obj["Body"] + b"corrupt")}


# --- fixtures: two-page raw month (english) + one-page chinese -----------

def _english_pages() -> dict[int, dict]:
    row = {
        "statistic_yyymm": "11507", "district_code": "65000010001", "site_id": "新北市板橋區",
        "village": "留侯里", "household_no": "1", "people_total": "2",
        "people_total_m": "1", "people_total_f": "1",
    }
    return {
        1: {
            "responseCode": "OD-0101-S", "responseMessage": "處理完成",
            "totalPage": "2", "totalDataSize": "3", "page": "1", "pageDataSize": "2",
            "responseData": [row, dict(row, district_code="65000010002", village="流芳里")],
        },
        2: {
            "responseCode": "OD-0101-S", "responseMessage": "處理完成",
            "totalPage": "2", "totalDataSize": "3", "page": "2", "pageDataSize": "1",
            "responseData": [dict(row, district_code="10017010012", site_id="連江縣東引鄉", village="樂華村")],
        },
        3: {"responseCode": RESPONSE_CODE_NO_MORE_DATA},
    }


def _fetcher(pages: dict[int, dict]):
    def fetch(url: str, page: int) -> dict:
        return pages.get(page, {"responseCode": RESPONSE_CODE_NO_MORE_DATA})

    return fetch


# --- deterministic serialization -----------------------------------------

def test_serialize_page_is_deterministic_and_utf8() -> None:
    payload = {"b": "留侯里", "a": 1, "responseData": [{"z": 1, "a": 2}]}
    b1 = serialize_page(payload)
    b2 = serialize_page(dict(reversed(list(payload.items()))))
    assert b1 == b2  # key order independent
    assert "留侯里" in b1.decode("utf-8")  # ensure_ascii=False
    assert sha256_hex(b1) == sha256_hex(b2)


def test_classify_schema_style() -> None:
    assert classify_schema_style(_english_pages()[1]) == "english"
    zh_page = {"responseData": [{"統計年月": "11504", "區域別代碼": "x"}]}
    assert classify_schema_style(zh_page) == "chinese"
    mixed = {"responseData": [{"統計年月": "1", "district_code": "2"}]}
    assert classify_schema_style(mixed) == "bilingual/mixed"


# --- raw page collection preserves source-of-truth ------------------------

def test_collect_raw_pages_preserves_raw_payload() -> None:
    collected = collect_raw_pages("11507", _fetcher(_english_pages()))
    assert collected["total_data_size"] == 3
    assert len(collected["pages"]) == 2
    # Raw field names preserved (not adapted).
    assert "statistic_yyymm" in collected["pages"][0]["responseData"][0]
    # Official metadata preserved.
    assert collected["pages"][0]["responseMessage"] == "處理完成"


def test_collect_raw_pages_row_count_mismatch_fails_closed() -> None:
    pages = _english_pages()
    pages[1]["totalDataSize"] = "999"
    pages[2]["totalDataSize"] = "999"
    with pytest.raises(RisPaginationError):
        collect_raw_pages("11507", _fetcher(pages))


def test_collect_raw_pages_bad_response_code() -> None:
    pages = _english_pages()
    pages[1] = {"responseCode": "OD-9999-E"}
    with pytest.raises(RisResponseCodeError):
        collect_raw_pages("11507", _fetcher(pages))


# --- page artifacts + manifest --------------------------------------------

def test_build_page_artifacts_keys_and_hashes() -> None:
    collected = collect_raw_pages("11507", _fetcher(_english_pages()))
    artifacts = build_page_artifacts(collected)
    assert [a["object_key"] for a in artifacts] == [
        f"{KEY_PREFIX}/2026-07/page-001.json",
        f"{KEY_PREFIX}/2026-07/page-002.json",
    ]
    for a in artifacts:
        assert a["sha256"] == sha256_hex(a["bytes"])
        assert a["byte_size"] == len(a["bytes"])


def test_build_manifest_fields() -> None:
    collected = collect_raw_pages("11507", _fetcher(_english_pages()))
    artifacts = build_page_artifacts(collected)
    manifest = build_manifest(collected, artifacts)
    assert manifest["manifest_schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["dataset"] == "ODRP014"
    assert manifest["statistic_yyymm"] == "11507"
    assert manifest["statistic_month"] == "2026-07"
    assert manifest["pages"] == 2
    assert manifest["total_data_size"] == 3
    assert manifest["schema_style"] == "english"
    assert manifest["total_archived_bytes"] == sum(a["byte_size"] for a in artifacts)
    assert len(manifest["page_files"]) == 2
    assert manifest["page_files"][0]["sha256"] == artifacts[0]["sha256"]
    # No secret-like fields present.
    assert "R2_SECRET_ACCESS_KEY" not in json.dumps(manifest)


def test_manifest_bytes_are_deterministic_without_runtime_timestamp() -> None:
    collected = collect_raw_pages("11507", _fetcher(_english_pages()))
    artifacts = build_page_artifacts(collected)

    first = build_manifest(collected, artifacts)
    second = build_manifest(collected, artifacts)

    assert serialize_manifest(first) == serialize_manifest(second)
    assert "archive_timestamp" not in first
    assert first["page_files"][0]["page_number"] == 1


# --- immutable upload semantics -------------------------------------------

def test_put_object_immutable_uploads_when_absent() -> None:
    client = MockR2()
    data = b"{}"
    result = put_object_immutable(client, "b", "k", data, sha256_hex(data))
    assert result["action"] == "upload"
    assert "k" in client.store


def test_put_object_immutable_skips_identical() -> None:
    client = MockR2()
    data = b'{"a":1}'
    sha = sha256_hex(data)
    put_object_immutable(client, "b", "k", data, sha)
    result = put_object_immutable(client, "b", "k", data, sha)
    assert result["action"] == "skip"
    assert client.put_calls == 1  # not re-uploaded


def test_put_object_immutable_conflict_fails_closed() -> None:
    client = MockR2()
    original = b'{"a":1}'
    put_object_immutable(client, "b", "k", original, sha256_hex(original))
    changed = b'{"a":2}'
    with pytest.raises(RisArchiveImmutabilityError):
        put_object_immutable(client, "b", "k", changed, sha256_hex(changed))
    # Original bytes untouched.
    assert client.store["k"]["Body"] == original


def test_put_object_immutable_dry_run_plans_without_upload() -> None:
    client = MockR2()
    data = b"{}"
    result = put_object_immutable(client, "b", "k", data, sha256_hex(data), dry_run=True)
    assert result["action"] == "planned"
    assert client.put_calls == 0
    assert "k" not in client.store


# --- verification ---------------------------------------------------------

def test_verify_object_success_and_failure() -> None:
    client = MockR2()
    data = b'{"a":1}'
    sha = sha256_hex(data)
    put_object_immutable(client, "b", "k", data, sha)
    ok = verify_object(client, "b", "k", len(data), sha)
    assert ok["verified"] is True
    with pytest.raises(RisArchiveVerificationError, match="metadata sha256"):
        verify_object(client, "b", "k", len(data), "deadbeef")


def test_verify_object_get_hash_mismatch_fails_closed() -> None:
    client = MockR2()
    expected = b'{"a":1}'
    expected_sha = sha256_hex(expected)
    client.store["k"] = {
        "Body": b'{"a":2}',
        "ContentType": "application/json",
        "Metadata": {"sha256": expected_sha},
    }

    with pytest.raises(RisArchiveVerificationError, match="GET sha256"):
        verify_object(client, "b", "k", len(expected), expected_sha)


def test_existing_manifest_is_verified_by_exact_bytes_not_fingerprint() -> None:
    client = MockR2()
    result = archive_month("11507", _fetcher(_english_pages()), client, "b")
    manifest_key = result["manifest_key"]
    original = client.store[manifest_key]
    tampered = b"{" + b" " * (len(original["Body"]) - 2) + b"}"
    client.store[manifest_key] = {
        "Body": tampered,
        "ContentType": "application/json",
        "Metadata": dict(original["Metadata"]),
    }

    with pytest.raises(RisArchiveVerificationError, match="GET sha256"):
        archive_month("11507", _fetcher(_english_pages()), client, "b")


# --- end-to-end archive_month --------------------------------------------

def test_archive_month_uploads_and_verifies() -> None:
    client = MockR2()
    result = archive_month("11507", _fetcher(_english_pages()), client, "proptech-government-data")
    # 2 pages + manifest = 3 objects.
    assert result["objects_uploaded"] == 3
    assert result["all_objects_verified"] is True
    assert result["manifest_key"] == f"{KEY_PREFIX}/2026-07/manifest.json"
    assert result["object_keys"][-1] == result["manifest_key"]
    # Re-running is idempotent: everything skipped, nothing re-uploaded.
    result2 = archive_month("11507", _fetcher(_english_pages()), client, "proptech-government-data")
    assert result2["objects_skipped"] == 3
    assert result2["objects_uploaded"] == 0


def test_archive_month_sets_required_metadata_on_pages_and_manifest() -> None:
    client = MockR2()
    result = archive_month("11507", _fetcher(_english_pages()), client, "b")

    for key in result["object_keys"]:
        metadata = client.store[key]["Metadata"]
        assert metadata["provider"] == "ris"
        assert metadata["dataset"] == "odrp014-population"
        assert metadata["statistic_yyymm"] == "11507"
        assert metadata["sha256"] == sha256_hex(client.store[key]["Body"])


def test_archive_month_emits_live_progress_events() -> None:
    client = MockR2()
    events: list[str] = []

    archive_month(
        "11507", _fetcher(_english_pages()), client, "b", progress=events.append
    )

    assert events == [
        "2026-07 START",
        "fetch page 1/2",
        "fetch page 2/2",
        "page objects upload/verify",
        "manifest upload/verify",
    ]


def test_archive_month_dry_run_writes_nothing() -> None:
    client = MockR2()
    result = archive_month("11507", _fetcher(_english_pages()), client, "b", dry_run=True)
    assert result["dry_run"] is True
    assert result["objects_planned"] == 3
    assert result["all_objects_verified"] is None
    assert client.put_calls == 0
    assert client.store == {}


def test_archive_month_conflict_fails_closed() -> None:
    client = MockR2()
    # Pre-seed the first page key with different bytes to force a conflict.
    collected = collect_raw_pages("11507", _fetcher(_english_pages()))
    artifacts = build_page_artifacts(collected)
    first_key = artifacts[0]["object_key"]
    tampered = b'{"tampered":true}'
    client.store[first_key] = {"Body": tampered, "ContentType": "application/json", "Metadata": {"sha256": "other"}}
    with pytest.raises(RisArchiveImmutabilityError):
        archive_month("11507", _fetcher(_english_pages()), client, "b")
    # Tampered object untouched.
    assert client.store[first_key]["Body"] == tampered


def test_archive_month_chinese_schema_style() -> None:
    zh_row = {
        "統計年月": "11504", "區域別代碼": "65000010002", "區域別": "新北市板橋區",
        "村里": "流芳里", "戶數": "1", "人口數": "2", "人口數-男": "1", "人口數-女": "1",
    }
    pages = {
        1: {
            "responseCode": "OD-0101-S", "responseMessage": "處理完成",
            "totalPage": "1", "totalDataSize": "1", "page": "1", "pageDataSize": "1",
            "responseData": [zh_row],
        },
        2: {"responseCode": RESPONSE_CODE_NO_MORE_DATA},
    }
    client = MockR2()
    result = archive_month("11504", _fetcher(pages), client, "b")
    assert result["schema_style"] == "chinese"
    assert result["statistic_month"] == "2026-04"
    assert result["all_objects_verified"] is True
    # Archived bytes preserve the Chinese source field names verbatim.
    page_key = result["object_keys"][0]
    stored = json.loads(client.store[page_key]["Body"].decode("utf-8"))
    assert "統計年月" in stored["responseData"][0]


# --- checkpoint / resume / CLI -------------------------------------------

def test_checkpoint_write_replaces_atomically_without_temp_residue(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "phase2d_checkpoint.json"
    checkpoint_path.write_text('{"old":true}', encoding="utf-8")
    expected = {"schema_version": "ris-phase2d-checkpoint-v1", "months": {}}

    write_checkpoint_atomic(checkpoint_path, expected)

    assert json.loads(checkpoint_path.read_text(encoding="utf-8")) == expected
    assert not checkpoint_path.with_name(checkpoint_path.name + ".tmp").exists()


def test_run_archive_resumes_only_unverified_months(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "phase2d_checkpoint.json"
    write_checkpoint_atomic(
        checkpoint_path,
        {
            "schema_version": "ris-phase2d-checkpoint-v1",
            "months": {
                "11506": {
                    "month": "11506",
                    "status": "VERIFIED",
                    "pages_verified": 2,
                    "manifest_verified": True,
                    "uploaded_objects": 3,
                    "skipped_objects": 0,
                    "total_bytes": 100,
                    "error": None,
                }
            },
        },
    )
    fetched_urls: list[str] = []

    def fetch(url: str, page: int) -> dict:
        fetched_urls.append(url)
        return _english_pages().get(page, {"responseCode": RESPONSE_CODE_NO_MORE_DATA})

    output: list[str] = []

    def emit(message: str) -> None:
        if message.endswith("PASS"):
            saved = load_checkpoint(checkpoint_path)
            assert saved["months"]["11507"]["status"] == "VERIFIED"
        output.append(message)

    run_archive(
        ["11506", "11507"],
        fetch,
        MockR2(),
        "proptech-government-data",
        checkpoint_path=checkpoint_path,
        emit=emit,
    )

    checkpoint = load_checkpoint(checkpoint_path)
    assert not any("11506" in url for url in fetched_urls)
    assert checkpoint["months"]["11507"]["status"] == "VERIFIED"
    assert output[0] == "[1/2] 2026-06 SKIP checkpoint VERIFIED"
    assert "[2/2] 2026-07 START" in output
    assert "[2/2] fetch page 1/2" in output
    assert output[-1] == "[2/2] PASS"


def test_verification_failure_marks_failed_and_stops_before_next_month(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "phase2d_checkpoint.json"
    fetched_urls: list[str] = []

    def fetch(url: str, page: int) -> dict:
        fetched_urls.append(url)
        return _english_pages().get(page, {"responseCode": RESPONSE_CODE_NO_MORE_DATA})

    client = CorruptingGetR2()
    output: list[str] = []
    with pytest.raises(RisArchiveVerificationError):
        run_archive(
            ["11507", "11508"],
            fetch,
            client,
            "b",
            checkpoint_path=checkpoint_path,
            emit=output.append,
        )

    checkpoint = load_checkpoint(checkpoint_path)
    assert checkpoint["months"]["11507"]["status"] == "FAILED"
    assert checkpoint["months"]["11507"]["manifest_verified"] is False
    assert "11508" not in checkpoint["months"]
    assert not any("11508" in url for url in fetched_urls)
    assert not any(key.endswith("manifest.json") for key in client.store)
    assert output[-1].startswith("[1/2] 2026-07 FAIL:")


def test_build_r2_client_uses_region_and_defaults_to_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_client(service: str, **kwargs: object) -> object:
        calls.append({"service": service, **kwargs})
        return object()

    monkeypatch.setattr("boto3.client", fake_client)
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "not-a-real-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "not-a-real-secret")
    monkeypatch.setenv("R2_ENDPOINT", "https://example.invalid")
    monkeypatch.delenv("R2_REGION", raising=False)
    build_r2_client()
    monkeypatch.setenv("R2_REGION", "custom-region")
    build_r2_client()

    assert calls[0]["region_name"] == "auto"
    assert calls[1]["region_name"] == "custom-region"


def test_live_main_uses_checkpoint_runner_and_clears_r2_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[list[str]] = []
    for name in (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_ENDPOINT",
        "R2_BUCKET",
        "R2_REGION",
    ):
        monkeypatch.setenv(name, "sensitive-test-value")

    monkeypatch.setattr(archive_cli, "build_r2_client", lambda: object())
    monkeypatch.setattr(archive_cli, "build_page_fetcher", lambda timeout: object())
    monkeypatch.setattr(
        archive_cli,
        "archive_month",
        lambda *args, **kwargs: {
            "yyymm": "11507",
            "statistic_month": "2026-07",
            "schema_style": "english",
            "pages": 1,
            "total_data_size": 1,
            "objects_uploaded": 2,
            "objects_skipped": 0,
            "objects_planned": 0,
            "total_archived_bytes": 10,
            "all_objects_verified": True,
            "object_keys": ["page", "manifest"],
            "manifest_key": "manifest",
        },
    )
    monkeypatch.setattr(
        archive_cli,
        "run_archive",
        lambda months, *args, **kwargs: called.append(months) or [],
    )

    assert archive_cli.main(["--month", "11507"]) == 0
    assert called == [["11507"]]
    for name in (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_ENDPOINT",
        "R2_BUCKET",
        "R2_REGION",
    ):
        assert name not in os.environ


def test_live_main_clears_partial_r2_env_when_client_build_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "sensitive-test-value")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "sensitive-test-value")
    monkeypatch.delenv("R2_ENDPOINT", raising=False)

    assert archive_cli.main(["--month", "11507"]) == 2
    assert "R2_ACCESS_KEY_ID" not in os.environ
    assert "R2_SECRET_ACCESS_KEY" not in os.environ


def test_live_main_flushes_each_progress_line(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[tuple[str, bool]] = []

    def fake_print(message: object = "", **kwargs: object) -> None:
        printed.append((str(message), kwargs.get("flush") is True))

    def fake_run(*args: object, **kwargs: object) -> list[dict]:
        emit = kwargs.get("emit", builtins.print)
        emit("[1/1] progress")
        return []

    for name in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT"):
        monkeypatch.setenv(name, "sensitive-test-value")
    monkeypatch.setattr(builtins, "print", fake_print)
    monkeypatch.setattr(archive_cli, "build_r2_client", lambda: object())
    monkeypatch.setattr(archive_cli, "build_page_fetcher", lambda timeout: object())
    monkeypatch.setattr(archive_cli, "run_archive", fake_run)

    assert archive_cli.main(["--month", "11507"]) == 0
    assert ("[1/1] progress", True) in printed
