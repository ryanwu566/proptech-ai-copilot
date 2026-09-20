"""Atomic PostgreSQL persistence for Case-local parcel-set review."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.case_parcel_set import (
    CaseParcelSetMemberRecord,
    CaseParcelSetRecord,
    ParcelMemberReviewStatus,
    ParcelSetStatus,
)
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.persistence import CASE_WRITE_ROLES, _append_audit, _bounded_text


CASE_PARCEL_SET_RESPONSE_TYPE = "case_parcel_set"

_SET_COLUMNS = (
    "parcel_set_id, workspace_id, case_id, status, version, active_member_id, "
    "created_by_user_id, created_at, updated_at, reviewed_at"
)
_MEMBER_COLUMNS = (
    "parcel_set_member_id, workspace_id, parcel_set_id, "
    "parcel_identity_reference_id, position, review_status, "
    "created_by_user_id, created_at, updated_at"
)


def _translate_database_error(error: Exception) -> VNextError:
    sqlstate = str(getattr(error, "sqlstate", ""))
    if sqlstate in {"40001"}:
        return VNextError.version_conflict()
    if sqlstate == "40P01":
        return VNextError(ErrorCode.MAINTENANCE)
    if sqlstate == "42501":
        return VNextError.permission_denied()
    if sqlstate == "23503":
        return VNextError.not_found()
    if sqlstate in {"23505", "23514"}:
        return VNextError.validation_failed()
    return VNextError(ErrorCode.INTERNAL_ERROR)


def _member_record(row: tuple[Any, ...]) -> CaseParcelSetMemberRecord:
    return CaseParcelSetMemberRecord(
        parcel_set_member_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        parcel_set_id=UUID(str(row[2])),
        parcel_identity_reference_id=UUID(str(row[3])),
        position=int(row[4]),
        review_status=ParcelMemberReviewStatus(str(row[5])),
        created_by_user_id=UUID(str(row[6])),
        created_at=row[7],
        updated_at=row[8],
    )


def _set_record(
    row: tuple[Any, ...],
    members: tuple[CaseParcelSetMemberRecord, ...],
) -> CaseParcelSetRecord:
    return CaseParcelSetRecord(
        parcel_set_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        case_id=UUID(str(row[2])),
        status=ParcelSetStatus(str(row[3])),
        version=int(row[4]),
        active_member_id=None if row[5] is None else UUID(str(row[5])),
        created_by_user_id=UUID(str(row[6])),
        created_at=row[7],
        updated_at=row[8],
        reviewed_at=row[9],
        members=members,
    )


class PostgresCaseParcelSetRepository:
    """Persist one parcel-review set per Case without changing Property Identity."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    @staticmethod
    def _read_members(
        connection: Any,
        *,
        workspace_id: UUID,
        parcel_set_id: UUID,
    ) -> tuple[CaseParcelSetMemberRecord, ...]:
        rows = connection.execute(
            f"SELECT {_MEMBER_COLUMNS} FROM vnext_core.case_parcel_set_members "
            "WHERE workspace_id = %s AND parcel_set_id = %s "
            "ORDER BY position, parcel_set_member_id",
            (workspace_id, parcel_set_id),
        ).fetchall()
        return tuple(_member_record(row) for row in rows)

    @classmethod
    def _read_locked_record(
        cls,
        connection: Any,
        row: tuple[Any, ...],
    ) -> CaseParcelSetRecord:
        workspace_id = UUID(str(row[1]))
        parcel_set_id = UUID(str(row[0]))
        return _set_record(
            row,
            cls._read_members(
                connection,
                workspace_id=workspace_id,
                parcel_set_id=parcel_set_id,
            ),
        )

    @staticmethod
    def _lock_set(
        connection: Any,
        *,
        workspace_id: UUID,
        case_id: UUID,
        expected_version: int,
    ) -> tuple[Any, ...]:
        row = connection.execute(
            f"SELECT {', '.join(f'set_record.{column.strip()}' for column in _SET_COLUMNS.split(','))} "
            "FROM vnext_core.case_parcel_sets set_record "
            "JOIN vnext_core.cases case_record "
            "ON case_record.workspace_id = set_record.workspace_id "
            "AND case_record.case_id = set_record.case_id "
            "WHERE set_record.workspace_id = %s AND set_record.case_id = %s "
            "AND case_record.status <> 'archived' FOR UPDATE OF set_record",
            (workspace_id, case_id),
        ).fetchone()
        if row is None:
            raise VNextError.not_found()
        if int(row[4]) != expected_version:
            raise VNextError.version_conflict()
        return row

    @staticmethod
    def _complete_idempotency(
        connection: Any,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        idempotency_record_id: UUID,
        parcel_set_id: UUID,
        response_status_code: int,
    ) -> str:
        row = connection.execute(
            "UPDATE vnext_private.idempotency_records "
            "SET operation_status = 'succeeded', response_status_code = %s, "
            "response_reference_type = %s, response_reference_id = %s, "
            "updated_at = clock_timestamp() "
            "WHERE idempotency_record_id = %s AND workspace_id = %s "
            "AND actor_user_id = %s AND operation_status = 'pending' "
            "RETURNING idempotency_key_hash",
            (
                response_status_code,
                CASE_PARCEL_SET_RESPONSE_TYPE,
                parcel_set_id,
                idempotency_record_id,
                workspace_id,
                principal.user_id,
            ),
        ).fetchone()
        if row is None:
            raise VNextError.idempotency_conflict()
        return str(row[0])

    @classmethod
    def _finish(
        cls,
        connection: Any,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        idempotency_record_id: UUID,
        request_id: str,
        event_type: str,
        row: tuple[Any, ...],
        membership_role: str,
        previous_version: int,
        response_status_code: int,
        extra_metadata: dict[str, object] | None = None,
    ) -> CaseParcelSetRecord:
        parcel_set_id = UUID(str(row[0]))
        members = cls._read_members(
            connection,
            workspace_id=workspace_id,
            parcel_set_id=parcel_set_id,
        )
        key_hash = cls._complete_idempotency(
            connection,
            principal=principal,
            workspace_id=workspace_id,
            idempotency_record_id=idempotency_record_id,
            parcel_set_id=parcel_set_id,
            response_status_code=response_status_code,
        )
        metadata: dict[str, object] = {
            "parcel_set_id": str(parcel_set_id),
            "parcel_set_status": str(row[3]),
            "previous_version": previous_version,
            "new_version": int(row[4]),
            "membership_role": membership_role,
            "member_count": len(members),
        }
        metadata.update(extra_metadata or {})
        _append_audit(
            connection,
            principal=principal,
            workspace_id=workspace_id,
            event_type=event_type,
            resource_type="case_parcel_set",
            resource_id=parcel_set_id,
            request_id=_bounded_text(request_id, maximum=128),
            outcome="succeeded",
            idempotency_key_hash=key_hash,
            metadata=metadata,
        )
        return _set_record(row, members)

    def get(
        self,
        *,
        principal: AuthenticatedPrincipal,
        case_id: UUID,
    ) -> CaseParcelSetRecord:
        try:
            with self._principal_context.transaction(principal) as connection:
                row = connection.execute(
                    f"SELECT {', '.join(f'set_record.{column.strip()}' for column in _SET_COLUMNS.split(','))} "
                    "FROM vnext_core.case_parcel_sets set_record "
                    "JOIN vnext_core.cases case_record "
                    "ON case_record.workspace_id = set_record.workspace_id "
                    "AND case_record.case_id = set_record.case_id "
                    "WHERE set_record.case_id = %s AND case_record.status <> 'archived'",
                    (case_id,),
                ).fetchone()
                if row is None:
                    raise VNextError.not_found()
                return self._read_locked_record(connection, row)
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def require_case(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
    ) -> None:
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        try:
            with self._principal_context.transaction(principal) as connection:
                row = connection.execute(
                    "SELECT 1 FROM vnext_core.cases WHERE workspace_id = %s "
                    "AND case_id = %s AND status <> 'archived'",
                    (workspace_id, case_id),
                ).fetchone()
            if row is None:
                raise VNextError.not_found()
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def initialize(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        expected_version: int,
        idempotency_record_id: UUID,
        request_id: str,
    ) -> CaseParcelSetRecord:
        if expected_version != 0:
            raise VNextError.validation_failed()
        membership = self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        try:
            with self._principal_context.transaction(principal) as connection:
                case_row = connection.execute(
                    "SELECT 1 FROM vnext_core.cases WHERE workspace_id = %s "
                    "AND case_id = %s AND status <> 'archived' FOR SHARE",
                    (workspace_id, case_id),
                ).fetchone()
                if case_row is None:
                    raise VNextError.not_found()
                row = connection.execute(
                    "INSERT INTO vnext_core.case_parcel_sets "
                    "(workspace_id, case_id, created_by_user_id) "
                    f"VALUES (%s, %s, %s) RETURNING {_SET_COLUMNS}",
                    (workspace_id, case_id, principal.user_id),
                ).fetchone()
                if row is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                return self._finish(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    request_id=request_id,
                    event_type="case_parcel_set.created",
                    row=row,
                    membership_role=membership.role.value,
                    previous_version=0,
                    response_status_code=201,
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def add_member(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        parcel_identity_reference_id: UUID,
        expected_version: int,
        idempotency_record_id: UUID,
        request_id: str,
    ) -> CaseParcelSetRecord:
        membership = self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        try:
            with self._principal_context.transaction(principal) as connection:
                locked = self._lock_set(
                    connection,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    expected_version=expected_version,
                )
                parcel_set_id = UUID(str(locked[0]))
                reference = connection.execute(
                    "SELECT reference_type FROM vnext_core.property_identity_references "
                    "WHERE workspace_id = %s AND identity_reference_id = %s",
                    (workspace_id, parcel_identity_reference_id),
                ).fetchone()
                if reference is None:
                    raise VNextError.not_found()
                if str(reference[0]) != "parcel":
                    raise VNextError.validation_failed()
                position = connection.execute(
                    "SELECT count(*), coalesce(max(position), 0) "
                    "FROM vnext_core.case_parcel_set_members "
                    "WHERE workspace_id = %s AND parcel_set_id = %s",
                    (workspace_id, parcel_set_id),
                ).fetchone()
                if position is None or int(position[0]) >= 100:
                    raise VNextError.validation_failed()
                member = connection.execute(
                    "INSERT INTO vnext_core.case_parcel_set_members "
                    "(workspace_id, parcel_set_id, parcel_identity_reference_id, position, "
                    "created_by_user_id) VALUES (%s, %s, %s, %s, %s) "
                    "RETURNING parcel_set_member_id",
                    (
                        workspace_id,
                        parcel_set_id,
                        parcel_identity_reference_id,
                        int(position[1]) + 1,
                        principal.user_id,
                    ),
                ).fetchone()
                if member is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                row = connection.execute(
                    "UPDATE vnext_core.case_parcel_sets SET status = 'draft', "
                    "reviewed_at = NULL, version = version + 1, "
                    "updated_at = clock_timestamp() "
                    f"WHERE workspace_id = %s AND parcel_set_id = %s RETURNING {_SET_COLUMNS}",
                    (workspace_id, parcel_set_id),
                ).fetchone()
                if row is None:
                    raise VNextError.not_found()
                return self._finish(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    request_id=request_id,
                    event_type="case_parcel_set.member_added",
                    row=row,
                    membership_role=membership.role.value,
                    previous_version=expected_version,
                    response_status_code=200,
                    extra_metadata={"parcel_set_member_id": str(member[0])},
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def review_member(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        member_id: UUID,
        review_status: ParcelMemberReviewStatus,
        expected_version: int,
        idempotency_record_id: UUID,
        request_id: str,
    ) -> CaseParcelSetRecord:
        if not isinstance(review_status, ParcelMemberReviewStatus):
            raise VNextError.validation_failed()
        membership = self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        try:
            with self._principal_context.transaction(principal) as connection:
                locked = self._lock_set(
                    connection,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    expected_version=expected_version,
                )
                parcel_set_id = UUID(str(locked[0]))
                member = connection.execute(
                    "UPDATE vnext_core.case_parcel_set_members "
                    "SET review_status = %s, updated_at = clock_timestamp() "
                    "WHERE workspace_id = %s AND parcel_set_id = %s "
                    "AND parcel_set_member_id = %s RETURNING parcel_set_member_id",
                    (review_status.value, workspace_id, parcel_set_id, member_id),
                ).fetchone()
                if member is None:
                    raise VNextError.not_found()
                row = connection.execute(
                    "UPDATE vnext_core.case_parcel_sets SET status = 'draft', "
                    "reviewed_at = NULL, version = version + 1, "
                    "updated_at = clock_timestamp() "
                    f"WHERE workspace_id = %s AND parcel_set_id = %s RETURNING {_SET_COLUMNS}",
                    (workspace_id, parcel_set_id),
                ).fetchone()
                if row is None:
                    raise VNextError.not_found()
                return self._finish(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    request_id=request_id,
                    event_type="case_parcel_set.member_case_reviewed",
                    row=row,
                    membership_role=membership.role.value,
                    previous_version=expected_version,
                    response_status_code=200,
                    extra_metadata={
                        "parcel_set_member_id": str(member_id),
                        "review_status": review_status.value,
                    },
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def set_active_member(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        active_member_id: UUID | None,
        expected_version: int,
        idempotency_record_id: UUID,
        request_id: str,
    ) -> CaseParcelSetRecord:
        membership = self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        try:
            with self._principal_context.transaction(principal) as connection:
                locked = self._lock_set(
                    connection,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    expected_version=expected_version,
                )
                parcel_set_id = UUID(str(locked[0]))
                if active_member_id is not None:
                    member = connection.execute(
                        "SELECT 1 FROM vnext_core.case_parcel_set_members "
                        "WHERE workspace_id = %s AND parcel_set_id = %s "
                        "AND parcel_set_member_id = %s",
                        (workspace_id, parcel_set_id, active_member_id),
                    ).fetchone()
                    if member is None:
                        raise VNextError.not_found()
                row = connection.execute(
                    "UPDATE vnext_core.case_parcel_sets SET active_member_id = %s, "
                    "version = version + 1, updated_at = clock_timestamp() "
                    f"WHERE workspace_id = %s AND parcel_set_id = %s RETURNING {_SET_COLUMNS}",
                    (active_member_id, workspace_id, parcel_set_id),
                ).fetchone()
                if row is None:
                    raise VNextError.not_found()
                return self._finish(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    request_id=request_id,
                    event_type="case_parcel_set.active_member_changed",
                    row=row,
                    membership_role=membership.role.value,
                    previous_version=expected_version,
                    response_status_code=200,
                    extra_metadata={
                        "active_member_id": (
                            None if active_member_id is None else str(active_member_id)
                        )
                    },
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def reorder(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        ordered_member_ids: tuple[UUID, ...],
        expected_version: int,
        idempotency_record_id: UUID,
        request_id: str,
    ) -> CaseParcelSetRecord:
        selected_ids = tuple(ordered_member_ids)
        if not selected_ids or len(selected_ids) > 100 or len(set(selected_ids)) != len(selected_ids):
            raise VNextError.validation_failed()
        membership = self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        try:
            with self._principal_context.transaction(principal) as connection:
                locked = self._lock_set(
                    connection,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    expected_version=expected_version,
                )
                parcel_set_id = UUID(str(locked[0]))
                current = connection.execute(
                    "SELECT parcel_set_member_id FROM vnext_core.case_parcel_set_members "
                    "WHERE workspace_id = %s AND parcel_set_id = %s FOR UPDATE",
                    (workspace_id, parcel_set_id),
                ).fetchall()
                current_ids = tuple(UUID(str(row[0])) for row in current)
                if len(current_ids) != len(selected_ids) or set(current_ids) != set(selected_ids):
                    raise VNextError.validation_failed()
                connection.execute(
                    "UPDATE vnext_core.case_parcel_set_members member "
                    "SET position = ordering.position, updated_at = clock_timestamp() "
                    "FROM unnest(%s::uuid[]) WITH ORDINALITY AS ordering(member_id, position) "
                    "WHERE member.workspace_id = %s AND member.parcel_set_id = %s "
                    "AND member.parcel_set_member_id = ordering.member_id",
                    (list(selected_ids), workspace_id, parcel_set_id),
                )
                row = connection.execute(
                    "UPDATE vnext_core.case_parcel_sets SET status = 'draft', "
                    "reviewed_at = NULL, version = version + 1, "
                    "updated_at = clock_timestamp() "
                    f"WHERE workspace_id = %s AND parcel_set_id = %s RETURNING {_SET_COLUMNS}",
                    (workspace_id, parcel_set_id),
                ).fetchone()
                if row is None:
                    raise VNextError.not_found()
                return self._finish(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    request_id=request_id,
                    event_type="case_parcel_set.reordered",
                    row=row,
                    membership_role=membership.role.value,
                    previous_version=expected_version,
                    response_status_code=200,
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None

    def mark_case_reviewed(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        expected_version: int,
        idempotency_record_id: UUID,
        request_id: str,
    ) -> CaseParcelSetRecord:
        membership = self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        try:
            with self._principal_context.transaction(principal) as connection:
                locked = self._lock_set(
                    connection,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    expected_version=expected_version,
                )
                parcel_set_id = UUID(str(locked[0]))
                states = connection.execute(
                    "SELECT count(*), count(*) FILTER (WHERE review_status = 'candidate') "
                    "FROM vnext_core.case_parcel_set_members "
                    "WHERE workspace_id = %s AND parcel_set_id = %s",
                    (workspace_id, parcel_set_id),
                ).fetchone()
                if states is None or int(states[0]) == 0 or int(states[1]) != 0:
                    raise VNextError.validation_failed()
                row = connection.execute(
                    "UPDATE vnext_core.case_parcel_sets SET status = 'case_reviewed', "
                    "reviewed_at = clock_timestamp(), version = version + 1, "
                    "updated_at = clock_timestamp() "
                    f"WHERE workspace_id = %s AND parcel_set_id = %s RETURNING {_SET_COLUMNS}",
                    (workspace_id, parcel_set_id),
                ).fetchone()
                if row is None:
                    raise VNextError.not_found()
                return self._finish(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    idempotency_record_id=idempotency_record_id,
                    request_id=request_id,
                    event_type="case_parcel_set.case_reviewed",
                    row=row,
                    membership_role=membership.role.value,
                    previous_version=expected_version,
                    response_status_code=200,
                )
        except VNextError:
            raise
        except Exception as error:
            raise _translate_database_error(error) from None
