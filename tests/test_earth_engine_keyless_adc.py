"""Only synthetic ADC and in-memory transports; no Google/provider calls."""
from datetime import datetime, timedelta, timezone
import json
import os
import stat
import sys
from types import SimpleNamespace

import pytest

TARGET = 'proptech-render-earth-engine@project-3bd34c3e-daee-493f-ad6.iam.gserviceaccount.com'
URL = 'https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/' + TARGET + ':generateAccessToken'
SCOPES = ('https://www.googleapis.com/auth/earthengine', 'https://www.googleapis.com/auth/cloud-platform')


def adc_info():
    return {'type': 'impersonated_service_account', 'service_account_impersonation_url': URL,
            'delegates': [], 'source_credentials': {
                'type': 'authorized_user', 'client_id': 'synthetic.apps.googleusercontent.com',
                'client_secret': 'SYNTHETIC_OAUTH_CLIENT_SECRET_0123456789',
                'refresh_token': 'SYNTHETIC_OAUTH_REFRESH_MATERIAL_0123456789'}}


def validate(info):
    from services.selfhost_secret_files import validate_credential
    return validate_credential('earth_engine_adc_json', json.dumps(info))


def test_installer_accepts_keyless_impersonated_adc_without_private_key():
    assert validate(adc_info()) == json.dumps(adc_info())


@pytest.mark.parametrize('change', [
    {'type': 'service_account', 'private_key': 'SYNTHETIC_FORBIDDEN'},
    {'type': 'authorized_user'}, {'type': 'external_account'},
    {'service_account_impersonation_url': URL.replace(TARGET, 'other@project.iam.gserviceaccount.com')},
    {'service_account_impersonation_url': URL.replace('iamcredentials.googleapis.com', 'attacker.invalid')},
    {'service_account_impersonation_url': URL + '?key=SYNTHETIC_FORBIDDEN'},
    {'service_account_impersonation_url': URL.replace('https:', 'http:')},
    {'delegates': ['other@project.iam.gserviceaccount.com']},
    {'credential_source': {'executable': {'command': 'unreviewed-command'}}},
    {'token': 'SYNTHETIC_CACHED_ACCESS_TOKEN'}, {'private_key': 'SYNTHETIC_FORBIDDEN'},
    {'universe_domain': 'attacker.invalid'}, {'quota_project_id': 'foreign-project'},
    {'scopes': ['https://www.googleapis.com/auth/drive']},
])
def test_installer_refuses_unreviewed_adc_authority_and_private_keys(change):
    from services.selfhost_secret_files import SecretRefused
    info = adc_info(); info.update(change)
    with pytest.raises(SecretRefused, match='^earth_engine_adc_contract_invalid$'):
        validate(info)


@pytest.mark.parametrize('change', [
    {'type': 'service_account', 'private_key': 'SYNTHETIC_FORBIDDEN'},
    {'token_uri': 'https://attacker.invalid/token'}, {'refresh_token': ''},
    {'client_secret': 'line\nbreak'}, {'client_id': 'invalid-client'},
    {'access_token': 'SYNTHETIC_CACHED'}, {'private_key': 'SYNTHETIC_FORBIDDEN'},
    {'credential_source': {'file': '/unreviewed/path'}},
    {'universe_domain': 'attacker.invalid'}, {'rapt_token': 'SYNTHETIC_REAUTH_TOKEN'},
])
def test_installer_refuses_unreviewed_source_credentials(change):
    from services.selfhost_secret_files import SecretRefused
    info = adc_info(); info['source_credentials'].update(change)
    with pytest.raises(SecretRefused, match='^earth_engine_adc_contract_invalid$'):
        validate(info)


def test_duplicate_json_fields_fail_closed_without_reflection():
    from services.selfhost_secret_files import SecretRefused, validate_credential
    raw = json.dumps(adc_info()).replace('"delegates": []', '"delegates": [], "delegates": []')
    with pytest.raises(SecretRefused, match='^earth_engine_adc_contract_invalid$'):
        validate_credential('earth_engine_adc_json', raw)


