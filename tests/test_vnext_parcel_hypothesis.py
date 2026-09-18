from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer, WorkspaceMembership, WorkspaceRole
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.parcel_hypothesis import normalize_parcel_hypothesis
from services.vnext.parcel_hypothesis_command import (
    PARCEL_HYPOTHESIS_RESPONSE_TYPE, ParcelHypothesisApplicationService,
    ParcelHypothesisRecord,
)
from services.vnext.persistence import IdempotencyDecision, IdempotencyReservation

WORKSPACE = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER_WORKSPACE = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROPERTY = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
OTHER_PROPERTY = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
USER = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)
COMPONENTS = {
    "county_city": "臺北市", "district_township": "中正區",
    "section": "南海段", "subsection": None, "land_number": "１２３ 之 ４",
}


def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(USER, str(USER), "http://localhost/auth/v1", NOW)


class Memberships:
    def __init__(self, role: WorkspaceRole | None = WorkspaceRole.MEMBER):
        self.role = role

    def get_active_membership(self, *, principal, workspace_id):
        if self.role is None or workspace_id != WORKSPACE:
            return None
        return WorkspaceMembership(WORKSPACE, principal.user_id, self.role)


class Idempotency:
    def __init__(self):
        self.records = {}
        self.ids = {}

    def reserve(self, **kwargs):
        scope = (kwargs["principal"].user_id, kwargs["workspace_id"], kwargs["canonical_route"], kwargs["idempotency_key"])
        fingerprint = hashlib.sha256(kwargs["canonical_request"]).hexdigest()
        if scope in self.records:
            existing = self.records[scope]
            if existing.request_fingerprint != fingerprint:
                raise VNextError.idempotency_conflict()
            return replace(existing, decision=IdempotencyDecision.REPLAY)
        record = IdempotencyReservation(IdempotencyDecision.NEW, uuid4(), fingerprint, "pending", None, None)
        self.records[scope] = record
        self.ids[record.idempotency_record_id] = scope
        return record

    def succeed(self, record_id, relation_id):
        scope = self.ids[record_id]
        self.records[scope] = replace(
            self.records[scope], operation_status="succeeded",
            response_reference_type=PARCEL_HYPOTHESIS_RESPONSE_TYPE,
            response_reference_id=relation_id, response_status_code=201,
        )

    def mark_failed(self, **kwargs):
        scope = self.ids[kwargs["idempotency_record_id"]]
        self.records[scope] = replace(
            self.records[scope], operation_status="failed",
            response_error_code=kwargs["response_error_code"],
            response_status_code=kwargs["response_status_code"],
        )


class Writer:
    def __init__(self, idempotency):
        self.idempotency = idempotency
        self.records = {}
        self.by_key = {}
        self.write_count = 0

    def require_property(self, *, principal, workspace_id, property_entity_id):
        if workspace_id != WORKSPACE or property_entity_id != PROPERTY:
            raise VNextError.not_found()

    def append(self, *, principal, workspace_id, property_entity_id, normalized, idempotency_record_id, request_id):
        if normalized.normalized_key in self.by_key:
            raise VNextError.conflicting_evidence()
        record = ParcelHypothesisRecord(
            property_entity_id, uuid4(), uuid4(), normalized.normalized_key,
            normalized.display_value, NOW,
        )
        self.records[record.relation_id] = record
        self.by_key[record.normalized_key] = record
        self.write_count += 1
        self.idempotency.succeed(idempotency_record_id, record.relation_id)
        return record

    def get_by_relation_id(self, *, principal, workspace_id, property_entity_id, relation_id):
        record = self.records[relation_id]
        if property_entity_id != record.property_entity_id or workspace_id != WORKSPACE:
            raise VNextError.not_found()
        return record


def service(role=WorkspaceRole.MEMBER):
    idem = Idempotency()
    writer = Writer(idem)
    app = ParcelHypothesisApplicationService(
        authorizer=WorkspaceAuthorizer(Memberships(role)), writer=writer,
        idempotency_repository=idem,
    )
    return app, writer, idem


def submit(app, *, components=None, key="parcel-hypothesis-key-0001", workspace=WORKSPACE, property_id=PROPERTY):
    return app.create(
        principal=principal(), workspace_id=workspace, property_entity_id=property_id,
        components=COMPONENTS if components is None else components,
        idempotency_key=key, request_id="parcel-fixture-request",
    )


