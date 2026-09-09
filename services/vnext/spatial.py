"""Provider-independent GIS contracts for the Stage 2A foundation.

This module deliberately owns no provider credentials, persistence, production
feature gate, or legal parcel-identity decision.  Spatial observations become
Stage 1 Evidence drafts and identity-affecting graph edges remain proposed
until the existing human-confirmation workflow approves them.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Generic, Mapping, Protocol, Sequence, TypeVar
from uuid import UUID

import pyproj
import shapely
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

from services.vnext.property_graph import (
    CoverageStatus,
    EvidenceDraft,
    EvidenceStatus,
    LicenseStatus,
    PropertyRelationDraft,
    PropertyRelationStatus,
    PropertyRelationType,
    QualityStatus,
    RelationDirection,
    SourceEnvironment,
    SourceType,
)


INTERCHANGE_CRS_ID = "EPSG:4326"
MAX_GEOMETRY_COORDINATES = 100_000
_STABLE_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{1,119}$")
_SAFE_ERROR_CODE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")


class SpatialContractError(ValueError):
    """A bounded validation failure that never includes provider payloads."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class GeometryType(str, Enum):
    POINT = "Point"
    LINE_STRING = "LineString"
    POLYGON = "Polygon"
    MULTI_POLYGON = "MultiPolygon"


class CoordinateOrder(str, Enum):
    LONGITUDE_LATITUDE = "longitude_latitude"
    EASTING_NORTHING = "easting_northing"
    X_Y = "x_y"


class SpatialAuthority(str, Enum):
    OFFICIAL = "official"
    DERIVED = "derived"
    USER_SUPPLIED = "user_supplied"
    SYNTHETIC = "synthetic"
    UNKNOWN = "unknown"


class SpatialCoverageStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class SpatialAvailability(str, Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    PENDING_APPROVAL = "pending_approval"


class SpatialObservationStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    NO_MATCH = "no_match"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    PARTIAL_COVERAGE = "partial_coverage"
    PROVIDER_ERROR = "provider_error"
    STALE = "stale"
    NOT_ASSESSED = "not_assessed"


class ProviderResultStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    NO_MATCH = "no_match"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    PROVIDER_ERROR = "provider_error"
    STALE = "stale"
    NOT_ASSESSED = "not_assessed"


class TemporalSemantics(str, Enum):
    SNAPSHOT = "snapshot"
    EFFECTIVE_INTERVAL = "effective_interval"
    LIVE_OBSERVATION = "live_observation"
    UNKNOWN = "unknown"


class RefreshSemantics(str, Enum):
    EVENT_DRIVEN = "event_driven"
    PERIODIC = "periodic"
    MANUAL = "manual"
    IMMUTABLE_RELEASE = "immutable_release"
    UNKNOWN = "unknown"


class SpatialOperation(str, Enum):
    POINT_IN_POLYGON = "point_in_polygon"
    INTERSECTS = "intersects"
    CONTAINS = "contains"
    DISTANCE = "distance"
    NEAREST = "nearest"
    BOUNDING_BOX = "bounding_box"


class OperationUnit(str, Enum):
    BOOLEAN = "boolean"
    METERS = "meters"
    CRS_UNITS = "crs_units"


def _bounded(value: str, *, maximum: int = 240) -> str:
    selected = value.strip()
    if not selected or len(selected) > maximum or "\x00" in selected:
        raise SpatialContractError("invalid_text")
    return selected


def _aware(value: datetime | None, *, required: bool = False) -> datetime | None:
    if value is None:
        if required:
            raise SpatialContractError("timestamp_required")
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise SpatialContractError("timezone_required")
    return value


def _json_compatible(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


def _json_object(value: Mapping[str, object]) -> Mapping[str, object]:
    try:
        encoded = json.dumps(
            _json_compatible(value),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        decoded = json.loads(encoded)
    except (TypeError, ValueError):
        raise SpatialContractError("invalid_json_object") from None
    if not isinstance(decoded, dict):
        raise SpatialContractError("invalid_json_object")
    return MappingProxyType(decoded)


def _stable_key(value: str) -> str:
    selected = value.strip().lower()
    if not _STABLE_KEY.fullmatch(selected):
        raise SpatialContractError("invalid_stable_key")
    return selected


def _validate_authority_source(
    authority: SpatialAuthority,
    source_type: SourceType,
    environment: SourceEnvironment,
) -> None:
    nonproduction = source_type in {SourceType.DEMO, SourceType.TEST}
    if nonproduction and (
        authority is not SpatialAuthority.SYNTHETIC
        or environment is SourceEnvironment.PRODUCTION
    ):
        raise SpatialContractError("synthetic_production_authority_forbidden")
    if environment is SourceEnvironment.PRODUCTION and nonproduction:
        raise SpatialContractError("nonproduction_source_forbidden")
    expected_types = {
        SpatialAuthority.OFFICIAL: {SourceType.OFFICIAL},
        SpatialAuthority.USER_SUPPLIED: {SourceType.USER},
        SpatialAuthority.SYNTHETIC: {SourceType.DEMO, SourceType.TEST},
        SpatialAuthority.DERIVED: {SourceType.DETERMINISTIC},
        SpatialAuthority.UNKNOWN: {
            SourceType.OFFICIAL,
            SourceType.PARTNER,
            SourceType.DOCUMENT,
        },
    }
    if source_type not in expected_types[authority]:
        raise SpatialContractError("source_authority_mismatch")


def _crs(value: str) -> CRS:
    try:
        return CRS.from_user_input(value)
    except CRSError:
        raise SpatialContractError("unsupported_crs") from None


@dataclass(frozen=True)
class CRSDefinition:
    identifier: str
    coordinate_order: CoordinateOrder

    def __post_init__(self) -> None:
        selected = _crs(self.identifier)
        epsg = selected.to_epsg()
        identifier = f"EPSG:{epsg}" if epsg is not None else selected.to_string()
        if len(identifier) > 160:
            raise SpatialContractError("unsupported_crs")
        if identifier == INTERCHANGE_CRS_ID:
            if self.coordinate_order is not CoordinateOrder.LONGITUDE_LATITUDE:
                raise SpatialContractError("invalid_coordinate_order")
        elif (
            selected.is_projected
            and self.coordinate_order is not CoordinateOrder.EASTING_NORTHING
        ):
            raise SpatialContractError("invalid_coordinate_order")
        object.__setattr__(self, "identifier", identifier)

    @property
    def is_projected(self) -> bool:
        return _crs(self.identifier).is_projected

    @property
    def linear_unit_name(self) -> str | None:
        selected = _crs(self.identifier)
        if not selected.axis_info:
            return None
        return selected.axis_info[0].unit_name


API_INTERCHANGE_CRS = CRSDefinition(
    INTERCHANGE_CRS_ID,
    CoordinateOrder.LONGITUDE_LATITUDE,
)


def projected_crs(identifier: str) -> CRSDefinition:
    """Create an explicit projected CRS; no Taiwan zone is selected implicitly."""

    if not _crs(identifier).is_projected:
        raise SpatialContractError("projected_crs_required")
    selected = CRSDefinition(identifier, CoordinateOrder.EASTING_NORTHING)
    return selected


@dataclass(frozen=True)
class SpatialCoverage:
    status: SpatialCoverageStatus
    geography: Mapping[str, object]
    temporal: Mapping[str, object]
    subject_scope: str
    fields: tuple[str, ...]
    gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "geography", _json_object(self.geography))
        object.__setattr__(self, "temporal", _json_object(self.temporal))
        object.__setattr__(
            self, "subject_scope", _bounded(self.subject_scope, maximum=80)
        )
        if not self.fields or any(
            not _STABLE_KEY.fullmatch(item) for item in self.fields
        ):
            raise SpatialContractError("invalid_coverage_fields")
        if any(not _SAFE_ERROR_CODE.fullmatch(item) for item in self.gaps):
            raise SpatialContractError("invalid_coverage_gap")

    @property
    def proves_absence(self) -> bool:
        return self.status is SpatialCoverageStatus.COMPLETE and not self.gaps

    def as_evidence_mapping(self) -> Mapping[str, object]:
        return _json_object(
            {
                "geography": dict(self.geography),
                "time": dict(self.temporal),
                "subject_scope": self.subject_scope,
                "fields": list(self.fields),
                "gaps": list(self.gaps),
                "status": self.status.value,
            }
        )


@dataclass(frozen=True)
class SpatialLicense:
    status: LicenseStatus
    license_id: str
    attribution: str
    commercial_use: str
    redistribution: str
    terms_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "license_id", _bounded(self.license_id, maximum=120))
        object.__setattr__(self, "attribution", _bounded(self.attribution, maximum=500))
        object.__setattr__(
            self, "commercial_use", _bounded(self.commercial_use, maximum=120)
        )
        object.__setattr__(
            self, "redistribution", _bounded(self.redistribution, maximum=120)
        )
        if self.terms_ref is not None:
            object.__setattr__(self, "terms_ref", _bounded(self.terms_ref, maximum=500))

    def as_evidence_mapping(self) -> Mapping[str, object]:
        return _json_object(
            {
                "license_id": self.license_id,
                "attribution": self.attribution,
                "commercial_use": self.commercial_use,
                "redistribution": self.redistribution,
                "terms_ref": self.terms_ref,
            }
        )


@dataclass(frozen=True)
class TransformationStep:
    operation: str
    library: str
    library_version: str
    source_crs: str
    target_crs: str
    coordinate_order: CoordinateOrder

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", _stable_key(self.operation))
        object.__setattr__(self, "library", _bounded(self.library, maximum=80))
        object.__setattr__(
            self, "library_version", _bounded(self.library_version, maximum=40)
        )
        _crs(self.source_crs)
        _crs(self.target_crs)

    def as_mapping(self) -> Mapping[str, object]:
        return _json_object(
            {
                "operation": self.operation,
                "library": self.library,
                "library_version": self.library_version,
                "source_crs": self.source_crs,
                "target_crs": self.target_crs,
                "coordinate_order": self.coordinate_order.value,
            }
        )


@dataclass(frozen=True)
class SpatialProvenance:
    source_id: str
    source_type: SourceType
    authority: SpatialAuthority
    environment: SourceEnvironment
    provider_id: str
    provider_version: str
    retrieved_at: datetime
    evidence_id: UUID
    source_record_id: str | None = None
    source_ref: str | None = None
    effective_at: datetime | None = None
    processing_lineage: tuple[TransformationStep, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _stable_key(self.source_id))
        object.__setattr__(self, "provider_id", _stable_key(self.provider_id))
        object.__setattr__(
            self, "provider_version", _bounded(self.provider_version, maximum=80)
        )
        _aware(self.retrieved_at, required=True)
        _aware(self.effective_at)
        if self.source_record_id is not None:
            object.__setattr__(
                self, "source_record_id", _bounded(self.source_record_id, maximum=240)
            )
        if self.source_ref is not None:
            object.__setattr__(
                self, "source_ref", _bounded(self.source_ref, maximum=500)
            )
        _validate_authority_source(
            self.authority,
            self.source_type,
            self.environment,
        )

    def lineage_mapping(self) -> Mapping[str, object]:
        return _json_object(
            {
                "source_record_id": self.source_record_id,
                "source_ref": self.source_ref,
                "processing_lineage": [
                    dict(item.as_mapping()) for item in self.processing_lineage
                ],
            }
        )


def _coordinate_count(geometry: BaseGeometry) -> int:
    if geometry.geom_type == "Point":
        return 1
    if geometry.geom_type == "LineString":
        return len(geometry.coords)
    if geometry.geom_type == "Polygon":
        return len(geometry.exterior.coords) + sum(
            len(ring.coords) for ring in geometry.interiors
        )
    if geometry.geom_type == "MultiPolygon":
        return sum(_coordinate_count(item) for item in geometry.geoms)
    return MAX_GEOMETRY_COORDINATES + 1


def _validated_geometry(
    value: Mapping[str, object],
    crs: CRSDefinition,
    *,
    allowed_types: frozenset[GeometryType] | None = None,
) -> BaseGeometry:
    try:
        geometry = shape(dict(value))
    except (AttributeError, KeyError, TypeError, ValueError):
        raise SpatialContractError("malformed_geometry") from None
    if geometry.is_empty:
        raise SpatialContractError("empty_geometry")
    try:
        geometry_type = GeometryType(geometry.geom_type)
    except ValueError:
        raise SpatialContractError("unsupported_geometry_type") from None
    if allowed_types is not None and geometry_type not in allowed_types:
        raise SpatialContractError("unexpected_geometry_type")
    if not geometry.is_valid:
        raise SpatialContractError("invalid_geometry")
    if _coordinate_count(geometry) > MAX_GEOMETRY_COORDINATES:
        raise SpatialContractError("geometry_too_complex")
    bounds = geometry.bounds
    if len(bounds) != 4 or not all(math.isfinite(item) for item in bounds):
        raise SpatialContractError("non_finite_geometry")
    if crs.identifier == INTERCHANGE_CRS_ID:
        west, south, east, north = bounds
        if west < -180 or east > 180 or south < -90 or north > 90:
            raise SpatialContractError("coordinate_order_or_bounds_invalid")
    return geometry


@dataclass(frozen=True)
class SpatialOperand:
    feature_id: str
    geometry: Mapping[str, object]
    crs: CRSDefinition

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_id", _bounded(self.feature_id, maximum=160))
        _validated_geometry(self.geometry, self.crs)
        object.__setattr__(self, "geometry", _json_object(self.geometry))


@dataclass(frozen=True)
class TransformedGeometry:
    source_geometry: Mapping[str, object]
    transformed_geometry: Mapping[str, object]
    source_crs: CRSDefinition
    target_crs: CRSDefinition
    lineage: TransformationStep


def transform_geometry(
    operand: SpatialOperand,
    target_crs: CRSDefinition,
) -> TransformedGeometry:
    """Transform with pyproj while retaining source geometry and CRS verbatim."""

    source = _validated_geometry(operand.geometry, operand.crs)
    if operand.crs.identifier == target_crs.identifier:
        transformed = source
        operation = "crs_identity"
    else:
        transformer = Transformer.from_crs(
            _crs(operand.crs.identifier),
            _crs(target_crs.identifier),
            always_xy=True,
        )
        try:
            transformed = shapely_transform(transformer.transform, source)
        except Exception:
            raise SpatialContractError("crs_transformation_failed") from None
        operation = "crs_transform"
    transformed_mapping = mapping(transformed)
    _validated_geometry(transformed_mapping, target_crs)
    return TransformedGeometry(
        source_geometry=_json_object(operand.geometry),
        transformed_geometry=_json_object(transformed_mapping),
        source_crs=operand.crs,
        target_crs=target_crs,
        lineage=TransformationStep(
            operation=operation,
            library="pyproj",
            library_version=pyproj.__version__,
            source_crs=operand.crs.identifier,
            target_crs=target_crs.identifier,
            coordinate_order=operand.crs.coordinate_order,
        ),
    )


@dataclass(frozen=True)
class SpatialPrecision:
    value: float | None
    unit: str
    method: str

    def __post_init__(self) -> None:
        if self.value is not None and (not math.isfinite(self.value) or self.value < 0):
            raise SpatialContractError("invalid_precision")
        object.__setattr__(self, "unit", _stable_key(self.unit))
        object.__setattr__(self, "method", _stable_key(self.method))


@dataclass(frozen=True)
class ParcelGeometry:
    geometry_id: UUID
    parcel_identity_reference_id: UUID
    geometry_type: GeometryType
    source_geometry: Mapping[str, object]
    geometry: Mapping[str, object]
    source_crs: CRSDefinition
    normalized_crs: CRSDefinition
    precision: SpatialPrecision
    tolerance: float
    tolerance_unit: str
    geometry_source: str
    retrieved_at: datetime
    effective_at: datetime | None
    valid_from: datetime | None
    valid_to: datetime | None
    coverage: SpatialCoverage
    provenance: SpatialProvenance
    evidence_id: UUID
    version: int
    supersedes_geometry_id: UUID | None = None

    def __post_init__(self) -> None:
        polygon_types = frozenset({GeometryType.POLYGON, GeometryType.MULTI_POLYGON})
        source = _validated_geometry(
            self.source_geometry, self.source_crs, allowed_types=polygon_types
        )
        normalized = _validated_geometry(
            self.geometry, self.normalized_crs, allowed_types=polygon_types
        )
        if (
            self.geometry_type.value != normalized.geom_type
            or source.geom_type != normalized.geom_type
        ):
            raise SpatialContractError("geometry_type_mismatch")
        if self.normalized_crs.identifier != INTERCHANGE_CRS_ID:
            raise SpatialContractError("interchange_crs_required")
        if self.retrieved_at != self.provenance.retrieved_at:
            raise SpatialContractError("retrieval_provenance_mismatch")
        if self.effective_at != self.provenance.effective_at:
            raise SpatialContractError("effective_provenance_mismatch")
        if self.source_crs.identifier != self.normalized_crs.identifier:
            if not self.provenance.processing_lineage:
                raise SpatialContractError("transformation_lineage_required")
            final_step = self.provenance.processing_lineage[-1]
            if (
                final_step.source_crs != self.source_crs.identifier
                or final_step.target_crs != self.normalized_crs.identifier
            ):
                raise SpatialContractError("transformation_lineage_mismatch")
        if self.version < 1:
            raise SpatialContractError("invalid_geometry_version")
        if self.supersedes_geometry_id == self.geometry_id:
            raise SpatialContractError("invalid_geometry_supersession")
        if self.version == 1 and self.supersedes_geometry_id is not None:
            raise SpatialContractError("invalid_geometry_supersession")
        if self.version > 1 and self.supersedes_geometry_id is None:
            raise SpatialContractError("geometry_supersession_required")
        if not math.isfinite(self.tolerance) or self.tolerance < 0:
            raise SpatialContractError("invalid_tolerance")
        object.__setattr__(self, "tolerance_unit", _stable_key(self.tolerance_unit))
        object.__setattr__(self, "geometry_source", _stable_key(self.geometry_source))
        _aware(self.retrieved_at, required=True)
        _aware(self.effective_at)
        _aware(self.valid_from)
        _aware(self.valid_to)
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to <= self.valid_from
        ):
            raise SpatialContractError("invalid_validity_interval")
        if self.provenance.evidence_id != self.evidence_id:
            raise SpatialContractError("evidence_provenance_mismatch")
        object.__setattr__(self, "source_geometry", _json_object(self.source_geometry))
        object.__setattr__(self, "geometry", _json_object(self.geometry))


