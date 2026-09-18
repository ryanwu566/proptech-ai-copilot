"""Conservative, provider-independent Taiwan parcel hypothesis normalization."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping

from services.vnext.errors import ErrorCode, VNextError

PARCEL_NORMALIZATION_VERSION = "parcel-v1"
_FIELDS = ("county_city", "district_township", "section", "subsection", "land_number")
_REQUIRED = ("county_city", "district_township", "section", "land_number")
_LAND_NUMBER = re.compile(r"^[0-9]{1,6}(?:[-之][0-9]{1,6})?$")
_PLACE = re.compile(r"^[^\W_]+$", re.UNICODE)


@dataclass(frozen=True)
class NormalizedParcelHypothesis:
    raw_input: Mapping[str, str | None]
    normalized_components: Mapping[str, str | None]
    normalized_key: str
    display_value: str


def _invalid(field: str, reason: str) -> VNextError:
    return VNextError(ErrorCode.VALIDATION_FAILED, details={"field": field, "reason": reason})


def normalize_parcel_hypothesis(components: Mapping[str, str | None]) -> NormalizedParcelHypothesis:
    """Normalize formatting only; never infer administrative or cadastral facts."""

    if set(components) - set(_FIELDS):
        raise _invalid("components", "unsupported_structure")
    raw = {field: components.get(field) for field in _FIELDS}
    normalized: dict[str, str | None] = {}
    for field in _FIELDS:
        value = raw[field]
        if value is None or not value.strip():
            if field in _REQUIRED:
                raise _invalid(field, "missing_required")
            normalized[field] = None
            continue
        if len(value) > 160:
            raise _invalid(field, "unsupported_structure")
        selected = unicodedata.normalize("NFKC", value).strip()
        if field == "land_number":
            selected = re.sub(r"\s*([-之])\s*", r"\1", selected)
            if not _LAND_NUMBER.fullmatch(selected):
                raise _invalid(field, "malformed_land_number")
            selected = selected.replace("之", "-")
        else:
            # Whitespace in these structured Taiwan names is formatting, not a
            # basis for changing characters such as 臺/台 or guessing suffixes.
            if re.search(r"[A-Za-z]\s+[A-Za-z]", selected):
                raise _invalid(field, "ambiguous_structure")
            selected = re.sub(r"\s+", "", selected)
            if not _PLACE.fullmatch(selected):
                raise _invalid(field, "ambiguous_structure")
        normalized[field] = selected
    encoded = json.dumps([normalized[field] for field in _FIELDS], ensure_ascii=False, separators=(",", ":"))
    key = f"{PARCEL_NORMALIZATION_VERSION}:{encoded}"
    if len(key) > 512:
        raise _invalid("components", "unsupported_structure")
    display = " ".join(str(normalized[field]) for field in _FIELDS if normalized[field] is not None)
    if len(display) > 512:
        raise _invalid("components", "unsupported_structure")
    return NormalizedParcelHypothesis(raw, normalized, key, display)
