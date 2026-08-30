"""Principal-bound Property graph and immutable Evidence persistence.

This module implements only the Stage 1 Slice 3 append/read foundation.  It
does not resolve inputs, rank candidates, confirm identity, call providers, or
attach Cases to PropertyEntity records.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer, WorkspaceRole
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import VNextError


GRAPH_WRITE_ROLES = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.MANAGER,
        WorkspaceRole.MEMBER,
    }
)


class SourceType(str, Enum):
    OFFICIAL = "official"
    PARTNER = "partner"
    USER = "user"
    DETERMINISTIC = "deterministic"
    DOCUMENT = "document"
    DEMO = "demo"
    TEST = "test"


class SourceEnvironment(str, Enum):
    PRODUCTION = "production"
    DEMO = "demo"
    TEST = "test"


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    source_type: SourceType
    readiness: str
    environments: frozenset[SourceEnvironment]
    request_appendable: bool


# Code-level counterpart of docs/vnext/data-source-registry-v1.md.  Presence
# here bounds source identifiers; it is not a production-readiness approval.
DATA_SOURCE_REGISTRY: Mapping[str, SourceDefinition] = MappingProxyType(
    {
        "moi-dla-plvr": SourceDefinition(
            "moi-dla-plvr",
            SourceType.OFFICIAL,
            "prototype_partial",
            frozenset({SourceEnvironment.PRODUCTION, SourceEnvironment.TEST}),
            False,
        ),
        "tgos-address": SourceDefinition(
            "tgos-address",
            SourceType.OFFICIAL,
            "prototype_partial",
            frozenset({SourceEnvironment.PRODUCTION, SourceEnvironment.TEST}),
            False,
        ),
        "nlsc-cadastral": SourceDefinition(
            "nlsc-cadastral",
            SourceType.OFFICIAL,
            "metadata_only",
            frozenset({SourceEnvironment.PRODUCTION, SourceEnvironment.TEST}),
            False,
        ),
        "user-upload": SourceDefinition(
            "user-upload",
            SourceType.USER,
            "user_input_partial",
            frozenset({SourceEnvironment.PRODUCTION, SourceEnvironment.TEST}),
            True,
        ),
        "vnext-deterministic": SourceDefinition(
            "vnext-deterministic",
            SourceType.DETERMINISTIC,
            "metadata_only",
            frozenset({SourceEnvironment.PRODUCTION, SourceEnvironment.TEST}),
            True,
        ),
        "vnext-demo": SourceDefinition(
            "vnext-demo",
            SourceType.DEMO,
            "metadata_only",
            frozenset({SourceEnvironment.DEMO}),
            True,
        ),
        "vnext-test": SourceDefinition(
            "vnext-test",
            SourceType.TEST,
            "metadata_only",
            frozenset({SourceEnvironment.TEST}),
            True,
        ),
    }
)


class PropertyEntityStatus(str, Enum):
    UNVERIFIED = "unverified"
    ACTIVE = "active"
    DISPUTED = "disputed"
    ARCHIVED = "archived"


class IdentityReferenceType(str, Enum):
    ADDRESS = "address"
    GEO_REFERENCE = "geo_reference"
    PARCEL = "parcel"
    BUILDING = "building"


class IdentityReferenceStatus(str, Enum):
    OBSERVED = "observed"
    LIMITED = "limited"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class PropertyRelationType(str, Enum):
    PROPERTY_ADDRESS = "property_address"
    PROPERTY_GEO_REFERENCE = "property_geo_reference"
    PROPERTY_PARCEL = "property_parcel"
    PROPERTY_BUILDING = "property_building"
    PARCEL_BUILDING = "parcel_building"


class RelationDirection(str, Enum):
    DIRECTED = "directed"
    BIDIRECTIONAL = "bidirectional"


class PropertyRelationStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"


class EvidenceStatus(str, Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    STALE = "stale"
    CONFLICTING = "conflicting"
    USER_PROVIDED = "user_provided"
    UNVERIFIED = "unverified"


class CoverageStatus(str, Enum):
    KNOWN = "known"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class QualityStatus(str, Enum):
    PASSED = "passed"
    LIMITED = "limited"
    FAILED = "failed"
    NOT_CHECKED = "not_checked"


class LicenseStatus(str, Enum):
    APPROVED = "approved"
    OWNER_REVIEW_REQUIRED = "owner_review_required"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class EvidenceLineageType(str, Enum):
    DERIVED_FROM = "derived_from"
    NORMALIZED_FROM = "normalized_from"
    AGGREGATED_FROM = "aggregated_from"
    CALCULATED_FROM = "calculated_from"
    MANUAL_REVIEW_FROM = "manual_review_from"
    SUPERSEDES = "supersedes"


class EvidenceTransformation(str, Enum):
    NORMALIZATION = "normalization"
    AGGREGATION = "aggregation"
    CALCULATION = "calculation"
    MANUAL_REVIEW = "manual_review"
    NONE = "none"


class EvidenceLinkType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    LIMITS = "limits"
    DESCRIBES = "describes"


@dataclass(frozen=True)
class PropertyEntityRecord:
    property_entity_id: UUID
    property_graph_node_id: UUID
    workspace_id: UUID
    entity_status: PropertyEntityStatus
    display_label: str
    version: int
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


@dataclass(frozen=True)
class IdentityReferenceDraft:
    reference_type: IdentityReferenceType
    normalized_key: str
    display_value: str
    source_id: str
    source_environment: SourceEnvironment
    reference_status: IdentityReferenceStatus = IdentityReferenceStatus.UNVERIFIED
    source_record_id: str | None = None
    confidence: float | None = None
    confidence_method: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    supersedes_reference_id: UUID | None = None


@dataclass(frozen=True)
class IdentityReferenceRecord:
    identity_reference_id: UUID
    property_graph_node_id: UUID
    workspace_id: UUID
    reference_type: IdentityReferenceType
    normalized_key: str
    display_value: str
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    source_record_id: str | None
    confidence: float | None
    confidence_method: str | None
    reference_status: IdentityReferenceStatus
    valid_from: datetime | None
    valid_to: datetime | None
    supersedes_reference_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class PropertyRelationDraft:
    from_node_id: UUID
    to_node_id: UUID
    relation_type: PropertyRelationType
    direction: RelationDirection
    source_id: str
    source_environment: SourceEnvironment
    relation_status: PropertyRelationStatus = PropertyRelationStatus.PROPOSED
    confidence: float | None = None
    confidence_method: str | None = None
    evidence_id: UUID | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    supersedes_relation_id: UUID | None = None


@dataclass(frozen=True)
class PropertyRelationRecord:
    property_relation_id: UUID
    workspace_id: UUID
    from_node_id: UUID
    to_node_id: UUID
    relation_type: PropertyRelationType
    direction: RelationDirection
    confidence: float | None
    confidence_method: str | None
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    evidence_id: UUID | None
    relation_status: PropertyRelationStatus
    valid_from: datetime | None
    valid_to: datetime | None
    supersedes_relation_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class EvidenceDraft:
    fact_type: str
    source_id: str
    source_environment: SourceEnvironment
    retrieved_at: datetime
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    evidence_status: EvidenceStatus
    quality_status: QualityStatus
    quality: Mapping[str, object]
    license_status: LicenseStatus
    license: Mapping[str, object]
    value: Mapping[str, object] | None = None
    value_ref: str | None = None
    value_schema: str | None = None
    provider: str | None = None
    source_record_id: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    expires_at: datetime | None = None
    quality_confidence: float | None = None
    quality_method: str | None = None
    license_ref: str | None = None
    lineage: Mapping[str, object] | None = None
    raw_artifact_ref: str | None = None
    supersedes_evidence_id: UUID | None = None


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: UUID
    workspace_id: UUID
    fact_type: str
    value: Mapping[str, object] | None
    value_ref: str | None
    value_schema: str | None
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    provider: str | None
    source_record_id: str | None
    retrieved_at: datetime
    effective_from: datetime | None
    effective_to: datetime | None
    expires_at: datetime | None
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    evidence_status: EvidenceStatus
    quality_confidence: float | None
    quality_method: str | None
    quality_status: QualityStatus
    quality: Mapping[str, object]
    license_status: LicenseStatus
    license_ref: str | None
    license: Mapping[str, object]
    lineage: Mapping[str, object]
    content_hash: str
    evidence_version: int
    raw_artifact_ref: str | None
    supersedes_evidence_id: UUID | None
    created_by_user_id: UUID | None
    created_by_service: str | None
    created_at: datetime


_PROPERTY_COLUMNS = (
    "property_entity_id, workspace_id, entity_status, display_label, version, "
    "created_by_user_id, created_at, updated_at, archived_at"
)
_REFERENCE_COLUMNS = (
    "identity_reference_id, workspace_id, reference_type, normalized_key, "
    "display_value, source_id, source_type, source_environment, source_record_id, "
    "confidence, confidence_method, reference_status, valid_from, valid_to, "
    "supersedes_reference_id, created_by_user_id, created_at"
)
_RELATION_COLUMNS = (
    "property_relation_id, workspace_id, from_node_id, to_node_id, relation_type, "
    "direction, confidence, confidence_method, source_id, source_type, "
    "source_environment, evidence_id, relation_status, valid_from, valid_to, "
    "supersedes_relation_id, created_by_user_id, created_at"
)
_EVIDENCE_COLUMNS = (
    "evidence_id, workspace_id, fact_type, value, value_ref, value_schema, "
    "source_id, source_type, source_environment, provider, source_record_id, "
    "retrieved_at, effective_from, effective_to, expires_at, coverage_status, "
    "coverage, evidence_status, quality_confidence, quality_method, quality_status, "
    "quality, license_status, license_ref, license, lineage, content_hash, "
    "evidence_version, raw_artifact_ref, supersedes_evidence_id, "
    "created_by_user_id, created_by_service, created_at"
)

_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")
_FACT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{2,119}$")
_OPAQUE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,239}$")


def _bounded_text(value: str, *, maximum: int) -> str:
    selected = value.strip()
    if not selected or len(selected) > maximum or "\x00" in selected:
        raise VNextError.validation_failed()
    return selected


def _optional_text(value: str | None, *, maximum: int) -> str | None:
    return None if value is None else _bounded_text(value, maximum=maximum)


def _optional_opaque_reference(value: str | None) -> str | None:
    selected = _optional_text(value, maximum=240)
    if selected is not None and not _OPAQUE_REFERENCE.fullmatch(selected):
        raise VNextError.validation_failed()
    return selected


def _json_object(value: Mapping[str, object] | None, *, maximum: int = 16_384) -> str:
    selected = dict(value or {})
    try:
        encoded = json.dumps(
            selected,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError):
        raise VNextError.validation_failed() from None
    if len(encoded.encode("utf-8")) > maximum:
        raise VNextError.validation_failed()
    return encoded


def _decoded_object(value: object | None) -> Mapping[str, object] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        selected = json.loads(value)
        if isinstance(selected, dict):
            return selected
    raise VNextError.validation_failed()


def _source_definition(
    source_id: str,
    environment: SourceEnvironment,
    *,
    require_request_append: bool = True,
) -> SourceDefinition:
    selected_id = source_id.strip()
    if not _SOURCE_ID.fullmatch(selected_id):
        raise VNextError.validation_failed()
    definition = DATA_SOURCE_REGISTRY.get(selected_id)
    if (
        definition is None
        or environment not in definition.environments
        or (require_request_append and not definition.request_appendable)
    ):
        raise VNextError.permission_denied()
    return definition


def _confidence(value: float | None, method: str | None) -> tuple[float | None, str | None]:
    selected_method = _optional_text(method, maximum=120)
    if value is None:
        return None, selected_method
    selected = float(value)
    if not math.isfinite(selected) or selected < 0 or selected > 1 or selected_method is None:
        raise VNextError.validation_failed()
    return selected, selected_method


def _valid_period(start: datetime | None, end: datetime | None) -> None:
    if any(value is not None and value.utcoffset() is None for value in (start, end)):
        raise VNextError.validation_failed()
    if start is not None and end is not None and start > end:
        raise VNextError.validation_failed()


def _property_record(row: tuple[Any, ...], node_id: object) -> PropertyEntityRecord:
    return PropertyEntityRecord(
        property_entity_id=UUID(str(row[0])),
        property_graph_node_id=UUID(str(node_id)),
        workspace_id=UUID(str(row[1])),
        entity_status=PropertyEntityStatus(str(row[2])),
        display_label=str(row[3]),
        version=int(row[4]),
        created_by_user_id=UUID(str(row[5])),
        created_at=row[6],
        updated_at=row[7],
        archived_at=row[8],
    )


def _reference_record(row: tuple[Any, ...], node_id: object) -> IdentityReferenceRecord:
    return IdentityReferenceRecord(
        identity_reference_id=UUID(str(row[0])),
        property_graph_node_id=UUID(str(node_id)),
        workspace_id=UUID(str(row[1])),
        reference_type=IdentityReferenceType(str(row[2])),
        normalized_key=str(row[3]),
        display_value=str(row[4]),
        source_id=str(row[5]),
        source_type=SourceType(str(row[6])),
        source_environment=SourceEnvironment(str(row[7])),
        source_record_id=None if row[8] is None else str(row[8]),
        confidence=None if row[9] is None else float(row[9]),
        confidence_method=None if row[10] is None else str(row[10]),
        reference_status=IdentityReferenceStatus(str(row[11])),
        valid_from=row[12],
        valid_to=row[13],
        supersedes_reference_id=None if row[14] is None else UUID(str(row[14])),
        created_by_user_id=UUID(str(row[15])),
        created_at=row[16],
    )


def _relation_record(row: tuple[Any, ...]) -> PropertyRelationRecord:
    return PropertyRelationRecord(
        property_relation_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        from_node_id=UUID(str(row[2])),
        to_node_id=UUID(str(row[3])),
        relation_type=PropertyRelationType(str(row[4])),
        direction=RelationDirection(str(row[5])),
        confidence=None if row[6] is None else float(row[6]),
        confidence_method=None if row[7] is None else str(row[7]),
        source_id=str(row[8]),
        source_type=SourceType(str(row[9])),
        source_environment=SourceEnvironment(str(row[10])),
        evidence_id=None if row[11] is None else UUID(str(row[11])),
        relation_status=PropertyRelationStatus(str(row[12])),
        valid_from=row[13],
        valid_to=row[14],
        supersedes_relation_id=None if row[15] is None else UUID(str(row[15])),
        created_by_user_id=UUID(str(row[16])),
        created_at=row[17],
    )


def _evidence_record(row: tuple[Any, ...]) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        fact_type=str(row[2]),
        value=_decoded_object(row[3]),
        value_ref=None if row[4] is None else str(row[4]),
        value_schema=None if row[5] is None else str(row[5]),
        source_id=str(row[6]),
        source_type=SourceType(str(row[7])),
        source_environment=SourceEnvironment(str(row[8])),
        provider=None if row[9] is None else str(row[9]),
        source_record_id=None if row[10] is None else str(row[10]),
        retrieved_at=row[11],
        effective_from=row[12],
        effective_to=row[13],
        expires_at=row[14],
        coverage_status=CoverageStatus(str(row[15])),
        coverage=_decoded_object(row[16]) or {},
        evidence_status=EvidenceStatus(str(row[17])),
        quality_confidence=None if row[18] is None else float(row[18]),
        quality_method=None if row[19] is None else str(row[19]),
        quality_status=QualityStatus(str(row[20])),
        quality=_decoded_object(row[21]) or {},
        license_status=LicenseStatus(str(row[22])),
        license_ref=None if row[23] is None else str(row[23]),
        license=_decoded_object(row[24]) or {},
        lineage=_decoded_object(row[25]) or {},
        content_hash=str(row[26]),
        evidence_version=int(row[27]),
        raw_artifact_ref=None if row[28] is None else str(row[28]),
        supersedes_evidence_id=None if row[29] is None else UUID(str(row[29])),
        created_by_user_id=None if row[30] is None else UUID(str(row[30])),
        created_by_service=None if row[31] is None else str(row[31]),
        created_at=row[32],
    )


class PostgresPropertyGraphRepository:
    """Create/read unverified property anchors and append graph observations."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def create_property_entity(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        display_label: str,
    ) -> PropertyEntityRecord:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=GRAPH_WRITE_ROLES,
        )
        label = _bounded_text(display_label, maximum=240)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "INSERT INTO vnext_core.property_entities ("
                "workspace_id, entity_status, display_label, created_by_user_id"
                ") VALUES (%s, 'unverified', %s, %s) RETURNING " + _PROPERTY_COLUMNS,
                (workspace_id, label, principal.user_id),
            ).fetchone()
            if row is None:
                raise VNextError.permission_denied()
            node = connection.execute(
                "SELECT property_graph_node_id FROM vnext_core.property_graph_nodes "
                "WHERE workspace_id = %s AND node_type = 'property' AND record_id = %s",
                (workspace_id, row[0]),
            ).fetchone()
            if node is None:
                raise VNextError.not_found()
            return _property_record(row, node[0])

    def get_property_entity(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        property_entity_id: UUID,
    ) -> PropertyEntityRecord:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _PROPERTY_COLUMNS + ", node.property_graph_node_id "
                "FROM vnext_core.property_entities property "
                "JOIN vnext_core.property_graph_nodes node "
                "ON node.workspace_id = property.workspace_id "
                "AND node.node_type = 'property' "
                "AND node.record_id = property.property_entity_id "
                "WHERE property.workspace_id = %s AND property.property_entity_id = %s",
                (workspace_id, property_entity_id),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _property_record(row[:9], row[9])

    def append_identity_reference(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        draft: IdentityReferenceDraft,
    ) -> IdentityReferenceRecord:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=GRAPH_WRITE_ROLES,
        )
        source = _source_definition(draft.source_id, draft.source_environment)
        normalized_key = _bounded_text(draft.normalized_key, maximum=512)
        display_value = _bounded_text(draft.display_value, maximum=512)
        source_record_id = _optional_text(draft.source_record_id, maximum=240)
        confidence, confidence_method = _confidence(
            draft.confidence,
            draft.confidence_method,
        )
        _valid_period(draft.valid_from, draft.valid_to)
        if (
            draft.reference_status is IdentityReferenceStatus.SUPERSEDED
            and draft.supersedes_reference_id is None
        ):
            raise VNextError.validation_failed()
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "INSERT INTO vnext_core.property_identity_references ("
                "workspace_id, reference_type, normalized_key, display_value, source_id, "
                "source_type, source_environment, source_record_id, confidence, "
                "confidence_method, reference_status, valid_from, valid_to, "
                "supersedes_reference_id, created_by_user_id"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING " + _REFERENCE_COLUMNS,
                (
                    workspace_id,
                    draft.reference_type.value,
                    normalized_key,
                    display_value,
                    source.source_id,
                    source.source_type.value,
                    draft.source_environment.value,
                    source_record_id,
                    confidence,
                    confidence_method,
                    draft.reference_status.value,
                    draft.valid_from,
                    draft.valid_to,
                    draft.supersedes_reference_id,
                    principal.user_id,
                ),
            ).fetchone()
            if row is None:
                raise VNextError.permission_denied()
            node = connection.execute(
                "SELECT property_graph_node_id FROM vnext_core.property_graph_nodes "
                "WHERE workspace_id = %s AND node_type = %s AND record_id = %s",
                (workspace_id, draft.reference_type.value, row[0]),
            ).fetchone()
            if node is None:
                raise VNextError.not_found()
            return _reference_record(row, node[0])

    def get_identity_reference(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        identity_reference_id: UUID,
    ) -> IdentityReferenceRecord:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _REFERENCE_COLUMNS + ", node.property_graph_node_id "
                "FROM vnext_core.property_identity_references reference "
                "JOIN vnext_core.property_graph_nodes node "
                "ON node.workspace_id = reference.workspace_id "
                "AND node.node_type = reference.reference_type "
                "AND node.record_id = reference.identity_reference_id "
                "WHERE reference.workspace_id = %s AND reference.identity_reference_id = %s",
                (workspace_id, identity_reference_id),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _reference_record(row[:17], row[17])

    def append_relation(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        draft: PropertyRelationDraft,
    ) -> PropertyRelationRecord:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=GRAPH_WRITE_ROLES,
        )
        source = _source_definition(draft.source_id, draft.source_environment)
        confidence, confidence_method = _confidence(
            draft.confidence,
            draft.confidence_method,
        )
        _valid_period(draft.valid_from, draft.valid_to)
        if draft.relation_status is PropertyRelationStatus.CONFIRMED:
            # Confirmation belongs to the later reviewed command slice.
            raise VNextError.permission_denied()
        if draft.relation_type is PropertyRelationType.PARCEL_BUILDING:
            if draft.direction is not RelationDirection.BIDIRECTIONAL:
                raise VNextError.validation_failed()
        elif draft.direction is not RelationDirection.DIRECTED:
            raise VNextError.validation_failed()
        if (
            draft.relation_status is PropertyRelationStatus.SUPERSEDED
            and (draft.supersedes_relation_id is None or draft.valid_to is None)
        ):
            raise VNextError.validation_failed()
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "INSERT INTO vnext_core.property_relations ("
                "workspace_id, from_node_id, to_node_id, relation_type, direction, "
                "confidence, confidence_method, source_id, source_type, "
                "source_environment, evidence_id, relation_status, valid_from, valid_to, "
                "supersedes_relation_id, created_by_user_id"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING " + _RELATION_COLUMNS,
                (
                    workspace_id,
                    draft.from_node_id,
                    draft.to_node_id,
                    draft.relation_type.value,
                    draft.direction.value,
                    confidence,
                    confidence_method,
                    source.source_id,
                    source.source_type.value,
                    draft.source_environment.value,
                    draft.evidence_id,
                    draft.relation_status.value,
                    draft.valid_from,
                    draft.valid_to,
                    draft.supersedes_relation_id,
                    principal.user_id,
                ),
            ).fetchone()
        if row is None:
            raise VNextError.permission_denied()
        return _relation_record(row)

    def get_relation(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        property_relation_id: UUID,
    ) -> PropertyRelationRecord:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _RELATION_COLUMNS + " FROM vnext_core.property_relations "
                "WHERE workspace_id = %s AND property_relation_id = %s",
                (workspace_id, property_relation_id),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _relation_record(row)