def parcel_geometry_from_source(
    *,
    geometry_id: UUID,
    parcel_identity_reference_id: UUID,
    source_operand: SpatialOperand,
    precision: SpatialPrecision,
    tolerance: float,
    tolerance_unit: str,
    geometry_source: str,
    coverage: SpatialCoverage,
    provenance: SpatialProvenance,
    version: int = 1,
    supersedes_geometry_id: UUID | None = None,
    effective_at: datetime | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> ParcelGeometry:
    transformed = transform_geometry(source_operand, API_INTERCHANGE_CRS)
    geometry_type = GeometryType(
        shape(dict(transformed.transformed_geometry)).geom_type
    )
    lineage = provenance.processing_lineage + (transformed.lineage,)
    enriched_provenance = SpatialProvenance(
        source_id=provenance.source_id,
        source_type=provenance.source_type,
        authority=provenance.authority,
        environment=provenance.environment,
        provider_id=provenance.provider_id,
        provider_version=provenance.provider_version,
        retrieved_at=provenance.retrieved_at,
        evidence_id=provenance.evidence_id,
        source_record_id=provenance.source_record_id,
        source_ref=provenance.source_ref,
        effective_at=provenance.effective_at,
        processing_lineage=lineage,
    )
    return ParcelGeometry(
        geometry_id=geometry_id,
        parcel_identity_reference_id=parcel_identity_reference_id,
        geometry_type=geometry_type,
        source_geometry=transformed.source_geometry,
        geometry=transformed.transformed_geometry,
        source_crs=source_operand.crs,
        normalized_crs=API_INTERCHANGE_CRS,
        precision=precision,
        tolerance=tolerance,
        tolerance_unit=tolerance_unit,
        geometry_source=geometry_source,
        retrieved_at=provenance.retrieved_at,
        effective_at=effective_at,
        valid_from=valid_from,
        valid_to=valid_to,
        coverage=coverage,
        provenance=enriched_provenance,
        evidence_id=provenance.evidence_id,
        version=version,
        supersedes_geometry_id=supersedes_geometry_id,
    )


@dataclass(frozen=True)
class SpatialLayer:
    layer_id: UUID
    layer_key: str
    title: str
    category: str
    provider_id: str
    provider_version: str
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    authority: SpatialAuthority
    geometry_types: frozenset[GeometryType]
    source_crs: tuple[CRSDefinition, ...]
    supported_crs: tuple[CRSDefinition, ...]
    coverage: SpatialCoverage
    temporal_semantics: TemporalSemantics
    refresh_semantics: RefreshSemantics
    license: SpatialLicense
    attribution: str
    evidence_requirements: tuple[str, ...]
    provenance_requirements: tuple[str, ...]
    availability: SpatialAvailability
    limitations: tuple[str, ...]
    layer_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "layer_key", _stable_key(self.layer_key))
        object.__setattr__(self, "title", _bounded(self.title, maximum=160))
        object.__setattr__(self, "category", _stable_key(self.category))
        object.__setattr__(self, "provider_id", _stable_key(self.provider_id))
        object.__setattr__(
            self, "provider_version", _bounded(self.provider_version, maximum=80)
        )
        object.__setattr__(self, "source_id", _stable_key(self.source_id))
        object.__setattr__(self, "attribution", _bounded(self.attribution, maximum=500))
        if not self.geometry_types or not self.source_crs or not self.supported_crs:
            raise SpatialContractError("incomplete_layer_geometry_contract")
        if INTERCHANGE_CRS_ID not in {item.identifier for item in self.supported_crs}:
            raise SpatialContractError("layer_interchange_crs_required")
        if not self.evidence_requirements or not self.provenance_requirements:
            raise SpatialContractError("incomplete_layer_evidence_contract")
        if self.layer_version < 1:
            raise SpatialContractError("invalid_layer_version")
        _validate_authority_source(
            self.authority,
            self.source_type,
            self.source_environment,
        )
        if self.attribution != self.license.attribution:
            raise SpatialContractError("layer_attribution_mismatch")
        if (
            self.authority is SpatialAuthority.SYNTHETIC
            and self.availability is SpatialAvailability.AVAILABLE
        ):
            raise SpatialContractError("synthetic_layer_cannot_be_authoritative")
        if not self.limitations:
            raise SpatialContractError("layer_limitations_required")


