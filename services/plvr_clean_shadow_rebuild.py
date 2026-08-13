"""Authoritative PLVR artifact acquisition and local clean-shadow rebuild.

The module deliberately separates immutable source identity from normalized
business deduplication.  It can read production through a SELECT-only
repository for reconciliation, but every rebuild write is constrained to a
local SQLite shadow database.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import ssl
import tempfile
import unicodedata
import urllib.parse
import uuid
import zipfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Protocol, Sequence

import httpx

from services.plvr_data_integrity import (
    FUTURE_TRANSACTION_PERIOD,
    INVALID_CITY_DISTRICT_PAIR,
    OFFICIAL_CITY_LEVEL_GEOGRAPHIES,
    current_transaction_period,
    normalized_row_integrity_reason,
)
from services.plvr_coverage_closure import build_coverage_report
from services.plvr_import_service import (
    ENCODINGS,
    FIELD_ALIASES,
    FILE_CITY_MAP,
    OFFICIAL_SOURCE,
    REQUIRED_HEADER_GROUPS,
    build_dedupe_key,
    city_from_filename,
    normalize_row,
    read_csv_rows,
    roc_date_to_period,
    same_city,
)
from services.plvr_market_aggregate_service import (
    PLVR_AGGREGATION_METHOD,
    PLVR_MARKET_SOURCE_NAME,
)
from services.taiwan_admin_registry import iter_taiwan_regions, normalize_market_region


OFFICIAL_SOURCE_AGENCY = "Ministry of the Interior, Department of Land Administration"
OFFICIAL_SOURCE_PAGE = "https://data.gov.tw/dataset/25119"
OFFICIAL_DOWNLOAD_HOSTS = frozenset({"plvr.land.moi.gov.tw"})
OFFICIAL_CURRENT_URL = "https://plvr.land.moi.gov.tw/opendata/lvr_landAcsv.zip"
OFFICIAL_SEASON_URL = (
    "https://plvr.land.moi.gov.tw/DownloadSeason?"
    "season={release}&type=zip&fileName=lvr_landcsv.zip"
)
OFFICIAL_HISTORY_URL = (
    "https://plvr.land.moi.gov.tw/DownloadHistory?type=history&fileName={release}"
)
MANIFEST_SCHEMA_VERSION = "plvr-authoritative-artifact-manifest-v1"
SHADOW_SCHEMA_VERSION = "plvr-clean-shadow-v2"
NORMALIZER_VERSION = "plvr-normalizer-v3-source-geography"
DEDUPE_ALGORITHM_VERSION = "plvr-dedupe-v2"
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
SHADOW_WRITE_BATCH_SIZE = 1000
EXPECTED_CITIES = tuple(FILE_CITY_MAP.values())
PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
SEASON_PATTERN = re.compile(r"^(?P<year>\d{3})S(?P<quarter>[1-4])$")
HISTORY_PATTERN = re.compile(r"^\d{8}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ArtifactAcquisitionError(RuntimeError):
    """Raised when an artifact cannot be acquired without weakening safety."""


class ShadowRebuildError(RuntimeError):
    """Raised when a clean shadow cannot be built deterministically."""


@dataclass(frozen=True)
class ArtifactRequest:
    artifact_id: str
    kind: str
    release: str
    download_source: str
    local_filename: str
    coverage_scope: str = "nationwide"
    transaction_type: str = "sale_main"


@dataclass(frozen=True)
class HttpMetadata:
    status_code: int
    final_url: str
    content_type: str = ""
    content_length: int | None = None
    last_modified: str = ""
    etag: str = ""
    content_disposition: str = ""


class ArtifactTransport(Protocol):
    def probe(self, url: str, *, timeout: int) -> HttpMetadata:
        """Return public HTTP metadata without persisting the response body."""

    def download(
        self,
        url: str,
        target: Path,
        *,
        timeout: int,
        max_bytes: int,
    ) -> HttpMetadata:
        """Download one response to target and return its HTTP metadata."""


class HttpxArtifactTransport:
    """Small HTTPS transport with bounded streaming and redirect validation."""

    user_agent = "PropTech-AI-Copilot-PLVR-Shadow/1.0"

    def probe(self, url: str, *, timeout: int) -> HttpMetadata:
        with httpx.Client(
            verify=_official_tls_context(),
            follow_redirects=True,
            max_redirects=5,
            timeout=timeout,
        ) as client:
            with client.stream(
                "GET",
                url,
                headers={
                    "Accept-Encoding": "identity",
                    "Range": "bytes=0-0",
                    "User-Agent": self.user_agent,
                },
            ) as response:
                return _response_metadata(response)

    def download(
        self,
        url: str,
        target: Path,
        *,
        timeout: int,
        max_bytes: int,
    ) -> HttpMetadata:
        with httpx.Client(
            verify=_official_tls_context(),
            follow_redirects=True,
            max_redirects=5,
            timeout=timeout,
        ) as client:
            with client.stream(
                "GET",
                url,
                headers={"Accept-Encoding": "identity", "User-Agent": self.user_agent},
            ) as response:
                metadata = _response_metadata(response)
                _validate_official_url(metadata.final_url)
                if metadata.status_code != 200:
                    raise ArtifactAcquisitionError("artifact_http_status_unavailable")
                if metadata.content_length is not None and metadata.content_length > max_bytes:
                    raise ArtifactAcquisitionError("artifact_exceeds_maximum_size")
                written = 0
                with target.open("xb") as handle:
                    for chunk in response.iter_bytes(1024 * 1024):
                        written += len(chunk)
                        if written > max_bytes:
                            raise ArtifactAcquisitionError("artifact_exceeds_maximum_size")
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
                if metadata.content_length is not None and written != metadata.content_length:
                    raise ArtifactAcquisitionError("partial_download_detected")
                return metadata


def build_artifact_requests(
    *,
    seasons: Iterable[str] = (),
    histories: Iterable[str] = (),
    current_release: str = "",
) -> list[ArtifactRequest]:
    """Build an explicit, deterministic list of official artifact requests."""

    requests: list[ArtifactRequest] = []
    for raw in seasons:
        release = str(raw).strip().upper()
        if not SEASON_PATTERN.fullmatch(release):
            raise ArtifactAcquisitionError("invalid_season_release")
        requests.append(
            ArtifactRequest(
                artifact_id=f"moi-plvr-sale-season-{release}",
                kind="season",
                release=release,
                download_source=OFFICIAL_SEASON_URL.format(release=release),
                local_filename=f"season-{release}.zip",
            )
        )
    for raw in histories:
        release = str(raw).strip()
        if not HISTORY_PATTERN.fullmatch(release):
            raise ArtifactAcquisitionError("invalid_history_release")
        requests.append(
            ArtifactRequest(
                artifact_id=f"moi-plvr-sale-history-{release}",
                kind="history",
                release=release,
                download_source=OFFICIAL_HISTORY_URL.format(release=release),
                local_filename=f"history-{release}.zip",
            )
        )
    if current_release:
        release = current_release.strip()
        if not HISTORY_PATTERN.fullmatch(release):
            raise ArtifactAcquisitionError("invalid_current_release")
        requests.append(
            ArtifactRequest(
                artifact_id=f"moi-plvr-sale-current-{release}",
                kind="current",
                release=release,
                download_source=OFFICIAL_CURRENT_URL,
                local_filename=f"current-{release}.zip",
            )
        )
    if not requests:
        raise ArtifactAcquisitionError("explicit_artifact_scope_required")
    ids = [request.artifact_id for request in requests]
    if len(ids) != len(set(ids)):
        raise ArtifactAcquisitionError("duplicate_artifact_request")
    for request in requests:
        _validate_official_url(request.download_source)
    return requests


def acquire_artifacts(
    requests: Sequence[ArtifactRequest],
    *,
    destination: Path,
    manifest_path: Path,
    download: bool = False,
    expected_sha256: Mapping[str, str] | None = None,
    transport: ArtifactTransport | None = None,
    retrieved_at: datetime | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Inventory or atomically acquire a bounded set of official artifacts."""

    if not requests:
        raise ArtifactAcquisitionError("explicit_artifact_scope_required")
    expected = {key: value.lower() for key, value in (expected_sha256 or {}).items()}
    for value in expected.values():
        if not SHA256_PATTERN.fullmatch(value):
            raise ArtifactAcquisitionError("invalid_expected_sha256")
    client = transport or HttpxArtifactTransport()
    stamp = (retrieved_at or datetime.now(UTC)).astimezone(UTC).isoformat()
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    previous = _read_manifest_if_present(manifest_path)
    previous_by_id = {
        str(item.get("artifact_id")): item
        for item in previous.get("artifacts", [])
        if isinstance(item, dict)
    }
    entries: list[dict[str, Any]] = []

    for sequence, request in enumerate(requests, start=1):
        target = destination / request.local_filename
        _assert_direct_child(destination, target)
        try:
            metadata = client.probe(request.download_source, timeout=min(timeout, 60))
            _validate_official_url(metadata.final_url)
            if metadata.status_code not in {200, 206}:
                raise ArtifactAcquisitionError("artifact_http_status_unavailable")
            if not download:
                entries.append(
                    _manifest_entry(
                        request,
                        sequence=sequence,
                        retrieved_at=stamp,
                        metadata=metadata,
                        source_status="FOUND_AUTHORITATIVE",
                        verification_status="NOT_DOWNLOADED",
                    )
                )
                continue

            if target.exists():
                prior = previous_by_id.get(request.artifact_id, {})
                actual_hash = sha256_file(target)
                allowed_hash = expected.get(request.artifact_id) or str(prior.get("sha256") or "").lower()
                if not allowed_hash or actual_hash != allowed_hash:
                    raise ArtifactAcquisitionError("overwrite_checksum_mismatch")
                verification = verify_artifact(
                    target,
                    expected_sha256=allowed_hash,
                    allow_partial_city_scope=request.kind in {"history", "current"},
                )
                entries.append(
                    _manifest_entry(
                        request,
                        sequence=sequence,
                        retrieved_at=str(prior.get("retrieved_at") or stamp),
                        metadata=metadata,
                        **verification,
                    )
                )
                continue

            partial = target.with_name(f"{target.name}.partial-{uuid.uuid4().hex}")
            try:
                downloaded_metadata = client.download(
                    request.download_source,
                    partial,
                    timeout=timeout,
                    max_bytes=MAX_ARTIFACT_BYTES,
                )
                _validate_official_url(downloaded_metadata.final_url)
                actual_hash = sha256_file(partial)
                expected_hash = expected.get(request.artifact_id)
                if expected_hash and actual_hash != expected_hash:
                    raise ArtifactAcquisitionError("artifact_sha256_mismatch")
                verification = verify_artifact(
                    partial,
                    expected_sha256=expected_hash,
                    allow_partial_city_scope=request.kind in {"history", "current"},
                )
                if verification["verification_status"] != "VERIFIED":
                    entries.append(
                        _manifest_entry(
                            request,
                            sequence=sequence,
                            retrieved_at=stamp,
                            metadata=downloaded_metadata,
                            **verification,
                        )
                    )
                    continue
                os.replace(partial, target)
                entries.append(
                    _manifest_entry(
                        request,
                        sequence=sequence,
                        retrieved_at=stamp,
                        metadata=downloaded_metadata,
                        **verification,
                    )
                )
            finally:
                partial.unlink(missing_ok=True)
        except Exception as error:
            entries.append(
                _manifest_entry(
                    request,
                    sequence=sequence,
                    retrieved_at=stamp,
                    source_status="UNAVAILABLE_AUTHORITATIVE",
                    verification_status="REJECTED",
                    reason_code=_safe_acquisition_reason(error),
                )
            )

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "source_agency": OFFICIAL_SOURCE_AGENCY,
        "official_source_page": OFFICIAL_SOURCE_PAGE,
        "generated_at": stamp,
        "artifacts": entries,
    }
    manifest["manifest_sha256"] = manifest_checksum(manifest)
    _write_json_atomic(manifest_path, manifest)
    return manifest


