"""Pure, bounded acceptance projections. Configuration is never authorization."""
from __future__ import annotations

import hashlib
import json
from typing import Mapping
from urllib.parse import urlsplit

from services.production_config import load_runtime_configuration
from services.provider_config_contract import REQUIREMENTS, SOURCES, configuration_status, valid_sha

SCHEMA = 'production-provider-closure-v1'
PLACEHOLDERS = ('changeme', 'change-me', 'replace-me', 'replace_me', 'placeholder', 'your_', 'your-', '<', '>')


def reserved_host(value: str) -> bool:
    host = value.lower().rstrip('.')
    return (not host or host in {'localhost', '127.0.0.1', '::1'}
            or host.endswith(('.invalid', '.example', '.test', '.internal', '.localhost'))
            or any(host == domain or host.endswith('.' + domain) for domain in ('example.com', 'example.org', 'example.net')))


def placeholder(value: str) -> bool:
    lower = value.strip().lower()
    return (not lower or lower in {'default', 'example', 'test', 'dummy', 'secret', 'unconfigured', 'unknown', 'latest'}
            or any(word in lower for word in PLACEHOLDERS))


def configuration_projection(values: Mapping[str, str]) -> dict:
    try:
        config = load_runtime_configuration(values).safe_report()
    except (ValueError, TypeError):
        config = {}
    names = {'database': ('DATABASE_URL', 'PILOT_EVIDENCE_DATABASE_URL'),
             'session_secret': ('PILOT_SESSION_SIGNING_KEY',), 'cors_origins': ('CORS_ALLOWED_ORIGINS',),
             'public_base_url': ('PUBLIC_APP_BASE_URL',), 'release_version': ('RELEASE_VERSION',),
             'api_contract_version': ('API_CONTRACT_VERSION',), 'schema_version': ('SCHEMA_VERSION',)}
    items = {}
    for item, env_names in names.items():
        raw = next((values.get(name, '') for name in env_names if values.get(name, '').strip()), '')
        valid = config.get(item) == 'configured' and not placeholder(raw)
        if item in {'database', 'cors_origins', 'public_base_url'} and valid:
            try:
                for value in raw.split(','):
                    host = urlsplit(value.strip()).hostname or ''
                    if reserved_host(host):
                        valid = False
                    if item != 'database' and urlsplit(value.strip()).scheme != 'https':
                        valid = False
            except ValueError:
                valid = False
        items[item] = {'status': 'PASS' if valid else 'BLOCKED', 'required': True,
                       'reason_code': 'configuration_contract_present' if valid else 'missing_invalid_or_placeholder'}
    mode = values.get('APP_ENV', '').strip().lower()
    items['production_environment'] = {'status': 'PASS' if mode == 'production' else 'BLOCKED', 'required': True}
    items['runtime_readiness'] = {'status': 'PASS' if config.get('ready') is True else 'BLOCKED', 'required': True}
    backend_url = values.get('BACKEND_PUBLIC_URL', '')
    try:
        parsed = urlsplit(backend_url)
        valid_backend_url = (parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username
                             and not parsed.password and not parsed.query and not parsed.fragment
                             and parsed.path in {'', '/'} and not reserved_host(parsed.hostname))
    except ValueError:
        valid_backend_url = False
    items['backend_public_origin'] = {'status': 'PASS' if valid_backend_url else 'BLOCKED', 'required': True}
    # Hash only categories, not secret values. This is an acceptance contract identity,
    # not a fingerprint of the complete deployed configuration.
    digest = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    return {'schema_version': SCHEMA, 'scope': 'runtime_configuration_contract',
            'status': 'PASS' if all(r['status'] == 'PASS' for r in items.values()) else 'BLOCKED',
            'items': items, 'projection_sha256': digest, 'authorization_proven': False,
            'component': 'backend', 'frontend_configuration': 'UNKNOWN',
            'limitation': 'Backend runtime contract only; frontend build configuration, secret rotation, IAM and schema migration remain unverified.'}


def provider_projection(capability: str, values: Mapping[str, str], evidence: dict | None = None) -> dict:
    config = configuration_status(capability, values)
    for name in config:
        if placeholder(values.get(name, '')):
            config[name] = 'missing-or-placeholder'
    configured = 'NOT_APPLICABLE' if not config else 'PASS' if all(v == 'present' for v in config.values()) else 'BLOCKED'
    disabled = capability == 'satellite' and values.get('EARTH_ENGINE_SATELLITE_REFERENCE_V1', '').lower() != 'true'
    manual = capability in {'active-fault', 'tax-legal'}
    kill_capabilities = {'ardswc-landslide': ('ardswc', 'terrain'), 'ardswc-debris-flow': ('ardswc', 'terrain'),
                         'ardswc': ('ardswc', 'terrain'), 'wra': ('terrain',), 'gsmma': ('terrain',),
                         'liquefaction': ('liquefaction', 'terrain'), 'nlsc': ('nlsc', 'terrain'),
                         'geocoding': ('geocoding',), 'places': ('places',), 'routes': ('routes',),
                         'tgos': ('tgos',), 'satellite': ('satellite',), 'valuation': ('valuation',),
                         'finder': ('finder',), 'trend': ('trend',), 'market': ('market',)}.get(capability, ())
    killed = any(values.get('ANTI_ABUSE_' + name.upper() + '_DISABLED', '').strip().lower()
                 not in {'', '0', 'false', 'no', 'off'} for name in kill_capabilities)
    row = {'capability': capability, 'provider': SOURCES[capability], 'configured': configured,
           'configuration': config, 'authorized': 'NOT_TESTED', 'reachable': 'NOT_TESTED',
           'contract_compatible': 'NOT_TESTED', 'fresh': 'UNKNOWN', 'degraded': None,
           'unavailable': True if disabled or manual else None, 'production_accepted': False,
           'status': 'NOT_APPLICABLE' if disabled or manual else 'BLOCKED' if configured == 'BLOCKED' else 'UNKNOWN',
           'reason_code': 'intentionally_disabled' if disabled else 'manual_verification_required' if manual else 'production_not_tested'}
    if evidence and evidence.get('capability') in {None, capability}:
        # Existing evidence is checkout-scoped, even when a single live query passed.
        # It cannot prove deployed credentials, freshness or operator authorization.
        if evidence.get('test_mode') in {'offline-fixture', 'bounded-live'}:
            row['contract_compatible'] = 'PASS' if evidence.get('result') == 'pass' else 'BLOCKED'
            row['contract_scope'] = 'local_fixture' if evidence['test_mode'] == 'offline-fixture' else 'operator_probe'
        if evidence.get('test_mode') == 'bounded-live':
            row['reachable'] = 'PASS' if evidence.get('result') == 'pass' else 'BLOCKED'
            row['authorized'] = 'UNKNOWN'  # Legal/billing/restriction approval is independent.
    if killed:
        row.update(unavailable=True, status='BLOCKED', reason_code='runtime_kill_switch')
    return row


def deployment_projection(smoke: dict | None, expected_frontend: str = '', expected_backend: str = '') -> dict:
    result = {'schema_version': SCHEMA, 'status': 'UNKNOWN', 'frontend_sha': None, 'backend_sha': None,
              'reason_code': 'hosted_observation_missing'}
    if not isinstance(smoke, dict) or smoke.get('mode') != 'hosted':
        return result
    identities = smoke.get('release_identity', {})
    if not isinstance(identities, dict):
        return result
    for component in ('frontend', 'backend'):
        value = identities.get(component + '_sha', '')
        result[component + '_sha'] = value.lower() if isinstance(value, str) and valid_sha(value) else None
    if not all(result[c + '_sha'] for c in ('frontend', 'backend')):
        return result
    expected = (expected_frontend, expected_backend)
    if not all(valid_sha(s) for s in expected):
        return {**result, 'reason_code': 'expected_identities_missing'}
    matching = result['frontend_sha'] == expected_frontend.lower() and result['backend_sha'] == expected_backend.lower()
    checks = smoke.get('checks', {})
    from services.production_identity import utc_timestamp
    required_checks = ('deployed_identity', 'backend_build_identity', 'release_environment', 'release_identity',
                       'frontend_commit_sha', 'backend_commit_sha', 'backend_security_headers', 'cache_safety')
    verified = (matching and smoke.get('status') == 'pass' and isinstance(checks, dict)
                and utc_timestamp(smoke.get('checked_at'))
                and all(checks.get(k) == 'pass' for k in required_checks))
    observation = {'mode': 'hosted', 'status': 'pass' if verified else 'fail',
                   'checked_at': smoke.get('checked_at') if utc_timestamp(smoke.get('checked_at')) else None,
                   'release_identity': {'frontend_sha': result['frontend_sha'], 'backend_sha': result['backend_sha']},
                   'checks': {k: 'pass' if isinstance(checks, dict) and checks.get(k) == 'pass' else 'fail' for k in required_checks}}
    return {**result, 'status': 'PASS' if verified else 'BLOCKED',
            'expected_frontend_sha': expected_frontend.lower(), 'expected_backend_sha': expected_backend.lower(),
            'observation': observation,
            'reason_code': 'hosted_identities_verified' if verified else 'identity_or_release_contract_unverified'}


def acceptance_projection(sections: dict, *, expected_backend_commit: str | None = None) -> dict:
    if not isinstance(sections, dict):
        sections = {}
    required = ('deployment', 'configuration', 'artifacts', 'providers', 'runtime_dependencies')
    blockers = []
    for name in required:
        section = sections.get(name)
        try:
            complete = _complete_section(name, section)
            if name == 'deployment' and expected_backend_commit is not None:
                complete = complete and section.get('backend_sha') == expected_backend_commit.lower()
        except (ValueError, TypeError, KeyError, AttributeError):
            complete = False
        if not complete:
            blockers.append(name)
    return {'schema_version': 'final-production-acceptance-v2-input',
            'lane_status': 'BLOCKED' if blockers else 'PASS', 'blockers': blockers,
            'product_go': False, 'scope': 'assigned_closure_lane_only'}


def _complete_section(name: str, section: object) -> bool:
    if not isinstance(section, dict) or section.get('schema_version') != SCHEMA or section.get('status') != 'PASS':
        return False
    if name == 'deployment':
        observation = deployment_projection(section.get('observation'), section.get('expected_frontend_sha', ''),
                                             section.get('expected_backend_sha', ''))
        return (observation['status'] == 'PASS'
                and all(section.get(c + '_sha') == observation[c + '_sha'] for c in ('frontend', 'backend')))
    if name == 'configuration':
        # Backend runtime reports and local frontend env values cannot attest the
        # separate deployed frontend build. No hosted config receipt exists yet.
        return False
    # This lane has no authenticated deployed artifact/provider/image reader.
    # A caller's arbitrary JSON cannot add that authority by changing its scope
    # or PASS fields. Local receipts remain consumable evidence, with blockers.
    # A future deployed collector must define and validate its receipt contract
    # before any of these sections can close; do not accept a speculative schema.
    return False
