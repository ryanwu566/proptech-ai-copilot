"""Tenant-safe append/read persistence for Stage 2A spatial evidence.

Provider acquisition stays outside this module. Persisting a geometry or an
observation does not create or confirm a PropertyEntity, relation, or Case
attachment.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping
from uuid import UUID

import shapely
from shapely.geometry import mapping, shape

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.persistence import CASE_WRITE_ROLES, _append_audit, _bounded_text
from services.vnext.property_graph import LicenseStatus, SourceEnvironment, SourceType
from services.vnext.spatial import (
    CRSDefinition,
    CoordinateOrder,
    GeometryType,
    ParcelGeometry,
    RefreshSemantics,
    SpatialAuthority,
    SpatialAvailability,
    SpatialCoverage,
    SpatialCoverageStatus,
    SpatialLayer,
    SpatialLicense,
    SpatialObservation,
    SpatialObservationStatus,
    SpatialPrecision,
    SpatialProvenance,
    TemporalSemantics,
    TransformationStep,
)


PARCEL_GEOMETRY_ROUTE = "/internal/vnext/spatial/parcel-geometries"
SPATIAL_OBSERVATION_ROUTE = "/internal/vnext/spatial/observations"
MAX_HISTORY_LIMIT = 200

_PARCEL_COLUMNS = (
    "parcel_geometry_id, workspace_id, parcel_identity_reference_id, "
    "geometry_version, supersedes_geometry_id, geometry_type, "
    "source_geometry_wkb, source_geometry_sha256, source_crs, "
    "source_coordinate_order, normalized_geometry, normalized_crs, "
    "normalized_coordinate_order, precision_value, precision_unit, "
    "precision_method, tolerance, tolerance_unit, geometry_source, source_id, "
    "source_type, source_environment, provider_id, provider_version, "
    "source_record_id, authority_class, retrieved_at, effective_at, valid_from, "
    "valid_to, coverage_status, coverage, processing_lineage, evidence_id, "
    "idempotency_record_id, created_by_user_id, created_at"
)

_LAYER_COLUMNS = (
    "spatial_layer_id, layer_key, layer_version, title, category, provider_id, "
    "provider_version, source_id, source_type, source_environment, "
    "authority_class, geometry_types, source_crs, supported_crs, "
    "coverage_semantics, temporal_semantics, refresh_semantics, license_status, "
    "license, attribution, evidence_requirements, provenance_requirements, "
    "limitations, availability, created_at"
)

_OBSERVATION_COLUMNS = (
    "spatial_observation_id, workspace_id, subject_type, subject_id, "
    "parcel_geometry_id, spatial_layer_id, observation_status, result, "
    "coverage_status, coverage, evidence_id, source_id, source_type, "
    "source_environment, provider_id, provider_version, source_record_id, "
    "authority_class, retrieved_at, effective_at, processing_lineage, "
    "license_status, license, confidence, confidence_method, limitations, "
    "idempotency_record_id, "
    "created_by_user_id, created_at"
)


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_value(item) for item in value]
    return value


def _encoded(value: object, *, maximum: int = 16_384) -> str:
    try:
        selected = json.dumps(
            _json_value(value),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError):
        raise VNextError.validation_failed() from None
    if len(selected.encode("utf-8")) > maximum:
        raise VNextError.validation_failed()
    return selected


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, Mapping):
        raise VNextError(ErrorCode.INTERNAL_ERROR)
    return value


def _sequence(value: object) -> list[object]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise VNextError(ErrorCode.INTERNAL_ERROR)
    return value


def _coverage(value: object, status: object) -> SpatialCoverage:
    selected = _mapping(value)
    return SpatialCoverage(
        status=SpatialCoverageStatus(str(status)),
        geography=_mapping(selected.get("geography")),
        temporal=_mapping(selected.get("time")),
        subject_scope=str(selected.get("subject_scope")),
        fields=tuple(str(item) for item in _sequence(selected.get("fields"))),
        gaps=tuple(str(item) for item in _sequence(selected.get("gaps"))),
    )


def _crs_payload(items: tuple[CRSDefinition, ...]) -> list[dict[str, str]]:
    return [
        {
            "identifier": item.identifier,
            "coordinate_order": item.coordinate_order.value,
        }
        for item in items
    ]


def _crs_items(value: object) -> tuple[CRSDefinition, ...]:
    return tuple(
        CRSDefinition(
            str(_mapping(item)["identifier"]),
            CoordinateOrder(str(_mapping(item)["coordinate_order"])),
        )
        for item in _sequence(value)
    )


def _lineage(value: object) -> tuple[TransformationStep, ...]:
    return tuple(
        TransformationStep(
            operation=str(_mapping(item)["operation"]),
            library=str(_mapping(item)["library"]),
            library_version=str(_mapping(item)["library_version"]),
            source_crs=str(_mapping(item)["source_crs"]),
            target_crs=str(_mapping(item)["target_crs"]),
            coordinate_order=CoordinateOrder(str(_mapping(item)["coordinate_order"])),
        )
        for item in _sequence(value)
    )


def _license(value: object, status: object) -> SpatialLicense:
    selected = _mapping(value)
    return SpatialLicense(
        status=LicenseStatus(str(status)),
        license_id=str(selected["license_id"]),
        attribution=str(selected["attribution"]),
        commercial_use=str(selected["commercial_use"]),
        redistribution=str(selected["redistribution"]),
        terms_ref=(
            None if selected.get("terms_ref") is None else str(selected["terms_ref"])
        ),
    )


def _provenance(
    *,
    source_id: object,
    source_type: object,
    source_environment: object,
    authority: object,
    provider_id: object,
    provider_version: object,
    retrieved_at: Any,
    effective_at: Any,
    evidence_id: object,
    source_record_id: object,
    processing_lineage: object,
) -> SpatialProvenance:
    return SpatialProvenance(
        source_id=str(source_id),
        source_type=SourceType(str(source_type)),
        environment=SourceEnvironment(str(source_environment)),
        authority=SpatialAuthority(str(authority)),
        provider_id=str(provider_id),
        provider_version=str(provider_version),
        retrieved_at=retrieved_at,
        effective_at=effective_at,
        evidence_id=UUID(str(evidence_id)),
        source_record_id=(None if source_record_id is None else str(source_record_id)),
        processing_lineage=_lineage(processing_lineage),
    )


def _parcel_record(row: tuple[Any, ...]) -> ParcelGeometry:
    source_geometry = mapping(shapely.from_wkb(bytes(row[6])))
    normalized_geometry = _mapping(row[10])
    provenance = _provenance(
        source_id=row[19],
        source_type=row[20],
        source_environment=row[21],
        provider_id=row[22],
        provider_version=row[23],
        source_record_id=row[24],
        authority=row[25],
        retrieved_at=row[26],
        effective_at=row[27],
        evidence_id=row[33],
        processing_lineage=row[32],
    )
    return ParcelGeometry(
        geometry_id=UUID(str(row[0])),
        parcel_identity_reference_id=UUID(str(row[2])),
        geometry_type=GeometryType(str(row[5])),
        source_geometry=source_geometry,
        geometry=normalized_geometry,
        source_crs=CRSDefinition(str(row[8]), CoordinateOrder(str(row[9]))),
        normalized_crs=CRSDefinition(str(row[11]), CoordinateOrder(str(row[12]))),
        precision=SpatialPrecision(
            None if row[13] is None else float(row[13]),
            str(row[14]),
            str(row[15]),
        ),
        tolerance=float(row[16]),
        tolerance_unit=str(row[17]),
        geometry_source=str(row[18]),
        retrieved_at=row[26],
        effective_at=row[27],
        valid_from=row[28],
        valid_to=row[29],
        coverage=_coverage(row[31], row[30]),
        provenance=provenance,
        evidence_id=UUID(str(row[33])),
        version=int(row[3]),
        supersedes_geometry_id=(None if row[4] is None else UUID(str(row[4]))),
    )


def _layer_record(row: tuple[Any, ...]) -> SpatialLayer:
    return SpatialLayer(
        layer_id=UUID(str(row[0])),
        layer_key=str(row[1]),
        layer_version=int(row[2]),
        title=str(row[3]),
        category=str(row[4]),
        provider_id=str(row[5]),
        provider_version=str(row[6]),
        source_id=str(row[7]),
        source_type=SourceType(str(row[8])),
        source_environment=SourceEnvironment(str(row[9])),
        authority=SpatialAuthority(str(row[10])),
        geometry_types=frozenset(GeometryType(str(item)) for item in row[11]),
        source_crs=_crs_items(row[12]),
        supported_crs=_crs_items(row[13]),
        coverage=_coverage(row[14], _mapping(row[14])["status"]),
        temporal_semantics=TemporalSemantics(str(row[15])),
        refresh_semantics=RefreshSemantics(str(row[16])),
        license=_license(row[18], row[17]),
        attribution=str(row[19]),
        evidence_requirements=tuple(str(item) for item in row[20]),
        provenance_requirements=tuple(str(item) for item in row[21]),
        limitations=tuple(str(item) for item in row[22]),
        availability=SpatialAvailability(str(row[23])),
    )


def _observation_record(
    row: tuple[Any, ...], layer: SpatialLayer
) -> SpatialObservation:
    provenance = _provenance(
        source_id=row[11],
        source_type=row[12],
        source_environment=row[13],
        provider_id=row[14],
        provider_version=row[15],
        source_record_id=row[16],
        authority=row[17],
        retrieved_at=row[18],
        effective_at=row[19],
        evidence_id=row[10],
        processing_lineage=row[20],
    )
    return SpatialObservation(
        observation_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        subject_type=str(row[2]),
        subject_id=UUID(str(row[3])),
        layer_id=layer.layer_id,
        status=SpatialObservationStatus(str(row[6])),
        value=None if row[7] is None else _mapping(row[7]),
        coverage=_coverage(row[9], row[8]),
        license=_license(row[22], row[21]),
        provenance=provenance,
        evidence_id=UUID(str(row[10])),
        limitations=tuple(str(item) for item in row[25]),
        confidence=None if row[23] is None else float(row[23]),
        confidence_method=None if row[24] is None else str(row[24]),
    )


def _translate_database_error(error: Exception) -> VNextError:
    sqlstate = str(getattr(error, "sqlstate", ""))
    if sqlstate in {"40001", "40P01", "23505"}:
        return VNextError.version_conflict()
    if sqlstate == "42501":
        return VNextError.permission_denied()
    if sqlstate == "23503":
        return VNextError.not_found()
    if sqlstate == "23514":
        return VNextError.validation_failed()
    return VNextError(ErrorCode.INTERNAL_ERROR)


class PostgresSpatialRepository:
    """Persist immutable spatial domain records under the VNext request role."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    @staticmethod
    def _idempotency_state(
        connection: Any,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        idempotency_record_id: UUID,
    ) -> tuple[str, str | None, UUID | None, str]:
        row = connection.execute(
            "SELECT operation_status, response_reference_type, "
            "response_reference_id, idempotency_key_hash "
            "FROM vnext_private.idempotency_records "
            "WHERE workspace_id = %s AND actor_user_id = %s "
            "AND idempotency_record_id = %s",
            (workspace_id, principal.user_id, idempotency_record_id),
        ).fetchone()
        if row is None:
            raise VNextError.idempotency_conflict()
        return (
            str(row[0]),
            None if row[1] is None else str(row[1]),
            None if row[2] is None else UUID(str(row[2])),
            str(row[3]),
        )

    @staticmethod
    def _complete_idempotency(
        connection: Any,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        idempotency_record_id: UUID,
        reference_type: str,
        reference_id: UUID,
    ) -> None:
        row = connection.execute(
            "UPDATE vnext_private.idempotency_records SET "
            "operation_status = 'succeeded', response_status_code = 201, "
            "response_reference_type = %s, response_reference_id = %s, "
            "updated_at = clock_timestamp() "
            "WHERE workspace_id = %s AND actor_user_id = %s "
            "AND idempotency_record_id = %s AND operation_status = 'pending' "
            "RETURNING idempotency_record_id",
            (
                reference_type,
                reference_id,
                workspace_id,
                principal.user_id,
                idempotency_record_id,
            ),
        ).fetchone()
        if row is None:
            raise VNextError.idempotency_conflict()

    @staticmethod
    def _layer_by_id(connection: Any, layer_id: UUID) -> SpatialLayer:
        row = connection.execute(
            "SELECT " + _LAYER_COLUMNS + " FROM vnext_core.spatial_layers "
            "WHERE spatial_layer_id = %s",
            (layer_id,),
        ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _layer_record(row)

    def append_parcel_geometry(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        geometry: ParcelGeometry,
        request_id: str,
        idempotency_record_id: UUID,
    ) -> ParcelGeometry:
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        selected_request_id = _bounded_text(request_id, maximum=128)
        source_shape = shape(dict(geometry.source_geometry))
        source_wkb = shapely.to_wkb(
            source_shape,
            hex=False,
            byte_order=1,
            include_srid=False,
        )
        source_hash = hashlib.sha256(source_wkb).hexdigest()
        coverage = geometry.coverage.as_evidence_mapping()
        lineage = [
            dict(item.as_mapping()) for item in geometry.provenance.processing_lineage
        ]
        try:
            with self._principal_context.transaction(principal) as connection:
                state, reference_type, reference_id, key_hash = self._idempotency_state(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                )
                if state == "succeeded":
                    if reference_type != "parcel_geometry" or reference_id is None:
                        raise VNextError.idempotency_conflict()
                    replay = connection.execute(
                        "SELECT " + _PARCEL_COLUMNS + " FROM "
                        "vnext_core.parcel_geometry_versions "
                        "WHERE workspace_id = %s AND parcel_geometry_id = %s",
                        (workspace_id, reference_id),
                    ).fetchone()
                    if replay is None:
                        raise VNextError.idempotency_conflict()
                    return _parcel_record(replay)
                if state != "pending":
                    raise VNextError.idempotency_conflict()
                row = connection.execute(
                    "INSERT INTO vnext_core.parcel_geometry_versions ("
                    "parcel_geometry_id, workspace_id, parcel_identity_reference_id, "
                    "geometry_version, supersedes_geometry_id, geometry_type, "
                    "source_geometry_wkb, source_geometry_sha256, source_crs, "
                    "source_coordinate_order, normalized_geometry, normalized_crs, "
                    "normalized_coordinate_order, precision_value, precision_unit, "
                    "precision_method, tolerance, tolerance_unit, geometry_source, "
                    "source_id, source_type, source_environment, provider_id, "
                    "provider_version, source_record_id, authority_class, retrieved_at, "
                    "effective_at, valid_from, valid_to, coverage_status, coverage, "
                    "processing_lineage, evidence_id, idempotency_record_id, "
                    "created_by_user_id"
                    ") VALUES ("
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, "
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s"
                    ") RETURNING " + _PARCEL_COLUMNS,
                    (
                        geometry.geometry_id,
                        workspace_id,
                        geometry.parcel_identity_reference_id,
                        geometry.version,
                        geometry.supersedes_geometry_id,
                        geometry.geometry_type.value,
                        source_wkb,
                        source_hash,
                        geometry.source_crs.identifier,
                        geometry.source_crs.coordinate_order.value,
                        _encoded(geometry.geometry, maximum=8_388_608),
                        geometry.normalized_crs.identifier,
                        geometry.normalized_crs.coordinate_order.value,
                        geometry.precision.value,
                        geometry.precision.unit,
                        geometry.precision.method,
                        geometry.tolerance,
                        geometry.tolerance_unit,
                        geometry.geometry_source,
                        geometry.provenance.source_id,
                        geometry.provenance.source_type.value,
                        geometry.provenance.environment.value,
                        geometry.provenance.provider_id,
                        geometry.provenance.provider_version,
                        geometry.provenance.source_record_id,
                        geometry.provenance.authority.value,
                        geometry.retrieved_at,
                        geometry.effective_at,
                        geometry.valid_from,
                        geometry.valid_to,
                        geometry.coverage.status.value,
                        _encoded(coverage),
                        _encoded(lineage),
                        geometry.evidence_id,
                        idempotency_record_id,
                        principal.user_id,
                    ),
                ).fetchone()
                if row is None:
                    raise VNextError.permission_denied()
                self._complete_idempotency(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    reference_type="parcel_geometry",
                    reference_id=geometry.geometry_id,
                )
                _append_audit(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    event_type="spatial.parcel_geometry.appended",
                    resource_type="parcel_geometry",
                    resource_id=geometry.geometry_id,
                    request_id=selected_request_id,
                    outcome="succeeded",
                    idempotency_key_hash=key_hash,
                    metadata={
                        "parcel_identity_reference_id": str(
                            geometry.parcel_identity_reference_id
                        ),
                        "geometry_version": geometry.version,
                        "supersedes_geometry_id": (
                            None
                            if geometry.supersedes_geometry_id is None
                            else str(geometry.supersedes_geometry_id)
                        ),
                        "authority_class": geometry.provenance.authority.value,
                    },
                )
                return _parcel_record(row)
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def latest_parcel_geometry(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        parcel_identity_reference_id: UUID,
    ) -> ParcelGeometry:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _PARCEL_COLUMNS + " FROM "
                "vnext_core.parcel_geometry_versions WHERE workspace_id = %s "
                "AND parcel_identity_reference_id = %s "
                "ORDER BY geometry_version DESC LIMIT 1",
                (workspace_id, parcel_identity_reference_id),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _parcel_record(row)

    def parcel_geometry_history(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        parcel_identity_reference_id: UUID,
        limit: int = 100,
    ) -> tuple[ParcelGeometry, ...]:
        self._authorizer.require_workspace_access(principal, workspace_id)
        if not 1 <= limit <= MAX_HISTORY_LIMIT:
            raise VNextError.validation_failed()
        with self._principal_context.transaction(principal) as connection:
            rows = connection.execute(
                "SELECT " + _PARCEL_COLUMNS + " FROM "
                "vnext_core.parcel_geometry_versions WHERE workspace_id = %s "
                "AND parcel_identity_reference_id = %s "
                "ORDER BY geometry_version DESC LIMIT %s",
                (workspace_id, parcel_identity_reference_id, limit),
            ).fetchall()
        return tuple(_parcel_record(row) for row in rows)

    def get_spatial_layer(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        layer_key: str,
        layer_version: int | None = None,
    ) -> SpatialLayer:
        self._authorizer.require_workspace_access(principal, workspace_id)
        selected_key = _bounded_text(layer_key, maximum=120).lower()
        if layer_version is not None and layer_version < 1:
            raise VNextError.validation_failed()
        with self._principal_context.transaction(principal) as connection:
            if layer_version is None:
                row = connection.execute(
                    "SELECT " + _LAYER_COLUMNS + " FROM vnext_core.spatial_layers "
                    "WHERE layer_key = %s ORDER BY layer_version DESC LIMIT 1",
                    (selected_key,),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT " + _LAYER_COLUMNS + " FROM vnext_core.spatial_layers "
                    "WHERE layer_key = %s AND layer_version = %s",
                    (selected_key, layer_version),
                ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _layer_record(row)

    def list_spatial_layers(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> tuple[SpatialLayer, ...]:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            rows = connection.execute(
                "SELECT " + _LAYER_COLUMNS + " FROM vnext_core.spatial_layers layer "
                "WHERE NOT EXISTS (SELECT 1 FROM vnext_core.spatial_layers later "
                "WHERE later.layer_key = layer.layer_key "
                "AND later.layer_version > layer.layer_version) "
                "ORDER BY layer.layer_key"
            ).fetchall()
        return tuple(_layer_record(row) for row in rows)

    def append_observation(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        observation: SpatialObservation,
        request_id: str,
        idempotency_record_id: UUID,
        parcel_geometry_id: UUID | None = None,
    ) -> SpatialObservation:
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        if observation.workspace_id != workspace_id:
            raise VNextError.validation_failed()
        selected_request_id = _bounded_text(request_id, maximum=128)
        coverage = observation.coverage.as_evidence_mapping()
        lineage = [
            dict(item.as_mapping())
            for item in observation.provenance.processing_lineage
        ]
        if observation.confidence is not None and not math.isfinite(
            observation.confidence
        ):
            raise VNextError.validation_failed()
        try:
            with self._principal_context.transaction(principal) as connection:
                state, reference_type, reference_id, key_hash = self._idempotency_state(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                )
                if state == "succeeded":
                    if reference_type != "spatial_observation" or reference_id is None:
                        raise VNextError.idempotency_conflict()
                    replay = connection.execute(
                        "SELECT " + _OBSERVATION_COLUMNS + " FROM "
                        "vnext_core.spatial_observations WHERE workspace_id = %s "
                        "AND spatial_observation_id = %s",
                        (workspace_id, reference_id),
                    ).fetchone()
                    if replay is None:
                        raise VNextError.idempotency_conflict()
                    layer = self._layer_by_id(connection, UUID(str(replay[5])))
                    return _observation_record(replay, layer)
                if state != "pending":
                    raise VNextError.idempotency_conflict()
                layer = self._layer_by_id(connection, observation.layer_id)
                if (
                    layer.provider_id != observation.provenance.provider_id
                    or layer.source_id != observation.provenance.source_id
                    or layer.source_type is not observation.provenance.source_type
                    or layer.source_environment
                    is not observation.provenance.environment
                    or layer.authority is not observation.provenance.authority
                ):
                    raise VNextError.validation_failed()
                row = connection.execute(
                    "INSERT INTO vnext_core.spatial_observations ("
                    "spatial_observation_id, workspace_id, subject_type, subject_id, "
                    "parcel_geometry_id, spatial_layer_id, observation_status, result, "
                    "coverage_status, coverage, evidence_id, source_id, source_type, "
                    "source_environment, provider_id, provider_version, source_record_id, "
                    "authority_class, retrieved_at, effective_at, processing_lineage, "
                    "license_status, license, confidence, confidence_method, limitations, "
                    "idempotency_record_id, "
                    "created_by_user_id"
                    ") VALUES ("
                    "%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, "
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, "
                    "%s, %s, %s, %s"
                    ") RETURNING " + _OBSERVATION_COLUMNS,
                    (
                        observation.observation_id,
                        workspace_id,
                        observation.subject_type,
                        observation.subject_id,
                        parcel_geometry_id,
                        observation.layer_id,
                        observation.status.value,
                        (
                            None
                            if observation.value is None
                            else _encoded(observation.value, maximum=32_768)
                        ),
                        observation.coverage.status.value,
                        _encoded(coverage),
                        observation.evidence_id,
                        observation.provenance.source_id,
                        observation.provenance.source_type.value,
                        observation.provenance.environment.value,
                        observation.provenance.provider_id,
                        observation.provenance.provider_version,
                        observation.provenance.source_record_id,
                        observation.provenance.authority.value,
                        observation.provenance.retrieved_at,
                        observation.provenance.effective_at,
                        _encoded(lineage),
                        observation.license.status.value,
                        _encoded(observation.license.as_evidence_mapping()),
                        observation.confidence,
                        observation.confidence_method,
                        list(observation.limitations),
                        idempotency_record_id,
                        principal.user_id,
                    ),
                ).fetchone()
                if row is None:
                    raise VNextError.permission_denied()
                self._complete_idempotency(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    reference_type="spatial_observation",
                    reference_id=observation.observation_id,
                )
                _append_audit(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    event_type="spatial.observation.appended",
                    resource_type="spatial_observation",
                    resource_id=observation.observation_id,
                    request_id=selected_request_id,
                    outcome="succeeded",
                    idempotency_key_hash=key_hash,
                    metadata={
                        "subject_type": observation.subject_type,
                        "subject_id": str(observation.subject_id),
                        "spatial_layer_id": str(observation.layer_id),
                        "observation_status": observation.status.value,
                        "authority_class": observation.provenance.authority.value,
                    },
                )
                return _observation_record(row, layer)
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def list_observations(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        subject_type: str,
        subject_id: UUID,
        parcel_geometry_id: UUID | None = None,
        limit: int = 100,
    ) -> tuple[SpatialObservation, ...]:
        self._authorizer.require_workspace_access(principal, workspace_id)
        selected_subject_type = _bounded_text(subject_type, maximum=32).lower()
        if not 1 <= limit <= MAX_HISTORY_LIMIT:
            raise VNextError.validation_failed()
        with self._principal_context.transaction(principal) as connection:
            rows = connection.execute(
                "SELECT " + _OBSERVATION_COLUMNS + " FROM "
                "vnext_core.spatial_observations WHERE workspace_id = %s "
                "AND subject_type = %s AND subject_id = %s "
                "AND (%s::uuid IS NULL OR parcel_geometry_id = %s) "
                "ORDER BY retrieved_at DESC, created_at DESC LIMIT %s",
                (
                    workspace_id,
                    selected_subject_type,
                    subject_id,
                    parcel_geometry_id,
                    parcel_geometry_id,
                    limit,
                ),
            ).fetchall()
            layers = {
                UUID(str(row[5])): self._layer_by_id(connection, UUID(str(row[5])))
                for row in rows
            }
        return tuple(
            _observation_record(row, layers[UUID(str(row[5]))]) for row in rows
        )
