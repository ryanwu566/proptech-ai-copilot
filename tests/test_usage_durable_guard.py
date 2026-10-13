"""Wave 1B shared-budget security contracts; no provider network traffic."""
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.abuse_middleware import AbuseMiddleware
from services import anti_abuse
from services.usage_principal import principal_from_scope


def test_shared_peer_key_survives_adapter_restart_and_is_persistable(monkeypatch):
    import importlib
    import services.usage_principal as identities
    monkeypatch.setenv("API_USAGE_PEER_HMAC_KEY", "ab" * 32)
    first = identities.principal_from_scope({"client": ("192.0.2.8", 2)})
    importlib.reload(identities)
    second = identities.principal_from_scope({"client": ("192.0.2.8", 3)})
    assert first.key == second.key
    assert first.principal_id == first.key.removeprefix("anon:")
    assert len(first.principal_id) == 64
    assert "192.0.2.8" not in str(first)


@pytest.mark.parametrize("value", [None, "short", "zz" * 32, "aa" * 31])
def test_production_peer_secret_is_required_and_strict(monkeypatch, value):
    monkeypatch.setenv("APP_ENV", "production")
    if value is None:
        monkeypatch.delenv("API_USAGE_PEER_HMAC_KEY", raising=False)
    else:
        monkeypatch.setenv("API_USAGE_PEER_HMAC_KEY", value)
    with pytest.raises(RuntimeError, match="usage identity configuration"):
        principal_from_scope({})


def test_anonymous_identifier_is_in_private_aggregate_not_prometheus():
    from services.api_usage import UsageAggregator
    peer = principal_from_scope({"client": ("192.0.2.8", 2)})
    usage = UsageAggregator()
    usage.observe(capability="places", event="admitted_requests", principal_class="anonymous", principal_id=peer.principal_id)
    assert usage.snapshot()[0]["principal_id"] == peer.principal_id
    assert peer.principal_id not in usage.render_prometheus()


