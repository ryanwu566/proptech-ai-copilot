from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import (
    WorkspaceAuthorizer,
    WorkspaceMembership,
    WorkspaceRole,
)
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_resolution import (
    CandidateRankingFactors,
    IdentityCandidateType,
    IdentityResolutionEngine,
    ProviderCandidateObservation,
    ProviderResolutionResult,
    ResolutionAttemptStatus,
    ResolutionErrorCategory,
    ResolutionInputType,
)
from services.vnext.identity_resolution_repository import (
    PostgresIdentityResolutionRepository,
)
from services.vnext.identity_resolution_service import (
    IdentityResolutionApplicationService,
)
from services.vnext.persistence import IdempotencyDecision, IdempotencyReservation
from services.vnext.property_graph import CoverageStatus, SourceEnvironment

NOW = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
WORKSPACE_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
WORKSPACE_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
USER_A = UUID("11111111-1111-4111-8111-111111111111")
USER_B = UUID("22222222-2222-4222-8222-222222222222")


def _principal(user_id: UUID) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user_id,
        token_subject=str(user_id),
        issuer="https://fixture.supabase.co/auth/v1",
        token_issued_at=NOW,
    )


class _Memberships:
    def __init__(self, values: dict[tuple[UUID, UUID], WorkspaceRole]) -> None:
        self.values = values

    def get_active_membership(self, *, principal, workspace_id):
        role = self.values.get((workspace_id, principal.user_id))
        if role is None:
            return None
        return WorkspaceMembership(workspace_id, principal.user_id, role)


class _Result:
    def __init__(self, row=None) -> None:
        self.row = row

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(self, statement, params=None):
        selected = " ".join(statement.lower().split())
        self.calls.append((selected, params))
        if selected.startswith("update vnext_private.idempotency_records"):
            return _Result((params[3],))
        return _Result()


class _Context:
    def __init__(self) -> None:
        self.connection = _Connection()

    @contextmanager
    def transaction(self, _principal):
        yield self.connection


class _MemoryIdempotency:
    def __init__(self, authorizer: WorkspaceAuthorizer) -> None:
        self.authorizer = authorizer
        self.by_scope: dict[tuple[object, ...], IdempotencyReservation] = {}
        self.by_id: dict[UUID, tuple[object, ...]] = {}

    def reserve(self, **kwargs):
        principal = kwargs["principal"]
        workspace_id = kwargs["workspace_id"]
        self.authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles={
                WorkspaceRole.OWNER,
                WorkspaceRole.ADMIN,
                WorkspaceRole.MANAGER,
                WorkspaceRole.MEMBER,
            },
        )
        fingerprint = hashlib.sha256(kwargs["canonical_request"]).hexdigest()
        scope = (
            workspace_id,
            principal.user_id,
            kwargs["method"],
            kwargs["canonical_route"],
            hashlib.sha256(kwargs["idempotency_key"].encode()).hexdigest(),
        )
        existing = self.by_scope.get(scope)
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise VNextError.idempotency_conflict()
            return IdempotencyReservation(
                **{**existing.__dict__, "decision": IdempotencyDecision.REPLAY}
            )
        reservation = IdempotencyReservation(
            decision=IdempotencyDecision.NEW,
            idempotency_record_id=uuid4(),
            request_fingerprint=fingerprint,
            operation_status="pending",
            response_reference_type=None,
            response_reference_id=None,
        )
        self.by_scope[scope] = reservation
        self.by_id[reservation.idempotency_record_id] = scope
        return reservation

    def complete(
        self, record_id: UUID, *, reference_id: UUID, status_code: int
    ) -> None:
        scope = self.by_id[record_id]
        existing = self.by_scope[scope]
        self.by_scope[scope] = IdempotencyReservation(
            decision=existing.decision,
            idempotency_record_id=record_id,
            request_fingerprint=existing.request_fingerprint,
            operation_status="succeeded" if status_code < 400 else "failed",
            response_reference_type="identity_resolution",
            response_reference_id=reference_id,
            response_status_code=status_code,
        )

    def mark_failed(self, **kwargs):
        record_id = kwargs["idempotency_record_id"]
        scope = self.by_id[record_id]
        existing = self.by_scope[scope]
        self.by_scope[scope] = IdempotencyReservation(
            decision=existing.decision,
            idempotency_record_id=record_id,
            request_fingerprint=existing.request_fingerprint,
            operation_status="failed",
            response_reference_type=None,
            response_reference_id=None,
            response_status_code=kwargs["response_status_code"],
            response_error_code=kwargs["response_error_code"],
        )


class _MemoryResolutions:
    def __init__(self, inner, idempotency, authorizer) -> None:
        self.inner = inner
        self.idempotency = idempotency
        self.authorizer = authorizer
        self.records = {}
        self.append_count = 0

    def append_resolution(self, **kwargs):
        record = self.inner.append_resolution(**kwargs)
        self.records[record.identity_resolution_id] = record
        self.append_count += 1
        self.idempotency.complete(
            kwargs["idempotency_record_id"],
            reference_id=record.identity_resolution_id,
            status_code=kwargs["idempotency_response_status_code"],
        )
        return record

    def get_resolution_by_id(self, *, principal, identity_resolution_id):
        record = self.records.get(identity_resolution_id)
        if record is None:
            raise VNextError.not_found()
        try:
            self.authorizer.require_workspace_access(principal, record.workspace_id)
        except VNextError:
            raise VNextError.not_found() from None
        return record


class _Cases:
    def get_case(self, **_kwargs):
        return object()


