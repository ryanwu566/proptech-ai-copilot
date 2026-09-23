"""Processed-artifact builder support for WRA flood potential SHP datasets.

Phase 2 scope: convert an operator-provided official WRA flood SHP ZIP into a
compact, deterministic ``processed`` artifact that a future Cloud Run runtime
can load quickly.  This module:

* reuses the pure normalization logic in ``services.wra_flood_offline_dataset``
  (canonical Class mapping, ``make_valid`` normalization, CRS transform,
  malformed ``flood_dept`` flag),
* never touches ``WraFloodProvider`` or the Terrain Risk runtime,
* never contacts Cloudflare R2, a database, or a network,
* never uses ``pickle``; geometry is serialized as base64-encoded WKB inside a
  deterministic gzip-compressed JSON document.

Large official SHP/ZIP inputs and processed artifacts must never be committed
to the repository; they belong in the ``proptech-government-data`` R2 bucket
(``raw/wra/flood/...`` and ``processed/wra/flood/...``).
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from pyproj import CRS
from shapely import wkb as shapely_wkb
from shapely.geometry import shape as shapely_shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from shapely.validation import make_valid

from services.wra_flood_offline_dataset import (
    CLASS_TO_CANONICAL_DEPTH,
    SOURCE_CRS,
    TARGET_CRS,
    FloodFeature,
    _TRANSFORMER_3826_TO_4326,
    _coerce_class,
    is_flood_dept_malformed,
    match_point,
)


# --- Safety limits for ZIP extraction --------------------------------------
MAX_ARCHIVE_ENTRIES = 64
MAX_SINGLE_ENTRY_BYTES = 120 * 1024 * 1024  # 120 MB (SHP ~45 MB)
MAX_TOTAL_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
MAX_COMPRESSION_RATIO = 500

DATASET_NAME = "wra_flood_potential"
PROVIDER_ID = "wra_flood_hazard_map"
DEFAULT_AREA_TOLERANCE_PCT = 0.01  # 0.01 percent

_SHP_COMPONENTS = (".shp", ".shx", ".dbf", ".prj")


class ArtifactBuildError(ValueError):
    """Raised when the raw ZIP cannot be safely converted to an artifact."""


@dataclass(frozen=True)
class ShpComponents:
    shp: bytes
    shx: bytes
    dbf: bytes
    prj: str
    encoding: str
    base_name: str


# ---------------------------------------------------------------------------
# 1. Raw ZIP ingestion (safe extraction)
# ---------------------------------------------------------------------------


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_safe_member_name(name: str) -> bool:
    """Reject absolute paths, drive letters, and parent traversal (zip-slip)."""

    if not name or name.endswith("/"):
        return False
    pure = PurePosixPath(name.replace("\\", "/"))
    if pure.is_absolute():
        return False
    parts = pure.parts
    if any(part == ".." for part in parts):
        return False
    # Reject Windows drive-letter style prefixes such as "C:".
    if ":" in parts[0]:
        return False
    return True


def extract_shp_components(zip_bytes: bytes) -> ShpComponents:
    """Safely locate the unique .shp/.shx/.dbf/.prj components inside the ZIP.

    Enforces entry-count, per-entry, total-size, and compression-ratio limits,
    and rejects zip-slip member names.  Requires exactly one of each SHP
    component (shared stem).  Reads .cpg for encoding when present.
    """

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise ArtifactBuildError(f"archive has too many entries: {len(infos)} > {MAX_ARCHIVE_ENTRIES}")

        total = 0
        for info in infos:
            if not _is_safe_member_name(info.filename):
                raise ArtifactBuildError(f"unsafe archive member name: {info.filename!r}")
            if info.file_size > MAX_SINGLE_ENTRY_BYTES:
                raise ArtifactBuildError(f"archive member too large: {info.filename}")
            if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise ArtifactBuildError(f"archive member compression ratio too high: {info.filename}")
            total += info.file_size
        if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ArtifactBuildError(f"archive uncompressed size too large: {total}")

        by_ext: dict[str, list[str]] = {ext: [] for ext in _SHP_COMPONENTS}
        cpg_names: list[str] = []
        for info in infos:
            lower = info.filename.lower()
            for ext in _SHP_COMPONENTS:
                if lower.endswith(ext):
                    by_ext[ext].append(info.filename)
            if lower.endswith(".cpg"):
                cpg_names.append(info.filename)

        for ext in _SHP_COMPONENTS:
            found = by_ext[ext]
            if len(found) == 0:
                raise ArtifactBuildError(f"missing required SHP component: *{ext}")
            if len(found) > 1:
                raise ArtifactBuildError(f"ambiguous SHP component *{ext}: {found}")

        shp_name = by_ext[".shp"][0]
        base_name = shp_name[: -len(".shp")]
        for ext in (".shx", ".dbf", ".prj"):
            if by_ext[ext][0][: -len(ext)] != base_name:
                raise ArtifactBuildError(f"SHP components do not share a common stem near {ext}")

        encoding = "utf-8"
        if cpg_names:
            cpg_value = archive.read(cpg_names[0]).decode("ascii", "replace").strip()
            if cpg_value:
                encoding = cpg_value

        return ShpComponents(
            shp=archive.read(by_ext[".shp"][0]),
            shx=archive.read(by_ext[".shx"][0]),
            dbf=archive.read(by_ext[".dbf"][0]),
            prj=archive.read(by_ext[".prj"][0]).decode("utf-8", "replace"),
            encoding=_normalize_encoding(encoding),
            base_name=base_name,
        )


def _normalize_encoding(encoding: str) -> str:
    normalized = encoding.strip().lower().replace("_", "-")
    if normalized in {"utf-8", "utf8"}:
        return "utf-8"
    return encoding.strip()


# ---------------------------------------------------------------------------
# 2. CRS validation
# ---------------------------------------------------------------------------


def validate_source_crs(prj_wkt: str, *, expected: str = SOURCE_CRS) -> CRS:
    """Confirm the .prj CRS is equivalent to the expected EPSG using pyproj.

    Never trusts the filename; compares parsed WKT against the expected CRS.
    """

    if not prj_wkt or not prj_wkt.strip():
        raise ArtifactBuildError("missing .prj CRS definition")
    try:
        source = CRS.from_wkt(prj_wkt)
    except Exception as exc:  # noqa: BLE001 - surface a clear build error
        raise ArtifactBuildError(f"unparseable .prj CRS: {exc}") from exc
    expected_crs = CRS.from_user_input(expected)
    if not source.equals(expected_crs) and source.to_epsg() != expected_crs.to_epsg():
        raise ArtifactBuildError(
            f"source CRS is not equivalent to {expected} (got {source.to_epsg() or source.name})"
        )
    return source


# ---------------------------------------------------------------------------
# 3. SHP -> normalized features
# ---------------------------------------------------------------------------


def _drop_z(geometry: BaseGeometry) -> BaseGeometry:
    if not geometry.has_z:
        return geometry
    return shapely_transform(lambda *coords: coords[:2], geometry)


def read_shp_records(components: ShpComponents) -> list[dict[str, Any]]:
    """Parse raw records (attributes + EPSG:3826 geometry) via pyshp.

    Geometry is returned as a 2D Shapely geometry still in the source CRS.
    """

    import shapefile  # pyshp

    reader = shapefile.Reader(
        shp=io.BytesIO(components.shp),
        shx=io.BytesIO(components.shx),
        dbf=io.BytesIO(components.dbf),
        encoding=components.encoding,
    )
    records: list[dict[str, Any]] = []
    for shape_record in reader.iterShapeRecords():
        attributes = shape_record.record.as_dict()
        geo = shape_record.shape.__geo_interface__
        geometry = _drop_z(shapely_shape(geo)) if geo and geo.get("coordinates") else None
        records.append(
            {
                "flood_dept": attributes.get("flood_dept"),
                "Class": attributes.get("Class"),
                "Town": attributes.get("Town"),
                "CityName": attributes.get("CityName"),
                "TownName": attributes.get("TownName"),
                "City": attributes.get("City"),
                "geometry_3826": geometry,
            }
        )
    return records


@dataclass
class BuildStats:
    feature_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    repaired_geometry_count: int = 0
    malformed_flood_dept_count: int = 0
    invalid_geometry_count: int = 0
    null_or_empty_geometry_count: int = 0
    invalid_class_count: int = 0
    area_before_m2: float = 0.0
    area_after_m2: float = 0.0
    class_distribution: dict[int, int] | None = None
    geometry_type_distribution: dict[str, int] | None = None
    city_codes: set[str] | None = None
    town_codes: set[str] | None = None
    rejections: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class ProcessedFeature:
    """A processed feature with WGS84 geometry, ready for serialization."""

    class_value: int
    canonical_depth: str
    flood_dept_raw: Any
    flood_dept_malformed: bool
    city_code: str | None
    city_name: str | None
    town_code: str | None
    town_name: str | None
    geometry_wgs84: BaseGeometry


def normalize_records(records: Iterable[dict[str, Any]]) -> tuple[list[ProcessedFeature], BuildStats]:
    """Normalize raw EPSG:3826 records into WGS84 processed features.

    Reuses the Phase 1 canonical mapping, ``make_valid`` normalization, malformed
    ``flood_dept`` flag, and CRS transform.  Also measures area conservation in
    the source CRS (EPSG:3826) before/after ``make_valid``.
    """

    features: list[ProcessedFeature] = []
    stats = BuildStats(
        class_distribution={},
        geometry_type_distribution={},
        city_codes=set(),
        town_codes=set(),
        rejections=[],
    )
    for index, record in enumerate(records):
        stats.feature_count += 1
        class_value = _coerce_class(record.get("Class"))
        if class_value is None:
            stats.rejected_count += 1
            stats.invalid_class_count += 1
            stats.rejections.append({"index": index, "reason": "invalid_class"})
            continue

        raw_geometry = record.get("geometry_3826")
        if raw_geometry is None or not isinstance(raw_geometry, BaseGeometry) or raw_geometry.is_empty:
            stats.rejected_count += 1
            stats.null_or_empty_geometry_count += 1
            stats.rejections.append({"index": index, "reason": "null_or_empty_geometry"})
            continue

        # Area conservation is measured in the source CRS (metres).
        area_before = raw_geometry.area
        was_valid = raw_geometry.is_valid
        repaired = make_valid(raw_geometry) if not was_valid else raw_geometry

        if repaired is None or repaired.is_empty or repaired.geom_type not in {"Polygon", "MultiPolygon"} or not repaired.is_valid:
            stats.rejected_count += 1
            stats.invalid_geometry_count += 1
            stats.rejections.append({"index": index, "reason": "geometry_not_polygonal_after_make_valid"})
            continue

        if not was_valid:
            stats.repaired_geometry_count += 1
        stats.area_before_m2 += area_before
        stats.area_after_m2 += repaired.area

        geometry_wgs84 = _reproject(repaired)

        flood_dept_raw = record.get("flood_dept")
        malformed = is_flood_dept_malformed(flood_dept_raw)
        if malformed:
            stats.malformed_flood_dept_count += 1

        city_code = _clean_text(record.get("City"))
        town_code = _clean_text(record.get("Town"))
        if city_code:
            stats.city_codes.add(city_code)
        if town_code:
            stats.town_codes.add(town_code)

        stats.accepted_count += 1
        stats.class_distribution[class_value] = stats.class_distribution.get(class_value, 0) + 1
        gtype = geometry_wgs84.geom_type
        stats.geometry_type_distribution[gtype] = stats.geometry_type_distribution.get(gtype, 0) + 1

        features.append(
            ProcessedFeature(
                class_value=class_value,
                canonical_depth=CLASS_TO_CANONICAL_DEPTH[class_value],
                flood_dept_raw=flood_dept_raw,
                flood_dept_malformed=malformed,
                city_code=city_code,
                city_name=_clean_text(record.get("CityName")),
                town_code=town_code,
                town_name=_clean_text(record.get("TownName")),
                geometry_wgs84=geometry_wgs84,
            )
        )
    return features, stats


def _reproject(geometry: BaseGeometry) -> BaseGeometry:
    def _project(xs: Any, ys: Any, zs: Any = None) -> tuple[Any, ...]:
        lons, lats = _TRANSFORMER_3826_TO_4326.transform(xs, ys)
        if zs is None:
            return lons, lats
        return lons, lats, zs

    return shapely_transform(_project, geometry)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def area_difference_pct(before: float, after: float) -> float:
    if before == 0:
        return 0.0 if after == 0 else 100.0
    return abs(after - before) / before * 100.0


def verify_point_against_features(
    lon: float,
    lat: float,
    features: Iterable["ProcessedFeature"],
) -> dict[str, Any]:
    """Match a WGS84 (lon, lat) point against processed WGS84 features.

    Returns a coordinate-free result summary.  A miss reports ``matched=False``
    without any risk interpretation: a no-hit for one scenario is NOT a claim
    that the location is low-risk or safe.  When several features intersect the
    deepest ``Class`` (largest canonical range) is reported as primary.
    """

    from shapely.geometry import Point

    point = Point(float(lon), float(lat))
    hits = [feature for feature in features if feature.geometry_wgs84.intersects(point)]
    if not hits:
        return {"matched": False, "matched_count": 0, "primary": None}
    primary = max(hits, key=lambda feature: feature.class_value)
    return {
        "matched": True,
        "matched_count": len(hits),
        "primary": {
            "class": primary.class_value,
            "canonical_depth": primary.canonical_depth,
            "city_code": primary.city_code,
            "city_name": primary.city_name,
            "town_code": primary.town_code,
            "town_name": primary.town_name,
            "flood_dept_raw": primary.flood_dept_raw,
            "flood_dept_malformed": primary.flood_dept_malformed,
        },
    }


# ---------------------------------------------------------------------------
# 5. Processed artifact serialization (WKB + base64 inside gzip JSON)
# ---------------------------------------------------------------------------


def _feature_to_record(feature: ProcessedFeature) -> dict[str, Any]:
    return {
        "class": feature.class_value,
        "canonical_depth": feature.canonical_depth,
        "flood_dept_raw": feature.flood_dept_raw,
        "flood_dept_malformed": feature.flood_dept_malformed,
        "city_code": feature.city_code,
        "city_name": feature.city_name,
        "town_code": feature.town_code,
        "town_name": feature.town_name,
        "geometry_wkb_base64": base64.b64encode(shapely_wkb.dumps(feature.geometry_wgs84)).decode("ascii"),
    }


def serialize_artifact(features: Iterable[ProcessedFeature], *, scenario: str) -> bytes:
    """Serialize features to a deterministic gzip-compressed JSON document.

    Geometry uses base64-encoded WKB (never pickle).  JSON keys are sorted and
    gzip is written with ``mtime=0`` so the output is byte-for-byte reproducible.
    """

    document = {
        "schema": "wra_flood_processed_v1",
        "dataset": DATASET_NAME,
        "provider": PROVIDER_ID,
        "scenario": scenario,
        "source_crs": SOURCE_CRS,
        "target_crs": TARGET_CRS,
        "geometry_encoding": "wkb_base64",
        "features": [_feature_to_record(feature) for feature in features],
    }
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz:
        gz.write(payload)
    return buffer.getvalue()


def load_artifact(artifact_bytes: bytes) -> tuple[dict[str, Any], list[FloodFeature]]:
    """Load a processed artifact back into Phase 1 :class:`FloodFeature` objects."""

    payload = gzip.decompress(artifact_bytes)
    document = json.loads(payload.decode("utf-8"))
    features: list[FloodFeature] = []
    for record in document.get("features", []):
        geometry = shapely_wkb.loads(base64.b64decode(record["geometry_wkb_base64"]))
        features.append(
            FloodFeature(
                class_value=int(record["class"]),
                canonical_depth=record["canonical_depth"],
                geometry=geometry,
                flood_dept_raw=record.get("flood_dept_raw"),
                flood_dept_malformed=bool(record.get("flood_dept_malformed")),
                properties={
                    "city_code": record.get("city_code"),
                    "city_name": record.get("city_name"),
                    "town_code": record.get("town_code"),
                    "town_name": record.get("town_name"),
                },
            )
        )
    return document, features


# ---------------------------------------------------------------------------
# 6. Manifest
# ---------------------------------------------------------------------------


def build_manifest(
    *,
    scenario: str,
    source_url: str,
    source_sha256: str,
    source_size_bytes: int,
    artifact_sha256: str,
    stats: BuildStats,
    area_tolerance_pct: float,
) -> dict[str, Any]:
    """Assemble the processed-artifact manifest (no local absolute paths)."""

    diff_pct = area_difference_pct(stats.area_before_m2, stats.area_after_m2)
    quality_status = "verified" if diff_pct <= area_tolerance_pct and stats.accepted_count > 0 else "review_required"
    return {
        "dataset": DATASET_NAME,
        "provider": PROVIDER_ID,
        "scenario": scenario,
        "source_url": source_url,
        "source_crs": SOURCE_CRS,
        "target_crs": TARGET_CRS,
        "source_sha256": source_sha256,
        "artifact_sha256": artifact_sha256,
        "source_size_bytes": source_size_bytes,
        "feature_count": stats.feature_count,
        "accepted_count": stats.accepted_count,
        "rejected_count": stats.rejected_count,
        "repaired_geometry_count": stats.repaired_geometry_count,
        "malformed_flood_dept_count": stats.malformed_flood_dept_count,
        "class_distribution": dict(sorted((stats.class_distribution or {}).items())),
        "geometry_type_distribution": dict(sorted((stats.geometry_type_distribution or {}).items())),
        "area_before_m2": stats.area_before_m2,
        "area_after_m2": stats.area_after_m2,
        "area_difference_pct": diff_pct,
        "city_count": len(stats.city_codes or set()),
        "town_count": len(stats.town_codes or set()),
        "quality_status": quality_status,
    }


# ---------------------------------------------------------------------------
# End-to-end build orchestration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuildResult:
    manifest: dict[str, Any]
    artifact_bytes: bytes
    features: list[ProcessedFeature]
    stats: BuildStats


def build_processed_artifact(
    zip_bytes: bytes,
    *,
    scenario: str,
    source_url: str,
    expected_source_sha256: str | None = None,
    area_tolerance_pct: float = DEFAULT_AREA_TOLERANCE_PCT,
) -> BuildResult:
    """Build a processed artifact + manifest from raw ZIP bytes (in memory)."""

    source_sha256 = sha256_bytes(zip_bytes)
    if expected_source_sha256 and source_sha256.lower() != expected_source_sha256.lower():
        raise ArtifactBuildError(
            f"source SHA256 mismatch: expected {expected_source_sha256}, got {source_sha256}"
        )

    components = extract_shp_components(zip_bytes)
    validate_source_crs(components.prj)
    records = read_shp_records(components)
    features, stats = normalize_records(records)
    if not features:
        raise ArtifactBuildError("no valid features produced from SHP")

    artifact_bytes = serialize_artifact(features, scenario=scenario)
    artifact_sha256 = sha256_bytes(artifact_bytes)
    manifest = build_manifest(
        scenario=scenario,
        source_url=source_url,
        source_sha256=source_sha256,
        source_size_bytes=len(zip_bytes),
        artifact_sha256=artifact_sha256,
        stats=stats,
        area_tolerance_pct=area_tolerance_pct,
    )
    return BuildResult(manifest=manifest, artifact_bytes=artifact_bytes, features=features, stats=stats)


def write_build_outputs(result: BuildResult, output_dir: Path, scenario: str) -> dict[str, Path]:
    """Write the artifact and manifest under ``output_dir/<scenario>/``.

    Writes only two files; never writes raw SHP/ZIP or absolute paths.
    """

    target_dir = output_dir / scenario
    target_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = target_dir / "features.json.gz"
    manifest_path = target_dir / "manifest.json"
    artifact_path.write_bytes(result.artifact_bytes)
    manifest_path.write_text(
        json.dumps(result.manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"artifact": artifact_path, "manifest": manifest_path}
