"""Truthful parcel providers, safe GIS upload parsing, and spatial analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import json
import math
from pathlib import PurePosixPath
import re
import time
from typing import Any, Callable, Protocol
from zipfile import BadZipFile, ZipFile

from defusedxml import ElementTree as SafeElementTree
from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform, unary_union
from shapely.validation import make_valid


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_FEATURES = 1_000
MAX_COORDINATES = 100_000
MAX_ARCHIVE_FILES = 100
MAX_EXPANDED_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
TAIWAN_PLAUSIBLE_BOUNDS = (117.0, 18.0, 124.5, 27.5)
POINT_LIMITATION = (
    "The analyzed coordinate is a location reference only. No parcel polygon, legal boundary, "
    "legal area, ownership, or lot identifier was determined."
)
UPLOAD_LIMITATION = (
    "USER_PROVIDED_GEOMETRY. The polygon was supplied by the user and is not an official "
    "cadastral boundary. Computed area is geometric, not legal area."
)


class ParcelGeometryError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code

    def detail(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class ParcelGeometryProvider(Protocol):
    def resolve(self, **kwargs: Any) -> dict[str, Any]: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1_000, 3)


class PointReferenceProvider:
    def resolve(self, *, latitude: float, longitude: float, checked_at: str | None = None, **_: Any) -> dict[str, Any]:
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ParcelGeometryError("INVALID_GEOMETRY", "The reference coordinate is outside valid bounds.")
        return {
            "status": "point_reference_only", "source": "point_reference", "geometry_type": "Point",
            "geometry": {"type": "Point", "coordinates": [float(longitude), float(latitude)]},
            "centroid": {"lat": float(latitude), "lng": float(longitude)},
            "crs_normalized": "EPSG:4326", "area_semantics": "not_available",
            "legal_boundary": False, "can_spatial_intersect": False, "geometry_validity": "VALID",
            "limitation": POINT_LIMITATION, "source_label": "POINT_REFERENCE",
            "checked_at": checked_at or _now(), "location_geometry_consistency": "NOT_CHECKED",
        }


@dataclass
class NlscCadastralProvider:
    """Future adapter that stays closed until endpoint and authorization are proven."""

    endpoint_verified: bool = False
    authorization_configured: bool = False
    resolver: Callable[..., dict[str, Any]] | None = None

    @property
    def enabled(self) -> bool:
        return self.endpoint_verified and self.authorization_configured and self.resolver is not None

    def resolve(self, **kwargs: Any) -> dict[str, Any]:
        if not self.enabled:
            return {
                "status": "unavailable", "source": "nlsc", "geometry_type": "Point",
                "crs_normalized": "EPSG:4326", "area_semantics": "not_available",
                "legal_boundary": False, "can_spatial_intersect": False, "geometry_validity": "INVALID",
                "limitation": "Official NLSC parcel vector is disabled: verified endpoint and authorization are not configured.",
                "source_label": "OFFICIAL_VECTOR_NOT_CONFIGURED", "checked_at": _now(),
            }
        evidence = self.resolver(**kwargs)
        if evidence.get("status") != "verified_official" or evidence.get("legal_boundary") is not True:
            raise ParcelGeometryError("INVALID_GEOMETRY", "The official provider returned an unverified contract.")
        return evidence


def _polygon_parts(geometry: BaseGeometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return [part for item in getattr(geometry, "geoms", []) for part in _polygon_parts(item)]


def _coordinate_count(geometry: BaseGeometry) -> int:
    return sum(len(part.exterior.coords) + sum(len(ring.coords) for ring in part.interiors) for part in _polygon_parts(geometry))


def _normalize_polygonal(geometry: BaseGeometry, *, plausibility_guard: bool = True) -> tuple[BaseGeometry, str, float]:
    started = time.perf_counter()
    if geometry.is_empty:
        raise ParcelGeometryError("INVALID_GEOMETRY", "The uploaded geometry is empty.")
    parts = _polygon_parts(geometry)
    if not parts:
        raise ParcelGeometryError("NO_POLYGON_FOUND", "The dataset does not contain Polygon or MultiPolygon geometry.")
    polygonal: BaseGeometry = unary_union(parts)
    validity = "VALID"
    if not polygonal.is_valid:
        repaired_parts = _polygon_parts(make_valid(polygonal))
        if not repaired_parts:
            raise ParcelGeometryError("INVALID_GEOMETRY", "Invalid topology could not be repaired safely.")
        polygonal, validity = unary_union(repaired_parts), "REPAIRED"
    if polygonal.is_empty or polygonal.area <= 0:
        raise ParcelGeometryError("INVALID_GEOMETRY", "The polygon has no usable area.")
    if _coordinate_count(polygonal) > MAX_COORDINATES:
        raise ParcelGeometryError("INVALID_GEOMETRY", f"Geometry exceeds {MAX_COORDINATES:,} coordinates.")
    bounds = polygonal.bounds
    if not all(math.isfinite(value) for value in bounds):
        raise ParcelGeometryError("INVALID_GEOMETRY", "Geometry contains non-finite coordinates.")
    if plausibility_guard:
        west, south, east, north = TAIWAN_PLAUSIBLE_BOUNDS
        if bounds[2] < west or bounds[0] > east or bounds[3] < south or bounds[1] > north:
            raise ParcelGeometryError("INVALID_GEOMETRY", "Geometry is outside the supported broad Taiwan region; check CRS and coordinate order.")
    return polygonal, validity, _elapsed_ms(started)


def _projected_crs(geometry: BaseGeometry) -> CRS:
    return CRS.from_epsg(3825 if geometry.centroid.x < 120 else 3826)


def _project(geometry: BaseGeometry, destination: CRS | None = None) -> BaseGeometry:
    transformer = Transformer.from_crs(4326, destination or _projected_crs(geometry), always_xy=True)
    return transform(transformer.transform, geometry)


def assess_location_geometry_consistency(
    geometry: BaseGeometry | dict[str, Any], *, latitude: float | None, longitude: float | None, tolerance_m: float = 100
) -> str:
    if latitude is None or longitude is None:
        return "NOT_CHECKED"
    polygon = shape(geometry) if isinstance(geometry, dict) else geometry
    point = Point(float(longitude), float(latitude))
    if polygon.covers(point):
        return "CONSISTENT"
    destination = _projected_crs(polygon)
    return "CONSISTENT" if _project(polygon, destination).distance(_project(point, destination)) <= tolerance_m else "POSSIBLE_MISMATCH"


def _evidence(
    geometry: BaseGeometry, *, source: str, crs_original: str, parse_ms: float,
    latitude: float | None, longitude: float | None, checked_at: str | None = None,
) -> dict[str, Any]:
    normalized, validity, validation_ms = _normalize_polygonal(geometry)
    centroid = normalized.centroid
    limitation = UPLOAD_LIMITATION + (" Topology was repaired; review the rendered shape before use." if validity == "REPAIRED" else "")
    return {
        "status": "user_provided", "source": source, "geometry_type": normalized.geom_type,
        "geometry": mapping(normalized), "centroid": {"lat": centroid.y, "lng": centroid.x},
        "bbox": list(normalized.bounds), "crs_original": crs_original, "crs_normalized": "EPSG:4326",
        "area_m2": round(_project(normalized).area, 2), "area_semantics": "computed_geometry_area",
        "legal_boundary": False, "can_spatial_intersect": True, "geometry_validity": validity,
        "limitation": limitation, "source_label": "USER_PROVIDED_GEOMETRY", "checked_at": checked_at or _now(),
        "location_geometry_consistency": assess_location_geometry_consistency(normalized, latitude=latitude, longitude=longitude),
        "timing_ms": {"parse_ms": parse_ms, "geometry_validation_ms": validation_ms},
    }


def _geojson(data: bytes) -> tuple[BaseGeometry, float]:
    started = time.perf_counter()
    try:
        document = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParcelGeometryError("PARSE_FAILED", "The GeoJSON file is not valid UTF-8 JSON.") from exc
    if not isinstance(document, dict):
        raise ParcelGeometryError("PARSE_FAILED", "The GeoJSON root must be an object.")
    kind = document.get("type")
    raw: list[dict[str, Any]] = []
    if kind == "FeatureCollection":
        features = document.get("features")
        if not isinstance(features, list):
            raise ParcelGeometryError("PARSE_FAILED", "FeatureCollection.features must be an array.")
        if len(features) > MAX_FEATURES:
            raise ParcelGeometryError("INVALID_GEOMETRY", f"GeoJSON exceeds {MAX_FEATURES:,} features.")
        for feature in features:
            if not isinstance(feature, dict) or feature.get("type") != "Feature" or not isinstance(feature.get("geometry"), dict):
                raise ParcelGeometryError("PARSE_FAILED", "GeoJSON contains a malformed Feature.")
            raw.append(feature["geometry"])
    elif kind == "Feature":
        if not isinstance(document.get("geometry"), dict):
            raise ParcelGeometryError("PARSE_FAILED", "GeoJSON Feature has no geometry.")
        raw = [document["geometry"]]
    elif kind in {"Polygon", "MultiPolygon"}:
        raw = [document]
    else:
        raise ParcelGeometryError("NO_POLYGON_FOUND", "Only GeoJSON Polygon and MultiPolygon are supported.")
    if not raw or any(item.get("type") not in {"Polygon", "MultiPolygon"} for item in raw):
        raise ParcelGeometryError("NO_POLYGON_FOUND", "Every uploaded GeoJSON feature must be polygonal.")
    try:
        return unary_union([shape(item) for item in raw]), _elapsed_ms(started)
    except (TypeError, ValueError, KeyError) as exc:
        raise ParcelGeometryError("INVALID_GEOMETRY", "GeoJSON polygon coordinates are malformed.") from exc


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first(element: Any, name: str) -> Any | None:
    return next((child for child in element.iter() if _local(child.tag) == name), None)


def _kml_coordinates(text: str | None) -> list[tuple[float, float]]:
    if not text or not text.strip():
        raise ParcelGeometryError("PARSE_FAILED", "KML polygon has no coordinates.")
    result: list[tuple[float, float]] = []
    try:
        for token in text.split():
            pieces = token.split(",")
            longitude, latitude = float(pieces[0]), float(pieces[1])
            if len(pieces) < 2 or not all(math.isfinite(value) for value in (longitude, latitude)):
                raise ValueError
            result.append((longitude, latitude))
    except (ValueError, IndexError) as exc:
        raise ParcelGeometryError("PARSE_FAILED", "KML contains malformed longitude,latitude coordinates.") from exc
    if result and result[0] != result[-1]:
        result.append(result[0])
    if len(result) < 4:
        raise ParcelGeometryError("INVALID_GEOMETRY", "KML polygon ring needs at least three positions.")
    return result


def _kml(data: bytes) -> tuple[BaseGeometry, float]:
    started = time.perf_counter()
    try:
        root = SafeElementTree.fromstring(data)
    except Exception as exc:
        raise ParcelGeometryError("PARSE_FAILED", "KML XML is malformed or contains prohibited entities.") from exc
    polygons: list[Polygon] = []
    for element in (item for item in root.iter() if _local(item.tag) == "Polygon"):
        outer = _first(element, "outerBoundaryIs")
        coordinates = _first(outer, "coordinates") if outer is not None else None
        if coordinates is None:
            raise ParcelGeometryError("PARSE_FAILED", "KML Polygon has no outer boundary.")
        holes = []
        for boundary in (item for item in element.iter() if _local(item.tag) == "innerBoundaryIs"):
            inner = _first(boundary, "coordinates")
            holes.append(_kml_coordinates(inner.text if inner is not None else None))
        polygons.append(Polygon(_kml_coordinates(coordinates.text), holes))
        if len(polygons) > MAX_FEATURES:
            raise ParcelGeometryError("INVALID_GEOMETRY", f"KML exceeds {MAX_FEATURES:,} polygons.")
    if not polygons:
        raise ParcelGeometryError("NO_POLYGON_FOUND", "The KML file contains no Polygon geometry.")
    return unary_union(polygons), _elapsed_ms(started)


def _safe_archive_path(name: str) -> str:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise ParcelGeometryError("PARSE_FAILED", "The ZIP contains an unsafe absolute path.")
    path = PurePosixPath(normalized)
    if ".." in path.parts:
        raise ParcelGeometryError("PARSE_FAILED", "The ZIP contains a path traversal entry.")
    return str(path).lower()


def _shapefile(data: bytes) -> tuple[BaseGeometry, str, float]:
    started = time.perf_counter()
    try:
        archive = ZipFile(BytesIO(data))
    except BadZipFile as exc:
        raise ParcelGeometryError("PARSE_FAILED", "The uploaded ZIP is not valid.") from exc
    with archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if not files or len(files) > MAX_ARCHIVE_FILES:
            raise ParcelGeometryError("PARSE_FAILED", "The ZIP has an unsafe or unsupported file count.")
        expanded, entries = 0, {}
        for item in files:
            path = _safe_archive_path(item.filename)
            expanded += item.file_size
            if expanded > MAX_EXPANDED_ARCHIVE_BYTES:
                raise ParcelGeometryError("FILE_TOO_LARGE", "Expanded ZIP exceeds 50 MB.", status_code=413)
            if item.file_size > 1_000_000 and item.file_size / max(item.compress_size, 1) > MAX_COMPRESSION_RATIO:
                raise ParcelGeometryError("PARSE_FAILED", "The ZIP has an unsafe compression ratio.")
            entries[path] = item
        shp = [path for path in entries if path.endswith(".shp")]
        if len(shp) != 1:
            raise ParcelGeometryError("MISSING_SHAPEFILE_COMPONENTS", "ZIP must contain exactly one .shp dataset.")
        stem = shp[0][:-4]
        required = {extension: f"{stem}{extension}" for extension in (".shp", ".shx", ".dbf")}
        missing = [extension for extension, path in required.items() if path not in entries]
        if missing:
            raise ParcelGeometryError("MISSING_SHAPEFILE_COMPONENTS", f"Shapefile ZIP is missing: {', '.join(missing)}.")
        prj = f"{stem}.prj"
        if prj not in entries:
            raise ParcelGeometryError("UNKNOWN_CRS", "Shapefile ZIP must include a readable .prj.")
        try:
            source_crs = CRS.from_wkt(archive.read(entries[prj]).decode("utf-8-sig"))
        except Exception as exc:
            raise ParcelGeometryError("UNKNOWN_CRS", "The Shapefile .prj CRS could not be identified.") from exc
        try:
            import shapefile
            reader = shapefile.Reader(
                shp=BytesIO(archive.read(entries[required[".shp"]])),
                shx=BytesIO(archive.read(entries[required[".shx"]])),
                dbf=BytesIO(archive.read(entries[required[".dbf"]])),
            )
            if len(reader) > MAX_FEATURES:
                raise ParcelGeometryError("INVALID_GEOMETRY", f"Shapefile exceeds {MAX_FEATURES:,} features.")
            geometries = [shape(record.__geo_interface__) for record in reader.iterShapes()]
            reader.close()
        except ParcelGeometryError:
            raise
        except Exception as exc:
            raise ParcelGeometryError("PARSE_FAILED", "Shapefile components are corrupt or inconsistent.") from exc
    if not geometries or any(item.geom_type not in {"Polygon", "MultiPolygon"} for item in geometries):
        raise ParcelGeometryError("NO_POLYGON_FOUND", "Shapefile contains no polygon dataset.")
    combined = unary_union(geometries)
    if source_crs != CRS.from_epsg(4326):
        try:
            transformer = Transformer.from_crs(source_crs, 4326, always_xy=True)
            combined = transform(transformer.transform, combined)
        except Exception as exc:
            raise ParcelGeometryError("UNKNOWN_CRS", "Shapefile CRS could not be transformed to EPSG:4326.") from exc
    label = f"EPSG:{source_crs.to_epsg()}" if source_crs.to_epsg() else source_crs.name
    return combined, label, _elapsed_ms(started)


class UploadedParcelProvider:
    def resolve(
        self, *, filename: str, data: bytes, latitude: float | None = None,
        longitude: float | None = None, checked_at: str | None = None, **_: Any,
    ) -> dict[str, Any]:
        if not data:
            raise ParcelGeometryError("PARSE_FAILED", "The uploaded file is empty.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ParcelGeometryError("FILE_TOO_LARGE", "Uploads are limited to 10 MB.", status_code=413)
        extension = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
        if extension in {".geojson", ".json"}:
            geometry, parse_ms = _geojson(data); source, crs = "uploaded_geojson", "EPSG:4326"
        elif extension == ".kml":
            geometry, parse_ms = _kml(data); source, crs = "uploaded_kml", "EPSG:4326"
        elif extension == ".zip":
            geometry, crs, parse_ms = _shapefile(data); source = "uploaded_shapefile"
        else:
            raise ParcelGeometryError("UNSUPPORTED_FORMAT", "Supported formats are GeoJSON, KML, and Shapefile ZIP.")
        return _evidence(geometry, source=source, crs_original=crs, parse_ms=parse_ms,
                         latitude=latitude, longitude=longitude, checked_at=checked_at)


def select_parcel_geometry(
    *, official: dict[str, Any] | None = None, uploaded: dict[str, Any] | None = None,
    latitude: float | None = None, longitude: float | None = None,
) -> dict[str, Any]:
    if official and official.get("status") == "verified_official" and official.get("legal_boundary") is True:
        return official
    if uploaded and uploaded.get("status") == "user_provided" and uploaded.get("geometry"):
        return uploaded
    if latitude is not None and longitude is not None:
        return PointReferenceProvider().resolve(latitude=latitude, longitude=longitude)
    return {
        "status": "unavailable", "source": "point_reference", "geometry_type": "Point",
        "crs_normalized": "EPSG:4326", "area_semantics": "not_available", "legal_boundary": False,
        "can_spatial_intersect": False, "geometry_validity": "INVALID", "source_label": "UNAVAILABLE",
        "limitation": "Neither verified parcel geometry nor a reference coordinate is available.", "checked_at": _now(),
    }


def resolve_parcel_geometry(
    *,
    official_provider: ParcelGeometryProvider | None = None,
    uploaded: dict[str, Any] | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """Resolve provider precedence while isolating an official-provider failure."""

    official = None
    if official_provider is not None:
        try:
            official = official_provider.resolve(latitude=latitude, longitude=longitude)
        except Exception:
            # A failed optional official adapter must not erase valid user geometry.
            official = None
    return select_parcel_geometry(official=official, uploaded=uploaded, latitude=latitude, longitude=longitude)


def spatial_intersection(
    parcel_geometry: dict[str, Any] | BaseGeometry | None,
    hazard_geometry: dict[str, Any] | BaseGeometry | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if parcel_geometry is None or hazard_geometry is None:
        return {"claim_type": "NO_GEOMETRY_AVAILABLE", "geometry_available": False,
                "timing_ms": {"spatial_intersection_ms": _elapsed_ms(started)}}
    try:
        parcel = shape(parcel_geometry) if isinstance(parcel_geometry, dict) else parcel_geometry
        hazard = shape(hazard_geometry) if isinstance(hazard_geometry, dict) else hazard_geometry
        parcel, _, _ = _normalize_polygonal(parcel)
        hazard, _, _ = _normalize_polygonal(hazard, plausibility_guard=False)
    except (ParcelGeometryError, TypeError, ValueError):
        return {"claim_type": "NO_GEOMETRY_AVAILABLE", "geometry_available": False,
                "timing_ms": {"spatial_intersection_ms": _elapsed_ms(started)}}
    destination = _projected_crs(parcel)
    parcel_projected, hazard_projected = _project(parcel, destination), _project(hazard, destination)
    overlap = parcel_projected.intersection(hazard_projected)
    return {
        "claim_type": "GEOMETRIC_INTERSECTION", "geometry_available": True,
        "intersects": parcel.intersects(hazard), "intersection_area_m2": round(overlap.area, 2),
        "intersection_ratio": round(overlap.area / parcel_projected.area, 6) if parcel_projected.area else 0,
        "nearest_distance_m": round(parcel_projected.distance(hazard_projected), 2),
        "timing_ms": {"spatial_intersection_ms": _elapsed_ms(started)},
    }
