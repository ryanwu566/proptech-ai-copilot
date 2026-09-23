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
from services.vnext.feature_flags import VNextFeatureFlags
from services.vnext.parcel_evidence import (
    ParcelEvidenceEnvelope, ParcelQualityStatus, ParcelReviewState,
    canonical_parcel_evidence, parcel_evidence_draft,
)
from services.vnext.parcel_evidence_command import (
    PARCEL_EVIDENCE_RESPONSE_TYPE, ParcelEvidenceApplicationService,
    ParcelEvidenceRecord,
)
from services.vnext.persistence import IdempotencyDecision, IdempotencyReservation
from services.vnext.property_graph import EvidenceStatus

WORKSPACE = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER_WORKSPACE = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROPERTY = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
PARCEL = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
USER = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def envelope(**overrides):
    base = {
        "schema_version": "parcel-evidence-v1",
        "value": {"section": "A", "land_number": "123-4"},
        "source": {
            "source_id": "vnext-deterministic", "provider": "fixture-a",
            "dataset": "synthetic-candidates", "record_id": "candidate-a",
            "endpoint_class": "offline-fixture",
        },
        "retrieved_at": NOW,
        "effective_at": None,
        "coverage": {"spatial": "fixture-area", "temporal": None, "status": "partial"},
        "confidence": {"score": 0.7123456789, "method": "derived", "basis": "fixture-rule-v1"},
        "quality_status": "partial",
        "license": {
            "name": "fixture-only", "attribution": "Synthetic fixture",
            "retention": "ephemeral", "display_constraints": ["no-public-display"],
        },
        "identity_scope": "parcel",
        "review_state": "unreviewed",
        "transformations": [
            {"name": "whitespace-normalization", "version": "v1", "input_ref": "fixture:raw-a"},
        ],
        "raw_evidence_ref": "fixture:raw-a",
        "unknown_reason": None,
    }
    base.update(overrides)
    return base


def principal():
    return AuthenticatedPrincipal(USER, str(USER), "http://localhost/auth/v1", NOW)


