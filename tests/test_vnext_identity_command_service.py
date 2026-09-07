from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import (WorkspaceAuthorizer,
                                          WorkspaceMembership, WorkspaceRole)
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_command_repository import (
    AttachmentWriteResult, CasePropertyLinkRecord, ConfirmationWriteResult)
from services.vnext.identity_command_service import \
    IdentityCommandApplicationService
from services.vnext.identity_resolution import (AmbiguityStatus,
                                                IdentityCandidateStatus,
                                                IdentityCandidateType,
                                                ResolutionInputType,
                                                ResolutionStatus,
                                                normalize_resolution_input)
from services.vnext.identity_resolution_repository import (
    IdentityCandidateRecord, IdentityDecisionRecord, IdentityResolutionRecord)
from services.vnext.persistence import (CaseIdentityStatus, CasePurpose,
                                        CaseRecord, CaseStatus,
                                        IdempotencyDecision,
                                        IdempotencyReservation)
from services.vnext.property_graph import (CoverageStatus, SourceEnvironment,
                                           SourceType)

NOW = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
RESOLUTION_ID = UUID("aaaaaaaa-1111-4111-8111-111111111111")
CANDIDATE_1 = UUID("aaaaaaaa-2222-4222-8222-222222222221")
CANDIDATE_2 = UUID("aaaaaaaa-2222-4222-8222-222222222222")
EVIDENCE_ID = UUID("aaaaaaaa-3333-4333-8333-333333333333")
REFERENCE_ID = UUID("aaaaaaaa-4444-4444-8444-444444444444")
PROPERTY_ID = UUID("aaaaaaaa-5555-4555-8555-555555555555")
CASE_ID = UUID("aaaaaaaa-6666-4666-8666-666666666666")
USER_ID = UUID("10000000-0000-4000-8000-000000000001")


def _principal(user_id: UUID = USER_ID) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id, str(user_id), "http://localhost/auth/v1", NOW)


class _Memberships:
    def __init__(self, role: WorkspaceRole | None) -> None:
        self.role = role

    def get_active_membership(self, *, principal, workspace_id):
        if self.role is None or workspace_id != WORKSPACE_ID:
            return None
        return WorkspaceMembership(workspace_id, principal.user_id, self.role)


def _candidate(candidate_id: UUID, rank: int, confidence: float) -> IdentityCandidateRecord:
    return IdentityCandidateRecord(
        identity_candidate_id=candidate_id,
        workspace_id=WORKSPACE_ID,
        identity_resolution_id=RESOLUTION_ID,
        candidate_type=IdentityCandidateType.ADDRESS,
        normalized_key=f"address:fixture-{rank}",
        normalized_identity={"address": f"Fixture {rank}"},
        display_identity=f"Fixture {rank}",
        source_id="vnext-deterministic",
        source_type=SourceType.DETERMINISTIC,
        source_environment=SourceEnvironment.PRODUCTION,
        source_record_id=f"fixture-{rank}",
        retrieved_at=NOW,
        confidence=confidence,
        confidence_method="identity-ranking-v1",
        ranking_factors={"rank": rank},
        rank=rank,
        candidate_status=IdentityCandidateStatus.PLAUSIBLE,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
        supporting_evidence_ids=(EVIDENCE_ID,),
        supporting_reference_ids=(REFERENCE_ID,),
        possible_existing_property_entity_id=None,
        supersedes_candidate_id=None,
        needs_human_confirmation=True,
        created_by_user_id=USER_ID,
        created_at=NOW,
    )


def _resolution() -> IdentityResolutionRecord:
    return IdentityResolutionRecord(
        identity_resolution_id=RESOLUTION_ID,
        workspace_id=WORKSPACE_ID,
        case_id=CASE_ID,
        resolution_input=normalize_resolution_input(
            ResolutionInputType.ADDRESS, {"address": "Fixture"}
        ),
        status=ResolutionStatus.AMBIGUOUS,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
        ambiguity_status=AmbiguityStatus.MULTIPLE_CANDIDATES,
        needs_human_confirmation=True,
        supersedes_resolution_id=None,
        version=1,
        requested_by_user_id=USER_ID,
        started_at=NOW,
        completed_at=NOW,
        created_at=NOW,
        attempts=(),
        candidates=(
            _candidate(CANDIDATE_1, 1, 1.0),
            _candidate(CANDIDATE_2, 2, 0.8),
        ),
        conflicts=(),
    )


