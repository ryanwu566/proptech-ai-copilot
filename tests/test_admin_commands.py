"""Wave 1C API boundary: shared account authority and bounded commands."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app
from services.vnext.accounts import Account, AccountAuthorizer, get_account_authorizer
from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal

ACTOR = UUID('11111111-1111-4111-8111-111111111111')
TARGET = UUID('22222222-2222-4222-8222-222222222222')


@pytest.fixture
def client():
    app.dependency_overrides[require_authenticated_principal] = lambda: AuthenticatedPrincipal(ACTOR, str(ACTOR), 'fixture')
    yield TestClient(app)
    app.dependency_overrides.clear()


def authority(status='active', role='consumer'):
    class Repository:
        def get_account(self, *, principal):
            return Account(principal.user_id, status, role, datetime.now(timezone.utc), datetime.now(timezone.utc))
    app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Repository())


@pytest.mark.parametrize('status,role', [('active', 'consumer'), ('suspended', 'platform_admin')])
@pytest.mark.parametrize('method,path,body', [
    ('get', '/v1/admin/users', None),
    ('get', f'/v1/admin/accounts/{TARGET}', None),
    ('post', f'/v1/admin/accounts/{TARGET}/commands', {'field': 'status', 'value': 'suspended', 'reason': 'investigation', 'command_id': str(uuid4())}),
    ('get', '/v1/admin/quota-policy', None),
    ('post', '/v1/admin/quota-policy/commands', {'principal_class': 'authenticated', 'request_hour': 12, 'operation_hour': 10, 'operation_day': 30, 'reason': 'investigation', 'command_id': str(uuid4())}),
])
def test_account_authority_denies_every_read_and_command(client, status, role, method, path, body):
    authority(status, role)
    response = client.request(method, path, json=body)
    assert response.status_code == 403


def test_active_admin_reaches_source_and_forged_identity_is_rejected(client):
    authority(role='platform_admin')
    response = client.get('/v1/admin/users', headers={'X-Role': 'platform_admin'})
    assert response.status_code == 422
    assert client.get('/v1/admin/users?role=platform_admin').status_code == 422


@pytest.mark.parametrize('reason', ['', ' ', 'x' * 501, 'bad\x00reason'])
def test_command_reason_is_bounded_before_database(client, reason):
    authority(role='platform_admin')
    response = client.post(f'/v1/admin/accounts/{TARGET}/commands', json={
        'field': 'status', 'value': 'suspended', 'reason': reason, 'command_id': str(uuid4())})
    assert response.status_code == 422


def test_legacy_fleet_flag_never_claims_global_capability_limits(monkeypatch):
    from services.anti_abuse import CONTROLS
    monkeypatch.setenv('API_USAGE_GUARD_MODE', 'postgres')
    monkeypatch.setenv('API_USAGE_DATABASE_URL', 'postgresql://fixture@localhost/test')
    result = CONTROLS.control_state()
    assert result['fleet_quota_enforced'] is False
    assert result['capability_enforcement_scope'] == 'process_local'


def test_database_dependency_errors_do_not_masquerade_as_idempotency_conflicts(monkeypatch):
    from services.admin import store
    from services.vnext.errors import VNextError
    class DependencyFailure(Exception):
        sqlstate = 'P0001'
    def fail(*args, **kwargs):
        raise DependencyFailure('private database details')
    monkeypatch.setattr(store, 'connect', fail)
    with pytest.raises(VNextError) as failure:
        with store.AdminStore('postgresql://fixture@localhost/admin_control_test').transaction(AuthenticatedPrincipal(ACTOR, str(ACTOR), 'fixture')):
            pytest.fail('unavailable connection must not be used')
    assert failure.value.status_code == 503


def test_declared_shared_guard_is_not_presented_as_verified_fleet_health(monkeypatch):
    from services.admin.summaries import LocalAdminSummarySource
    monkeypatch.setenv('API_USAGE_GUARD_MODE', 'postgres')
    monkeypatch.setenv('API_USAGE_DATABASE_URL', 'postgresql://fixture@localhost/test')
    rows = {row.key: row for row in LocalAdminSummarySource().read('operations').operations}
    assert rows['principal_quota'].state == 'unknown'
    assert rows['principal_quota'].value == 'declared'
    assert rows['fleet_enforcement'].value == 'local_only'
