"""Collect local bounded evidence. No networking, dotenv, provider calls or writes except output."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.production_closure import SCHEMA, acceptance_projection, configuration_projection, deployment_projection, provider_projection
from services.production_artifact_registry import artifact_section
from services.production_identity import backend_identity
from services.provider_config_contract import REQUIREMENTS
from services.provider_config_contract import valid_sha
from services.runtime_dependency_evidence import python_projection, npm_projection


def read_payload(path: Path | None, limit: int = 2_000_000) -> object:
    if path is None:
        return None
    try:
        if path.stat().st_size > limit:
            return None
        with path.open('rb') as stream:
            raw = stream.read(limit + 1)
        return json.loads(raw) if len(raw) <= limit else None
    except (OSError, ValueError):
        return None


def read_json(path: Path | None, limit: int = 2_000_000) -> dict | None:
    data = read_payload(path, limit)
    return data if isinstance(data, dict) else None


def collect(*, as_of: date, values: dict, smoke: dict | None = None,
            python_audit: dict | None = None, npm_audit: dict | None = None,
            machine_audit: dict | None = None, npm_full: dict | None = None,
            npm_policy_result: dict | None = None, alternate_python_audit: dict | None = None,
            provider_evidence: dict | None = None, offline_artifacts: list[dict] | None = None) -> dict:
    manifest_hash = hashlib.sha256((ROOT / 'backend/requirements.txt').read_bytes()).hexdigest()
    lock_hash = hashlib.sha256((ROOT / 'frontend_next/package-lock.json').read_bytes()).hexdigest()
    python = python_projection(python_audit, manifest_sha256=manifest_hash)
    alternate_hash = hashlib.sha256((ROOT / 'requirements.txt').read_bytes()).hexdigest()
    alternate = python_projection(alternate_python_audit, manifest_sha256=alternate_hash)
    alternate['scope'] = 'alternate_streamlit_docker_manifest_resolution'
    frontend = npm_projection(npm_audit, lock_sha256=lock_hash)
    machine = python_projection(machine_audit, manifest_sha256=manifest_hash)
    machine.update(scope='machine_global_not_deployable_runtime', manifest_sha256=None)
    dev = npm_projection(npm_full, lock_sha256=lock_hash)
    dev['scope'] = 'frontend_all_dependencies'
    # These are raw audit inputs from this operator invocation. No claim that the
    # audit was run in the deployed image, or that its Python resolver was 3.12/Linux.
    runtime = {'schema_version': SCHEMA, 'status': 'UNKNOWN', 'python': python, 'alternate_python': alternate, 'frontend': frontend,
               'machine_global': machine, 'frontend_all': dev,
               'development_exception_policy': npm_policy_result or {'status': 'UNKNOWN'},
               'collector_python': platform.python_version(), 'collector_platform': sys.platform,
               'deployment_python_contract': '3.12/Linux', 'deployment_resolution_locked': False,
               'audit_tool_contract': 'pip-audit>=2,<3; npm auditReportVersion=2',
               'manifests': {'backend': ['Dockerfile.cloudrun', 'render.yaml', 'backend/requirements.txt'],
                             'alternate_runtime': ['Dockerfile', 'docker-compose.yml', 'requirements.txt'],
                             'frontend': ['frontend_next/package.json', 'frontend_next/package-lock.json']},
               'development_test_manifest': 'requirements-dev.txt; CI workflows declare separate test dependencies',
               'reason_code': 'deployed_runtime_inventory_missing'}
    providers = [provider_projection(c, values, (provider_evidence or {}).get(c)) for c in sorted(REQUIREMENTS) if c != 'hosted']
    sections = {'deployment': deployment_projection(smoke, values.get('EXPECTED_FRONTEND_COMMIT_SHA', ''), values.get('EXPECTED_BACKEND_COMMIT_SHA', '')),
                'configuration': configuration_projection(values), 'artifacts': artifact_section(values, as_of=as_of),
                'providers': {'schema_version': SCHEMA, 'status': 'BLOCKED', 'records': providers, 'network_requests': 0},
                'runtime_dependencies': runtime}
    if offline_artifacts:
        sections['artifacts']['offline_receipts'] = offline_artifacts
    checkout_sha, dirty = None, None
    try:
        captured = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True,
                                  capture_output=True, timeout=5, check=True).stdout.strip()
        checkout_sha = captured if valid_sha(captured) else None
        dirty = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, text=True,
                                    capture_output=True, timeout=5, check=True).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {'schema_version': SCHEMA, 'as_of': as_of.isoformat(), 'scope': 'local_checkout_not_production',
            'source_checkout_sha': checkout_sha, 'source_checkout_dirty': dirty,
            'backend_build': backend_identity(environ=values), 'sections': sections,
            'acceptance': acceptance_projection(sections), 'network_requests': 0,
            'privacy': {'secrets_included': False, 'raw_payloads_included': False}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--as-of', required=True, type=date.fromisoformat)
    parser.add_argument('--smoke-json', type=Path)
    parser.add_argument('--python-audit-json', type=Path)
    parser.add_argument('--npm-production-audit-json', type=Path)
    parser.add_argument('--npm-full-audit-json', type=Path)
    parser.add_argument('--machine-audit-json', type=Path)
    parser.add_argument('--alternate-python-audit-json', type=Path)
    parser.add_argument('--provider-evidence-json', type=Path, action='append', default=[])
    parser.add_argument('--offline-artifact', choices=('wra-flood', 'gsmma-sensitivity'))
    parser.add_argument('--artifact-manifest', type=Path)
    parser.add_argument('--artifact-file', type=Path)
    parser.add_argument('--scenario', default='24h-350mm')
    parser.add_argument('--dataset-version')
    parser.add_argument('--npm-explanation-json', type=Path)
    parser.add_argument('--use-runtime-environment', action='store_true', help='Read categories from process environment; never load dotenv')
    args = parser.parse_args()
    if len(args.provider_evidence_json) > 24:
        parser.error('at most 24 bounded provider receipts')
    provider_evidence = {}
    for path in args.provider_evidence_json:
        evidence = read_json(path)
        if evidence and isinstance(evidence.get('capability'), str) and evidence['capability'] in REQUIREMENTS:
            provider_evidence[evidence['capability']] = evidence
    offline_artifacts = []
    if args.offline_artifact:
        if not args.artifact_manifest or not args.artifact_file:
            parser.error('offline artifact requires explicit saved manifest and artifact paths')
        from services.production_artifact_registry import verify_local_artifact
        offline_artifacts.append(verify_local_artifact(args.offline_artifact, args.artifact_manifest,
                                args.artifact_file, scenario=args.scenario, dataset_version=args.dataset_version))
    policy = None
    if args.npm_full_audit_json and args.npm_production_audit_json and args.npm_explanation_json:
        from scripts.npm_audit_gate import evaluate_json, DEFAULT_POLICY
        try:
            if any(p.stat().st_size > 2_000_000 for p in (args.npm_full_audit_json, args.npm_production_audit_json, args.npm_explanation_json)):
                raise ValueError('audit_input_too_large')
            outcome = evaluate_json(json.dumps(read_payload(args.npm_full_audit_json)),
                                    json.dumps(read_payload(args.npm_production_audit_json)),
                                    json.dumps(read_payload(args.npm_explanation_json)),
                                    DEFAULT_POLICY.read_text(encoding='utf-8'), today=args.as_of)
            policy = {'status': outcome['status'], 'accepted': outcome['accepted'], 'error_count': len(outcome['errors'])}
        except (OSError, ValueError):
            policy = {'status': 'UNKNOWN'}
    result = collect(as_of=args.as_of, values=dict(os.environ) if args.use_runtime_environment else {},
                     smoke=read_json(args.smoke_json), python_audit=read_json(args.python_audit_json),
                     npm_audit=read_json(args.npm_production_audit_json), machine_audit=read_json(args.machine_audit_json),
                     npm_full=read_json(args.npm_full_audit_json), npm_policy_result=policy,
                     alternate_python_audit=read_json(args.alternate_python_audit_json),
                     provider_evidence=provider_evidence, offline_artifacts=offline_artifacts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('PRODUCTION_CLOSURE=' + result['acceptance']['lane_status'])
    return 0 if result['acceptance']['lane_status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