class _Idempotency:
    def __init__(self) -> None:
        self.records = {}
        self.ids = {}

    def reserve(self, **kwargs):
        fingerprint = hashlib.sha256(kwargs["canonical_request"]).hexdigest()
        scope = (
            kwargs["workspace_id"],
            kwargs["principal"].user_id,
            kwargs["method"],
            kwargs["canonical_route"],
            hashlib.sha256(kwargs["idempotency_key"].encode()).hexdigest(),
        )
        existing = self.records.get(scope)
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise VNextError.idempotency_conflict()
            return replace(existing, decision=IdempotencyDecision.REPLAY)
        record = IdempotencyReservation(
            IdempotencyDecision.NEW,
            uuid4(),
            fingerprint,
            "pending",
            None,
            None,
        )
        self.records[scope] = record
        self.ids[record.idempotency_record_id] = scope
        return record

    def complete(self, record_id, reference_type, reference_id, status_code):
        scope = self.ids[record_id]
        self.records[scope] = replace(
            self.records[scope],
            operation_status="succeeded",
            response_reference_type=reference_type,
            response_reference_id=reference_id,
            response_status_code=status_code,
        )

    def mark_failed(self, **kwargs):
        record_id = kwargs["idempotency_record_id"]
        scope = self.ids[record_id]
        self.records[scope] = replace(
            self.records[scope],
            operation_status="failed",
            response_status_code=kwargs["response_status_code"],
            response_error_code=kwargs["response_error_code"],
        )


class _Resolutions:
    def __init__(self, authorizer) -> None:
        self.authorizer = authorizer
        self.record = _resolution()

    def get_resolution_by_id(self, *, principal, identity_resolution_id):
        if identity_resolution_id != RESOLUTION_ID:
            raise VNextError.not_found()
        self.authorizer.require_workspace_access(principal, WORKSPACE_ID)
        return self.record

    def get_decision_by_id(self, *, principal, identity_decision_id):
        self.authorizer.require_workspace_access(principal, WORKSPACE_ID)
        decision = next(
            (item for item in self.record.decisions if item.identity_decision_id == identity_decision_id),
            None,
        )
        if decision is None:
            raise VNextError.not_found()
        return decision


class _Cases:
    def __init__(self, authorizer, idempotency) -> None:
        self.authorizer = authorizer
        self.idempotency = idempotency
        self.record = CaseRecord(
            CASE_ID,
            WORKSPACE_ID,
            CasePurpose.BUY_DUE_DILIGENCE,
            CaseStatus.OPEN,
            "Fixture Case",
            CaseIdentityStatus.UNVERIFIED,
            None,
            1,
            NOW,
            NOW,
            None,
            None,
        )
        self.create_count = 0

    def get_case_by_id(self, *, principal, case_id):
        if case_id != CASE_ID:
            raise VNextError.not_found()
        self.authorizer.require_workspace_access(principal, WORKSPACE_ID)
        return self.record

    def create_case(self, **kwargs):
        self.create_count += 1
        self.idempotency.complete(
            kwargs["idempotency_record_id"], "case", CASE_ID, 201
        )
        return self.record