def test_normalizer_is_deterministic_and_preserves_raw_input():
    first = normalize_parcel_hypothesis(COMPONENTS)
    equivalent = normalize_parcel_hypothesis({
        "county_city": " 臺 北 市 ", "district_township": "中正區",
        "section": "南海段", "land_number": "123-4",
    })
    assert first.normalized_key == equivalent.normalized_key
    assert first.normalized_key.startswith("parcel-v1:")
    assert first.raw_input["land_number"] == "１２３ 之 ４"
    assert first.normalized_components["land_number"] == "123-4"
    assert "臺北市" in first.display_value


@pytest.mark.parametrize("field,value,reason", [
    ("county_city", None, "missing_required"),
    ("district_township", "", "missing_required"),
    ("section", "南海段/北海段", "ambiguous_structure"),
    ("land_number", "123/4", "malformed_land_number"),
    ("land_number", "1 23", "malformed_land_number"),
    ("land_number", "123-4-5", "malformed_land_number"),
])
def test_normalizer_fails_closed(field, value, reason):
    with pytest.raises(VNextError) as caught:
        normalize_parcel_hypothesis({**COMPONENTS, field: value})
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert caught.value.details == {"field": field, "reason": reason}


def test_normalizer_does_not_rewrite_place_names_or_call_providers():
    tai = normalize_parcel_hypothesis(COMPONENTS)
    alternate = normalize_parcel_hypothesis({**COMPONENTS, "county_city": "台北市"})
    assert tai.normalized_key != alternate.normalized_key
    assert "provider" not in normalize_parcel_hypothesis.__code__.co_names


def test_replay_uses_normalized_fingerprint_without_duplicate_write():
    app, writer, _ = service()
    first = submit(app)
    replay = submit(app, components={
        "county_city": "臺 北 市", "district_township": "中正區",
        "section": "南海段", "subsection": None, "land_number": "123-4",
    })
    assert first.replayed is False and replay.replayed is True
    assert replay.record == first.record
    assert writer.write_count == 1
    assert replay.normalized.raw_input["land_number"] == "123-4"


def test_same_key_with_different_input_conflicts_and_existing_key_never_merges():
    app, writer, _ = service()
    first = submit(app)
    changed = {**COMPONENTS, "land_number": "125"}
    with pytest.raises(VNextError) as conflict:
        submit(app, components=changed)
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(VNextError) as duplicate:
        submit(app, key="parcel-hypothesis-key-0002")
    assert duplicate.value.code is ErrorCode.CONFLICTING_EVIDENCE
    assert writer.write_count == 1
    assert writer.by_key[first.record.normalized_key] == first.record


@pytest.mark.parametrize("role", [None, WorkspaceRole.VIEWER])
def test_unauthorized_workspace_role_cannot_submit(role):
    app, writer, _ = service(role)
    with pytest.raises(VNextError) as denied:
        submit(app)
    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    assert writer.write_count == 0


def test_cross_workspace_and_property_targets_are_rejected():
    app, writer, _ = service()
    with pytest.raises(VNextError) as tenant:
        submit(app, workspace=OTHER_WORKSPACE)
    assert tenant.value.code is ErrorCode.PERMISSION_DENIED
    with pytest.raises(VNextError) as target:
        submit(app, property_id=OTHER_PROPERTY)
    assert target.value.code is ErrorCode.NOT_FOUND
    assert writer.write_count == 0


def test_existing_schema_guards_geometry_and_graph_without_new_migration():
    root = Path(__file__).resolve().parents[1]
    graph = (root / "database/migrations/014_vnext_property_graph_evidence_foundation.sql").read_text(encoding="utf-8")
    command = (root / "services/vnext/parcel_hypothesis_command.py").read_text(encoding="utf-8")
    assert "record.reference_type = new.node_type" in graph
    assert "new.relation_type = 'property_parcel'" in graph
    assert "selected_from_type <> 'property' or selected_to_type <> 'parcel'" in graph
    assert "before update or delete on vnext_core.property_identity_references" in graph
    assert "before update or delete on vnext_core.property_relations" in graph
    assert "parcel_geometry" not in command
    assert not list((root / "database/migrations").glob("018_*.sql"))
