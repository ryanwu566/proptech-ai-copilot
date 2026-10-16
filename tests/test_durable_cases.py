from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.durable_cases import (
    CaseService, CreateCase, MetadataUpdate, MembershipUpdate, MonitoringUpdate,
    UnavailableCaseRepository,
)
from services.vnext.errors import VNextError
from tests.durable_case_fixtures import MemoryCaseRepository, snapshot

A, B, C = [AuthenticatedPrincipal(UUID(int=i), str(UUID(int=i)), "test") for i in (1, 2, 3)]


def create(service, principal=A, **changes):
    return service.create(principal, CreateCase(snapshot=snapshot(), import_key="local-case-v1", explicit_consent=True, **changes))


def test_explicit_consent_and_identity_are_strict():
    for fields in ({"explicit_consent": False}, {"explicit_consent": "true"}, {"owner_id": str(A.user_id)}, {"email": "owner@example.invalid"}):
        with pytest.raises(ValidationError):
            CreateCase.model_validate({"snapshot": snapshot(), "import_key": "case", "explicit_consent": True, **fields})


def test_import_preserves_historical_json_and_does_not_alias_caller():
    repo = MemoryCaseRepository(); service = CaseService(repo)
    original = snapshot(); request = CreateCase(snapshot=original, import_key="case", explicit_consent=True)
    row = service.create(A, request)
    assert row.snapshot == original
    assert row.owner_id == A.user_id and row.revision == 1 and row.role == "owner"
    original["data"]["notes"] = "changed"
    row.snapshot["data"]["notes"] = "also changed"
    assert service.open(A, row.id).snapshot == snapshot()
    assert service.activity(A, row.id, offset=0, limit=20)[0].kind == "case_imported"


def test_idempotent_import_retries_and_changed_payload_conflict():
    service = CaseService(MemoryCaseRepository())
    first = create(service)
    assert create(service).id == first.id
    changed = snapshot(); changed["data"]["notes"] = "different"
    with pytest.raises(VNextError, match="idempotency_conflict"):
        service.create(A, CreateCase(snapshot=changed, import_key="local-case-v1", explicit_consent=True))
    assert len(service.list(A, scope="owned", offset=0, limit=20)) == 1
    assert create(service, B).id != first.id


def test_mis_scoped_import_repository_cannot_select_another_owner():
    repo = MemoryCaseRepository(); service = CaseService(repo); row = create(service, B)
    foreign = repo.get(row.id); foreign.members[A.user_id] = "editor"
    repo.find_import = lambda *args: foreign
    with pytest.raises(VNextError, match="permission_denied"):
        create(service, A)


def test_no_cross_account_read_or_workspace_role_shortcut():
    service = CaseService(MemoryCaseRepository()); row = create(service)
    assert service.list(B, scope="owned", offset=0, limit=20) == []
    for operation in (lambda: service.open(B, row.id), lambda: service.activity(B, row.id, offset=0, limit=20),
                      lambda: service.metadata(B, row.id, MetadataUpdate(expected_revision=1, title="stolen"))):
        with pytest.raises(VNextError, match="not_found"):
            operation()


@pytest.mark.parametrize("role", ["editor", "viewer"])
def test_collaboration_boundaries_and_revocation(role):
    service = CaseService(MemoryCaseRepository()); row = create(service)
    row = service.membership(A, row.id, MembershipUpdate(expected_revision=1, member_id=B.user_id, role=role))
    assert service.open(B, row.id).role == role
    assert service.list(B, scope="owned", offset=0, limit=20) == []
    assert len(service.list(B, scope="shared", offset=0, limit=20)) == 1
    for op in (lambda: service.membership(B, row.id, MembershipUpdate(expected_revision=2, member_id=C.user_id, role="viewer")),
               lambda: service.monitoring(B, row.id, MonitoringUpdate(expected_revision=2, cadence="daily"))):
        with pytest.raises(VNextError, match="permission_denied"):
            op()
    if role == "viewer":
        with pytest.raises(VNextError, match="permission_denied"):
            service.metadata(B, row.id, MetadataUpdate(expected_revision=2, title="denied"))
    else:
        row = service.metadata(B, row.id, MetadataUpdate(expected_revision=2, notes="editor note"))
        assert row.notes == "editor note" and row.snapshot == snapshot()
    row = service.membership(A, row.id, MembershipUpdate(expected_revision=row.revision, member_id=B.user_id, role=None))
    with pytest.raises(VNextError, match="not_found"):
        service.open(B, row.id)
    with pytest.raises(VNextError, match="permission_denied"):
        service.membership(A, row.id, MembershipUpdate(expected_revision=row.revision, member_id=A.user_id, role="viewer"))


def test_concurrent_updates_have_one_winner_and_atomic_activity():
    service = CaseService(MemoryCaseRepository()); row = create(service)
    def update(title):
        try:
            return service.metadata(A, row.id, MetadataUpdate(expected_revision=1, title=title)).revision
        except VNextError as error:
            return error.code.value
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(update, ["a", "b"]))
    assert sorted(map(str, results)) == ["2", "version_conflict"]
    assert len(service.activity(A, row.id, offset=0, limit=100)) == 2
    assert service.open(A, row.id).snapshot == snapshot()


