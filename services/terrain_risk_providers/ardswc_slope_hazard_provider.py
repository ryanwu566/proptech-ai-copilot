"""ARDSWC official MVT slope hazard provider.

This provider uses only the four public MVT endpoints listed by the Ministry of
Agriculture ARDSWC open-data platform. Tests inject fake HTTP and decoder
adapters; production can use the optional mapbox-vector-tile dependency.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import httpx

from .base import source_meta, unavailable_layer


AGENCY = "農業部農村發展及水土保持署"
DATA_PAGE_URL = "https://data.ardswc.gov.tw/Data/OpenData/Api"
DATA_VINTAGE = "113年度（官方公開 MVT）"
LIMITATION = "官方平台另有較新年度之圖台或下載資料，但本系統目前僅使用已公開、可程式查詢的 MVT 服務。"
MVT_ZOOM = 14
MAX_TILE_REQUESTS_PER_MVT_LAYER = 36
TILE_CACHE_TTL_SECONDS = 600
REQUEST_TIMEOUT_SECONDS = 4.0
EARTH_RADIUS_M = 6378137.0

MVT_LAYERS = {
    "debris_affect": {
        "hazard_key": "debris_flow",
        "label": "土石流潛勢溪流影響範圍",
        "geometry_kind": "polygon",
        "risk_level": "high",
        "url": "https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/debris_affect/{z}/{y}/{x}.pbf",
        "message": "位置或指定範圍與官方土石流潛勢溪流影響範圍有重疊，建議優先向地方主管機關與官方圖台確認。",
    },
    "debris_flow": {
        "hazard_key": "debris_flow",
        "label": "土石流潛勢溪流",
        "geometry_kind": "line",
        "risk_level": "medium",
        "url": "https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/debris_flow/{z}/{y}/{x}.pbf",
        "message": "指定範圍附近有官方列示的土石流潛勢溪流，需搭配影響範圍與現地條件確認。",
    },
    "potential_landslide": {
        "hazard_key": "landslide",
        "label": "大規模崩塌潛勢區",
        "geometry_kind": "polygon",
        "risk_level": "medium",
        "url": "https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/potential_landslide/{z}/{y}/{x}.pbf",
        "message": "位置或指定範圍與官方大規模崩塌潛勢區有重疊，建議優先確認。",
    },
    "potential_landslide_affect": {
        "hazard_key": "landslide",
        "label": "大規模崩塌潛勢區影響範圍",
        "geometry_kind": "polygon",
        "risk_level": "high",
        "url": "https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/potential_landslide_affect/{z}/{y}/{x}.pbf",
        "message": "位置或指定範圍與官方大規模崩塌潛勢區影響範圍有重疊，建議優先確認。",
    },
}

HAZARD_TO_MVT = {
    "debris_flow": ("debris_affect", "debris_flow"),
    "landslide": ("potential_landslide_affect", "potential_landslide"),
}

_TILE_CACHE: dict[tuple[str, int, int, int], tuple[float, bytes]] = {}


@dataclass(frozen=True)
class TileCoord:
    z: int
    x: int
    y: int


def _optional_decoder_available() -> bool:
    try:
        import mapbox_vector_tile  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


class ArdswcSlopeHazardProvider:
    source_url = DATA_PAGE_URL

    def __init__(
        self,
        http_get: Callable[[str, float], bytes] | None = None,
        decoder: Callable[[bytes, TileCoord], list[dict[str, Any]]] | None = None,
        zoom: int = MVT_ZOOM,
        max_tiles_per_layer: int = MAX_TILE_REQUESTS_PER_MVT_LAYER,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        use_cache: bool = True,
    ) -> None:
        self.http_get = http_get or self._http_get
        self.decoder = decoder or self._decode_mvt
        self.decoder_ready = decoder is not None or _optional_decoder_available()
        self.zoom = zoom
        self.max_tiles_per_layer = max_tiles_per_layer
        self.timeout_seconds = timeout_seconds
        self.use_cache = use_cache

    def analyze(self, latitude: float, longitude: float, radius_m: int, include_layers: Iterable[str] | None = None) -> dict[str, Any]:
        requested = set(include_layers or HAZARD_TO_MVT)
        result = {
            "landslide": self._skipped_or_empty("landslide", requested),
            "debris_flow": self._skipped_or_empty("debris_flow", requested),
        }
        if not self.decoder_ready:
            return {
                key: self._error_layer(key, "本環境尚未安裝可靠的 MVT decoder，無法完成官方 MVT 圖資比對。")
                if key in requested else result[key]
                for key in result
            }
        tiles = tiles_for_radius(latitude, longitude, radius_m, self.zoom)
        if len(tiles) > self.max_tiles_per_layer:
            return {
                key: self._error_layer(key, f"查詢半徑涵蓋 {len(tiles)} 個 tile，超過單一圖層上限 {self.max_tiles_per_layer}。請縮小半徑後重試。")
                if key in requested else result[key]
                for key in result
            }

        for hazard_key in ("debris_flow", "landslide"):
            if hazard_key not in requested:
                continue
            layer_results = [self._query_mvt_layer(mvt_key, tiles, latitude, longitude, radius_m) for mvt_key in HAZARD_TO_MVT[hazard_key]]
            result[hazard_key] = merge_layer_results(hazard_key, layer_results)
        return result

    def _query_mvt_layer(self, mvt_key: str, tiles: list[TileCoord], latitude: float, longitude: float, radius_m: int) -> dict[str, Any]:
        config = MVT_LAYERS[mvt_key]
        decoded_features: list[dict[str, Any]] = []
        errors: list[str] = []
        successful_tiles = 0
        for tile in tiles:
            try:
                payload = self._fetch_tile(mvt_key, tile)
                decoded_features.extend(self.decoder(payload, tile))
                successful_tiles += 1
            except Exception as exc:
                errors.append(f"{tile.z}/{tile.y}/{tile.x}: {type(exc).__name__}")

        if successful_tiles == 0:
            return self._mvt_result(mvt_key, "error", False, None, [], f"{config['label']}本次無法完成官方 MVT 比對，請稍後重試或前往官方圖台確認。", errors)

        features = dedupe_features(decoded_features)
        matches = [match for feature in features if (match := match_feature(feature, latitude, longitude, radius_m, config["geometry_kind"]))]
        if matches:
            nearest = min(item["distance_m"] for item in matches if item["distance_m"] is not None)
            status = "limited" if errors else "available"
            return self._mvt_result(mvt_key, status, True, round(nearest), [item["feature_id"] for item in matches], config["message"], errors)

        status = "limited" if errors else "available"
        explanation = "此官方圖層未比對到明確重疊，仍須搭配其他待補查來源判斷。"
        return self._mvt_result(mvt_key, status, False, None, [], explanation, errors)

    def _fetch_tile(self, mvt_key: str, tile: TileCoord) -> bytes:
        cache_key = (mvt_key, tile.z, tile.x, tile.y)
        now = time.monotonic()
        if self.use_cache and cache_key in _TILE_CACHE:
            cached_at, payload = _TILE_CACHE[cache_key]
            if now - cached_at <= TILE_CACHE_TTL_SECONDS:
                return payload
        url = MVT_LAYERS[mvt_key]["url"].format(z=tile.z, x=tile.x, y=tile.y)
        payload = self.http_get(url, self.timeout_seconds)
        if self.use_cache:
            _TILE_CACHE[cache_key] = (now, payload)
        return payload

    def _http_get(self, url: str, timeout_seconds: float) -> bytes:
        response = httpx.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        return response.content

    def _decode_mvt(self, payload: bytes, tile: TileCoord) -> list[dict[str, Any]]:
        try:
            from mapbox_vector_tile import decode  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("mapbox-vector-tile dependency is required to decode official MVT payloads") from exc
        decoded = decode(payload)
        features: list[dict[str, Any]] = []
        for layer in decoded.values():
            extent = int(layer.get("extent") or 4096)
            for feature in layer.get("features", []):
                geometry = feature.get("geometry")
                if geometry is None:
                    continue
                features.append({
                    "id": feature.get("id"),
                    "properties": feature.get("properties", {}),
                    "geometry": tile_geometry_to_lonlat(geometry, tile, extent),
                })
        return features

    def _mvt_result(self, mvt_key: str, status: str, matched: bool, distance_m: int | None, feature_ids: list[str], explanation: str, errors: list[str]) -> dict[str, Any]:
        config = MVT_LAYERS[mvt_key]
        return {
            "mvt_key": mvt_key,
            "key": config["hazard_key"],
            "label": config["label"],
            "status": status,
            "level": config["risk_level"] if matched else "unknown",
            "matched": matched,
            "distance_m": distance_m,
            "value": {"feature_count": len(feature_ids), "feature_ids": feature_ids[:10], "tile_errors": errors[:5]},
            "explanation": explanation,
            "source": self._source_meta(status, config["url"]),
        }

    def _skipped_or_empty(self, hazard_key: str, requested: set[str]) -> dict[str, Any]:
        if hazard_key not in requested:
            layer = unavailable_layer(hazard_key, hazard_label(hazard_key), self._source_meta("skipped", DATA_PAGE_URL), "此圖層未在 include_layers 中啟用，已略過查詢。")
            layer["status"] = "skipped"
            return layer
        layer = unavailable_layer(hazard_key, hazard_label(hazard_key), self._source_meta("unavailable", DATA_PAGE_URL), "尚未完成此圖層查詢。")
        return layer

    def _error_layer(self, hazard_key: str, explanation: str) -> dict[str, Any]:
        layer = unavailable_layer(hazard_key, hazard_label(hazard_key), self._source_meta("error", DATA_PAGE_URL), explanation)
        layer["status"] = "error"
        return layer

    def _source_meta(self, status: str, source_url: str) -> dict[str, str]:
        return source_meta(
            "ARDSWC 坡地災害官方 MVT",
            AGENCY,
            source_url,
            status,
            data_vintage=DATA_VINTAGE,
            data_quality="limited",
            limitation=LIMITATION,
        )


def hazard_label(hazard_key: str) -> str:
    return {"debris_flow": "土石流潛勢溪流／影響範圍", "landslide": "大規模崩塌潛勢區／影響範圍"}[hazard_key]


def merge_layer_results(hazard_key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if any(row["matched"] and row["level"] == "high" for row in rows):
        picked = next(row for row in rows if row["matched"] and row["level"] == "high")
    elif any(row["matched"] for row in rows):
        picked = next(row for row in rows if row["matched"])
    else:
        picked = rows[0]

    statuses = {row["status"] for row in rows}
    if statuses == {"error"}:
        status = "error"
    elif "limited" in statuses or "error" in statuses:
        status = "limited"
    else:
        status = "available"

    return {
        **picked,
        "key": hazard_key,
        "label": hazard_label(hazard_key),
        "status": status,
        "value": {
            "sublayers": [
                {
                    "mvt_key": row["mvt_key"],
                    "label": row["label"],
                    "status": row["status"],
                    "matched": row["matched"],
                    "level": row["level"],
                    "distance_m": row["distance_m"],
                    "source": row["source"],
                }
                for row in rows
            ]
        },
    }


def tiles_for_radius(latitude: float, longitude: float, radius_m: int, zoom: int = MVT_ZOOM) -> list[TileCoord]:
    lat_delta = math.degrees(radius_m / EARTH_RADIUS_M)
    lon_delta = math.degrees(radius_m / (EARTH_RADIUS_M * max(math.cos(math.radians(latitude)), 0.01)))
    min_x, max_y = lonlat_to_tile(longitude - lon_delta, latitude - lat_delta, zoom)
    max_x, min_y = lonlat_to_tile(longitude + lon_delta, latitude + lat_delta, zoom)
    x0, x1 = sorted((min_x, max_x))
    y0, y1 = sorted((min_y, max_y))
    return [TileCoord(zoom, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def tile_geometry_to_lonlat(geometry: Any, tile: TileCoord, extent: int) -> Any:
    if isinstance(geometry, (tuple, list)) and len(geometry) == 2 and all(isinstance(value, (int, float)) for value in geometry):
        px, py = geometry
        n = 2**tile.z
        lon = (tile.x + px / extent) / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (tile.y + py / extent) / n)))
        return [lon, math.degrees(lat_rad)]
    if isinstance(geometry, list):
        return [tile_geometry_to_lonlat(item, tile, extent) for item in geometry]
    return geometry


def dedupe_features(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for feature in features:
        feature_id = stable_feature_id(feature)
        if feature_id in seen:
            continue
        seen.add(feature_id)
        rows.append({**feature, "_stable_id": feature_id})
    return rows


def stable_feature_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    for key in ("id", "ID", "OBJECTID", "流水號", "編號", "NO", "no"):
        value = feature.get(key) or props.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    return hashlib.sha1(repr([props, feature.get("geometry")]).encode("utf-8")).hexdigest()


def match_feature(feature: dict[str, Any], latitude: float, longitude: float, radius_m: int, geometry_kind: str) -> dict[str, Any] | None:
    geometry = feature.get("geometry")
    distance = geometry_distance_m(geometry, longitude, latitude)
    if distance is None:
        return None
    if distance <= radius_m:
        return {"feature_id": feature["_stable_id"], "distance_m": distance}
    return None


def geometry_distance_m(geometry: Any, lon: float, lat: float) -> float | None:
    paths = extract_paths(geometry)
    distances: list[float] = []
    for path in paths:
        if len(path) == 1:
            distances.append(distance_m(lon, lat, path[0][0], path[0][1]))
        elif len(path) >= 2:
            if point_in_ring(lon, lat, path):
                return 0.0
            distances.extend(point_segment_distance_m(lon, lat, a, b) for a, b in zip(path, path[1:]))
    return min(distances) if distances else None


def extract_paths(geometry: Any) -> list[list[tuple[float, float]]]:
    if not isinstance(geometry, list) or not geometry:
        return []
    if is_point(geometry):
        return [[(float(geometry[0]), float(geometry[1]))]]
    if all(is_point(item) for item in geometry):
        return [[(float(item[0]), float(item[1])) for item in geometry]]
    paths: list[list[tuple[float, float]]] = []
    for item in geometry:
        paths.extend(extract_paths(item))
    return paths


def is_point(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value)


def point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_segment_distance_m(lon: float, lat: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = project_m(a[0], a[1], lat)
    bx, by = project_m(b[0], b[1], lat)
    px, py = project_m(lon, lat, lat)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    return math.hypot(*tuple(a - b for a, b in zip(project_m(lon1, lat1, (lat1 + lat2) / 2), project_m(lon2, lat2, (lat1 + lat2) / 2))))


def project_m(lon: float, lat: float, ref_lat: float) -> tuple[float, float]:
    x = math.radians(lon) * EARTH_RADIUS_M * math.cos(math.radians(ref_lat))
    y = math.radians(lat) * EARTH_RADIUS_M
    return x, y