def verify_artifact(
    path: Path,
    *,
    expected_sha256: str | None = None,
    allow_partial_city_scope: bool = False,
) -> dict[str, Any]:
    """Verify one ZIP without exposing any transaction rows."""

    actual_hash = sha256_file(path)
    if expected_sha256 and actual_hash != expected_sha256.lower():
        return {
            "source_status": "UNAVAILABLE_AUTHORITATIVE",
            "verification_status": "REJECTED",
            "reason_code": "artifact_sha256_mismatch",
            "sha256": actual_hash,
            "byte_size": path.stat().st_size,
        }
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or archive.testzip() is not None:
                raise ArtifactAcquisitionError("invalid_or_corrupt_zip")
            for info in infos:
                member = PurePosixPath(info.filename.replace("\\", "/"))
                if member.is_absolute() or ".." in member.parts:
                    raise ArtifactAcquisitionError("unsafe_zip_member")
            basenames = {PurePosixPath(info.filename).name.lower() for info in infos}
            if "manifest.csv" not in basenames or "schema-main.csv" not in basenames:
                raise ArtifactAcquisitionError("official_manifest_or_schema_missing")
            sale_members = [
                info
                for info in infos
                if city_from_filename(Path(PurePosixPath(info.filename).name))
            ]
            if not sale_members:
                raise ArtifactAcquisitionError("sale_main_files_missing")
            parser_compatible = all(_member_headers_compatible(archive, info) for info in sale_members)
            if not parser_compatible:
                raise ArtifactAcquisitionError("parser_incompatible")
            cities = sorted(
                {
                    city_from_filename(Path(PurePosixPath(info.filename).name))
                    for info in sale_members
                }
            )
            missing_cities = sorted(set(EXPECTED_CITIES) - set(cities))
            source_window = _source_window_description(archive, infos)
    except (OSError, zipfile.BadZipFile, ArtifactAcquisitionError) as error:
        return {
            "source_status": "UNAVAILABLE_AUTHORITATIVE",
            "verification_status": "REJECTED",
            "reason_code": _safe_acquisition_reason(error),
            "sha256": actual_hash,
            "byte_size": path.stat().st_size if path.exists() else 0,
        }
    if missing_cities:
        return {
            "source_status": "PARTIAL_AUTHORITATIVE",
            "verification_status": "VERIFIED" if allow_partial_city_scope else "REJECTED",
            "reason_code": "expected_city_members_missing",
            "coverage_status": "PARTIAL",
            "sha256": actual_hash,
            "byte_size": path.stat().st_size,
            "zip_entry_count": len(infos),
            "sale_main_file_count": len(sale_members),
            "coverage_cities": cities,
            "missing_cities": missing_cities,
            "parser_compatibility": True,
            "source_window_description": source_window,
        }
    return {
        "source_status": "FOUND_AUTHORITATIVE",
        "verification_status": "VERIFIED",
        "reason_code": "",
        "coverage_status": "COMPLETE",
        "sha256": actual_hash,
        "byte_size": path.stat().st_size,
        "zip_entry_count": len(infos),
        "sale_main_file_count": len(sale_members),
        "coverage_cities": cities,
        "missing_cities": [],
        "parser_compatibility": True,
        "source_window_description": source_window,
    }


