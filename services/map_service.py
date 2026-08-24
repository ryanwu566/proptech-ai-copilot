"""Mock-first Map Insight Lite service with stable frontend contracts."""

from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from services.adapters.geocoding_adapter import GeocodingAdapter, GoogleGeocodingAdapter, MockGeocodingAdapter
from services.adapters.google_places_adapter import GooglePlacesAdapter, distance_meters, is_valid_place_type
from services.adapters.tgos_geocoding_adapter import TgosGeocodingAdapter
from services.adapters.poi_adapter import MockPoiAdapter, PoiAdapter
from services.adapters.traffic_adapter import MockTrafficAdapter, TrafficAdapter
from services.geocoding_acceptance import evaluate_geocoding_acceptance, unavailable_geocoding_acceptance


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_map_points.json"
SEARCH_DISCLAIMER = "展示型 mock data，不代表正式地址定位結果"
INSIGHT_DISCLAIMER = "展示型 mock data，不代表正式估價、投資或交通分析"
NEARBY_DISCLAIMER = "生活機能資料僅供展示與區域理解，不代表正式估價、投資或交通分析。"
CATEGORY_LABELS = {
    "transport": "交通",
    "school": "學校",
    "park": "公園",
    "medical": "醫療",
    "shopping": "商圈",
    "food": "餐飲",
}
CATEGORY_WEIGHTS = {"transport": 25, "food": 20, "shopping": 20, "school": 15, "medical": 10, "park": 10}
DEFAULT_GOOGLE_PLACES_ADAPTER = GooglePlacesAdapter()
DEFAULT_TGOS_GEOCODING_ADAPTER = TgosGeocodingAdapter()
GOOGLE_HEALTH_CACHE: tuple[float, dict[str, Any]] | None = None
GOOGLE_HEALTH_TTL_SECONDS = 300
MAX_CATEGORY_WORKERS = 6
LOGGER = logging.getLogger(__name__)

atexit.register(DEFAULT_GOOGLE_PLACES_ADAPTER.close)
atexit.register(DEFAULT_TGOS_GEOCODING_ADAPTER.close)


def load_map_data() -> dict[str, Any]:
    """Load and minimally validate bundled map mock data."""

    try:
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Map Insight 展示資料無法載入。") from exc
    if not payload.get("regions") or not payload.get("categories"):
        raise ValueError("Map Insight 展示資料缺少區域或 POI 分類。")
    return payload


def list_regions() -> list[dict[str, Any]]:
    """Return searchable mock region metadata."""

    return [
        {"id": row["id"], "city": row["city"], "district": row["district"], "road": row["road"], "center": row["center"]}
        for row in load_map_data()["regions"]
    ]


def list_poi_categories() -> list[dict[str, str]]:
    """Return the stable POI category list."""

    return [{"category": key, "label": value} for key, value in CATEGORY_LABELS.items()]