def test_stale_membership_and_preferences_have_no_side_effects():
    service = CaseService(MemoryCaseRepository()); row = create(service)
    service.metadata(A, row.id, MetadataUpdate(expected_revision=1, title="updated"))
    for op in (lambda: service.membership(A, row.id, MembershipUpdate(expected_revision=1, member_id=B.user_id, role="editor")),
               lambda: service.monitoring(A, row.id, MonitoringUpdate(expected_revision=1, cadence="daily"))):
        with pytest.raises(VNextError, match="version_conflict"):
            op()
    current = service.open(A, row.id)
    assert current.members == {} and current.monitoring.cadence == "off"
    assert len(service.activity(A, row.id, offset=0, limit=100)) == 2


def test_repository_commit_failure_is_safe_and_rolls_back():
    repo = MemoryCaseRepository(); service = CaseService(repo); row = create(service)
    original = deepcopy(repo.rows)
    def fail(value, **kwargs):
        repo.rows[value.id] = value
        raise RuntimeError("SECRET SQL")
    repo.replace = fail
    with pytest.raises(VNextError, match="maintenance") as exc:
        service.metadata(A, row.id, MetadataUpdate(expected_revision=1, notes="not committed"))
    assert "SECRET" not in str(exc.value) and repo.rows == original


def test_no_acknowledgment_before_commit_and_activity_is_atomic():
    class FailedCommit(MemoryCaseRepository):
        @contextmanager
        def transaction(self, principal):
            with super().transaction(principal) as tx:
                yield tx
                raise RuntimeError("private commit failure")
    repo = FailedCommit()
    with pytest.raises(VNextError, match="maintenance"):
        create(CaseService(repo))
    assert repo.rows == {} and repo.events == {}


def test_history_is_paged_and_contains_no_notes_or_snapshot():
    service = CaseService(MemoryCaseRepository()); row = create(service)
    service.metadata(A, row.id, MetadataUpdate(expected_revision=1, notes="Private authored content"))
    first = service.activity(A, row.id, offset=0, limit=1)
    second = service.activity(A, row.id, offset=1, limit=1)
    assert [first[0].revision, second[0].revision] == [2, 1]
    assert "Private authored content" not in first[0].model_dump_json()
    assert "snapshot" not in first[0].model_dump()
    for offset, limit in [(-1, 20), (0, 101), (10001, 20)]:
        with pytest.raises(VNextError, match="validation_failed"):
            service.activity(A, row.id, offset=offset, limit=limit)


@pytest.mark.parametrize("secret", [
    {"access_token": "private"}, {"nested": {"Authorization": "Bearer private"}},
    {"apiKey": "private"}, {"password": "private"}, {"notes": "Bearer abcdefghijkl"},
    {"provider_access_token": "private"}, {"openai_api_key": "private"},
    {"url": "https://example.invalid/?key=private"}, {"notes": "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhIn0.signature"},
])
def test_credentials_reject_entire_snapshot_without_rewriting(secret):
    value = snapshot(); value["data"]["unsafe"] = secret
    with pytest.raises(ValidationError):
        CreateCase(snapshot=value, import_key="case", explicit_consent=True)
    with pytest.raises(ValidationError):
        MetadataUpdate(expected_revision=1, notes="Bearer abcdefghijkl")


def test_import_key_cannot_persist_credential_shaped_values():
    with pytest.raises(ValidationError):
        CreateCase(snapshot=snapshot(), import_key="sb_secret_examplecredential", explicit_consent=True)


def test_strict_bounded_metadata_and_monitoring():
    for changes in ({"snapshot": {}}, {"owner_id": str(B.user_id)}, {"title": "x" * 501}, {"expected_revision": True}, {}):
        with pytest.raises(ValidationError):
            MetadataUpdate.model_validate({"expected_revision": 1, **changes} if changes else {"expected_revision": 1})
    with pytest.raises(ValidationError):
        MonitoringUpdate(expected_revision=1, cadence="minutely")
    with pytest.raises(ValidationError):
        MonitoringUpdate(expected_revision=1, cadence="daily", refresh_policy="automatic")
    with pytest.raises(ValidationError):
        CreateCase(snapshot={**snapshot(), "data": {"notes": "x" * 270000}}, import_key="case", explicit_consent=True)


def test_monitoring_records_preferences_only_and_status_is_honest():
    service = CaseService(MemoryCaseRepository()); row = create(service)
    row = service.monitoring(A, row.id, MonitoringUpdate(expected_revision=1, cadence="daily"))
    assert row.monitoring.cadence == "daily"
    assert row.monitoring.refresh_policy == "manual_only"
    assert row.monitoring.execution_status == "not_configured"
    assert row.monitoring.delivery_status == "not_configured"
    assert service.open(A, row.id).snapshot == snapshot()


def test_default_persistence_fails_closed():
    with pytest.raises(VNextError, match="maintenance") as exc:
        CaseService(UnavailableCaseRepository()).list(A, scope="owned", offset=0, limit=20)
    assert exc.value.details == {"reason_code": "persistence_pending"}