def build_clean_shadow(
    manifest_path: Path,
    shadow_path: Path,
    *,
    since: str,
    until: str,
    as_of: date,
    allowed_shadow_root: Path,
    normalized_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a deterministic local SQLite shadow from verified artifacts."""

    _validate_period(since)
    _validate_period(until)
    if since > until:
        raise ShadowRebuildError("invalid_rebuild_window")
    if until > current_transaction_period(as_of):
        raise ShadowRebuildError("rebuild_window_exceeds_as_of_period")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ShadowRebuildError("unsupported_artifact_manifest")
    if manifest.get("manifest_sha256") != manifest_checksum(manifest):
        raise ShadowRebuildError("artifact_manifest_checksum_mismatch")
    _assert_shadow_target(shadow_path, allowed_shadow_root)
    entries = [item for item in manifest.get("artifacts", []) if isinstance(item, dict)]
    verified_entries = [item for item in entries if item.get("verification_status") == "VERIFIED"]
    if not verified_entries:
        raise ShadowRebuildError("no_verified_artifacts")
    stamp = (normalized_at or datetime.now(UTC)).astimezone(UTC).isoformat()
    temporary_path = shadow_path.with_name(f"{shadow_path.name}.building-{uuid.uuid4().hex}")
    temporary_path.parent.mkdir(parents=True, exist_ok=True)
    exclusions: Counter[str] = Counter()
    artifact_rejections = len(entries) - len(verified_entries)
    raw_rows = 0
    source_identity_counts: Counter[str] = Counter()

    try:
        connection = sqlite3.connect(temporary_path)
        connection.row_factory = sqlite3.Row
        try:
            _create_shadow_schema(connection)
            for entry in sorted(verified_entries, key=lambda item: int(item.get("sequence") or 0)):
                artifact_path = manifest_path.parent / str(entry.get("local_filename") or "")
                if not artifact_path.is_file():
                    raise ShadowRebuildError("verified_artifact_missing")
                if sha256_file(artifact_path) != str(entry.get("sha256") or ""):
                    raise ShadowRebuildError("verified_artifact_checksum_changed")
                _insert_shadow_artifact(connection, entry)
                with zipfile.ZipFile(artifact_path) as archive:
                    sale_infos = sorted(
                        (
                            info
                            for info in archive.infolist()
                            if city_from_filename(Path(PurePosixPath(info.filename).name))
                        ),
                        key=lambda info: info.filename.lower(),
                    )
                    with tempfile.TemporaryDirectory(prefix="plvr-clean-shadow-") as temp_dir:
                        temp_root = Path(temp_dir)
                        for info in sale_infos:
                            filename = PurePosixPath(info.filename).name
                            extracted = temp_root / filename
                            with archive.open(info) as source, extracted.open("wb") as target:
                                shutil.copyfileobj(source, target, length=1024 * 1024)
                            rows, _encoding = read_csv_rows(extracted)
                            city_hint = city_from_filename(extracted)
                            source_batch: list[dict[str, Any]] = []
                            candidate_batch: list[dict[str, Any]] = []
                            forensic_batch: list[dict[str, Any]] = []
                            for row_number, source_row in enumerate(rows, start=3):
                                raw_rows += 1
                                result = _normalize_shadow_row(
                                    source_row,
                                    artifact=entry,
                                    source_filename=filename,
                                    source_row_number=row_number,
                                    city_hint=city_hint,
                                    since=since,
                                    until=until,
                                    as_of=as_of,
                                    normalized_at=stamp,
                                )
                                exclusions[result["reason_code"]] += int(result["status"] != "candidate")
                                source_identity_counts[result["source_identity"]] += 1
                                source_batch.append(result)
                                if result["status"] == "candidate":
                                    candidate_batch.append(result)
                                elif result["status"] == "forensic":
                                    forensic_batch.append(result)
                                if len(source_batch) >= SHADOW_WRITE_BATCH_SIZE:
                                    _insert_source_rows(connection, source_batch)
                                    _insert_candidates(connection, candidate_batch)
                                    _insert_forensic_transactions(connection, forensic_batch)
                                    source_batch.clear()
                                    candidate_batch.clear()
                                    forensic_batch.clear()
                            _insert_source_rows(connection, source_batch)
                            _insert_candidates(connection, candidate_batch)
                            _insert_forensic_transactions(connection, forensic_batch)
                            extracted.unlink(missing_ok=True)
                            connection.commit()
                connection.commit()
            finalization = _finalize_shadow(connection, entries, since, until, stamp)
            connection.commit()
            integrity = _shadow_integrity_report(connection, as_of)
            if not integrity["invariants_satisfied"]:
                raise ShadowRebuildError("clean_shadow_invariant_failed")
        finally:
            connection.close()
        os.replace(temporary_path, shadow_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    duplicate_source_identities = sum(max(0, count - 1) for count in source_identity_counts.values())
    report = {
        "schema_version": SHADOW_SCHEMA_VERSION,
        "manifest_sha256": manifest["manifest_sha256"],
        "rebuild_window": {"since": since, "until": until, "as_of_date": as_of.isoformat()},
        "artifacts": {
            "required": len(entries),
            "verified": len(verified_entries),
            "rejected_or_missing": artifact_rejections,
            "total_verified_bytes": sum(int(item.get("byte_size") or 0) for item in verified_entries),
        },
        "raw_rows_read": raw_rows,
        "accepted_transaction_rows": finalization["accepted_transaction_rows"],
        "exclusion_reasons": dict(sorted((key, value) for key, value in exclusions.items() if value)),
        "duplicate_source_identities": duplicate_source_identities,
        "business_duplicates": finalization["business_duplicates"],
        "source_identity_conflicts": finalization["source_identity_conflicts"],
        "source_identity_revisions_resolved": finalization["source_identity_revisions_resolved"],
        "cities": finalization["cities"],
        "geographic_units": finalization["geographic_units"],
        "period_min": finalization["period_min"],
        "period_max": finalization["period_max"],
        "coverage": finalization["coverage"],
        "lineage": integrity["lineage"],
        "aggregates": finalization["aggregates"],
        "invariants": integrity["invariants"],
        "invariants_satisfied": integrity["invariants_satisfied"],
        "production_writes": 0,
    }
    report["shadow_dataset_sha256"] = shadow_dataset_checksum(shadow_path)
    report["gate"] = replacement_readiness_gate(report, reconciliation=None)
    return report


def source_row_hash(
    raw_row: Mapping[str, Any],
    *,
    artifact_sha256: str,
    official_transaction_id: str,
    official_transfer_id: str,
) -> str:
    """Bind one canonical raw row serialization to its immutable artifact."""

    clean_row = {
        _normalize_raw_text(key): _normalize_raw_text(value)
        for key, value in raw_row.items()
        if not str(key).startswith("__plvr_")
    }
    return _hash_payload(
        {
            "artifact_sha256": artifact_sha256,
            "official_transaction_id": official_transaction_id,
            "official_transfer_id": official_transfer_id,
            "raw_row": clean_row,
        }
    )


def source_identity(
    *,
    city: str,
    official_transaction_id: str,
    official_transfer_id: str,
    row_hash: str,
) -> str:
    """Return official identity when present, otherwise immutable row identity."""

    serial = official_transaction_id.strip()
    transfer = official_transfer_id.strip()
    if serial or transfer:
        return "official:" + _hash_payload(
            {
                "city": city.replace("臺", "台").strip(),
                "official_transaction_id": serial,
                "official_transfer_id": transfer,
            }
        )
    return f"source-row:{row_hash}"


def reconcile_shadow_rows(
    clean_rows: Sequence[Mapping[str, Any]],
    production_rows: Iterable[Mapping[str, Any]],
    *,
    as_of_period: str,
) -> dict[str, Any]:
    """Reconcile production rows without mutating either dataset."""

    clean_by_key = {str(row.get("business_dedupe_key") or ""): row for row in clean_rows}
    clean_by_fact: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in clean_rows:
        clean_by_fact[_production_fact_hash(row)].append(row)

    authoritative: dict[str, list[tuple[Mapping[str, Any], bool]]] = defaultdict(list)
    probable: Counter[str] = Counter()
    production_only = 0
    future = 0
    supporting: Counter[str] = Counter()
    for production in production_rows:
        period = str(production.get("transaction_period") or "")
        if period > as_of_period:
            future += 1
            continue
        clean = clean_by_key.get(str(production.get("dedupe_key") or ""))
        if clean is None:
            candidates = clean_by_fact.get(_production_fact_hash(production), [])
            proven = [candidate for candidate in candidates if _dedupe_proves_official_identity(production, candidate)]
            if len(proven) == 1:
                clean = proven[0]
            elif len(candidates) == 1:
                probable["probable_only"] += 1
                supporting["PROBABLE_ONLY"] += 1
                continue
            elif len(candidates) > 1:
                probable["conflicting"] += 1
                supporting["CONFLICTING"] += 1
                continue
            else:
                production_only += 1
                supporting["NO_SOURCE_MATCH"] += 1
                continue
        clean_id = str(clean.get("source_identity") or clean.get("source_row_hash") or "")
        geography_matches = _same_region(production, clean)
        authoritative[clean_id].append((production, geography_matches))
        supporting[
            "AUTHORITATIVE_GEOGRAPHY_CORRUPTION_CONFIRMED" if not geography_matches else "AUTHORITATIVE_MATCH"
        ] += 1

    authoritative_matches = 0
    geography_corrupt = 0
    provable_duplicates = 0
    present_clean_ids: set[str] = set()
    corrupt_clean_ids: set[str] = set()
    for clean_id, matches in authoritative.items():
        present_clean_ids.add(clean_id)
        correct = [item for item in matches if item[1]]
        if correct:
            authoritative_matches += 1
        else:
            geography_corrupt += 1
            corrupt_clean_ids.add(clean_id)
        provable_duplicates += max(0, len(matches) - 1)

    clean_identities = {
        str(row.get("source_identity") or row.get("source_row_hash") or "")
        for row in clean_rows
    }
    return {
        "production": {
            "authoritative_matches": authoritative_matches,
            "geography_corrupt_matches": geography_corrupt,
            "provable_duplicates": provable_duplicates,
            "probable_duplicates": probable["probable_only"],
            "production_only": production_only,
            "future_anomalies": future,
            "conflicting": probable["conflicting"],
        },
        "clean": {
            "present_correctly": authoritative_matches,
            "present_but_production_corrupt": len(corrupt_clean_ids),
            "missing_from_production": len(clean_identities - present_clean_ids),
        },
        "supporting_geography": dict(supporting),
    }


class ReadOnlyProductionRepository:
    """Stream production facts through a connection forced to read-only mode."""

    TRANSACTION_SQL = """
    select id, transaction_period, city, district, road, address_text,
           building_type, area_ping, total_price, unit_price_per_ping,
           source, dedupe_key
    from real_price_transactions
    where source = %s
    order by id
    """

    def __init__(self, database_url: str, *, batch_size: int = 2_000) -> None:
        self._database_url = database_url
        self._batch_size = batch_size
        _assert_select_only_sql(self.TRANSACTION_SQL)

    def iter_transactions(self) -> Iterator[Mapping[str, Any]]:
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            self._database_url,
            connect_timeout=20,
            prepare_threshold=None,
            row_factory=dict_row,
            options="-c default_transaction_read_only=on -c statement_timeout=120000",
        )
        cursor = None
        try:
            connection.read_only = True
            cursor = connection.cursor(name="plvr_clean_shadow_reconciliation")
            cursor.execute(self.TRANSACTION_SQL, [OFFICIAL_SOURCE])
            while rows := cursor.fetchmany(self._batch_size):
                yield from rows
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()


def load_clean_rows(shadow_path: Path) -> list[dict[str, Any]]:
    """Load bounded reconciliation fields, never raw source rows."""

    with sqlite3.connect(shadow_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select source_identity, source_row_hash, official_transaction_id,
                   official_transfer_id, business_dedupe_key, transaction_period,
                   city, district, geographic_unit_kind, road, address_text,
                   building_type, area_ping, total_price, unit_price_per_ping,
                   source, production_fact_hash, revision_anchor_hash
            from shadow_transactions
            """
        ).fetchall()
    return [dict(row) for row in rows]