def search_location(query: str, adapter: GeocodingAdapter | None = None) -> dict[str, Any]:
    """Use Google, TGOS, then bundled mock geocoding. Multi-provider recovery when Google is rejected."""

    started = time.perf_counter()
    regions = load_map_data()["regions"]
    source_chain = ["google_geocoding", "tgos_geocoding", "mock"]
    source = "mock"
    google = adapter if adapter is not None else GoogleGeocodingAdapter()
    region = google.search(query, regions)
    if region is not None and isinstance(google, GoogleGeocodingAdapter):
        source = "google_geocoding"
    if region is None and adapter is None:
        region = DEFAULT_TGOS_GEOCODING_ADAPTER.search(query, regions)
        if region is not None:
            source = "tgos_geocoding"

    # Multi-provider recovery: if Google returned a result but acceptance rejects it, try TGOS
    if region is not None and source == "google_geocoding" and adapter is None:
        google_acceptance = evaluate_geocoding_acceptance(query, region, source)
        if not google_acceptance["accepted_for_analysis"]:
            tgos_region = DEFAULT_TGOS_GEOCODING_ADAPTER.search(query, regions)
            if tgos_region is not None:
                tgos_acceptance = evaluate_geocoding_acceptance(query, tgos_region, "tgos_geocoding")
                if tgos_acceptance["accepted_for_analysis"]:
                    # TGOS recovered — use TGOS result
                    LOGGER.info("multi_provider_recovery query=%s google_quality=%s tgos_quality=%s action=tgos_accepted", query[:30], google_acceptance["match_quality"], tgos_acceptance["match_quality"])
                    region = tgos_region
                    source = "tgos_geocoding"
                else:
                    LOGGER.info("multi_provider_recovery query=%s google_quality=%s tgos_quality=%s action=both_refused", query[:30], google_acceptance["match_quality"], tgos_acceptance["match_quality"])
            else:
                LOGGER.info("multi_provider_recovery query=%s google_quality=%s tgos=unavailable", query[:30], google_acceptance["match_quality"])

    if region is None and adapter is None:
        region = MockGeocodingAdapter().search(query, regions)
    if region is None:
        geocoding_ms = round((time.perf_counter() - started) * 1000)
        LOGGER.info("map_geocoding timing_ms=%s matched=false source=unavailable", geocoding_ms)
        acceptance = unavailable_geocoding_acceptance(query)
        return {
            "query": query, "matched": False, "center": None, "city": "", "district": "", "road": "",
            "source": "mock", "source_chain": source_chain, "formatted_address": "", "place_id": "", "confidence": "mock",
            "location_note": "找不到符合的展示資料定位。", "disclaimer": SEARCH_DISCLAIMER,
            "geocoding_ms": geocoding_ms,
            **acceptance,
            "geocoding_acceptance": acceptance,
        }
    formatted_address = region.get("formatted_address") or f"{region.get('city', '')}{region.get('district', '')}{region.get('road', '')}"
    geocoding_ms = round((time.perf_counter() - started) * 1000)
    LOGGER.info("map_geocoding timing_ms=%s matched=true source=%s", geocoding_ms, source)
    acceptance = evaluate_geocoding_acceptance(query, region, source)
    # Mock geocoding must NEVER be accepted as real location evidence
    if source == "mock" and acceptance.get("accepted_for_analysis"):
        acceptance = {
            **acceptance,
            "accepted_for_analysis": False,
            "requires_confirmation": True,
            "match_quality": "PARTIAL_MATCH",
            "mismatch_reasons": [*acceptance.get("mismatch_reasons", []), "mock_source_not_real_evidence"],
            "message": "展示資料定位不是真實位置證據，不可用於正式分析。",
        }
    return {
        "query": query,
        "matched": True,
        "center": region["center"],
        "city": region["city"],
        "district": region["district"],
        "road": region["road"],
        "source": source,
        "source_chain": source_chain,
        "formatted_address": formatted_address,
        "place_id": region.get("place_id", ""),
        "confidence": (
            "high"
            if source == "google_geocoding" and acceptance["accepted_for_analysis"]
            else "medium"
            if source == "tgos_geocoding" and acceptance["accepted_for_analysis"]
            else "mock"
            if source == "mock"
            else "low"
            if not acceptance["accepted_for_analysis"]
            else "mock"
        ),
        "location_note": acceptance["message"] if not acceptance["accepted_for_analysis"] else (
            "Google Geocoding 定位結果。"
            if source == "google_geocoding"
            else "TGOS 定位結果；周遭設施來源另行標示。"
            if source == "tgos_geocoding"
            else "展示資料定位，座標僅供操作示範。"
        ),
        "geocoding_ms": geocoding_ms,
        "disclaimer": SEARCH_DISCLAIMER,
        **acceptance,
        "geocoding_acceptance": acceptance,
    }


