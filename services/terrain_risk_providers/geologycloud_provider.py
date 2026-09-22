"""Bounded GSMMA GeologyCloud soil-liquefaction provider."""

from __future__ import annotations

import json
import math
from typing import Any, Callable, Iterable
from urllib.parse import urlencode

import httpx

from .base import source_meta, unavailable_layer


API_URL = "https://www.geologycloud.tw/api/v1/zh-tw/liquefaction"
SERVICE_PAGE_URL = "https://www.geologycloud.tw/dashboard/datalist"
GEOLOGYCLOUD_URL = "https://www.geologycloud.tw/"
SOURCE_NAME = "土壤液化潛勢範圍"
GEOLOGY_SOURCE_NAME = "地質雲與地質敏感圖資"
AGENCY = "經濟部地質調查及礦業管理中心"
REQUEST_TIMEOUT_SECONDS = 4.0
MAX_RESPONSE_BYTES = 1_000_000
MAX_FEATURES_PER_CLASSIFICATION = 1_000
RESPONSE_CHUNK_BYTES = 64 * 1024
EARTH_RADIUS_M = 6_378_137.0

OFFICIAL_CLASSIFICATIONS = ("低潛勢", "中潛勢", "高潛勢")
CLASSIFICATION_LEVELS = {"低潛勢": "low", "中潛勢": "medium", "高潛勢": "high"}
CLASSIFICATION_RANK = {"低潛勢": 1, "中潛勢": 2, "高潛勢": 3}

# This list is intentionally narrower than the OpenAPI area enum. Every entry
# below has a corresponding named dataset in the official service catalog.
OFFICIAL_CITY_TO_AREA = {
    "臺北市": "臺北",
    "新北市": "臺北",
    "新竹市": "新竹",
    "新竹縣": "新竹",
    "臺中市": "臺中",
    "彰化縣": "彰化",
    "雲林縣": "雲林",
    "嘉義縣": "嘉義",
    "臺南市": "臺南",
    "高雄市": "高雄",
    "屏東縣": "屏東",
    "宜蘭縣": "宜蘭",
    "花蓮縣": "花蓮",
}

COVERAGE_LIMITATION = (
    "僅涵蓋地質雲官方服務目錄明列的區域性土壤液化潛勢資料；"
    "未宣稱全臺覆蓋，恆春地區等無法由縣市提示唯一選定的範圍不自動推測。"
)
DATA_LIMITATION = "本圖資屬區域性初級土壤液化潛勢評估，工程個案仍需進一步現地調查與專業分析。"
PLACEHOLDER_EXPLANATION = "目前未設定可合法直接比對座標的官方圖資查詢 API；請至地質雲官方圖台確認。"


class GeologyCloudResponseError(ValueError):
    """Raised when an official response is incomplete or unsafe to consume."""


