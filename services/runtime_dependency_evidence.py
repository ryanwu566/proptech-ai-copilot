"""Sanitized dependency evidence. Unknown/skipped audits never become PASS."""
from __future__ import annotations

import re

TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,159}\Z')


def safe(value: object) -> str | None:
    return value if isinstance(value, str) and TOKEN.fullmatch(value) else None


def python_projection(payload: object, *, manifest_sha256: str) -> dict:
    unknown = {'status': 'UNKNOWN', 'scope': 'manifest_resolution', 'manifest_sha256': manifest_sha256,
               'packages': [], 'findings': [], 'reason_code': 'audit_missing_or_invalid', 'deployed_runtime': 'UNKNOWN'}
    if not isinstance(payload, dict) or not isinstance(payload.get('dependencies'), list) or not 0 < len(payload['dependencies']) <= 1000:
        return unknown
    packages, findings, invalid = [], [], 0
    for dep in payload['dependencies']:
        if (not isinstance(dep, dict) or not safe(dep.get('name')) or not safe(dep.get('version'))
            or not isinstance(dep.get('vulns'), list) or len(dep['vulns']) > 100 or dep.get('skip_reason')):
            invalid += 1
            continue
        packages.append({'name': dep['name'], 'version': dep['version']})
        for vuln in dep['vulns']:
            if not isinstance(vuln, dict) or not safe(vuln.get('id')) or not isinstance(vuln.get('fix_versions', []), list):
                invalid += 1
                continue
            fixes = vuln.get('fix_versions', [])
            if len(fixes) > 100 or not all(safe(v) for v in fixes):
                invalid += 1
                continue
            findings.append({'package': dep['name'], 'version': dep['version'], 'id': vuln['id'],
                             'severity': 'UNKNOWN', 'fix_versions': fixes})
    return {**unknown, 'status': 'BLOCKED' if findings else 'UNKNOWN' if invalid else 'PASS',
            'packages': sorted(packages, key=lambda p: p['name']), 'findings': findings,
            'invalid_or_skipped_dependencies': invalid,
            'reason_code': 'vulnerabilities_found' if findings else 'audit_incomplete' if invalid else 'resolution_audit_clean'}


def npm_projection(payload: object, *, lock_sha256: str) -> dict:
    unknown = {'status': 'UNKNOWN', 'scope': 'frontend_production_lock', 'lock_sha256': lock_sha256,
               'findings': [], 'reason_code': 'audit_missing_or_invalid', 'deployed_runtime': 'UNKNOWN'}
    if not isinstance(payload, dict) or not isinstance(payload.get('metadata'), dict) or not isinstance(payload.get('vulnerabilities'), dict):
        return unknown
    from scripts.npm_audit_gate import _audit_schema_error, SEVERITY_RANK
    try:
        schema_valid = _audit_schema_error(payload) is None
    except (TypeError, ValueError, KeyError):
        schema_valid = False
    findings, invalid = [], 0
    vulns = payload['vulnerabilities']
    if len(vulns) > 1000:
        return unknown
    for name, vuln in sorted(vulns.items()):
        if (not isinstance(vuln, dict) or not isinstance(vuln.get('severity'), str)
            or vuln.get('severity') not in {'info', 'low', 'moderate', 'high', 'critical'}):
            invalid += 1
            continue
        # Preserve severity even when a package identity cannot be safely emitted.
        safe_name = isinstance(name, str) and safe(name.replace('@', '').replace('/', '-'))
        if not safe_name:
            invalid += 1
        via = vuln.get('via')
        if not isinstance(via, list) or len(via) > 100:
            invalid += 1
            via = []
        ids = []
        severity = vuln['severity']
        for item in via:
            if isinstance(item, dict):
                nested = item.get('severity')
                if isinstance(nested, str) and nested in SEVERITY_RANK and SEVERITY_RANK[nested] > SEVERITY_RANK[severity]:
                    severity = nested
                url = item.get('url', '')
                match = re.fullmatch(r'https://github.com/advisories/(GHSA-[a-z0-9-]+)', url) if isinstance(url, str) else None
                if match:
                    ids.append(match[1])
        findings.append({'package': name if safe_name else 'unidentified-package', 'severity': severity, 'advisories': sorted(set(ids))})
    complete = schema_valid and invalid == 0
    return {**unknown, 'status': 'BLOCKED' if any(v['severity'] in {'high', 'critical'} for v in findings) else 'PASS' if complete else 'UNKNOWN',
            'findings': findings, 'invalid_entries': invalid,
            'reason_code': 'audit_complete' if complete else 'audit_inconsistent_or_invalid'}