def shadow_dataset_checksum(shadow_path: Path) -> str:
    """Hash deterministic accepted rows and aggregates, excluding build timestamps."""

    digest = hashlib.sha256()
    with sqlite3.connect(shadow_path) as connection:
        for table, columns, order in (
            (
                "shadow_transactions",
                "source_row_hash, source_identity, business_dedupe_key, transaction_period, city, district, "
                "geographic_unit_kind, road, building_type, area_ping, total_price, unit_price_per_ping",
                "source_identity, source_row_hash",
            ),
            (
                "shadow_market_aggregates",
                "county, district, geographic_unit_kind, period, average_unit_price, transaction_count, aggregation_method",
                "county, district, period",
            ),
        ):
            for row in connection.execute(f"select {columns} from {table} order by {order}"):
                digest.update(_canonical_json(list(row)).encode("utf-8"))
                digest.update(b"\n")
    return digest.hexdigest()


def replacement_readiness_gate(
    shadow_report: Mapping[str, Any],
    reconciliation: Mapping[str, Any] | None,
) -> str:
    """Fail closed unless source, lineage, QC, and reconciliation are complete."""

    coverage = shadow_report.get("coverage") or {}
    lineage = shadow_report.get("lineage") or {}
    artifacts = shadow_report.get("artifacts") or {}
    if int(artifacts.get("rejected_or_missing") or 0) > 0:
        return "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    if float(
        coverage.get("expected_official_coverage_percent")
        or coverage.get("complete_percent")
        or 0
    ) < 100:
        return "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    if int(shadow_report.get("source_identity_conflicts") or 0) > 0:
        return "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    if int(lineage.get("rows_missing_artifact_hash") or 0) > 0:
        return "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    if int(lineage.get("rows_missing_source_row_hash") or 0) > 0:
        return "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    if reconciliation is None:
        return "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    production = reconciliation.get("production") or {}
    if int(production.get("production_only") or 0) > 0 or int(production.get("conflicting") or 0) > 0:
        return "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
    return "READY_FOR_SHADOW_CUTOVER_DESIGN"


