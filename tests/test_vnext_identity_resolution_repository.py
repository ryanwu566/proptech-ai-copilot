from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

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
    ResolutionInputType,
)
from services.vnext.identity_resolution_repository import (
    PostgresIdentityResolutionRepository,
)
from services.vnext.property_graph import CoverageStatus, SourceEnvironment


NOW = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
CASE_ID = UUID("aaaaaaaa-cccc-4ccc-8ccc-cccccccccccc")
EVIDENCE_ID = UUID("60000000-0000-4000-8000-000000000001")
REFERENCE_ID = UUID("30000000-0000-4000-8000-000000000001")
IDS = tuple(
    UUID(f"90000000-0000-4000-8000-{index:012d}") for index in range(1, 20)
)

PRINCIPAL = AuthenticatedPrincipal(
    user_id=USER_ID,
    token_subject=str(USER_ID),
    issuer="https://fixture.supabase.co/auth/v1",
    token_issued_at=NOW,
)


class _Memberships:
    def __init__(self, role: WorkspaceRole) -> None:
        self._role = role

    def get_active_membership(self, *, principal, workspace_id):
        if principal.user_id != USER_ID or workspace_id != WORKSPACE_ID:
            return None
        return WorkspaceMembership(WORKSPACE_ID, USER_ID, self._role)


class _Result:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, scripted=()):
        self.scripted = list(scripted)
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(self, statement, params=None):
        self.calls.append((" ".join(statement.lower().split()), params))
        return _Result(self.scripted.pop(0) if self.scripted else ())


class _Context:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.principals = []

    @contextmanager
    def transaction(self, principal):
        self.principals.append(principal)
        yield self.connection


@dataclass(frozen=True)
class _Provider:
    result: ProviderResolutionResult
    provider_id: str = "repository-fixture"
    strategy_id: str = "fixture-lookup-v1"
    source_id: str = "vnext-test"
    source_environment: SourceEnvironment = SourceEnvironment.TEST

    def resolve(self, _resolution_input):
        return self.result


def _draft():
    candidate = ProviderCandidateObservation(
        observation_id="repository-candidate",
        candidate_type=IdentityCandidateType.PARCEL,
        normalized_key="parcel:fixture-1",
        normalized_identity={"lot_number": "fixture-1"},
        display_identity="Fixture parcel 1",
        source_record_id="provider-record-1",
        retrieved_at=NOW,
        ranking_factors=CandidateRankingFactors(1, 1, 1, 1, 1, 0.9),
        coverage_status=CoverageStatus.PARTIAL,
        coverage={"geography": "fixture"},
        supporting_evidence_ids=(EVIDENCE_ID,),
        supporting_reference_ids=(REFERENCE_ID,),
    )
    provider = _Provider(
        ProviderResolutionResult(
            status=ResolutionAttemptStatus.LIMITED,
            started_at=NOW,
            completed_at=NOW,
            retrieved_at=NOW,
            coverage_status=CoverageStatus.PARTIAL,
            coverage={"scope": "fixture"},
            candidates=(candidate,),
        )
    )
    return IdentityResolutionEngine((provider,), clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市信義路1號"},
    )


def _repository(role: WorkspaceRole, connection: _Connection):
    generated = iter(IDS)
    return PostgresIdentityResolutionRepository(
        _Context(connection),
        WorkspaceAuthorizer(_Memberships(role)),
        id_factory=lambda: next(generated),
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
def test_writer_roles_atomically_append_resolution_attempt_and_candidate(role) -> None:
    connection = _Connection()
    result = _repository(role, connection).append_resolution(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_ID,
        draft=_draft(),
        case_id=CASE_ID,
    )

    assert result.identity_resolution_id == IDS[0]
    assert result.case_id == CASE_ID
    assert result.needs_human_confirmation is True
    assert result.candidates[0].identity_candidate_id == IDS[2]
    assert result.candidates[0].supporting_evidence_ids == (EVIDENCE_ID,)
    assert result.candidates[0].supporting_reference_ids == (REFERENCE_ID,)
    assert [call[0].split(" (")[0] for call in connection.calls] == [
        "insert into vnext_core.identity_resolutions",
        "insert into vnext_core.resolution_attempts",
        "insert into vnext_core.identity_candidates",
    ]
    assert not any("property_entities" in statement for statement, _ in connection.calls)
    assert not any("update vnext_core.cases" in statement for statement, _ in connection.calls)


def test_viewer_cannot_append_resolution_history() -> None:
    connection = _Connection()
    with pytest.raises(VNextError) as error:
        _repository(WorkspaceRole.VIEWER, connection).append_resolution(
            principal=PRINCIPAL,
            workspace_id=WORKSPACE_ID,
            draft=_draft(),
        )

    assert error.value.code is ErrorCode.PERMISSION_DENIED
    assert connection.calls == []


def test_reader_rehydrates_immutable_candidate_set() -> None:
    resolution_id = IDS[0]
    resolution_row = (
        resolution_id,
        WORKSPACE_ID,
        CASE_ID,
        "address",
        '{"address":"台北市信義路1號"}',
        '{"address":"台北市信義路1號"}',
        "address:台北市信義路1號",
        "identity-input-normalization-v1",
        "partially_resolved",
        "partial",
        '{"attempt_count":1}',
        "provider_limitation",
        True,
        None,
        1,
        USER_ID,
        NOW,
        NOW,
        NOW,
    )
    connection = _Connection((([resolution_row]), (), (), ()))
    result = _repository(WorkspaceRole.VIEWER, connection).get_resolution(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_ID,
        identity_resolution_id=resolution_id,
    )

    assert result.identity_resolution_id == resolution_id
    assert result.resolution_input.normalized_key == "address:台北市信義路1號"
    assert result.needs_human_confirmation is True
    assert result.attempts == ()
    assert result.candidates == ()
    assert result.conflicts == ()
    assert result.decisions == ()
    assert len(connection.calls) == 5