def get_google_health(force_refresh: bool = False) -> dict[str, Any]:
    """Check backend-only Google integrations with a five-minute process cache."""

    global GOOGLE_HEALTH_CACHE
    now = time.monotonic()
    if not force_refresh and GOOGLE_HEALTH_CACHE and now - GOOGLE_HEALTH_CACHE[0] < GOOGLE_HEALTH_TTL_SECONDS:
        return GOOGLE_HEALTH_CACHE[1]

    geocoding = GoogleGeocodingAdapter()
    places = GooglePlacesAdapter()
    if not geocoding.available:
        result = {
            "google_key_configured": False, "geocoding_enabled": False, "places_enabled": False,
            "last_error": "", "mode": "mock", "safe_message": "目前使用展示資料",
        }
        GOOGLE_HEALTH_CACHE = (now, result)
        return result

    geocoding_enabled = geocoding.search("台北101", []) is not None
    places_enabled = False
    places_error = ""
    try:
        places.nearby(25.0330, 121.5654, 200, "transport", "zh-TW")
        places_enabled = True
    except httpx.TimeoutException:
        places_error = "Google Places 回應逾時"
    except httpx.HTTPStatusError:
        places_error = "Google Places 目前無法使用"
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        places_error = "Google Places 未回傳可用資料"
    enabled = geocoding_enabled and places_enabled
    errors = [message for message in [geocoding.last_error, places_error] if message]
    result = {
        "google_key_configured": True,
        "geocoding_enabled": geocoding_enabled,
        "places_enabled": places_enabled,
        "last_error": "；".join(errors),
        "mode": "google" if enabled else "mock",
        "safe_message": "目前使用 Google Places API" if enabled else "Google API 暫不可用，已切換展示資料",
    }
    GOOGLE_HEALTH_CACHE = (now, result)
    return result


def get_map_insight(query: str, geocoding: GeocodingAdapter | None = None, poi: PoiAdapter | None = None, traffic: TrafficAdapter | None = None) -> dict[str, Any] | None:
    """Build one Map Insight result using mock-first adapters."""

    region = (geocoding or MockGeocodingAdapter()).search(query, load_map_data()["regions"])
    if region is None:
        return None
    layers = (poi or MockPoiAdapter()).get_layers(region)
    (traffic or MockTrafficAdapter()).get_summary(region)
    return {
        "center": region["center"],
        "zoom": int(region["zoom"]),
        "area_summary": region["area_summary"],
        "poi_layers": layers,
        "livability_score": int(region["livability_score"]),
        "poi_summary": region["poi_summary"],
        "source": "mock",
        "disclaimer": INSIGHT_DISCLAIMER,
    }


