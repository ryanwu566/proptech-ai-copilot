from __future__ import annotations

import importlib.util
import json
from dataclasses import FrozenInstanceError
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
from services.vnext.persistence import IdempotencyDecision, IdempotencyReservation


WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
CASE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SET_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
MEMBER_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
OTHER_MEMBER_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
PARCEL_ID = UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)


def test_case_parcel_set_service_modules_exist() -> None:
    assert importlib.util.find_spec("services.vnext.case_parcel_set") is not None
    assert importlib.util.find_spec("services.vnext.case_parcel_set_service") is not None


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(USER_ID, str(USER_ID), "http://localhost/auth/v1", NOW)


def _record(*, parcel_set_id: UUID = SET_ID, workspace_id: UUID = WORKSPACE_ID):
    from services.vnext.case_parcel_set import (
        CaseParcelSetRecord,
        ParcelSetStatus,
    )

    return CaseParcelSetRecord(
        parcel_set_id=parcel_set_id,
        workspace_id=workspace_id,
        case_id=CASE_ID,
        status=ParcelSetStatus.DRAFT,
        version=1,
        active_member_id=None,
        created_by_user_id=USER_ID,
        created_at=NOW,
        updated_at=NOW,
        reviewed_at=None,
        members=(),
    )


class _Memberships:
    def __init__(self, role: WorkspaceRole) -> None:
        self.role = role

    def get_active_membership(self, *, principal, workspace_id):
        if workspace_id != WORKSPACE_ID:
            return None
        return WorkspaceMembership(workspace_id, principal.user_id, self.role)


class _Idempotency:
    def __init__(self, reservation: IdempotencyReservation | None = None) -> None:
        self.reservation = reservation
        self.reserve_calls: list[dict[str, object]] = []
        self.failed_calls: list[dict[str, object]] = []

    def reserve(self, **kwargs):
        self.reserve_calls.append(kwargs)
        return self.reservation or IdempotencyReservation(
            decision=IdempotencyDecision.NEW,
            idempotency_record_id=uuid4(),
            request_fingerprint="a" * 64,
            operation_status="pending",
            response_reference_type=None,
            response_reference_id=None,
        )

    def mark_failed(self, **kwargs) -> None:
        self.failed_calls.append(kwargs)


class _Writer:
    def __init__(
        self,
        *,
        record=None,
        error: Exception | None = None,
        case_error: Exception | None = None,
    ) -> None:
        self.record = record
        self.error = error
        self.case_error = case_error
        self.require_case_calls: list[dict[str, object]] = []
        self.get_calls: list[dict[str, object]] = []
        self.mutations: list[tuple[str, dict[str, object]]] = []

    def require_case(self, **kwargs) -> None:
        self.require_case_calls.append(kwargs)
        if self.case_error is not None:
            raise self.case_error

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        return self.record or _record()

    def _mutate(self, name: str, kwargs: dict[str, object]):
        self.mutations.append((name, kwargs))
        if self.error is not None:
            raise self.error
        return self.record or _record()

    def initialize(self, **kwargs):
        return self._mutate("initialize", kwargs)

    def add_member(self, **kwargs):
        return self._mutate("add_member", kwargs)

    def review_member(self, **kwargs):
        return self._mutate("review_member", kwargs)

    def set_active_member(self, **kwargs):
        return self._mutate("set_active_member", kwargs)

    def reorder(self, **kwargs):
        return self._mutate("reorder", kwargs)

    def mark_case_reviewed(self, **kwargs):
        return self._mutate("mark_case_reviewed", kwargs)


def _service(
    *,
    role: WorkspaceRole = WorkspaceRole.MEMBER,
    writer: _Writer | None = None,
    idempotency: _Idempotency | None = None,
):
    from services.vnext.case_parcel_set_service import CaseParcelSetApplicationService

    selected_writer = writer or _Writer()
    selected_idempotency = idempotency or _Idempotency()
    return (
        CaseParcelSetApplicationService(
            authorizer=WorkspaceAuthorizer(_Memberships(role)),
            writer=selected_writer,
            idempotency_repository=selected_idempotency,
        ),
        selected_writer,
        selected_idempotency,
    )


def test_domain_records_are_immutable_and_use_explicit_case_scoped_states() -> None:
    from services.vnext.case_parcel_set import (
        CaseParcelSetMemberRecord,
        ParcelMemberReviewStatus,
        ParcelSetStatus,
    )

    member = CaseParcelSetMemberRecord(
        parcel_set_member_id=MEMBER_ID,
        workspace_id=WORKSPACE_ID,
        parcel_set_id=SET_ID,
        parcel_identity_reference_id=PARCEL_ID,
        position=1,
        review_status=ParcelMemberReviewStatus.CASE_SELECTED,
        created_by_user_id=USER_ID,
        created_at=NOW,
        updated_at=NOW,
    )

    assert ParcelSetStatus.CASE_REVIEWED.value == "case_reviewed"
    assert ParcelMemberReviewStatus.CANDIDATE.value == "candidate"
    assert ParcelMemberReviewStatus.CASE_SELECTED.value == "case_selected"
    assert ParcelMemberReviewStatus.CASE_REJECTED.value == "case_rejected"
    with pytest.raises(FrozenInstanceError):
        member.position = 2  # type: ignore[misc]


