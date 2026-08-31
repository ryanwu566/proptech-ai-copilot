from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.api.v1.property_identity import (
    get_cursor_codec,
    get_property_read_repository,
    get_resolution_application_service,
)
from backend.api_main import app
from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier
from services.vnext.authorization import (
    WorkspaceAuthorizer,
    WorkspaceMembership,
    WorkspaceRole,
    get_workspace_authorizer,
)
from services.vnext.errors import VNextError
from services.vnext.feature_flags import VNextFeatureFlags, get_vnext_feature_flags
from services.vnext.identity_resolution import (
    AmbiguityStatus,
    IdentityCandidateStatus,
    IdentityCandidateType,
    ResolutionAttemptStatus,
    ResolutionInputType,
    ResolutionStatus,
    normalize_resolution_input,
)
from services.vnext.identity_resolution_repository import (
    IdentityCandidateRecord,
    IdentityResolutionRecord,
    ResolutionAttemptRecord,
)
from services.vnext.identity_resolution_service import ResolutionCreateOutcome
from services.vnext.pagination import CursorCodec
from services.vnext.property_graph import (
    CoverageStatus,
    EvidenceRecord,
    EvidenceStatus,
    LicenseStatus,
    PropertyEntityRecord,
    PropertyEntityStatus,
    PropertyRelationRecord,
    PropertyRelationStatus,
    PropertyRelationType,
    QualityStatus,
    RelationDirection,
    SourceEnvironment,
    SourceType,
)
from services.vnext.property_read_repository import (
    EvidencePosition,
    GraphPosition,
    PropertyEvidencePage,
    PropertyGraphNodeRecord,
    PropertyGraphPage,
)

NOW = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
ISSUER = "https://fixture-project.supabase.co/auth/v1"
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-4222-8222-222222222222")
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
RESOLUTION_ID = UUID("aaaaaaaa-1111-4111-8111-111111111111")
CANDIDATE_ID = UUID("aaaaaaaa-2222-4222-8222-222222222222")
ATTEMPT_ID = UUID("aaaaaaaa-3333-4333-8333-333333333333")
PROPERTY_ID = UUID("aaaaaaaa-4444-4444-8444-444444444444")
PROPERTY_NODE_ID = UUID("aaaaaaaa-5555-4555-8555-555555555555")
ADDRESS_NODE_ID = UUID("aaaaaaaa-6666-4666-8666-666666666666")
ADDRESS_ID = UUID("aaaaaaaa-7777-4777-8777-777777777777")
RELATION_ID = UUID("aaaaaaaa-8888-4888-8888-888888888888")
EVIDENCE_UNKNOWN_ID = UUID("aaaaaaaa-9999-4999-8999-999999999991")
EVIDENCE_LIMITED_ID = UUID("aaaaaaaa-9999-4999-8999-999999999992")
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()


def _token(user_id: UUID = USER_ID, *, private_key=PRIVATE_KEY) -> str:
    issued_at = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iss": ISSUER,
            "aud": "authenticated",
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "fixture-key"},
    )


def _principal(user_id: UUID = USER_ID):
    from services.vnext.auth import AuthenticatedPrincipal

    return AuthenticatedPrincipal(
        user_id=user_id,
        token_subject=str(user_id),
        issuer=ISSUER,
        token_issued_at=NOW,
    )


class _Memberships:
    def __init__(self, role: WorkspaceRole | None, user_id: UUID) -> None:
        self.role = role
        self.user_id = user_id

    def get_active_membership(self, *, principal, workspace_id):
        if (
            self.role is None
            or principal.user_id != self.user_id
            or workspace_id != WORKSPACE_ID
        ):
            return None
        return WorkspaceMembership(WORKSPACE_ID, self.user_id, self.role)


