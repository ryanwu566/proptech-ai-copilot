from __future__ import annotations

import hashlib
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
from services.vnext.legacy_case_import_repository import (
    LegacyCaseImportRecord,
    LegacyImportWriteResult,
)
from services.vnext.legacy_case_import_service import LegacyCaseImportApplicationService
from services.vnext.persistence import (
    CaseIdentityStatus,
    CasePurpose,
    CaseRecord,
    CaseStatus,
    IdempotencyDecision,
    IdempotencyReservation,
)


WORKSPACE_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
WORKSPACE_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
USERS = {
    "viewer": UUID("10000000-0000-4000-8000-000000000001"),
    "member": UUID("10000000-0000-4000-8000-000000000002"),
    "manager": UUID("10000000-0000-4000-8000-000000000003"),
    "admin": UUID("10000000-0000-4000-8000-000000000004"),
    "owner": UUID("10000000-0000-4000-8000-000000000005"),
}


def principal(role: str) -> AuthenticatedPrincipal:
    user_id = USERS[role]
    return AuthenticatedPrincipal(
        user_id=user_id,
        token_subject=str(user_id),
        issuer="https://fixture.invalid/auth/v1",
        token_issued_at=datetime.now(timezone.utc),
    )


class Memberships:
    def get_active_membership(self, *, principal, workspace_id):
        role = next((name for name, user_id in USERS.items() if user_id == principal.user_id), None)
        if role is None:
            return None
        return WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=principal.user_id,
            role=WorkspaceRole(role),
        )


class FakeIdempotency:
    def __init__(self) -> None:
        self.records: dict[tuple[UUID, UUID, str], dict[str, object]] = {}
        self.by_id: dict[UUID, dict[str, object]] = {}
        self.failed: list[tuple[UUID, str]] = []

    def reserve(self, **kwargs):
        scope = (kwargs["workspace_id"], kwargs["principal"].user_id, kwargs["idempotency_key"])
        fingerprint = hashlib.sha256(kwargs["canonical_request"]).hexdigest()
        row = self.records.get(scope)
        if row is None:
            row = {
                "id": uuid4(), "fingerprint": fingerprint, "status": "pending",
                "reference_type": None, "reference_id": None, "status_code": None,
                "error_code": None,
            }
            self.records[scope] = row
            self.by_id[row["id"]] = row
            decision = IdempotencyDecision.NEW
        else:
            if row["fingerprint"] != fingerprint:
                raise VNextError.idempotency_conflict()
            decision = IdempotencyDecision.REPLAY
        return IdempotencyReservation(
            decision=decision,
            idempotency_record_id=row["id"],
            request_fingerprint=row["fingerprint"],
            operation_status=row["status"],
            response_reference_type=row["reference_type"],
            response_reference_id=row["reference_id"],
            response_status_code=row["status_code"],
            response_error_code=row["error_code"],
        )

    def complete(self, record_id: UUID, reference_id: UUID) -> None:
        row = self.by_id[record_id]
        row.update(
            status="succeeded",
            reference_type="legacy_case_import",
            reference_id=reference_id,
            status_code=201,
        )

    def mark_failed(self, **kwargs):
        row = self.by_id[kwargs["idempotency_record_id"]]
        row.update(
            status="failed",
            status_code=kwargs["response_status_code"],
            error_code=kwargs["response_error_code"],
        )
        self.failed.append((kwargs["idempotency_record_id"], kwargs["response_error_code"]))


