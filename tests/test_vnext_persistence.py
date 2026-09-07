from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import (
    PostgresWorkspaceMembershipRepository,
    WorkspaceAuthorizer,
    WorkspaceMembership,
    WorkspaceMembershipStatus,
    WorkspaceRole,
)
from services.vnext.errors import VNextError
from services.vnext.persistence import (
    CasePurpose,
    CaseStatus,
    IdempotencyDecision,
    PostgresAuditRepository,
    PostgresCaseRepository,
    PostgresIdempotencyRepository,
)


USER_A = UUID("11111111-1111-4111-8111-111111111111")
USER_B = UUID("22222222-2222-4222-8222-222222222222")
WORKSPACE_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
WORKSPACE_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
CASE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
IDEMPOTENCY_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
NOW = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _principal(user_id: UUID) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user_id,
        token_subject=str(user_id),
        issuer="https://fixture.supabase.co/auth/v1",
        token_issued_at=NOW,
    )


PRINCIPAL_A = _principal(USER_A)
PRINCIPAL_B = _principal(USER_B)


class _Memberships:
    def __init__(self, memberships: list[WorkspaceMembership]) -> None:
        self._memberships = {
            (membership.workspace_id, membership.user_id): membership
            for membership in memberships
        }

    def get_active_membership(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> WorkspaceMembership | None:
        return self._memberships.get((workspace_id, principal.user_id))


def _authorizer(
    role: WorkspaceRole = WorkspaceRole.MEMBER,
    *,
    workspaces: tuple[UUID, ...] = (WORKSPACE_A,),
    principal: AuthenticatedPrincipal = PRINCIPAL_A,
    status: WorkspaceMembershipStatus = WorkspaceMembershipStatus.ACTIVE,
) -> WorkspaceAuthorizer:
    return WorkspaceAuthorizer(
        _Memberships(
            [
                WorkspaceMembership(
                    workspace_id,
                    principal.user_id,
                    role,
                    status,
                )
                for workspace_id in workspaces
            ]
        )
    )


class _Result:
    def __init__(self, row: tuple[object, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[object, ...] | None:
        return self._row


class _Connection:
    def __init__(self, rows: list[tuple[object, ...] | None]) -> None:
        self._rows = list(rows)
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(
        self,
        statement: str,
        params: tuple[object, ...] | None = None,
    ) -> _Result:
        self.calls.append((" ".join(statement.lower().split()), params))
        if not self._rows:
            raise AssertionError(f"no scripted result for: {statement}")
        return _Result(self._rows.pop(0))


class _Context:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.principals: list[AuthenticatedPrincipal] = []

    @contextmanager
    def transaction(self, principal: AuthenticatedPrincipal):
        self.principals.append(principal)
        yield self.connection


def _case_row(
    *,
    version: int = 1,
    title: str = "Unverified investigation",
    status: str = "open",
) -> tuple[object, ...]:
    return (
        CASE_ID,
        WORKSPACE_A,
        "buy_due_diligence",
        status,
        title,
        "unverified",
        None,
        version,
        NOW,
        NOW,
        NOW if status == "closed" else None,
        NOW if status == "archived" else None,
    )


def test_postgres_membership_repository_uses_validated_principal() -> None:
    connection = _Connection(
        [(WORKSPACE_A, USER_A, "manager", "active")]
    )
    context = _Context(connection)
    repository = PostgresWorkspaceMembershipRepository(lambda: context)

    membership = repository.get_active_membership(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
    )

    assert membership == WorkspaceMembership(
        WORKSPACE_A,
        USER_A,
        WorkspaceRole.MANAGER,
        WorkspaceMembershipStatus.ACTIVE,
    )
    assert connection.calls[0][1] == (WORKSPACE_A, USER_A)
    assert context.principals == [PRINCIPAL_A]


@pytest.mark.parametrize("status", ["invited", "suspended", "left", "removed"])
def test_postgres_membership_repository_denies_inactive_rows(status: str) -> None:
    connection = _Connection([(WORKSPACE_A, USER_A, "owner", status)])
    repository = PostgresWorkspaceMembershipRepository(lambda: _Context(connection))

    assert (
        repository.get_active_membership(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
        )
        is None
    )


@pytest.mark.parametrize(
    "role",
    [
        WorkspaceRole.MEMBER,
        WorkspaceRole.MANAGER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.OWNER,
    ],
)
def test_case_create_without_property_entity_is_allowed_for_writers(
    role: WorkspaceRole,
) -> None:
    connection = _Connection([_case_row(), None])
    context = _Context(connection)
    repository = PostgresCaseRepository(context, _authorizer(role))

    case = repository.create_case(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
        purpose=CasePurpose.BUY_DUE_DILIGENCE,
        title="  Unverified investigation  ",
        request_id="request-create-case",
    )

    assert case.case_id == CASE_ID
    assert case.identity_status.value == "unverified"
    assert case.version == 1
    assert "property_entity_id" not in connection.calls[0][0]
    assert connection.calls[0][1] == (
        WORKSPACE_A,
        "buy_due_diligence",
        "Unverified investigation",
        USER_A,
    )
    audit_params = connection.calls[1][1]
    assert audit_params is not None
    assert audit_params[1:3] == (WORKSPACE_A, USER_A)
    assert audit_params[3:7] == (
        "case.created",
        "case",
        CASE_ID,
        "request-create-case",
    )


def test_viewer_and_revoked_member_cannot_create_case() -> None:
    for authorizer in (
        _authorizer(WorkspaceRole.VIEWER),
        _authorizer(WorkspaceRole.OWNER, status=WorkspaceMembershipStatus.REMOVED),
    ):
        context = _Context(_Connection([]))
        repository = PostgresCaseRepository(context, authorizer)

        with pytest.raises(VNextError) as error:
            repository.create_case(
                principal=PRINCIPAL_A,
                workspace_id=WORKSPACE_A,
                purpose=CasePurpose.BUY_DUE_DILIGENCE,
                title="Denied",
                request_id="request-denied",
            )

        assert error.value.code.value == "permission_denied"
        assert context.principals == []


@pytest.mark.parametrize("role", list(WorkspaceRole))
def test_every_active_workspace_role_can_read_case(role: WorkspaceRole) -> None:
    repository = PostgresCaseRepository(
        _Context(_Connection([_case_row()])),
        _authorizer(role),
    )

    case = repository.get_case(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
        case_id=CASE_ID,
    )

    assert case.case_id == CASE_ID


def test_no_membership_denies_case_read_create_and_update() -> None:
    context = _Context(_Connection([]))
    repository = PostgresCaseRepository(
        context,
        WorkspaceAuthorizer(_Memberships([])),
    )

    operations = (
        lambda: repository.get_case(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
            case_id=CASE_ID,
        ),
        lambda: repository.create_case(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
            purpose=CasePurpose.BUY_DUE_DILIGENCE,
            title="Denied",
            request_id="request-denied",
        ),
        lambda: repository.update_case(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
            case_id=CASE_ID,
            expected_version=1,
            purpose=CasePurpose.BUY_DUE_DILIGENCE,
            status=CaseStatus.OPEN,
            title="Denied",
            request_id="request-denied",
        ),
    )
    for operation in operations:
        with pytest.raises(VNextError) as error:
            operation()
        assert error.value.code.value == "permission_denied"
    assert context.principals == []


def test_viewer_cannot_update_case() -> None:
    context = _Context(_Connection([]))
    repository = PostgresCaseRepository(
        context,
        _authorizer(WorkspaceRole.VIEWER),
    )

    with pytest.raises(VNextError) as error:
        repository.update_case(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
            case_id=CASE_ID,
            expected_version=1,
            purpose=CasePurpose.BUY_DUE_DILIGENCE,
            status=CaseStatus.OPEN,
            title="Denied",
            request_id="request-denied",
        )

    assert error.value.code.value == "permission_denied"
    assert context.principals == []


def test_case_read_and_optimistic_update() -> None:
    connection = _Connection(
        [
            _case_row(),
            _case_row(version=2, title="Reviewed", status="in_progress"),
            None,
        ]
    )
    context = _Context(connection)
    repository = PostgresCaseRepository(context, _authorizer())

    original = repository.get_case(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
        case_id=CASE_ID,
    )
    updated = repository.update_case(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
        case_id=CASE_ID,
        expected_version=1,
        purpose=CasePurpose.BUY_DUE_DILIGENCE,
        status=CaseStatus.IN_PROGRESS,
        title="Reviewed",
        request_id="request-update-case",
    )

    assert original.version == 1
    assert updated.version == 2
    assert updated.title == "Reviewed"
    assert "workspace_id = %s and case_id = %s and version = %s" in connection.calls[1][0]
    assert "workspace_id =" not in connection.calls[1][0].split(" set ", 1)[1].split(" where ", 1)[0]


def test_case_version_conflict_and_hidden_cross_workspace_case() -> None:
    conflict = PostgresCaseRepository(
        _Context(_Connection([None, (2,)])),
        _authorizer(),
    )
    with pytest.raises(VNextError) as error:
        conflict.update_case(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
            case_id=CASE_ID,
            expected_version=1,
            purpose=CasePurpose.BUY_DUE_DILIGENCE,
            status=CaseStatus.OPEN,
            title="Stale",
            request_id="request-stale",
        )
    assert error.value.code.value == "version_conflict"

    hidden = PostgresCaseRepository(
        _Context(_Connection([None])),
        _authorizer(workspaces=(WORKSPACE_A, WORKSPACE_B)),
    )
    with pytest.raises(VNextError) as error:
        hidden.get_case(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_B,
            case_id=CASE_ID,
        )
    assert error.value.code.value == "not_found"


def test_idempotency_same_key_same_request_replays() -> None:
    canonical_request = b'{"purpose":"buy_due_diligence"}'
    fingerprint = hashlib.sha256(canonical_request).hexdigest()
    stored = (IDEMPOTENCY_ID, fingerprint, "pending", None, None)
    connection = _Connection([stored, None, stored])
    repository = PostgresIdempotencyRepository(
        _Context(connection),
        _authorizer(),
    )

    first = repository.reserve(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
        method="POST",
        canonical_route="/v1/cases",
        idempotency_key="case-create-key-0001",
        canonical_request=canonical_request,
    )
    second = repository.reserve(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
        method="POST",
        canonical_route="/v1/cases",
        idempotency_key="case-create-key-0001",
        canonical_request=canonical_request,
    )

    assert first.decision == IdempotencyDecision.NEW
    assert second.decision == IdempotencyDecision.REPLAY
    insert_params = connection.calls[0][1]
    assert insert_params is not None
    assert "case-create-key-0001" not in repr(insert_params)
    assert canonical_request.decode() not in repr(insert_params)


def test_idempotency_same_key_different_request_conflicts() -> None:
    stored = (IDEMPOTENCY_ID, "0" * 64, "pending", None, None)
    repository = PostgresIdempotencyRepository(
        _Context(_Connection([None, stored])),
        _authorizer(),
    )

    with pytest.raises(VNextError) as error:
        repository.reserve(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
            method="POST",
            canonical_route="/v1/cases",
            idempotency_key="case-create-key-0001",
            canonical_request=b"different request",
        )

    assert error.value.code.value == "idempotency_conflict"


def test_idempotency_scope_keeps_workspace_and_actor_distinct() -> None:
    fingerprint = hashlib.sha256(b"same").hexdigest()
    connection = _Connection(
        [
            (IDEMPOTENCY_ID, fingerprint, "pending", None, None),
            (
                UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
                fingerprint,
                "pending",
                None,
                None,
            ),
        ]
    )
    context = _Context(connection)
    repository_a = PostgresIdempotencyRepository(
        context,
        _authorizer(workspaces=(WORKSPACE_A, WORKSPACE_B)),
    )
    repository_b = PostgresIdempotencyRepository(
        context,
        _authorizer(
            principal=PRINCIPAL_B,
            workspaces=(WORKSPACE_A,),
        ),
    )

    repository_a.reserve(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_B,
        method="POST",
        canonical_route="/v1/cases",
        idempotency_key="same-scope-key-0001",
        canonical_request=b"same",
    )
    repository_b.reserve(
        principal=PRINCIPAL_B,
        workspace_id=WORKSPACE_A,
        method="POST",
        canonical_route="/v1/cases",
        idempotency_key="same-scope-key-0001",
        canonical_request=b"same",
    )

    assert connection.calls[0][1][1:3] == (WORKSPACE_B, USER_A)
    assert connection.calls[1][1][1:3] == (WORKSPACE_A, USER_B)


def test_audit_append_has_canonical_actor_and_workspace() -> None:
    connection = _Connection([None])
    repository = PostgresAuditRepository(_Context(connection), _authorizer())

    event = repository.append(
        principal=PRINCIPAL_A,
        workspace_id=WORKSPACE_A,
        event_type="case.read_sensitive",
        resource_type="case",
        resource_id=CASE_ID,
        request_id="request-audit",
        metadata={"operation_status": "authorized"},
    )

    assert event.workspace_id == WORKSPACE_A
    assert event.actor_user_id == USER_A
    params = connection.calls[0][1]
    assert params is not None
    assert params[1:7] == (
        WORKSPACE_A,
        USER_A,
        "case.read_sensitive",
        "case",
        CASE_ID,
        "request-audit",
    )


def test_audit_rejects_unbounded_or_unapproved_metadata() -> None:
    repository = PostgresAuditRepository(_Context(_Connection([])), _authorizer())

    with pytest.raises(VNextError) as error:
        repository.append(
            principal=PRINCIPAL_A,
            workspace_id=WORKSPACE_A,
            event_type="case.updated",
            resource_type="case",
            resource_id=CASE_ID,
            request_id="request-audit",
            metadata={"raw_authorization_header": "Bearer secret"},
        )

    assert error.value.code.value == "validation_failed"
