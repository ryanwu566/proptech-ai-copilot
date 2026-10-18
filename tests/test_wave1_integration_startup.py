"""Integrated startup ordering; synthetic configuration, no external I/O."""
import asyncio

import pytest

from backend import api_main
from services import usage_guard, usage_ledger


@pytest.mark.parametrize(('failure','message'), [
    ('missing_app_db','production configuration'),
    ('missing_hosts','guardrail configuration'),
    ('missing_peer','usage identity configuration'),
    ('invalid_peer','usage identity configuration'),
    ('missing_usage_db','usage guard configuration'),
    ('invalid_guard_mode','usage guard configuration'),
    ('unsafe_guard','usage guard is unavailable'),
    ('unavailable_guard','usage guard is unavailable'),
    ('required_ledger','usage ledger is unavailable'),
])
def test_production_lifespan_refuses_invalid_wave1_dependencies(monkeypatch, failure, message):
    values = {
        'APP_ENV':'production', 'APP_RUNTIME':'standard',
        'DATABASE_URL':'postgresql://synthetic.invalid/app',
        'PILOT_SESSION_SIGNING_KEY':'s'*32,
        'CORS_ALLOWED_ORIGINS':'https://frontend.example.invalid',
        'PUBLIC_APP_BASE_URL':'https://frontend.example.invalid',
        'API_ALLOWED_HOSTS':'api.example.invalid',
        'API_USAGE_PEER_HMAC_KEY':'ab'*32,
        'API_USAGE_DATABASE_URL':'postgresql://synthetic.invalid/usage',
        'API_USAGE_GUARD_MODE':'postgres', 'API_USAGE_LEDGER_REQUIRED':'true',
    }
    for key,value in values.items():
        monkeypatch.setenv(key,value)
    removed = {'missing_app_db':'DATABASE_URL', 'missing_hosts':'API_ALLOWED_HOSTS',
               'missing_peer':'API_USAGE_PEER_HMAC_KEY','missing_usage_db':'API_USAGE_DATABASE_URL'}
    if failure in removed:
        monkeypatch.delenv(removed[failure])
    if failure == 'missing_app_db':
        monkeypatch.delenv('PILOT_EVIDENCE_DATABASE_URL',raising=False)
    if failure == 'invalid_peer':
        monkeypatch.setenv('API_USAGE_PEER_HMAC_KEY','invalid')
    if failure == 'invalid_guard_mode':
        monkeypatch.setenv('API_USAGE_GUARD_MODE','local')
    calls = []
    def guard_check(_self):
        calls.append('guard')
        if failure in {'unsafe_guard','unavailable_guard'}:
            raise RuntimeError('Synthetic unsafe/unavailable guard')
    def ledger_check(_self):
        calls.append('ledger')
        raise RuntimeError('Synthetic unavailable ledger')
    monkeypatch.setattr(usage_guard.PostgresQuotaGuard,'check',guard_check)
    monkeypatch.setattr(usage_ledger.PostgresUsageStore,'check',ledger_check)
    monkeypatch.setattr(api_main,'_get_earth_engine_worker_manager',
                        lambda: pytest.fail('Provider startup must follow required Wave 1 validation'))
    async def enter():
        async with api_main.app_lifespan(api_main.app):
            pytest.fail('Invalid production dependencies accepted requests')
    with pytest.raises(RuntimeError,match=message):
        asyncio.run(enter())
    assert calls == (['guard','ledger'] if failure == 'required_ledger' else
                     ['guard'] if failure in {'unsafe_guard','unavailable_guard'} else [])


def test_missing_auth_and_account_configuration_denies_at_request_authority(monkeypatch):
    """Missing Auth/account factories deny authority without external I/O."""
    from services.vnext.auth import get_supabase_jwt_verifier
    from services.vnext.db_principal import (
        DatabasePrincipalContextError, get_vnext_database_principal_context,
    )
    from services.vnext.errors import VNextError

    for key in ('SUPABASE_URL','SUPABASE_JWT_ISSUER','VNEXT_DATABASE_URL'):
        monkeypatch.delenv(key,raising=False)
    get_supabase_jwt_verifier.cache_clear()
    get_vnext_database_principal_context.cache_clear()
    try:
        with pytest.raises(VNextError) as denied:
            get_supabase_jwt_verifier()
        assert denied.value.status_code == 401
        with pytest.raises(DatabasePrincipalContextError,match='database_request_role_unavailable'):
            get_vnext_database_principal_context()
    finally:
        get_supabase_jwt_verifier.cache_clear()
        get_vnext_database_principal_context.cache_clear()