def _decision(candidate, decision_type, version, principal, reason=None):
    return IdentityDecisionRecord(
        identity_decision_id=uuid4(),
        workspace_id=WORKSPACE_ID,
        identity_resolution_id=RESOLUTION_ID,
        identity_candidate_id=None if candidate is None else candidate.identity_candidate_id,
        property_entity_id=PROPERTY_ID if decision_type == "confirmed" else None,
        materialized_identity_reference_id=(
            REFERENCE_ID if decision_type == "confirmed" else None
        ),
        primary_evidence_id=EVIDENCE_ID if decision_type == "confirmed" else None,
        decision_type=decision_type,
        decision_reason=reason,
        reason_code=None if decision_type == "confirmed" else "not_same_property",
        resolution_version_observed=version,
        decision_version=version + 1,
        candidate_type_snapshot=None if candidate is None else candidate.candidate_type.value,
        candidate_status_snapshot=None if candidate is None else candidate.candidate_status.value,
        confidence_snapshot=None if candidate is None else candidate.confidence,
        confidence_method_snapshot=None if candidate is None else candidate.confidence_method,
        coverage_status_snapshot=(
            CoverageStatus.KNOWN if candidate is None else candidate.coverage_status
        ),
        coverage_snapshot={"scope": "fixture"},
        supporting_evidence_ids_snapshot=() if candidate is None else (EVIDENCE_ID,),
        supporting_reference_ids_snapshot=() if candidate is None else (REFERENCE_ID,),
        source_id_snapshot=None if candidate is None else candidate.source_id,
        source_type_snapshot=None if candidate is None else candidate.source_type,
        source_environment_snapshot=(None if candidate is None else candidate.source_environment),
        source_record_id_snapshot=None if candidate is None else candidate.source_record_id,
        created_new_property=False if decision_type == "confirmed" else None,
        created_new_reference=False if decision_type == "confirmed" else None,
        actor_user_id=principal.user_id,
        request_id="request-fixture",
        idempotency_record_id=uuid4(),
        created_at=NOW,
    )


class _Commands:
    def __init__(self, resolutions, cases, idempotency) -> None:
        self.resolutions = resolutions
        self.cases = cases
        self.idempotency = idempotency
        self.confirm_count = 0
        self.reject_count = 0
        self.attach_count = 0
        self.property_count = 0
        self.links = {}

    def confirm(self, **kwargs):
        current = self.resolutions.record
        if kwargs["expected_version"] != 1 + len(current.decisions) or any(
            item.decision_type in {"confirmed", "resolution_rejected"}
            for item in current.decisions
        ):
            raise VNextError.version_conflict()
        if any(
            item.decision_type == "candidate_rejected"
            and item.identity_candidate_id == kwargs["identity_candidate_id"]
            for item in current.decisions
        ):
            raise VNextError.version_conflict()
        candidate = next(
            item
            for item in current.candidates
            if item.identity_candidate_id == kwargs["identity_candidate_id"]
        )
        decision = _decision(
            candidate,
            "confirmed",
            kwargs["expected_version"],
            kwargs["principal"],
            kwargs["confirmation_reason"],
        )
        self.confirm_count += 1
        self.property_count += 1
        self.resolutions.record = replace(current, decisions=(*current.decisions, decision))
        self.idempotency.complete(
            kwargs["idempotency_record_id"],
            "identity_decision",
            decision.identity_decision_id,
            200,
        )
        return ConfirmationWriteResult(decision, PROPERTY_ID, REFERENCE_ID, uuid4())

    def reject(self, **kwargs):
        current = self.resolutions.record
        if kwargs["expected_version"] != 1 + len(current.decisions):
            raise VNextError.version_conflict()
        candidate = next(
            (
                item
                for item in current.candidates
                if item.identity_candidate_id == kwargs["identity_candidate_id"]
            ),
            None,
        )
        decision = _decision(
            candidate,
            "candidate_rejected" if candidate else "resolution_rejected",
            kwargs["expected_version"],
            kwargs["principal"],
        )
        self.reject_count += 1
        self.resolutions.record = replace(current, decisions=(*current.decisions, decision))
        self.idempotency.complete(
            kwargs["idempotency_record_id"],
            "identity_decision",
            decision.identity_decision_id,
            200,
        )
        return decision

    def attach_resolution(self, **kwargs):
        if kwargs["expected_case_version"] != self.cases.record.version:
            raise VNextError.version_conflict()
        link = CasePropertyLinkRecord(
            uuid4(),
            WORKSPACE_ID,
            CASE_ID,
            PROPERTY_ID,
            RESOLUTION_ID,
            kwargs["identity_confirmation_id"],
            kwargs["principal"].user_id,
            self.cases.record.version,
            self.cases.record.version + 1,
            next(reversed(self.links), None),
            kwargs["request_id"],
            kwargs["idempotency_record_id"],
            NOW,
        )
        self.attach_count += 1
        self.cases.record = replace(
            self.cases.record,
            identity_status=CaseIdentityStatus.CONFIRMED,
            version=self.cases.record.version + 1,
        )
        self.links[link.case_property_link_id] = link
        self.idempotency.complete(
            kwargs["idempotency_record_id"],
            "case_property_link",
            link.case_property_link_id,
            200,
        )
        return AttachmentWriteResult(self.cases.record, link)

    def get_case_property_link_by_id(self, *, case_property_link_id, **_kwargs):
        return self.links[case_property_link_id]


