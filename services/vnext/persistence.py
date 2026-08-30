"""RLS-backed durable Workspace command records and Cases for VNext."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import (
    WorkspaceAuthorizer,
    WorkspaceRole,
)
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import VNextError


CASE_WRITE_ROLES = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.MANAGER,
        WorkspaceRole.MEMBER,
    }
)


class CasePurpose(str, Enum):
    BUY_DUE_DILIGENCE = "buy_due_diligence"
    DEVELOPMENT = "development"
    BROKERAGE = "brokerage"
    VALUATION_REVIEW = "valuation_review"
    INVESTMENT_REVIEW = "investment_review"


class CaseStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CaseIdentityStatus(str, Enum):
    UNVERIFIED = "unverified"
    LEGACY_UNVERIFIED = "legacy_unverified"
    RESOLVING = "resolving"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class CaseRecord:
    case_id: UUID
    workspace_id: UUID
    purpose: CasePurpose
    status: CaseStatus
    title: str
    identity_status: CaseIdentityStatus
    assigned_member_id: UUID | None
    version: int
    opened_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    archived_at: datetime | None


_CASE_COLUMNS = (
    "case_id, workspace_id, purpose, status, title, identity_status, "
    "assigned_member_id, version, opened_at, updated_at, closed_at, archived_at"
)


def _bounded_text(value: str, *, maximum: int) -> str:
    selected = value.strip()
    if not selected or len(selected) > maximum or "\x00" in selected:
        raise VNextError.validation_failed()
    return selected


def _case_record(row: tuple[Any, ...]) -> CaseRecord:
    return CaseRecord(
        case_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        purpose=CasePurpose(str(row[2])),
        status=CaseStatus(str(row[3])),
        title=str(row[4]),
        identity_status=CaseIdentityStatus(str(row[5])),
        assigned_member_id=None if row[6] is None else UUID(str(row[6])),
        version=int(row[7]),
        opened_at=row[8],
        updated_at=row[9],
        closed_at=row[10],
        archived_at=row[11],
    )


_AUDIT_METADATA_KEYS = frozenset(
    {
        "changed_fields",
        "previous_version",
        "new_version",
        "operation_status",
        "membership_role",
    }
)


def _audit_metadata(metadata: Mapping[str, object] | None) -> str:
    selected = dict(metadata or {})
    if set(selected) - _AUDIT_METADATA_KEYS:
        raise VNextError.validation_failed()
    encoded = json.dumps(
        selected,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(encoded.encode("utf-8")) > 16_384:
        raise VNextError.validation_failed()
    return encoded


def _append_audit(
    connection: Any,
    *,
    principal: AuthenticatedPrincipal,
    workspace_id: UUID,
    event_type: str,
    resource_type: str,
    resource_id: UUID | None,
    request_id: str,
    outcome: str,
    metadata: Mapping[str, object] | None = None,
    idempotency_key_hash: str | None = None,
) -> UUID:
    audit_event_id = uuid4()
    connection.execute(
        "INSERT INTO vnext_private.audit_events ("
        "audit_event_id, workspace_id, actor_user_id, event_type, resource_type, "
        "resource_id, request_id, idempotency_key_hash, outcome, metadata"
        ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
        (
            audit_event_id,
            workspace_id,
            principal.user_id,
            _bounded_text(event_type, maximum=120),
            _bounded_text(resource_type, maximum=80),
            resource_id,
            _bounded_text(request_id, maximum=128),
            idempotency_key_hash,
            outcome,
            _audit_metadata(metadata),
        ),
    )
    return audit_event_id


class PostgresCaseRepository:
    """Create, read, and optimistically update Cases under app auth + RLS."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def create_case(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        purpose: CasePurpose,
        title: str,
        request_id: str,
    ) -> CaseRecord:
        membership = self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=CASE_WRITE_ROLES,
        )
        selected_title = _bounded_text(title, maximum=240)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "INSERT INTO vnext_core.cases ("
                "workspace_id, purpose, status, title, identity_status, created_by_user_id"
                ") VALUES (%s, %s, 'open', %s, 'unverified', %s) RETURNING "
                + _CASE_COLUMNS,
                (workspace_id, purpose.value, selected_title, principal.user_id),
            ).fetchone()
            if row is None:
                raise VNextError.permission_denied()
            case = _case_record(row)
            _append_audit(
                connection,
                principal=principal,
                workspace_id=workspace_id,
                event_type="case.created",
                resource_type="case",
                resource_id=case.case_id,
                request_id=request_id,
                outcome="succeeded",
                metadata={
                    "operation_status": "created",
                    "membership_role": membership.role.value,
                    "new_version": case.version,
                },
            )
            return case

    def get_case(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
    ) -> CaseRecord:
        self._authorizer.require_workspace_access(principal, workspace_id)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _CASE_COLUMNS + " FROM vnext_core.cases "
                "WHERE workspace_id = %s AND case_id = %s",
                (workspace_id, case_id),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        return _case_record(row)

    def update_case(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        expected_version: int,
        purpose: CasePurpose,
        status: CaseStatus,
        title: str,
        request_id: str,
    ) -> CaseRecord:
        membership = self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=CASE_WRITE_ROLES,
        )
        if expected_version < 1:
            raise VNextError.validation_failed()
        selected_title = _bounded_text(title, maximum=240)
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "UPDATE vnext_core.cases SET "
                "purpose = %s, status = %s, title = %s, version = version + 1, "
                "updated_at = clock_timestamp(), "
                "closed_at = CASE WHEN %s = 'closed' THEN "
                "COALESCE(closed_at, clock_timestamp()) ELSE closed_at END, "
                "archived_at = CASE WHEN %s = 'archived' THEN "
                "COALESCE(archived_at, clock_timestamp()) ELSE NULL END "
                "WHERE workspace_id = %s AND case_id = %s AND version = %s RETURNING "
                + _CASE_COLUMNS,
                (
                    purpose.value,
                    status.value,
                    selected_title,
                    status.value,
                    status.value,
                    workspace_id,
                    case_id,
                    expected_version,
                ),
            ).fetchone()
            if row is None:
                current = connection.execute(
                    "SELECT version FROM vnext_core.cases "
                    "WHERE workspace_id = %s AND case_id = %s",
                    (workspace_id, case_id),
                ).fetchone()
                if current is None:
                    raise VNextError.not_found()
                raise VNextError.version_conflict()
            case = _case_record(row)
            _append_audit(
                connection,
                principal=principal,
                workspace_id=workspace_id,
                event_type="case.updated",
                resource_type="case",
                resource_id=case.case_id,
                request_id=request_id,
                outcome="succeeded",
                metadata={
                    "changed_fields": ["purpose", "status", "title"],
                    "previous_version": expected_version,
                    "new_version": case.version,
                    "membership_role": membership.role.value,
                },
            )
            return case


