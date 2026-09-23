"""Pure offline dataset and normalization logic for WRA flood potential SHP.

Scope (Phase 1): this module contains ONLY pure functions and small data
models.  It does not:

* touch ``WraFloodProvider`` or the Terrain Risk runtime,
* read or write a database,
* download data, call a provider, or contact Cloudflare R2,
* retain query coordinates.

Official raw/processed flood artifacts are intended to live in Cloudflare R2
(bucket ``proptech-government-data`` under ``raw/wra/flood/`` and
``processed/wra/flood/``).  Large SHP/ZIP artifacts must never be committed to
the repository; only tiny synthetic fixtures belong in tests.

The canonical flood depth range is derived exclusively from the ``Class``
attribute.  The raw ``flood_dept`` string is preserved verbatim and, when it is
malformed, flagged -- but it is never parsed as canonical truth.

Quality expectations (feature count, class distribution, zero invalid/empty
geometries, ~0 percent area difference after ``make_valid``) have only been
verified for the 24-hour / 350mm scenario.  Callers must pass their own
``expected`` metadata for any other scenario; nothing here hard-codes a single
scenario's counts as a permanent rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid


# ---------------------------------------------------------------------------
# A. Canonical depth mapping (Class is the single source of truth)
# ---------------------------------------------------------------------------

#: Canonical flood depth range keyed by official ``Class`` value.
CLASS_TO_CANONICAL_DEPTH: dict[int, str] = {
    1: "0.3-0.5 m",
    2: "0.5-1.0 m",
    3: "1.0-2.0 m",
    4: "2.0-3.0 m",
    5: ">3.0 m",
}

#: The only accepted ``Class`` values.
VALID_CLASSES: frozenset[int] = frozenset(CLASS_TO_CANONICAL_DEPTH)

#: Source CRS of the official WRA flood SHP.
SOURCE_CRS = "EPSG:3826"

#: Runtime CRS used for point-in-polygon matching.
TARGET_CRS = "EPSG:4326"

#: Required per-feature attribute fields (excluding geometry).
REQUIRED_FIELDS: frozenset[str] = frozenset({"Class"})

_ACCEPTED_GEOMETRY_TYPES: frozenset[str] = frozenset({"Polygon", "MultiPolygon"})


def canonical_depth_for_class(class_value: int) -> str:
    """Return the canonical depth range for a ``Class`` value.

    Raises ``ValueError`` for any value outside ``{1, 2, 3, 4, 5}``.  The
    canonical range is derived solely from ``Class``; ``flood_dept`` is never
    consulted here.
    """

    normalized = _coerce_class(class_value)
    if normalized is None:
        raise ValueError(f"invalid flood Class: {class_value!r}")
    return CLASS_TO_CANONICAL_DEPTH[normalized]


def _coerce_class(class_value: Any) -> int | None:
    """Best-effort coercion of a ``Class`` attribute to a valid int, or None."""

    if isinstance(class_value, bool):
        return None
    if isinstance(class_value, int):
        return class_value if class_value in VALID_CLASSES else None
    if isinstance(class_value, float):
        if class_value.is_integer() and int(class_value) in VALID_CLASSES:
            return int(class_value)
        return None
    if isinstance(class_value, str):
        text = class_value.strip()
        if text.isdigit() and int(text) in VALID_CLASSES:
            return int(text)
        return None
    return None


# Malformed ``flood_dept`` examples observed in the official 24h/350mm SHP
# (concentrated in 金門 / 連江 / 澎湖), e.g. ``0.3-0.>3.0`` or ``0.>3.0-1.0``.
def is_flood_dept_malformed(flood_dept_raw: Any) -> bool:
    """Return True when the raw ``flood_dept`` string looks malformed.

    A well-formed value is either a plain range ``a-b`` of numeric bounds or a
    ``>x`` form.  Anything containing ``>`` in a non-terminal position, or with
    more than one range separator around a stray ``>``, is treated as malformed.
    This detection never feeds canonical depth; it only sets a flag.
    """

    if flood_dept_raw is None:
        return True
    text = str(flood_dept_raw).strip()
    if not text:
        return True
    # A stray ">" that is not the single leading marker of a ">x" bound is the
    # signature of the observed malformed strings (e.g. "0.3-0.>3.0").
    inner = text[1:] if text.startswith(">") else text
    if ">" in inner:
        return True
    if text.startswith(">"):
        return not _is_number(text[1:])
    parts = text.split("-")
    if len(parts) != 2:
        return True
    return not (_is_number(parts[0]) and _is_number(parts[1]))


def _is_number(value: str) -> bool:
    try:
        float(value.strip())
    except (TypeError, ValueError):
        return False
    return True


# ---------------------------------------------------------------------------
# B. Geometry normalization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeometryNormalizationResult:
    """Outcome of normalizing one geometry via ``make_valid``."""

    valid: bool
    geometry: BaseGeometry | None
    geometry_type: str | None
    error: str | None = None


def normalize_geometry(geometry: BaseGeometry | None) -> GeometryNormalizationResult:
    """Validate and repair a single Polygon/MultiPolygon geometry.

    Applies Shapely ``make_valid`` and enforces that the result is non-null,
    non-empty, valid, and still a Polygon or MultiPolygon.  If ``make_valid``
    produces any other geometry type (e.g. GeometryCollection, LineString,
    Point), this returns a validation failure rather than silently accepting it.
    """

    if geometry is None:
        return GeometryNormalizationResult(False, None, None, "null_geometry")
    if not isinstance(geometry, BaseGeometry):
        return GeometryNormalizationResult(False, None, None, "not_a_geometry")
    if geometry.is_empty:
        return GeometryNormalizationResult(False, None, geometry.geom_type, "empty_geometry")
    if geometry.geom_type not in _ACCEPTED_GEOMETRY_TYPES:
        return GeometryNormalizationResult(False, None, geometry.geom_type, "unexpected_input_geometry_type")

    repaired = make_valid(geometry)

    if repaired is None or repaired.is_empty:
        return GeometryNormalizationResult(False, None, None, "empty_after_make_valid")
    if repaired.geom_type not in _ACCEPTED_GEOMETRY_TYPES:
        return GeometryNormalizationResult(
            False, None, repaired.geom_type, "unexpected_geometry_type_after_make_valid"
        )
    if not repaired.is_valid:
        return GeometryNormalizationResult(False, None, repaired.geom_type, "still_invalid_after_make_valid")
    return GeometryNormalizationResult(True, repaired, repaired.geom_type)


# ---------------------------------------------------------------------------
# C. CRS transformation helper
# ---------------------------------------------------------------------------

# Cache the forward transformer; ``always_xy=True`` keeps (x=lon, y=lat) order.
_TRANSFORMER_3826_TO_4326 = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)


def project_3826_to_4326(x: float, y: float) -> tuple[float, float]:
    """Project a single EPSG:3826 (x, y) coordinate to EPSG:4326 (lon, lat)."""

    lon, lat = _TRANSFORMER_3826_TO_4326.transform(x, y)
    return float(lon), float(lat)


def transform_geometry_3826_to_4326(geometry: BaseGeometry) -> BaseGeometry:
    """Reproject a Shapely geometry from EPSG:3826 to EPSG:4326.

    Uses the module-level ``always_xy=True`` transformer so the output is in
    (lon, lat) order, matching the repo's WGS84 convention.
    """

    from shapely.ops import transform as shapely_transform

    def _project(xs: Any, ys: Any, zs: Any = None) -> tuple[Any, ...]:
        lons, lats = _TRANSFORMER_3826_TO_4326.transform(xs, ys)
        if zs is None:
            return lons, lats
        return lons, lats, zs

    return shapely_transform(_project, geometry)


# ---------------------------------------------------------------------------
# Feature model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FloodFeature:
    """A normalized flood feature ready for point-in-polygon matching.

    ``geometry`` is expected to be a valid WGS84 (EPSG:4326) Polygon or
    MultiPolygon.  ``canonical_depth`` is derived from ``class_value`` only.
    """

    class_value: int
    canonical_depth: str
    geometry: BaseGeometry
    flood_dept_raw: Any = None
    flood_dept_malformed: bool = False
    properties: Mapping[str, Any] = field(default_factory=dict)

    def metadata(self) -> dict[str, Any]:
        """Coordinate-free metadata describing this feature."""

        return {
            "class": self.class_value,
            "canonical_depth": self.canonical_depth,
            "flood_dept_raw": self.flood_dept_raw,
            "flood_dept_malformed": self.flood_dept_malformed,
            "geometry_type": self.geometry.geom_type,
        }


# ---------------------------------------------------------------------------
# D. Dataset validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasetValidationSummary:
    """Aggregate validation statistics for a candidate flood dataset."""

    valid: bool
    feature_count: int
    accepted_count: int
    rejected_count: int
    class_distribution: dict[int, int]
    malformed_flood_dept_count: int
    invalid_geometry_count: int
    null_or_empty_geometry_count: int
    invalid_class_count: int
    missing_field_count: int
    errors: list[str] = field(default_factory=list)
    rejections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "feature_count": self.feature_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "class_distribution": dict(sorted(self.class_distribution.items())),
            "malformed_flood_dept_count": self.malformed_flood_dept_count,
            "invalid_geometry_count": self.invalid_geometry_count,
            "null_or_empty_geometry_count": self.null_or_empty_geometry_count,
            "invalid_class_count": self.invalid_class_count,
            "missing_field_count": self.missing_field_count,
            "errors": list(self.errors),
            "rejections": list(self.rejections),
        }


@dataclass(frozen=True)
class DatasetExpectation:
    """Optional, caller-supplied expectations for a specific scenario.

    Nothing here is hard-coded per scenario.  The 24h/350mm fixture/tests may
    pass known values; other scenarios must supply their own or omit them.
    """

    feature_count: int | None = None
    class_distribution: Mapping[int, int] | None = None
    malformed_flood_dept_count: int | None = None
    max_invalid_geometry_count: int | None = None


def _raw_field(record: Mapping[str, Any], name: str) -> Any:
    """Read a record field allowing common WRA aliases (case/synonyms)."""

    if name in record:
        return record[name]
    aliases = {
        "Class": ("class", "CLASS"),
        "flood_dept": ("FLOOD_DEPT", "flood_dept_raw"),
    }
    for alias in aliases.get(name, ()):  # pragma: no branch - trivial
        if alias in record:
            return record[alias]
    return None


def normalize_feature(record: Mapping[str, Any]) -> tuple[FloodFeature | None, str | None]:
    """Normalize one raw record into a :class:`FloodFeature` or a reason string.

    ``record`` must contain a ``Class`` field and a ``geometry`` (a Shapely
    geometry).  The returned reason is a machine-readable rejection code when
    the feature cannot be accepted.
    """

    if not isinstance(record, Mapping):
        return None, "not_a_record"

    if _raw_field(record, "Class") is None and "Class" not in record:
        # Distinguish "missing field" from "present but invalid".
        return None, "missing_field:Class"

    class_value = _coerce_class(_raw_field(record, "Class"))
    if class_value is None:
        return None, "invalid_class"

    geometry = record.get("geometry")
    geometry_result = normalize_geometry(geometry if isinstance(geometry, BaseGeometry) else None) \
        if not isinstance(geometry, BaseGeometry) else normalize_geometry(geometry)
    if not geometry_result.valid or geometry_result.geometry is None:
        return None, f"geometry:{geometry_result.error or 'invalid'}"

    flood_dept_raw = _raw_field(record, "flood_dept")
    malformed = is_flood_dept_malformed(flood_dept_raw)

    feature = FloodFeature(
        class_value=class_value,
        canonical_depth=CLASS_TO_CANONICAL_DEPTH[class_value],
        geometry=geometry_result.geometry,
        flood_dept_raw=flood_dept_raw,
        flood_dept_malformed=malformed,
        properties={key: value for key, value in record.items() if key != "geometry"},
    )
    return feature, None


def validate_dataset(
    records: Iterable[Mapping[str, Any]],
    *,
    expected: DatasetExpectation | None = None,
) -> tuple[list[FloodFeature], DatasetValidationSummary]:
    """Validate and normalize a sequence of raw flood records.

    Returns the accepted features plus an aggregate summary.  Geometry is NOT
    reprojected here; callers decide whether inputs are already WGS84 or need
    :func:`transform_geometry_3826_to_4326` first.
    """

    records = list(records)
    accepted: list[FloodFeature] = []
    rejections: list[dict[str, Any]] = []
    class_distribution: dict[int, int] = {}
    malformed_count = 0
    invalid_geometry_count = 0
    null_or_empty_count = 0
    invalid_class_count = 0
    missing_field_count = 0

    for index, record in enumerate(records):
        feature, reason = normalize_feature(record)
        if feature is None:
            rejections.append({"index": index, "reason": reason})
            if reason == "invalid_class":
                invalid_class_count += 1
            elif reason and reason.startswith("missing_field"):
                missing_field_count += 1
            elif reason and reason.startswith("geometry:"):
                detail = reason.split(":", 1)[1]
                if detail in {"null_geometry", "empty_geometry", "empty_after_make_valid", "not_a_geometry"}:
                    null_or_empty_count += 1
                else:
                    invalid_geometry_count += 1
            continue
        accepted.append(feature)
        class_distribution[feature.class_value] = class_distribution.get(feature.class_value, 0) + 1
        if feature.flood_dept_malformed:
            malformed_count += 1

    errors: list[str] = []
    if not accepted:
        errors.append("no_valid_features")
    if expected is not None:
        errors.extend(_check_expectation(expected, len(accepted), class_distribution, malformed_count, invalid_geometry_count))

    summary = DatasetValidationSummary(
        valid=not errors,
        feature_count=len(records),
        accepted_count=len(accepted),
        rejected_count=len(rejections),
        class_distribution=class_distribution,
        malformed_flood_dept_count=malformed_count,
        invalid_geometry_count=invalid_geometry_count,
        null_or_empty_geometry_count=null_or_empty_count,
        invalid_class_count=invalid_class_count,
        missing_field_count=missing_field_count,
        errors=errors,
        rejections=rejections,
    )
    return accepted, summary


def _check_expectation(
    expected: DatasetExpectation,
    accepted_count: int,
    class_distribution: Mapping[int, int],
    malformed_count: int,
    invalid_geometry_count: int,
) -> list[str]:
    errors: list[str] = []
    if expected.feature_count is not None and accepted_count != expected.feature_count:
        errors.append(f"feature_count_mismatch:expected={expected.feature_count},actual={accepted_count}")
    if expected.class_distribution is not None:
        expected_dist = {int(k): int(v) for k, v in expected.class_distribution.items()}
        if dict(sorted(class_distribution.items())) != dict(sorted(expected_dist.items())):
            errors.append(f"class_distribution_mismatch:expected={dict(sorted(expected_dist.items()))},actual={dict(sorted(class_distribution.items()))}")
    if expected.malformed_flood_dept_count is not None and malformed_count != expected.malformed_flood_dept_count:
        errors.append(f"malformed_flood_dept_count_mismatch:expected={expected.malformed_flood_dept_count},actual={malformed_count}")
    if expected.max_invalid_geometry_count is not None and invalid_geometry_count > expected.max_invalid_geometry_count:
        errors.append(f"invalid_geometry_over_limit:limit={expected.max_invalid_geometry_count},actual={invalid_geometry_count}")
    return errors


# ---------------------------------------------------------------------------
# E. Point-in-polygon matcher
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FloodMatchResult:
    """Result of matching a WGS84 point against normalized flood features."""

    matched: bool
    matched_feature: dict[str, Any] | None = None
    matched_count: int = 0


def match_point(
    lon: float,
    lat: float,
    features: Sequence[FloodFeature],
) -> FloodMatchResult:
    """Match a WGS84 (lon, lat) point against normalized flood features.

    Uses ``intersects`` so boundary points are treated as hits (rather than
    being excluded by strict ``contains``).  When several features intersect,
    the one with the highest ``Class`` (deepest canonical range) is reported
    as the primary match.

    This does not persist the query coordinate.  It has no global side effect;
    callers pass the feature sequence explicitly.
    """

    point = Point(float(lon), float(lat))
    hits = [feature for feature in features if feature.geometry.intersects(point)]
    if not hits:
        return FloodMatchResult(matched=False, matched_feature=None, matched_count=0)
    primary = max(hits, key=lambda feature: feature.class_value)
    return FloodMatchResult(
        matched=True,
        matched_feature=primary.metadata(),
        matched_count=len(hits),
    )
