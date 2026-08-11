"""Safe, file-based official PLVR market-data pipeline primitives.

The module is deliberately usable without a database or network connection.
Network acquisition is bounded and restricted to the official source registry;
normalization, quality checks, aggregation, and comparable scoring are pure
functions so they can be tested with synthetic fixtures.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import socket
import ssl
import tempfile
import urllib.parse
import urllib.error
import urllib.request
import zipfile
from html.parser import HTMLParser
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from services.plvr_data_integrity import (
    FUTURE_TRANSACTION_PERIOD,
    INVALID_CITY_DISTRICT_PAIR,
    is_future_transaction_period,
    is_publishable_transaction_date,
    is_publishable_transaction_period,
)
from services.taiwan_admin_registry import normalize_market_region


PING_SQM = 3.305785
PIPELINE_VERSION = "official-plvr-pipeline-v1"
AGGREGATION_VERSION = "median-quartiles-v1"
COMPARABLE_VERSION = "bounded-similarity-v1"
DISCOVERY_STATUSES = {
    "new_release_available", "already_imported", "source_unavailable",
    "source_changed", "schema_changed", "validation_failed", "configuration_required",
    "resource_discovered", "resource_unchanged", "metadata_unavailable_resource_known", "metadata_changed",
    "resource_unavailable", "archive_invalid", "network_unavailable",
}
FRESHNESS_STATUSES = {
    "current", "update_available", "importing", "stale", "failed_latest_update", "unknown", "configuration_required",
}
QUALITY_STATUSES = {"valid", "valid_with_warning", "quarantined", "rejected_schema", "duplicate", "cancelled", "unsupported"}
TRANSACTION_TYPES = {"existing_sale", "presale", "land", "building_only", "parking_only", "mixed", "rental", "other"}
REQUIRED_REGISTRY_FIELDS = {
    "source_id", "authority", "dataset_name", "transaction_type", "access_type", "discovery_url",
    "download_resolution_strategy", "expected_content_type", "expected_archive_type", "publication_frequency",
    "schema_strategy", "license", "enabled", "priority", "geographic_scope", "trust_level", "known_limitations",
}
DEFAULT_LIMITS = {
    "max_archive_bytes": 512 * 1024 * 1024,
    "max_extracted_bytes": 2 * 1024 * 1024 * 1024,
    "max_files": 20_000,
    "max_rows": 2_000_000,
    "max_text_length": 512,
    "max_zip_ratio": 100,
}

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "source_record_id": ("source_record_id", "id", "編號", "序號"),
    "county": ("county", "city", "縣市", "縣市名稱", "都市土地區域"),
    "district": ("district", "鄉鎮市區", "行政區", "區"),
    "transaction_date": ("transaction_date", "交易年月日", "交易日期", "交易年月"),
    "transaction_type": ("transaction_type", "交易標的", "交易類型", "用途"),
    "building_type": ("building_type", "建物型態", "建物型態類別"),
    "area_sqm": ("building_area_sqm", "area_sqm", "建物移轉總面積平方公尺", "建物移轉總面積"),
    "total_price_ntd": ("total_price_ntd", "total_price", "總價元", "交易總價元"),
    "unit_price_ntd_sqm": ("unit_price_ntd_sqm", "unit_price", "單價元平方公尺"),
    "parking_area_sqm": ("parking_area_sqm", "車位移轉總面積平方公尺", "車位面積"),
    "parking_price_ntd": ("parking_price_ntd", "車位總價元", "車位價格"),
    "parking_type": ("parking_type", "車位類別"),
    "special_transaction_note": ("special_transaction_note", "備註", "特殊交易備註"),
    "floor": ("floor", "移轉層次", "樓層"),
    "total_floors": ("total_floors", "總樓層數"),
    "rooms": ("rooms", "建物現況格局-房"),
    "completion_date": ("completion_date", "建築完成年月"),
}
PUBLIC_AGGREGATE_FIELDS = (
    "county", "district", "period", "transaction_type", "sample_status", "transaction_count",
    "valid_comparable_count", "median_unit_price_ntd_sqm", "mean_unit_price_ntd_sqm",
    "lower_quartile_unit_price_ntd_sqm", "upper_quartile_unit_price_ntd_sqm", "minimum_unit_price_ntd_sqm",
    "maximum_unit_price_ntd_sqm", "median_total_price_ntd", "median_area_sqm", "total_transaction_value_ntd",
    "source_name", "source_release_id", "source_updated_at", "coverage_status", "data_status",
    "aggregation_version", "methodology", "caveat",
)


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    authority: str
    dataset_name: str
    transaction_type: str
    access_type: str
    discovery_url: str
    expected_archive_type: str
    enabled: bool
    priority: int
    geographic_scope: str
    trust_level: str
    known_limitations: tuple[str, ...]
    metadata_url: str = ""
    public_resource_url: str = ""
    fallback_resource_urls: tuple[str, ...] = ()
    accepted_content_types: tuple[str, ...] = ("application/zip", "application/octet-stream", "binary/octet-stream")
    official_hosts: tuple[str, ...] = ()
    dataset_id: str | None = None
    filename_query_parameter: str | None = None
    publication_schedule: str | None = None
    source_priority: int = 1
    expected_archive_signature: tuple[str, ...] = ("PK\\x03\\x04", "PK\\x05\\x06", "PK\\x07\\x08")
    transaction_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiscoveryResult:
    status: str
    source_id: str | None = None
    release_id: str | None = None
    publication_date: str | None = None
    schema_version: str | None = None
    reason_code: str | None = None


@dataclass(frozen=True)
class SchemaReport:
    status: str
    schema_version: str | None
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    renamed_columns: tuple[str, ...] = ()
    unknown_columns: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass
class NormalizedTransaction:
    transaction_id: str
    source_id: str
    source_release_id: str
    transaction_type: str
    county: str
    district: str
    transaction_date: date | None
    area_sqm: float | None
    total_price_ntd: float | None
    unit_price_ntd_sqm: float | None
    unit_price_ntd_ping: float | None
    parking_type: str | None = None
    parking_area_sqm: float | None = None
    parking_price_ntd: float | None = None
    building_type: str | None = None
    special_transaction_flags: tuple[str, ...] = ()
    special_transaction_note: str | None = None
    source_record_id: str | None = None
    imported_at: str | None = None
    validation_status: str = "valid"
    quality_reason_codes: tuple[str, ...] = ()
    dedupe_fingerprint: str = ""

    def public_trace(self) -> dict[str, Any]:
        """Return bounded comparable-safe data; never expose raw address fields."""
        return {
            "transaction_type": self.transaction_type,
            "county": self.county,
            "district": self.district,
            "transaction_month": self.transaction_date.strftime("%Y-%m") if self.transaction_date else None,
            "area_sqm": self.area_sqm,
            "unit_price_ntd_sqm": self.unit_price_ntd_sqm,
            "unit_price_ntd_ping": self.unit_price_ntd_ping,
            "building_type": self.building_type,
            "special_transaction_flags": list(self.special_transaction_flags),
            "source_release_id": self.source_release_id,
        }


@dataclass(frozen=True)
class PipelineSummary:
    input_rows: int
    parsed_rows: int
    accepted_rows: int
    warning_rows: int
    quarantined_rows: int
    duplicate_rows: int
    cancelled_rows: int
    reason_counts: dict[str, int] = field(default_factory=dict)


class _OfficialLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def load_source_registry(path: Path) -> list[SourceSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ValueError("source_registry_invalid")
    sources: list[SourceSpec] = []
    for raw in payload["sources"]:
        if not isinstance(raw, dict) or not REQUIRED_REGISTRY_FIELDS.issubset(raw):
            raise ValueError("source_registry_fields_missing")
        parsed = urllib.parse.urlparse(str(raw["discovery_url"]))
        if parsed.scheme != "https" or not parsed.hostname or raw["trust_level"] != "official":
            raise ValueError("source_registry_official_https_required")
        if not isinstance(raw["known_limitations"], list):
            raise ValueError("source_registry_limitations_invalid")
        sources.append(SourceSpec(
            source_id=str(raw["source_id"]), authority=str(raw["authority"]), dataset_name=str(raw["dataset_name"]),
            transaction_type=str(raw["transaction_type"]), access_type=str(raw["access_type"]),
            discovery_url=str(raw["discovery_url"]), expected_archive_type=str(raw["expected_archive_type"]),
            enabled=bool(raw["enabled"]), priority=int(raw["priority"]), geographic_scope=str(raw["geographic_scope"]),
            trust_level=str(raw["trust_level"]), known_limitations=tuple(str(v) for v in raw["known_limitations"]),
            metadata_url=str(raw.get("metadata_url") or ""), public_resource_url=str(raw.get("public_resource_url") or ""),
            fallback_resource_urls=tuple(str(v) for v in raw.get("fallback_resource_urls", []) if str(v).strip()),
            accepted_content_types=tuple(str(v).lower() for v in raw.get("accepted_content_types", ["application/zip", "application/octet-stream", "binary/octet-stream"])),
            official_hosts=tuple(str(v).lower() for v in raw.get("official_hosts", [parsed.hostname])),
            dataset_id=str(raw.get("dataset_id") or "") or None,
            filename_query_parameter=str(raw.get("filename_query_parameter") or "") or None,
            publication_schedule=str(raw.get("publication_schedule") or "") or None,
            source_priority=int(raw.get("source_priority", raw["priority"])),
            expected_archive_signature=tuple(
                str(value) for value in raw.get(
                    "expected_archive_signature",
                    ["PK\\x03\\x04", "PK\\x05\\x06", "PK\\x07\\x08"],
                )
            ),
            transaction_types=tuple(str(value) for value in raw.get("transaction_types", [raw["transaction_type"]])),
        ))
    return sorted(sources, key=lambda item: (not item.enabled, item.priority, item.source_id))


def validate_official_url(url: str, allowed_hosts: Iterable[str]) -> str:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    allowed = {item.lower().rstrip(".") for item in allowed_hosts}
    if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("source_url_rejected")
    if host not in allowed and not any(host.endswith("." + item) for item in allowed):
        raise ValueError("source_url_host_rejected")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def validate_redirect_chain(urls: Iterable[str], allowed_hosts: Iterable[str]) -> bool:
    try:
        for url in urls:
            validate_official_url(url, allowed_hosts)
        return True
    except ValueError:
        return False


def validate_public_resource_url(url: str, source: SourceSpec) -> str:
    """Validate a registry-owned PLVR resource, including query filenames."""
    safe = validate_official_url(url, source.official_hosts or [urllib.parse.urlparse(source.discovery_url).hostname or ""])
    parsed = urllib.parse.urlparse(safe)
    allowed_paths = {"/opendata/lvr_landAcsv.zip", "/Download"}
    if parsed.path not in allowed_paths:
        raise ValueError("resource_path_rejected")
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if parsed.path == "/Download":
        if set(query) - {source.filename_query_parameter or "fileName", "type"}:
            raise ValueError("resource_query_rejected")
        filename = (query.get(source.filename_query_parameter or "fileName") or [""])[0]
        if filename not in {"lvr_landcsv.zip", "lvr_landAcsv.zip"}:
            raise ValueError("resource_filename_rejected")
    elif query:
        raise ValueError("resource_query_rejected")
    return safe


def resolve_resource_from_metadata(source: SourceSpec, *, max_bytes: int = 2 * 1024 * 1024) -> str | None:
    """Read only the official catalog page and keep only PLVR-hosted links."""
    if not source.metadata_url:
        return None
    try:
        catalog_url = validate_official_url(source.metadata_url, ["data.gov.tw"])
        request = urllib.request.Request(catalog_url, headers={"Accept": "text/html, application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            return None
        text = payload.decode("utf-8", errors="replace")
        urls = re.findall(r"https://plvr\.land\.moi\.gov\.tw[^\"'\\s<>]+", text)
        for url in urls:
            try:
                return validate_public_resource_url(url.replace("&amp;", "&"), source)
            except ValueError:
                continue
    except Exception:
        return None
    return None


def resolve_public_resource(source: SourceSpec) -> tuple[str, str]:
    metadata_resource = resolve_resource_from_metadata(source)
    if metadata_resource:
        return metadata_resource, "official_metadata_catalog"
    metadata_unavailable = bool(source.metadata_url)
    candidates = [
        (source.public_resource_url, "metadata_unavailable_resource_known" if metadata_unavailable else "registry_public_resource"),
        *[(url, "registry_fallback") for url in source.fallback_resource_urls],
    ]
    for candidate, strategy in candidates:
        if not candidate:
            continue
        try:
            return validate_public_resource_url(candidate, source), strategy
        except ValueError:
            continue
    raise ValueError("resource_unavailable")


def discover_official_release(source: SourceSpec, *, max_page_bytes: int = 2 * 1024 * 1024) -> DiscoveryResult:
    """Discover a public release link without accepting arbitrary HTML URLs."""
    try:
        _resource_url, strategy = resolve_public_resource(source)
        return DiscoveryResult("resource_discovered", source_id=source.source_id, reason_code=strategy)
    except ValueError:
        pass
    try:
        safe_url = validate_official_url(source.discovery_url, [urllib.parse.urlparse(source.discovery_url).hostname or ""])
        request = urllib.request.Request(safe_url, headers={"Accept": "text/html"})
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = str(response.headers.get("Content-Type") or "").lower()
            if "html" not in content_type:
                return DiscoveryResult("source_changed", source_id=source.source_id, reason_code="discovery_content_type_invalid")
            payload = response.read(max_page_bytes + 1)
        if len(payload) > max_page_bytes:
            return DiscoveryResult("validation_failed", source_id=source.source_id, reason_code="discovery_size_limit")
        parser = _OfficialLinkParser()
        parser.feed(payload.decode("utf-8", errors="replace"))
        candidates: list[str] = []
        for link in parser.links:
            try:
                candidate = urllib.parse.urljoin(safe_url, link)
                validate_public_resource_url(candidate, source)
                candidates.append(candidate)
            except ValueError:
                continue
        if not candidates:
            return DiscoveryResult("resource_unavailable", source_id=source.source_id, reason_code="public_resource_not_discovered")
        return DiscoveryResult("resource_discovered", source_id=source.source_id, reason_code="page_resource_discovered")
    except Exception:
        return DiscoveryResult("network_unavailable", source_id=source.source_id, reason_code="official_discovery_network_unavailable")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_official_archive(
    url: str,
    destination: Path,
    *,
    allowed_hosts: Iterable[str],
    expected_sha256: str | None = None,
    max_bytes: int = DEFAULT_LIMITS["max_archive_bytes"],
    timeout: tuple[int, int] = (20, 120),
    accepted_content_types: Iterable[str] | None = None,
    expected_archive_signatures: Iterable[bytes] | None = None,
) -> dict[str, Any]:
    """Download atomically; callers must supply an official allowlist host."""
    safe_url = validate_official_url(url, allowed_hosts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="plvr-", suffix=".part", dir=destination.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        request = urllib.request.Request(safe_url, headers={"Accept": "application/zip, application/octet-stream"})
        with urllib.request.urlopen(request, timeout=timeout[1]) as response, temp_path.open("wb") as handle:
            validate_official_url(response.geturl(), allowed_hosts)
            content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            accepted = {str(value).lower().split(";", 1)[0].strip() for value in (accepted_content_types or ("application/zip", "application/octet-stream", "binary/octet-stream"))}
            if not content_type or content_type not in accepted:
                raise ValueError("content_type_invalid")
            content_length = str(response.headers.get("Content-Length") or "").strip()
            if content_length.isdigit() and int(content_length) > max_bytes:
                raise ValueError("archive_size_limit")
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("archive_size_limit")
                handle.write(chunk)
        if total <= 0:
            raise ValueError("archive_empty")
        with temp_path.open("rb") as handle:
            signature = handle.read(4)
        signatures = set(expected_archive_signatures or (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
        if signature not in signatures:
            raise ValueError("archive_signature_invalid")
        checksum = sha256_file(temp_path)
        if expected_sha256 and checksum.lower() != expected_sha256.lower():
            raise ValueError("archive_checksum_mismatch")
        temp_path.replace(destination)
        return {"status": "downloaded", "bytes": total, "sha256": checksum, "content_type": content_type}
    except urllib.error.HTTPError as exc:
        temp_path.unlink(missing_ok=True)
        return {"status": "resource_unavailable", "reason_code": f"http_status_{exc.code}"}
    except (socket.gaierror, urllib.error.URLError):
        temp_path.unlink(missing_ok=True)
        return {"status": "network_unavailable", "reason_code": "dns_or_transport_failure"}
    except (TimeoutError, socket.timeout):
        temp_path.unlink(missing_ok=True)
        return {"status": "network_unavailable", "reason_code": "timeout"}
    except ssl.SSLError:
        temp_path.unlink(missing_ok=True)
        return {"status": "network_unavailable", "reason_code": "tls_failure"}
    except ValueError as exc:
        temp_path.unlink(missing_ok=True)
        return {"status": "archive_invalid", "reason_code": str(exc)}
    except Exception:
        temp_path.unlink(missing_ok=True)
        return {"status": "resource_unavailable", "reason_code": "download_failed"}


def inspect_zip_archive(path: Path, *, limits: Mapping[str, int] = DEFAULT_LIMITS) -> dict[str, Any]:
    if path.stat().st_size > limits["max_archive_bytes"]:
        raise ValueError("archive_size_limit")
    if path.read_bytes()[:2] != b"PK":
        raise ValueError("archive_signature_invalid")
    extracted_size = 0
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > limits["max_files"]:
            raise ValueError("archive_file_count_limit")
        for entry in entries:
            name = entry.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts or Path(name).drive:
                raise ValueError("zip_path_traversal")
            if entry.file_size > limits["max_extracted_bytes"]:
                raise ValueError("archive_member_size_limit")
            if entry.compress_size and entry.file_size / entry.compress_size > limits["max_zip_ratio"]:
                raise ValueError("zip_bomb_ratio")
            extracted_size += entry.file_size
            if extracted_size > limits["max_extracted_bytes"]:
                raise ValueError("extracted_size_limit")
    return {"status": "valid", "file_count": len(entries), "extracted_bytes": extracted_size}


def extract_zip_archive(path: Path, destination: Path, *, limits: Mapping[str, int] = DEFAULT_LIMITS) -> list[Path]:
    inspect_zip_archive(path, limits=limits)
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            target = destination / Path(entry.filename.replace("\\", "/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            extracted.append(target)
    return extracted


def parse_manifest(payload: str | bytes) -> dict[str, Any]:
    try:
        result = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("manifest_invalid") from exc
    if not isinstance(result, dict) or not result.get("release_id"):
        raise ValueError("manifest_fields_missing")
    return {key: result[key] for key in ("release_id", "publication_date", "schema_version", "files") if key in result}


def validate_schema(headers: Iterable[str], *, schema_version: str | None = None) -> SchemaReport:
    supplied = tuple(str(value).strip() for value in headers if str(value).strip())
    canonical = set(supplied)
    aliases = {alias for values in FIELD_ALIASES.values() for alias in values}
    required = {"county", "district", "transaction_date", "total_price_ntd", "area_sqm"}
    missing = sorted(field for field in required if not any(alias in canonical for alias in FIELD_ALIASES[field]))
    renamed = sorted(field for field in required if field not in canonical and any(alias in canonical for alias in FIELD_ALIASES[field][1:]))
    known = set(aliases)
    unknown = sorted(canonical - known)
    return SchemaReport(
        status="valid" if not missing else "rejected_schema", schema_version=schema_version,
        required_columns=tuple(sorted(required)), optional_columns=tuple(sorted(set(FIELD_ALIASES) - required)),
        renamed_columns=tuple(renamed), unknown_columns=tuple(unknown),
        reason_codes=tuple(["missing_required_column"] if missing else []),
    )


def parse_roc_date(value: Any) -> date | None:
    text = str(value or "").strip().replace("年", "/").replace("月", "/").replace("日", "")
    if not text:
        return None
    text = re.sub(r"[.\-]", "/", text)
    parts = [part for part in text.split("/") if part]
    if len(parts) == 1 and len(parts[0]) in {7, 8}:
        raw = parts[0]
        if len(raw) == 7:
            parts = [raw[:3], raw[3:5], raw[5:]]
        else:
            parts = [raw[:4], raw[4:6], raw[6:]]
    if len(parts) != 3:
        raise ValueError("transaction_date_invalid")
    year, month, day = (int(item) for item in parts)
    if year < 1911:
        year += 1911
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError("transaction_date_invalid") from exc


def sqm_to_ping(value: float | int | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number / PING_SQM if number > 0 else None


def _number(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text or text in {"-", "—", "N/A", "無"}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _read_alias(row: Mapping[str, Any], field: str) -> str:
    for alias in FIELD_ALIASES[field]:
        if alias in row and str(row[alias] or "").strip():
            return str(row[alias]).strip()
    return ""


def classify_transaction(row: Mapping[str, Any]) -> str:
    text = " ".join(_read_alias(row, field) for field in ("transaction_type", "building_type")).lower()
    if any(token in text for token in ("租賃", "租屋", "rental")):
        return "rental"
    if any(token in text for token in ("預售", "presale")):
        return "presale"
    if "土地" in text or "land" in text:
        return "land"
    if "車位" in text and not any(token in text for token in ("房", "建物", "building")):
        return "parking_only"
    return "existing_sale"


def special_transaction_flags(note: str | None) -> tuple[str, ...]:
    text = (note or "").strip()
    if not text:
        return ()
    patterns = {
        "related_party": ("親友", "關係人", "親屬"), "auction": ("拍賣", "法拍"),
        "partial_ownership": ("持分", "共有"), "complex_land_rights": ("地上權", "土地權利"),
        "multiple_properties": ("多筆", "多棟"), "renovation_included": ("裝潢", "家具"),
    }
    found = [key for key, tokens in patterns.items() if any(token in text for token in tokens)]
    return tuple(found or ["requires_review"])


def _fingerprint(values: Iterable[Any]) -> str:
    material = "|".join(str(value or "").strip() for value in values)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def normalize_transaction_row(
    row: Mapping[str, Any],
    *,
    source_id: str,
    release_id: str,
    imported_at: str | None = None,
    as_of: date | datetime | None = None,
) -> NormalizedTransaction:
    county_value = _read_alias(row, "county")
    district_value = _read_alias(row, "district")
    normalized = normalize_market_region(county_value, district_value)
    if not normalized.valid:
        raise ValueError(INVALID_CITY_DISTRICT_PAIR)
    transaction_date = parse_roc_date(_read_alias(row, "transaction_date"))
    area = _number(_read_alias(row, "area_sqm"))
    total = _number(_read_alias(row, "total_price_ntd"))
    unit = _number(_read_alias(row, "unit_price_ntd_sqm"))
    if unit is None and area and total and area > 0:
        unit = total / area
    note = _read_alias(row, "special_transaction_note") or None
    transaction_type = classify_transaction(row)
    source_record_id = _read_alias(row, "source_record_id") or None
    transaction_id = source_record_id or _fingerprint((source_id, release_id, normalized.county, normalized.district, transaction_date, area, total, unit))
    flags = special_transaction_flags(note)
    reasons: list[str] = []
    if transaction_date is None:
        reasons.append("transaction_date_missing")
    elif is_future_transaction_period(transaction_date.strftime("%Y-%m"), as_of=as_of):
        reasons.append(FUTURE_TRANSACTION_PERIOD)
    if area is None or area <= 0:
        reasons.append("area_invalid")
    if total is None or total <= 0:
        reasons.append("price_invalid")
    if transaction_type not in TRANSACTION_TYPES:
        reasons.append("transaction_type_unsupported")
    status = "quarantined" if reasons else ("valid_with_warning" if flags else "valid")
    return NormalizedTransaction(
        transaction_id=transaction_id, source_id=source_id, source_release_id=release_id,
        transaction_type=transaction_type, county=normalized.county, district=normalized.district,
        transaction_date=transaction_date, area_sqm=area, total_price_ntd=total,
        unit_price_ntd_sqm=unit, unit_price_ntd_ping=unit * PING_SQM if unit and unit > 0 else None,
        parking_type=_read_alias(row, "parking_type") or None, parking_area_sqm=_number(_read_alias(row, "parking_area_sqm")),
        parking_price_ntd=_number(_read_alias(row, "parking_price_ntd")), building_type=_read_alias(row, "building_type") or None,
        special_transaction_flags=flags, special_transaction_note=note, source_record_id=source_record_id,
        imported_at=imported_at, validation_status=status, quality_reason_codes=tuple(reasons),
        dedupe_fingerprint=_fingerprint((source_id, source_record_id, normalized.county, normalized.district, transaction_date, area, total, unit)),
    )


def parse_csv_rows(path: Path, *, max_rows: int = DEFAULT_LIMITS["max_rows"]) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("duplicate_header")
        for index, row in enumerate(reader):
            if index >= max_rows:
                raise ValueError("row_limit")
            yield {str(key): str(value or "") for key, value in row.items() if key is not None}


def normalize_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_id: str,
    release_id: str,
    imported_at: str | None = None,
    as_of: date | datetime | None = None,
) -> tuple[list[NormalizedTransaction], PipelineSummary]:
    accepted: list[NormalizedTransaction] = []
    seen: set[str] = set()
    counts: dict[str, int] = {}
    input_rows = parsed_rows = warning = quarantined = duplicates = cancelled = 0
    for row in rows:
        input_rows += 1
        try:
            item = normalize_transaction_row(
                row,
                source_id=source_id,
                release_id=release_id,
                imported_at=imported_at,
                as_of=as_of,
            )
            parsed_rows += 1
        except ValueError as exc:
            quarantined += 1
            counts[str(exc)] = counts.get(str(exc), 0) + 1
            continue
        if item.dedupe_fingerprint in seen:
            duplicates += 1
            counts["duplicate"] = counts.get("duplicate", 0) + 1
            continue
        seen.add(item.dedupe_fingerprint)
        if item.transaction_type == "presale" and any(token in (item.special_transaction_note or "") for token in ("取消", "撤銷")):
            cancelled += 1
            continue
        if item.validation_status == "quarantined":
            quarantined += 1
            for reason in item.quality_reason_codes:
                counts[reason] = counts.get(reason, 0) + 1
            continue
        warning += item.validation_status == "valid_with_warning"
        accepted.append(item)
    return accepted, PipelineSummary(input_rows, parsed_rows, len(accepted), warning, quarantined, duplicates, cancelled, counts)


def _quartile(values: list[float], fraction: float) -> float | None:
    return statistics.quantiles(values, n=4, method="inclusive")[int(fraction * 4) - 1] if len(values) >= 2 else values[0] if values else None


def sample_status(count: int) -> str:
    return "no_data" if count == 0 else "insufficient" if count < 3 else "limited" if count < 10 else "sufficient"


def aggregate_transactions(
    transactions: Iterable[NormalizedTransaction], *, source_name: str, source_release_id: str,
    source_updated_at: str | None, coverage_status: str = "partial", transaction_type: str = "existing_sale",
    as_of: date | datetime | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[NormalizedTransaction]] = {}
    for item in transactions:
        if (
            item.validation_status == "quarantined"
            or item.transaction_type != transaction_type
            or not item.transaction_date
            or not item.unit_price_ntd_sqm
            or not is_publishable_transaction_date(item.transaction_date, as_of=as_of)
        ):
            continue
        period = item.transaction_date.strftime("%Y-%m")
        grouped.setdefault((item.county, item.district, period), []).append(item)
    result: list[dict[str, Any]] = []
    for (county, district, period), items in sorted(grouped.items()):
        prices = [item.unit_price_ntd_sqm for item in items if item.unit_price_ntd_sqm and item.unit_price_ntd_sqm > 0]
        totals = [item.total_price_ntd for item in items if item.total_price_ntd and item.total_price_ntd > 0]
        areas = [item.area_sqm for item in items if item.area_sqm and item.area_sqm > 0]
        result.append({
            "county": county, "district": district, "period": period, "transaction_type": transaction_type,
            "sample_status": sample_status(len(prices)), "transaction_count": len(prices), "valid_comparable_count": len(prices),
            "median_unit_price_ntd_sqm": statistics.median(prices), "mean_unit_price_ntd_sqm": statistics.fmean(prices),
            "lower_quartile_unit_price_ntd_sqm": _quartile(prices, .25), "upper_quartile_unit_price_ntd_sqm": _quartile(prices, .75),
            "minimum_unit_price_ntd_sqm": min(prices), "maximum_unit_price_ntd_sqm": max(prices),
            "median_total_price_ntd": statistics.median(totals) if totals else None, "median_area_sqm": statistics.median(areas) if areas else None,
            "total_transaction_value_ntd": sum(totals) if totals else None, "source_name": source_name,
            "source_release_id": source_release_id, "source_updated_at": source_updated_at, "coverage_status": coverage_status,
            "data_status": "available", "aggregation_version": AGGREGATION_VERSION,
            "methodology": "median_primary; mean_and_quartiles_descriptive; residential_sale_only_by_default",
            "caveat": "Market Insight is an aggregated reference, not an appraisal or purchase recommendation.",
        })
    return result


def score_comparables(
    target: NormalizedTransaction,
    candidates: Iterable[NormalizedTransaction],
    *,
    limit: int = 10,
    as_of: date | datetime | None = None,
) -> list[dict[str, Any]]:
    if (
        target.transaction_type not in {"existing_sale", "presale"}
        or not is_publishable_transaction_date(target.transaction_date, as_of=as_of)
    ):
        return []
    bounded_limit = max(1, min(int(limit), 10))
    scored: list[tuple[float, NormalizedTransaction, list[str]]] = []
    for candidate in candidates:
        if (
            candidate.validation_status == "quarantined"
            or candidate.transaction_type != target.transaction_type
            or not is_publishable_transaction_date(candidate.transaction_date, as_of=as_of)
        ):
            continue
        score = 0.0
        reasons: list[str] = []
        if candidate.county == target.county and candidate.district == target.district:
            score += 50; reasons.append("same_district")
        if candidate.building_type and candidate.building_type == target.building_type:
            score += 20; reasons.append("same_building_type")
        if target.area_sqm and candidate.area_sqm:
            score += max(0.0, 20.0 - abs(candidate.area_sqm - target.area_sqm) / target.area_sqm * 20.0)
            reasons.append("area_similarity")
        if target.transaction_date and candidate.transaction_date:
            days = abs((target.transaction_date - candidate.transaction_date).days)
            score += max(0.0, 10.0 - days / 365.0 * 10.0)
            reasons.append("date_recency")
        scored.append((score, candidate, reasons))
    scored.sort(key=lambda row: (-row[0], row[1].dedupe_fingerprint))
    return [{**candidate.public_trace(), "similarity_score": round(score, 2), "similarity_reasons": reasons, "limitation": "Comparable reference only; not an appraisal."} for score, candidate, reasons in scored[:bounded_limit]]


def freshness_status(latest_publication: date | None, latest_import: datetime | None, *, now: date | None = None) -> str:
    if latest_publication is None or latest_import is None:
        return "unknown"
    today = now or date.today()
    if latest_publication > today + timedelta(days=1):
        return "unknown"
    age = (today - latest_publication).days
    return "current" if age <= 45 else "stale"


def safe_release_evidence(*, source_id: str, release_id: str, schema_version: str | None, archive_sha256: str | None, input_rows: int, accepted_rows: int, quarantined_rows: int, source_updated_at: str | None) -> dict[str, Any]:
    return {"source_id": source_id, "release_id": release_id, "schema_version": schema_version, "archive_sha256": archive_sha256, "input_rows": input_rows, "accepted_rows": accepted_rows, "quarantined_rows": quarantined_rows, "source_updated_at": source_updated_at, "pipeline_version": PIPELINE_VERSION, "aggregation_version": AGGREGATION_VERSION}


def discover_release(current_release_id: str | None, candidate: Mapping[str, Any] | None) -> DiscoveryResult:
    """Classify a bounded manifest comparison without calling a provider."""
    if not candidate:
        return DiscoveryResult("source_unavailable", reason_code="manifest_unavailable")
    release_id = str(candidate.get("release_id") or "").strip()
    if not release_id:
        return DiscoveryResult("validation_failed", reason_code="release_id_missing")
    if current_release_id and release_id == current_release_id:
        return DiscoveryResult("already_imported", release_id=release_id, publication_date=str(candidate.get("publication_date") or "") or None, schema_version=str(candidate.get("schema_version") or "") or None)
    return DiscoveryResult("new_release_available", release_id=release_id, publication_date=str(candidate.get("publication_date") or "") or None, schema_version=str(candidate.get("schema_version") or "") or None)


def publish_release(
    connection: Any,
    *,
    release: Mapping[str, Any],
    transactions: Iterable[NormalizedTransaction],
    aggregates: Iterable[Mapping[str, Any]],
    as_of: date | datetime | None = None,
) -> dict[str, Any]:
    """Publish one validated release atomically on a caller-owned connection.

    The caller controls commit/rollback. The active flag changes only after all
    transaction and aggregate inserts succeed, so a failed transaction keeps
    the previous active release visible.
    """
    transaction_rows = list(transactions)
    aggregate_rows = list(aggregates)
    if any(
        not is_publishable_transaction_date(item.transaction_date, as_of=as_of)
        for item in transaction_rows
    ):
        raise ValueError(FUTURE_TRANSACTION_PERIOD)
    if any(
        not is_publishable_transaction_period(aggregate.get("period"), as_of=as_of)
        for aggregate in aggregate_rows
    ):
        raise ValueError(FUTURE_TRANSACTION_PERIOD)

    release_id = str(release["release_id"])
    source_id = str(release["source_id"])
    cursor = connection.cursor()
    try:
        cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", ["official-plvr-market-import"])
        cursor.execute(
            "insert into official_market_releases (release_id, source_id, publication_date, schema_version, archive_sha256, status, is_active) values (%s,%s,%s,%s,%s,'validated',false) on conflict (release_id) do update set schema_version=excluded.schema_version, archive_sha256=excluded.archive_sha256, status='validated'",
            [release_id, source_id, release.get("publication_date"), release.get("schema_version"), release.get("archive_sha256")],
        )
        for item in transaction_rows:
            cursor.execute(
                "insert into market_transactions (transaction_id, release_id, source_id, source_record_id, transaction_type, county, district, transaction_date, area_sqm, total_price_ntd, unit_price_ntd_sqm, unit_price_ntd_ping, parking_area_sqm, parking_price_ntd, building_type, special_transaction_flags, validation_status, dedupe_fingerprint) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (transaction_id) do nothing",
                [item.transaction_id, release_id, item.source_id, item.source_record_id, item.transaction_type, item.county, item.district, item.transaction_date, item.area_sqm, item.total_price_ntd, item.unit_price_ntd_sqm, item.unit_price_ntd_ping, item.parking_area_sqm, item.parking_price_ntd, item.building_type, json.dumps(list(item.special_transaction_flags)), item.validation_status, item.dedupe_fingerprint],
            )
        for aggregate in aggregate_rows:
            values = [aggregate.get(field) for field in ("county", "district", "period", "transaction_type", "sample_status", "transaction_count", "valid_comparable_count", "median_unit_price_ntd_sqm", "mean_unit_price_ntd_sqm", "lower_quartile_unit_price_ntd_sqm", "upper_quartile_unit_price_ntd_sqm", "minimum_unit_price_ntd_sqm", "maximum_unit_price_ntd_sqm", "median_total_price_ntd", "median_area_sqm", "total_transaction_value_ntd", "aggregation_version", "source_updated_at", "coverage_status", "data_status")]
            cursor.execute("insert into market_region_period_aggregates (release_id, county, district, period, transaction_type, sample_status, transaction_count, valid_comparable_count, median_unit_price_ntd_sqm, mean_unit_price_ntd_sqm, lower_quartile_unit_price_ntd_sqm, upper_quartile_unit_price_ntd_sqm, minimum_unit_price_ntd_sqm, maximum_unit_price_ntd_sqm, median_total_price_ntd, median_area_sqm, total_transaction_value_ntd, aggregation_version, source_updated_at, coverage_status, data_status) values (%s," + ",".join(["%s"] * len(values)) + ") on conflict do nothing", [release_id, *values])
        cursor.execute("update official_market_releases set is_active = false where is_active")
        cursor.execute("update official_market_releases set is_active = true, status = 'published' where release_id = %s", [release_id])
        return {"status": "published", "release_id": release_id}
    except Exception:
        raise
    finally:
        cursor.close()


def rollback_release(connection: Any, *, release_id: str) -> dict[str, Any]:
    """Atomically reactivate a previously published release.

    Rollback is deliberately explicit and release-id based. It never accepts
    a URL, raw transaction payload, or arbitrary SQL from an operator.
    """
    clean_release_id = str(release_id or "").strip()
    if not clean_release_id or len(clean_release_id) > 160:
        raise ValueError("release_id_invalid")
    cursor = connection.cursor()
    try:
        cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", ["official-plvr-market-import"])
        cursor.execute(
            "select status from official_market_releases where release_id = %s for update",
            [clean_release_id],
        )
        row = cursor.fetchone()
        if not row or str(row[0] if not isinstance(row, dict) else row.get("status")) not in {"published", "rolled_back"}:
            raise ValueError("release_not_rollbackable")
        cursor.execute("update official_market_releases set is_active = false where is_active")
        cursor.execute(
            "update official_market_releases set is_active = true, status = 'published' where release_id = %s",
            [clean_release_id],
        )
        if cursor.rowcount != 1:
            raise ValueError("release_not_found")
        return {"status": "rolled_back", "release_id": clean_release_id}
    finally:
        cursor.close()
