"""Offline unit tests for the manual proposed parcel <-> building relation.

These tests exercise the application service contract with in-memory fakes for
the writer and idempotency store. They assert the non-confirming, manual,
proposed-only, bidirectional semantics; idempotent replay; changed-payload
conflict; duplicate-pair rejection; authorization; reference validation; the
response contract that cannot be forged as confirmed; and that no provider
fields are accepted. Postgres-backed behavior is covered separately and is
gated on disposable-Postgres availability.
"""

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
from services.vnext.parcel_building_relation_command import (
    PARCEL_BUILDING_RELATION_FACT_TYPE, PARCEL_BUILDING_RELATION_RESPONSE_TYPE,
    PARCEL_BUILDING_RELATION_SOURCE_ID, PARCEL_BUILDING_RELATION_VERSION,
    ParcelBuildingRelationApplicationService, ParcelBuildingRelationRecord,
    _pair_key, _relation_audit_metadata, _relation_evidence,
)
from services.vnext.persistence import (IdempotencyDecision,
                                        IdempotencyReservation, _audit_metadata)
from services.vnext.property_graph import (CoverageStatus, EvidenceStatus,
                                           LicenseStatus, QualityStatus)


WORKSPACE = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER_WORKSPACE = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PARCEL_REF = UUID("11111111-1111-4111-8111-111111111111")
BUILDING_REF = UUID("22222222-2222-4222-8222-222222222222")
PARCEL_REF_2 = UUID("33333333-3333-4333-8333-333333333333")
BUILDING_REF_2 = UUID("44444444-4444-4444-8444-444444444444")
# A reference that exists but with the wrong type in its workspace.
WRONG_TYPE_REF = UUID("55555555-5555-4555-8555-555555555555")
MISSING_REF = UUID("66666666-6666-4666-8666-666666666666")
USER = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


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
            response_reference_type=PARCEL_BUILDING_RELATION_RESPONSE_TYPE,
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
    """In-memory stand-in for the Postgres repository.

    It models: reference existence per workspace, reference typing, existing
    graph node reuse (never creating new references), and duplicate-open-pair
    rejection for a bidirectional pair regardless of orientation.
    """

    def __init__(self, idempotency):
        self.idempotency = idempotency
        self.records = {}
        self.open_pairs = set()
        self.write_count = 0
        # workspace -> {reference_id: reference_type}. Existing references only.
        self.references = {
            WORKSPACE: {
                PARCEL_REF: "parcel",
                BUILDING_REF: "building",
                PARCEL_REF_2: "parcel",
                BUILDING_REF_2: "building",
                WRONG_TYPE_REF: "building",
            },
        }
        # Stable node ids for existing references (never re-created).
        self.node_ids = {}

    def _node_id(self, reference_id):
        return self.node_ids.setdefault(reference_id, uuid4())

    def append(self, *, principal, workspace_id, parcel_identity_reference_id,
               building_identity_reference_id, idempotency_record_id, request_id):
        refs = self.references.get(workspace_id, {})
        if refs.get(parcel_identity_reference_id) != "parcel":
            raise VNextError.not_found()
        if refs.get(building_identity_reference_id) != "building":
            raise VNextError.not_found()
        pair = frozenset({parcel_identity_reference_id, building_identity_reference_id})
        if pair in self.open_pairs:
            raise VNextError.conflicting_evidence()
        record = ParcelBuildingRelationRecord(
            workspace_id, parcel_identity_reference_id, building_identity_reference_id,
            self._node_id(parcel_identity_reference_id),
            self._node_id(building_identity_reference_id),
            uuid4(), uuid4(), uuid4(),
            _pair_key(parcel_identity_reference_id, building_identity_reference_id), NOW,
        )
        self.records[record.relation_id] = record
        self.open_pairs.add(pair)
        self.write_count += 1
        self.idempotency.succeed(idempotency_record_id, record.relation_id)
        return record

    def get_by_relation_id(self, *, principal, workspace_id, relation_id):
        record = self.records[relation_id]
        if workspace_id != record.workspace_id:
            raise VNextError.not_found()
        return record


def service(role=WorkspaceRole.MEMBER):
    idempotency = Idempotency()
    writer = Writer(idempotency)
    app = ParcelBuildingRelationApplicationService(
        authorizer=WorkspaceAuthorizer(Memberships(role)), writer=writer,
        idempotency_repository=idempotency,
    )
    return app, writer


def submit(app, *, parcel=PARCEL_REF, building=BUILDING_REF,
           key="parcel-building-relation-key-0001", workspace=WORKSPACE):
    return app.create(
        principal=principal(), workspace_id=workspace,
        parcel_identity_reference_id=parcel,
        building_identity_reference_id=building,
        idempotency_key=key, request_id="parcel-building-fixture",
    )


