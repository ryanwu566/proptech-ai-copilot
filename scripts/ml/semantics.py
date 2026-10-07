"""Strict, versioned raw PLVR semantics. Evidence references require upstream review.

No positive eligibility inference is made from legacy normalized transactions.
Context evidence is a private staging contract, not proof manufactured here.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATASET_ID = "moi-plvr-existing-sale-main-25119"
REGISTRY = ROOT / "data/taiwan-admin-areas.json"
PARSER_VERSION = "plvr-ml-strict-parser-v1"
TRANSFORM_VERSION = "plvr-ml-foundation-transform-v1"
GEOGRAPHY_VERSION = "plvr-source-county-strict-geography-v1"
TARGET_VERSION = "residential-unit-ntd-ping-log-v1"
AREA_VERSION = "registered-transferred-building-including-aux-common-no-parking-v1"
COHORT_VERSION = "residential-apartment-no-parking-v1"
SOURCE_COUNTIES = dict(zip("abcdefghijkmnopqtuvwxz", (
    "臺北市", "臺中市", "基隆市", "臺南市", "高雄市", "新北市", "宜蘭縣",
    "桃園市", "嘉義市", "新竹縣", "苗栗縣", "南投縣", "彰化縣", "新竹市",
    "雲林縣", "嘉義縣", "屏東縣", "花蓮縣", "臺東縣", "金門縣", "澎湖縣", "連江縣")))
TYPES = {
    "住宅大樓": "住宅大樓", "住宅大樓(11層含以上有電梯)": "住宅大樓",
    "住宅大樓(11層含以上)": "住宅大樓", "華廈": "華廈",
    "華廈(10層含以下有電梯)": "華廈", "公寓": "公寓",
    "公寓(5樓含以下無電梯)": "公寓",
}
HISTORICAL_COUNTIES = {"臺北縣", "桃園縣", "臺中縣", "臺南縣", "高雄縣"}
_AREAS = json.loads(REGISTRY.read_text(encoding="utf-8"))["areas"]
DISTRICTS = {x["county"]: set(x["districts"]) for x in _AREAS}


def text(value) -> str:
    return "" if value is None else str(value).strip()


def evidence_valid(value) -> bool:
    return (isinstance(value, dict) and isinstance(value.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
            and bool(text(value.get("locator"))) and bool(text(value.get("version"))))


def source_county(member: str) -> str | None:
    match = re.fullmatch(r"([a-z])_lvr_land_a\.csv", text(member).lower())
    return SOURCE_COUNTIES.get(match[1]) if match else None


def normalize_geography(raw_city: str, raw_district: str, member: str = "") -> dict:
    city, district = text(raw_city).replace("台", "臺"), text(raw_district).replace("台", "臺")
    origin = source_county(member) if member else None
    result = {"raw_city": raw_city, "raw_district": raw_district, "city": city,
              "district": district, "source_county": origin, "version": GEOGRAPHY_VERSION}
    if "�" in city + district or any(ord(ch) < 32 for ch in city + district):
        reason = "source_encoding_issue"
    elif any(ch.isspace() for ch in city + district) or not district:
        reason = "malformed_source_value"
    elif city in HISTORICAL_COUNTIES:
        reason = "historical_admin_name"
    elif member and origin is None:
        reason = "unsupported_source_member"
    elif origin and city and city != origin:
        reason = "source_county_conflict"
    else:
        city = city or origin or ""
        result["city"] = city
        if city == district and city in {"新竹市", "嘉義市"}:
            reason = "city_level_only"
        elif city not in DISTRICTS:
            reason = "true_unsupported_geography"
        elif district not in DISTRICTS[city]:
            reason = "current_registry_mismatch"
        else:
            reason = "tai_variant" if "台" in text(raw_city) + text(raw_district) else "canonical"
    result.update(valid=reason in {"canonical", "tai_variant"}, reason=reason,
                  source_proven=origin is not None and reason in {"canonical", "tai_variant"})
    return result


def parse_roc_date(value: str) -> dict | None:
    raw = text(value)
    if not re.fullmatch(r"\d{5}|\d{7}", raw, flags=re.ASCII):
        return None
    year, month = int(raw[:3]) + 1911, int(raw[3:5])
    if int(raw[:3]) < 1:
        return None
    try:
        parsed = date(year, month, int(raw[5:]) if len(raw) == 7 else 1)
    except ValueError:
        return None
    return {"value": parsed.isoformat() if len(raw) == 7 else parsed.strftime("%Y-%m"),
            "precision": "day" if len(raw) == 7 else "month"}


def parse_floor(value: str) -> int | None:
    raw = text(value).removesuffix("層")
    if re.fullmatch(r"[0-9]{1,3}", raw):
        number = int(raw)
    else:
        digits = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
        if raw in digits:
            number = digits[raw]
        elif re.fullmatch(r"[一二三四五六七八九]?十[一二三四五六七八九]?", raw):
            tens, units = raw.split("十")
            number = digits.get(tens, 1) * 10 + digits.get(units, 0)
        elif raw == "一百":
            number = 100
        else:
            return None
    return number if 1 <= number <= 100 else None


def parse_counts(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"土地([0-9]{1,4})建物([0-9]{1,4})車位([0-9]{1,4})", text(value))
    return tuple(int(x) for x in match.groups()) if match else None


def number(value) -> Decimal | None:
    raw = text(value)
    if len(raw) > 80 or not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", raw):
        return None
    try:
        result = Decimal(raw)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def classify_parking(raw: dict, context: dict) -> str:
    counts = parse_counts(raw.get("交易筆棟數"))
    price, area = (number(raw.get(key)) for key in ("車位總價元", "車位移轉總面積平方公尺"))
    detail = context.get("parking_detail_count")
    if ((counts and counts[2] > 0) or text(raw.get("車位類別"))
            or (price is not None and price > 0) or (area is not None and area > 0)
            or (type(detail) is int and detail > 0)):
        return "PARKING_PRESENT"
    if any(n is not None and n < 0 for n in (price, area)):
        return "PARKING_SEMANTICS_AMBIGUOUS"
    if any(text(raw.get(key)) and number(raw.get(key)) is None
           for key in ("車位總價元", "車位移轉總面積平方公尺")):
        return "PARKING_SEMANTICS_AMBIGUOUS"
    if not {"車位類別","車位總價元","車位移轉總面積平方公尺"} <= raw.keys():
        return "UNKNOWN"
    if (not counts or type(detail) is not int or detail != 0
            or not evidence_valid(context.get("parking_evidence"))
            or not evidence_valid(context.get("schema_evidence"))):
        return "UNKNOWN"
    if text(raw.get("交易標的")) != "房地(土地+建物)":
        return "PARKING_SEMANTICS_AMBIGUOUS"
    if (price is None or area is None) and context.get("blank_parking_means_absent") is not True:
        return "PARKING_SEMANTICS_AMBIGUOUS"
    return "NO_PARKING_CONFIRMED"


def construct_target(raw: dict, context: dict) -> dict:
    reasons = []
    price, area = number(raw.get("總價元")), number(raw.get("建物移轉總面積平方公尺"))
    if price is None or price <= 0:
        reasons.append("invalid_price")
    if area is None or area <= 0:
        reasons.append("invalid_area")
    if context.get("area_basis") != AREA_VERSION or not evidence_valid(context.get("area_evidence")):
        reasons.append("area_basis_unresolved")
    if classify_parking(raw, context) != "NO_PARKING_CONFIRMED":
        reasons.append("parking_basis_unresolved")
    if reasons:
        return {"valid":False,"reasons":reasons}
    with localcontext() as ctx:
        ctx.prec = 28
        ping = area * Decimal("0.3025")
        unit = price / ping
        sqm_unit = price / area
        if not Decimal(5) <= ping <= Decimal(150):
            reasons.append("scope_area_limit")
        if not Decimal(10000) <= unit <= Decimal(5000000):
            reasons.append("scope_unit_price_limit")
        supplied = text(raw.get("單價元平方公尺"))
        if supplied:
            official = number(supplied)
            if official is None or official <= 0:
                reasons.append("invalid_official_unit_price")
            elif abs(official - sqm_unit) > max(Decimal(1), Decimal("0.001") * sqm_unit):
                reasons.append("unit_basis_mismatch")
        if reasons:
            return {"valid":False,"reasons":reasons}
        return {"valid":True,"reasons":[],"area_ping":str(ping),"unit_price_ntd_ping":str(unit),
                "log_unit_price":math.log(float(unit)),"target_version":TARGET_VERSION,
                "area_version":AREA_VERSION,"target_method":"gross_total_over_verified_no_parking_area"}


def age_at_transaction(transaction: str, completion: str) -> dict | None:
    trans, built = parse_roc_date(transaction), parse_roc_date(completion)
    if not trans or not built:
        return None
    if trans["precision"] == built["precision"] == "day" and built["value"] > trans["value"]:
        return None
    ty, tm = map(int, trans["value"][:7].split("-"))
    by, bm = map(int, built["value"][:7].split("-"))
    months = 12 * (ty - by) + tm - bm
    return {"age_months":months,"age_years":months / 12,"precision":"month"} if months >= 0 else None


def evaluate_row(raw: dict, context: dict) -> dict:
    stages = {}
    def add(stage, condition, reason):
        if condition:
            stages.setdefault(stage, []).append(reason)
    transaction = parse_roc_date(raw.get("交易年月日"))
    counts = parse_counts(raw.get("交易筆棟數"))
    add("parse_valid", not evidence_valid(context.get("schema_evidence"))
        or not text(context.get("source_schema_version")), "source_schema_unverified")
    add("parse_valid", not transaction or transaction["precision"] != "day", "transaction_day_required")
    add("parse_valid", text(raw.get("交易標的")) != "房地(土地+建物)", "unsupported_transaction_target")
    geo = normalize_geography(raw.get("縣市", ""), raw.get("鄉鎮市區", ""), context.get("member_name", ""))
    add("geography_valid", not geo["valid"] or not geo["source_proven"], "geography_" + geo["reason"])
    add("residential_use", text(raw.get("主要用途")) != "住家用", "non_residential_use")
    add("rights_valid", not evidence_valid(context.get("rights_evidence"))
        or context.get("full_rights") is not True or context.get("one_dwelling") is not True, "rights_unverified")
    add("rights_valid", not counts or counts[1] != 1, "not_single_building")
    add("property_type_supported", text(raw.get("建物型態")) not in TYPES, "unsupported_building_type")
    parking = classify_parking(raw, context)
    add("parking_safe", parking != "NO_PARKING_CONFIRMED", "parking_" + parking.lower())
    target = construct_target(raw, context)
    if not target["valid"]:
        stages["target_valid"] = target["reasons"]
    floor, total = parse_floor(raw.get("移轉層次")), parse_floor(raw.get("總樓層數"))
    add("physical_valid", floor is None or total is None or floor > total, "floor_ambiguous")
    add("physical_valid", "備註" not in raw or bool(text(raw.get("備註"))), "special_note_requires_review")
    add("physical_valid", context.get("special_transaction") is not False, "special_status_unverified")
    reasons = [reason for values in stages.values() for reason in values]
    return {"eligible":not reasons,"first_reason":reasons[0] if reasons else None,
            "reasons":reasons,"stage_reasons":stages,"geography":geo,"parking":parking,
            "target":target,"floor":floor,"total_floor":total,"transaction_effective_period":transaction,
            "cohort_version":COHORT_VERSION}