class GeologyCloudProvider:
    source_url = API_URL

    def __init__(
        self,
        http_get: Callable[[str, float], bytes] | None = None,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
        max_features: int = MAX_FEATURES_PER_CLASSIFICATION,
    ) -> None:
        self.http_get = http_get
        self.timeout_seconds = min(float(timeout_seconds), 5.0)
        self.max_response_bytes = max_response_bytes
        self.max_features = max_features

    def analyze(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        area_hint: str | None = None,
        include_layers: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        requested = set(
            ("geological_sensitivity", "liquefaction", "active_fault")
            if include_layers is None
            else include_layers
        )
        unavailable_source = self._source("unavailable")
        generic_geology_source = self._generic_source("unavailable")
        result = {
            "geological_sensitivity": unavailable_layer(
                "geological_sensitivity", "地質敏感區", generic_geology_source, PLACEHOLDER_EXPLANATION
            ),
            "liquefaction": unavailable_layer(
                "liquefaction", "土壤液化潛勢", unavailable_source, PLACEHOLDER_EXPLANATION
            ),
            "active_fault": unavailable_layer(
                "active_fault", "活動斷層", generic_geology_source, PLACEHOLDER_EXPLANATION
            ),
        }
        if "liquefaction" not in requested:
            return result

        area = official_area_for_city(area_hint)
        if area is None:
            result["liquefaction"] = self._unroutable_liquefaction(area_hint)
            return result

        try:
            bbox = bbox_for_radius(latitude, longitude, radius_m)
        except (TypeError, ValueError):
            result["liquefaction"] = self._unroutable_liquefaction(
                area_hint, "座標或查詢半徑無效，未向官方服務發送查詢。"
            )
            return result

        result["liquefaction"] = self._query_liquefaction(latitude, longitude, area, bbox)
        return result

    def _query_liquefaction(
        self,
        latitude: float,
        longitude: float,
        area: str,
        bbox: str,
    ) -> dict[str, Any]:
        outcomes: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}
        for classification in OFFICIAL_CLASSIFICATIONS:
            url = build_query_url(area, classification, bbox)
            try:
                payload = self._fetch(url)
                features = parse_feature_collection(payload, self.max_response_bytes, self.max_features)
                outcomes[classification] = {
                    "feature_count": len(features),
                    "matched": any(
                        geometry_contains_point(feature["geometry"], longitude, latitude)
                        for feature in features
                    ),
                }
            except Exception as exc:
                errors[classification] = type(exc).__name__

        matched_classifications = [
            classification for classification, outcome in outcomes.items() if outcome["matched"]
        ]
        matched_classification = max(
            matched_classifications, key=CLASSIFICATION_RANK.__getitem__, default=None
        )
        status = "error" if not outcomes else "limited" if errors else "available"

        level = "unknown"
        if matched_classification and not errors:
            level = CLASSIFICATION_LEVELS[matched_classification]
        elif matched_classification == "高潛勢":
            level = "high"
        elif matched_classification == "中潛勢" and "高潛勢" not in errors:
            level = "medium"

        if errors and matched_classification:
            explanation = (
                f"官方 {area} 資料已比對到「{matched_classification}」多邊形，但部分分類查詢失敗，"
                "本次結果不完整，請再至官方圖台確認。"
            )
        elif errors:
            explanation = "三項官方液化潛勢分類未能全部完成查詢；本次無比對結果不得解讀為低風險或沒有液化風險。"
        elif matched_classification:
            explanation = (
                f"此座標落在官方 {area}「{matched_classification}」土壤液化潛勢多邊形內；"
                "圖資屬區域性初級評估，個案仍需專業調查。"
            )
        else:
            explanation = (
                f"已完成官方 {area} 低、中、高三項潛勢資料查詢，未比對到包含此座標的多邊形；"
                "這不代表沒有土壤液化風險。"
            )

        source_classification = (
            matched_classification
            if matched_classification
            else "查詢不完整"
            if errors
            else "未比對"
        )
        source = self._source(
            status,
            queried_area=area,
            official_classification=source_classification,
        )
        return {
            "key": "liquefaction",
            "label": "土壤液化潛勢",
            "status": status,
            "level": level,
            "matched": matched_classification is not None,
            "distance_m": 0 if matched_classification is not None else None,
            "value": {
                "queried_area": area,
                "queried_classifications": list(OFFICIAL_CLASSIFICATIONS),
                "official_classification": matched_classification,
                "feature_counts": {
                    classification: outcome["feature_count"]
                    for classification, outcome in outcomes.items()
                },
                "query_errors": errors,
            },
            "explanation": explanation,
            "source": source,
        }

    def _fetch(self, url: str) -> bytes:
        if self.http_get is not None:
            payload = self.http_get(url, self.timeout_seconds)
            if not isinstance(payload, bytes):
                raise GeologyCloudResponseError("HTTP adapter returned a non-bytes payload")
            if len(payload) > self.max_response_bytes:
                raise GeologyCloudResponseError("official response exceeded the byte limit")
            return payload

        timeout = httpx.Timeout(
            self.timeout_seconds,
            connect=min(2.0, self.timeout_seconds),
            pool=min(1.0, self.timeout_seconds),
        )
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            with client.stream(
                "GET", url, headers={"Accept": "application/geo+json, application/json"}
            ) as response:
                response.raise_for_status()
                declared_length = response.headers.get("Content-Length")
                if declared_length:
                    try:
                        if int(declared_length) > self.max_response_bytes:
                            raise GeologyCloudResponseError("official response exceeded the byte limit")
                    except ValueError as exc:
                        raise GeologyCloudResponseError("invalid Content-Length") from exc
                payload = bytearray()
                for chunk in response.iter_bytes(chunk_size=RESPONSE_CHUNK_BYTES):
                    if len(chunk) > self.max_response_bytes - len(payload):
                        raise GeologyCloudResponseError("official response exceeded the byte limit")
                    payload.extend(chunk)
                return bytes(payload)

    def _unroutable_liquefaction(
        self, area_hint: str | None, explanation: str | None = None
    ) -> dict[str, Any]:
        if explanation is None:
            if not area_hint:
                explanation = (
                    "只有座標且沒有經接受地址定位取得的縣市提示；"
                    "系統不從座標猜測行政區，未發送官方查詢。"
                )
            else:
                explanation = (
                    "官方服務目錄未提供可由此縣市提示唯一選定的土壤液化資料區域；"
                    "系統未猜測區域，也未發送官方查詢。"
                )
        return unavailable_layer(
            "liquefaction", "土壤液化潛勢", self._source("unavailable"), explanation
        )

    @staticmethod
    def _source(status: str, **extra: str) -> dict[str, str]:
        return source_meta(
            SOURCE_NAME,
            AGENCY,
            API_URL,
            status,
            official_classifications="、".join(OFFICIAL_CLASSIFICATIONS),
            coverage_limitation=COVERAGE_LIMITATION,
            limitation=DATA_LIMITATION,
            service_catalog_url=SERVICE_PAGE_URL,
            **extra,
        )

    @staticmethod
    def _generic_source(status: str) -> dict[str, str]:
        return source_meta(
            GEOLOGY_SOURCE_NAME,
            AGENCY,
            GEOLOGYCLOUD_URL,
            status,
        )


