"""Admin endpoints must never inherit consumer/workspace authorization."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.api_main import app
from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier
from services.vnext.accounts import AccountAuthorizer, get_account_authorizer
from tests.test_admin_commands import authority
from dataclasses import dataclass

@dataclass
class PlatformPrivilege:
    user_id: UUID
    platform_role: str
    account_status: str
from services.admin.summaries import LocalAdminSummarySource, get_admin_summary_source
from services.admin.contracts import AdminSnapshot

SECTIONS = ("overview", "users", "usage", "providers", "limits", "operations", "audit")
USER = UUID("11111111-1111-4111-8111-111111111111")
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ISSUER = "https://admin-fixture.supabase.co/auth/v1"


@pytest.fixture
def client():
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: SupabaseJWTVerifier(
        issuer=ISSUER, signing_key_resolver=lambda _: KEY.public_key()
    )
    authority()
    app.dependency_overrides[get_admin_summary_source] = lambda: LocalAdminSummarySource()
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()


def headers(**claims):
    token = jwt.encode({"sub": str(USER), "iss": ISSUER, "aud": "authenticated",
                        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                        **claims}, KEY, algorithm="RS256", headers={"kid": "fixture"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("section", SECTIONS)
def test_anonymous_direct_admin_api_requires_authentication(client, section):
    response = client.get(f"/v1/admin/{section}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("claims", [{}, {"user_metadata": {"role": "platform_admin"}},
                                     {"role": "workspace_admin"}, {"app_metadata": {"role": "platform_admin"}}])
@pytest.mark.parametrize("section", SECTIONS)
def test_unwired_authority_denies_consumers_and_client_claims(client, section, claims):
    response = client.get(f"/v1/admin/{section}", headers=headers(**claims))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


class Authority:
    def __init__(self, value):
        self.value = value

    def lookup(self, principal):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def grant(value=None):
    from services.vnext.accounts import Account
    privilege = value or PlatformPrivilege(USER, "platform_admin", "active")
    class Repo:
        def get_account(self, *, principal):
            if isinstance(privilege, Exception):
                raise privilege
            if not isinstance(privilege, PlatformPrivilege):
                return None
            return Account(privilege.user_id, privilege.account_status, privilege.platform_role,
                           datetime.now(timezone.utc), datetime.now(timezone.utc))
    app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Repo())


@pytest.mark.parametrize("section", SECTIONS)
def test_active_platform_admin_gets_private_passive_summary(client, section):
    grant()
    response = client.get(f"/v1/admin/{section}", headers=headers())
    assert response.status_code == 200
    assert response.json()["section"] == section
    assert response.headers["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("value", [PlatformPrivilege(USER, "platform_admin", "suspended"),
    PlatformPrivilege(USER, "workspace_admin", "active"), PlatformPrivilege(USER, "admin", "active"),
    PlatformPrivilege(USER, "platform_admin", "unknown"), {"platform_role": "platform_admin"},
    PlatformPrivilege(UUID("22222222-2222-4222-8222-222222222222"), "platform_admin", "active"),
    RuntimeError("private dependency details")])
@pytest.mark.parametrize("section", SECTIONS)
def test_invalid_authority_never_reads_data(client, section, value):
    grant(value)
    class NeverRead:
        def read(self, *_):
            pytest.fail("unauthorized summary read")
    app.dependency_overrides[get_admin_summary_source] = lambda: NeverRead()
    response = client.get(f"/v1/admin/{section}", headers=headers())
    assert response.status_code == (403 if isinstance(value, PlatformPrivilege) and value.account_status == "suspended" else 503)
    assert "private dependency details" not in response.text


def test_passive_provider_semantics_and_configuration_do_not_expose_secrets(client, monkeypatch):
    grant()
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "private-provider-key")
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "private-scrape-secret")
    monkeypatch.setenv("ANTI_ABUSE_GEOCODING_DISABLED", "true")
    response = client.get("/v1/admin/providers", headers=headers())
    row = next(r for r in response.json()["providers"] if r["capability"] == "geocoding")
    assert row["configuration"] == "configured"
    assert row["status"] == "not_checked"
    assert row["freshness"] == "unknown"
    assert row["disabled"] is True
    assert "private-provider-key" not in response.text
    assert "private-scrape-secret" not in response.text
    assert "GOOGLE_MAPS_API_KEY" not in response.text


def test_missing_data_remains_unavailable_not_zero():
    source = LocalAdminSummarySource()
    snapshot = source.read("overview")
    assert all(metric.value is None and metric.state == "unavailable" for metric in snapshot.metrics)
    assert source.read("users").state == "unavailable"
    assert source.read("audit").state == "unavailable"
    assert all(row.state != "known" for row in source.read("operations").operations if row.key in {"backup", "restore", "incident"})


def test_audit_projection_drops_metadata_and_user_projection_minimizes_identity(client):
    grant()
    class SafeFixture:
        def read(self, section, cursor):
            return {"section": section, "state": "available", "source": "wave_1a", "as_of": "2026-10-13T00:00:00Z",
                "audit": [{"timestamp": "2026-10-13T00:00:00Z", "actor": str(USER), "event_type": "admin_read",
                    "target_type": "admin", "outcome": "success", "reason_code": "authorized", "metadata": {"jwt": "private-token"}}],
                "users": [{"user_id": str(USER), "status": "active", "platform_role": "consumer",
                    "email": "private@example.invalid", "password_hash": "private-hash", "property_history": "private-address"}]}
    app.dependency_overrides[get_admin_summary_source] = lambda: SafeFixture()
    response = client.get("/v1/admin/audit", headers=headers())
    assert response.status_code == 200
    assert all(value not in response.text for value in ["private-token", "private-hash", "private-address", "private@example.invalid", "metadata"])


def test_oversized_and_wrong_section_source_fails_safely(client):
    grant()
    class Oversized:
        def read(self, section, cursor):
            return {"section": section, "state": "available", "source": "wave_1a", "as_of": "2026-10-13T00:00:00Z",
                    "users": [{"user_id": str(USER), "status": "active", "platform_role": "consumer"}] * 51}
    app.dependency_overrides[get_admin_summary_source] = lambda: Oversized()
    response = client.get("/v1/admin/users", headers=headers())
    assert response.status_code == 503
    assert "users" not in response.json()["error"]["message"]


def test_cursor_is_bounded_and_reauthorized(client):
    grant()
    response = client.get("/v1/admin/audit?cursor=" + "a" * 129, headers=headers())
    assert response.status_code == 422
    authority()
    assert client.get("/v1/admin/audit?cursor=next", headers=headers()).status_code == 403


def test_numeric_truth_rejects_boolean_metrics():
    with pytest.raises(ValueError):
        AdminSnapshot.model_validate({"section": "overview", "state": "available", "source": "wave_1b", "as_of": "2026-10-13T00:00:00Z",
            "metrics": [{"key": "requests", "state": "known", "value": True, "source": "wave_1b", "window": "last_24h"}]})


def test_incomplete_http_429_totals_are_unknown_even_with_multiple_rejection_counters(monkeypatch):
    from services.provider_cost_metrics import ProviderCostMetrics
    from services.admin import summaries
    counters = ProviderCostMetrics()
    counters.record("routes", "rate_limited", 2)
    counters.record("routes", "provider_budget_exhausted", 3)
    monkeypatch.setattr(summaries, "PROVIDER_COST_METRICS", counters)
    row = LocalAdminSummarySource().read("usage").usage[0]
    assert row.http_429 is None


def test_limits_read_the_current_enforcement_registry(monkeypatch):
    from services import anti_abuse
    policy = anti_abuse.Policy(requests=7, window=60, concurrency=1, operations=11)
    monkeypatch.setattr(anti_abuse, "CONTROLS", anti_abuse.AbuseControls({"routes": policy}))
    rows = LocalAdminSummarySource().read("limits").limits
    assert len(rows) == 1
    assert rows[0].requests == 7
    assert rows[0].operations == 11