@dataclass(frozen=True)
class _Provider:
    result: ProviderResolutionResult
    provider_id: str = "slice-5-test-provider"
    strategy_id: str = "slice-5-test-v1"
    source_id: str = "vnext-test"
    source_environment: SourceEnvironment = SourceEnvironment.TEST

    def resolve(self, _resolution_input):
        return self.result


def _candidate(observation_id: str = "candidate-1", *, confidence: float = 1.0):
    return ProviderCandidateObservation(
        observation_id=observation_id,
        candidate_type=IdentityCandidateType.ADDRESS,
        normalized_key=f"address:{observation_id}",
        normalized_identity={"address": observation_id},
        display_identity=observation_id,
        source_record_id=observation_id,
        retrieved_at=NOW,
        ranking_factors=CandidateRankingFactors(
            confidence,
            confidence,
            confidence,
            confidence,
            confidence,
            confidence,
        ),
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
    )


def _service(result: ProviderResolutionResult | None, memberships=None):
    values = (
        {(WORKSPACE_A, USER_A): WorkspaceRole.MEMBER}
        if memberships is None
        else memberships
    )
    authorizer = WorkspaceAuthorizer(_Memberships(values))
    context = _Context()
    ids = (UUID(int=index) for index in range(1, 100))
    inner = PostgresIdentityResolutionRepository(
        context,
        authorizer,
        id_factory=lambda: next(ids),
    )
    idempotency = _MemoryIdempotency(authorizer)
    repository = _MemoryResolutions(inner, idempotency, authorizer)
    providers = () if result is None else (_Provider(result),)
    service = IdentityResolutionApplicationService(
        authorizer=authorizer,
        engine=IdentityResolutionEngine(providers, clock=lambda: NOW),
        resolution_repository=repository,
        idempotency_repository=idempotency,
        case_repository=_Cases(),
        runtime_environment="test",
    )
    return service, repository, idempotency, context


def _create(
    service,
    *,
    key="resolution-key-0001",
    workspace_id=WORKSPACE_A,
    principal=None,
    text="one",
):
    return service.create(
        principal=principal or _principal(USER_A),
        workspace_id=workspace_id,
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": text},
        case_id=None,
        idempotency_key=key,
    )


def test_clear_candidate_is_persisted_once_and_replayed_without_confirmation() -> None:
    result = ProviderResolutionResult(
        status=ResolutionAttemptStatus.AVAILABLE,
        started_at=NOW,
        completed_at=NOW,
        retrieved_at=NOW,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
        candidates=(_candidate(),),
    )
    service, repository, _idempotency, context = _service(result)

    first = _create(service)
    replay = _create(service)

    assert first.status_code == replay.status_code == 201
    assert (
        first.resolution.identity_resolution_id
        == replay.resolution.identity_resolution_id
    )
    assert repository.append_count == 1
    assert first.resolution.needs_human_confirmation is True
    assert first.resolution.candidates[0].confidence == 1.0
    assert first.resolution.candidates[0].needs_human_confirmation is True
    assert not any(
        "property_entities" in statement for statement, _ in context.connection.calls
    )


def test_same_key_with_different_request_conflicts() -> None:
    result = ProviderResolutionResult(
        status=ResolutionAttemptStatus.NO_MATCH,
        started_at=NOW,
        completed_at=NOW,
        retrieved_at=NOW,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
    )
    service, repository, _idempotency, _context = _service(result)
    _create(service, text="one")

    with pytest.raises(VNextError) as error:
        _create(service, text="two")

    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert repository.append_count == 1


def test_key_scope_is_independent_by_workspace_and_actor() -> None:
    result = ProviderResolutionResult(
        status=ResolutionAttemptStatus.NO_MATCH,
        started_at=NOW,
        completed_at=NOW,
        retrieved_at=NOW,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
    )
    memberships = {
        (WORKSPACE_A, USER_A): WorkspaceRole.MEMBER,
        (WORKSPACE_B, USER_A): WorkspaceRole.MEMBER,
        (WORKSPACE_A, USER_B): WorkspaceRole.MEMBER,
    }
    service, repository, _idempotency, _context = _service(result, memberships)

    _create(service, key="same-resolution-key", workspace_id=WORKSPACE_A)
    _create(service, key="same-resolution-key", workspace_id=WORKSPACE_B)
    _create(
        service,
        key="same-resolution-key",
        workspace_id=WORKSPACE_A,
        principal=_principal(USER_B),
    )

    assert repository.append_count == 3


def test_no_provider_persists_safe_unresolved_attempt_and_replays_503() -> None:
    service, repository, _idempotency, _context = _service(None)

    for _ in range(2):
        with pytest.raises(VNextError) as error:
            _create(service)
        assert error.value.code is ErrorCode.PROVIDER_UNAVAILABLE

    assert repository.append_count == 1
    record = next(iter(repository.records.values()))
    assert record.status.value == "unresolved"
    assert record.candidates == ()
    assert record.attempts[0].error_category is ResolutionErrorCategory.NOT_CONFIGURED


@pytest.mark.parametrize("role", [WorkspaceRole.VIEWER, None])
def test_viewer_and_nonmember_cannot_start_resolution(role) -> None:
    memberships = {} if role is None else {(WORKSPACE_A, USER_A): role}
    service, repository, _idempotency, _context = _service(None, memberships)

    with pytest.raises(VNextError) as error:
        _create(service)

    assert error.value.code is ErrorCode.PERMISSION_DENIED
    assert repository.append_count == 0