def test_only_the_accepted_project_and_default_google_endpoints_are_allowed():
    info = adc_info()
    info.update(universe_domain='googleapis.com', quota_project_id='project-3bd34c3e-daee-493f-ad6')
    info['source_credentials'].update(token_uri='https://oauth2.googleapis.com/token',
                                     universe_domain='googleapis.com')
    assert validate(info)


def test_empty_optional_source_account_matches_google_sdk_semantics(tmp_path, monkeypatch):
    import google.auth
    info=adc_info();info['source_credentials']['account']=''
    raw=validate(info)
    path=tmp_path/'synthetic-empty-account-adc.json';path.write_text(raw);path.chmod(0o600)
    monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS',str(path))
    credentials,_=google.auth.default(scopes=SCOPES,request=lambda **kw:pytest.fail('network forbidden'))
    assert credentials.service_account_email==TARGET


@pytest.mark.parametrize('account',[None,7,'\n',' whitespace '])
def test_optional_source_account_is_still_bounded(account):
    from services.selfhost_secret_files import SecretRefused
    info=adc_info();info['source_credentials']['account']=account
    with pytest.raises(SecretRefused,match='^earth_engine_adc_contract_invalid$'):validate(info)


def test_installer_leak_scan_covers_nested_refresh_and_client_secret():
    from scripts.ops.professor_provider_storage import scanner_values
    from services.professor_activation_scan import SecretScanner, ScanRefused
    from tests.test_professor_required_providers import values
    material = values(); material['GOOGLE_APPLICATION_CREDENTIALS'] = json.dumps(adc_info())
    scanner = SecretScanner(scanner_values(material, []))
    for name in ('client_secret', 'refresh_token'):
        with pytest.raises(ScanRefused, match='^credential_detected$'):
            scanner.check_bytes(('unrelated-prefix ' + adc_info()['source_credentials'][name]).encode())