class SpatialLayerRegistry:
    def __init__(self, layers: Sequence[SpatialLayer] = ()) -> None:
        self._layers: dict[tuple[str, int], SpatialLayer] = {}
        for layer in layers:
            self.register(layer)

    def register(self, layer: SpatialLayer) -> None:
        key = (layer.layer_key, layer.layer_version)
        if key in self._layers:
            raise SpatialContractError("duplicate_layer_version")
        if any(
            existing.layer_id == layer.layer_id for existing in self._layers.values()
        ):
            raise SpatialContractError("duplicate_layer_id")
        self._layers[key] = layer

    def get(self, layer_key: str, layer_version: int | None = None) -> SpatialLayer:
        selected_key = _stable_key(layer_key)
        try:
            if layer_version is not None:
                return self._layers[(selected_key, layer_version)]
            versions = [
                item
                for (key, _version), item in self._layers.items()
                if key == selected_key
            ]
            return max(versions, key=lambda item: item.layer_version)
        except (KeyError, ValueError):
            raise SpatialContractError("unknown_layer") from None

    def all(self) -> tuple[SpatialLayer, ...]:
        return tuple(self._layers[key] for key in sorted(self._layers))


@dataclass(frozen=True)
class ProviderError:
    code: str
    retryable: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _stable_key(self.code))


