"""Archive raw monthly RIS ODRP014 responses to R2 (source-of-truth).

This module archives the *raw* API response per page — not the Phase 2B
adapter's canonical rows — so that if the schema adapter changes later, the
original bytes can be re-processed. It is I/O-capable but keeps all external
dependencies injected:

* ``page_fetcher(url, page) -> dict`` returns the parsed JSON of one page.
* an R2/S3-style ``client`` exposing ``head_object`` / ``put_object`` /
  ``get_object`` is passed in by the operator script and mocked in tests.

Design guarantees:

* Raw pages preserve official field names and metadata verbatim.
* Page JSON is serialized deterministically (sorted keys, compact separators,
  ``ensure_ascii=False``) so the same response always produces the same bytes
  and the same SHA-256.
* Pagination enforces the same fail-closed contract as the provider
  (responseCode, page-number echo, stable totals, row-count == totalDataSize,
  duplicate-page rejection, hard max pages).
* Raw archive objects are immutable: an existing object is HEAD-checked; a
  byte-identical object (size + stored sha256 metadata + downloaded bytes) is
  skipped; a same-key object with a different checksum fails closed and is
  never overwritten.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Protocol

from services.ris_population_dataset import roc_yyymm_to_gregorian
from services.ris_population_provider import (
    FIRST_PAGE,
    PAGE_PARAM,
    RESPONSE_CODE_NO_MORE_DATA,
    RESPONSE_CODE_SUCCESS,
    RisPaginationError,
    RisResponseCodeError,
    RisSchemaError,
    _coerce_int,
    build_dataset_url,
)

DATASET = "ODRP014"
PROVIDER = "moi_ris"
MANIFEST_SCHEMA_VERSION = "ris-raw-archive-manifest-v1"
KEY_PREFIX = "raw/ris/population"
SHA256_METADATA_KEY = "sha256"
DEFAULT_MAX_PAGES = 64

# Raw-schema markers (mirror the adapter's, but used only to *label* the month,
# never to mutate the archived bytes).
_CHINESE_MARKERS = {"統計年月", "區域別代碼", "區域別", "村里"}
_ENGLISH_MARKERS = {"statistic_yyymm", "district_code", "site_id", "village"}


class ObjectStore(Protocol):
    """Minimal S3/R2 client surface used by the archiver (injected/mocked)."""

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]: ...

    def put_object(
        self, *, Bucket: str, Key: str, Body: bytes, ContentType: str, Metadata: dict[str, str]
    ) -> dict[str, Any]: ...

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]: ...


PageFetcher = Callable[[str, int], dict[str, Any]]
ProgressCallback = Callable[[str], None]


class RisArchiveError(RuntimeError):
    """Base error for archival failures."""


class RisArchiveImmutabilityError(RisArchiveError):
    """A same-key object exists with a different checksum; never overwrite."""


class RisArchiveVerificationError(RisArchiveError):
    """A remote object failed strict HEAD/GET checksum verification."""


# --- deterministic serialization ----------------------------------------

def serialize_page(payload: dict[str, Any]) -> bytes:
    """Serialize a raw page payload to deterministic UTF-8 JSON bytes."""

    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_schema_style(payload: dict[str, Any]) -> str:
    rd = payload.get("responseData")
    if not isinstance(rd, list) or not rd or not isinstance(rd[0], dict):
        return "unknown"
    keys = set(rd[0].keys())
    has_zh = bool(keys & _CHINESE_MARKERS)
    has_en = bool(keys & _ENGLISH_MARKERS)
    if has_zh and has_en:
        return "bilingual/mixed"
    if has_zh:
        return "chinese"
    if has_en:
        return "english"
    return "unknown"


# --- raw page collection (preserves source-of-truth) ---------------------

def collect_raw_pages(
    yyymm: str,
    page_fetcher: PageFetcher,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Fetch every page's raw payload for a month, enforcing the RIS contract.

    Returns ``{"yyymm", "url", "pages": [raw payload, ...], "total_data_size",
    "total_page", "schema_style"}``. Raw payloads are returned unmodified.
    """

    url = build_dataset_url(yyymm)
    pages: list[dict[str, Any]] = []
    seen_pages: set[int] = set()
    total_data_size: int | None = None
    total_page: int | None = None
    row_count = 0

    page = FIRST_PAGE
    while page <= max_pages:
        payload = page_fetcher(url, page)
        if not isinstance(payload, dict):
            raise RisSchemaError(f"page {page}: payload is not a JSON object")

        code = payload.get("responseCode")
        if code == RESPONSE_CODE_NO_MORE_DATA:
            break
        if code != RESPONSE_CODE_SUCCESS:
            raise RisResponseCodeError(
                f"page {page}: unexpected responseCode {code!r} "
                f"(message: {payload.get('responseMessage')!r})"
            )
        if page in seen_pages:
            raise RisPaginationError(f"duplicate page {page} received; failing closed")
        seen_pages.add(page)

        reported_page = _coerce_int(payload.get("page"), "page")
        if reported_page != page:
            raise RisPaginationError(
                f"requested page {page} but server reported page {reported_page}"
            )

        page_total = _coerce_int(payload.get("totalDataSize"), "totalDataSize")
        page_total_page = _coerce_int(payload.get("totalPage"), "totalPage")
        if total_data_size is None:
            total_data_size = page_total
            total_page = page_total_page
        else:
            if page_total != total_data_size:
                raise RisPaginationError(
                    f"totalDataSize changed across pages: {total_data_size} -> {page_total}"
                )
            if page_total_page != total_page:
                raise RisPaginationError(
                    f"totalPage changed across pages: {total_page} -> {page_total_page}"
                )

        rd = payload.get("responseData")
        if not isinstance(rd, list):
            raise RisSchemaError(f"page {page}: responseData must be a list")
        row_count += len(rd)
        pages.append(payload)
        if progress is not None:
            progress(f"fetch page {page}/{total_page}")

        if total_page is not None and page >= total_page:
            break
        page += 1
    else:
        raise RisPaginationError(
            f"exceeded hard maximum of {max_pages} pages without completing collection"
        )

    if total_data_size is None:
        raise RisPaginationError("no successful data page was returned")
    if row_count != total_data_size:
        raise RisPaginationError(
            f"collected {row_count} rows but server reported totalDataSize "
            f"{total_data_size}; failing closed"
        )

    return {
        "yyymm": str(yyymm).strip(),
        "url": url,
        "pages": pages,
        "total_data_size": total_data_size,
        "total_page": total_page,
        "schema_style": classify_schema_style(pages[0]) if pages else "unknown",
    }


