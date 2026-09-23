"""Verified R2 archive to PostgreSQL ingestion for monthly RIS demographics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import re
import time
from typing import Any, Callable, Mapping, Sequence

from services.ris_population_archive import (
    DATASET,
    MANIFEST_SCHEMA_VERSION,
    PROVIDER,
    SHA256_METADATA_KEY,
    ObjectStore,
    RisArchiveVerificationError,
    manifest_key,
    page_key,
    sha256_hex,
)
from services.ris_population_dataset import normalize_rows, roc_yyymm_to_gregorian
from services.ris_population_provider import (
    RESPONSE_CODE_SUCCESS,
    normalize_source_row_schema,
)


RIS_ADVISORY_LOCK_NAMESPACE = 0x524953
DEFAULT_BATCH_SIZE = 500
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_COUNT_FIELDS = (
    "household_count",
    "total_population",
    "male_population",
    "female_population",
    "age_0_14",
    "age_15_64",
    "age_65_plus",
)
_UNIT_RATIO_FIELDS = ("child_ratio", "working_age_ratio", "elderly_ratio")
_IDENTITY_FIELDS = ("statistic_yyymm", "district_code", "site_id", "village")


class RisPopulationIngestionError(RuntimeError):
    """Archive or normalized rows violate the all-or-nothing month contract."""


@dataclass(frozen=True)
class PreparedRisMonth:
    statistic_yyymm: str
    statistic_month: date
    rows_source: int
    rows_normalized: int
    rows: tuple[dict[str, Any], ...]


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise RisPopulationIngestionError(f"{field} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RisPopulationIngestionError(f"{field} must be an integer") from exc
    return parsed


def _read_verified_object(
    client: ObjectStore,
    bucket: str,
    key: str,
    *,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    head = client.head_object(Bucket=bucket, Key=key)
    size = _integer(head.get("ContentLength"), f"{key} ContentLength")
    metadata_sha = str((head.get("Metadata") or {}).get(SHA256_METADATA_KEY, ""))
    if not _SHA256.fullmatch(metadata_sha):
        raise RisArchiveVerificationError(f"object {key!r} has invalid sha256 metadata")
    if expected_size is not None and size != expected_size:
        raise RisArchiveVerificationError(
            f"object {key!r} HEAD size mismatch: expected {expected_size}, got {size}"
        )
    if expected_sha256 is not None and metadata_sha != expected_sha256:
        raise RisArchiveVerificationError(
            f"object {key!r} metadata sha256 mismatch: expected {expected_sha256}, got {metadata_sha}"
        )

    remote = client.get_object(Bucket=bucket, Key=key)["Body"]
    data = remote.read() if hasattr(remote, "read") else remote
    if not isinstance(data, bytes):
        raise RisArchiveVerificationError(f"object {key!r} did not return bytes")
    if len(data) != size:
        raise RisArchiveVerificationError(
            f"object {key!r} GET size mismatch: expected {size}, got {len(data)}"
        )
    actual_sha = sha256_hex(data)
    if actual_sha != metadata_sha:
        raise RisArchiveVerificationError(
            f"object {key!r} GET sha256 mismatch: expected {metadata_sha}, got {actual_sha}"
        )
    return data


def _json_object(data: bytes, key: str) -> dict[str, Any]:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RisPopulationIngestionError(f"object {key!r} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise RisPopulationIngestionError(f"object {key!r} must contain a JSON object")
    return payload


def _manifest_page_files(manifest: Mapping[str, Any], yyymm: str) -> list[dict[str, Any]]:
    gregorian = roc_yyymm_to_gregorian(yyymm)
    if manifest.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        raise RisPopulationIngestionError("archive manifest schema version mismatch")
    if manifest.get("dataset") != DATASET or manifest.get("provider") != PROVIDER:
        raise RisPopulationIngestionError("archive manifest provider or dataset mismatch")
    if str(manifest.get("statistic_yyymm", "")) != yyymm:
        raise RisPopulationIngestionError("archive manifest statistic_yyymm mismatch")
    if manifest.get("statistic_month") != gregorian:
        raise RisPopulationIngestionError("archive manifest statistic_month mismatch")

    pages = _integer(manifest.get("pages"), "manifest pages")
    total_data_size = _integer(manifest.get("total_data_size"), "manifest total_data_size")
    page_files = manifest.get("page_files")
    if pages < 1 or total_data_size < 0 or not isinstance(page_files, list):
        raise RisPopulationIngestionError("archive manifest page metadata is invalid")
    if len(page_files) != pages:
        raise RisPopulationIngestionError("archive manifest page count mismatch")

    normalized: list[dict[str, Any]] = []
    total_bytes = 0
    for expected_page, item in enumerate(page_files, start=1):
        if not isinstance(item, dict):
            raise RisPopulationIngestionError("archive manifest page entry must be an object")
        number = _integer(item.get("page_number"), "manifest page_number")
        size = _integer(item.get("byte_size"), "manifest byte_size")
        checksum = str(item.get("sha256", ""))
        key = str(item.get("object_key", ""))
        if number != expected_page or key != page_key(gregorian, expected_page):
            raise RisPopulationIngestionError("archive manifest page ordering or key mismatch")
        if size < 0 or not _SHA256.fullmatch(checksum):
            raise RisPopulationIngestionError("archive manifest page checksum metadata is invalid")
        total_bytes += size
        normalized.append(
            {"page_number": number, "byte_size": size, "sha256": checksum, "object_key": key}
        )
    if _integer(manifest.get("total_archived_bytes"), "manifest total_archived_bytes") != total_bytes:
        raise RisPopulationIngestionError("archive manifest total_archived_bytes mismatch")
    return normalized


def prepare_archive_month(
    client: ObjectStore,
    bucket: str,
    yyymm: str,
) -> PreparedRisMonth:
    """Verify and normalize one archived month without opening a DB transaction."""

    cleaned = str(yyymm).strip()
    gregorian = roc_yyymm_to_gregorian(cleaned)
    m_key = manifest_key(gregorian)
    manifest = _json_object(_read_verified_object(client, bucket, m_key), m_key)
    page_files = _manifest_page_files(manifest, cleaned)

    raw_rows: list[dict[str, Any]] = []
    expected_pages = len(page_files)
    expected_total = _integer(manifest["total_data_size"], "manifest total_data_size")
    for item in page_files:
        key = item["object_key"]
        payload = _json_object(
            _read_verified_object(
                client,
                bucket,
                key,
                expected_size=item["byte_size"],
                expected_sha256=item["sha256"],
            ),
            key,
        )
        page_number = item["page_number"]
        if payload.get("responseCode") != RESPONSE_CODE_SUCCESS:
            raise RisPopulationIngestionError(f"page {page_number} responseCode is not successful")
        if _integer(payload.get("page"), "page number") != page_number:
            raise RisPopulationIngestionError(f"page number mismatch for archived page {page_number}")
        if _integer(payload.get("totalPage"), "totalPage") != expected_pages:
            raise RisPopulationIngestionError("totalPage changed across archived pages")
        if _integer(payload.get("totalDataSize"), "totalDataSize") != expected_total:
            raise RisPopulationIngestionError("totalDataSize changed across archived pages")
        response_data = payload.get("responseData")
        if not isinstance(response_data, list):
            raise RisPopulationIngestionError(f"page {page_number} responseData must be a list")
        if "pageDataSize" in payload and _integer(payload["pageDataSize"], "pageDataSize") != len(response_data):
            raise RisPopulationIngestionError(f"page {page_number} pageDataSize mismatch")
        for row in response_data:
            raw_rows.append(normalize_source_row_schema(row))

    if len(raw_rows) != expected_total:
        raise RisPopulationIngestionError(
            f"archive row count mismatch: expected {expected_total}, got {len(raw_rows)}"
        )
    normalized_rows = normalize_rows(raw_rows)
    return prepare_normalized_month(normalized_rows, rows_source=len(raw_rows))


def prepare_normalized_month(
    rows: Sequence[Mapping[str, Any]],
    *,
    rows_source: int,
) -> PreparedRisMonth:
    """Validate a complete canonical month and convert its month to a SQL date."""

    if not rows:
        raise RisPopulationIngestionError("normalized month must contain at least one row")
    if rows_source != len(rows):
        raise RisPopulationIngestionError("source and normalized row counts differ")

    expected_yyymm = str(rows[0].get("statistic_yyymm", "")).strip()
    expected_month_text = roc_yyymm_to_gregorian(expected_yyymm)
    expected_month = date.fromisoformat(f"{expected_month_text}-01")
    seen: set[tuple[str, str]] = set()
    validated: list[dict[str, Any]] = []

    for index, source in enumerate(rows):
        row = dict(source)
        for field in _IDENTITY_FIELDS:
            if not str(row.get(field, "")).strip():
                raise RisPopulationIngestionError(f"row {index} has empty {field}")
        yyymm = str(row["statistic_yyymm"]).strip()
        if yyymm != expected_yyymm:
            raise RisPopulationIngestionError("normalized rows span multiple statistic months")
        month_value = row.get("statistic_month")
        if isinstance(month_value, date):
            actual_month = month_value
        else:
            try:
                actual_month = date.fromisoformat(f"{str(month_value)}-01")
            except ValueError as exc:
                raise RisPopulationIngestionError(f"row {index} has invalid statistic_month") from exc
        if actual_month != expected_month:
            raise RisPopulationIngestionError("statistic_month does not match statistic_yyymm")

        for field in _COUNT_FIELDS:
            value = _integer(row.get(field), field)
            if value < 0:
                raise RisPopulationIngestionError(f"row {index} has negative {field}")
            row[field] = value
        for field in _UNIT_RATIO_FIELDS:
            value = row.get(field)
            if value is not None and not 0 <= float(value) <= 1:
                raise RisPopulationIngestionError(f"row {index} has out-of-range {field}")
        household_size = row.get("average_household_size")
        if household_size is not None and float(household_size) < 0:
            raise RisPopulationIngestionError(f"row {index} has negative average_household_size")
        audit_reasons = row.get("audit_reasons")
        if not isinstance(audit_reasons, list) or not all(isinstance(reason, str) for reason in audit_reasons):
            raise RisPopulationIngestionError(f"row {index} has invalid audit_reasons")

        district_code = str(row["district_code"]).strip()
        business_key = (yyymm, district_code)
        if business_key in seen:
            raise RisPopulationIngestionError(f"duplicate monthly district_code {district_code!r}")
        seen.add(business_key)
        row.update(
            statistic_yyymm=yyymm,
            statistic_month=expected_month,
            district_code=district_code,
            site_id=str(row["site_id"]).strip(),
            village=str(row["village"]).strip(),
        )
        validated.append(row)

    return PreparedRisMonth(
        statistic_yyymm=expected_yyymm,
        statistic_month=expected_month,
        rows_source=rows_source,
        rows_normalized=len(validated),
        rows=tuple(validated),
    )


_UPSERT_SQL = """
insert into public.ris_village_demographics (
    statistic_yyymm, statistic_month, district_code, site_id, village,
    household_count, total_population, male_population, female_population,
    age_0_14, age_15_64, age_65_plus, child_ratio, working_age_ratio,
    elderly_ratio, average_household_size, audit_reasons,
    source_provider, source_dataset
) values (
    %(statistic_yyymm)s, %(statistic_month)s, %(district_code)s, %(site_id)s, %(village)s,
    %(household_count)s, %(total_population)s, %(male_population)s, %(female_population)s,
    %(age_0_14)s, %(age_15_64)s, %(age_65_plus)s, %(child_ratio)s, %(working_age_ratio)s,
    %(elderly_ratio)s, %(average_household_size)s, %(audit_reasons_json)s::jsonb,
    %(source_provider)s, %(source_dataset)s
)
on conflict (statistic_yyymm, district_code) do update set
    statistic_month = excluded.statistic_month,
    site_id = excluded.site_id,
    village = excluded.village,
    household_count = excluded.household_count,
    total_population = excluded.total_population,
    male_population = excluded.male_population,
    female_population = excluded.female_population,
    age_0_14 = excluded.age_0_14,
    age_15_64 = excluded.age_15_64,
    age_65_plus = excluded.age_65_plus,
    child_ratio = excluded.child_ratio,
    working_age_ratio = excluded.working_age_ratio,
    elderly_ratio = excluded.elderly_ratio,
    average_household_size = excluded.average_household_size,
    audit_reasons = excluded.audit_reasons,
    source_provider = excluded.source_provider,
    source_dataset = excluded.source_dataset,
    updated_at = clock_timestamp()