def test_each_command_authorizes_reserves_canonical_input_and_calls_one_writer() -> None:
    from services.vnext.case_parcel_set import ParcelMemberReviewStatus

    service, writer, idempotency = _service()
    common = {
        "principal": _principal(),
        "workspace_id": WORKSPACE_ID,
        "case_id": CASE_ID,
    }
    outcomes = [
        service.initialize(
            **common,
            expected_version=0,
            idempotency_key="parcel-set-create-0001",
            request_id="request-create",
        ),
        service.add_member(
            **common,
            parcel_identity_reference_id=PARCEL_ID,
            expected_version=1,
            idempotency_key="parcel-set-add-0001",
            request_id="request-add",
        ),
        service.review_member(
            **common,
            member_id=MEMBER_ID,
            review_status=ParcelMemberReviewStatus.CASE_SELECTED,
            expected_version=2,
            idempotency_key="parcel-set-review-member-0001",
            request_id="request-review-member",
        ),
        service.set_active_member(
            **common,
            active_member_id=MEMBER_ID,
            expected_version=3,
            idempotency_key="parcel-set-active-0001",
            request_id="request-active",
        ),
        service.reorder(
            **common,
            ordered_member_ids=(MEMBER_ID, OTHER_MEMBER_ID),
            expected_version=4,
            idempotency_key="parcel-set-reorder-0001",
            request_id="request-reorder",
        ),
        service.mark_case_reviewed(
            **common,
            expected_version=5,
            idempotency_key="parcel-set-case-review-0001",
            request_id="request-case-review",
        ),
    ]

    assert all(outcome.record.parcel_set_id == SET_ID for outcome in outcomes)
    assert all(outcome.replayed is False for outcome in outcomes)
    assert [name for name, _kwargs in writer.mutations] == [
        "initialize",
        "add_member",
        "review_member",
        "set_active_member",
        "reorder",
        "mark_case_reviewed",
    ]
    assert [call["canonical_route"] for call in idempotency.reserve_calls] == [
        f"/v1/cases/{CASE_ID}/parcel-set",
        f"/v1/cases/{CASE_ID}/parcel-set/members",
        f"/v1/cases/{CASE_ID}/parcel-set/members/{MEMBER_ID}/review",
        f"/v1/cases/{CASE_ID}/parcel-set/active-member",
        f"/v1/cases/{CASE_ID}/parcel-set/reorder",
        f"/v1/cases/{CASE_ID}/parcel-set/review",
    ]
    assert all(
        call["conflict_scope"] == "case_parcel_set"
        for call in idempotency.reserve_calls
    )
    assert len(writer.require_case_calls) == 6
    requests = [json.loads(call["canonical_request"]) for call in idempotency.reserve_calls]
    assert [request["expected_version"] for request in requests] == [0, 1, 2, 3, 4, 5]
    assert requests[1]["parcel_identity_reference_id"] == str(PARCEL_ID)
    assert requests[2]["review_status"] == "case_selected"
    assert requests[3]["active_member_id"] == str(MEMBER_ID)
    assert requests[4]["ordered_member_ids"] == [str(MEMBER_ID), str(OTHER_MEMBER_ID)]


def test_viewer_can_read_but_is_denied_before_mutation_reservation() -> None:
    service, writer, idempotency = _service(role=WorkspaceRole.VIEWER)

    assert service.get(principal=_principal(), case_id=CASE_ID).parcel_set_id == SET_ID
    with pytest.raises(VNextError) as denied:
        service.initialize(
            principal=_principal(),
            workspace_id=WORKSPACE_ID,
            case_id=CASE_ID,
            expected_version=0,
            idempotency_key="parcel-set-viewer-0001",
            request_id="request-viewer",
        )

    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    assert len(writer.get_calls) == 1
    assert writer.mutations == []
    assert idempotency.reserve_calls == []
    assert writer.require_case_calls == []


def test_hidden_or_cross_workspace_case_fails_before_idempotency_reservation() -> None:
    writer = _Writer(case_error=VNextError.not_found())
    service, _writer, idempotency = _service(writer=writer)

    with pytest.raises(VNextError) as hidden:
        service.initialize(
            principal=_principal(),
            workspace_id=WORKSPACE_ID,
            case_id=CASE_ID,
            expected_version=0,
            idempotency_key="parcel-set-hidden-case-0001",
            request_id="request-hidden-case",
        )

    assert hidden.value.code is ErrorCode.NOT_FOUND
    assert len(writer.require_case_calls) == 1
    assert idempotency.reserve_calls == []
    assert writer.mutations == []


