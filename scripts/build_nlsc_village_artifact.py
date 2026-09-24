"""Build a deterministic processed NLSC village-boundary artifact."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET = "nlsc-village-boundary-7440"
SCHEMA_VERSION = "nlsc-village-boundary-v1"
SOURCE_VINTAGE = "ROC-1150817-main-with-ROC-1150624-Sanhe"
SOURCE_CRS = "EPSG:3826"
TARGET_CRS = "EPSG:4326"
DEFAULT_RAW_ROOT = Path(r"C:\Projects\_ris-population-test\raw\nlsc\village-boundary\2026-08-25\extracted")
DEFAULT_OUTPUT_ROOT = Path(r"C:\Projects\_ris-population-test\processed\nlsc\village-boundary\v1")
REQUIRED_FIELDS = ("VILLCODE", "COUNTYNAME", "TOWNNAME", "VILLNAME")


class ArtifactBuildError(RuntimeError):
    """The official source failed the processed artifact contract."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _field_names(reader: shapefile.Reader) -> list[str]:
    return [str(item[0]) for item in reader.fields[1:]]


def _value(record: Any, name: str) -> str:
    value = record[name]
    return "" if value is None else str(value)


def _vintage(path: Path) -> str:
    marker = path.stem.rsplit("_", 1)[-1]
    return f"ROC-{marker}" if marker.isdigit() else SOURCE_VINTAGE


def _json_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _gzip_bytes(data: bytes) -> bytes:
    import io

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0) as handle:
        handle.write(data)
    return buffer.getvalue()


def _normalize_geometry(geometry: Any, path: Path) -> Any:
    if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ArtifactBuildError(f"{path.name}: source geometry is empty or non-polygon")
    if not geometry.is_valid:
        geometry = make_valid(geometry)
    if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"} or not geometry.is_valid:
        raise ArtifactBuildError(f"{path.name}: normalized geometry is invalid")
    return geometry


def build_feature_collection(raw_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = sorted(raw_root.rglob("*.shp"))
    if not paths:
        raise ArtifactBuildError(f"no SHP files found under {raw_root}")
    features: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    source_files: list[str] = []
    geometry_type_counts = {"Polygon": 0, "MultiPolygon": 0}
    invalid_count = 0
    empty_count = 0
    non_polygon_count = 0
    transformed_count = 0

    for path in paths:
        reader = shapefile.Reader(str(path), encoding="utf-8")
        fields = _field_names(reader)
        missing = [field for field in REQUIRED_FIELDS if field not in fields]
        if missing:
            raise ArtifactBuildError(f"{path.name}: missing fields {missing}")
        prj_path = path.with_suffix(".prj")
        if not prj_path.exists():
            raise ArtifactBuildError(f"{path.name}: missing PRJ")
        try:
            source_crs = CRS.from_wkt(prj_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ArtifactBuildError(f"{path.name}: invalid PRJ") from exc
        if source_crs.to_epsg() != 3826:
            raise ArtifactBuildError(f"{path.name}: expected EPSG:3826, got {source_crs.to_authority()}")
        transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
        source_files.append(path.name)
        for item in reader.iterShapeRecords():
            source_geometry = shape(item.shape.__geo_interface__)
            if source_geometry.is_empty:
                empty_count += 1
                raise ArtifactBuildError(f"{path.name}: empty geometry")
            if source_geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                non_polygon_count += 1
                raise ArtifactBuildError(f"{path.name}: non-polygon geometry")
            geometry = transform(transformer.transform, source_geometry)
            transformed_count += 1
            was_invalid = not geometry.is_valid
            geometry = _normalize_geometry(geometry, path)
            invalid_count += int(was_invalid)
            village_code = _value(item.record, "VILLCODE")
            if not village_code:
                raise ArtifactBuildError(f"{path.name}: blank VILLCODE")
            if village_code in seen_codes:
                raise ArtifactBuildError(f"duplicate VILLCODE: {village_code}")
            seen_codes.add(village_code)
            county_name = _value(item.record, "COUNTYNAME")
            town_name = _value(item.record, "TOWNNAME")
            village_name = _value(item.record, "VILLNAME")
            geometry_type_counts[geometry.geom_type] += 1
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "village_code": village_code,
                        "county_name": county_name,
                        "town_name": town_name,
                        "village_name": village_name,
                        "source_vintage": _vintage(path),
                        "source_dataset": DATASET,
                        "source_crs": SOURCE_CRS,
                        "target_crs": TARGET_CRS,
                        "source_provenance": "data.gov.tw dataset 7440 / NLSC official Village Boundary Map",
                    },
                    "geometry": mapping(geometry),
                }
            )
        reader.close()

    features.sort(
        key=lambda feature: (
            feature["properties"]["village_code"],
            feature["properties"]["county_name"],
            feature["properties"]["town_name"],
            feature["properties"]["village_name"],
            json.dumps(feature["geometry"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    )
    document = {
        "type": "FeatureCollection",
        "schema_version": SCHEMA_VERSION,
        "dataset": DATASET,
        "source_vintage": SOURCE_VINTAGE,
        "source_crs": SOURCE_CRS,
        "target_crs": TARGET_CRS,
        "features": features,
    }
    audit = {
        "source_files": source_files,
        "feature_count": len(features),
        "demographic_feature_count": sum(bool(item["properties"]["village_name"]) for item in features),
        "special_geometry_count": sum(not bool(item["properties"]["village_name"]) for item in features),
        "polygon_count": geometry_type_counts["Polygon"],
        "multipolygon_count": geometry_type_counts["MultiPolygon"],
        "invalid_geometry_count": invalid_count,
        "empty_geometry_count": empty_count,
        "non_polygon_geometry_count": non_polygon_count,
        "transformed_count": transformed_count,
    }
    return document, audit


def build_artifact(raw_root: Path, output_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    document, audit = build_feature_collection(raw_root)
    json_payload = _json_bytes(document)
    compressed = _gzip_bytes(json_payload)
    artifact_path = output_root / "features.json.gz"
    manifest_path = output_root / "manifest.json"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset": DATASET,
        "source_vintage": SOURCE_VINTAGE,
        "source_crs": SOURCE_CRS,
        "target_crs": TARGET_CRS,
        "feature_count": audit["feature_count"],
        "demographic_feature_count": audit["demographic_feature_count"],
        "special_geometry_count": audit["special_geometry_count"],
        "invalid_geometry_count": audit["invalid_geometry_count"],
        "empty_geometry_count": audit["empty_geometry_count"],
        "non_polygon_geometry_count": audit["non_polygon_geometry_count"],
        "polygon_count": audit["polygon_count"],
        "multipolygon_count": audit["multipolygon_count"],
        "sha256": _sha256(compressed),
        "artifact_size_bytes": len(compressed),
        "generated_from": "data.gov.tw dataset 7440 NLSC official Village Boundary Map",
        "build_contract": "sorted feature identity + canonical UTF-8 JSON + gzip mtime=0 + EPSG:3826 to EPSG:4326 transform",
        "source_files": audit["source_files"],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(compressed)
    manifest_path.write_bytes(_json_bytes(manifest) + b"\n")
    return {
        "artifact_path": str(artifact_path),
        "manifest_path": str(manifest_path),
        "build_ms": round((time.perf_counter() - started) * 1000, 3),
        "manifest": manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic NLSC village-boundary artifact")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    result = build_artifact(args.raw_root, args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