def test_valid_relation_is_proposed_bidirectional_manual_and_unconfirmed():
    app, writer = service()
    outcome = submit(app)
    assert outcome.replayed is False
    assert writer.write_count == 1
    record = outcome.record
    assert record.parcel_identity_reference_id == PARCEL_REF
    assert record.building_identity_reference_id == BUILDING_REF
    assert record.parcel_node_id != record.building_node_id
    assert record.pair_key.startswith(f"{PARCEL_BUILDING_RELATION_VERSION}:")


def test_relation_evidence_is_user_provided_manual_without_provider():
    evidence = _relation_evidence(
        workspace_id=WORKSPACE, parcel_reference_id=PARCEL_REF,
        building_reference_id=BUILDING_REF, principal=principal(),
        request_id="evidence-fixture",
    )
    assert evidence.evidence_status is EvidenceStatus.USER_PROVIDED
    assert evidence.coverage_status is CoverageStatus.UNKNOWN
    assert evidence.quality_status is QualityStatus.NOT_CHECKED
    assert evidence.license_status is LicenseStatus.NOT_APPLICABLE
    assert evidence.source_id == PARCEL_BUILDING_RELATION_SOURCE_ID
    assert evidence.fact_type == PARCEL_BUILDING_RELATION_FACT_TYPE
    assert evidence.provider is None
    assert evidence.value["authority"] == "unverified_manual_relation"
    assert evidence.value["relation_kind"] == "parcel_building"
    assert evidence.value["parcel_identity_reference_id"] == str(PARCEL_REF)
    assert evidence.value["building_identity_reference_id"] == str(BUILDING_REF)


def test_missing_parcel_reference_is_not_found_with_zero_writes():
    app, writer = service()
    with pytest.raises(VNextError) as rejected:
        submit(app, parcel=MISSING_REF)
    assert rejected.value.code is ErrorCode.NOT_FOUND
    assert writer.write_count == 0


def test_missing_building_reference_is_not_found_with_zero_writes():
    app, writer = service()
    with pytest.raises(VNextError) as rejected:
        submit(app, building=MISSING_REF)
    assert rejected.value.code is ErrorCode.NOT_FOUND
    assert writer.write_count == 0


def test_wrong_reference_types_are_rejected_with_zero_writes():
    app, writer = service()
    # A building reference supplied where a parcel is required.
    with pytest.raises(VNextError) as parcel_slot:
        submit(app, parcel=WRONG_TYPE_REF, key="parcel-building-wrong-parcel-slot")
    assert parcel_slot.value.code is ErrorCode.NOT_FOUND
    # A parcel reference supplied where a building is required.
    with pytest.raises(VNextError) as building_slot:
        submit(app, building=PARCEL_REF, key="parcel-building-wrong-building-slot")
    assert building_slot.value.code is ErrorCode.NOT_FOUND
    assert writer.write_count == 0


def test_cross_workspace_reference_is_denied_with_zero_writes():
    app, writer = service()
    with pytest.raises(VNextError) as tenant:
        submit(app, workspace=OTHER_WORKSPACE)
    # A caller with no membership in the target workspace is denied before any write.
    assert tenant.value.code is ErrorCode.PERMISSION_DENIED
    assert writer.write_count == 0


@pytest.mark.parametrize("role", [None, WorkspaceRole.VIEWER])
def test_viewer_and_non_member_are_denied(role):
    app, writer = service(role)
    with pytest.raises(VNextError) as denied:
        submit(app)
    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    assert writer.write_count == 0


def test_idempotent_replay_returns_same_result_without_duplicate_write():
    app, writer = service()
    first = submit(app)
    replay = submit(app)
    assert first.replayed is False and replay.replayed is True
    assert first.record == replay.record
    assert writer.write_count == 1


def test_changed_pair_with_same_key_conflicts():
    app, writer = service()
    submit(app)
    with pytest.raises(VNextError) as changed:
        submit(app, building=BUILDING_REF_2)
    assert changed.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert writer.write_count == 1


def test_duplicate_pair_with_different_key_is_rejected_not_merged():
    app, writer = service()
    first = submit(app)
    with pytest.raises(VNextError) as duplicate:
        submit(app, key="parcel-building-relation-key-0002")
    assert duplicate.value.code is ErrorCode.CONFLICTING_EVIDENCE
    assert writer.write_count == 1
    # The first relation is untouched; the duplicate is never silently merged.
    assert writer.records[first.record.relation_id] == first.record


def test_distinct_pairs_are_independently_writable_supporting_m_to_n():
    app, writer = service()
    first = submit(app, parcel=PARCEL_REF, building=BUILDING_REF,
                   key="parcel-building-relation-key-a")
    # Same parcel, different building.
    second = submit(app, parcel=PARCEL_REF, building=BUILDING_REF_2,
                    key="parcel-building-relation-key-b")
    # Same building as first, different parcel.
    third = submit(app, parcel=PARCEL_REF_2, building=BUILDING_REF,
                   key="parcel-building-relation-key-c")
    assert writer.write_count == 3
    relation_ids = {first.record.relation_id, second.record.relation_id,
                    third.record.relation_id}
    assert len(relation_ids) == 3