# --- keys / manifest ------------------------------------------------------

def month_prefix(gregorian: str) -> str:
    return f"{KEY_PREFIX}/{gregorian}"


def page_key(gregorian: str, page_number: int) -> str:
    return f"{month_prefix(gregorian)}/page-{page_number:03d}.json"


def manifest_key(gregorian: str) -> str:
    return f"{month_prefix(gregorian)}/manifest.json"


def build_page_artifacts(collected: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-page artifacts: number, key, bytes, byte_size, sha256."""

    gregorian = roc_yyymm_to_gregorian(collected["yyymm"])
    artifacts = []
    for index, payload in enumerate(collected["pages"], start=FIRST_PAGE):
        data = serialize_page(payload)
        artifacts.append(
            {
                "page": index,
                "object_key": page_key(gregorian, index),
                "bytes": data,
                "byte_size": len(data),
                "sha256": sha256_hex(data),
            }
        )
    return artifacts


def build_manifest(
    collected: dict[str, Any],
    page_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    yyymm = collected["yyymm"]
    gregorian = roc_yyymm_to_gregorian(yyymm)
    total_bytes = sum(a["byte_size"] for a in page_artifacts)
    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": DATASET,
        "provider": PROVIDER,
        "statistic_yyymm": yyymm,
        "statistic_month": gregorian,
        "source_endpoint": collected["url"],
        "pages": len(page_artifacts),
        "total_data_size": collected["total_data_size"],
        "schema_style": collected["schema_style"],
        "page_files": [
            {
                "page_number": a["page"],
                "object_key": a["object_key"],
                "byte_size": a["byte_size"],
                "sha256": a["sha256"],
            }
            for a in page_artifacts
        ],
        "total_archived_bytes": total_bytes,
    }


def serialize_manifest(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


# --- immutable upload + verify -------------------------------------------

def _head_or_none(client: ObjectStore, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001
        # boto3 raises ClientError with a 404/NoSuchKey; treat "not found" as
        # absent, but re-raise anything that is not a not-found signal.
        if _is_not_found(exc):
            return None
        raise


def _is_not_found(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = str(response.get("Error", {}).get("Code", ""))
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code in {"404", "NoSuchKey", "NotFound"} or status == 404:
            return True
    return exc.__class__.__name__ in {"NoSuchKey", "NotFound", "404"}


def put_object_immutable(
    client: ObjectStore,
    bucket: str,
    key: str,
    data: bytes,
    checksum: str,
    *,
    content_type: str = "application/json",
    metadata: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Upload one object with immutability semantics.

    * If no object exists: upload (or, in dry-run, report ``planned``).
    * If an object exists with matching size + stored sha256 metadata: ``skip``.
    * If an object exists with a different checksum: raise
      :class:`RisArchiveImmutabilityError` (never overwrite).

    In ``dry_run`` mode no remote call is made (``client`` may be ``None``): the
    action is always reported as ``planned``.
    """

    if dry_run:
        return {"key": key, "action": "planned", "byte_size": len(data), "sha256": checksum}

    head = _head_or_none(client, bucket, key)
    if head is not None:
        remote_len = head.get("ContentLength")
        remote_sha = (head.get("Metadata") or {}).get(SHA256_METADATA_KEY)
        if remote_len == len(data) and remote_sha == checksum:
            return {"key": key, "action": "skip", "byte_size": len(data), "sha256": checksum}
        raise RisArchiveImmutabilityError(
            f"object {key!r} already exists with a different checksum "
            f"(remote size={remote_len}, remote sha256={remote_sha!r}); refusing to overwrite"
        )

    object_metadata = dict(metadata or {})
    object_metadata[SHA256_METADATA_KEY] = checksum
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        Metadata=object_metadata,
    )
    return {"key": key, "action": "upload", "byte_size": len(data), "sha256": checksum}