def _replay(
    *,
    operation_status: str = "succeeded",
    response_reference_type: str | None = "case_parcel_set",
    response_reference_id: UUID | None = SET_ID,
    response_error_code: str | None = None,
) -> IdempotencyReservation:
    return IdempotencyReservation(
        decision=IdempotencyDecision.REPLAY,
        idempotency_record_id=uuid4(),
        request_fingerprint="b" * 64,
        operation_status=operation_status,
        response_reference_type=response_reference_type,
        response_reference_id=response_reference_id,
        response_status_code=200,
        response_error_code=response_error_code,
    )


def test_successful_replay_reads_the_set_without_repeating_mutation() -> None:
    idempotency = _Idempotency(_replay())
    service, writer, _selected = _service(idempotency=idempotency)

    outcome = service.add_member(
        principal=_principal(),
        workspace_id=WORKSPACE_ID,
        case_id=CASE_ID,
        parcel_identity_reference_id=PARCEL_ID,
        expected_version=1,
        idempotency_key="parcel-set-replay-0001",
        request_id="request-replay",
    )

    assert outcome.replayed is True
    assert outcome.record.parcel_set_id == SET_ID
    assert writer.mutations == []
    assert writer.get_calls == [{"principal": _principal(), "case_id": CASE_ID}]


@pytest.mark.parametrize(
    ("reservation", "expected"),
    [
        (_replay(operation_status="pending", response_reference_type=None, response_reference_id=None), ErrorCode.MAINTENANCE),
        (_replay(operation_status="failed", response_error_code="version_conflict"), ErrorCode.VERSION_CONFLICT),
        (_replay(response_reference_type="wrong"), ErrorCode.INTERNAL_ERROR),
        (_replay(response_reference_id=OTHER_MEMBER_ID), ErrorCode.INTERNAL_ERROR),
    ],
)
def test_replay_state_is_bounded_and_never_reexecutes(
    reservation: IdempotencyReservation,
    expected: ErrorCode,
) -> None:
    service, writer, _selected = _service(idempotency=_Idempotency(reservation))

    with pytest.raises(VNextError) as raised:
        service.mark_case_reviewed(
            principal=_principal(),
            workspace_id=WORKSPACE_ID,
            case_id=CASE_ID,
            expected_version=1,
            idempotency_key="parcel-set-replay-state-0001",
            request_id="request-replay-state",
        )

    assert raised.value.code is expected
    assert writer.mutations == []


@pytest.mark.parametrize(
    ("writer_error", "expected_code", "expected_status"),
    [
        (VNextError.not_found(), ErrorCode.NOT_FOUND, 404),
        (RuntimeError("database credentials must not leak"), ErrorCode.INTERNAL_ERROR, 500),
    ],
)
def test_writer_failure_marks_idempotency_with_only_allowlisted_error(
    writer_error: Exception,
    expected_code: ErrorCode,
    expected_status: int,
) -> None:
    idempotency = _Idempotency()
    service, _writer, _selected = _service(
        writer=_Writer(error=writer_error),
        idempotency=idempotency,
    )

    with pytest.raises(VNextError) as raised:
        service.mark_case_reviewed(
            principal=_principal(),
            workspace_id=WORKSPACE_ID,
            case_id=CASE_ID,
            expected_version=1,
            idempotency_key="parcel-set-failure-0001",
            request_id="request-failure",
        )

    assert raised.value.code is expected_code
    assert len(idempotency.failed_calls) == 1
    assert idempotency.failed_calls[0]["response_status_code"] == expected_status
    assert idempotency.failed_calls[0]["response_error_code"] == expected_code.value
    assert "credentials" not in repr(idempotency.failed_calls[0])


@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        ("initialize", {"expected_version": 1}),
        ("add_member", {"parcel_identity_reference_id": PARCEL_ID, "expected_version": 0}),
        ("review_member", {"member_id": MEMBER_ID, "review_status": "case_selected", "expected_version": 0}),
        ("set_active_member", {"active_member_id": None, "expected_version": 0}),
        ("reorder", {"ordered_member_ids": (), "expected_version": 1}),
        ("reorder", {"ordered_member_ids": (MEMBER_ID, MEMBER_ID), "expected_version": 1}),
        ("reorder", {"ordered_member_ids": tuple(uuid4() for _ in range(101)), "expected_version": 1}),
        ("mark_case_reviewed", {"expected_version": 0}),
    ],
)
def test_invalid_versions_states_and_orders_fail_before_reservation(
    method: str,
    kwargs: dict[str, object],
) -> None:
    service, writer, idempotency = _service()

    with pytest.raises(VNextError) as raised:
        getattr(service, method)(
            principal=_principal(),
            workspace_id=WORKSPACE_ID,
            case_id=CASE_ID,
            idempotency_key="parcel-set-validation-0001",
            request_id="request-validation",
            **kwargs,
        )

    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert idempotency.reserve_calls == []
    assert writer.mutations == []