class Memberships:
    def __init__(self, role=WorkspaceRole.MEMBER):
        self.role = role

    def get_active_membership(self, *, principal, workspace_id):
        if self.role is None or workspace_id != WORKSPACE:
            return None
        return WorkspaceMembership(workspace_id, principal.user_id, self.role)


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

    def succeed(self, record_id, evidence_id):
        scope = self.ids[record_id]
        self.records[scope] = replace(
            self.records[scope], operation_status="succeeded",
            response_reference_type=PARCEL_EVIDENCE_RESPONSE_TYPE,
            response_reference_id=evidence_id, response_status_code=201,
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
        self.by_hash = {}
        self.reference_status = "unverified"
        self.relation_status = "proposed"
        self.case_writes = 0

    def require_target(self, *, principal, workspace_id, property_entity_id, parcel_identity_reference_id):
        if (workspace_id, property_entity_id, parcel_identity_reference_id) != (WORKSPACE, PROPERTY, PARCEL):
            raise VNextError.not_found()

    def append(self, *, principal, workspace_id, property_entity_id, parcel_identity_reference_id,
               envelope, content_hash, idempotency_record_id, request_id):
        if content_hash in self.by_hash:
            record = self.by_hash[content_hash]
            duplicate = True
        else:
            record = ParcelEvidenceRecord(uuid4(), uuid4(), content_hash, NOW)
            self.by_hash[content_hash] = record
            self.records[record.evidence_id] = (record, envelope)
            duplicate = False
        self.idempotency.succeed(idempotency_record_id, record.evidence_id)
        return record, duplicate

    def get_by_evidence_id(self, *, principal, workspace_id, property_entity_id, parcel_identity_reference_id, evidence_id):
        self.require_target(principal=principal, workspace_id=workspace_id,
                            property_entity_id=property_entity_id,
                            parcel_identity_reference_id=parcel_identity_reference_id)
        return self.records[evidence_id][0]


def service(role=WorkspaceRole.MEMBER, enabled=True):
    idem = Idempotency()
    writer = Writer(idem)
    application = ParcelEvidenceApplicationService(
        flags=VNextFeatureFlags(identity_v1=enabled),
        authorizer=WorkspaceAuthorizer(Memberships(role)),
        writer=writer, idempotency_repository=idem,
    )
    return application, writer


def attach(application, *, evidence=None, key="parcel-evidence-key-0001", workspace=WORKSPACE,
           property_id=PROPERTY, parcel_id=PARCEL, actor=None):
    return application.attach(
        principal=principal() if actor is None else actor,
        workspace_id=workspace, property_entity_id=property_id,
        parcel_identity_reference_id=parcel_id,
        envelope=envelope() if evidence is None else evidence,
        idempotency_key=key, request_id="parcel-evidence-fixture",
    )


def test_valid_evidence_links_to_existing_hypothesis_and_preserves_provenance():
    application, writer = service()
    result = attach(application)
    assert result.replayed is False and result.duplicate is False
    assert result.envelope.value == {"section": "A", "land_number": "123-4"}
    assert result.envelope.raw_evidence_ref == "fixture:raw-a"
    assert result.envelope.transformations[0].name == "whitespace-normalization"
    assert result.envelope.source.record_id == "candidate-a"
    assert result.envelope.effective_at is None
    assert len(writer.records) == 1
    assert writer.reference_status == "unverified"
    assert writer.relation_status == "proposed"
    assert writer.case_writes == 0
    draft = parcel_evidence_draft(result.envelope)
    assert draft.source_id == "vnext-deterministic"
    assert draft.evidence_status is EvidenceStatus.LIMITED
    assert draft.raw_artifact_ref == "fixture:raw-a"
    assert draft.lineage["confidence"] == {
        "score": 0.7123456789, "method": "derived", "basis": "fixture-rule-v1",
    }
    assert draft.lineage["transformations"][0]["input_ref"] == "fixture:raw-a"
    assert draft.license["display_constraints"] == ["no-public-display"]


@pytest.mark.parametrize("reason,status", [
    ("not_found", EvidenceStatus.UNKNOWN),
    ("ambiguous", EvidenceStatus.UNKNOWN),
    ("auth_required", EvidenceStatus.UNAVAILABLE),
    ("provider_error", EvidenceStatus.UNAVAILABLE),
])
def test_absent_value_preserves_unknown_reason(reason, status):
    selected = ParcelEvidenceEnvelope.model_validate(envelope(
        value=None, unknown_reason=reason, quality_status="unavailable",
        review_state="unresolved", confidence={"score": None, "method": None, "basis": None},
    ))
    draft = parcel_evidence_draft(selected)
    assert draft.value is None
    assert draft.evidence_status is status
    assert draft.quality["unknown_reason"] == reason


def test_duplicate_normalized_evidence_and_same_key_replay_are_safe():
    application, writer = service()
    first = attach(application)
    replay = attach(application)
    duplicate = attach(application, key="parcel-evidence-key-0002")
    assert first.record == replay.record == duplicate.record
    assert replay.replayed is True and duplicate.duplicate is True
    assert len(writer.records) == 1


def test_same_key_different_payload_conflicts_and_hash_includes_provenance():
    application, writer = service()
    first = attach(application)
    changed = envelope(raw_evidence_ref="fixture:raw-b")
    assert canonical_parcel_evidence(ParcelEvidenceEnvelope.model_validate(changed))[1] != first.record.content_hash
    with pytest.raises(VNextError) as conflict:
        attach(application, evidence=changed)
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert len(writer.records) == 1


def test_conflicting_provider_observations_coexist_without_resolution():
    application, writer = service()
    first = attach(application)
    other = envelope(
        value={"section": "A", "land_number": "123-5"},
        source={"source_id": "vnext-deterministic", "provider": "fixture-b",
                "dataset": "synthetic-candidates", "record_id": "candidate-b",
                "endpoint_class": "offline-fixture"},
        quality_status="conflict", review_state="manual_review_required",
        raw_evidence_ref="fixture:raw-b",
    )
    second = attach(application, evidence=other, key="parcel-evidence-key-0003")
    assert first.record.evidence_id != second.record.evidence_id
    assert len(writer.records) == 2
    assert second.envelope.quality_status is ParcelQualityStatus.CONFLICT
    assert second.envelope.review_state is ParcelReviewState.MANUAL_REVIEW_REQUIRED
    assert parcel_evidence_draft(second.envelope).evidence_status is EvidenceStatus.CONFLICTING
    assert writer.reference_status == "unverified" and writer.relation_status == "proposed"


@pytest.mark.parametrize("change", [
    {"quality_status": "official"}, {"review_state": "confirmed"},
    {"identity_scope": "building"}, {"source": {"source_id": "nlsc-cadastral", "provider": "NLSC", "dataset": "x", "record_id": "1", "endpoint_class": "live"}},
    {"relation_status": "confirmed"}, {"authority": "official"},
    {"property_entity_id": str(PROPERTY)}, {"case_id": str(uuid4())},
    {"geometry_confirmation": True},
])
def test_official_or_mutating_fields_and_malformed_enums_fail_closed(change):
    application, writer = service()
    with pytest.raises(VNextError) as denied:
        attach(application, evidence=envelope(**change))
    assert denied.value.code is ErrorCode.VALIDATION_FAILED
    assert writer.records == {}


@pytest.mark.parametrize("confidence", [
    {"score": float("nan"), "method": "derived", "basis": "x"},
    {"score": float("inf"), "method": "derived", "basis": "x"},
    {"score": 1.2, "method": "derived", "basis": "x"},
    {"score": "0.5", "method": "derived", "basis": "x"},
    {"score": True, "method": "derived", "basis": "x"},
    {"score": 0.4, "method": "official", "basis": "x"},
    {"score": 0.4, "method": "derived", "basis": None},
])
def test_malformed_confidence_fails_closed(confidence):
    application, _ = service()
    with pytest.raises(VNextError) as invalid:
        attach(application, evidence=envelope(confidence=confidence))
    assert invalid.value.code is ErrorCode.VALIDATION_FAILED


@pytest.mark.parametrize("change", [
    {"value": None},
    {"value": None, "unknown_reason": "not_found", "quality_status": "available"},
    {"unknown_reason": "not_found"},
    {"quality_status": "conflict"},
])
def test_missing_value_and_conflict_combinations_fail_closed(change):
    application, _ = service()
    with pytest.raises(VNextError) as invalid:
        attach(application, evidence=envelope(**change))
    assert invalid.value.code is ErrorCode.VALIDATION_FAILED


def test_verified_labels_payload_validation_only_and_never_promotes_identity():
    application, writer = service()
    with pytest.raises(VNextError):
        attach(application, evidence=envelope(quality_status="verified"))
    evidence = envelope(
        quality_status="verified",
        transformations=[{"name": "payload-validation", "version": "v1", "input_ref": "fixture:raw-a"}],
    )
    result = attach(application, evidence=evidence, key="parcel-evidence-key-verified")
    assert result.envelope.quality_status is ParcelQualityStatus.VERIFIED
    assert parcel_evidence_draft(result.envelope).evidence_status is EvidenceStatus.AVAILABLE
    assert writer.reference_status == "unverified" and writer.relation_status == "proposed"


def test_auth_feature_role_and_workspace_isolation():
    application, writer = service()
    with pytest.raises(VNextError) as anonymous:
        attach(application, actor="forged")
    assert anonymous.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    with pytest.raises(VNextError) as tenant:
        attach(application, workspace=OTHER_WORKSPACE)
    assert tenant.value.code is ErrorCode.PERMISSION_DENIED
    with pytest.raises(VNextError) as target:
        attach(application, parcel_id=uuid4())
    assert target.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(VNextError) as viewer:
        attach(service(role=WorkspaceRole.VIEWER)[0])
    assert viewer.value.code is ErrorCode.PERMISSION_DENIED
    with pytest.raises(VNextError) as disabled:
        attach(service(enabled=False)[0])
    assert disabled.value.code is ErrorCode.NOT_FOUND
    assert writer.records == {}


def test_existing_graph_and_geometry_boundaries_are_untouched():
    root = Path(__file__).resolve().parents[1]
    command = (root / "services/vnext/parcel_evidence_command.py").read_text(encoding="utf-8")
    assert "INSERT INTO vnext_core.evidence_items" in command
    assert "INSERT INTO vnext_core.evidence_links" in command
    assert "UPDATE vnext_core.property_identity_references" not in command
    assert "UPDATE vnext_core.property_relations" not in command
    assert "INSERT INTO vnext_core.identity_decisions" not in command
    assert "vnext_core.cases" not in command
    assert "parcel_geometry" not in command
    assert [
        path.name for path in (root / "database/migrations").glob("018_*.sql")
    ] == ["018_vnext_case_parcel_set_v1.sql"]
    assert [
        path.name for path in (root / "database/migrations").glob("019_*.sql")
    ] == ["019_add_ris_village_demographics.sql"]
    assert not list((root / "database/migrations").glob("020_*.sql"))