"""


def _database_params(row: Mapping[str, Any]) -> dict[str, Any]:
    params = dict(row)
    params["audit_reasons_json"] = json.dumps(
        row["audit_reasons"], ensure_ascii=False, separators=(",", ":")
    )
    params["source_provider"] = "RIS"
    params["source_dataset"] = DATASET
    return params


def ingest_prepared_month(
    connection: Any,
    prepared: PreparedRisMonth,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Upsert one complete month in one transaction and return its report."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    started = time.perf_counter()
    with connection.transaction():
        connection.execute(
            "select pg_advisory_xact_lock(%s, %s)",
            (RIS_ADVISORY_LOCK_NAMESPACE, int(prepared.statistic_yyymm)),
        )
        existing = {
            str(row[0])
            for row in connection.execute(
                "select district_code from public.ris_village_demographics where statistic_yyymm = %s",
                (prepared.statistic_yyymm,),
            ).fetchall()
        }
        params = [_database_params(row) for row in prepared.rows]
        with connection.cursor() as cursor:
            for start in range(0, len(params), batch_size):
                cursor.executemany(_UPSERT_SQL, params[start : start + batch_size])

    updated = sum(1 for row in prepared.rows if str(row["district_code"]) in existing)
    inserted = prepared.rows_normalized - updated
    return {
        "month": prepared.statistic_yyymm,
        "rows_source": prepared.rows_source,
        "rows_normalized": prepared.rows_normalized,
        "inserted": inserted,
        "updated": updated,
        "rejected": 0,
        "audit_flagged": sum(bool(row["audit_reasons"]) for row in prepared.rows),
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "status": "VERIFIED",
    }


def ingest_archive_month(
    client: ObjectStore,
    bucket: str,
    yyymm: str,
    connection_factory: Callable[[], Any],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Verify R2 fully, then and only then open the database connection."""

    prepared = prepare_archive_month(client, bucket, yyymm)
    with connection_factory() as connection:
        return ingest_prepared_month(connection, prepared, batch_size=batch_size)