def _service(role: WorkspaceRole | None):
    authorizer = WorkspaceAuthorizer(_Memberships(role))
    idempotency = _Idempotency()
    resolutions = _Resolutions(authorizer)
    cases = _Cases(authorizer, idempotency)
    commands = _Commands(resolutions, cases, idempotency)
    service = IdentityCommandApplicationService(
        authorizer=authorizer,
        resolution_repository=resolutions,
        command_repository=commands,
        idempotency_repository=idempotency,
        case_repository=cases,
    )
    return service, resolutions, commands, cases


def test_explicit_rank_two_confirmation_is_idempotent_and_not_confidence_driven() -> None:
    service, _resolutions, commands, _cases = _service(WorkspaceRole.OWNER)

    first = service.confirm(
        principal=_principal(),
        identity_resolution_id=RESOLUTION_ID,
        identity_candidate_id=CANDIDATE_2,
        expected_version=1,
        confirmation_reason="human reviewed the displayed evidence",
        idempotency_key="confirmation-key-0001",
        request_id="request-1",
    )
    replay = service.confirm(
        principal=_principal(),
        identity_resolution_id=RESOLUTION_ID,
        identity_candidate_id=CANDIDATE_2,
        expected_version=1,
        confirmation_reason="human reviewed the displayed evidence",
        idempotency_key="confirmation-key-0001",
        request_id="request-2",
    )

    assert first.decision.identity_candidate_id == CANDIDATE_2
    assert first.resolution.candidates[0].confidence == 1.0
    assert first.resolution.candidates[0].identity_candidate_id == CANDIDATE_1
    assert replay.replayed is True
    assert commands.confirm_count == 1
    assert commands.property_count == 1


@pytest.mark.parametrize(
    "role",
    [WorkspaceRole.MANAGER, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER, None],
)
def test_confirmation_least_privilege_denies_non_owner_admin(role) -> None:
    service, _resolutions, commands, _cases = _service(role)

    with pytest.raises(VNextError) as error:
        service.confirm(
            principal=_principal(),
            identity_resolution_id=RESOLUTION_ID,
            identity_candidate_id=CANDIDATE_1,
            expected_version=1,
            confirmation_reason="human reviewed the displayed evidence",
            idempotency_key="confirmation-key-0002",
            request_id="request-1",
        )

    assert error.value.code is ErrorCode.PERMISSION_DENIED
    assert commands.confirm_count == 0
    assert commands.property_count == 0


def test_same_key_different_confirmation_and_conflicting_second_command_fail() -> None:
    service, _resolutions, commands, _cases = _service(WorkspaceRole.ADMIN)
    service.confirm(
        principal=_principal(),
        identity_resolution_id=RESOLUTION_ID,
        identity_candidate_id=CANDIDATE_2,
        expected_version=1,
        confirmation_reason="human reviewed the displayed evidence",
        idempotency_key="confirmation-key-0003",
        request_id="request-1",
    )

    with pytest.raises(VNextError) as key_error:
        service.confirm(
            principal=_principal(),
            identity_resolution_id=RESOLUTION_ID,
            identity_candidate_id=CANDIDATE_1,
            expected_version=1,
            confirmation_reason="human reviewed different displayed evidence",
            idempotency_key="confirmation-key-0003",
            request_id="request-2",
        )
    with pytest.raises(VNextError) as conflict_error:
        service.confirm(
            principal=_principal(),
            identity_resolution_id=RESOLUTION_ID,
            identity_candidate_id=CANDIDATE_1,
            expected_version=1,
            confirmation_reason="human reviewed different displayed evidence",
            idempotency_key="confirmation-key-0004",
            request_id="request-3",
        )

    assert key_error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert conflict_error.value.code is ErrorCode.VERSION_CONFLICT
    assert commands.confirm_count == 1
    assert commands.property_count == 1