def _validated_evidence_draft(
    draft: EvidenceDraft,
) -> tuple[SourceDefinition, dict[str, object]]:
    source = _source_definition(draft.source_id, draft.source_environment)
    fact_type = draft.fact_type.strip()
    if not _FACT_TYPE.fullmatch(fact_type):
        raise VNextError.validation_failed()
    if draft.retrieved_at.utcoffset() is None:
        raise VNextError.validation_failed()
    _valid_period(draft.effective_from, draft.effective_to)
    if draft.expires_at is not None and (
        draft.expires_at.utcoffset() is None
        or draft.expires_at <= draft.retrieved_at
    ):
        raise VNextError.validation_failed()
    value = None if draft.value is None else _json_object(draft.value, maximum=32_768)
    value_ref = _optional_opaque_reference(draft.value_ref)
    if value is not None and value_ref is not None:
        raise VNextError.validation_failed()
    if draft.evidence_status in {
        EvidenceStatus.AVAILABLE,
        EvidenceStatus.LIMITED,
        EvidenceStatus.USER_PROVIDED,
    } and value is None and value_ref is None:
        raise VNextError.validation_failed()
    if draft.evidence_status in {EvidenceStatus.UNAVAILABLE, EvidenceStatus.UNKNOWN} and (
        value is not None or value_ref is not None
    ):
        raise VNextError.validation_failed()
    if draft.evidence_status is EvidenceStatus.USER_PROVIDED and source.source_type is not SourceType.USER:
        raise VNextError.validation_failed()
    if source.source_type in {SourceType.DEMO, SourceType.TEST} and draft.evidence_status is EvidenceStatus.AVAILABLE:
        raise VNextError.validation_failed()
    confidence, quality_method = _confidence(
        draft.quality_confidence,
        draft.quality_method,
    )
    selected = {
        "fact_type": fact_type,
        "value": value,
        "value_ref": value_ref,
        "value_schema": _optional_text(draft.value_schema, maximum=120),
        "provider": _optional_text(draft.provider, maximum=120),
        "source_record_id": _optional_text(draft.source_record_id, maximum=240),
        "coverage": _json_object(draft.coverage),
        "quality": _json_object(draft.quality),
        "quality_confidence": confidence,
        "quality_method": quality_method,
        "license_ref": _optional_text(draft.license_ref, maximum=160),
        "license": _json_object(draft.license),
        "lineage": _json_object(draft.lineage),
        "raw_artifact_ref": _optional_opaque_reference(draft.raw_artifact_ref),
    }
    return source, selected


