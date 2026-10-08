"""Deterministic offline artifact builder for GSMMA geological sensitivity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import codecs
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable
import zipfile

import shapefile
from shapely import get_coordinates, wkb
from shapely.geometry import shape as geometry_shape

from services.gsmma_geological_sensitivity_dataset import (
    CrsInvalidError,
    IndexRecord,
    NormalizationStats,
    NormalizedFeature,
    QuarantineRecord,
    OFFICIAL_CATEGORY_MAP,
    UnsupportedDatasetError,
    normalize_feature,
    parse_index_csv,
    resolve_source_crs,
    summarize_normalization,
)


DATASET_NAME = "gsmma_geological_sensitivity"
ARTIFACT_SCHEMA = "gsmma_geological_sensitivity_features"
MANIFEST_SCHEMA = "gsmma_geological_sensitivity_manifest"
QUARANTINE_SCHEMA = "gsmma_geological_sensitivity_quarantine"
SCHEMA_VERSION = 1
MAX_ARCHIVE_ENTRIES = 256
MAX_SINGLE_ENTRY_BYTES = 256 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_COMPRESSION_RATIO = 500


class ArtifactBuildError(ValueError):
    status = "artifact_invalid"


@dataclass(frozen=True)
class PackageInput:
    index_no: str
    path: Path
    shapefile_path: str | None = None
    encoding: str | None = None
    expected_sha256: str | None = None


@dataclass(frozen=True)
class ShapefileComponents:
    relative_shp_path: str
    shp: bytes
    shx: bytes
    dbf: bytes
    prj: bytes
    cpg: bytes | None
    encoding: str
    source_package_sha256: str


@dataclass(frozen=True)
class BuildResult:
    manifest: dict[str, Any]
    manifest_bytes: bytes
    artifact_bytes: bytes
    quarantine_bytes: bytes
    features: list[NormalizedFeature]
    quarantine: list[QuarantineRecord]
    stats: NormalizationStats


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


_DATASET_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def validate_dataset_version(value: str) -> str:
    version = value.strip()
    if version.casefold() == "latest" or not _DATASET_VERSION_RE.fullmatch(version):
        raise ArtifactBuildError(
            "dataset_version must be an explicit immutable path-safe identifier"
        )
    return version


def _members_sha(members: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, payload in sorted(members.items(), key=lambda item: item[0].casefold()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _deterministic_gzip(payload: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as archive:
        archive.write(payload)
    return output.getvalue()


def _safe_relative_name(name: str) -> str:
    if not name or "\\" in name:
        raise ArtifactBuildError(f"unsafe archive member name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ArtifactBuildError(f"unsafe archive member name: {name!r}")
    if path.parts and ":" in path.parts[0]:
        raise ArtifactBuildError(f"unsafe archive member name: {name!r}")
    return path.as_posix()


def _validate_encoding(value: str) -> str:
    cleaned = value.strip().strip("\ufeff")
    aliases = {"65001": "utf-8", "UTF8": "utf-8", "UTF-8": "utf-8"}
    cleaned = aliases.get(cleaned.upper(), cleaned)
    if not cleaned:
        raise ArtifactBuildError("shapefile encoding declaration is empty")
    try:
        return codecs.lookup(cleaned).name
    except LookupError as exc:
        raise ArtifactBuildError(f"unsupported shapefile encoding: {value!r}") from exc


def _select_shp(candidates: list[str], selected: str | None) -> str:
    if selected:
        selected = _safe_relative_name(selected)
        matches = [candidate for candidate in candidates if candidate.casefold() == selected.casefold()]
        if len(matches) != 1:
            raise ArtifactBuildError(f"selected shapefile not found: {selected}")
        return matches[0]
    if not candidates:
        raise ArtifactBuildError("package contains no shapefile")
    if len(candidates) != 1:
        raise ArtifactBuildError("package contains multiple shapefiles; select one explicitly")
    return candidates[0]


def _components_from_members(
    members: dict[str, bytes], package: PackageInput, *, source_package_sha256: str
) -> ShapefileComponents:
    candidates = sorted(
        (name for name in members if PurePosixPath(name).suffix.casefold() == ".shp"),
        key=str.casefold,
    )
    shp_name = _select_shp(candidates, package.shapefile_path)
    stem = str(PurePosixPath(shp_name).with_suffix(""))
    lookup = {name.casefold(): name for name in members}

    def required(suffix: str) -> bytes:
        key = (stem + suffix).casefold()
        actual = lookup.get(key)
        if actual is None:
            raise ArtifactBuildError(f"missing required shapefile sidecar: {stem + suffix}")
        return members[actual]

    cpg_name = lookup.get((stem + ".cpg").casefold())
    cpg = members[cpg_name] if cpg_name else None
    if package.encoding:
        encoding = _validate_encoding(package.encoding)
        if cpg is not None:
            try:
                cpg_encoding = _validate_encoding(cpg.decode("ascii", errors="strict"))
            except UnicodeDecodeError as exc:
                raise ArtifactBuildError("shapefile .cpg is not ASCII/UTF-8 text") from exc
            if cpg_encoding != encoding:
                raise ArtifactBuildError("explicit encoding conflicts with shapefile .cpg")
    elif cpg is not None:
        try:
            encoding = _validate_encoding(cpg.decode("ascii", errors="strict"))
        except UnicodeDecodeError as exc:
            raise ArtifactBuildError("shapefile .cpg is not ASCII/UTF-8 text") from exc
    else:
        raise ArtifactBuildError("shapefile encoding is missing; provide .cpg or explicit encoding")
    return ShapefileComponents(
        relative_shp_path=shp_name,
        shp=required(".shp"),
        shx=required(".shx"),
        dbf=required(".dbf"),
        prj=required(".prj"),
        cpg=cpg,
        encoding=encoding,
        source_package_sha256=source_package_sha256,
    )


def _read_zip(package: PackageInput) -> ShapefileComponents:
    payload = package.path.read_bytes()
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ArtifactBuildError("invalid ZIP package") from exc
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise ArtifactBuildError("ZIP package has too many entries")
        total = 0
        names: set[str] = set()
        members: dict[str, bytes] = {}
        for info in infos:
            name = _safe_relative_name(info.filename)
            folded = name.casefold()
            if folded in names:
                raise ArtifactBuildError(f"duplicate case-insensitive ZIP member: {name}")
            names.add(folded)
            if info.file_size > MAX_SINGLE_ENTRY_BYTES:
                raise ArtifactBuildError(f"ZIP member exceeds size limit: {name}")
            total += info.file_size
            if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ArtifactBuildError("ZIP package exceeds expanded-size limit")
            if info.file_size and info.compress_size == 0:
                raise ArtifactBuildError(f"ZIP member has invalid compression metadata: {name}")
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise ArtifactBuildError(f"ZIP member exceeds compression-ratio limit: {name}")
            members[name] = archive.read(info)
    return _components_from_members(
        members, package, source_package_sha256=sha256_bytes(payload)
    )


def _read_directory(package: PackageInput) -> ShapefileComponents:
    root = package.path.resolve()
    members: dict[str, bytes] = {}
    folded_names: set[str] = set()
    total = 0
    files = sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda path: path.as_posix().casefold(),
    )
    if len(files) > MAX_ARCHIVE_ENTRIES:
        raise ArtifactBuildError("extracted package has too many entries")
    for path in files:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError as exc:
            raise ArtifactBuildError("extracted package path escapes its root") from exc
        name = _safe_relative_name(relative)
        folded = name.casefold()
        if folded in folded_names:
            raise ArtifactBuildError(f"duplicate case-insensitive package member: {name}")
        folded_names.add(folded)
        size = resolved.stat().st_size
        if size > MAX_SINGLE_ENTRY_BYTES:
            raise ArtifactBuildError(f"package member exceeds size limit: {name}")
        total += size
        if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ArtifactBuildError("extracted package exceeds expanded-size limit")
        members[name] = resolved.read_bytes()
    return _components_from_members(
        members, package, source_package_sha256=_members_sha(members)
    )


def read_package(package: PackageInput) -> ShapefileComponents:
    path = Path(package.path)
    suffix = path.suffix.casefold()
    if suffix in {".rar", ".7z"}:
        raise UnsupportedDatasetError(
            f"{suffix} archives are unsupported in-process; extract with an approved operator tool and supply the extracted directory"
        )
    if path.is_dir():
        return _read_directory(package)
    if suffix != ".zip":
        raise UnsupportedDatasetError("package must be a safe ZIP or an operator-extracted directory")
    if not path.is_file():
        raise ArtifactBuildError(f"package does not exist: {path.name}")
    return _read_zip(package)


def _read_records(
    components: ShapefileComponents,
    index_record: IndexRecord,
    dataset_version: str,
    source_package_sha256: str,
) -> list[Any]:
    try:
        source_crs = resolve_source_crs(
            components.prj.decode("utf-8-sig", errors="strict"),
            index_record.declared_crs_values,
        )
    except UnicodeDecodeError as exc:
        raise CrsInvalidError("shapefile .prj is not UTF-8 text") from exc
    try:
        reader = shapefile.Reader(
            shp=io.BytesIO(components.shp),
            shx=io.BytesIO(components.shx),
            dbf=io.BytesIO(components.dbf),
            encoding=components.encoding,
        )
        field_names = [field[0] for field in reader.fields[1:]]
        results = []
        for shape_record in reader.iterShapeRecords():
            attributes = dict(zip(field_names, list(shape_record.record), strict=True))
            geometry = geometry_shape(shape_record.shape.__geo_interface__)
            results.append(
                normalize_feature(
                    geometry,
                    attributes,
                    index_record,
                    source_crs=source_crs,
                    dataset_version=dataset_version,
                    source_package_sha256=source_package_sha256,
                )
            )
        return results
    except (CrsInvalidError, UnsupportedDatasetError):
        raise
    except Exception as exc:
        raise ArtifactBuildError(f"shapefile decode failed: {type(exc).__name__}") from exc


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    return str(value)


def _feature_record(feature: NormalizedFeature) -> dict[str, Any]:
    return {
        "announcement_date": feature.announcement_date,
        "announcement_no": feature.announcement_no,
        "canonical_category": feature.canonical_category,
        "dataset_version": feature.dataset_version,
        "geometry_wkb_hex": wkb.dumps(feature.geometry, hex=True, output_dimension=2, byte_order=1),
        "official_category": feature.official_category,
        "official_name": feature.official_name,
        "original_attributes": _json_value(dict(feature.original_attributes)),
        "sensitivity_area_no": feature.sensitivity_area_no,
        "source_agency": feature.source_agency,
        "source_crs": feature.source_crs,
        "source_index_no": feature.source_index_no,
        "source_package_sha256": feature.source_package_sha256,
        "source_url": feature.source_url,
        "target_crs": feature.target_crs,
    }


def _feature_sort_key(feature: NormalizedFeature) -> tuple[str, ...]:
    return (
        feature.canonical_category,
        feature.sensitivity_area_no,
        feature.announcement_no,
        feature.official_name,
        wkb.dumps(feature.geometry, hex=True, output_dimension=2, byte_order=1),
    )


def _serialize_artifact(features: Iterable[NormalizedFeature], dataset_version: str) -> bytes:
    document = {
        "dataset": DATASET_NAME,
        "dataset_version": dataset_version,
        "schema": ARTIFACT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "target_crs": "EPSG:4326",
        "features": [_feature_record(feature) for feature in sorted(features, key=_feature_sort_key)],
    }
    return _deterministic_gzip(_canonical_json(document))


def _quarantine_record(record: QuarantineRecord) -> dict[str, Any]:
    return {
        "geometry_type": record.geometry_type,
        "original_attributes": _json_value(dict(record.original_attributes)),
        "reason": record.reason,
        "source_index_no": record.source_index_no,
    }


def _serialize_quarantine(records: Iterable[QuarantineRecord], dataset_version: str) -> bytes:
    rows = sorted(
        (_quarantine_record(record) for record in records),
        key=lambda row: (row["source_index_no"], row["reason"], row.get("geometry_type") or ""),
    )
    return _deterministic_gzip(
        _canonical_json(
            {
                "dataset": DATASET_NAME,
                "dataset_version": dataset_version,
                "schema": QUARANTINE_SCHEMA,
                "schema_version": SCHEMA_VERSION,
                "records": rows,
            }
        )
    )


def _stats_manifest(stats: NormalizationStats) -> dict[str, Any]:
    payload = asdict(stats)
    return {
        key: dict(sorted(value.items())) if isinstance(value, dict) else value
        for key, value in payload.items()
    }


def build_processed_artifact(
    index_csv_bytes: bytes,
    packages: list[PackageInput],
    *,
    dataset_version: str,
    source_vintage: str,
) -> BuildResult:
    """Build deterministic processed outputs from operator-supplied local inputs."""

    dataset_version = validate_dataset_version(dataset_version)
    if not source_vintage.strip():
        raise ArtifactBuildError("source_vintage is required")
    index_records = parse_index_csv(index_csv_bytes)
    package_by_index: dict[str, PackageInput] = {}
    for package in packages:
        if package.index_no in package_by_index:
            raise UnsupportedDatasetError(f"duplicate package mapping for index {package.index_no}")
        package_by_index[package.index_no] = package
    expected = {record.source_index_no for record in index_records}
    if set(package_by_index) != expected:
        raise UnsupportedDatasetError("package mappings must exactly cover the official index rows")

    outcomes = []
    source_packages: list[dict[str, Any]] = []
    for index_record in index_records:
        package = package_by_index[index_record.source_index_no]
        components = read_package(package)
        source_sha = components.source_package_sha256
        if package.expected_sha256 and source_sha.lower() != package.expected_sha256.lower():
            raise ArtifactBuildError(
                f"source SHA256 mismatch for index {index_record.source_index_no}"
            )
        outcomes.extend(
            _read_records(components, index_record, dataset_version, source_sha)
        )
        source_packages.append(
            {
                "index_no": index_record.source_index_no,
                "official_category": index_record.official_category,
                "sensitivity_area_no": index_record.sensitivity_area_no,
                "selected_shapefile": components.relative_shp_path,
                "source_crs_declarations": list(index_record.declared_crs_values),
                "source_package_sha256": source_sha,
                "source_url": index_record.source_url,
            }
        )

    features, quarantine, stats = summarize_normalization(outcomes)
    artifact_bytes = _serialize_artifact(features, dataset_version)
    quarantine_bytes = _serialize_quarantine(quarantine, dataset_version)
    stats_payload = _stats_manifest(stats)
    manifest = {
        "artifact_sha256": sha256_bytes(artifact_bytes),
        "dataset": DATASET_NAME,
        "dataset_version": dataset_version,
        "feature_count": len(features),
        "manifest_schema": MANIFEST_SCHEMA,
        "quality_status": "accepted" if features and not quarantine else "review_required",
        "quarantine_sha256": sha256_bytes(quarantine_bytes),
        "schema_version": SCHEMA_VERSION,
        "source_index_sha256": sha256_bytes(index_csv_bytes),
        "source_packages": sorted(source_packages, key=lambda row: row["index_no"]),
        "source_vintage": source_vintage,
        "target_crs": "EPSG:4326",
        **stats_payload,
    }
    manifest_bytes = _canonical_json(manifest)
    return BuildResult(
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        artifact_bytes=artifact_bytes,
        quarantine_bytes=quarantine_bytes,
        features=features,
        quarantine=quarantine,
        stats=stats,
    )


def load_artifact(payload: bytes) -> tuple[dict[str, Any], list[NormalizedFeature]]:
    try:
        document = json.loads(gzip.decompress(payload).decode("utf-8"))
        if not isinstance(document, dict):
            raise TypeError("artifact root is not an object")
        if document.get("schema") != ARTIFACT_SCHEMA or document.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported artifact schema")
        dataset_version = document["dataset_version"]
        if document.get("target_crs") != "EPSG:4326" or not isinstance(dataset_version, str):
            raise ValueError("invalid artifact metadata")
        validate_dataset_version(dataset_version)
        rows = document.get("features")
        if not isinstance(rows, list):
            raise TypeError("artifact features are not a list")
        features: list[NormalizedFeature] = []
        for row in rows:
            if not isinstance(row, dict):
                raise TypeError("artifact feature is not an object")
            geometry = wkb.loads(row["geometry_wkb_hex"], hex=True)
            if geometry.geom_type not in {"Polygon", "MultiPolygon"} or geometry.is_empty or not geometry.is_valid:
                raise ValueError("artifact contains invalid polygon geometry")
            if not all(math.isfinite(x) and math.isfinite(y) and -180 <= x <= 180 and -90 <= y <= 90
                       for x, y in get_coordinates(geometry)):
                raise ValueError("artifact polygon coordinates are outside finite WGS84 bounds")
            if row["dataset_version"] != dataset_version or row["target_crs"] != "EPSG:4326":
                raise ValueError("artifact feature metadata mismatch")
            official_category = row["official_category"]
            if OFFICIAL_CATEGORY_MAP.get(official_category) != row["canonical_category"]:
                raise ValueError("artifact feature category mapping mismatch")
            if not isinstance(row["original_attributes"], dict):
                raise TypeError("artifact original_attributes is not an object")
            features.append(
                NormalizedFeature(
                    official_category=row["official_category"],
                    canonical_category=row["canonical_category"],
                    official_name=row["official_name"],
                    sensitivity_area_no=row["sensitivity_area_no"],
                    announcement_no=row["announcement_no"],
                    announcement_date=row["announcement_date"],
                    source_agency=row["source_agency"],
                    source_url=row["source_url"],
                    source_index_no=row["source_index_no"],
                    source_crs=row["source_crs"],
                    target_crs=row["target_crs"],
                    dataset_version=row["dataset_version"],
                    source_package_sha256=row["source_package_sha256"],
                    original_attributes=row["original_attributes"],
                    geometry=geometry,
                )
            )
        return document, features
    except Exception as exc:
        if isinstance(exc, ArtifactBuildError):
            raise
        raise ArtifactBuildError(f"artifact decode failed: {type(exc).__name__}") from exc


def write_build_outputs(result: BuildResult, output_dir: Path) -> dict[str, Path]:
    version = validate_dataset_version(result.manifest["dataset_version"])
    target = Path(output_dir) / version
    target.mkdir(parents=True, exist_ok=True)
    paths = {
        "artifact": target / "features.json.gz",
        "manifest": target / "manifest.json",
        "quarantine": target / "quarantine.json.gz",
    }
    paths["artifact"].write_bytes(result.artifact_bytes)
    paths["manifest"].write_bytes(result.manifest_bytes)
    paths["quarantine"].write_bytes(result.quarantine_bytes)
    return paths
