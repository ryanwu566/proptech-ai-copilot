"""Rule-based terrain and disaster risk analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from services.map_service import search_location
from services.terrain_risk_providers import (
    ArdswcSlopeHazardProvider,
    GeologyCloudProvider,
    NlscTerrainProvider,
    WraFloodProvider,
)
from services.terrain_risk_providers.base import source_meta


DISCLAIMER = "本分析僅使用公開圖資做買房前初步檢查，不代表建築結構鑑定、土地使用限制、地質調查或正式防災結論；實際風險仍需以現場、主管機關與專業人員判定為準。"
DEFAULT_LAYERS = [
    "terrain",
    "landslide",
    "debris_flow",
    "flood",
    "geological_sensitivity",
    "liquefaction",
    "active_fault",
]
LAYER_LABELS = {
    "terrain": "地形／坡度",
    "landslide": "大規模崩塌潛勢",
    "debris_flow": "土石流潛勢溪流",
    "flood": "淹水潛勢",
    "geological_sensitivity": "地質敏感區",
    "liquefaction": "土壤液化潛勢",
    "active_fault": "活動斷層",
}
TRANSPARENCY_NOTICE = "地勢與災害資料僅供看房風險參考，資料不足或暫時不可用不代表沒有風險。"


class TerrainRiskLocationError(ValueError):
    """Raised when no coordinates can be resolved."""


def analyze_terrain_risk(
    address: str = "",
    city: str = "",
    district: str = "",
    road: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    radius_m: int = 500,
    include_layers: list[str] | None = None,
    searcher: Callable[[str], dict[str, Any]] | None = None,
    providers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if radius_m < 100 or radius_m > 2000:
        raise ValueError("radius_m must be between 100 and 2000")
    layers = _normalize_layers(include_layers)
    resolved = _resolve_location(address, city, district, road, latitude, longitude, searcher or search_location)
    if resolved is None:
        raise TerrainRiskLocationError("無法定位此地址，請改用完整地址或提供座標後再分析地勢與災害風險。")

    provider_map = providers or _default_providers()
    terrain = _terrain_unavailable()
    hazards = {key: _hazard_skipped(key) if key not in layers else _hazard_unavailable(key) for key in DEFAULT_LAYERS if key != "terrain"}

    if "terrain" in layers:
        terrain = _safe_terrain(provider_map["terrain"], resolved, radius_m)
    slope_layers = tuple(key for key in ("landslide", "debris_flow") if key in layers)
    if slope_layers:
        hazards.update(_safe_hazard_group(provider_map["slope_hazard"], resolved, radius_m, slope_layers))
    if "flood" in layers:
        hazards["flood"] = _safe_hazard(provider_map["flood"], resolved, radius_m, "flood")
    if any(key in layers for key in ("geological_sensitivity", "liquefaction", "active_fault")):
        hazards.update(_safe_hazard_group(provider_map["geology"], resolved, radius_m, ("geological_sensitivity", "liquefaction", "active_fault")))

    risk_factors = _risk_factors(terrain, hazards, layers)
    missing_sources = _missing_sources(terrain, hazards, layers)
    data_quality = _data_quality(terrain, hazards, layers, missing_sources)
    overall = _overall(risk_factors, data_quality, layers)

    return {
        "input": {
            "address": address,
            "city": city,
            "district": district,
            "road": road,
            "latitude": latitude,
            "longitude": longitude,
            "radius_m": radius_m,
            "include_layers": layers,
        },
        "resolved_location": resolved,
        "overall": overall,
        "terrain": terrain,
        "hazards": hazards,
        "risk_factors": risk_factors,
        "missing_sources": missing_sources,
        "recommended_checks": _recommended_checks(overall, missing_sources),
        "map_layers": _map_layers(terrain, hazards, layers),
        "source_transparency": _source_transparency(terrain, hazards, layers),
        "data_quality": data_quality,
        "disclaimer": DISCLAIMER,
    }


def _default_providers() -> dict[str, Any]:
    return {
        "terrain": NlscTerrainProvider(),
        "slope_hazard": ArdswcSlopeHazardProvider(),
        "flood": WraFloodProvider(),
        "geology": GeologyCloudProvider(),
    }


def _normalize_layers(layers: list[str] | None) -> list[str]:
    requested = layers or DEFAULT_LAYERS
    return [item for item in DEFAULT_LAYERS if item in requested]


def _resolve_location(
    address: str,
    city: str,
    district: str,
    road: str,
    latitude: float | None,
    longitude: float | None,
    searcher: Callable[[str], dict[str, Any]],
) -> dict[str, Any] | None:
    query = address.strip() or "".join(part.strip() for part in (city, district, road) if part.strip())
    if latitude is not None and longitude is not None:
        return {
            "address_label": query or "使用者提供座標",
            "latitude": latitude,
            "longitude": longitude,
            "geocoding_confidence": "provided_coordinates",
        }
    if not query:
        return None
    found = searcher(query)
    center = found.get("center") if found.get("matched") else None
    if not center:
        return None
    return {
        "address_label": found.get("formatted_address") or query,
        "latitude": float(center["lat"]),
        "longitude": float(center["lng"]),
        "geocoding_confidence": found.get("confidence", "unknown"),
    }


def _safe_terrain(provider: Any, resolved: dict[str, Any], radius_m: int) -> dict[str, Any]:
    try:
        return provider.analyze(resolved["latitude"], resolved["longitude"], radius_m)
    except Exception as exc:
        return {
            **_terrain_unavailable(),
            "status": "error",
            "explanation": f"地形來源查詢失敗：{type(exc).__name__}。請稍後重試或改至官方圖台確認。",
            "source": source_meta("NLSC 國土測繪中心地形圖資", "內政部國土測繪中心", "https://maps.nlsc.gov.tw/", "error"),
        }


def _safe_hazard(provider: Any, resolved: dict[str, Any], radius_m: int, key: str) -> dict[str, Any]:
    try:
        return provider.analyze(resolved["latitude"], resolved["longitude"], radius_m)
    except Exception as exc:
        return {**_hazard_unavailable(key), "status": "error", "explanation": f"{LAYER_LABELS[key]}來源查詢失敗：{type(exc).__name__}。"}


def _safe_hazard_group(provider: Any, resolved: dict[str, Any], radius_m: int, keys: Iterable[str]) -> dict[str, Any]:
    keys = tuple(keys)
    try:
        try:
            result = provider.analyze(resolved["latitude"], resolved["longitude"], radius_m, include_layers=keys)
        except TypeError as exc:
            if "include_layers" not in str(exc):
                raise
            result = provider.analyze(resolved["latitude"], resolved["longitude"], radius_m)
    except Exception as exc:
        return {key: {**_hazard_unavailable(key), "status": "error", "explanation": f"{LAYER_LABELS[key]}來源查詢失敗：{type(exc).__name__}。"} for key in keys}
    return {key: result.get(key, _hazard_unavailable(key)) for key in keys}


def _terrain_unavailable() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "slope_value": None,
        "slope_class": None,
        "elevation_m": None,
        "explanation": "尚未取得可直接查詢的官方坡度／高程資料。",
        "source": source_meta("NLSC 國土測繪中心地形圖資", "內政部國土測繪中心", "https://maps.nlsc.gov.tw/", "unavailable"),
    }


def _hazard_unavailable(key: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": LAYER_LABELS[key],
        "status": "unavailable",
        "level": "unknown",
        "matched": False,
        "distance_m": None,
        "value": None,
        "explanation": "此圖資目前未設定可合法直接查詢的官方 API，需至官方圖台確認。",
        "source": source_meta(LAYER_LABELS[key], "官方公開圖資", "", "unavailable"),
    }


def _hazard_skipped(key: str) -> dict[str, Any]:
    return {
        **_hazard_unavailable(key),
        "status": "skipped",
        "explanation": "此圖層未在 include_layers 中啟用，已略過查詢。",
    }


def _risk_factors(terrain: dict[str, Any], hazards: dict[str, dict[str, Any]], layers: list[str]) -> list[dict[str, Any]]:
    factors: list[dict[str, Any]] = []
    if "terrain" in layers and terrain.get("status") == "available":
        slope = terrain.get("slope_value")
        if isinstance(slope, (int, float)) and slope >= 30:
            factors.append({"key": "terrain", "level": "medium", "title": "地勢偏陡", "message": "官方坡度資料顯示坡度較高，建議實地確認基地與周邊排水。", "source_name": terrain.get("source", {}).get("name")})
    for key, hazard in hazards.items():
        if key not in layers:
            continue
        if hazard.get("matched"):
            level = hazard.get("level") if hazard.get("level") in {"low", "medium", "high", "unknown"} else "medium"
            factors.append({
                "key": key,
                "level": level,
                "title": hazard.get("label") or LAYER_LABELS.get(key, key),
                "message": hazard.get("explanation") or "官方圖資顯示此項目需進一步確認。",
                "source_name": hazard.get("source", {}).get("name"),
            })
    return factors


def _missing_sources(terrain: dict[str, Any], hazards: dict[str, dict[str, Any]], layers: list[str]) -> list[str]:
    missing: list[str] = []
    if "terrain" in layers and terrain.get("status") in {"unavailable", "error"}:
        missing.append("地形／坡度官方查詢")
    for key, hazard in hazards.items():
        if key in layers and hazard.get("status") in {"unavailable", "error", "limited"}:
            missing.append(f"{LAYER_LABELS[key]}官方查詢")
    return missing


def _data_quality(terrain: dict[str, Any], hazards: dict[str, dict[str, Any]], layers: list[str], missing: list[str]) -> dict[str, Any]:
    checked = len(layers)
    available = 0
    if "terrain" in layers and terrain.get("status") in {"available", "limited"}:
        available += 1
    available += sum(1 for key, value in hazards.items() if key in layers and value.get("status") in {"available", "limited"})
    status = "good" if checked and available == checked else "limited" if available else "unavailable"
    warnings = []
    if missing:
        warnings.append("部分官方圖資目前只能提供外部圖台確認，不能自動判定為低風險。")
    if status == "unavailable":
        warnings.append("主要地勢與災害圖資尚未完成自動比對，請以官方圖台與專業實勘補查。")
    return {"status": status, "warnings": warnings, "checked_at": datetime.now(timezone.utc).isoformat()}


def _overall(risk_factors: list[dict[str, Any]], data_quality: dict[str, Any], layers: list[str]) -> dict[str, str]:
    if data_quality["status"] == "unavailable":
        return {
            "level": "unknown",
            "label": "資料不足，無法判定",
            "summary": "目前未取得足夠官方圖資做自動比對，請改至官方圖台或專業單位確認。",
            "confidence": "unknown",
        }
    if any(item["level"] == "high" for item in risk_factors) or len(risk_factors) >= 2:
        return {"level": "high", "label": "需要優先確認", "summary": "已命中明確或多項風險提醒，建議先補查官方圖台與現場條件。", "confidence": "medium" if data_quality["status"] == "limited" else "high"}
    if risk_factors:
        return {"level": "medium", "label": "有項目需注意", "summary": "有一項地勢或災害相關提醒，建議看屋前補查。", "confidence": "medium"}
    if data_quality["status"] == "good" and set(DEFAULT_LAYERS).issubset(set(layers)):
        return {"level": "low", "label": "目前未比對到明確風險", "summary": "可用官方來源未比對到明確風險，但仍需實地確認。", "confidence": "high"}
    return {"level": "unknown", "label": "資料不足，無法判定", "summary": "部分來源不足，不能推論為低風險。", "confidence": "low"}


def _recommended_checks(overall: dict[str, str], missing: list[str]) -> list[str]:
    checks = ["看屋時確認基地周邊排水、邊坡、擋土設施與地下室淹水紀錄。"]
    if missing:
        checks.append("至官方圖台逐項查詢：" + "、".join(missing[:4]))
    if overall["level"] in {"medium", "high", "unknown"}:
        checks.append("必要時請地政、建管、防災或地質專業人員協助判讀。")
    return checks


def _map_layers(terrain: dict[str, Any], hazards: dict[str, dict[str, Any]], layers: list[str]) -> list[dict[str, Any]]:
    rows = []
    if "terrain" in layers:
        rows.append(_layer_row("terrain", "地形／坡度", terrain))
    rows.extend(_layer_row(key, LAYER_LABELS[key], value) for key, value in hazards.items() if key in layers)
    return rows


def _source_transparency(terrain: dict[str, Any], hazards: dict[str, dict[str, Any]], layers: list[str]) -> dict[str, Any]:
    rows = []
    if "terrain" in layers:
        rows.append(_source_layer_row("terrain", "地形／坡度", terrain))
    rows.extend(_source_layer_row(key, LAYER_LABELS[key], value) for key, value in hazards.items() if key in layers)
    return {"notice": TRANSPARENCY_NOTICE, "layers": rows}


def _source_layer_row(key: str, label: str, payload: dict[str, Any]) -> dict[str, str]:
    status = str(payload.get("status") or "unavailable")
    matched = bool(payload.get("matched"))
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    assessment_status = _assessment_status(status, matched)
    coverage_status = _coverage_status(status, assessment_status)
    return {
        "layer_id": key,
        "display_name": label,
        "source_name": _safe_source_text(source.get("name"), label),
        "source_kind": _safe_source_text(source.get("agency"), "unknown"),
        "assessment_status": assessment_status,
        "coverage_status": coverage_status,
        "data_updated_at": _safe_source_text(source.get("data_updated_at") or source.get("data_vintage"), "unknown"),
        "caveat": _source_caveat(assessment_status),
    }


def _assessment_status(status: str, matched: bool) -> str:
    if status == "skipped":
        return "not_assessed"
    if status in {"unavailable", "error", "limited"}:
        return "unavailable"
    if status == "available" and matched:
        return "matched"
    if status == "available":
        return "not_matched"
    return "unavailable"


def _coverage_status(status: str, assessment_status: str) -> str:
    if assessment_status in {"unavailable", "not_assessed"}:
        return "unknown"
    if status == "available":
        return "covered"
    return "unknown"


def _safe_source_text(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _source_caveat(assessment_status: str) -> str:
    if assessment_status == "matched":
        return "已比對到需補查的風險訊號，建議實地與官方資料複核。"
    if assessment_status == "not_matched":
        return "目前可用資料未比對到明確風險，仍需實地確認。"
    if assessment_status == "not_assessed":
        return "此圖層本次未評估，不能解讀為低風險。"
    return "資料暫時不可用或來源狀態不明，不能解讀為低風險。"


def _layer_row(key: str, label: str, payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source") or {}
    return {
        "key": key,
        "label": label,
        "status": payload.get("status", "unavailable"),
        "source_url": source.get("source_url"),
        "external_view_url": source.get("source_url"),
        "data_vintage": source.get("data_vintage"),
        "data_quality": source.get("data_quality"),
        "limitation": source.get("limitation"),
    }