def _resolution_record() -> IdentityResolutionRecord:
    attempt = ResolutionAttemptRecord(
        resolution_attempt_id=ATTEMPT_ID,
        workspace_id=WORKSPACE_ID,
        identity_resolution_id=RESOLUTION_ID,
        attempt_order=1,
        strategy_id="fixture-v1",
        provider_id="fixture-provider",
        source_id="vnext-test",
        source_type=SourceType.TEST,
        source_environment=SourceEnvironment.TEST,
        status=ResolutionAttemptStatus.AVAILABLE,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
        result_count=1,
        error_category=None,
        error_code=None,
        error_retryable=None,
        started_at=NOW,
        completed_at=NOW,
        retrieved_at=NOW,
        created_by_user_id=USER_ID,
        created_at=NOW,
    )
    candidate = IdentityCandidateRecord(
        identity_candidate_id=CANDIDATE_ID,
        workspace_id=WORKSPACE_ID,
        identity_resolution_id=RESOLUTION_ID,
        candidate_type=IdentityCandidateType.ADDRESS,
        normalized_key="address:fixture",
        normalized_identity={"address": "Fixture"},
        display_identity="Fixture",
        source_id="vnext-test",
        source_type=SourceType.TEST,
        source_environment=SourceEnvironment.TEST,
        source_record_id="fixture-1",
        retrieved_at=NOW,
        confidence=1.0,
        confidence_method="identity-ranking-v1",
        ranking_factors={"method": "identity-ranking-v1", "final_confidence": 1.0},
        rank=1,
        candidate_status=IdentityCandidateStatus.PLAUSIBLE,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
        supporting_evidence_ids=(EVIDENCE_LIMITED_ID,),
        supporting_reference_ids=(ADDRESS_ID,),
        possible_existing_property_entity_id=PROPERTY_ID,
        supersedes_candidate_id=None,
        needs_human_confirmation=True,
        created_by_user_id=USER_ID,
        created_at=NOW,
    )
    return IdentityResolutionRecord(
        identity_resolution_id=RESOLUTION_ID,
        workspace_id=WORKSPACE_ID,
        case_id=None,
        resolution_input=normalize_resolution_input(
            ResolutionInputType.ADDRESS,
            {"address": "Fixture"},
        ),
        status=ResolutionStatus.CANDIDATES_FOUND,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"attempt_count": 1},
        ambiguity_status=AmbiguityStatus.NONE,
        needs_human_confirmation=True,
        supersedes_resolution_id=None,
        version=1,
        requested_by_user_id=USER_ID,
        started_at=NOW,
        completed_at=NOW,
        created_at=NOW,
        attempts=(attempt,),
        candidates=(candidate,),
        conflicts=(),
    )


def _property_record() -> PropertyEntityRecord:
    return PropertyEntityRecord(
        property_entity_id=PROPERTY_ID,
        property_graph_node_id=PROPERTY_NODE_ID,
        workspace_id=WORKSPACE_ID,
        entity_status=PropertyEntityStatus.UNVERIFIED,
        display_label="Unverified fixture property",
        version=1,
        created_by_user_id=USER_ID,
        created_at=NOW,
        updated_at=NOW,
        archived_at=None,
    )


def _evidence(evidence_id: UUID, status: EvidenceStatus) -> EvidenceRecord:
    has_value = status is EvidenceStatus.LIMITED
    return EvidenceRecord(
        evidence_id=evidence_id,
        workspace_id=WORKSPACE_ID,
        fact_type="address.normalized",
        value={"address": "Fixture"} if has_value else None,
        value_ref=None,
        value_schema="address-fact-v1" if has_value else None,
        source_id="vnext-test",
        source_type=SourceType.TEST,
        source_environment=SourceEnvironment.TEST,
        provider="fixture-provider",
        source_record_id="fixture-record",
        retrieved_at=NOW,
        effective_from=None,
        effective_to=None,
        expires_at=None,
        coverage_status=(
            CoverageStatus.PARTIAL if has_value else CoverageStatus.UNKNOWN
        ),
        coverage={"scope": "fixture"},
        evidence_status=status,
        quality_confidence=None,
        quality_method=None,
        quality_status=QualityStatus.LIMITED,
        quality={"limitations": ["fixture"]},
        license_status=LicenseStatus.NOT_APPLICABLE,
        license_ref=None,
        license={},
        lineage={"transformation": "none"},
        content_hash="f" * 64,
        evidence_version=1,
        raw_artifact_ref=None,
        supersedes_evidence_id=None,
        created_by_user_id=USER_ID,
        created_by_service=None,
        created_at=NOW,
    )