@pytest.mark.parametrize('direct_user', [False, True])
def test_isolated_image_probe_checks_real_adc_loader_without_refresh(tmp_path, monkeypatch, capsys, direct_user):
    import google.auth
    from scripts.ops.professor_provider_storage import PROBE
    info = adc_info()['source_credentials'] if direct_user else adc_info()
    (tmp_path/'earth_engine_adc_json').write_text(json.dumps(info))
    (tmp_path/'earth_engine_project').write_text('project-3bd34c3e-daee-493f-ad6')
    real_load = google.auth.default
    calls = []
    def load(*args, **kwargs):
        calls.append(True)
        return real_load(*args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(sys, 'argv', ['probe','earth_engine','earth_engine_adc_json','earth_engine_project'])
        patch.setattr(os, 'fstat', lambda fd: SimpleNamespace(st_mode=stat.S_IFREG|0o440,
            st_uid=0,st_gid=10001,st_nlink=1,st_size=1024))
        patch.setattr(google.auth,'default',load)
        patch.setattr(os, 'environ', dict(os.environ))
        code=PROBE.replace('/run/provider-verify/',str(tmp_path)+'/')
        if direct_user:
            with pytest.raises(SystemExit) as caught: exec(code,{})
            assert caught.value.code==1
        else:
            exec(code,{})
    result=json.loads(capsys.readouterr().out)
    assert calls==[True]
    assert result['status']==('REFUSED' if direct_user else 'PASS')
    assert result['values_returned'] is False


class FakeTransport:
    def __init__(self):
        self.urls = []

    def __call__(self, url, method='GET', body=None, headers=None, **kwargs):
        self.urls.append(url)
        if url == 'https://oauth2.googleapis.com/token':
            data = {'access_token': 'SYNTHETIC_SOURCE_ACCESS', 'expires_in': 3600, 'token_type': 'Bearer'}
        elif url == URL:
            request = json.loads(body)
            assert set(request['scope']) == set(SCOPES) and request['lifetime'] == '3600s'
            assert request['delegates'] == []
            data = {'accessToken': 'SYNTHETIC_IMPERSONATED_ACCESS',
                    'expireTime': (datetime.now(timezone.utc) + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')}
        else:
            pytest.fail('unreviewed authentication endpoint')
        return SimpleNamespace(status=200, data=json.dumps(data).encode(), headers={})


def load_adc(tmp_path, monkeypatch):
    import google.auth
    path = tmp_path / 'synthetic-impersonation-adc.json'
    path.write_text(validate(adc_info())); path.chmod(0o600)
    monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', str(path))
    monkeypatch.delenv('GOOGLE_CLOUD_QUOTA_PROJECT', raising=False)
    def no_network(*args, **kwargs):
        pytest.fail('ADC discovery must not perform network calls')
    return google.auth.default(scopes=SCOPES, request=no_network)[0], path


def test_real_google_auth_loads_and_refreshes_after_restart_without_gcloud(tmp_path, monkeypatch):
    from google.auth import impersonated_credentials
    credentials, path = load_adc(tmp_path, monkeypatch)
    transport = FakeTransport(); credentials.refresh(transport)
    assert isinstance(credentials, impersonated_credentials.Credentials)
    assert credentials.service_account_email == TARGET and credentials.valid
    assert transport.urls == ['https://oauth2.googleapis.com/token', URL]
    assert 'SYNTHETIC_IMPERSONATED_ACCESS' not in path.read_text()
    # A new process/reboot can reload the same protected refresh material.
    credentials, _ = load_adc(tmp_path, monkeypatch)
    second = FakeTransport(); credentials.refresh(second)
    assert credentials.valid and second.urls == transport.urls


def test_existing_earth_engine_adapter_consumes_keyless_adc_and_renews_short_tokens(tmp_path, monkeypatch):
    from services.adapters.earth_engine_adapter import EarthEngineSatelliteAdapter
    credentials, _ = load_adc(tmp_path, monkeypatch)
    transport = FakeTransport(); initialized = []
    fake_ee = SimpleNamespace(data=SimpleNamespace(setMaxRetries=lambda n: None),
                              Initialize=lambda **kw: initialized.append(kw))
    adapter = EarthEngineSatelliteAdapter(project='project-3bd34c3e-daee-493f-ad6', ee_module=fake_ee,
        auth_default=lambda **kw: (credentials, None), auth_request_factory=lambda: transport)
    adapter.initialize(); adapter.initialize()
    assert len(initialized) == 1 and initialized[0]['credentials'].service_account_email == TARGET
    assert transport.urls == ['https://oauth2.googleapis.com/token', URL]
    active = initialized[0]['credentials']
    active.expiry = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    active.refresh(transport)
    assert active.valid and transport.urls[-1] == URL


def test_revoked_impersonation_source_fails_sanitized_without_earth_engine_call(tmp_path, monkeypatch, caplog):
    from services.adapters.earth_engine_adapter import EarthEngineSatelliteAdapter
    from services.satellite_reference import EarthEngineCredentialUnavailable
    credentials, _ = load_adc(tmp_path, monkeypatch)
    initialized = []
    def refused(*args, **kwargs):
        raise RuntimeError('SYNTHETIC_REFRESH_MUST_NEVER_BE_LOGGED')
    fake_ee = SimpleNamespace(Initialize=lambda **kw: initialized.append(kw))
    adapter = EarthEngineSatelliteAdapter(project='project-3bd34c3e-daee-493f-ad6', ee_module=fake_ee,
        auth_default=lambda **kw: (credentials, None), auth_request_factory=lambda: refused)
    with pytest.raises(EarthEngineCredentialUnavailable, match='^Application Default Credentials are unavailable$'):
        adapter.initialize()
    assert not initialized and 'SYNTHETIC_REFRESH_MUST_NEVER_BE_LOGGED' not in caplog.text