def get_nearby_places(
    lat: float,
    lng: float,
    radius_m: int,
    categories: list[str],
    language_code: str = "zh-TW",
    adapter: GooglePlacesAdapter | None = None,
) -> dict[str, Any]:
    """Return Google Places nearby results or a normalized mock fallback."""

    total_started = time.perf_counter()
    supported = [category for category in categories if category in CATEGORY_LABELS]
    requested = supported or list(CATEGORY_LABELS)
    google = adapter or DEFAULT_GOOGLE_PLACES_ADAPTER
    grouped: list[dict[str, Any]] = []
    source = "google_places" if google.available else "mock"
    failed_categories: list[str] = []
    provider_timing_ms: dict[str, int] = {}
    category_status: dict[str, dict[str, str | int]] = {}

    if google.available:
        with ThreadPoolExecutor(max_workers=min(MAX_CATEGORY_WORKERS, len(requested)), thread_name_prefix="map-category") as executor:
            futures = [(category, executor.submit(_timed_nearby_call, google, lat, lng, radius_m, category, language_code)) for category in requested]
            # Read futures in request order so response order stays deterministic.
            for category, future in futures:
                try:
                    places, elapsed_ms = future.result()
                    provider_timing_ms[category] = elapsed_ms
                    grouped.append(_category_result(category, places, source="google_places", availability="available"))
                    category_status[category] = {"status": "available", "source": "google_places", "timing_ms": elapsed_ms}
                except Exception as exc:
                    failed_categories.append(category)
                    elapsed_ms = int(getattr(exc, "provider_timing_ms", 0))
                    provider_timing_ms[category] = elapsed_ms
                    category_status[category] = {"status": "error", "source": "unavailable", "timing_ms": elapsed_ms}

        if not grouped:
            source = "mock"

    if source == "mock":
        grouped = [_category_result(category, _mock_places(lat, lng, radius_m, category), source="mock", availability="fallback") for category in requested]
        category_status = {
            category: {"status": "fallback", "source": "mock", "timing_ms": provider_timing_ms.get(category, 0)}
            for category in requested
        }

    quality_stats = {"input_place_count": sum(row["count"] for row in grouped), "accepted_place_count": sum(row["count"] for row in grouped), "rejected_type_count": 0, "deduplicated_count": 0}
    if source == "google_places":
        grouped, quality_stats = _filter_and_dedupe_google_places(grouped)
        for group in grouped:
            status = category_status.get(group["category"])
            if status is not None:
                status.update({
                    "input_count": group.get("input_count", group["count"]),
                    "accepted_count": group["count"],
                    "rejected_type_count": group.get("rejected_type_count", 0),
                    "deduplicated_count": group.get("deduplicated_count", 0),
                })
    partial = source == "google_places" and bool(failed_categories)
    evidence_quality_status = (
        "fallback"
        if source == "mock"
        else "partial"
        if partial or quality_stats["rejected_type_count"] or quality_stats["deduplicated_count"]
        else "high"
    )
    scoring = build_livability_scoring(grouped, radius_m, evidence_quality_status)
    counts = "、".join(f"{row['label']} {row['count']} 處" for row in grouped)
    evidence_quality = {
        "status": evidence_quality_status,
        **quality_stats,
        "score_factor": scoring["evidence_quality_factor"],
        "score_ceiling": scoring["score_ceiling"],
    }
    nearby_total_ms = round((time.perf_counter() - total_started) * 1000)
    response = {
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius_m,
        "source": source,
        "partial": partial,
        "fallback": source == "mock",
        "failed_categories": failed_categories,
        "category_status": category_status,
        "evidence_quality": evidence_quality,
        "provider_timing_ms": provider_timing_ms,
        "nearby_total_ms": nearby_total_ms,
        "categories": grouped,
        "livability_score": scoring["livability_score"],
        "livability_level": scoring["livability_level"],
        "score_summary": scoring["score_summary"],
        "category_scores": scoring["category_scores"],
        "category_score_map": scoring["category_score_map"],
        "nearest_places": scoring["nearest_places"],
        "recommendation_text": scoring["recommendation_text"],
        "score_explanation": scoring["score_explanation"],
        "scoring_criteria": {
            "radius_m": 800,
            "category_weights": CATEGORY_WEIGHTS,
            "distance_bands": [
                {"range": "0-300m", "weight": "high"},
                {"range": "300-800m", "weight": "medium"},
                {"range": "800m+", "weight": "excluded"},
            ],
            "quality_adjustment": {
                "status": evidence_quality_status,
                "factor": scoring["evidence_quality_factor"],
                "score_ceiling": scoring["score_ceiling"],
            },
            "disclaimer": NEARBY_DISCLAIMER,
        },
        "summary": scoring["summary"] or f"{radius_m} 公尺生活圈共涵蓋 {counts}；分數僅用於比較周遭設施完整度。",
        "disclaimer": NEARBY_DISCLAIMER,
    }
    LOGGER.info(
        "map_nearby timing_ms=%s categories=%s failed_categories=%s source=%s partial=%s",
        nearby_total_ms,
        requested,
        failed_categories,
        source,
        partial,
    )
    return response


def _timed_nearby_call(
    adapter: GooglePlacesAdapter,
    lat: float,
    lng: float,
    radius_m: int,
    category: str,
    language_code: str,
) -> tuple[list[dict[str, Any]], int]:
    started = time.perf_counter()
    try:
        places = adapter.nearby(lat, lng, radius_m, category, language_code)
    except Exception as exc:
        setattr(exc, "provider_timing_ms", round((time.perf_counter() - started) * 1000))
        raise
    return places, round((time.perf_counter() - started) * 1000)


def calculate_livability_score(categories: list[dict[str, Any]], radius_m: int) -> int:
    """Return the overall score while preserving the original public helper."""

    return int(build_livability_scoring(categories, radius_m)["livability_score"])