class _ResolutionService:
    def __init__(self, authorizer: WorkspaceAuthorizer) -> None:
        self.authorizer = authorizer
        self.record = _resolution_record()
        self.create_calls = 0
        self.error: VNextError | None = None

    def create(self, **kwargs):
        self.create_calls += 1
        if self.error is not None:
            raise self.error
        return ResolutionCreateOutcome(self.record, 201, False)

    def get(self, *, principal, identity_resolution_id):
        if identity_resolution_id != RESOLUTION_ID:
            raise VNextError.not_found()
        try:
            self.authorizer.require_workspace_access(principal, WORKSPACE_ID)
        except VNextError:
            raise VNextError.not_found() from None
        return self.record


class _PropertyReads:
    def __init__(self, authorizer: WorkspaceAuthorizer) -> None:
        self.authorizer = authorizer
        self.last_graph_position = None
        self.last_evidence_position = None
        self.malformed_node_source = False

    def _authorize(self, principal, property_entity_id):
        if property_entity_id != PROPERTY_ID:
            raise VNextError.not_found()
        try:
            self.authorizer.require_workspace_access(principal, WORKSPACE_ID)
        except VNextError:
            raise VNextError.not_found() from None

    def get_property(self, *, principal, property_entity_id):
        self._authorize(principal, property_entity_id)
        return _property_record()

    def get_graph(self, *, principal, property_entity_id, position, **_kwargs):
        self._authorize(principal, property_entity_id)
        self.last_graph_position = position
        relation = PropertyRelationRecord(
            property_relation_id=RELATION_ID,
            workspace_id=WORKSPACE_ID,
            from_node_id=PROPERTY_NODE_ID,
            to_node_id=ADDRESS_NODE_ID,
            relation_type=PropertyRelationType.PROPERTY_ADDRESS,
            direction=RelationDirection.DIRECTED,
            confidence=1.0,
            confidence_method="fixture-v1",
            source_id="vnext-test",
            source_type=SourceType.TEST,
            source_environment=SourceEnvironment.TEST,
            evidence_id=EVIDENCE_LIMITED_ID,
            relation_status=PropertyRelationStatus.PROPOSED,
            valid_from=NOW,
            valid_to=None,
            supersedes_relation_id=None,
            created_by_user_id=USER_ID,
            created_at=NOW,
        )
        nodes = (
            PropertyGraphNodeRecord(
                PROPERTY_NODE_ID,
                WORKSPACE_ID,
                "property",
                PROPERTY_ID,
                "Unverified fixture property",
                None,
                None,
                None,
                None,
                None,
                None,
                NOW,
            ),
            PropertyGraphNodeRecord(
                ADDRESS_NODE_ID,
                WORKSPACE_ID,
                "address",
                ADDRESS_ID,
                "Fixture address",
                None,
                "vnext-test",
                None if self.malformed_node_source else SourceType.TEST,
                SourceEnvironment.TEST,
                NOW,
                None,
                NOW,
            ),
        )
        return PropertyGraphPage(
            property=_property_record(),
            nodes=nodes,
            relations=(relation,),
            as_of=None,
            next_position=(
                GraphPosition(NOW, RELATION_ID) if position is None else None
            ),
        )

    def get_evidence(self, *, principal, property_entity_id, position, **_kwargs):
        self._authorize(principal, property_entity_id)
        self.last_evidence_position = position
        records = (
            _evidence(EVIDENCE_LIMITED_ID, EvidenceStatus.LIMITED),
            _evidence(EVIDENCE_UNKNOWN_ID, EvidenceStatus.UNKNOWN),
        )
        return PropertyEvidencePage(
            property=_property_record(),
            evidence=records,
            next_position=(
                EvidencePosition(
                    "address.normalized",
                    None,
                    NOW,
                    EVIDENCE_UNKNOWN_ID,
                )
                if position is None
                else None
            ),
        )