class FakeRepository:
    def __init__(self, idempotency: FakeIdempotency) -> None:
        self.idempotency = idempotency
        self.imports: dict[UUID, LegacyImportWriteResult] = {}
        self.scoped_clients: set[tuple[UUID, UUID, str]] = set()
        self.calls: list[dict[str, object]] = []
        self.fail = False

    def import_case(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        scope = (
            kwargs["workspace_id"],
            kwargs["principal"].user_id,
            kwargs["legacy_client_id_hash"],
        )
        if scope in self.scoped_clients:
            raise VNextError.duplicate_legacy_import(
                details={"import_status": "duplicate_requires_explicit_choice"}
            )
        self.scoped_clients.add(scope)
        now = datetime.now(timezone.utc)
        case_id = uuid4()
        import_id = uuid4()
        parsed = kwargs["parsed"]
        result = LegacyImportWriteResult(
            case=CaseRecord(
                case_id=case_id,
                workspace_id=kwargs["workspace_id"],
                purpose=CasePurpose.BUY_DUE_DILIGENCE,
                status=CaseStatus.OPEN,
                title=parsed.title,
                identity_status=CaseIdentityStatus.LEGACY_UNVERIFIED,
                assigned_member_id=None,
                version=1,
                opened_at=now,
                updated_at=now,
                closed_at=None,
                archived_at=None,
            ),
            import_record=LegacyCaseImportRecord(
                legacy_case_import_id=import_id,
                workspace_id=kwargs["workspace_id"],
                case_id=case_id,
                actor_user_id=kwargs["principal"].user_id,
                legacy_format="saved_case_v1",
                legacy_client_id_hash=kwargs["legacy_client_id_hash"],
                schema_version=1,
                import_mode="copy",
                imported_at=now,
                client_created_at=parsed.client_created_at,
                client_updated_at=parsed.client_updated_at,
                accepted_field_classes=parsed.accepted_field_classes,
                dropped_field_classes=parsed.dropped_field_classes,
                warnings=parsed.warnings,
                idempotency_record_id=kwargs["idempotency_record_id"],
                request_id=kwargs["request_id"],
            ),
            evidence_ids=tuple(uuid4() for _ in parsed.evidence),
        )
        self.imports[import_id] = result
        self.idempotency.complete(kwargs["idempotency_record_id"], import_id)
        return result

    def get_import_by_id(self, **kwargs):
        return self.imports[kwargs["legacy_case_import_id"]]


def payload(title: str = "Synthetic saved case") -> dict[str, object]:
    return {
        "title": title,
        "version": 1,
        "workflowMode": "buying_wizard",
        "inputSummary": {"city": "Synthetic City", "road": "Example Road"},
        "data": {"inputs": {"city": "Synthetic City", "road": "Example Road"}},
    }


def service():
    idempotency = FakeIdempotency()
    repository = FakeRepository(idempotency)
    application = LegacyCaseImportApplicationService(
        authorizer=WorkspaceAuthorizer(Memberships()),
        repository=repository,
        idempotency_repository=idempotency,
    )
    return application, repository, idempotency


def import_case(application, role="member", workspace_id=WORKSPACE_A, key="slice7-idempotency-key-0001", body=None, client_id="browser-case-1"):
    return application.import_case(
        principal=principal(role),
        workspace_id=workspace_id,
        legacy_format="saved_case_v1",
        legacy_client_id=client_id,
        payload=body or payload(),
        import_mode="copy",
        consent=True,
        idempotency_key=key,
        request_id="slice7-request",
    )


@pytest.mark.parametrize("role", ["member", "manager", "admin", "owner"])
def test_active_writers_can_import_only_legacy_unverified_cases(role: str) -> None:
    application, repository, _ = service()

    outcome = import_case(application, role=role)

    assert outcome.replayed is False
    assert outcome.result.case.identity_status is CaseIdentityStatus.LEGACY_UNVERIFIED
    assert outcome.result.case.purpose is CasePurpose.BUY_DUE_DILIGENCE
    assert outcome.result.case.version == 1
    assert len(repository.calls) == 1
    assert "legacy_client_id" not in repository.calls[0]
    assert repository.calls[0]["legacy_client_id_hash"] != "browser-case-1"


def test_viewer_is_denied_before_idempotency_or_persistence() -> None:
    application, repository, idempotency = service()

    with pytest.raises(VNextError) as error:
        import_case(application, role="viewer")

    assert error.value.code is ErrorCode.PERMISSION_DENIED
    assert repository.calls == []
    assert idempotency.records == {}


def test_same_actor_workspace_key_and_request_replays_without_duplicate_case() -> None:
    application, repository, _ = service()

    created = import_case(application)
    replay = import_case(application)

    assert replay.replayed is True
    assert replay.result.case.case_id == created.result.case.case_id
    assert len(repository.calls) == 1


def test_same_key_with_changed_request_conflicts() -> None:
    application, repository, _ = service()
    import_case(application)

    with pytest.raises(VNextError) as error:
        import_case(application, body=payload("Changed synthetic case"))

    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert len(repository.calls) == 1


def test_idempotency_scope_is_independent_by_actor_and_workspace() -> None:
    application, repository, _ = service()

    first = import_case(application, role="member")
    other_actor = import_case(application, role="manager")
    other_workspace = import_case(application, role="member", workspace_id=WORKSPACE_B)

    assert len({first.result.case.case_id, other_actor.result.case.case_id, other_workspace.result.case.case_id}) == 3
    assert len(repository.calls) == 3


def test_different_key_same_scoped_legacy_client_id_fails_closed() -> None:
    application, repository, idempotency = service()
    import_case(application, key="slice7-duplicate-key-0001")

    with pytest.raises(VNextError) as error:
        import_case(application, key="slice7-duplicate-key-0002")

    assert error.value.code is ErrorCode.DUPLICATE_LEGACY_IMPORT
    assert error.value.details == {"import_status": "duplicate_requires_explicit_choice"}
    assert len(repository.imports) == 1
    assert idempotency.failed[-1][1] == "duplicate_legacy_import"


@pytest.mark.parametrize(
    ("legacy_format", "import_mode", "consent"),
    [("future_format", "copy", True), ("saved_case_v1", "merge", True), ("saved_case_v1", "copy", False)],
)
def test_format_mode_and_consent_fail_closed(legacy_format: str, import_mode: str, consent: bool) -> None:
    application, repository, idempotency = service()

    with pytest.raises(VNextError) as error:
        application.import_case(
            principal=principal("member"), workspace_id=WORKSPACE_A,
            legacy_format=legacy_format, legacy_client_id="browser-case-1", payload=payload(),
            import_mode=import_mode, consent=consent,
            idempotency_key="slice7-validation-key-0001", request_id="slice7-request",
        )

    assert error.value.code is ErrorCode.UNSUPPORTED_INPUT
    assert repository.calls == []
    assert idempotency.records == {}


def test_failed_import_records_failure_without_partial_case() -> None:
    application, repository, idempotency = service()
    repository.fail = True

    with pytest.raises(VNextError) as error:
        import_case(application, key="slice7-failed-import-0001")

    assert error.value.code is ErrorCode.INTERNAL_ERROR
    assert repository.imports == {}
    assert idempotency.failed[-1][1] == "internal_error"


def test_service_has_no_identity_resolution_confirmation_or_attachment_call() -> None:
    source = __import__(
        "services.vnext.legacy_case_import_service", fromlist=["LegacyCaseImportApplicationService"]
    )
    text = open(source.__file__, encoding="utf-8").read()

    assert "create_property_entity" not in text
    assert "attach_resolution" not in text
    assert "identity_resolution" not in text
    assert "identity_confirmation" not in text
