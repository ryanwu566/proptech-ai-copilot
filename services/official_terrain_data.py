"""Offline official Terrain snapshot validation and deterministic matching.

The module accepts an operator-provided GeoJSON snapshot.  It never fetches a
provider, stores coordinates, or returns a provider payload.  Coordinates are
used only for the in-memory point-in-polygon decision.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


TerrainQueryStatus = Literal["matched", "not_matched_in_loaded_layer", "outside_coverage", "source_unavailable", "source_not_configured", "partial", "limited", "unknown", "error"]
TerrainCoverageStatus = Literal["covered", "outside_coverage", "unknown", "partial"]

TERRAIN_QUERY_STATUSES = frozenset({"matched", "not_matched_in_loaded_layer", "outside_coverage", "source_unavailable", "source_not_configured", "partial", "limited", "unknown", "error"})
TERRAIN_REQUIRED_RECORD_FIELDS = frozenset({"official_name", "layer_id"})


def normalize_terrain_evidence(
    *,
    layer_id: str,
    official_name: str,
    provider_id: str,
    query_status: str,
    coverage_status: str,
    match_status: str | None = None,
    matched_feature_count: int = 0,
    nearest_feature_distance_m: float | None = None,
    source_version: str | None = None,
    effective_date: str | None = None,
    fetched_at: str | None = None,
    limitation: str = "資料僅作地勢與災害風險參考，不代表沒有風險或安全保證。",
    attribution: str = "官方來源 attribution 需依資料集公告標示。",
) -> dict[str, object]:
    """Build the provider-neutral, safe Terrain reference contract."""

    if query_status not in TERRAIN_QUERY_STATUSES:
        raise ValueError("invalid terrain query_status")
    if coverage_status not in {"covered", "outside_coverage", "unknown", "partial"}:
        raise ValueError("invalid terrain coverage_status")
    if match_status is None:
        match_status = "matched" if query_status == "matched" else query_status
    if match_status not in TERRAIN_QUERY_STATUSES:
        raise ValueError("invalid terrain match_status")
    if matched_feature_count < 0:
        raise ValueError("matched_feature_count must not be negative")
    if nearest_feature_distance_m is not None and nearest_feature_distance_m < 0:
        raise ValueError("nearest_feature_distance_m must not be negative")
    return {
        "layer_id": layer_id,
        "official_name": official_name,
        "provider_id": provider_id,
        "query_status": query_status,
        "coverage_status": coverage_status,
        "match_status": match_status,
        "matched_feature_count": matched_feature_count,
        "nearest_feature_distance_m": nearest_feature_distance_m,
        "source_version": source_version,
        "effective_date": effective_date,
        "fetched_at": fetched_at,
        "limitation": limitation,
        "attribution": attribution,
    }


def validate_terrain_snapshot(payload: object, expected_provider_id: str | None = None) -> dict[str, object]:
    """Validate a small GeoJSON FeatureCollection without retaining raw data."""

    errors: list[str] = []
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        return {"valid": False, "errors": ["expected_feature_collection"], "feature_count": 0, "rejected_count": 0}
    provider_id = payload.get("provider_id")
    if not isinstance(provider_id, str) or not provider_id.strip():
        errors.append("provider_id_missing")
    if expected_provider_id and provider_id != expected_provider_id:
        errors.append("provider_id_mismatch")
    if not isinstance(payload.get("source_version"), str) or not payload["source_version"].strip():
        errors.append("source_version_missing")
    if not isinstance(payload.get("features"), list):
        errors.append("features_missing")
        return {"valid": False, "errors": errors, "feature_count": 0, "rejected_count": 0}
    accepted = 0
    rejected = 0
    seen: set[str] = set()
    for feature in payload["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            rejected += 1
            continue
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not TERRAIN_REQUIRED_RECORD_FIELDS.issubset(properties):
            rejected += 1
            continue
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Point", "Polygon", "MultiPolygon"}:
            rejected += 1
            continue
        identity = str(properties.get("feature_id") or f"{properties.get('layer_id')}:{properties.get('official_name')}")
        if identity in seen:
            rejected += 1
            continue
        seen.add(identity)
        accepted += 1
    if accepted == 0:
        errors.append("no_valid_features")
    return {"valid": not errors, "errors": errors, "feature_count": accepted, "rejected_count": rejected}


def match_terrain_snapshot(payload: object, latitude: float, longitude: float, layer_id: str) -> dict[str, object]:
    """Match one layer in a validated in-memory snapshot."""

    validation = validate_terrain_snapshot(payload)
    if not validation["valid"]:
        return normalize_terrain_evidence(
            layer_id=layer_id,
            official_name=layer_id,
            provider_id=str(payload.get("provider_id") if isinstance(payload, dict) else "unknown"),
            query_status="error",
            coverage_status="unknown",
            match_status="error",
            limitation="官方快照格式或欄位不完整，未進行風險判定。",
        )
    assert isinstance(payload, dict)
    features = [feature for feature in payload["features"] if feature["properties"].get("layer_id") == layer_id]
    if not features:
        return normalize_terrain_evidence(
            layer_id=layer_id,
            official_name=layer_id,
            provider_id=str(payload["provider_id"]),
            query_status="outside_coverage",
            coverage_status="outside_coverage",
            match_status="outside_coverage",
            source_version=str(payload["source_version"]),
            effective_date=_optional_text(payload.get("effective_date")),
            fetched_at=_optional_text(payload.get("fetched_at")),
            limitation="載入快照不涵蓋此圖層，不能推論為低風險。",
        )
    matched = [feature for feature in features if _geometry_contains(feature["geometry"], latitude, longitude)]
    first_properties = features[0]["properties"]
    status = "matched" if matched else "not_matched_in_loaded_layer"
    coverage_status = "partial" if validation["rejected_count"] else "covered"
    return normalize_terrain_evidence(
        layer_id=layer_id,
        official_name=str(first_properties["official_name"]),
        provider_id=str(payload["provider_id"]),
        query_status=status,
        coverage_status=coverage_status,
        match_status=status,
        matched_feature_count=len(matched),
        source_version=str(payload["source_version"]),
        effective_date=_optional_text(payload.get("effective_date")),
        fetched_at=_optional_text(payload.get("fetched_at")),
        limitation="命中結果是官方快照的參考證據，不代表安全、無風險或購買建議。" if matched else "目前未在已載入圖層中比對到特徵，不能推論為沒有風險。",
        attribution=_optional_text(payload.get("attribution")) or "官方來源 attribution 需依資料集公告標示。",
    )


def sanitize_terrain_evidence_for_case(evidence: dict[str, object]) -> dict[str, object]:
    """Return only the reduced reference fields allowed in a saved case."""

    allowed = {"layer_id", "official_name", "provider_id", "query_status", "coverage_status", "match_status", "matched_feature_count", "nearest_feature_distance_m", "source_version", "effective_date", "fetched_at", "limitation", "attribution"}
    for key in allowed:
        value = evidence.get(key)
        if isinstance(value, str) and any(token in value.lower() for token in ("address", "latitude", "longitude", "coordinate", "geometry", "payload", "token", "secret", "sql", "stack trace")):
            raise ValueError("unsafe Terrain reference text")
    return {key: evidence[key] for key in allowed if key in evidence}


class OfficialTerrainSnapshotAdapter:
    """Source-bound adapter for an already loaded official snapshot.

    It returns the normalized reference contract and never feeds the legacy
    Terrain score calculation automatically.
    """

    def __init__(self, snapshot: dict[str, object], provider_id: str):
        self.snapshot = snapshot
        self.provider_id = provider_id

    def query(self, latitude: float, longitude: float, layer_id: str) -> dict[str, object]:
        return match_terrain_snapshot(self.snapshot, latitude, longitude, layer_id)


def ingest_terrain_snapshot(path: str | Path, provider_id: str, *, dry_run: bool = True) -> dict[str, object]:
    """Validate a manually downloaded snapshot; never mutates production data."""

    source_path = Path(path)
    raw = source_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    validation = validate_terrain_snapshot(payload, provider_id)
    return {
        "status": "partial" if validation["valid"] and validation["rejected_count"] else "validated" if validation["valid"] else "rejected",
        "dry_run": dry_run,
        "provider_id": provider_id,
        "source_checksum_sha256": hashlib.sha256(raw).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "feature_count": validation["feature_count"],
        "rejected_count": validation["rejected_count"],
        "validation_errors": validation["errors"],
        "mutation": "none",
    }


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _geometry_contains(geometry: dict[str, object], latitude: float, longitude: float) -> bool:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Point" and isinstance(coordinates, list) and len(coordinates) >= 2:
        return float(coordinates[0]) == longitude and float(coordinates[1]) == latitude
    if kind == "Polygon" and isinstance(coordinates, list):
        return any(_point_in_ring(longitude, latitude, ring) for ring in coordinates if isinstance(ring, list))
    if kind == "MultiPolygon" and isinstance(coordinates, list):
        return any(_geometry_contains({"type": "Polygon", "coordinates": polygon}, latitude, longitude) for polygon in coordinates if isinstance(polygon, list))
    return False


def _point_in_ring(x: float, y: float, ring: list[object]) -> bool:
    points = [(float(point[0]), float(point[1])) for point in ring if isinstance(point, list) and len(point) >= 2]
    if len(points) < 3:
        return False
    inside = False
    previous_x, previous_y = points[-1]
    for current_x, current_y in points:
        if (current_y > y) != (previous_y > y) and x < (previous_x - current_x) * (y - current_y) / (previous_y - current_y) + current_x:
            inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside
