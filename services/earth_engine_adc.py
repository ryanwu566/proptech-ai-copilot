"""Offline Professor Earth Engine ADC contract: impersonation, never private keys.

This module opens no files and performs no discovery, authentication or network
requests. Only the operator installer supplies real credential bytes.
"""
from __future__ import annotations

import json
import re

PROJECT = 'project-3bd34c3e-daee-493f-ad6'
SERVICE_ACCOUNT = 'proptech-render-earth-engine@' + PROJECT + '.iam.gserviceaccount.com'
IMPERSONATION_URL = ('https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/'
                     + SERVICE_ACCOUNT + ':generateAccessToken')
TOKEN_URL = 'https://oauth2.googleapis.com/token'
_TOP = {'type', 'service_account_impersonation_url', 'source_credentials',
        'delegates', 'quota_project_id', 'universe_domain'}
_SOURCE = {'type', 'client_id', 'client_secret', 'refresh_token', 'token_uri',
           'universe_domain', 'account'}


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError()
        result[name] = value
    return result


def _scalar(value):
    return (isinstance(value, str) and 0 < len(value) <= 8192 and value == value.strip()
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def validate_keyless_adc(raw: str) -> dict:
    """Accept one fixed target and renewable user source; refuse unknown schemas.

    The refresh token/client secret remain protected secrets. No cached access
    token, executable, alternate endpoint, delegation chain, external-account
    source or private-key fallback is accepted. WIF needs a separately reviewed
    renewable subject identity and bounded source contract.
    """
    try:
        if not isinstance(raw, str) or len(raw.encode('utf-8')) > 65536:
            raise ValueError()
        data = json.loads(raw, object_pairs_hook=_unique_object)
        if (not isinstance(data, dict) or set(data) - _TOP
                or data.get('type') != 'impersonated_service_account'
                or data.get('service_account_impersonation_url') != IMPERSONATION_URL
                or data.get('delegates', []) != []
                or data.get('quota_project_id', PROJECT) != PROJECT
                or data.get('universe_domain', 'googleapis.com') != 'googleapis.com'):
            raise ValueError()
        source = data.get('source_credentials')
        if (not isinstance(source, dict) or set(source) - _SOURCE
                or source.get('type') != 'authorized_user'
                or source.get('token_uri', TOKEN_URL) != TOKEN_URL
                or source.get('universe_domain', 'googleapis.com') != 'googleapis.com'
                or not all(_scalar(source.get(k)) for k in ('client_id', 'client_secret', 'refresh_token'))
                or not re.fullmatch(r'[A-Za-z0-9._-]{1,256}[.]apps[.]googleusercontent[.]com', source['client_id'])
                or 'account' in source and not (source['account'] == '' or _scalar(source['account']))):
            raise ValueError()
        return data
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError('earth_engine_adc_contract_invalid') from None


def credential_scalars(raw: str) -> tuple[str, str]:
    """Internal scanner input only; callers must never log or return these."""
    source = validate_keyless_adc(raw)['source_credentials']
    return source['refresh_token'], source['client_secret']
