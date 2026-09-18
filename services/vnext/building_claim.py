"""Conservative normalization of a user's cadastral building-number claim."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping

from services.vnext.errors import ErrorCode, VNextError


BUILDING_CLAIM_VERSION = "building-cadastral-claim-v1"
BUILDING_CLAIM_KIND = "cadastral_building_number"
_FIELDS = (
    "county_city", "district_township", "section", "subsection_status",
    "subsection", "building_number",
)
_PLACE = re.compile(r"^[^\W_]+$", re.UNICODE)
_BUILDING_NUMBER = re.compile(r"^[0-9]{1,6}(?:[-之][0-9]{1,6})?$")


@dataclass(frozen=True)
class NormalizedBuildingClaim:
    raw_input: Mapping[str, str | None]
    normalized_components: Mapping[str, str | None]
    normalized_key: str
    display_value: str


def _invalid(field: str, reason: str) -> VNextError:
    return VNextError(ErrorCode.VALIDATION_FAILED, details={"field": field, "reason": reason})


def normalize_building_claim(components: Mapping[str, str | None]) -> NormalizedBuildingClaim:
    """Fingerprint a fully scoped manual claim; never infer an official identity."""

    if set(components) != set(_FIELDS):
        raise _invalid("components", "unsupported_structure")
    raw = {field: components[field] for field in _FIELDS}
    status = raw["subsection_status"]
    if not isinstance(status, str) or status not in {"specified", "not_applicable"}:
        raise _invalid("subsection_status", "unsupported_structure")
    if status == "specified" and not raw["subsection"]:
        raise _invalid("subsection", "missing_required")
    if status == "not_applicable" and raw["subsection"] is not None:
        raise _invalid("subsection", "unsupported_structure")

    normalized: dict[str, str | None] = {"subsection_status": status}
    for field in ("county_city", "district_township", "section", "subsection", "building_number"):
        value = raw[field]
        if value is None:
            if field == "subsection" and status == "not_applicable":
                normalized[field] = None
                continue
            raise _invalid(field, "missing_required")
        if not isinstance(value, str) or len(value) > 160 or not value.strip():
            raise _invalid(field, "missing_required" if not value else "unsupported_structure")
        selected = unicodedata.normalize("NFKC", value).strip()
        if field == "building_number":
            if not _BUILDING_NUMBER.fullmatch(selected):
                raise _invalid(field, "malformed_building_number")
        elif not _PLACE.fullmatch(selected):
            raise _invalid(field, "ambiguous_structure")
        normalized[field] = selected

    key_fields = [normalized[field] for field in _FIELDS]
    key = f"{BUILDING_CLAIM_VERSION}:" + json.dumps(
        key_fields, ensure_ascii=False, separators=(",", ":"),
    )
    display = " ".join(
        str(normalized[field]) for field in
        ("county_city", "district_township", "section", "subsection", "building_number")
        if normalized[field] is not None
    ) + " (manual cadastral claim)"
    if len(key) > 512 or len(display) > 512:
        raise _invalid("components", "unsupported_structure")
    return NormalizedBuildingClaim(raw, normalized, key, display)
