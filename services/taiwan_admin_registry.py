"""Canonical Taiwan county and district registry for safe market queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = ROOT / "data" / "taiwan-admin-areas.json"


@dataclass(frozen=True)
class TaiwanRegion:
    county: str
    district: str


@dataclass(frozen=True)
class RegionNormalizationResult:
    county: str
    district: str
    valid: bool
    reason: str


def load_taiwan_admin_areas(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the safe county/district registry."""

    payload = json.loads((path or DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    areas = payload.get("areas")
    if not isinstance(areas, list) or not areas:
        raise ValueError("Taiwan admin area registry is empty.")
    return areas


def iter_taiwan_regions(path: Path | None = None) -> list[TaiwanRegion]:
    regions: list[TaiwanRegion] = []
    for area in load_taiwan_admin_areas(path):
        county = _required_text(area.get("county"))
        districts = area.get("districts")
        if not isinstance(districts, list) or not districts:
            raise ValueError("Taiwan admin area registry has an invalid district list.")
        for district in districts:
            regions.append(TaiwanRegion(county=county, district=_required_text(district)))
    return regions


def expected_region_count(path: Path | None = None) -> int:
    return len(iter_taiwan_regions(path))


def normalize_market_region(
    county: str,
    district: str = "",
    *,
    path: Path | None = None,
) -> RegionNormalizationResult:
    """Normalize one county and optional district without cross-county fallback."""

    county_aliases = _county_aliases(path)
    canonical_county = county_aliases.get(_normalize_key(county), "")
    if not canonical_county:
        return RegionNormalizationResult("", "", False, "unknown_county")

    clean_district = (district or "").strip()
    if not clean_district:
        return RegionNormalizationResult(canonical_county, "", True, "county_only")

    district_aliases = _district_aliases(canonical_county, path)
    canonical_district = district_aliases.get(_normalize_key(clean_district), "")
    if not canonical_district:
        return RegionNormalizationResult(canonical_county, "", False, "unknown_district")
    return RegionNormalizationResult(canonical_county, canonical_district, True, "county_district")


def audit_region_coverage(
    covered_regions: Iterable[tuple[str, str]],
    *,
    unknown_regions: Iterable[tuple[str, str]] = (),
    path: Path | None = None,
) -> dict[str, Any]:
    expected = {(region.county, region.district) for region in iter_taiwan_regions(path)}
    covered = _valid_region_pairs(covered_regions, expected)
    unknown = _valid_region_pairs(unknown_regions, expected) - covered
    missing = expected - covered - unknown
    status = "FULL" if not missing and not unknown else "UNKNOWN" if unknown else "PARTIAL"
    return {
        "status": status,
        "expected_region_count": len(expected),
        "covered_region_count": len(covered),
        "missing_region_count": len(missing),
        "unknown_region_count": len(unknown),
        "missing_regions": sorted(_region_label(*item) for item in missing),
        "unknown_regions": sorted(_region_label(*item) for item in unknown),
    }


def _county_aliases(path: Path | None = None) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for area in load_taiwan_admin_areas(path):
        county = _required_text(area.get("county"))
        candidates = {
            county,
            county.replace("臺", "台"),
            county.removesuffix("市").removesuffix("縣"),
            county.replace("臺", "台").removesuffix("市").removesuffix("縣"),
        }
        for candidate in candidates:
            aliases[_normalize_key(candidate)] = county
    return aliases


def _district_aliases(county: str, path: Path | None = None) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for area in load_taiwan_admin_areas(path):
        if _required_text(area.get("county")) != county:
            continue
        for district in area.get("districts", []):
            text = _required_text(district)
            aliases[_normalize_key(text)] = text
        break
    return aliases


def _valid_region_pairs(regions: Iterable[tuple[str, str]], expected: set[tuple[str, str]]) -> set[tuple[str, str]]:
    return {(county, district) for county, district in regions if (county, district) in expected}


def _region_label(county: str, district: str) -> str:
    return f"{county}/{district}"


def _required_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Taiwan admin area registry contains a blank value.")
    return text


def _normalize_key(value: str) -> str:
    return (value or "").strip().replace(" ", "").replace("\t", "").replace("\n", "").replace("台", "臺")