def build_livability_scoring(categories: list[dict[str, Any]], radius_m: int, evidence_quality_status: str = "unassessed") -> dict[str, Any]:
    """Score category coverage using both POI count and tiered walking distance."""

    quality_factor = {"high": 0.95, "partial": 0.78, "fallback": 0.65}.get(evidence_quality_status, 1.0)
    score_ceiling = {"high": 95, "partial": 78, "fallback": 65}.get(evidence_quality_status, 100)
    total = 0.0
    category_score_map: dict[str, int] = {}
    category_metrics: list[dict[str, Any]] = []
    all_places: list[dict[str, Any]] = []
    for group in categories:
        category = group["category"]
        places = [place for place in group["places"] if place.get("distance_m", radius_m + 1) <= min(radius_m, 800)]
        all_places.extend({**place, "category": place.get("category", category)} for place in places)
        proximity_units = sum(_distance_weight(float(place["distance_m"])) for place in places)
        raw_category_score = max(0, min(100, round(min(proximity_units / 4, 1) * 100)))
        category_score = round(raw_category_score * quality_factor)
        category_score_map[category] = category_score
        nearest_distance = min((int(place["distance_m"]) for place in places), default=None)
        level = _score_level(category_score)
        category_metrics.append({
            "category": category,
            "label": CATEGORY_LABELS[category],
            "weight": CATEGORY_WEIGHTS.get(category, 0),
            "score": category_score,
            "level": level,
            "poi_count": len(places),
            "nearest_distance_m": nearest_distance,
            "explanation": _category_explanation(category, category_score, len(places), nearest_distance),
        })
        total += CATEGORY_WEIGHTS.get(category, 0) * category_score / 100

    for category in CATEGORY_LABELS:
        if category not in category_score_map:
            category_score_map[category] = 0
            category_metrics.append({
                "category": category, "label": CATEGORY_LABELS[category], "weight": CATEGORY_WEIGHTS.get(category, 0),
                "score": 0, "level": "不足", "poi_count": 0, "nearest_distance_m": None,
                "explanation": "800m 內未找到足夠資料，建議搭配實地確認。",
            })
    ordered = sorted(all_places, key=lambda place: float(place.get("distance_m", radius_m + 1)))
    nearest = ordered[:3]
    ranked = sorted(category_score_map, key=category_score_map.get, reverse=True)
    strongest = [CATEGORY_LABELS[key] for key in ranked[:2] if category_score_map[key] > 0]
    weakest = [CATEGORY_LABELS[key] for key in reversed(ranked) if category_score_map[key] < 65][:2]
    strength_text = "與".join(strongest) if strongest else "周遭設施"
    weak_text = "與".join(weakest) if weakest else "其他生活設施"
    summary = f"此區{strength_text}密度較高，適合展示生活便利性；{weak_text}資源可再搭配實地確認。"
    recommendation = f"若用於客戶溝通，可強調本區步行範圍內的{strength_text}機能，並將{weak_text}列為看屋時的補充確認項目。"
    overall = max(0, min(score_ceiling, round(total)))
    level = _score_level(overall)
    return {
        "livability_score": overall,
        "livability_level": level,
        "score_summary": f"生活機能總分 {overall}，整體屬於「{level}」；{summary}",
        "category_scores": sorted(category_metrics, key=lambda item: item["weight"], reverse=True),
        "category_score_map": category_score_map,
        "nearest_places": nearest,
        "summary": summary,
        "recommendation_text": recommendation,
        "score_explanation": f"分數依通過類型驗證與去重後的設施、距離及類別權重估算；證據品質為 {evidence_quality_status}，套用 {quality_factor:.2f} 品質係數與 {score_ceiling} 分上限。",
        "evidence_quality_factor": quality_factor,
        "score_ceiling": score_ceiling,
    }


def _score_level(score: int) -> str:
    """Translate a score into the user-facing five-level scale."""

    if score >= 90:
        return "極佳"
    if score >= 75:
        return "良好"
    if score >= 60:
        return "普通"
    if score >= 40:
        return "偏弱"
    return "不足"


def _category_explanation(category: str, score: int, count: int, nearest_distance: int | None) -> str:
    """Explain one category score using visible POI evidence."""

    if not count or nearest_distance is None:
        return "800m 內未找到足夠資料，建議搭配實地確認。"
    subject = {"transport": "大眾運輸節點", "food": "餐飲選擇", "shopping": "採買與商圈", "school": "教育資源", "medical": "醫療資源", "park": "公園綠地"}[category]
    return f"800m 內找到 {count} 個{subject}，最近約 {nearest_distance}m，指標等級為{_score_level(score)}。"