def manifest_checksum(manifest: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_shadow_row(
    raw_row: Mapping[str, Any],
    *,
    artifact: Mapping[str, Any],
    source_filename: str,
    source_row_number: int,
    city_hint: str,
    since: str,
    until: str,
    as_of: date,
    normalized_at: str,
) -> dict[str, Any]:
    official_id = _raw_value(raw_row, ("編號", "transaction_id"))
    transfer_id = _raw_value(raw_row, ("移轉編號", "transfer_id"))
    raw_date = _raw_value(raw_row, FIELD_ALIASES["transaction_date"])
    raw_period = roc_date_to_period(raw_date)
    row_hash = source_row_hash(
        raw_row,
        artifact_sha256=str(artifact.get("sha256") or ""),
        official_transaction_id=official_id,
        official_transfer_id=transfer_id,
    )
    identity = source_identity(
        city=city_hint,
        official_transaction_id=official_id,
        official_transfer_id=transfer_id,
        row_hash=row_hash,
    )
    base = {
        "artifact_id": str(artifact.get("artifact_id") or ""),
        "artifact_sequence": int(artifact.get("sequence") or 0),
        "artifact_sha256": str(artifact.get("sha256") or ""),
        "artifact_filename": str(artifact.get("local_filename") or ""),
        "source_filename": source_filename,
        "source_row_number": source_row_number,
        "source_row_hash": row_hash,
        "source_identity": identity,
        "source_agency": OFFICIAL_SOURCE_AGENCY,
        "official_transaction_id": official_id,
        "official_transfer_id": transfer_id,
        "raw_transaction_date": raw_date,
        "raw_transaction_period": raw_period,
        "source_city": city_hint,
        "raw_district": _raw_value(raw_row, FIELD_ALIASES["district"]),
        "normalizer_version": NORMALIZER_VERSION,
        "dedupe_algorithm_version": DEDUPE_ALGORITHM_VERSION,
        "normalized_at": normalized_at,
    }
    explicit_city = _raw_value(raw_row, FIELD_ALIASES["city"])
    if explicit_city and not same_city(explicit_city, city_hint):
        return {**base, "status": "rejected", "reason_code": INVALID_CITY_DISTRICT_PAIR}
    normalized, reason = normalize_row(
        dict(raw_row),
        city_hint=city_hint,
        as_of=as_of,
        allow_official_city_level=True,
        allow_future_forensic=True,
    )
    if reason or normalized is None:
        return {**base, "status": "rejected", "reason_code": reason or "normalization_unavailable"}
    unit_kind = str(normalized.get("geographic_unit_kind") or "district")
    region = normalize_market_region(city_hint, str(normalized.get("district") or ""))
    valid_city_level = (
        unit_kind == "city_level"
        and region.valid
        and not region.district
        and region.county in OFFICIAL_CITY_LEVEL_GEOGRAPHIES
    )
    if (not region.valid or not region.district) and not valid_city_level:
        return {**base, "status": "rejected", "reason_code": INVALID_CITY_DISTRICT_PAIR}
    normalized["city"] = region.county
    normalized["district"] = "" if valid_city_level else region.district
    normalized["geographic_unit_kind"] = "city_level" if valid_city_level else "district"
    normalized["dedupe_key"] = build_dedupe_key(normalized, official_id or transfer_id)
    integrity_reason = normalized_row_integrity_reason(
        normalized,
        as_of=as_of,
        allow_official_city_level=True,
    )
    business_fact_hash = _normalized_business_fact_hash(normalized)
    normalized_fields = {
        **base,
        **normalized,
        "business_dedupe_key": str(normalized["dedupe_key"]),
        "business_fact_hash": business_fact_hash,
        "production_fact_hash": _production_fact_hash(normalized),
        "revision_anchor_hash": _revision_anchor_hash(normalized),
    }
    if integrity_reason == FUTURE_TRANSACTION_PERIOD:
        return {
            **normalized_fields,
            "status": "forensic",
            "reason_code": FUTURE_TRANSACTION_PERIOD,
        }
    if integrity_reason:
        return {**base, "status": "rejected", "reason_code": integrity_reason}
    period = str(normalized["transaction_period"])
    if period < since:
        return {**base, "status": "rejected", "reason_code": "outside_rebuild_window_before"}
    if period > until:
        return {**base, "status": "rejected", "reason_code": "outside_rebuild_window_after"}
    return {
        **normalized_fields,
        "status": "candidate",
        "reason_code": "",
    }


def _create_shadow_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        pragma journal_mode = delete;
        pragma synchronous = full;
        create table shadow_artifacts (
            artifact_id text primary key,
            sequence integer not null,
            release text not null,
            kind text not null,
            source_agency text not null,
            sha256 text not null,
            local_filename text not null,
            source_window_description text not null default '',
            retrieved_at text not null
        );
        create table shadow_source_rows (
            artifact_id text not null,
            source_filename text not null,
            source_row_number integer not null,
            source_row_hash text not null,
            source_identity text not null,
            official_transaction_id text not null default '',
            official_transfer_id text not null default '',
            raw_transaction_date text not null default '',
            raw_transaction_period text not null default '',
            source_city text not null,
            raw_district text not null default '',
            assessment_status text not null,
            reason_code text not null default '',
            primary key (artifact_id, source_filename, source_row_number),
            foreign key (artifact_id) references shadow_artifacts(artifact_id)
        );
        create index idx_shadow_source_row_hash on shadow_source_rows(source_row_hash);
        create index idx_shadow_source_identity on shadow_source_rows(source_identity);
        create table shadow_candidate_transactions (
            artifact_id text not null,
            artifact_sequence integer not null,
            artifact_sha256 text not null,
            artifact_filename text not null,
            source_filename text not null,
            source_row_number integer not null,
            source_row_hash text not null,
            source_identity text not null,
            source_agency text not null,
            official_transaction_id text not null default '',
            official_transfer_id text not null default '',
            raw_transaction_date text not null,
            transaction_period text not null,
            city text not null,
            district text not null,
            geographic_unit_kind text not null,
            road text not null,
            address_text text not null default '',
            building_type text not null,
            area_ping real not null,
            building_age_years real not null,
            floor integer not null,
            total_floor integer,
            unit_price_per_ping real not null,
            total_price real not null,
            source text not null,
            business_dedupe_key text not null,
            business_fact_hash text not null,
            production_fact_hash text not null,
            revision_anchor_hash text not null,
            normalizer_version text not null,
            dedupe_algorithm_version text not null,
            normalized_at text not null
        );
        create index idx_shadow_candidate_source_identity
            on shadow_candidate_transactions(source_identity);
        create index idx_shadow_candidate_business_key
            on shadow_candidate_transactions(business_dedupe_key);
        create index idx_shadow_candidate_production_fact
            on shadow_candidate_transactions(production_fact_hash);
        create table shadow_source_conflicts (
            source_identity text primary key,
            conflicting_fact_count integer not null,
            candidate_row_count integer not null,
            revision_anchor_count integer not null,
            resolution_status text not null
        );
        create table shadow_transactions as select * from shadow_candidate_transactions where 0;
        create unique index uq_shadow_transaction_source_row_hash
            on shadow_transactions(source_row_hash);
        create unique index uq_shadow_transaction_business_key
            on shadow_transactions(business_dedupe_key);
        create index idx_shadow_transaction_region_period
            on shadow_transactions(city, district, transaction_period);
        create index idx_shadow_transaction_production_fact
            on shadow_transactions(production_fact_hash);
        create table shadow_forensic_transactions as
            select *, '' as forensic_reason from shadow_candidate_transactions where 0;
        create index idx_shadow_forensic_business_key
            on shadow_forensic_transactions(business_dedupe_key);
        create index idx_shadow_forensic_production_fact
            on shadow_forensic_transactions(production_fact_hash);
        create table shadow_market_aggregates (
            county text not null,
            district text not null,
            geographic_unit_kind text not null,
            period text not null,
            average_unit_price real,
            transaction_count integer not null,
            record_count integer not null,
            source_name text not null,
            coverage_status text not null,
            data_status text not null,
            aggregation_method text not null,
            built_at text not null,
            primary key (county, district, period)
        );
        create table shadow_coverage_matrix (
            county text not null,
            district text not null,
            geographic_unit_kind text not null,
            period text not null,
            coverage_status text not null,
            reason_code text not null,
            primary key (county, district, period)
        );
        """
    )


def _insert_shadow_artifact(connection: sqlite3.Connection, entry: Mapping[str, Any]) -> None:
    connection.execute(
        """
        insert into shadow_artifacts (
            artifact_id, sequence, release, kind, source_agency, sha256,
            local_filename, source_window_description, retrieved_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.get("artifact_id"),
            int(entry.get("sequence") or 0),
            entry.get("release"),
            entry.get("kind"),
            OFFICIAL_SOURCE_AGENCY,
            entry.get("sha256"),
            entry.get("local_filename"),
            entry.get("source_window_description") or "",
            entry.get("retrieved_at"),
        ),
    )