T = TypeVar("T")


@dataclass(frozen=True)
class SpatialProviderResult(Generic[T]):
    status: ProviderResultStatus
    data: T | None
    coverage: SpatialCoverage
    license: SpatialLicense
    provenance: SpatialProvenance
    errors: tuple[ProviderError, ...] = ()

    def __post_init__(self) -> None:
        data_statuses = {
            ProviderResultStatus.PRESENT,
            ProviderResultStatus.LIMITED,
            ProviderResultStatus.STALE,
        }
        if self.status in data_statuses and self.data is None:
            raise SpatialContractError("provider_data_required")
        if self.status not in data_statuses and self.data is not None:
            raise SpatialContractError("provider_failure_data_forbidden")
        if (
            self.status is ProviderResultStatus.ABSENT
            and not self.coverage.proves_absence
        ):
            raise SpatialContractError("absence_requires_complete_coverage")
        if (
            self.status is ProviderResultStatus.LIMITED
            and self.coverage.status is not SpatialCoverageStatus.PARTIAL
        ):
            raise SpatialContractError("limited_requires_partial_coverage")
        if self.status is ProviderResultStatus.PROVIDER_ERROR and not self.errors:
            raise SpatialContractError("provider_error_code_required")
        if self.status is not ProviderResultStatus.PROVIDER_ERROR and self.errors:
            raise SpatialContractError("unexpected_provider_error")


@dataclass(frozen=True)
class SpatialProviderRequest:
    workspace_id: UUID
    subject_type: str
    subject_id: UUID
    purpose: str
    as_of: datetime | None = None
    query_geometry: SpatialOperand | None = None
    layer_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_type", _stable_key(self.subject_type))
        object.__setattr__(self, "purpose", _stable_key(self.purpose))
        _aware(self.as_of)
        if self.layer_key is not None:
            object.__setattr__(self, "layer_key", _stable_key(self.layer_key))


class ParcelProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def resolve_parcel(
        self,
        request: SpatialProviderRequest,
    ) -> SpatialProviderResult[ParcelGeometry]: ...


class GeometryProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def resolve_geometry(
        self,
        request: SpatialProviderRequest,
    ) -> SpatialProviderResult[SpatialOperand]: ...


class SpatialLayerProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def observe_layer(
        self,
        request: SpatialProviderRequest,
    ) -> SpatialProviderResult[Mapping[str, object]]: ...


_OBSERVATION_EVIDENCE_STATUS = {
    SpatialObservationStatus.PRESENT: EvidenceStatus.AVAILABLE,
    SpatialObservationStatus.ABSENT: EvidenceStatus.AVAILABLE,
    SpatialObservationStatus.NO_MATCH: EvidenceStatus.UNKNOWN,
    SpatialObservationStatus.UNAVAILABLE: EvidenceStatus.UNAVAILABLE,
    SpatialObservationStatus.UNKNOWN: EvidenceStatus.UNKNOWN,
    SpatialObservationStatus.PARTIAL_COVERAGE: EvidenceStatus.LIMITED,
    SpatialObservationStatus.PROVIDER_ERROR: EvidenceStatus.UNAVAILABLE,
    SpatialObservationStatus.STALE: EvidenceStatus.STALE,
    SpatialObservationStatus.NOT_ASSESSED: EvidenceStatus.UNKNOWN,
}


@dataclass(frozen=True)
class SpatialObservation:
    observation_id: UUID
    workspace_id: UUID
    subject_type: str
    subject_id: UUID
    layer_id: UUID
    status: SpatialObservationStatus
    value: Mapping[str, object] | None
    coverage: SpatialCoverage
    license: SpatialLicense
    provenance: SpatialProvenance
    evidence_id: UUID
    limitations: tuple[str, ...]
    confidence: float | None = None
    confidence_method: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_type", _stable_key(self.subject_type))
        if self.value is not None:
            object.__setattr__(self, "value", _json_object(self.value))
        if self.status in {
            SpatialObservationStatus.PRESENT,
            SpatialObservationStatus.PARTIAL_COVERAGE,
            SpatialObservationStatus.STALE,
        }:
            if self.value is None:
                raise SpatialContractError("observation_value_required")
        elif self.value is not None:
            raise SpatialContractError("observation_value_forbidden")
        if (
            self.status is SpatialObservationStatus.ABSENT
            and not self.coverage.proves_absence
        ):
            raise SpatialContractError("absence_requires_complete_coverage")
        if self.status is SpatialObservationStatus.PARTIAL_COVERAGE:
            if self.coverage.status is not SpatialCoverageStatus.PARTIAL:
                raise SpatialContractError(
                    "partial_observation_requires_partial_coverage"
                )
        if self.provenance.evidence_id != self.evidence_id:
            raise SpatialContractError("evidence_provenance_mismatch")
        if not self.limitations and self.status is not SpatialObservationStatus.PRESENT:
            raise SpatialContractError("observation_limitation_required")
        if self.confidence is None:
            if self.confidence_method is not None:
                raise SpatialContractError("confidence_method_without_value")
        elif (
            not math.isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
            or self.confidence_method is None
        ):
            raise SpatialContractError("invalid_confidence")
        if self.confidence_method is not None:
            object.__setattr__(
                self,
                "confidence_method",
                _bounded(self.confidence_method, maximum=120),
            )

    @property
    def evidence_status(self) -> EvidenceStatus:
        return _OBSERVATION_EVIDENCE_STATUS[self.status]

    @property
    def supports_safe_conclusion(self) -> bool:
        return False