def verify_object(client: ObjectStore, bucket: str, key: str, expected_size: int, expected_sha256: str) -> dict[str, Any]:
    """HEAD (ContentLength) + GET (download & re-hash) verification."""

    head = client.head_object(Bucket=bucket, Key=key)
    head_len = head.get("ContentLength")
    if head_len != expected_size:
        raise RisArchiveVerificationError(
            f"object {key!r} HEAD size mismatch: expected {expected_size}, got {head_len}"
        )
    metadata_sha = (head.get("Metadata") or {}).get(SHA256_METADATA_KEY)
    if metadata_sha != expected_sha256:
        raise RisArchiveVerificationError(
            f"object {key!r} metadata sha256 mismatch: "
            f"expected {expected_sha256}, got {metadata_sha!r}"
        )

    obj = client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"]
    data = body.read() if hasattr(body, "read") else body
    actual_sha = sha256_hex(data)
    if actual_sha != expected_sha256:
        raise RisArchiveVerificationError(
            f"object {key!r} GET sha256 mismatch: "
            f"expected {expected_sha256}, got {actual_sha}"
        )

    return {
        "key": key,
        "content_length_match": True,
        "metadata_sha256_match": True,
        "sha256_match": True,
        "verified": True,
    }


def archive_month(
    yyymm: str,
    page_fetcher: PageFetcher,
    client: ObjectStore,
    bucket: str,
    *,
    dry_run: bool = False,
    max_pages: int = DEFAULT_MAX_PAGES,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Archive one RIS month: collect raw pages, upload pages + manifest, verify.

    Returns a per-month result dict with object actions, verification results,
    byte totals, and ``all_objects_verified``. In ``dry_run`` mode no object is
    written and no verification is performed (planned actions only).
    """

    gregorian = roc_yyymm_to_gregorian(yyymm)
    if progress is not None:
        progress(f"{gregorian} START")
    collected = collect_raw_pages(
        yyymm, page_fetcher, max_pages=max_pages, progress=progress
    )
    page_artifacts = build_page_artifacts(collected)
    manifest = build_manifest(collected, page_artifacts)
    manifest_bytes = serialize_manifest(manifest)
    manifest_sha = sha256_hex(manifest_bytes)
    m_key = manifest_key(gregorian)
    object_metadata = {
        "provider": "ris",
        "dataset": "odrp014-population",
        "statistic_yyymm": yyymm,
    }

    actions: list[dict[str, Any]] = []
    verifications: list[dict[str, Any]] = []
    all_verified = True
    if progress is not None:
        progress("page objects upload/verify")
    for a in page_artifacts:
        action = put_object_immutable(
            client,
            bucket,
            a["object_key"],
            a["bytes"],
            a["sha256"],
            metadata=object_metadata,
            dry_run=dry_run,
        )
        actions.append(action)
        if not dry_run:
            verifications.append(
                verify_object(
                    client, bucket, a["object_key"], a["byte_size"], a["sha256"]
                )
            )
    if progress is not None:
        progress("manifest upload/verify")
    manifest_action = put_object_immutable(
        client,
        bucket,
        m_key,
        manifest_bytes,
        manifest_sha,
        metadata=object_metadata,
        dry_run=dry_run,
    )
    actions.append(manifest_action)

    if not dry_run:
        v = verify_object(client, bucket, m_key, len(manifest_bytes), manifest_sha)
        verifications.append(v)
        all_verified = all(v["verified"] for v in verifications)

    uploaded = sum(1 for a in actions if a["action"] == "upload")
    skipped = sum(1 for a in actions if a["action"] == "skip")
    planned = sum(1 for a in actions if a["action"] == "planned")

    return {
        "yyymm": yyymm,
        "statistic_month": gregorian,
        "schema_style": collected["schema_style"],
        "pages": len(page_artifacts),
        "total_data_size": collected["total_data_size"],
        "manifest_key": m_key,
        "object_keys": [a["object_key"] for a in page_artifacts] + [m_key],
        "actions": actions,
        "objects_uploaded": uploaded,
        "objects_skipped": skipped,
        "objects_planned": planned,
        "total_archived_bytes": manifest["total_archived_bytes"],
        "manifest_bytes": len(manifest_bytes),
        "verifications": verifications,
        "all_objects_verified": all_verified if not dry_run else None,
        "dry_run": dry_run,
    }
