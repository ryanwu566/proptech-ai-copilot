from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import (
    WorkspaceAuthorizer,
    WorkspaceMembership,
    WorkspaceMembershipStatus,
    WorkspaceRole,
)
from services.vnext.errors import VNextError
from services.vnext.property_graph import (
    CoverageStatus,
    EvidenceDraft,
    EvidenceLineageType,
    EvidenceLinkType,
    EvidenceStatus,
    EvidenceTransformation,
    IdentityReferenceDraft,
    IdentityReferenceStatus,
    IdentityReferenceType,
    LicenseStatus,
    PostgresEvidenceRepository,
    PostgresPropertyGraphRepository,
    PropertyRelationDraft,
    PropertyRelationStatus,
    PropertyRelationType,
    QualityStatus,
    RelationDirection,
    SourceEnvironment,
)


USER_A = UUID("11111111-1111-4111-8111-111111111111")
WORKSPACE_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
WORKSPACE_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROPERTY_ID = UUID("10000000-0000-4000-8000-000000000001")
PROPERTY_NODE_ID = UUID("20000000-0000-4000-8000-000000000001")
REFERENCE_ID = UUID("30000000-0000-4000-8000-000000000001")
REFERENCE_ID_2 = UUID("30000000-0000-4000-8000-000000000002")
REFERENCE_NODE_ID = UUID("40000000-0000-4000-8000-000000000001")
REFERENCE_NODE_ID_2 = UUID("40000000-0000-4000-8000-000000000002")
RELATION_ID = UUID("50000000-0000-4000-8000-000000000001")
EVIDENCE_ID = UUID("60000000-0000-4000-8000-000000000001")
EVIDENCE_ID_2 = UUID("60000000-0000-4000-8000-000000000002")
LINEAGE_ID = UUID("70000000-0000-4000-8000-000000000001")
LINK_ID = UUID("80000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)


PRINCIPAL = AuthenticatedPrincipal(
    user_id=USER_A,
    token_subject=str(USER_A),
    issuer="https://fixture.supabase.co/auth/v1",
    token_issued_at=NOW,
)


class _Memberships:
    def __init__(self, memberships: list[WorkspaceMembership]) -> None:
        self._memberships = {
            (membership.workspace_id, membership.user_id): membership
            for membership in memberships
        }

    def get_active_membership(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
    ) -> WorkspaceMembership | None:
        return self._memberships.get((workspace_id, principal.user_id))


def _authorizer(
    role: WorkspaceRole = WorkspaceRole.MEMBER,
    *,
    workspace_id: UUID = WORKSPACE_A,
    status: WorkspaceMembershipStatus = WorkspaceMembershipStatus.ACTIVE,
) -> WorkspaceAuthorizer:
    return WorkspaceAuthorizer(
        _Memberships(
            [WorkspaceMembership(workspace_id, USER_A, role, status)]
        )
    )


class _Result:
    def __init__(self, row: tuple[object, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[object, ...] | None:
        return self._row


class _Connection:
    def __init__(self, rows: list[tuple[object, ...] | None]) -> None:
        self._rows = list(rows)
        self.calls: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(
        self,
        statement: str,
        params: tuple[object, ...] | None = None,
    ) -> _Result:
        self.calls.append((" ".join(statement.lower().split()), params))
        if not self._rows:
            raise AssertionError(f"no scripted result for: {statement}")
        return _Result(self._rows.pop(0))


class _Context:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.principals: list[AuthenticatedPrincipal] = []

    @contextmanager
    def transaction(self, principal: AuthenticatedPrincipal):
        self.principals.append(principal)
        yield self.connection


def _property_row(*, workspace_id: UUID = WORKSPACE_A) -> tuple[object, ...]:
    return (
        PROPERTY_ID,
        workspace_id,
        "unverified",
        "No. 1 Example Road",
        1,
        USER_A,
        NOW,
        NOW,
        None,
    )


def _reference_row(
    reference_id: UUID = REFERENCE_ID,
    *,
    reference_type: str = "address",
) -> tuple[object, ...]:
    return (
        reference_id,
        WORKSPACE_A,
        reference_type,
        f"normalized:{reference_id}",
        "Source observation",
        "vnext-test",
        "test",
        "test",
        f"record:{reference_id}",
        0.75,
        "fixture",
        "unverified",
        NOW,
        None,
        None,
        USER_A,
        NOW,
    )


def _relation_row() -> tuple[object, ...]:
    return (
        RELATION_ID,
        WORKSPACE_A,
        PROPERTY_NODE_ID,
        REFERENCE_NODE_ID,
        "property_address",
        "directed",
        0.8,
        "fixture",
        "vnext-test",
        "test",
        "test",
        None,
        "proposed",
        NOW,
        None,
        None,
        USER_A,
        NOW,
    )


def _evidence_row(
    evidence_id: UUID = EVIDENCE_ID,
    *,
    source_id: str = "user-upload",
    source_type: str = "user",
    source_environment: str = "production",
    status: str = "user_provided",
    value: object | None = '{"amount":12000000}',
    version: int = 1,
    supersedes: UUID | None = None,
) -> tuple[object, ...]:
    return (
        evidence_id,
        WORKSPACE_A,
        "property.assessed_value",
        value,
        None,
        "money-twd-v1",
        source_id,
        source_type,
        source_environment,
        None,
        "source-record-1",
        NOW,
        NOW - timedelta(days=30),
        None,
        None,
        "known",
        '{"geography":"property"}',
        status,
        0.9,
        "manual-review",
        "passed",
        '{"checks":["shape"]}',
        "approved",
        "license-record-1",
        '{"redistribution":false}',
        '{"capture":"manual"}',
        "a" * 64,
        version,
        "artifact:fixture-1",
        supersedes,
        USER_A,
        None,
        NOW,
    )


def _evidence_draft(**overrides: object) -> EvidenceDraft:
    values: dict[str, object] = {
        "fact_type": "property.assessed_value",
        "source_id": "user-upload",
        "source_environment": SourceEnvironment.PRODUCTION,
        "retrieved_at": NOW,
        "coverage_status": CoverageStatus.KNOWN,
        "coverage": {"geography": "property"},
        "evidence_status": EvidenceStatus.USER_PROVIDED,
        "quality_status": QualityStatus.PASSED,
        "quality": {"checks": ["shape"]},
        "license_status": LicenseStatus.APPROVED,
        "license": {"redistribution": False},
        "value": {"amount": 12_000_000},
        "value_schema": "money-twd-v1",
        "source_record_id": "source-record-1",
        "effective_from": NOW - timedelta(days=30),
        "quality_confidence": 0.9,
        "quality_method": "manual-review",
        "license_ref": "license-record-1",
        "lineage": {"capture": "manual"},
        "raw_artifact_ref": "artifact:fixture-1",
    }
    values.update(overrides)
    return EvidenceDraft(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "role",
    [
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.MANAGER,
        WorkspaceRole.MEMBER,
    ],
)
def test_every_writer_role_can_create_an_unverified_property(role: WorkspaceRole) -> None:
    connection = _Connection([_property_row(), (PROPERTY_NODE_ID,)])
    context = _Context(connection)
    repository = PostgresPropertyGraphRepository(context, _authorizer(role))

    record = repository.create_property_entity(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        display_label="  No. 1 Example Road  ",
    )

    assert record.entity_status.value == "unverified"
    assert record.property_graph_node_id == PROPERTY_NODE_ID
    assert connection.calls[0][1] == (WORKSPACE_A, "No. 1 Example Road", USER_A)
    assert "'unverified'" in connection.calls[0][0]
    assert context.principals == [PRINCIPAL]


@pytest.mark.parametrize(
    ("role", "status"),
    [
        (WorkspaceRole.VIEWER, WorkspaceMembershipStatus.ACTIVE),
        (WorkspaceRole.OWNER, WorkspaceMembershipStatus.REMOVED),
    ],
)
def test_viewer_and_revoked_member_cannot_create_property(
    role: WorkspaceRole,
    status: WorkspaceMembershipStatus,
) -> None:
    context = _Context(_Connection([]))
    repository = PostgresPropertyGraphRepository(
        context,
        _authorizer(role, status=status),
    )

    with pytest.raises(VNextError) as error:
        repository.create_property_entity(
            principal=PRINCIPAL,
            workspace_id=WORKSPACE_A,
            display_label="Denied",
        )

    assert error.value.code.value == "permission_denied"
    assert context.principals == []


def test_viewer_can_read_property_but_cross_workspace_row_is_hidden() -> None:
    visible = PostgresPropertyGraphRepository(
        _Context(_Connection([_property_row() + (PROPERTY_NODE_ID,)])),
        _authorizer(WorkspaceRole.VIEWER),
    )
    assert visible.get_property_entity(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        property_entity_id=PROPERTY_ID,
    ).property_entity_id == PROPERTY_ID

    hidden = PostgresPropertyGraphRepository(
        _Context(_Connection([None])),
        _authorizer(WorkspaceRole.VIEWER, workspace_id=WORKSPACE_B),
    )
    with pytest.raises(VNextError) as error:
        hidden.get_property_entity(
            principal=PRINCIPAL,
            workspace_id=WORKSPACE_B,
            property_entity_id=PROPERTY_ID,
        )
    assert error.value.code.value == "not_found"


def test_multiple_conflicting_identity_observations_remain_separate_rows() -> None:
    connection = _Connection(
        [
            _reference_row(),
            (REFERENCE_NODE_ID,),
            _reference_row(REFERENCE_ID_2),
            (REFERENCE_NODE_ID_2,),
        ]
    )
    repository = PostgresPropertyGraphRepository(connection_context := _Context(connection), _authorizer())

    first = repository.append_identity_reference(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        draft=IdentityReferenceDraft(
            reference_type=IdentityReferenceType.ADDRESS,
            normalized_key="taipei:example:1",
            display_value="Example Road 1",
            source_id="vnext-test",
            source_environment=SourceEnvironment.TEST,
            confidence=0.75,
            confidence_method="fixture",
            valid_from=NOW,
        ),
    )
    second = repository.append_identity_reference(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        draft=IdentityReferenceDraft(
            reference_type=IdentityReferenceType.ADDRESS,
            normalized_key="taipei:example:1-conflict",
            display_value="Example Rd. No. 1",
            source_id="vnext-test",
            source_environment=SourceEnvironment.TEST,
            reference_status=IdentityReferenceStatus.DISPUTED,
        ),
    )

    assert first.identity_reference_id != second.identity_reference_id
    assert first.property_graph_node_id != second.property_graph_node_id
    assert len(connection_context.principals) == 2
    assert all("on conflict" not in sql for sql, _ in connection.calls)


def test_unregistered_and_non_request_sources_are_rejected_before_database_use() -> None:
    for source_id, environment in (
        ("arbitrary-source", SourceEnvironment.PRODUCTION),
        ("moi-dla-plvr", SourceEnvironment.PRODUCTION),
    ):
        context = _Context(_Connection([]))
        repository = PostgresPropertyGraphRepository(context, _authorizer())
        with pytest.raises(VNextError) as error:
            repository.append_identity_reference(
                principal=PRINCIPAL,
                workspace_id=WORKSPACE_A,
                draft=IdentityReferenceDraft(
                    reference_type=IdentityReferenceType.PARCEL,
                    normalized_key="parcel-1",
                    display_value="Parcel 1",
                    source_id=source_id,
                    source_environment=environment,
                ),
            )
        assert error.value.code.value == "permission_denied"
        assert context.principals == []


def test_relation_append_preserves_type_direction_time_and_source() -> None:
    connection = _Connection([_relation_row()])
    repository = PostgresPropertyGraphRepository(_Context(connection), _authorizer())

    relation = repository.append_relation(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        draft=PropertyRelationDraft(
            from_node_id=PROPERTY_NODE_ID,
            to_node_id=REFERENCE_NODE_ID,
            relation_type=PropertyRelationType.PROPERTY_ADDRESS,
            direction=RelationDirection.DIRECTED,
            source_id="vnext-test",
            source_environment=SourceEnvironment.TEST,
            relation_status=PropertyRelationStatus.PROPOSED,
            confidence=0.8,
            confidence_method="fixture",
            valid_from=NOW,
        ),
    )

    assert relation.property_relation_id == RELATION_ID
    assert relation.relation_type is PropertyRelationType.PROPERTY_ADDRESS
    assert relation.direction is RelationDirection.DIRECTED
    assert connection.calls[0][1][7:10] == ("vnext-test", "test", "test")


def test_viewer_can_read_a_relation_and_cross_workspace_relation_is_hidden() -> None:
    visible = PostgresPropertyGraphRepository(
        _Context(_Connection([_relation_row()])),
        _authorizer(WorkspaceRole.VIEWER),
    )
    assert visible.get_relation(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        property_relation_id=RELATION_ID,
    ).property_relation_id == RELATION_ID

    hidden = PostgresPropertyGraphRepository(
        _Context(_Connection([None])),
        _authorizer(WorkspaceRole.VIEWER, workspace_id=WORKSPACE_B),
    )
    with pytest.raises(VNextError) as error:
        hidden.get_relation(
            principal=PRINCIPAL,
            workspace_id=WORKSPACE_B,
            property_relation_id=RELATION_ID,
        )
    assert error.value.code.value == "not_found"


def test_relation_confirmation_and_invalid_temporal_or_directional_shapes_are_deferred() -> None:
    repository = PostgresPropertyGraphRepository(_Context(_Connection([])), _authorizer())
    base = {
        "from_node_id": PROPERTY_NODE_ID,
        "to_node_id": REFERENCE_NODE_ID,
        "relation_type": PropertyRelationType.PROPERTY_ADDRESS,
        "direction": RelationDirection.DIRECTED,
        "source_id": "vnext-test",
        "source_environment": SourceEnvironment.TEST,
    }
    invalid = (
        PropertyRelationDraft(**base, relation_status=PropertyRelationStatus.CONFIRMED),
        PropertyRelationDraft(**base, valid_from=NOW, valid_to=NOW - timedelta(seconds=1)),
        PropertyRelationDraft(**{**base, "direction": RelationDirection.BIDIRECTIONAL}),
        PropertyRelationDraft(**base, relation_status=PropertyRelationStatus.SUPERSEDED),
    )

    for draft in invalid:
        with pytest.raises(VNextError):
            repository.append_relation(
                principal=PRINCIPAL,
                workspace_id=WORKSPACE_A,
                draft=draft,
            )


def test_user_evidence_preserves_provenance_status_quality_license_and_hash() -> None:
    connection = _Connection([_evidence_row()])
    repository = PostgresEvidenceRepository(_Context(connection), _authorizer())

    evidence = repository.append_evidence(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        draft=_evidence_draft(),
    )

    assert evidence.evidence_status is EvidenceStatus.USER_PROVIDED
    assert evidence.source_id == "user-upload"
    assert evidence.coverage == {"geography": "property"}
    assert evidence.quality == {"checks": ["shape"]}
    assert evidence.license == {"redistribution": False}
    params = connection.calls[0][1]
    assert params is not None
    assert params[5:8] == ("user-upload", "user", "production")
    assert len(str(params[25])) == 64


@pytest.mark.parametrize("status", [EvidenceStatus.UNKNOWN, EvidenceStatus.UNAVAILABLE])
def test_unknown_and_unavailable_are_explicit_null_value_states(status: EvidenceStatus) -> None:
    connection = _Connection([
        _evidence_row(status=status.value, value=None),
    ])
    repository = PostgresEvidenceRepository(_Context(connection), _authorizer())

    record = repository.append_evidence(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        draft=_evidence_draft(evidence_status=status, value=None),
    )

    assert record.evidence_status is status
    assert record.value is None


def test_unknown_with_value_and_test_available_are_rejected() -> None:
    repository = PostgresEvidenceRepository(_Context(_Connection([])), _authorizer())
    invalid = (
        _evidence_draft(evidence_status=EvidenceStatus.UNKNOWN),
        _evidence_draft(
            source_id="vnext-test",
            source_environment=SourceEnvironment.TEST,
            evidence_status=EvidenceStatus.AVAILABLE,
        ),
    )

    for draft in invalid:
        with pytest.raises(VNextError) as error:
            repository.append_evidence(
                principal=PRINCIPAL,
                workspace_id=WORKSPACE_A,
                draft=draft,
            )
        assert error.value.code.value == "validation_failed"


def test_nonfinite_confidence_and_naive_temporal_values_are_rejected() -> None:
    repository = PostgresEvidenceRepository(_Context(_Connection([])), _authorizer())
    invalid = (
        _evidence_draft(quality_confidence=float("nan")),
        _evidence_draft(retrieved_at=datetime(2026, 8, 30, 12)),
        _evidence_draft(expires_at=datetime(2026, 9, 1, 12)),
    )

    for draft in invalid:
        with pytest.raises(VNextError) as error:
            repository.append_evidence(
                principal=PRINCIPAL,
                workspace_id=WORKSPACE_A,
                draft=draft,
            )
        assert error.value.code.value == "validation_failed"


def test_superseding_evidence_appends_version_and_lineage_without_mutating_parent() -> None:
    connection = _Connection(
        [
            (1,),
            _evidence_row(EVIDENCE_ID_2, version=2, supersedes=EVIDENCE_ID),
            None,
        ]
    )
    repository = PostgresEvidenceRepository(_Context(connection), _authorizer())

    record = repository.append_evidence(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        draft=_evidence_draft(
            evidence_status=EvidenceStatus.STALE,
            supersedes_evidence_id=EVIDENCE_ID,
        ),
    )

    assert record.evidence_version == 2
    assert record.supersedes_evidence_id == EVIDENCE_ID
    assert connection.calls[0][0].startswith("select evidence_version")
    assert connection.calls[2][1] == (WORKSPACE_A, EVIDENCE_ID_2, EVIDENCE_ID, USER_A)
    assert not any(sql.startswith("update ") for sql, _ in connection.calls)


def test_viewer_can_read_registered_official_evidence_but_cannot_append() -> None:
    official = _evidence_row(
        source_id="moi-dla-plvr",
        source_type="official",
        status="available",
    )
    context = _Context(_Connection([official]))
    repository = PostgresEvidenceRepository(context, _authorizer(WorkspaceRole.VIEWER))

    record = repository.get_evidence(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        evidence_id=EVIDENCE_ID,
    )
    assert record.source_type.value == "official"
    assert record.evidence_status is EvidenceStatus.AVAILABLE

    with pytest.raises(VNextError) as error:
        repository.append_evidence(
            principal=PRINCIPAL,
            workspace_id=WORKSPACE_A,
            draft=_evidence_draft(),
        )
    assert error.value.code.value == "permission_denied"
    assert context.principals == [PRINCIPAL]


def test_multi_parent_lineage_and_graph_links_are_append_only_operations() -> None:
    connection = _Connection([(LINEAGE_ID,), (LINK_ID,)])
    repository = PostgresEvidenceRepository(_Context(connection), _authorizer())

    lineage_id = repository.append_lineage(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        child_evidence_id=EVIDENCE_ID_2,
        parent_evidence_id=EVIDENCE_ID,
        lineage_type=EvidenceLineageType.CALCULATED_FROM,
        transformation=EvidenceTransformation.CALCULATION,
        transformation_version="valuation-v1",
    )
    link_id = repository.link_evidence(
        principal=PRINCIPAL,
        workspace_id=WORKSPACE_A,
        evidence_id=EVIDENCE_ID_2,
        subject_node_id=PROPERTY_NODE_ID,
        link_type=EvidenceLinkType.SUPPORTS,
        fact_scope="property.assessed_value",
    )

    assert lineage_id == LINEAGE_ID
    assert link_id == LINK_ID
    assert connection.calls[0][1] == (
        WORKSPACE_A,
        EVIDENCE_ID_2,
        EVIDENCE_ID,
        "calculated_from",
        "calculation",
        "valuation-v1",
        USER_A,
    )
    assert connection.calls[1][1] == (
        WORKSPACE_A,
        EVIDENCE_ID_2,
        PROPERTY_NODE_ID,
        "supports",
        "property.assessed_value",
        USER_A,
    )