def normalize_provider_observation(
    *,
    observation_id: UUID,
    request: SpatialProviderRequest,
    layer: SpatialLayer,
    result: SpatialProviderResult[Mapping[str, object]],
    limitations: tuple[str, ...] = (),
) -> SpatialObservation:
    if request.layer_key is not None and request.layer_key != layer.layer_key:
        raise SpatialContractError("provider_layer_mismatch")
    if (
        result.provenance.provider_id != layer.provider_id
        or result.provenance.source_id != layer.source_id
        or result.provenance.authority is not layer.authority
    ):
        raise SpatialContractError("provider_source_mismatch")
    status_mapping = {
        ProviderResultStatus.PRESENT: SpatialObservationStatus.PRESENT,
        ProviderResultStatus.ABSENT: SpatialObservationStatus.ABSENT,
        ProviderResultStatus.NO_MATCH: SpatialObservationStatus.NO_MATCH,
        ProviderResultStatus.LIMITED: SpatialObservationStatus.PARTIAL_COVERAGE,
        ProviderResultStatus.UNAVAILABLE: SpatialObservationStatus.UNAVAILABLE,
        ProviderResultStatus.UNKNOWN: SpatialObservationStatus.UNKNOWN,
        ProviderResultStatus.PROVIDER_ERROR: SpatialObservationStatus.PROVIDER_ERROR,
        ProviderResultStatus.STALE: SpatialObservationStatus.STALE,
        ProviderResultStatus.NOT_ASSESSED: SpatialObservationStatus.NOT_ASSESSED,
    }
    selected_status = status_mapping[result.status]
    selected_limitations = limitations or layer.limitations
    return SpatialObservation(
        observation_id=observation_id,
        workspace_id=request.workspace_id,
        subject_type=request.subject_type,
        subject_id=request.subject_id,
        layer_id=layer.layer_id,
        status=selected_status,
        value=result.data,
        coverage=result.coverage,
        license=result.license,
        provenance=result.provenance,
        evidence_id=result.provenance.evidence_id,
        limitations=selected_limitations,
    )


def _evidence_coverage_status(status: SpatialCoverageStatus) -> CoverageStatus:
    return {
        SpatialCoverageStatus.COMPLETE: CoverageStatus.KNOWN,
        SpatialCoverageStatus.PARTIAL: CoverageStatus.PARTIAL,
        SpatialCoverageStatus.UNKNOWN: CoverageStatus.UNKNOWN,
        SpatialCoverageStatus.UNAVAILABLE: CoverageStatus.UNAVAILABLE,
    }[status]


def parcel_geometry_evidence_draft(
    geometry: ParcelGeometry,
    license_metadata: SpatialLicense,
) -> EvidenceDraft:
    """Represent a durable parcel geometry through the Stage 1 Evidence store."""

    evidence_status = {
        SpatialAuthority.OFFICIAL: EvidenceStatus.AVAILABLE,
        SpatialAuthority.DERIVED: EvidenceStatus.LIMITED,
        SpatialAuthority.USER_SUPPLIED: EvidenceStatus.USER_PROVIDED,
        SpatialAuthority.SYNTHETIC: EvidenceStatus.UNVERIFIED,
        SpatialAuthority.UNKNOWN: EvidenceStatus.UNVERIFIED,
    }[geometry.provenance.authority]
    quality_status = {
        EvidenceStatus.AVAILABLE: QualityStatus.PASSED,
        EvidenceStatus.LIMITED: QualityStatus.LIMITED,
    }.get(evidence_status, QualityStatus.NOT_CHECKED)
    return EvidenceDraft(
        fact_type="spatial.parcel_geometry.v1",
        source_id=geometry.provenance.source_id,
        source_environment=geometry.provenance.environment,
        retrieved_at=geometry.retrieved_at,
        effective_from=geometry.effective_at,
        effective_to=geometry.valid_to,
        coverage_status=_evidence_coverage_status(geometry.coverage.status),
        coverage=geometry.coverage.as_evidence_mapping(),
        evidence_status=evidence_status,
        quality_status=quality_status,
        quality={
            "authority": geometry.provenance.authority.value,
            "geometry_type": geometry.geometry_type.value,
            "source_crs": geometry.source_crs.identifier,
            "normalized_crs": geometry.normalized_crs.identifier,
            "precision": {
                "value": geometry.precision.value,
                "unit": geometry.precision.unit,
                "method": geometry.precision.method,
            },
        },
        license_status=license_metadata.status,
        license=license_metadata.as_evidence_mapping(),
        value_ref=f"parcel-geometry:{geometry.geometry_id}",
        value_schema="spatial-parcel-geometry-v1",
        provider=geometry.provenance.provider_id,
        source_record_id=geometry.provenance.source_record_id,
        lineage=geometry.provenance.lineage_mapping(),
    )


def observation_evidence_draft(observation: SpatialObservation) -> EvidenceDraft:
    """Adapt spatial output into the existing Stage 1 Evidence contract."""

    value: Mapping[str, object] | None
    if observation.status is SpatialObservationStatus.ABSENT:
        value = _json_object({"observation_status": observation.status.value})
    elif observation.value is None:
        value = None
    else:
        value = _json_object(
            {
                "observation_status": observation.status.value,
                "result": dict(observation.value),
            }
        )
    quality_status = {
        EvidenceStatus.AVAILABLE: QualityStatus.PASSED,
        EvidenceStatus.LIMITED: QualityStatus.LIMITED,
        EvidenceStatus.STALE: QualityStatus.LIMITED,
    }.get(observation.evidence_status, QualityStatus.NOT_CHECKED)
    return EvidenceDraft(
        fact_type="spatial.layer_observation.v1",
        source_id=observation.provenance.source_id,
        source_environment=observation.provenance.environment,
        retrieved_at=observation.provenance.retrieved_at,
        effective_from=observation.provenance.effective_at,
        coverage_status=_evidence_coverage_status(observation.coverage.status),
        coverage=observation.coverage.as_evidence_mapping(),
        evidence_status=observation.evidence_status,
        quality_status=quality_status,
        quality={
            "authority": observation.provenance.authority.value,
            "limitations": list(observation.limitations),
            "validation_status": quality_status.value,
        },
        license_status=observation.license.status,
        license=observation.license.as_evidence_mapping(),
        value=value,
        value_schema="spatial-layer-observation-v1",
        provider=observation.provenance.provider_id,
        source_record_id=observation.provenance.source_record_id,
        lineage=observation.provenance.lineage_mapping(),
    )