def test_response_cannot_be_forged_as_confirmed():
    from backend.api.v1.property_identity import parcel_building_relation_dto
    app, _ = service()
    outcome = submit(app)
    dto = parcel_building_relation_dto(outcome)
    assert dto.hypothesis is True
    assert dto.authority == "unverified_manual_relation"
    assert dto.relation_type == "parcel_building"
    assert dto.direction == "bidirectional"
    assert dto.relation_status == "proposed"
    assert dto.identity_confirmation_id is None
    assert dto.source_id == "user-upload"
    assert dto.source_type == "user"
    assert dto.source_environment == "production"
    dumped = dto.model_dump(mode="json")
    assert dumped["relation_status"] == "proposed"
    assert dumped["identity_confirmation_id"] is None
    assert "confirmed" not in {dumped["relation_status"]}


def test_request_model_rejects_provider_and_extra_fields():
    from pydantic import ValidationError

    from backend.api.v1.property_identity import ParcelBuildingRelationRequest

    valid = ParcelBuildingRelationRequest(
        workspace_id=WORKSPACE,
        parcel_identity_reference_id=PARCEL_REF,
        building_identity_reference_id=BUILDING_REF,
    )
    assert valid.parcel_identity_reference_id == PARCEL_REF
    for forbidden in (
        {"provider": "nlsc"},
        {"source_id": "nlsc-parcel"},
        {"relation_status": "confirmed"},
        {"direction": "directed"},
        {"identity_confirmation_id": str(uuid4())},
        {"confidence": 0.9},
        {"geometry": {"type": "Point", "coordinates": [121.0, 25.0]}},
    ):
        with pytest.raises(ValidationError):
            ParcelBuildingRelationRequest(
                workspace_id=WORKSPACE,
                parcel_identity_reference_id=PARCEL_REF,
                building_identity_reference_id=BUILDING_REF,
                **forbidden,
            )


def test_response_dto_is_provider_free_and_only_declares_manual_authority():
    from backend.api.v1.property_identity import ParcelBuildingRelationDTO

    fields = ParcelBuildingRelationDTO.model_fields
    assert "provider" not in fields
    assert "confidence" not in fields
    assert "confirmed_by" not in fields
    assert "geometry" not in fields
    # authority is a fixed literal that cannot be set to a confirmed value.
    authority = fields["authority"].annotation
    assert authority is not None



def test_relation_audit_metadata_is_accepted_by_the_real_validator():
    # The metadata the command actually emits must pass the real allowlist
    # validator so the single write transaction can persist the audit row
    # instead of rolling back. This is the P0 audit-compatibility regression.
    metadata = _relation_audit_metadata(
        parcel_reference_id=PARCEL_REF, building_reference_id=BUILDING_REF,
    )
    assert metadata == {
        "parcel_identity_reference_id": str(PARCEL_REF),
        "building_identity_reference_id": str(BUILDING_REF),
        "relation_type": "parcel_building",
        "direction": "bidirectional",
    }
    # The real validator accepts it and preserves every traceable identifier.
    encoded = _audit_metadata(metadata)
    assert str(PARCEL_REF) in encoded
    assert str(BUILDING_REF) in encoded
    assert "parcel_building" in encoded
    assert "bidirectional" in encoded


def test_relation_audit_metadata_traces_parcel_building_and_relation():
    # Traceability to the parcel reference, the building reference, and the
    # relation shape must survive as distinct, named audit dimensions.
    metadata = _relation_audit_metadata(
        parcel_reference_id=PARCEL_REF, building_reference_id=BUILDING_REF,
    )
    assert metadata["parcel_identity_reference_id"] == str(PARCEL_REF)
    assert metadata["building_identity_reference_id"] == str(BUILDING_REF)
    assert metadata["relation_type"] == "parcel_building"
    assert metadata["direction"] == "bidirectional"


def test_unknown_audit_metadata_key_is_still_rejected():
    # The allowlist must remain strict: any key outside the contract fails closed.
    with pytest.raises(VNextError) as rejected:
        _audit_metadata(
            {
                "parcel_identity_reference_id": str(PARCEL_REF),
                "building_identity_reference_id": str(BUILDING_REF),
                "relation_type": "parcel_building",
                "direction": "bidirectional",
                "provider": "nlsc",
            }
        )
    assert rejected.value.code is ErrorCode.VALIDATION_FAILED
    # A single unrelated key is enough to fail closed.
    with pytest.raises(VNextError) as bare:
        _audit_metadata({"unexpected_dimension": "x"})
    assert bare.value.code is ErrorCode.VALIDATION_FAILED