@contextmanager
def _client(
    role: WorkspaceRole | None = WorkspaceRole.MEMBER,
    *,
    user_id: UUID = USER_ID,
    feature_enabled: bool = True,
):
    verifier = SupabaseJWTVerifier(
        issuer=ISSUER,
        signing_key_resolver=lambda _token: PUBLIC_KEY,
    )
    authorizer = WorkspaceAuthorizer(_Memberships(role, user_id))
    service = _ResolutionService(authorizer)
    reads = _PropertyReads(authorizer)
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_workspace_authorizer] = lambda: authorizer
    app.dependency_overrides[get_vnext_feature_flags] = lambda: VNextFeatureFlags(
        identity_v1=feature_enabled
    )
    app.dependency_overrides[get_resolution_application_service] = lambda: service
    app.dependency_overrides[get_property_read_repository] = lambda: reads
    app.dependency_overrides[get_cursor_codec] = lambda: CursorCodec(
        b"slice-5-test-cursor-key-material-0001"
    )
    client = TestClient(app)
    try:
        yield client, service, reads
    finally:
        client.close()
        app.dependency_overrides.clear()


def _auth(user_id: UUID = USER_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user_id)}"}


def _resolution_body(text: str = "Fixture") -> dict[str, object]:
    return {
        "workspace_id": str(WORKSPACE_ID),
        "input": {"kind": "address", "value": {"text": text}},
        "case_id": None,
    }


def test_slice_5_openapi_exposes_only_non_confirming_routes() -> None:
    with _client() as (client, _service, _reads):
        schema = client.get("/openapi.json").json()

    expected = {
        "/v1/property-resolutions",
        "/v1/property-resolutions/{identity_resolution_id}",
        "/v1/properties/{property_entity_id}",
        "/v1/properties/{property_entity_id}/graph",
        "/v1/properties/{property_entity_id}/evidence",
    }
    assert expected <= set(schema["paths"])
    assert not any("confirm" in path or "reject" in path for path in schema["paths"])
    post = schema["paths"]["/v1/property-resolutions"]["post"]
    assert {"SupabaseBearer": []} in post["security"]
    assert "Idempotency-Key" in [item["name"] for item in post["parameters"]]
    assert "202" not in post["responses"]