@dataclass(frozen=True)
class SpatialOperationRequest:
    operation: SpatialOperation
    left: SpatialOperand
    processing_crs: CRSDefinition
    units: OperationUnit
    tolerance: float = 0.0
    tolerance_unit: OperationUnit | None = None
    right: SpatialOperand | None = None
    candidates: tuple[SpatialOperand, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.tolerance) or self.tolerance < 0:
            raise SpatialContractError("invalid_tolerance")
        if self.tolerance == 0 and self.tolerance_unit is not None:
            raise SpatialContractError("unexpected_tolerance_unit")
        if self.tolerance > 0:
            if (
                self.tolerance_unit is not OperationUnit.METERS
                or not self.processing_crs.is_projected
            ):
                raise SpatialContractError("projected_meter_tolerance_required")
            tolerance_crs_unit = (self.processing_crs.linear_unit_name or "").lower()
            if "metre" not in tolerance_crs_unit and "meter" not in tolerance_crs_unit:
                raise SpatialContractError("projected_meter_tolerance_required")
        binary = {
            SpatialOperation.POINT_IN_POLYGON,
            SpatialOperation.INTERSECTS,
            SpatialOperation.CONTAINS,
            SpatialOperation.DISTANCE,
        }
        if self.operation in binary and self.right is None:
            raise SpatialContractError("right_operand_required")
        if self.operation is SpatialOperation.NEAREST and not self.candidates:
            raise SpatialContractError("nearest_candidates_required")
        if self.operation is SpatialOperation.BOUNDING_BOX:
            if self.right is not None or not self.candidates:
                raise SpatialContractError("bounding_box_candidates_required")
        if self.operation in {SpatialOperation.DISTANCE, SpatialOperation.NEAREST}:
            if (
                not self.processing_crs.is_projected
                or self.units is not OperationUnit.METERS
            ):
                raise SpatialContractError("projected_meter_crs_required")
            unit_name = (self.processing_crs.linear_unit_name or "").lower()
            if "metre" not in unit_name and "meter" not in unit_name:
                raise SpatialContractError("projected_meter_crs_required")
        elif (
            self.operation
            in {
                SpatialOperation.POINT_IN_POLYGON,
                SpatialOperation.INTERSECTS,
                SpatialOperation.CONTAINS,
            }
            and self.units is not OperationUnit.BOOLEAN
        ):
            raise SpatialContractError("boolean_units_required")
        elif self.operation is SpatialOperation.BOUNDING_BOX:
            if self.units is not OperationUnit.CRS_UNITS or self.tolerance != 0:
                raise SpatialContractError("bounding_box_contract_invalid")


@dataclass(frozen=True)
class SpatialOperationProvenance:
    engine: str
    engine_version: str
    input_feature_ids: tuple[str, ...]
    transformations: tuple[TransformationStep, ...]


@dataclass(frozen=True)
class SpatialOperationResult:
    operation: SpatialOperation
    result: Mapping[str, object]
    input_crs: tuple[str, ...]
    processing_crs: str
    units: OperationUnit
    tolerance: float
    tolerance_unit: OperationUnit | None
    provenance: SpatialOperationProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "result", _json_object(self.result))


def _processed(
    operand: SpatialOperand,
    processing_crs: CRSDefinition,
) -> tuple[BaseGeometry, TransformationStep]:
    transformed = transform_geometry(operand, processing_crs)
    return (
        _validated_geometry(transformed.transformed_geometry, processing_crs),
        transformed.lineage,
    )


