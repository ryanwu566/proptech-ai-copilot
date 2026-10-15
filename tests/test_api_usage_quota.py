"""Wave 1B trust, independent quota layers and bounded accounting regressions."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from services import anti_abuse
from backend.api.abuse_middleware import AbuseMiddleware


class Clock:
    now = 0.0
    def __call__(self):
        return self.now


def principal(number=1):
    from services.vnext.auth import AuthenticatedPrincipal
    return AuthenticatedPrincipal(UUID(int=number), str(UUID(int=number)), "https://fixture.test/auth/v1")


def test_identity_uses_only_verified_server_state():
    from services.usage_principal import principal_from_scope
    scope = {"client": ("192.0.2.1", 100), "state": {}, "headers": [(b"x-user-id", b"victim"), (b"authorization", b"Bearer forged")]}
    anonymous = principal_from_scope(scope)
    assert anonymous.principal_class == "anonymous"
    assert "192.0.2.1" not in anonymous.key
    scope["state"]["authenticated_principal"] = {"user_id": str(UUID(int=1))}
    assert principal_from_scope(scope) == anonymous
    scope["state"]["authenticated_principal"] = principal()
    user = principal_from_scope(scope)
    assert user.key == "user:00000000-0000-0000-0000-000000000001"
    assert user.principal_class == "authenticated"


def test_anonymous_peer_isolation_ignores_port_and_forwarded_headers():
    from services.usage_principal import principal_from_scope
    a = principal_from_scope({"client": ("192.0.2.1", 100)})
    assert a == principal_from_scope({"client": ("192.0.2.1", 200), "headers": [(b"x-forwarded-for", b"192.0.2.2")]})
    assert a != principal_from_scope({"client": ("192.0.2.2", 100)})
    assert principal_from_scope({}).key.startswith("anon:")


def test_request_operation_daily_windows_are_independent_and_bounded():
    from services.usage_quota import PrincipalQuotas, QuotaPolicy, QuotaExceeded
    from services.usage_principal import principal_from_scope
    clock = Clock()
    quotas = PrincipalQuotas({"anonymous": QuotaPolicy(2, 60, 1, 60, 2, 1)}, clock=clock, wall_clock=clock)
    identity = principal_from_scope({})
    for _ in range(2):
        with quotas.request(identity):
            pass
    with pytest.raises(QuotaExceeded) as error:
        with quotas.request(identity):
            pass
    assert error.value.reason == "principal_request_quota"
    assert error.value.retry_after == 60
    quotas.reserve_operation(identity)
    with pytest.raises(QuotaExceeded):
        quotas.reserve_operation(identity)
    clock.now = 60
    quotas.reserve_operation(identity)
    clock.now = 120
    with pytest.raises(QuotaExceeded) as error:
        quotas.reserve_operation(identity)
    assert error.value.reason == "principal_daily_quota"
    assert 1 <= error.value.retry_after <= 3600
    clock.now = 86400
    quotas.reserve_operation(identity)


def test_user_and_anonymous_buckets_do_not_share_and_concurrency_recovers():
    from services.usage_quota import PrincipalQuotas, QuotaPolicy, QuotaExceeded
    from services.usage_principal import principal_from_scope
    quotas = PrincipalQuotas({name: QuotaPolicy(1, 60, 1, 60, 1, 1) for name in ("anonymous", "free")})
    identities = [principal_from_scope({"state": {"authenticated_principal": principal(i)}}) for i in (1, 2)]
    identities += [principal_from_scope({"client": (ip, 1)}) for ip in ("192.0.2.1", "192.0.2.2")]
    for identity in identities:
        with quotas.request(identity):
            with pytest.raises(QuotaExceeded) as error:
                with quotas.request(identity):
                    pass
            assert error.value.reason == "principal_concurrency"
        quotas.reserve_operation(identity)
        with pytest.raises(QuotaExceeded):
            quotas.reserve_operation(identity)


@pytest.mark.parametrize("value", ["0", "-1", "nan", "true", "1.2", "999999999999999999999"])
def test_malformed_quota_config_fails_closed(monkeypatch, value):
    from services.usage_quota import configured_quota_policies
    monkeypatch.setenv("API_QUOTA_ANONYMOUS_REQUESTS", value)
    with pytest.raises(RuntimeError, match="Invalid API quota configuration"):
        configured_quota_policies()


def test_bounded_quota_keys_overflow_cannot_reset_allowance():
    from services.usage_quota import PrincipalQuotas, QuotaPolicy, QuotaExceeded
    from services.usage_principal import principal_from_scope
    quotas = PrincipalQuotas({"anonymous": QuotaPolicy(1, 60, 1, 60, 1, 1)}, max_keys=4)
    allowed = 0
    for i in range(100):
        try:
            with quotas.request(principal_from_scope({"client": (f"peer-{i}", 1)})):
                allowed += 1
        except QuotaExceeded:
            pass
    assert allowed == 4
    assert quotas.tracked_key_count() == 4


def test_capability_process_cap_retained_across_distinct_peers():
    guard = anti_abuse.AbuseControls({"places": anti_abuse.Policy(1, 60, 1, 100)})
    for i in range(16):
        guard.admit("places", f"peer-{i}")
    with pytest.raises(anti_abuse.AbuseRejected) as error:
        guard.admit("places", "another-peer")
    assert error.value.status_code == 429
    assert error.value.detail["reason_code"] == "capability_request_quota"


def make_app(monkeypatch, *, quotas=None, verified=None, fail=False):
    from services.api_usage import UsageAggregator
    from services.usage_quota import PrincipalQuotas, QuotaPolicy
    usage = UsageAggregator()
    monkeypatch.setattr("services.api_usage.USAGE", usage)
    guard = anti_abuse.AbuseControls({"places": anti_abuse.Policy(100, 60, 8, 100)}, principal_quotas=quotas or PrincipalQuotas({name: QuotaPolicy(100, 60, 100, 3600, 100, 8) for name in ("anonymous", "free")}))
    monkeypatch.setattr(anti_abuse, "CONTROLS", guard)
    app = FastAPI()
    from services.provider_request_cache import BoundedRequestCache
    from services.provider_cost_metrics import PROVIDER_COST_METRICS
    cache = BoundedRequestCache("places", 60, 8)
    @anti_abuse.provider_operation("places")
    def provider():
        PROVIDER_COST_METRICS.record("places", "physical_calls")
        if fail:
            PROVIDER_COST_METRICS.record("places", "provider_failure")
            raise RuntimeError("private-provider-secret")
        return {"ok": True}
    @app.post("/map/nearby")
    def route(request: Request):
        return cache.run("fixed-server-key", provider)
    app.add_middleware(AbuseMiddleware, controls=guard)
    if verified:
        @app.middleware("http")
        async def identity(request, call_next):
            request.state.authenticated_principal = verified
            return await call_next(request)
    return TestClient(app, raise_server_exceptions=False), usage, guard


def test_cache_and_rejected_requests_never_fake_provider_attempt(monkeypatch):
    from services.usage_quota import PrincipalQuotas, QuotaPolicy
    quotas = PrincipalQuotas({"anonymous": QuotaPolicy(2, 60, 1, 3600, 1, 2)})
    client, usage, _ = make_app(monkeypatch, quotas=quotas)
    assert client.post("/map/nearby", json={"address": "PRIVATE", "coordinates": [25, 121]}).status_code == 200
    assert client.post("/map/nearby").status_code == 200
    assert client.post("/map/nearby", headers={"X-User-ID": "victim"}).status_code == 429
    summary = usage.summary()
    assert summary["totals"]["provider_attempt_count"] == 1
    assert summary["totals"]["quota_units"] == 1
    assert summary["totals"]["responses_429"] == 1
    assert summary["totals"]["cache_hits"] == 1
    assert "PRIVATE" not in str(summary)
    assert "principal_id" not in usage.render_prometheus()


def test_failed_actual_attempt_and_5xx_remain_counted(monkeypatch):
    client, usage, _ = make_app(monkeypatch, fail=True)
    assert client.post("/map/nearby").status_code == 500
    assert usage.summary()["totals"]["provider_attempt_count"] == 1
    assert usage.summary()["totals"]["provider_failures"] == 1
    assert usage.summary()["totals"]["responses_5xx"] == 1
    assert "private-provider-secret" not in str(usage.summary())


def test_context_survives_fanout_and_late_producer_events(monkeypatch):
    from services.api_usage import UsageAggregator, UsageContext, usage_context, record_cost_event
    from services.usage_principal import principal_from_scope
    usage = UsageAggregator()
    monkeypatch.setattr("services.api_usage.USAGE", usage)
    context = UsageContext(principal_from_scope({"state": {"authenticated_principal": principal()}}), "places", "POST:places", None)
    with usage_context(context):
        with ThreadPoolExecutor(max_workers=2) as pool:
            pool.submit(copy_context().run, record_cost_event, "places", "physical_calls", 1).result()
    with usage_context(context):  # a detached producer retains its identity
        record_cost_event("places", "provider_failure", 1)
    rows = usage.snapshot()
    assert sum(row["provider_attempt_count"] for row in rows) == 1
    assert all(row["principal_id"] == "00000000-0000-0000-0000-000000000001" for row in rows)


def test_cost_unknown_configured_and_not_applicable_are_distinct():
    from services.api_usage import cost_estimate
    assert cost_estimate("google_places", 2)["currency_estimate"] is None
    assert cost_estimate("google_places", 0)["status"] == "not_applicable"
    estimate = cost_estimate("google_places", 2, {"google_places": {"currency": "TWD", "per_operation": "1.25"}})
    assert estimate == {"status": "configured_estimate", "currency": "TWD", "currency_estimate": "2.50"}
    with pytest.raises(ValueError):
        cost_estimate("google_places", 1, {"google_places": {"currency": "TWD", "per_operation": "NaN"}})


def test_cardinality_and_recent_windows_are_bounded():
    from services.api_usage import UsageAggregator
    clock = Clock()
    usage = UsageAggregator(max_rows=4, wall_clock=clock)
    for i in range(100):
        usage.observe(capability="places", principal_class="authenticated", principal_id=str(UUID(int=i)), event="physical_calls", provider="google_places")
    assert len(usage.snapshot()) <= 4
    assert usage.summary()["accounting"]["dropped_observations"] == 96
    with pytest.raises(ValueError):
        usage.observe(capability="raw-private-address", event="physical_calls")
    clock.now = 90000
    assert usage.summary()["totals"]["provider_attempt_count"] == 0
    assert usage.summary()["accounting"]["complete"] is False


def test_control_plane_truth_and_kill_switch(monkeypatch):
    guard = anti_abuse.AbuseControls({"places": anti_abuse.Policy(2, 60, 1, 2)})
    monkeypatch.setenv("ANTI_ABUSE_PLACES_DISABLED", "malformed")
    state = guard.control_state()
    assert state["enforcement_scope"] == "process_local"
    assert state["fleet_quota_enforced"] is False
    assert state["capabilities"]["places"]["enabled"] is False
    assert state["mutable_controls_available"] is False
    with pytest.raises(anti_abuse.AbuseRejected):
        guard.admit("places", "peer")


def test_existing_auth_dependency_binds_verified_user_before_quota(monkeypatch):
    from fastapi import Depends
    from services.vnext.accounts import require_active_account, get_account_authorizer
    from tests.account_fixtures import active_account_authorizer
    from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier, require_authenticated_principal
    from tests.test_vnext_auth_api import _token, PUBLIC_KEY, ISSUER
    from services.usage_quota import PrincipalQuotas, QuotaPolicy
    from services.api_usage import UsageAggregator
    usage = UsageAggregator()
    monkeypatch.setattr("services.api_usage.USAGE", usage)
    quotas = PrincipalQuotas({name: QuotaPolicy(1, 60, 10, 60, 10, 2) for name in ("anonymous", "free")})
    guard = anti_abuse.AbuseControls({"identity": anti_abuse.Policy(20, 60, 4, 100)}, principal_quotas=quotas)
    app = FastAPI()
    @app.post("/v1/property-resolutions")
    def endpoint(identity=Depends(require_authenticated_principal), active=Depends(require_active_account)):
        return {"ok": True}
    app.dependency_overrides[get_account_authorizer] = active_account_authorizer
    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: SupabaseJWTVerifier(issuer=ISSUER, signing_key_resolver=lambda _: PUBLIC_KEY)
    app.add_middleware(AbuseMiddleware, controls=guard)
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + _token(subject=str(UUID(int=1)))}
    assert client.post("/v1/property-resolutions", headers=headers).status_code == 200
    assert client.post("/v1/property-resolutions", headers={**headers, "X-User-ID": str(UUID(int=2))}).status_code == 429
    assert client.post("/v1/property-resolutions", headers={"Authorization": "Bearer " + _token(subject=str(UUID(int=2)))}).status_code == 200
    rows = usage.summary(include_principals=True)["rows"]
    assert sum(row["admitted"] for row in rows if row["principal_id"] == str(UUID(int=1))) == 1
    assert sum(row["admitted"] for row in rows if row["principal_id"] == str(UUID(int=2))) == 1
    assert not any("Bearer" in str(row) for row in rows)


def test_missing_instrumentation_remains_explicitly_unknown(monkeypatch):
    from services.api_usage import UsageAggregator
    usage = UsageAggregator()
    monkeypatch.setattr("services.api_usage.USAGE", usage)
    app = FastAPI()
    @app.post("/map/nearby")
    def endpoint(): return {"ok": True}
    app.add_middleware(AbuseMiddleware, controls=anti_abuse.AbuseControls({"places": anti_abuse.Policy(10, 60, 4, 100)}))
    assert TestClient(app).post("/map/nearby").status_code == 200
    summary = usage.summary()
    assert summary["totals"]["provider_accounting_unknown"] == 1
    assert summary["provider_attempts_complete"] is False


def test_failed_retry_cannot_bypass_principal_operation_quota(monkeypatch):
    from services.usage_quota import PrincipalQuotas, QuotaPolicy
    client, usage, _ = make_app(monkeypatch, fail=True, quotas=PrincipalQuotas({"anonymous": QuotaPolicy(10, 60, 1, 3600, 1, 2)}))
    assert client.post("/map/nearby").status_code == 500
    assert client.post("/map/nearby").status_code == 429
    assert usage.summary()["totals"]["provider_attempt_count"] == 1
    assert usage.summary()["totals"]["quota_units"] == 1


@pytest.mark.parametrize("event", ["physical_calls", "cache_hit"])
def test_composite_capability_does_not_claim_complete_from_one_known_stage(monkeypatch, event):
    from services.api_usage import UsageAggregator
    from services.provider_cost_metrics import PROVIDER_COST_METRICS
    usage = UsageAggregator()
    monkeypatch.setattr("services.api_usage.USAGE", usage)
    app = FastAPI()
    @app.post("/terrain-risk/analyze")
    def endpoint():
        PROVIDER_COST_METRICS.record("geocoding", event)
        # Other stages (e.g. a cold WRA R2 read) need separate instrumentation.
        return {"ok": True}
    app.add_middleware(AbuseMiddleware, controls=anti_abuse.AbuseControls({"terrain": anti_abuse.Policy(10, 60, 4, 100)}))
    assert TestClient(app).post("/terrain-risk/analyze").status_code == 200
    summary = usage.summary()
    assert summary["totals"]["provider_accounting_unknown"] == 1
    assert summary["provider_attempts_complete"] is False


def test_default_request_concurrency_preserves_ordinary_ten_request_envelope():
    from contextlib import ExitStack
    from services.usage_quota import PrincipalQuotas
    from services.usage_principal import principal_from_scope
    quotas = PrincipalQuotas()
    with ExitStack() as stack:
        for _ in range(10):
            stack.enter_context(quotas.request(principal_from_scope({})))


def test_read_only_policy_snapshot_cannot_mutate_active_quota():
    from services.usage_quota import PrincipalQuotas, QuotaPolicy, QuotaExceeded
    from services.usage_principal import principal_from_scope
    quotas = PrincipalQuotas({"anonymous": QuotaPolicy(1, 60, 10, 60, 10, 2)})
    identity = principal_from_scope({})
    guard = anti_abuse.AbuseControls({"places": anti_abuse.Policy(20, 60, 4, 100)}, principal_quotas=quotas)
    with quotas.request(identity):
        pass
    quotas.current_usage(identity)["policy"]["requests"] = 1000
    guard.control_state()["principal_policies"]["anonymous"]["requests"] = 1000
    with pytest.raises(QuotaExceeded):
        with quotas.request(identity):
            pass