def _insert_source_rows(
    connection: sqlite3.Connection,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    if not rows:
        return
    connection.executemany(
        """
        insert into shadow_source_rows (
            artifact_id, source_filename, source_row_number, source_row_hash,
            source_identity, official_transaction_id, official_transfer_id,
            raw_transaction_date, raw_transaction_period, source_city,
            raw_district, assessment_status, reason_code
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["artifact_id"], row["source_filename"], row["source_row_number"],
                row["source_row_hash"], row["source_identity"], row["official_transaction_id"],
                row["official_transfer_id"], row["raw_transaction_date"],
                row["raw_transaction_period"], row["source_city"], row["raw_district"],
                row["status"], row["reason_code"],
            )
            for row in rows
        ],
    )


def _insert_candidates(
    connection: sqlite3.Connection,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    if not rows:
        return
    columns = (
        "artifact_id", "artifact_sequence", "artifact_sha256", "artifact_filename",
        "source_filename", "source_row_number", "source_row_hash", "source_identity",
        "source_agency", "official_transaction_id", "official_transfer_id",
        "raw_transaction_date", "transaction_period", "city", "district",
        "geographic_unit_kind", "road",
        "address_text", "building_type", "area_ping", "building_age_years", "floor",
        "total_floor", "unit_price_per_ping", "total_price", "source",
        "business_dedupe_key", "business_fact_hash", "production_fact_hash",
        "revision_anchor_hash", "normalizer_version",
        "dedupe_algorithm_version", "normalized_at",
    )
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(
        f"insert into shadow_candidate_transactions ({', '.join(columns)}) values ({placeholders})",
        [tuple(row.get(column) for column in columns) for row in rows],
    )


def _insert_forensic_transactions(
    connection: sqlite3.Connection,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    if not rows:
        return
    columns = (
        "artifact_id", "artifact_sequence", "artifact_sha256", "artifact_filename",
        "source_filename", "source_row_number", "source_row_hash", "source_identity",
        "source_agency", "official_transaction_id", "official_transfer_id",
        "raw_transaction_date", "transaction_period", "city", "district",
        "geographic_unit_kind", "road", "address_text", "building_type", "area_ping",
        "building_age_years", "floor", "total_floor", "unit_price_per_ping", "total_price",
        "source", "business_dedupe_key", "business_fact_hash", "production_fact_hash",
        "revision_anchor_hash", "normalizer_version", "dedupe_algorithm_version",
        "normalized_at", "forensic_reason",
    )
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(
        f"insert into shadow_forensic_transactions ({', '.join(columns)}) values ({placeholders})",
        [
            tuple(
                row.get("reason_code") if column == "forensic_reason" else row.get(column)
                for column in columns
            )
            for row in rows
        ],
    )


def _finalize_shadow(
    connection: sqlite3.Connection,
    manifest_entries: Sequence[Mapping[str, Any]],
    since: str,
    until: str,
    built_at: str,
) -> dict[str, Any]:
    connection.executescript(
        """
        insert into shadow_source_conflicts (
            source_identity, conflicting_fact_count, candidate_row_count,
            revision_anchor_count, resolution_status
        )
        select source_identity, count(distinct business_fact_hash), count(*),
               count(distinct revision_anchor_hash),
               case when count(distinct revision_anchor_hash) = 1
                    then 'RESOLVED_OFFICIAL_REVISION'
                    else 'UNRESOLVED'
               end
        from shadow_candidate_transactions
        where official_transaction_id <> '' or official_transfer_id <> ''
        group by source_identity
        having count(distinct business_fact_hash) > 1;

        insert into shadow_transactions
        select artifact_id, artifact_sequence, artifact_sha256, artifact_filename,
               source_filename, source_row_number, source_row_hash, source_identity,
               source_agency, official_transaction_id, official_transfer_id,
               raw_transaction_date, transaction_period, city, district,
               geographic_unit_kind, road, address_text, building_type, area_ping,
               building_age_years, floor, total_floor, unit_price_per_ping,
               total_price, source, business_dedupe_key, business_fact_hash,
               production_fact_hash, revision_anchor_hash, normalizer_version,
               dedupe_algorithm_version, normalized_at
        from (
            select candidate.*,
                   row_number() over (
                       partition by case
                           when exists (
                               select 1 from shadow_source_conflicts conflict
                               where conflict.source_identity = candidate.source_identity
                                 and conflict.resolution_status = 'RESOLVED_OFFICIAL_REVISION'
                           ) then 'source:' || source_identity
                           else 'business:' || business_dedupe_key
                       end
                       order by artifact_sequence desc, source_row_hash
                   ) as business_rank
            from shadow_candidate_transactions candidate
            where not exists (
                select 1 from shadow_source_conflicts conflict
                where conflict.source_identity = candidate.source_identity
                  and conflict.resolution_status = 'UNRESOLVED'
            )
        ) ranked
        where business_rank = 1;
        """
    )
    coverage = _build_coverage_matrix(connection, manifest_entries, since, until)
    connection.execute(
        """
        insert into shadow_market_aggregates (
            county, district, geographic_unit_kind, period, average_unit_price,
            transaction_count, record_count, source_name, coverage_status,
            data_status, aggregation_method, built_at
        )
        select city, district, geographic_unit_kind, transaction_period,
               round(avg(unit_price_per_ping), 2), count(*), count(*), ?,
               coalesce((
                   select matrix.coverage_status
                   from shadow_coverage_matrix matrix
                   where matrix.county = shadow_transactions.city
                     and matrix.period = shadow_transactions.transaction_period
                   limit 1
               ), 'PARTIAL'),
               'available', ?, ?
        from shadow_transactions
        group by city, district, geographic_unit_kind, transaction_period
        """,
        (PLVR_MARKET_SOURCE_NAME, PLVR_AGGREGATION_METHOD, built_at),
    )
    candidate_count = int(connection.execute("select count(*) from shadow_candidate_transactions").fetchone()[0])
    accepted = int(connection.execute("select count(*) from shadow_transactions").fetchone()[0])
    unresolved_conflict_rows = int(
        connection.execute(
            """
            select count(*) from shadow_candidate_transactions candidate
            where exists (
                select 1 from shadow_source_conflicts conflict
                where conflict.source_identity = candidate.source_identity
                  and conflict.resolution_status = 'UNRESOLVED'
            )
            """
        ).fetchone()[0]
    )
    revision_rows_superseded = int(
        connection.execute(
            """
            select coalesce(sum(candidate_row_count - 1), 0)
            from shadow_source_conflicts
            where resolution_status = 'RESOLVED_OFFICIAL_REVISION'
            """
        ).fetchone()[0]
    )
    conflicts = int(
        connection.execute(
            "select count(*) from shadow_source_conflicts where resolution_status = 'UNRESOLVED'"
        ).fetchone()[0]
    )
    revisions = int(
        connection.execute(
            "select count(*) from shadow_source_conflicts where resolution_status = 'RESOLVED_OFFICIAL_REVISION'"
        ).fetchone()[0]
    )
    aggregate_row = connection.execute(
        """
        select count(*), count(distinct county), count(distinct county || '|' || district),
               min(period), max(period)
        from shadow_market_aggregates
        """
    ).fetchone()
    cities = [row[0] for row in connection.execute("select distinct city from shadow_transactions order by city")]
    geographic_units = int(
        connection.execute(
            "select count(distinct city || '|' || district || '|' || geographic_unit_kind) from shadow_transactions"
        ).fetchone()[0]
    )
    return {
        "accepted_transaction_rows": accepted,
        "business_duplicates": max(
            0,
            candidate_count - unresolved_conflict_rows - revision_rows_superseded - accepted,
        ),
        "source_identity_conflicts": conflicts,
        "source_identity_revisions_resolved": revisions,
        "cities": cities,
        "geographic_units": geographic_units,
        "period_min": aggregate_row[3],
        "period_max": aggregate_row[4],
        "coverage": coverage,
        "aggregates": {
            "transaction_rows": accepted,
            "aggregate_rows": int(aggregate_row[0] or 0),
            "cities": int(aggregate_row[1] or 0),
            "districts": int(aggregate_row[2] or 0),
            "period_min": aggregate_row[3],
            "period_max": aggregate_row[4],
        },
    }


def _build_coverage_matrix(
    connection: sqlite3.Connection,
    manifest_entries: Sequence[Mapping[str, Any]],
    since: str,
    until: str,
) -> dict[str, Any]:
    report = build_coverage_report({"artifacts": list(manifest_entries)}, since=since, until=until)
    for cell in report["matrix"]:
        region = normalize_market_region(str(cell["city"]))
        if not region.valid:
            raise ShadowRebuildError("coverage_city_not_canonical")
        connection.execute(
            "insert into shadow_coverage_matrix values (?, ?, ?, ?, ?, ?)",
            (
                region.county,
                "",
                "city_scope",
                cell["period"],
                cell["coverage_state"],
                cell["reason_code"],
            ),
        )
    counts = report["counts"]
    return {
        "complete": counts["COMPLETE"],
        "partial": counts["PARTIAL"],
        "missing": counts["MISSING"],
        "not_expected": counts["NOT_YET_EXPECTED"],
        "not_yet_expected": counts["NOT_YET_EXPECTED"],
        "not_applicable": counts["NOT_APPLICABLE"],
        "total": report["calendar_scope_count"],
        "complete_percent": report["expected_official_coverage_percent"],
        "raw_calendar_coverage_percent": report["raw_calendar_coverage_percent"],
        "expected_official_coverage_percent": report["expected_official_coverage_percent"],
        "expected_scope_count": report["expected_scope_count"],
        "complete_through": report["complete_through"],
        "expected_release_ceiling": report["expected_release_ceiling"],
        "basis": report["basis"],
        "artifact_scope_audit": report["artifact_scope_audit"],
    }


def _shadow_integrity_report(connection: sqlite3.Connection, as_of: date) -> dict[str, Any]:
    row = connection.execute(
        """
        select count(*) as rows,
               count(*) filter (where artifact_sha256 = '') as missing_artifact,
               count(*) filter (where source_row_hash = '') as missing_row_hash,
               count(*) filter (
                   where official_transaction_id = '' and official_transfer_id = ''
               ) as missing_official_id,
               count(*) filter (where transaction_period > ?) as future_rows,
               count(*) filter (where source <> ?) as unsupported_source
        from shadow_transactions
        """,
        (current_transaction_period(as_of), OFFICIAL_SOURCE),
    ).fetchone()
    invalid_geography = 0
    for city, district, unit_kind in connection.execute(
        "select distinct city, district, geographic_unit_kind from shadow_transactions"
    ):
        region = normalize_market_region(str(city), str(district))
        valid_city_level = (
            str(unit_kind) == "city_level"
            and region.valid
            and not region.district
            and region.county in OFFICIAL_CITY_LEVEL_GEOGRAPHIES
        )
        invalid_geography += int((not region.valid or not region.district) and not valid_city_level)
    future_aggregates = int(
        connection.execute(
            "select count(*) from shadow_market_aggregates where period > ?",
            (current_transaction_period(as_of),),
        ).fetchone()[0]
    )
    lineage = {
        "accepted_rows": int(row[0]),
        "rows_with_artifact_hash": int(row[0]) - int(row[1]),
        "rows_with_source_row_hash": int(row[0]) - int(row[2]),
        "rows_with_official_id": int(row[0]) - int(row[3]),
        "rows_missing_identity": int(row[3]),
        "rows_missing_artifact_hash": int(row[1]),
        "rows_missing_source_row_hash": int(row[2]),
    }
    invariants = {
        "every_row_has_artifact_hash": int(row[1]) == 0,
        "every_row_has_source_row_hash": int(row[2]) == 0,
        "canonical_invalid_geography": invalid_geography,
        "publishable_future_rows": int(row[4]),
        "publishable_future_aggregates": future_aggregates,
        "unsupported_source_rows": int(row[5]),
        "sale_main_only": True,
    }
    return {
        "lineage": lineage,
        "invariants": invariants,
        "invariants_satisfied": all(
            (
                invariants["every_row_has_artifact_hash"],
                invariants["every_row_has_source_row_hash"],
                invalid_geography == 0,
                int(row[4]) == 0,
                future_aggregates == 0,
                int(row[5]) == 0,
            )
        ),
    }


def _member_headers_compatible(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bool:
    with archive.open(info) as member:
        first_line = member.readline()
    header_text = ""
    for encoding in ENCODINGS:
        try:
            header_text = first_line.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not header_text:
        return False
    headers = set(next(csv.reader([header_text]), []))
    return all(any(alias in headers for alias in FIELD_ALIASES[field]) for field in REQUIRED_HEADER_GROUPS)


def _source_window_description(archive: zipfile.ZipFile, infos: Sequence[zipfile.ZipInfo]) -> str:
    build_info = next(
        (info for info in infos if PurePosixPath(info.filename).name.lower() == "build_time.xml"),
        None,
    )
    if build_info is None:
        return ""
    payload = archive.read(build_info)
    text = ""
    for encoding in ENCODINGS:
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    match = re.search(r"<lvr_time>(.*?)</lvr_time>", text, re.DOTALL)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _manifest_entry(
    request: ArtifactRequest,
    *,
    sequence: int,
    retrieved_at: str,
    metadata: HttpMetadata | None = None,
    **values: Any,
) -> dict[str, Any]:
    metadata = metadata or HttpMetadata(0, request.download_source)
    original_filename = _content_disposition_filename(metadata.content_disposition)
    return {
        **asdict(request),
        "sequence": sequence,
        "source_agency": OFFICIAL_SOURCE_AGENCY,
        "official_source_page": OFFICIAL_SOURCE_PAGE,
        "original_filename": original_filename or request.local_filename,
        "retrieved_at": retrieved_at,
        "content_type": metadata.content_type,
        "http_status": metadata.status_code,
        "http_content_length": metadata.content_length,
        "http_last_modified": metadata.last_modified,
        "http_etag": metadata.etag,
        **values,
    }


def _response_metadata(response: Any) -> HttpMetadata:
    headers = response.headers
    length = headers.get("Content-Length")
    content_range = str(headers.get("Content-Range") or "")
    range_match = re.fullmatch(r"bytes\s+\d+-\d+/(\d+)", content_range, re.IGNORECASE)
    if range_match:
        length = range_match.group(1)
    status_code = getattr(response, "status_code", None)
    if status_code is None:
        status_code = getattr(response, "status", None)
    if status_code is None:
        status_code = response.getcode()
    final_url = getattr(response, "url", None)
    if final_url is None:
        final_url = response.geturl()
    return HttpMetadata(
        status_code=int(status_code),
        final_url=str(final_url),
        content_type=str(headers.get("Content-Type") or ""),
        content_length=int(length) if length and str(length).isdigit() else None,
        last_modified=str(headers.get("Last-Modified") or ""),
        etag=str(headers.get("ETag") or ""),
        content_disposition=str(headers.get("Content-Disposition") or ""),
    )


def _official_tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    # The official PLVR chain lacks a legacy extension required by OpenSSL's
    # strict mode. Chain and hostname verification remain mandatory.
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _validate_official_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in OFFICIAL_DOWNLOAD_HOSTS:
        raise ArtifactAcquisitionError("source_not_authoritative")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ArtifactAcquisitionError("source_not_authoritative")


def _content_disposition_filename(value: str) -> str:
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", value or "", re.IGNORECASE)
    return Path(urllib.parse.unquote(match.group(1).strip())).name if match else ""


def _safe_acquisition_reason(error: Exception) -> str:
    if isinstance(error, ArtifactAcquisitionError):
        return str(error)
    return "artifact_transport_unavailable"


def _read_manifest_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ArtifactAcquisitionError("existing_manifest_invalid")
    return payload if isinstance(payload, dict) else {}


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.partial-{uuid.uuid4().hex}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _assert_direct_child(parent: Path, child: Path) -> None:
    if child.resolve().parent != parent.resolve() or child.name in {"", ".", ".."}:
        raise ArtifactAcquisitionError("unsafe_artifact_destination")


def _assert_shadow_target(path: Path, allowed_root: Path) -> None:
    raw = str(path)
    if "://" in raw or path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ShadowRebuildError("local_sqlite_shadow_required")
    resolved_root = allowed_root.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ShadowRebuildError("shadow_target_outside_allowed_root")
    if "production" in path.name.lower():
        raise ShadowRebuildError("production_target_forbidden")


def _raw_value(row: Mapping[str, Any], aliases: Iterable[str]) -> str:
    for alias in aliases:
        value = row.get(alias)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_raw_text(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value or "")).strip()


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _normalized_business_fact_hash(row: Mapping[str, Any]) -> str:
    return _hash_payload(
        {
            "source": str(row.get("source") or OFFICIAL_SOURCE),
            "city": str(row.get("city") or "").replace("臺", "台").strip(),
            "district": str(row.get("district") or "").strip(),
            "transaction_period": str(row.get("transaction_period") or "").strip(),
            "address_text": re.sub(r"\s+", "", str(row.get("address_text") or "")),
            "road": re.sub(r"\s+", "", str(row.get("road") or "")),
            "building_type": re.sub(r"\s+", "", str(row.get("building_type") or "")),
            "area_ping": f"{float(row.get('area_ping') or 0):.2f}",
            "total_price": f"{float(row.get('total_price') or 0):.2f}",
            "unit_price_per_ping": f"{float(row.get('unit_price_per_ping') or 0):.2f}",
            "floor": int(row.get("floor") or 0),
            "total_floor": int(row.get("total_floor") or 0),
        }
    )


def _production_fact_hash(row: Mapping[str, Any]) -> str:
    return _hash_payload(
        {
            "source": str(row.get("source") or OFFICIAL_SOURCE),
            "transaction_period": str(row.get("transaction_period") or "").strip(),
            "address_text": re.sub(r"\s+", "", str(row.get("address_text") or "")),
            "road": re.sub(r"\s+", "", str(row.get("road") or "")),
            "building_type": re.sub(r"\s+", "", str(row.get("building_type") or "")),
            "area_ping": f"{float(row.get('area_ping') or 0):.2f}",
            "total_price": f"{float(row.get('total_price') or 0):.2f}",
            "unit_price_per_ping": f"{float(row.get('unit_price_per_ping') or 0):.2f}",
            "floor": int(row.get("floor") or 0),
            "total_floor": int(row.get("total_floor") or 0),
        }
    )


def _revision_anchor_hash(row: Mapping[str, Any]) -> str:
    """Bind immutable transaction facts while allowing official corrections."""

    return _hash_payload(
        {
            "source": str(row.get("source") or OFFICIAL_SOURCE),
            "transaction_period": str(row.get("transaction_period") or "").strip(),
            "city": str(row.get("city") or "").replace("臺", "台").strip(),
            "district": str(row.get("district") or "").strip(),
            "address_fingerprint": hashlib.sha256(
                re.sub(r"\s+", "", str(row.get("address_text") or "")).encode("utf-8")
            ).hexdigest(),
            "building_type": re.sub(r"\s+", "", str(row.get("building_type") or "")),
            "floor": int(row.get("floor") or 0),
            "total_floor": int(row.get("total_floor") or 0),
        }
    )


def _dedupe_proves_official_identity(
    production: Mapping[str, Any],
    clean: Mapping[str, Any],
) -> bool:
    official_id = str(clean.get("official_transaction_id") or clean.get("official_transfer_id") or "")
    persisted = str(production.get("dedupe_key") or "")
    return bool(official_id and persisted and build_dedupe_key(dict(production), official_id) == persisted)


def _same_region(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_region = normalize_market_region(str(left.get("city") or ""), str(left.get("district") or ""))
    right_region = normalize_market_region(str(right.get("city") or ""), str(right.get("district") or ""))
    return (
        left_region.valid
        and right_region.valid
        and left_region.county == right_region.county
        and left_region.district == right_region.district
    )


def _latest_settled_period(entries: Sequence[Mapping[str, Any]]) -> str:
    periods: list[str] = []
    for entry in entries:
        match = SEASON_PATTERN.fullmatch(str(entry.get("release") or ""))
        if not match:
            continue
        year = int(match.group("year")) + 1911
        quarter = int(match.group("quarter"))
        end_month = quarter * 3
        settled_month = end_month - 1
        periods.append(f"{year:04d}-{settled_month:02d}")
    return max(periods, default="")


def _iter_periods(since: str, until: str) -> Iterator[str]:
    year, month = map(int, since.split("-"))
    end_year, end_month = map(int, until.split("-"))
    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def _validate_period(value: str) -> None:
    if not PERIOD_PATTERN.fullmatch(value):
        raise ShadowRebuildError("invalid_period")


def _assert_select_only_sql(sql: str) -> None:
    compact = re.sub(r"\s+", " ", sql).strip().lower()
    if not compact.startswith("select "):
        raise ShadowRebuildError("production_query_not_select_only")
    forbidden = (" insert ", " update ", " delete ", " upsert ", " truncate ", " drop ", " alter ", " create ")
    padded = f" {compact} "
    if any(token in padded for token in forbidden):
        raise ShadowRebuildError("production_query_not_select_only")