def official_area_for_city(area_hint: str | None) -> str | None:
    if not isinstance(area_hint, str):
        return None
    normalized = area_hint.strip().replace("台", "臺")
    return OFFICIAL_CITY_TO_AREA.get(normalized)


def bbox_for_radius(latitude: float, longitude: float, radius_m: int) -> str:
    latitude = float(latitude)
    longitude = float(longitude)
    radius_m = int(radius_m)
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        raise ValueError("coordinates must be finite")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and radius_m > 0):
        raise ValueError("coordinates or radius are outside valid bounds")
    cosine = math.cos(math.radians(latitude))
    if abs(cosine) < 1e-9:
        raise ValueError("longitude radius is undefined at the pole")
    latitude_delta = math.degrees(radius_m / EARTH_RADIUS_M)
    longitude_delta = math.degrees(radius_m / (EARTH_RADIUS_M * cosine))
    values = (
        longitude - longitude_delta,
        latitude - latitude_delta,
        longitude + longitude_delta,
        latitude + latitude_delta,
    )
    return ",".join(f"{value:.7f}" for value in values)


def build_query_url(area: str, classification: str, bbox: str) -> str:
    query = urlencode({"area": area, "classify": classification, "bbox": bbox}, safe=",")
    return f"{API_URL}?{query}"


def parse_feature_collection(
    payload: bytes, max_bytes: int, max_features: int
) -> list[dict[str, Any]]:
    if len(payload) > max_bytes:
        raise GeologyCloudResponseError("official response exceeded the byte limit")
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeologyCloudResponseError("official response was not valid JSON") from exc
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise GeologyCloudResponseError("official response was not a GeoJSON FeatureCollection")
    features = document.get("features")
    if not isinstance(features, list):
        raise GeologyCloudResponseError("official response did not contain a feature list")
    if len(features) > max_features:
        raise GeologyCloudResponseError("official response exceeded the feature limit")
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise GeologyCloudResponseError("official response contained a malformed feature")
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise GeologyCloudResponseError("official response contained unsupported geometry")
        validate_geometry(geometry)
    return features


def validate_geometry(geometry: dict[str, Any]) -> None:
    coordinates = geometry.get("coordinates")
    if geometry["type"] == "Polygon":
        validate_polygon(coordinates)
        return
    if not isinstance(coordinates, list) or not coordinates:
        raise GeologyCloudResponseError("official MultiPolygon coordinates were malformed")
    for polygon in coordinates:
        validate_polygon(polygon)


def validate_polygon(coordinates: Any) -> None:
    if not isinstance(coordinates, list) or not coordinates:
        raise GeologyCloudResponseError("official Polygon coordinates were malformed")
    for ring in coordinates:
        if not isinstance(ring, list) or len(ring) < 4:
            raise GeologyCloudResponseError("official polygon ring was malformed")
        points: list[tuple[float, float]] = []
        for coordinate in ring:
            if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 2:
                raise GeologyCloudResponseError("official polygon coordinate was malformed")
            longitude, latitude = coordinate[0], coordinate[1]
            if not isinstance(longitude, (int, float)) or not isinstance(latitude, (int, float)):
                raise GeologyCloudResponseError("official polygon coordinate was not numeric")
            if not (math.isfinite(longitude) and math.isfinite(latitude)):
                raise GeologyCloudResponseError("official polygon coordinate was not finite")
            points.append((float(longitude), float(latitude)))
        if points[0] != points[-1]:
            raise GeologyCloudResponseError("official polygon ring was not closed")


def geometry_contains_point(
    geometry: dict[str, Any], longitude: float, latitude: float
) -> bool:
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        return polygon_contains_point(coordinates, longitude, latitude)
    return any(
        polygon_contains_point(polygon, longitude, latitude) for polygon in coordinates
    )


def polygon_contains_point(polygon: list[Any], longitude: float, latitude: float) -> bool:
    if not point_in_ring(polygon[0], longitude, latitude):
        return False
    return not any(point_in_ring(hole, longitude, latitude) for hole in polygon[1:])


def point_in_ring(ring: list[Any], longitude: float, latitude: float) -> bool:
    inside = False
    for index in range(len(ring) - 1):
        x1, y1 = float(ring[index][0]), float(ring[index][1])
        x2, y2 = float(ring[index + 1][0]), float(ring[index + 1][1])
        if point_on_segment(longitude, latitude, x1, y1, x2, y2):
            return True
        if (y1 > latitude) != (y2 > latitude):
            crossing_x = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < crossing_x:
                inside = not inside
    return inside


def point_on_segment(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> bool:
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > 1e-12:
        return False
    return (
        min(x1, x2) - 1e-12 <= px <= max(x1, x2) + 1e-12
        and min(y1, y2) - 1e-12 <= py <= max(y1, y2) + 1e-12
    )
