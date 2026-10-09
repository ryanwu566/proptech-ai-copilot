from services import runtime_dependency_evidence as runtime

import pytest


def test_empty_python_audit_is_unknown():
    assert runtime.python_projection({'dependencies': []}, manifest_sha256='a' * 64)['status'] == 'UNKNOWN'


def test_python_findings_keep_unknown_severity_blocking():
    payload = {'dependencies': [{'name': 'example-package', 'version': '1.0',
        'vulns': [{'id': 'PYSEC-2026-1', 'fix_versions': ['2.0']}]}]}
    result = runtime.python_projection(payload, manifest_sha256='a' * 64)
    assert result['status'] == 'BLOCKED'
    assert result['findings'][0]['severity'] == 'UNKNOWN'
    assert result['findings'][0]['id'] == 'PYSEC-2026-1'


def test_npm_missing_metadata_does_not_pass():
    assert runtime.npm_projection({'vulnerabilities': {}}, lock_sha256='a' * 64)['status'] == 'UNKNOWN'


def test_npm_runtime_high_is_blocked():
    payload = {'metadata': {'vulnerabilities': {'total': 1}}, 'vulnerabilities': {
        'package': {'severity': 'high', 'via': [{'source': 1, 'name': 'package', 'severity': 'high', 'url': 'https://github.com/advisories/GHSA-abcd-abcd-abcd'}]}}}
    result = runtime.npm_projection(payload, lock_sha256='a' * 64)
    assert result['status'] == 'BLOCKED'
    assert len(result['findings']) == 1


def test_npm_inconsistent_high_counts_cannot_pass():
    result = runtime.npm_projection({'metadata': {'vulnerabilities': {'high': 99, 'critical': 99, 'total': 0}},
        'vulnerabilities': {}}, lock_sha256='a' * 64)
    assert result['status'] != 'PASS'


def test_npm_nested_critical_is_not_discarded():
    result = runtime.npm_projection({'metadata': {'vulnerabilities': {'total': 1}}, 'vulnerabilities': {
        'package': {'severity': 'low', 'via': [{'severity': 'critical', 'url': 'https://github.com/advisories/GHSA-abcd-abcd-abcd'}]}}}, lock_sha256='a' * 64)
    assert result['status'] == 'BLOCKED'
    assert result['findings'][0]['severity'] == 'critical'


def test_python_partial_report_preserves_known_findings():
    result = runtime.python_projection({'dependencies': [
        {'name': 'package', 'version': '1.0', 'vulns': [{'id': 'PYSEC-1', 'fix_versions': []}]},
        {'name': 'skipped', 'skip_reason': 'private-local-path'}]}, manifest_sha256='a' * 64)
    assert result['status'] == 'BLOCKED'
    assert result['findings'][0]['id'] == 'PYSEC-1'
    assert result['invalid_or_skipped_dependencies'] == 1
    assert 'private-local-path' not in str(result)


def test_npm_later_invalid_row_cannot_erase_critical():
    result = runtime.npm_projection({'metadata': {}, 'vulnerabilities': {
        'first': {'severity': 'critical', 'via': []}, 'later': None}}, lock_sha256='a' * 64)
    assert result['status'] == 'BLOCKED'
    assert result['findings'][0]['severity'] == 'critical'
    assert result['invalid_entries'] == 1


def test_test_runner_is_not_installed_in_alternate_production_image():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    runtime_manifest = (root / 'requirements.txt').read_text()
    assert not any(line.strip().startswith('pytest') for line in runtime_manifest.splitlines())


def test_malformed_npm_severity_is_unknown_without_crashing():
    result = runtime.npm_projection({'auditReportVersion': 2, 'metadata': {'vulnerabilities': {}},
        'vulnerabilities': {'package': {'severity': {}, 'via': []}}}, lock_sha256='a' * 64)
    assert result['status'] == 'UNKNOWN'


@pytest.mark.parametrize(('severity', 'status'), [('critical', 'BLOCKED'), ('low', 'UNKNOWN')])
def test_schema_valid_npm_audit_with_unsanitizable_name_never_passes(severity, status):
    from scripts.npm_audit_gate import _audit_schema_error

    name = 'a' * 161
    counts = {key: int(key == severity) for key in ('info', 'low', 'moderate', 'high', 'critical')}
    payload = {'auditReportVersion': 2, 'metadata': {'vulnerabilities': {**counts, 'total': 1}},
        'vulnerabilities': {name: {'name': name, 'severity': severity, 'isDirect': True,
            'via': [{'source': 1, 'name': name, 'dependency': name, 'title': 'fixture-advisory',
                'url': 'https://github.com/advisories/GHSA-abcd-abcd-abcd', 'severity': severity,
                'range': '*', 'cwe': [], 'cvss': {'score': 9.8, 'vectorString': 'fixture'}}],
            'effects': [], 'range': '*', 'nodes': ['node_modules/' + name], 'fixAvailable': False}}}
    assert _audit_schema_error(payload) is None
    result = runtime.npm_projection(payload, lock_sha256='a' * 64)
    assert result['status'] == status
    assert result['invalid_entries'] == 1
    assert result['findings'][0]['severity'] == severity
    assert result['findings'][0]['package'] == 'unidentified-package'
    assert name not in str(result)
    assert result['reason_code'] == 'audit_inconsistent_or_invalid'