def test_high_cost_production_requires_durable_guard_before_dispatch(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_USAGE_PEER_HMAC_KEY", "ab" * 32)
    monkeypatch.delenv("API_USAGE_DATABASE_URL", raising=False)
    calls = []
    app = FastAPI()
    @app.post("/map/nearby")
    def endpoint():
        calls.append(1)
        return {"ok": True}
    app.add_middleware(AbuseMiddleware)
    response = TestClient(app).post("/map/nearby")
    assert response.status_code == 503
    assert response.json()["detail"]["reason_code"] == "guard_unavailable"
    assert not calls


def test_durable_rejection_has_safe_429_and_never_dispatches(monkeypatch):
    from services.usage_quota import QuotaExceeded
    class Exhausted:
        def consume(self, *args, **kwargs):
            raise QuotaExceeded("anonymous_quota", 50000)
    guard = anti_abuse.AbuseControls()
    guard.durable_guard = Exhausted()
    calls = []
    app = FastAPI()
    @app.post("/map/nearby")
    def endpoint():
        calls.append(1)
        return {}
    app.add_middleware(AbuseMiddleware, controls=guard)
    response = TestClient(app).post("/map/nearby", headers={"Idempotency-Key": "a" * 10000})
    assert response.status_code == 429
    assert response.json()["detail"]["reason_code"] == "anonymous_quota"
    assert response.headers["Retry-After"] == "3600"
    assert not calls


def test_public_bearer_reuses_verified_identity_and_active_account(monkeypatch):
    from services.vnext.auth import get_supabase_jwt_verifier
    from services.vnext.accounts import get_account_authorizer
    from services.vnext.errors import ErrorCode, VNextError
    from tests.test_api_usage_quota import principal
    seen = []
    class Verifier:
        def verify(self, token):
            assert token == "signed-fixture"
            return principal(9)
    class Accounts:
        def require_active(self, identity):
            seen.append(identity.user_id)
            raise VNextError(ErrorCode.ACCOUNT_SUSPENDED)
    monkeypatch.setattr("services.vnext.auth.get_supabase_jwt_verifier", lambda: Verifier())
    monkeypatch.setattr("services.vnext.accounts.get_account_authorizer", lambda: Accounts())
    calls = []
    app = FastAPI()
    @app.post("/map/nearby")
    def endpoint():
        calls.append(1)
        return {}
    app.add_middleware(AbuseMiddleware)
    response = TestClient(app).post("/map/nearby", headers={"Authorization": "Bearer signed-fixture", "X-User-ID": str(UUID(int=2))})
    assert response.status_code == 403
    assert seen == [UUID(int=9)]
    assert not calls


def test_runtime_cannot_silently_disable_production_enforcement(monkeypatch):
    from services.usage_guard import guard_configuration
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_USAGE_GUARD_MODE", "local")
    with pytest.raises(RuntimeError, match="usage guard configuration"):
        guard_configuration()


def test_serverless_contract_cannot_use_ephemeral_peer_or_local_quota(monkeypatch):
    from services.usage_guard import guard_configuration
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("API_USAGE_PEER_HMAC_KEY", raising=False)
    with pytest.raises(RuntimeError):
        principal_from_scope({})
    with pytest.raises(RuntimeError):
        guard_configuration()


def test_every_forwarded_or_client_identity_claim_keeps_same_budget(monkeypatch):
    from services.api_usage import UsageAggregator
    monkeypatch.setenv("API_USAGE_PEER_HMAC_KEY", "ab" * 32)
    scopes = [{"client": ("192.0.2.1", 1), "headers": [(header, b"victim")],
               "query_string": b"user_id=victim", "localStorage": {"user_id": "victim"},
               "user_metadata": {"user_id": "victim", "role": "platform_admin"}}
              for header in (b"x-user-id", b"x-role", b"x-workspace-role", b"x-forwarded-for", b"x-real-ip", b"forwarded", b"x-client-ip")]
    selected = {principal_from_scope(scope).key for scope in scopes}
    assert len(selected) == 1
    usage = UsageAggregator()
    for scope in scopes:
        identity = principal_from_scope(scope)
        usage.observe(capability="places", event="request", principal_class=identity.principal_class, principal_id=identity.principal_id)
    metrics = usage.render_prometheus()
    assert "192.0.2.1" not in metrics
    assert next(iter(selected)).removeprefix("anon:") not in metrics
    assert "victim" not in metrics


def test_metrics_series_count_does_not_grow_with_authenticated_subjects():
    from services.api_usage import UsageAggregator
    usage = UsageAggregator()
    usage.observe(capability="places", event="admitted_requests", principal_class="authenticated", principal_id=str(UUID(int=1)))
    count = len(usage.render_prometheus().splitlines())
    for i in range(2, 100):
        usage.observe(capability="places", event="admitted_requests", principal_class="authenticated", principal_id=str(UUID(int=i)))
    assert len(usage.render_prometheus().splitlines()) == count
    assert str(UUID(int=1)) not in usage.render_prometheus()


def test_unadmitted_peers_do_not_create_durable_telemetry_identity_rows(monkeypatch):
    from services.api_usage import UsageAggregator
    from services.usage_quota import QuotaExceeded
    class Exhausted:
        def consume(self, *args, **kwargs):
            raise QuotaExceeded("anonymous_quota", 60)
    usage = UsageAggregator()
    monkeypatch.setattr("services.api_usage.USAGE", usage)
    controls = anti_abuse.AbuseControls()
    controls.durable_guard = Exhausted()
    app = FastAPI()
    @app.post("/map/nearby")
    def endpoint():
        pytest.fail("Rejected quota must not dispatch")
    app.add_middleware(AbuseMiddleware, controls=controls)
    for i in range(8):
        response = TestClient(app, client=(f"192.0.2.{i+1}", 3000)).post("/map/nearby")
        assert response.status_code == 429
    assert len(usage.snapshot()) <= 2
    assert all(row["principal_class"] == "system" and row["principal_id"] == "" for row in usage.snapshot())


def test_operator_tdx_refresh_is_inside_existing_kill_switch_and_budget():
    from backend.api.abuse_middleware import capability
    assert capability({"method": "POST", "path": "/commute/refresh"}) == "market_ops"


def test_public_invalid_bearer_does_not_downgrade_to_anonymous(monkeypatch):
    from services.vnext.errors import VNextError
    class Verifier:
        def verify(self, _):
            raise VNextError.authentication_required()
    monkeypatch.setattr("services.vnext.auth.get_supabase_jwt_verifier", lambda: Verifier())
    app = FastAPI()
    calls = []
    @app.post("/map/nearby")
    def endpoint():
        calls.append(1)
        return {}
    app.add_middleware(AbuseMiddleware)
    response = TestClient(app).post("/map/nearby", headers={"Authorization": "Bearer forged"})
    assert response.status_code == 401
    assert not calls


@pytest.mark.parametrize("disabled", [False, True])
def test_local_envelope_rejects_before_optional_jwt_or_account_work(monkeypatch, disabled):
    from services.vnext.errors import VNextError
    calls = []
    class Verifier:
        def verify(self, _):
            calls.append(1)
            raise VNextError.authentication_required()
    monkeypatch.setattr("services.vnext.auth.get_supabase_jwt_verifier", lambda: Verifier())
    controls = anti_abuse.AbuseControls({"places": anti_abuse.Policy(1,60,1,10)})
    app = FastAPI()
    @app.post("/map/nearby")
    def endpoint():
        pytest.fail("Rejected request must never dispatch")
    app.add_middleware(AbuseMiddleware,controls=controls)
    client = TestClient(app)
    headers = {"Authorization":"Bearer hostile-unknown-kid"}
    if disabled:
        monkeypatch.setenv("ANTI_ABUSE_PLACES_DISABLED","true")
        assert client.post("/map/nearby",headers=headers).status_code == 503
        assert calls == []
    else:
        assert client.post("/map/nearby",headers=headers).status_code == 401
        assert client.post("/map/nearby",headers=headers).status_code == 429
        assert calls == [1]


def test_async_provider_durable_admission_does_not_block_event_loop(monkeypatch):
    import asyncio
    import threading
    from services.api_usage import UsageContext, usage_context
    entered, release = threading.Event(), threading.Event()
    class Guard:
        def consume(self, *args, **kwargs):
            entered.set()
            assert release.wait(1)
    controls = anti_abuse.AbuseControls()
    controls.durable_guard = Guard()
    monkeypatch.setattr(anti_abuse, "CONTROLS", controls)
    context = UsageContext(principal_from_scope({}), "places", "POST:places", controls)
    context.request_admitted = True
    @anti_abuse.provider_operation("places")
    async def provider():
        return "done"
    async def run():
        async def ticker():
            while not entered.is_set():
                await asyncio.sleep(0.001)
            release.set()
        with usage_context(context):
            result, _ = await asyncio.gather(provider(), ticker())
        assert result == "done"
    asyncio.run(run())


@pytest.mark.parametrize("failure_at,expected_attempts", [(None,3),(1,1),(2,2),(3,3)])
def test_tdx_counts_each_physical_transport_including_failure(monkeypatch,failure_at,expected_attempts):
    import httpx
    from services.tdx_mrt_client import TdxMrtClient,TdxMrtClientError
    from services.api_usage import USAGE
    calls = []
    class Response:
        def __init__(self,payload): self.payload=payload
        def raise_for_status(self): pass
        def json(self): return self.payload
    def dispatch(token=False):
        calls.append(1)
        if len(calls)==failure_at:
            raise httpx.ReadTimeout("private-provider-client-secret")
        return Response({"access_token":"private-token"} if token else [])
    monkeypatch.setattr(httpx,"post",lambda *args,**kwargs:dispatch(True))
    monkeypatch.setattr(httpx,"get",lambda *args,**kwargs:dispatch())
    client = TdxMrtClient(client_id="fixture",client_secret="private-secret")
    if failure_at is None:
        client.refresh_payload()
    else:
        with pytest.raises(TdxMrtClientError):
            client.refresh_payload()
    summary = USAGE.summary()
    assert summary["totals"]["provider_attempt_count"]==expected_attempts
    assert summary["totals"]["provider_failures"]==int(failure_at is not None)
    assert summary["totals"]["provider_timeouts"]==int(failure_at is not None)
    assert summary["cost_estimates"]["tdx_mrt"]["status"]=="unknown"
    assert "private" not in str(summary)


def test_disabled_tdx_rejects_before_any_transport(monkeypatch):
    import httpx
    from services.tdx_mrt_client import TdxMrtClient
    calls = []
    monkeypatch.setenv("ANTI_ABUSE_MARKET_OPS_DISABLED","true")
    monkeypatch.setattr(httpx,"post",lambda *args,**kwargs:calls.append(1))
    with pytest.raises(anti_abuse.AbuseRejected):
        TdxMrtClient(client_id="fixture",client_secret="fixture").refresh_payload()
    assert not calls


@pytest.mark.parametrize("provider",["user:private-identity","none"])
def test_physical_provider_override_cannot_add_labels_or_claim_no_provider(provider):
    from services.provider_cost_metrics import ProviderCostMetrics
    metrics = ProviderCostMetrics()
    with pytest.raises(ValueError):
        metrics.record("market_ops","physical_calls",provider=provider)
    assert metrics.snapshot()=={}


def test_cancelled_request_drains_admission_before_releasing_local_permit(monkeypatch):
    import asyncio
    import threading
    from services.usage_quota import PrincipalQuotas
    from services.api_usage import current_usage_context
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    identity = principal_from_scope({})
    class Guard:
        def consume(self, *args, **kwargs):
            entered.set()
            assert release.wait(2)
            finished.set()
    controls = anti_abuse.AbuseControls(principal_quotas=PrincipalQuotas())
    controls.durable_guard = Guard()
    async def app(scope, receive, send):
        pytest.fail("Cancelled admission must not dispatch work")
    middleware = AbuseMiddleware(app, controls=controls)
    async def run():
        async def receive(): return {"type": "http.request", "body": b""}
        async def send(message): pass
        scope = {"type": "http", "method": "POST", "path": "/map/nearby", "headers": [], "state": {}}
        task = asyncio.create_task(middleware(scope, receive, send))
        while not entered.is_set():
            await asyncio.sleep(0.001)
        timer = threading.Timer(0.2, release.set)
        timer.start()
        try:
            task.cancel()
            await asyncio.sleep(0.01)
            assert not release.is_set(), "Cancellation cleanup blocked the event loop"
        finally:
            release.set()
            timer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        while not finished.is_set():
            await asyncio.sleep(0.001)
        await asyncio.sleep(0.01)
        assert controls.principal_quotas.current_usage(identity)["concurrency"] == 0
    asyncio.run(run())