def test_failed_confirmation_replays_the_same_allowlisted_error() -> None:
    service, _resolutions, commands, _cases = _service(WorkspaceRole.OWNER)

    for request_id in ("request-1", "request-2"):
        with pytest.raises(VNextError) as stale:
            service.confirm(
                principal=_principal(),
                identity_resolution_id=RESOLUTION_ID,
                identity_candidate_id=CANDIDATE_2,
                expected_version=2,
                confirmation_reason="human reviewed the displayed evidence",
                idempotency_key="confirmation-failed-replay-0001",
                request_id=request_id,
            )
        assert stale.value.code is ErrorCode.VERSION_CONFLICT

    assert commands.confirm_count == 0
    assert commands.property_count == 0


def test_rejection_retains_history_and_blocks_later_candidate_confirmation() -> None:
    service, resolutions, commands, _cases = _service(WorkspaceRole.OWNER)
    rejected = service.reject(
        principal=_principal(),
        identity_resolution_id=RESOLUTION_ID,
        identity_candidate_id=CANDIDATE_2,
        expected_version=1,
        reason_code="not_same_property",
        idempotency_key="rejection-key-0001",
        request_id="request-1",
    )

    with pytest.raises(VNextError) as error:
        service.confirm(
            principal=_principal(),
            identity_resolution_id=RESOLUTION_ID,
            identity_candidate_id=CANDIDATE_2,
            expected_version=2,
            confirmation_reason="human reconsidered the stale resolution",
            idempotency_key="confirmation-key-0005",
            request_id="request-2",
        )

    assert rejected.decision.decision_type == "candidate_rejected"
    assert len(resolutions.record.candidates) == 2
    assert error.value.code is ErrorCode.VERSION_CONFLICT
    assert commands.property_count == 0


def test_case_creation_and_attachment_are_separate_idempotent_commands() -> None:
    service, _resolutions, commands, cases = _service(WorkspaceRole.OWNER)
    created = service.create_case(
        principal=_principal(),
        workspace_id=WORKSPACE_ID,
        purpose=CasePurpose.BUY_DUE_DILIGENCE,
        title="Fixture Case",
        idempotency_key="case-create-key-0001",
        request_id="request-1",
    )
    service.confirm(
        principal=_principal(),
        identity_resolution_id=RESOLUTION_ID,
        identity_candidate_id=CANDIDATE_2,
        expected_version=1,
        confirmation_reason="human reviewed the displayed evidence",
        idempotency_key="confirmation-key-0006",
        request_id="request-2",
    )
    assert cases.record.identity_status is CaseIdentityStatus.UNVERIFIED
    attached = service.attach_resolution(
        principal=_principal(),
        case_id=CASE_ID,
        identity_resolution_id=RESOLUTION_ID,
        expected_case_version=1,
        idempotency_key="case-attach-key-0001",
        request_id="request-3",
    )
    replay = service.attach_resolution(
        principal=_principal(),
        case_id=CASE_ID,
        identity_resolution_id=RESOLUTION_ID,
        expected_case_version=1,
        idempotency_key="case-attach-key-0001",
        request_id="request-4",
    )

    assert created.case.identity_status is CaseIdentityStatus.UNVERIFIED
    assert attached.case.identity_status is CaseIdentityStatus.CONFIRMED
    assert attached.case.version == 2
    assert replay.replayed is True
    assert commands.attach_count == 1
    assert len(commands.links) == 1