def execute_spatial_operation(
    request: SpatialOperationRequest,
) -> SpatialOperationResult:
    """Execute deterministic bounded predicates without making identity claims."""

    left, left_lineage = _processed(request.left, request.processing_crs)
    transformations = [left_lineage]
    input_crs = [request.left.crs.identifier]
    input_feature_ids = [request.left.feature_id]
    right: BaseGeometry | None = None
    if request.right is not None:
        right, right_lineage = _processed(request.right, request.processing_crs)
        transformations.append(right_lineage)
        input_crs.append(request.right.crs.identifier)
        input_feature_ids.append(request.right.feature_id)

    if request.operation is SpatialOperation.POINT_IN_POLYGON:
        assert right is not None
        if left.geom_type != "Point" or right.geom_type not in {
            "Polygon",
            "MultiPolygon",
        }:
            raise SpatialContractError("point_polygon_operands_required")
        outcome = right.covers(left) or right.distance(left) <= request.tolerance
        result: Mapping[str, object] = {"matches": bool(outcome)}
    elif request.operation is SpatialOperation.INTERSECTS:
        assert right is not None
        result = {
            "matches": bool(
                left.intersects(right) or left.distance(right) <= request.tolerance
            )
        }
    elif request.operation is SpatialOperation.CONTAINS:
        assert right is not None
        outcome = left.covers(right)
        if not outcome and request.tolerance:
            outcome = left.buffer(request.tolerance).covers(right)
        result = {"matches": bool(outcome)}
    elif request.operation is SpatialOperation.DISTANCE:
        assert right is not None
        distance = float(left.distance(right))
        result = {
            "distance": distance,
            "within_tolerance": bool(distance <= request.tolerance),
        }
    elif request.operation is SpatialOperation.NEAREST:
        ranked: list[tuple[float, str]] = []
        for candidate in request.candidates:
            geometry, lineage = _processed(candidate, request.processing_crs)
            transformations.append(lineage)
            input_crs.append(candidate.crs.identifier)
            input_feature_ids.append(candidate.feature_id)
            ranked.append((float(left.distance(geometry)), candidate.feature_id))
        distance, feature_id = min(ranked, key=lambda item: (item[0], item[1]))
        result = {
            "feature_id": feature_id,
            "distance": distance,
            "within_tolerance": bool(distance <= request.tolerance),
        }
    elif request.operation is SpatialOperation.BOUNDING_BOX:
        matches: list[str] = []
        query_envelope = left.envelope
        for candidate in request.candidates:
            geometry, lineage = _processed(candidate, request.processing_crs)
            transformations.append(lineage)
            input_crs.append(candidate.crs.identifier)
            input_feature_ids.append(candidate.feature_id)
            if query_envelope.intersects(geometry.envelope):
                matches.append(candidate.feature_id)
        result = {
            "bounds": list(left.bounds),
            "feature_ids": sorted(matches),
        }
    else:  # pragma: no cover - enum exhaustiveness guard
        raise SpatialContractError("unsupported_spatial_operation")

    return SpatialOperationResult(
        operation=request.operation,
        result=result,
        input_crs=tuple(input_crs),
        processing_crs=request.processing_crs.identifier,
        units=request.units,
        tolerance=request.tolerance,
        tolerance_unit=request.tolerance_unit,
        provenance=SpatialOperationProvenance(
            engine="shapely",
            engine_version=shapely.__version__,
            input_feature_ids=tuple(input_feature_ids),
            transformations=tuple(transformations),
        ),
    )


def proposed_property_parcel_relation(
    *,
    property_node_id: UUID,
    parcel_node_id: UUID,
    evidence_id: UUID,
    source_id: str,
    source_environment: SourceEnvironment,
    confidence: float | None,
    confidence_method: str | None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> PropertyRelationDraft:
    """Create a reviewable graph proposal; confidence never confirms identity."""

    return PropertyRelationDraft(
        from_node_id=property_node_id,
        to_node_id=parcel_node_id,
        relation_type=PropertyRelationType.PROPERTY_PARCEL,
        direction=RelationDirection.DIRECTED,
        source_id=source_id,
        source_environment=source_environment,
        relation_status=PropertyRelationStatus.PROPOSED,
        confidence=confidence,
        confidence_method=confidence_method,
        evidence_id=evidence_id,
        valid_from=valid_from,
        valid_to=valid_to,
    )


@dataclass(frozen=True)
class MapViewport:
    center_longitude: float
    center_latitude: float
    zoom: float
    bounds: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        values = (self.center_longitude, self.center_latitude, self.zoom)
        if not all(math.isfinite(item) for item in values):
            raise SpatialContractError("invalid_viewport")
        if (
            not -180 <= self.center_longitude <= 180
            or not -90 <= self.center_latitude <= 90
        ):
            raise SpatialContractError("invalid_viewport")
        if not 0 <= self.zoom <= 24:
            raise SpatialContractError("invalid_viewport")
        if self.bounds is not None:
            west, south, east, north = self.bounds
            if not all(math.isfinite(item) for item in self.bounds):
                raise SpatialContractError("invalid_viewport")
            if west > east or south > north:
                raise SpatialContractError("invalid_viewport")


@dataclass(frozen=True)
class MapLegendItem:
    layer_key: str
    title: str
    authority: SpatialAuthority
    observation_status: SpatialObservationStatus
    attribution: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "layer_key", _stable_key(self.layer_key))
        object.__setattr__(self, "title", _bounded(self.title, maximum=160))
        object.__setattr__(self, "attribution", _bounded(self.attribution, maximum=500))


@dataclass(frozen=True)
class MapFeatureSelection:
    feature_id: str
    feature_type: str
    layer_key: str
    evidence_id: UUID | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_id", _bounded(self.feature_id, maximum=160))
        object.__setattr__(self, "feature_type", _stable_key(self.feature_type))
        object.__setattr__(self, "layer_key", _stable_key(self.layer_key))


@dataclass(frozen=True)
class MapWorkspaceContract:
    workspace_id: UUID
    case_id: UUID
    selected_property_entity_id: UUID | None
    candidate_parcel_geometry_ids: tuple[UUID, ...]
    confirmed_parcel_geometry_ids: tuple[UUID, ...]
    selected_layer_keys: tuple[str, ...]
    legend: tuple[MapLegendItem, ...]
    observation_ids: tuple[UUID, ...]
    viewport: MapViewport
    selected_feature: MapFeatureSelection | None
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        selected = tuple(_stable_key(item) for item in self.selected_layer_keys)
        if len(set(selected)) != len(selected):
            raise SpatialContractError("duplicate_selected_layer")
        legend_keys = {item.layer_key for item in self.legend}
        if len(legend_keys) != len(self.legend):
            raise SpatialContractError("duplicate_legend_layer")
        if set(selected) - legend_keys:
            raise SpatialContractError("selected_layer_missing_legend")
        if (
            self.selected_feature is not None
            and self.selected_feature.layer_key not in selected
        ):
            raise SpatialContractError("selected_feature_layer_inactive")
        if not self.limitations:
            raise SpatialContractError("map_limitations_required")
        candidate_ids = set(self.candidate_parcel_geometry_ids)
        confirmed_ids = set(self.confirmed_parcel_geometry_ids)
        if (
            len(candidate_ids) != len(self.candidate_parcel_geometry_ids)
            or len(confirmed_ids) != len(self.confirmed_parcel_geometry_ids)
            or candidate_ids & confirmed_ids
        ):
            raise SpatialContractError("invalid_parcel_geometry_selection")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise SpatialContractError("duplicate_observation")
        object.__setattr__(self, "selected_layer_keys", selected)
