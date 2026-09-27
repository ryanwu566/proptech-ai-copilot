"""Pure normalization for official GSMMA geological-sensitivity datasets."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
import io
import re
from typing import Any, Mapping

from pyproj import CRS, Transformer
from shapely import make_valid
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.ops import transform as transform_geometry


TARGET_CRS = "EPSG:4326"
SOURCE_AGENCY = "經濟部地質調查及礦業管理中心"

OFFICIAL_CATEGORY_MAP = {
    "地質遺跡地質敏感區": "geological_heritage_sensitive_area",
    "地下水補注地質敏感區": "groundwater_recharge_sensitive_area",
    "活動斷層地質敏感區": "active_fault_sensitive_area",
    "山崩與地滑地質敏感區": "landslide_sensitive_area",
}

INDEX_FIELDS = (
    "No.",
    "地質敏感區類型",
    "地質敏感區編號",
    "地質敏感區名稱",
    "公告日期",
    "文號",
    "座標系統1",
    "座標系統2",
    "下載連結",
)


class GeologicalSensitivityDatasetError(ValueError):
    status = "unsupported_dataset"


class UnsupportedDatasetError(GeologicalSensitivityDatasetError):
    status = "unsupported_dataset"


class CrsInvalidError(GeologicalSensitivityDatasetError):
    status = "crs_invalid"


@dataclass(frozen=True)
class IndexRecord:
    source_index_no: str
    official_category: str
    canonical_category: str
    sensitivity_area_no: str
    official_name: str
    announcement_date: str
    announcement_no: str
    declared_crs_values: tuple[str, ...]
    source_url: str

    @property
    def designation_identity(self) -> tuple[str, str, str, str, str]:
        return (
            self.official_category,
            self.sensitivity_area_no,
            self.official_name,
            self.announcement_date,
            self.announcement_no,
        )


@dataclass(frozen=True)
class NormalizedFeature:
    official_category: str
    canonical_category: str
    official_name: str
    sensitivity_area_no: str
    announcement_no: str
    announcement_date: str
    source_agency: str
    source_url: str
    source_index_no: str
    source_crs: str
    target_crs: str
    dataset_version: str
    source_package_sha256: str
    original_attributes: Mapping[str, Any]
    geometry: Any


@dataclass(frozen=True)
class QuarantineRecord:
    source_index_no: str
    reason: str
    geometry_type: str | None
    original_attributes: Mapping[str, Any]


@dataclass
class NormalizationStats:
    input_feature_count: int = 0
    accepted_feature_count: int = 0
    rejected_feature_count: int = 0
    invalid_geometry_count: int = 0
    repaired_geometry_count: int = 0
    unsupported_geometry_count: int = 0
    empty_geometry_count: int = 0
    discarded_repair_part_count: int = 0
    official_category_distribution: dict[str, int] = field(default_factory=dict)
    canonical_category_distribution: dict[str, int] = field(default_factory=dict)
    source_crs_distribution: dict[str, int] = field(default_factory=dict)
    geometry_type_distribution: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class FeatureNormalizationResult:
    feature: NormalizedFeature | None
    quarantine: QuarantineRecord | None
    invalid: bool = False
    repaired: bool = False
    unsupported: bool = False
    empty: bool = False
    official_category: str = ""
    canonical_category: str = ""
    source_crs: str = ""
    input_geometry_type: str = "Unknown"
    discarded_repair_part_count: int = 0


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalize_date(value: str) -> str:
    cleaned = _clean(value)
    western = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", cleaned)
    if western:
        year, month, day = map(int, western.groups())
    else:
        roc = re.fullmatch(r"(\d{2,3})年(\d{1,2})月(\d{1,2})日", cleaned)
        if not roc:
            raise UnsupportedDatasetError(f"unsupported announcement date: {cleaned!r}")
        roc_year, month, day = map(int, roc.groups())
        year = roc_year + 1911
    try:
        return date(year, month, day).isoformat()
    except ValueError as exc:
        raise UnsupportedDatasetError(f"invalid announcement date: {cleaned!r}") from exc


def _index_sort_key(record: IndexRecord) -> tuple[int, int | str, str]:
    number = record.source_index_no
    return (0, int(number), record.sensitivity_area_no) if number.isdigit() else (1, number, record.sensitivity_area_no)


def parse_index_csv(payload: bytes) -> list[IndexRecord]:
    """Parse the official index as strict UTF-8 with an optional BOM."""

    if not isinstance(payload, bytes):
        raise UnsupportedDatasetError("official index must be bytes encoded as UTF-8")
    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise UnsupportedDatasetError("official index must be UTF-8 or UTF-8 with BOM") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = tuple(reader.fieldnames or ())
    missing = [name for name in INDEX_FIELDS if name not in headers]
    if missing:
        raise UnsupportedDatasetError(
            "missing required index fields: " + ", ".join(missing)
        )

    records: list[IndexRecord] = []
    seen_area_numbers: dict[str, IndexRecord] = {}
    seen_index_numbers: set[str] = set()
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            raise UnsupportedDatasetError(f"unexpected extra index fields on line {line_number}")
        if not any(_clean(value) for value in row.values()):
            continue
        official_category = _clean(row["地質敏感區類型"])
        canonical_category = OFFICIAL_CATEGORY_MAP.get(official_category)
        if canonical_category is None:
            raise UnsupportedDatasetError(
                f"unsupported official category on line {line_number}: {official_category!r}"
            )
        source_index_no = _clean(row["No."])
        sensitivity_area_no = _clean(row["地質敏感區編號"])
        official_name = _clean(row["地質敏感區名稱"])
        announcement_no = _clean(row["文號"])
        source_url = _clean(row["下載連結"])
        required_values = {
            "No.": source_index_no,
            "地質敏感區編號": sensitivity_area_no,
            "地質敏感區名稱": official_name,
            "文號": announcement_no,
            "下載連結": source_url,
        }
        empty = [name for name, value in required_values.items() if not value]
        if empty:
            raise UnsupportedDatasetError(
                f"empty required index fields on line {line_number}: " + ", ".join(empty)
            )
        declared_crs_values = tuple(
            value
            for value in (_clean(row["座標系統1"]), _clean(row["座標系統2"]))
            if value
        )
        record = IndexRecord(
            source_index_no=source_index_no,
            official_category=official_category,
            canonical_category=canonical_category,
            sensitivity_area_no=sensitivity_area_no,
            official_name=official_name,
            announcement_date=_normalize_date(row["公告日期"]),
            announcement_no=announcement_no,
            declared_crs_values=declared_crs_values,
            source_url=source_url,
        )
        if source_index_no in seen_index_numbers or sensitivity_area_no in seen_area_numbers:
            raise UnsupportedDatasetError(
                f"duplicate index or sensitivity-area identifier: {source_index_no}/{sensitivity_area_no}"
            )
        seen_index_numbers.add(source_index_no)
        seen_area_numbers[sensitivity_area_no] = record
        records.append(record)

    if not records:
        raise UnsupportedDatasetError("official index contains no dataset rows")
    return sorted(records, key=_index_sort_key)


_SUPPORTED_SOURCE_EPSGS = frozenset({3825, 3826, 3827, 3828, 4326})


def _declared_epsgs(value: str) -> set[int]:
    normalized = re.sub(r"[^A-Z0-9]", "", value.upper())
    direct = re.search(r"EPSG(3825|3826|3827|3828|4326)", normalized)
    if direct:
        return {int(direct.group(1))}
    if "WGS84" in normalized or "WGS1984" in normalized:
        return {4326}
    family: tuple[int, int] | None = None
    if "TWD97" in normalized:
        family = (3825, 3826)
    elif "TWD67" in normalized:
        family = (3827, 3828)
    if family is None:
        raise CrsInvalidError(f"unsupported CRS declaration: {value!r}")
    has_119 = "119" in normalized
    has_121 = "121" in normalized
    if has_119 and has_121:
        raise CrsInvalidError(f"ambiguous CRS declaration: {value!r}")
    if has_119:
        return {family[0]}
    if has_121:
        return {family[1]}
    return set(family)


def resolve_source_crs(prj_wkt: str, declared_crs_values: tuple[str, ...]) -> CRS:
    """Resolve a package CRS from its PRJ and cross-check the official index."""

    if not _clean(prj_wkt):
        raise CrsInvalidError("missing shapefile .prj CRS")
    try:
        source_crs = CRS.from_wkt(prj_wkt)
    except Exception as exc:
        raise CrsInvalidError("could not parse shapefile .prj CRS") from exc
    epsg = source_crs.to_epsg()
    if epsg not in _SUPPORTED_SOURCE_EPSGS:
        raise CrsInvalidError(f"unsupported source CRS: {source_crs.to_string()}")
    if not declared_crs_values:
        raise CrsInvalidError("missing official index CRS declaration")
    allowed: set[int] = set()
    for value in declared_crs_values:
        allowed.update(_declared_epsgs(value))
    if epsg not in allowed:
        raise CrsInvalidError(
            f"shapefile CRS EPSG:{epsg} conflicts with official index declarations"
        )
    return CRS.from_epsg(epsg)


def _polygonal_members(geometry: Any) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        members: list[Polygon] = []
        for part in geometry.geoms:
            members.extend(_polygonal_members(part))
        return members
    return []


def _non_polygonal_part_count(geometry: Any) -> int:
    if isinstance(geometry, (Polygon, MultiPolygon)) or geometry.is_empty:
        return 0
    if isinstance(geometry, GeometryCollection):
        return sum(_non_polygonal_part_count(part) for part in geometry.geoms)
    return 1


def _quarantine(
    index_record: IndexRecord,
    attributes: Mapping[str, Any],
    geometry_type: str,
    source_crs: str,
    reason: str,
    *,
    invalid: bool = False,
    unsupported: bool = False,
    empty: bool = False,
) -> FeatureNormalizationResult:
    return FeatureNormalizationResult(
        feature=None,
        quarantine=QuarantineRecord(
            source_index_no=index_record.source_index_no,
            reason=reason,
            geometry_type=geometry_type,
            original_attributes=dict(attributes),
        ),
        invalid=invalid,
        unsupported=unsupported,
        empty=empty,
        official_category=index_record.official_category,
        canonical_category=index_record.canonical_category,
        source_crs=source_crs,
        input_geometry_type=geometry_type,
    )


def normalize_feature(
    geometry: Any,
    attributes: Mapping[str, Any],
    index_record: IndexRecord,
    *,
    source_crs: CRS,
    dataset_version: str,
    source_package_sha256: str,
) -> FeatureNormalizationResult:
    """Normalize one official polygon while preserving legal source metadata."""

    epsg = source_crs.to_epsg()
    if epsg not in _SUPPORTED_SOURCE_EPSGS:
        raise CrsInvalidError(f"unsupported source CRS: {source_crs.to_string()}")
    source_crs_name = f"EPSG:{epsg}"
    geometry_type = getattr(geometry, "geom_type", type(geometry).__name__)
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        return _quarantine(
            index_record,
            attributes,
            geometry_type,
            source_crs_name,
            "unsupported_geometry",
            unsupported=True,
        )
    if geometry.is_empty:
        return _quarantine(
            index_record,
            attributes,
            geometry_type,
            source_crs_name,
            "empty_geometry",
            empty=True,
        )

    invalid = not geometry.is_valid
    repaired = False
    discarded_repair_part_count = 0
    normalized = geometry
    if invalid:
        try:
            candidate = make_valid(geometry)
        except Exception:
            candidate = GeometryCollection()
        members = [part for part in _polygonal_members(candidate) if not part.is_empty]
        discarded_repair_part_count = _non_polygonal_part_count(candidate)
        if not members:
            return _quarantine(
                index_record,
                attributes,
                geometry_type,
                source_crs_name,
                "unrepairable_geometry",
                invalid=True,
            )
        normalized = members[0] if len(members) == 1 else MultiPolygon(members)
        repaired = True

    transformer = Transformer.from_crs(source_crs, TARGET_CRS, always_xy=True)
    try:
        wgs84_geometry = transform_geometry(transformer.transform, normalized)
    except Exception as exc:
        raise CrsInvalidError("geometry transformation failed") from exc
    if wgs84_geometry.is_empty or not wgs84_geometry.is_valid:
        return _quarantine(
            index_record,
            attributes,
            geometry_type,
            source_crs_name,
            "invalid_transformed_geometry",
            invalid=invalid,
            empty=wgs84_geometry.is_empty,
        )

    feature = NormalizedFeature(
        official_category=index_record.official_category,
        canonical_category=index_record.canonical_category,
        official_name=index_record.official_name,
        sensitivity_area_no=index_record.sensitivity_area_no,
        announcement_no=index_record.announcement_no,
        announcement_date=index_record.announcement_date,
        source_agency=SOURCE_AGENCY,
        source_url=index_record.source_url,
        source_index_no=index_record.source_index_no,
        source_crs=source_crs_name,
        target_crs=TARGET_CRS,
        dataset_version=_clean(dataset_version),
        source_package_sha256=_clean(source_package_sha256).lower(),
        original_attributes=dict(attributes),
        geometry=wgs84_geometry,
    )
    return FeatureNormalizationResult(
        feature=feature,
        quarantine=None,
        invalid=invalid,
        repaired=repaired,
        official_category=index_record.official_category,
        canonical_category=index_record.canonical_category,
        source_crs=source_crs_name,
        input_geometry_type=geometry_type,
        discarded_repair_part_count=discarded_repair_part_count,
    )


def _increment(distribution: dict[str, int], value: str) -> None:
    distribution[value] = distribution.get(value, 0) + 1


def summarize_normalization(
    results: list[FeatureNormalizationResult],
) -> tuple[list[NormalizedFeature], list[QuarantineRecord], NormalizationStats]:
    features: list[NormalizedFeature] = []
    quarantine: list[QuarantineRecord] = []
    stats = NormalizationStats()
    for result in results:
        stats.input_feature_count += 1
        _increment(stats.official_category_distribution, result.official_category)
        _increment(stats.canonical_category_distribution, result.canonical_category)
        _increment(stats.source_crs_distribution, result.source_crs)
        _increment(stats.geometry_type_distribution, result.input_geometry_type)
        if result.invalid:
            stats.invalid_geometry_count += 1
        if result.repaired:
            stats.repaired_geometry_count += 1
        if result.unsupported:
            stats.unsupported_geometry_count += 1
        if result.empty:
            stats.empty_geometry_count += 1
        stats.discarded_repair_part_count += result.discarded_repair_part_count
        if result.feature is not None:
            features.append(result.feature)
            stats.accepted_feature_count += 1
        else:
            stats.rejected_feature_count += 1
            if result.quarantine is not None:
                quarantine.append(result.quarantine)
    return features, quarantine, stats