def _evidence_hash(
    draft: EvidenceDraft,
    source: SourceDefinition,
    selected: Mapping[str, object],
) -> str:
    payload = {
        "fact_type": selected["fact_type"],
        "value": selected["value"],
        "value_ref": selected["value_ref"],
        "value_schema": selected["value_schema"],
        "source_id": source.source_id,
        "source_type": source.source_type.value,
        "source_environment": draft.source_environment.value,
        "source_record_id": selected["source_record_id"],
        "retrieved_at": draft.retrieved_at.isoformat(),
        "effective_from": None if draft.effective_from is None else draft.effective_from.isoformat(),
        "effective_to": None if draft.effective_to is None else draft.effective_to.isoformat(),
        "coverage": selected["coverage"],
        "status": draft.evidence_status.value,
        "quality": selected["quality"],
        "license": selected["license"],
        "lineage": selected["lineage"],
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class PostgresEvidenceRepository:
    """Append/read immutable Evidence, lineage, and resource links under RLS."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def append_evidence(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        draft: EvidenceDraft,
    ) -> EvidenceRecord:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=GRAPH_WRITE_ROLES,
        )
        source, selected = _validated_evidence_draft(draft)
        content_hash = _evidence_hash(draft, source, selected)
        with self._principal_context.transaction(principal) as connection:
            evidence_version = 1
            if draft.supersedes_evidence_id is not None:
                parent = connection.execute(
                    "SELECT evidence_version FROM vnext_core.evidence_items "
                    "WHERE workspace_id = %s AND evidence_id = %s",
                    (workspace_id, draft.supersedes_evidence_id),
                ).fetchone()
                if parent is None:
                    raise VNextError.not_found()
                evidence_version = int(parent[0]) + 1
            row = connection.execute(
                "INSERT INTO vnext_core.evidence_items ("
                "workspace_id, fact_type, value, value_ref, value_schema, source_id, "
                "source_type, source_environment, provider, source_record_id, "
                "retrieved_at, effective_from, effective_to, expires_at, coverage_status, "
                "coverage, evidence_status, quality_confidence, quality_method, "
                "quality_status, quality, license_status, license_ref, license, lineage, "
                "content_hash, evidence_version, raw_artifact_ref, supersedes_evidence_id, "
                "created_by_user_id"
                ") VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, "
                "%s::jsonb, %s, %s, %s, %s, %s) RETURNING " + _EVIDENCE_COLUMNS,
                (
                    workspace_id,
                    selected["fact_type"],
                    selected["value"],
                    selected["value_ref"],
                    selected["value_schema"],
                    source.source_id,
                    source.source_type.value,
                    draft.source_environment.value,
                    selected["provider"],
                    selected["source_record_id"],
                    draft.retrieved_at,
                    draft.effective_from,
                    draft.effective_to,
                    draft.expires_at,
                    draft.coverage_status.value,
                    selected["coverage"],
                    draft.evidence_status.value,
                    selected["quality_confidence"],
                    selected["quality_method"],
                    draft.quality_status.value,
                    selected["quality"],
                    draft.license_status.value,
                    selected["license_ref"],
                    selected["license"],
                    selected["lineage"],
                    content_hash,
                    evidence_version,
                    selected["raw_artifact_ref"],
                    draft.supersedes_evidence_id,
                    principal.user_id,
                ),
            ).fetchone()
            if row is None:
                raise VNextError.permission_denied()
            if draft.supersedes_evidence_id is not None:
                connection.execute(
                    "INSERT INTO vnext_core.evidence_lineage ("
                    "workspace_id, child_evidence_id, parent_evidence_id, lineage_type, "
                    "transformation, created_by_user_id"
                    ") VALUES (%s, %s, %s, 'supersedes', 'none', %s)",
                    (workspace_id, row[0], draft.supersedes_evidence_id, principal.user_id),
                )
            return _evidence_record(row)

    def get_evidence(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        evidence_id: UUID,
    ) -> EvidenceRecord:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _EVIDENCE_COLUMNS + " FROM vnext_core.evidence_items "
                "WHERE workspace_id = %s AND evidence_id = %s",
                (workspace_id, evidence_id),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _evidence_record(row)

    def append_lineage(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        child_evidence_id: UUID,
        parent_evidence_id: UUID,
        lineage_type: EvidenceLineageType,
        transformation: EvidenceTransformation,
        transformation_version: str | None = None,
    ) -> UUID:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=GRAPH_WRITE_ROLES,
        )
        if child_evidence_id == parent_evidence_id:
            raise VNextError.validation_failed()
        version = _optional_text(transformation_version, maximum=120)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "INSERT INTO vnext_core.evidence_lineage ("
                "workspace_id, child_evidence_id, parent_evidence_id, lineage_type, "
                "transformation, transformation_version, created_by_user_id"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING evidence_lineage_id",
                (
                    workspace_id,
                    child_evidence_id,
                    parent_evidence_id,
                    lineage_type.value,
                    transformation.value,
                    version,
                    principal.user_id,
                ),
            ).fetchone()
        if row is None:
            raise VNextError.permission_denied()
        return UUID(str(row[0]))

    def link_evidence(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        evidence_id: UUID,
        subject_node_id: UUID,
        link_type: EvidenceLinkType,
        fact_scope: str,
    ) -> UUID:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=GRAPH_WRITE_ROLES,
        )
        selected_scope = fact_scope.strip()
        if not _FACT_TYPE.fullmatch(selected_scope):
            raise VNextError.validation_failed()
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "INSERT INTO vnext_core.evidence_links ("
                "workspace_id, evidence_id, subject_node_id, link_type, fact_scope, "
                "created_by_user_id"
                ") VALUES (%s, %s, %s, %s, %s, %s) RETURNING evidence_link_id",
                (
                    workspace_id,
                    evidence_id,
                    subject_node_id,
                    link_type.value,
                    selected_scope,
                    principal.user_id,
                ),
            ).fetchone()
        if row is None:
            raise VNextError.permission_denied()
        return UUID(str(row[0]))