def _distance_weight(distance_m: float) -> float:
    """Return a simple walking-distance weight for one POI."""

    if distance_m <= 300:
        return 1.0
    if distance_m <= 800:
        return 0.55
    return 0.0


def _category_result(category: str, places: list[dict[str, Any]], source: str | None = None, availability: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"category": category, "label": CATEGORY_LABELS[category], "count": len(places), "places": places}
    if source is not None:
        result["source"] = source
    if availability is not None:
        result["availability"] = availability
    return result


def _filter_and_dedupe_google_places(groups: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Validate category types and keep each physical place once in request order."""

    seen: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    totals = {"input_place_count": 0, "accepted_place_count": 0, "rejected_type_count": 0, "deduplicated_count": 0}
    for group in groups:
        category = group["category"]
        accepted: list[dict[str, Any]] = []
        input_count = len(group.get("places", []))
        rejected = 0
        deduplicated = 0
        totals["input_place_count"] += input_count
        for place in group.get("places", []):
            if not is_valid_place_type(category, place.get("types"), place.get("name", "")):
                rejected += 1
                continue
            identity = _place_identity(place)
            if identity in seen:
                deduplicated += 1
                continue
            seen.add(identity)
            accepted.append({**place, "category": category})
        totals["rejected_type_count"] += rejected
        totals["deduplicated_count"] += deduplicated
        totals["accepted_place_count"] += len(accepted)
        cleaned.append({
            **group,
            "count": len(accepted),
            "places": accepted,
            "input_count": input_count,
            "rejected_type_count": rejected,
            "deduplicated_count": deduplicated,
        })
    return cleaned, totals


def _place_identity(place: dict[str, Any]) -> str:
    place_id = str(place.get("place_id") or "").strip()
    if place_id:
        return f"id:{place_id}"
    try:
        return f"coord:{float(place['lat']):.5f},{float(place['lng']):.5f}"
    except (KeyError, TypeError, ValueError):
        name = "".join(str(place.get("name") or "").lower().split())
        address = "".join(str(place.get("address") or "").lower().split())
        return f"text:{name}|{address}"


def _mock_places(lat: float, lng: float, radius_m: int, category: str) -> list[dict[str, Any]]:
    """Normalize the closest bundled region's POIs into nearby-place schema."""

    regions = load_map_data()["regions"]
    region = min(regions, key=lambda row: distance_meters(lat, lng, row["center"]["lat"], row["center"]["lng"]))
    nearby_places = [
        {
            **place,
            "distance_m": distance_meters(lat, lng, place["lat"], place["lng"]),
            "types": place.get("types", [place["category"]]),
            "source": "mock",
            "opening_status": "unknown",
            "opening_status_label": "展示資料",
            "opening_hours_source": "mock",
        }
        for place in region.get("nearby_places", [])
        if place["category"] == category and distance_meters(lat, lng, place["lat"], place["lng"]) <= radius_m
    ]
    if nearby_places:
        return sorted(nearby_places, key=lambda place: place["distance_m"])

    source_category = "commerce" if category in {"shopping", "food"} else category
    layer = next((item for item in region["poi_layers"] if item["category"] == source_category), None)
    points = list(layer.get("points", [])) if layer else []
    if category == "food" and points:
        points = [{**points[0], "name": f"{region['district']}生活圈餐飲"}]
    return [
        {
            "place_id": f"mock-{region['id']}-{category}-{index}",
            "name": point["name"],
            "lat": point["lat"],
            "lng": point["lng"],
            "address": f"{region['city']}{region['district']}{region['road']}周邊",
            "rating": 4.2 if category in {"food", "shopping"} else None,
            "user_rating_count": 80 if category in {"food", "shopping"} else 0,
            "business_status": "OPERATIONAL",
            "opening_status": "unknown",
            "opening_status_label": "展示資料",
            "opening_hours_source": "mock",
            "distance_m": distance_meters(lat, lng, point["lat"], point["lng"]),
            "types": [source_category],
            "category": category,
            "source": "mock",
        }
        for index, point in enumerate(points)
        if distance_meters(lat, lng, point["lat"], point["lng"]) <= radius_m
    ]
