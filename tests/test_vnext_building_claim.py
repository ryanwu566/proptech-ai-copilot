from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer, WorkspaceMembership, WorkspaceRole
from services.vnext.building_claim import BUILDING_CLAIM_VERSION, normalize_building_claim
from services.vnext.building_claim_command import (
    BUILDING_CLAIM_RESPONSE_TYPE, BuildingClaimApplicationService,
    BuildingClaimRecord, _claim_evidence,
)
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.persistence import IdempotencyDecision, IdempotencyReservation
from services.vnext.property_graph import CoverageStatus, EvidenceStatus, QualityStatus


WORKSPACE = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PROPERTY = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
USER = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)
COMPONENTS = {
    "county_city": "臺北市",
    "district_township": "中正區",
    "section": "城中段",
    "subsection_status": "not_applicable",
    "subsection": None,
    "building_number": "１２３－４",
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
        self.keys = {}

    def reserve(self, **kwargs):
        scope = (kwargs["workspace_id"], kwargs["principal"].user_id,
                 kwargs["canonical_route"], kwargs["idempotency_key"])
        fingerprint = hashlib.sha256(kwargs["canonical_request"]).hexdigest()
        if scope in self.records:
            record = self.records[scope]
            if record.request_fingerprint != fingerprint:
                raise VNextError.idempotency_conflict()
            return replace(record, decision=IdempotencyDecision.REPLAY)
        record = IdempotencyReservation(IdempotencyDecision.NEW, uuid4(), fingerprint,
                                        "pending", None, None)
        self.records[scope] = record
        self.keys[record.idempotency_record_id] = scope
        return record

    def succeed(self, record_id, relation_id):
        scope = self.keys[record_id]
        self.records[scope] = replace(
            self.records[scope], operation_status="succeeded",
            response_reference_type=BUILDING_CLAIM_RESPONSE_TYPE,
            response_reference_id=relation_id, response_status_code=201,
        )

    def mark_failed(self, **kwargs):
        scope = self.keys[kwargs["idempotency_record_id"]]
        self.records[scope] = replace(
            self.records[scope], operation_status="failed",
            response_error_code=kwargs["response_error_code"],
            response_status_code=kwargs["response_status_code"],
        )


class Writer:
    def __init__(self, idempotency):
        self.idempotency = idempotency
        self.records = {}
        self.write_count = 0

    def require_property(self, *, principal, workspace_id, property_entity_id):
        if workspace_id != WORKSPACE or property_entity_id != PROPERTY:
            raise VNextError.not_found()

    def append(self, *, principal, workspace_id, property_entity_id,
               normalized, idempotency_record_id, request_id):
        record = BuildingClaimRecord(
            property_entity_id, uuid4(), uuid4(), uuid4(), uuid4(), uuid4(),
            normalized.normalized_key, normalized.display_value, NOW,
        )
        self.records[record.relation_id] = record
        self.write_count += 1
        self.idempotency.succeed(idempotency_record_id, record.relation_id)
        return record

    def get_by_relation_id(self, *, principal, workspace_id, property_entity_id, relation_id):
        record = self.records[relation_id]
        if workspace_id != WORKSPACE or property_entity_id != record.property_entity_id:
            raise VNextError.not_found()
        return record


def service(role=WorkspaceRole.MEMBER):
    idempotency = Idempotency()
    writer = Writer(idempotency)
    app = BuildingClaimApplicationService(
        authorizer=WorkspaceAuthorizer(Memberships(role)), writer=writer,
        idempotency_repository=idempotency,
    )
    return app, writer


def submit(app, *, components=None, key="building-claim-key-0001",
           workspace=WORKSPACE, property_id=PROPERTY):
    return app.create(
        principal=principal(), workspace_id=workspace, property_entity_id=property_id,
        components=COMPONENTS if components is None else components,
        idempotency_key=key, request_id="building-claim-fixture",
    )


def test_normalization_preserves_raw_and_fails_closed_on_ambiguous_scope():
    normalized = normalize_building_claim(COMPONENTS)
    equivalent = normalize_building_claim({**COMPONENTS, "building_number": "123-4"})
    assert normalized.normalized_key == equivalent.normalized_key
    assert normalized.normalized_key.startswith(f"{BUILDING_CLAIM_VERSION}:")
    assert normalized.raw_input["building_number"] == "１２３－４"
    assert normalized.normalized_components["building_number"] == "123-4"
    assert "manual cadastral claim" in normalized.display_value
    for invalid in (
        {**COMPONENTS, "section": ""},
        {**COMPONENTS, "subsection_status": "unknown"},
        {**COMPONENTS, "subsection_status": "specified"},
        {**COMPONENTS, "subsection": "一小段"},
        {**COMPONENTS, "building_number": "建號123"},
        {**COMPONENTS, "building_number": "123 4"},
        {**COMPONENTS, "community": "Example"},
    ):
        with pytest.raises(VNextError) as rejected:
            normalize_building_claim(invalid)
        assert rejected.value.code is ErrorCode.VALIDATION_FAILED


def test_raw_claim_evidence_keeps_input_separate_from_reference():
    normalized = normalize_building_claim(COMPONENTS)
    evidence = _claim_evidence(
        normalized=normalized, property_entity_id=PROPERTY,
        principal=principal(), request_id="claim-evidence-fixture",
    )
    assert evidence.value["raw_input"] == COMPONENTS
    assert evidence.value["normalized_components"]["building_number"] == "123-4"
    assert evidence.value["property_entity_id"] == str(PROPERTY)
    assert evidence.value["actor_user_id"] == str(USER)
    assert evidence.evidence_status is EvidenceStatus.USER_PROVIDED
    assert evidence.coverage_status is CoverageStatus.UNKNOWN
    assert evidence.quality_status is QualityStatus.NOT_CHECKED
    assert evidence.provider is None


def test_replay_returns_same_result_and_changed_payload_conflicts():
    app, writer = service()
    first = submit(app)
    replay = submit(app)
    assert first.replayed is False and replay.replayed is True
    assert first.record == replay.record
    assert writer.write_count == 1
    with pytest.raises(VNextError) as changed:
        submit(app, components={**COMPONENTS, "building_number": "123-5"})
    assert changed.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert writer.write_count == 1


@pytest.mark.parametrize("role", [None, WorkspaceRole.VIEWER])
def test_non_writer_cannot_submit(role):
    app, writer = service(role)
    with pytest.raises(VNextError) as rejected:
        submit(app)
    assert rejected.value.code is ErrorCode.PERMISSION_DENIED
    assert writer.write_count == 0


def test_wrong_workspace_and_property_have_zero_writes():
    app, writer = service()
    with pytest.raises(VNextError) as wrong_workspace:
        submit(app, workspace=uuid4())
    assert wrong_workspace.value.code is ErrorCode.PERMISSION_DENIED
    with pytest.raises(VNextError) as wrong_property:
        submit(app, property_id=uuid4())
    assert wrong_property.value.code is ErrorCode.NOT_FOUND
    assert writer.write_count == 0