def test_resolution_create_returns_persisted_non_confirming_201() -> None:
    with _client() as (client, service, _reads):
        response = client.post(
            "/v1/property-resolutions",
            headers={**_auth(), "Idempotency-Key": "resolution-key-0001"},
            json=_resolution_body(),
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["resolution_id"] == str(RESOLUTION_ID)
    assert payload["state"] == "candidates_found"
    assert payload["needs_human_confirmation"] is True
    assert payload["selected_candidate_id"] is None
    assert payload["confirmed_property_entity_id"] is None
    assert payload["candidates"][0]["confidence"] == 1.0
    assert payload["candidates"][0]["needs_human_confirmation"] is True
    assert payload["candidates"][0]["possible_existing_property_entity_id"] == str(
        PROPERTY_ID
    )
    assert service.create_calls == 1
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["X-Correlation-ID"]


@pytest.mark.parametrize(
    "role, expected",
    [
        (WorkspaceRole.MEMBER, 201),
        (WorkspaceRole.MANAGER, 201),
        (WorkspaceRole.ADMIN, 201),
        (WorkspaceRole.OWNER, 201),
        (WorkspaceRole.VIEWER, 403),
        (None, 403),
    ],
)
def test_resolution_create_role_matrix(role, expected) -> None:
    with _client(role) as (client, _service, _reads):
        response = client.post(
            "/v1/property-resolutions",
            headers={**_auth(), "Idempotency-Key": "resolution-key-0001"},
            json=_resolution_body(),
        )
    assert response.status_code == expected


def test_auth_feature_flag_and_client_identity_boundaries() -> None:
    with _client() as (client, _service, _reads):
        assert client.get(f"/v1/properties/{PROPERTY_ID}").status_code == 401
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        assert (
            client.get(
                f"/v1/properties/{PROPERTY_ID}",
                headers={"Authorization": f"Bearer {_token(private_key=other_key)}"},
            ).status_code
            == 401
        )
        forged = client.get(
            f"/v1/properties/{PROPERTY_ID}",
            headers={**_auth(), "X-Workspace-Role": "owner"},
        )
        assert forged.status_code == 422
    with _client(feature_enabled=False) as (client, _service, _reads):
        response = client.get(f"/v1/properties/{PROPERTY_ID}", headers=_auth())
        assert response.status_code == 404


def test_unknown_resolution_input_kind_is_allowlisted_unsupported_error() -> None:
    with _client() as (client, _service, _reads):
        body = _resolution_body()
        body["input"] = {"kind": "listing_url", "value": {"text": "https://invalid"}}
        response = client.post(
            "/v1/property-resolutions",
            headers={**_auth(), "Idempotency-Key": "resolution-key-0001"},
            json=body,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_input"


def test_resolution_read_is_viewer_safe_and_cross_tenant_non_enumerating() -> None:
    with _client(WorkspaceRole.VIEWER) as (client, _service, _reads):
        response = client.get(
            f"/v1/property-resolutions/{RESOLUTION_ID}", headers=_auth()
        )
        assert response.status_code == 200
        assert (
            response.json()["provider_attempts"][0]["source"]["provider_id"]
            == "fixture-provider"
        )
    with _client(None, user_id=OTHER_USER_ID) as (client, _service, _reads):
        hidden = client.get(
            f"/v1/property-resolutions/{RESOLUTION_ID}",
            headers=_auth(OTHER_USER_ID),
        )
        assert hidden.status_code == 404
        assert "workspace" not in hidden.json()["error"]["message"].lower()


def test_property_graph_and_evidence_reads_preserve_limits_and_states() -> None:
    with _client(WorkspaceRole.VIEWER) as (client, _service, reads):
        property_response = client.get(f"/v1/properties/{PROPERTY_ID}", headers=_auth())
        graph = client.get(
            f"/v1/properties/{PROPERTY_ID}/graph",
            params={"status": "proposed", "limit": 1},
            headers=_auth(),
        )
        evidence = client.get(
            f"/v1/properties/{PROPERTY_ID}/evidence",
            params={"limit": 2},
            headers=_auth(),
        )
        graph_cursor = graph.json()["next_cursor"]
        evidence_cursor = evidence.json()["next_cursor"]
        graph_replay = client.get(
            f"/v1/properties/{PROPERTY_ID}/graph",
            params={"status": "proposed", "cursor": graph_cursor},
            headers=_auth(),
        )
        evidence_replay = client.get(
            f"/v1/properties/{PROPERTY_ID}/evidence",
            params={"cursor": evidence_cursor},
            headers=_auth(),
        )

    assert property_response.status_code == 200
    assert property_response.json()["lifecycle_state"] == "unverified"
    assert property_response.json()["confirmation_summary"]["human_confirmed"] is False
    assert graph.status_code == graph_replay.status_code == 200
    assert graph.json()["relations"][0]["status"] == "proposed"
    assert reads.last_graph_position == GraphPosition(NOW, RELATION_ID)
    assert evidence.status_code == evidence_replay.status_code == 200
    assert [item["status"] for item in evidence.json()["evidence"]] == [
        "limited",
        "unknown",
    ]
    assert evidence.json()["evidence"][1]["value"] is None
    assert reads.last_evidence_position == EvidencePosition(
        "address.normalized", None, NOW, EVIDENCE_UNKNOWN_ID
    )


def test_pagination_and_query_validation_fail_closed() -> None:
    with _client() as (client, _service, _reads):
        excessive = client.get(
            f"/v1/properties/{PROPERTY_ID}/graph",
            params={"limit": 101},
            headers=_auth(),
        )
        bad_cursor = client.get(
            f"/v1/properties/{PROPERTY_ID}/evidence",
            params={"cursor": "not-a-signed-cursor"},
            headers=_auth(),
        )
        bad_fact = client.get(
            f"/v1/properties/{PROPERTY_ID}/evidence",
            params={"fact_type": "INVALID FACT"},
            headers=_auth(),
        )

    assert (
        excessive.status_code == bad_cursor.status_code == bad_fact.status_code == 422
    )
    assert all(
        response.json()["error"]["code"] == "validation_failed"
        for response in (excessive, bad_cursor, bad_fact)
    )


def test_graph_read_never_fabricates_missing_source_provenance() -> None:
    with _client() as (client, _service, reads):
        reads.malformed_node_source = True
        response = client.get(
            f"/v1/properties/{PROPERTY_ID}/graph",
            headers=_auth(),
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "maintenance"
