"""Conservative acceptance rules for property geocoding results."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any


EXACT_OR_ACCEPTABLE = "EXACT_OR_ACCEPTABLE"
PARTIAL_MATCH = "PARTIAL_MATCH"
AMBIGUOUS = "AMBIGUOUS"
INSUFFICIENT_SPECIFICITY = "INSUFFICIENT_SPECIFICITY"
MISMATCH = "MISMATCH"

_HOUSE_NUMBER = re.compile(r"(\d+(?:[-之]\d+)?)號")
_CITY = re.compile(r"([^縣市區鄉鎮\s]{2,4}(?:縣|市))")
_DISTRICT = re.compile(r"([^縣市區鄉鎮\s]{1,5}(?:區|鄉|鎮))")
_ROUTE = re.compile(r"([^\s縣市區鄉鎮]{1,16}(?:大道|路|街))")
_SECTION = re.compile(r"(?:大道|路|街)((?:一|二|三|四|五|六|七|八|九|十)段)")
_ADMIN_TYPES = {
    "administrative_area_level_1",
    "administrative_area_level_2",
    "administrative_area_level_3",
    "country",
    "locality",
    "political",
    "postal_code",
}


def canonical_address(value: Any) -> str:
    """Normalize presentation-only differences without changing address identity."""

    text = unicodedata.normalize("NFKC", str(value or "")).lower().replace("台", "臺")
    return re.sub(r"[\s,，。．、_-]+", "", text)


def evaluate_geocoding_acceptance(query: str, region: dict[str, Any], source: str) -> dict[str, Any]:
    """Classify whether a provider result is safe to use for downstream evidence."""

    original_query = str(query or "").strip()
    normalized_address = str(
        region.get("formatted_address")
        or "".join(str(region.get(key) or "") for key in ("city", "district", "road"))
    ).strip()
    center = region.get("center") if isinstance(region.get("center"), dict) else {}
    metadata = region.get("geocoding_metadata") if isinstance(region.get("geocoding_metadata"), dict) else {}
    query_key = canonical_address(original_query)
    resolved_key = canonical_address(normalized_address)
    reasons: list[str] = []

    query_house = _first_group(_HOUSE_NUMBER, query_key)
    resolved_house = _first_group(_HOUSE_NUMBER, resolved_key)
    # Also check structured street_number from metadata
    metadata_house = re.sub(r"[號号]", "", str(metadata.get("street_number") or "")).strip()
    effective_resolved_house = resolved_house or metadata_house
    if query_house and effective_resolved_house and query_house != effective_resolved_house:
        reasons.append("house_number_mismatch")
    elif query_house and not effective_resolved_house:
        reasons.append("house_number_missing")

    query_route = _first_group(_ROUTE, query_key)
    resolved_route = canonical_address(metadata.get("route") or region.get("road"))
    resolved_route_match = _first_group(_ROUTE, resolved_route or resolved_key)
    if query_route and resolved_route_match and query_route != resolved_route_match:
        reasons.append("street_mismatch")
    elif query_route and not resolved_route_match:
        reasons.append("street_missing")

    # Section comparison (四段 vs 三段)
    query_section = _first_group(_SECTION, query_key)
    resolved_section = _first_group(_SECTION, resolved_route or resolved_key)
    if query_section and resolved_section and query_section != resolved_section:
        reasons.append("street_mismatch")

    query_city = _first_group(_CITY, query_key)
    resolved_city = canonical_address(region.get("city"))
    # Ignore country-level values like 台灣/臺灣 — they are NOT a city
    if resolved_city in ("臺灣", "台灣", "taiwan"):
        resolved_city = ""
    if query_city and resolved_city and query_city != resolved_city:
        reasons.append("city_mismatch")

    query_district = _first_group(_DISTRICT, query_key)
    resolved_district = canonical_address(region.get("district"))
    if query_district and resolved_district and query_district != resolved_district:
        # Flexible match: try with/without suffix since regex can be ambiguous
        # e.g. "前鎮" from regex vs "前鎮區" from provider
        if not (resolved_district.startswith(query_district) or query_district.startswith(resolved_district)):
            reasons.append("district_mismatch")
    elif query_district and not resolved_district:
        reasons.append("district_missing")

    provider_types = {str(item).strip().lower() for item in metadata.get("provider_types", []) if item}
    location_type = str(metadata.get("location_type") or "").upper()
    provider_partial = bool(metadata.get("partial_match"))
    if provider_partial:
        reasons.append("provider_partial_match")
    city_only = bool(provider_types and provider_types <= _ADMIN_TYPES and not resolved_district) or (
        bool(resolved_city) and not resolved_district and not resolved_route_match and not resolved_house
    )
    if city_only:
        reasons.append("city_only_resolution")

    input_specificity = _specificity(query_key)
    resolved_specificity = _specificity(resolved_key, city=resolved_city, district=resolved_district, route=resolved_route_match)
    # Skip specificity complaint when structured metadata confirms identity
    meta_route = canonical_address(metadata.get("route") or "")
    meta_number = re.sub(r"[號号]", "", str(metadata.get("street_number") or "")).strip()
    # Route match is prefix-tolerant (query_route="信義路" matches meta_route="信義路五段")
    route_matches = bool(meta_route and query_route and (meta_route.startswith(query_route) or query_route.startswith(meta_route) or meta_route == query_route))
    has_structured_proof = bool(route_matches and (not query_house or meta_number == query_house))
    if input_specificity >= 2 and resolved_specificity < input_specificity and not has_structured_proof:
        reasons.append("lower_specificity_than_input")
    if location_type in {"APPROXIMATE", "GEOMETRIC_CENTER"} and input_specificity >= 4:
        # Only flag if structured components don't confirm the exact address identity
        structured_route = str(metadata.get("route") or "").strip()
        structured_number = str(metadata.get("street_number") or "").strip()
        has_structured_identity = bool(structured_route and structured_number)
        if not has_structured_identity:
            reasons.append("approximate_provider_location")

    english_tokens = re.findall(r"[a-z0-9]{3,}", query_key)
    # Skip text-similarity checks when structured components prove identity
    structured_route = canonical_address(metadata.get("route") or "")
    structured_number = re.sub(r"[號号]", "", str(metadata.get("street_number") or "")).strip()
    structured_confirms_identity = bool(structured_route and query_route and (structured_route.startswith(query_route) or query_route.startswith(structured_route) or structured_route == query_route))
    if not structured_confirms_identity:
        if len(english_tokens) >= 2:
            matched_tokens = sum(token in resolved_key for token in english_tokens)
            if matched_tokens / len(english_tokens) < 0.6:
                reasons.append("named_place_not_preserved")
        elif query_key and resolved_key and query_key not in resolved_key and resolved_key not in query_key:
            if SequenceMatcher(None, query_key, resolved_key).ratio() < 0.45 and input_specificity >= 2:
                reasons.append("low_text_similarity")

    critical_mismatch = any(reason in reasons for reason in ("house_number_mismatch", "street_mismatch", "city_mismatch", "district_mismatch"))
    insufficient = any(
        reason in reasons
        for reason in (
            "house_number_missing",
            "street_missing",
            "district_missing",
            "city_only_resolution",
            "lower_specificity_than_input",
            "approximate_provider_location",
        )
    )
    ambiguous = any(reason in reasons for reason in ("named_place_not_preserved", "low_text_similarity"))

    if critical_mismatch:
        match_quality = MISMATCH
    elif insufficient:
        match_quality = INSUFFICIENT_SPECIFICITY
    elif provider_partial:
        match_quality = PARTIAL_MATCH
    elif ambiguous:
        match_quality = AMBIGUOUS
    else:
        match_quality = EXACT_OR_ACCEPTABLE

    accepted = match_quality == EXACT_OR_ACCEPTABLE
    return {
        "original_query": original_query,
        "normalized_address": normalized_address,
        "resolved_lat": _safe_coordinate(center.get("lat")),
        "resolved_lng": _safe_coordinate(center.get("lng")),
        "geocoding_source": source,
        "match_quality": match_quality,
        "accepted_for_analysis": accepted,
        "requires_confirmation": not accepted and bool(center),
        "mismatch_reasons": reasons,
        "message": _acceptance_message(match_quality),
    }


def unavailable_geocoding_acceptance(query: str) -> dict[str, Any]:
    return {
        "original_query": str(query or "").strip(),
        "normalized_address": "",
        "resolved_lat": None,
        "resolved_lng": None,
        "geocoding_source": "unavailable",
        "match_quality": INSUFFICIENT_SPECIFICITY,
        "accepted_for_analysis": False,
        "requires_confirmation": False,
        "mismatch_reasons": ["no_geocoding_result"],
        "message": _acceptance_message(INSUFFICIENT_SPECIFICITY),
    }


def _specificity(value: str, *, city: str = "", district: str = "", route: str = "") -> int:
    if _HOUSE_NUMBER.search(value):
        return 4
    if route or _ROUTE.search(value):
        return 3
    if district or _DISTRICT.search(value):
        return 2
    if city or _CITY.search(value):
        return 1
    return 2 if len(value) >= 4 else 0


def _first_group(pattern: re.Pattern[str], value: str) -> str:
    match = pattern.search(value)
    return canonical_address(match.group(1)) if match else ""


def _safe_coordinate(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _acceptance_message(match_quality: str) -> str:
    return {
        EXACT_OR_ACCEPTABLE: "定位結果與輸入條件相符，可用於後續區域參考。",
        PARTIAL_MATCH: "定位服務只回傳部分符合結果，請確認或修正後再分析。",
        AMBIGUOUS: "定位結果可能對應不同地點，請確認完整地址。",
        INSUFFICIENT_SPECIFICITY: "定位結果比輸入更不具體，已停止後續分析。",
        MISMATCH: "定位結果與輸入的重要地址欄位不一致，已停止後續分析。",
    }[match_quality]