class IdempotencyDecision(str, Enum):
    NEW = "new"
    REPLAY = "replay"


@dataclass(frozen=True)
class IdempotencyReservation:
    decision: IdempotencyDecision
    idempotency_record_id: UUID
    request_fingerprint: str
    operation_status: str
    response_reference_type: str | None
    response_reference_id: UUID | None


_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")
_IDEMPOTENCY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class PostgresIdempotencyRepository:
    """Reserve a bounded command key without retaining the raw key or body."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def reserve(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        method: str,
        canonical_route: str,
        idempotency_key: str,
        canonical_request: bytes,
        replay_window: timedelta = timedelta(hours=24),
    ) -> IdempotencyReservation:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=CASE_WRITE_ROLES,
        )
        selected_method = method.strip().upper()
        selected_route = _bounded_text(canonical_route, maximum=300)
        if (
            selected_method not in _IDEMPOTENCY_METHODS
            or not selected_route.startswith("/")
            or not _IDEMPOTENCY_KEY.fullmatch(idempotency_key)
            or len(canonical_request) > 65_536
            or replay_window < timedelta(hours=24)
        ):
            raise VNextError.validation_failed()
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        fingerprint = hashlib.sha256(canonical_request).hexdigest()
        record_id = uuid4()
        expires_at = datetime.now(timezone.utc) + replay_window
        with self._principal_context.transaction(principal) as connection:
            inserted = connection.execute(
                "INSERT INTO vnext_private.idempotency_records ("
                "idempotency_record_id, workspace_id, actor_user_id, http_method, "
                "canonical_route, idempotency_key_hash, request_fingerprint, expires_at"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (workspace_id, actor_user_id, http_method, "
                "canonical_route, idempotency_key_hash) DO NOTHING "
                "RETURNING idempotency_record_id, request_fingerprint, "
                "operation_status, response_reference_type, response_reference_id",
                (
                    record_id,
                    workspace_id,
                    principal.user_id,
                    selected_method,
                    selected_route,
                    key_hash,
                    fingerprint,
                    expires_at,
                ),
            ).fetchone()
            decision = IdempotencyDecision.NEW
            row = inserted
            if row is None:
                row = connection.execute(
                    "SELECT idempotency_record_id, request_fingerprint, "
                    "operation_status, response_reference_type, response_reference_id "
                    "FROM vnext_private.idempotency_records WHERE workspace_id = %s "
                    "AND actor_user_id = %s AND http_method = %s "
                    "AND canonical_route = %s AND idempotency_key_hash = %s",
                    (
                        workspace_id,
                        principal.user_id,
                        selected_method,
                        selected_route,
                        key_hash,
                    ),
                ).fetchone()
                if row is None:
                    raise VNextError.permission_denied()
                if str(row[1]) != fingerprint:
                    raise VNextError.idempotency_conflict()
                decision = IdempotencyDecision.REPLAY
            return IdempotencyReservation(
                decision=decision,
                idempotency_record_id=UUID(str(row[0])),
                request_fingerprint=str(row[1]),
                operation_status=str(row[2]),
                response_reference_type=(None if row[3] is None else str(row[3])),
                response_reference_id=(None if row[4] is None else UUID(str(row[4]))),
            )


@dataclass(frozen=True)
class AuditEvent:
    audit_event_id: UUID
    workspace_id: UUID
    actor_user_id: UUID
    event_type: str
    resource_type: str
    resource_id: UUID | None
    request_id: str
    outcome: str


class PostgresAuditRepository:
    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def append(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        event_type: str,
        resource_type: str,
        resource_id: UUID | None,
        request_id: str,
        outcome: str = "succeeded",
        metadata: Mapping[str, object] | None = None,
    ) -> AuditEvent:
        self._authorizer.require_workspace_access(principal, workspace_id)
        if outcome not in {"succeeded", "denied", "failed"}:
            raise VNextError.validation_failed()
        with self._principal_context.transaction(principal) as connection:
            audit_event_id = _append_audit(
                connection,
                principal=principal,
                workspace_id=workspace_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id,
                outcome=outcome,
                metadata=metadata,
            )
        return AuditEvent(
            audit_event_id=audit_event_id,
            workspace_id=workspace_id,
            actor_user_id=principal.user_id,
            event_type=event_type.strip(),
            resource_type=resource_type.strip(),
            resource_id=resource_id,
            request_id=request_id.strip(),
            outcome=outcome,
        )
