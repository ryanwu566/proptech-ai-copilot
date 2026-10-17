"""Offline private evidence intake, double rebuild and frozen ML-B admission.

Run with python -m scripts.ml.reopen_data_gate --bundle PRIVATE --output PRIVATE.
No CLI switch accepts synthetic authority. Hashes/format checks do not establish
government authenticity: the existing accountable steward review is mandatory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.ml'

from jsonschema import Draft202012Validator, FormatChecker
from . import audit_target_reframing as staging, external_evidence as e
from . import historical as h, lineage as l, observed_transaction as b, semantics as s
from .acquire_external_metadata import official_url
from .audit_foundation import _archive_status, file_sha256, read_json, repository_text_sha256
from .verify_authoritative_history_builds import check_privacy

VERSION = 'ml-data-gate-reopen-v1'
CONTRACTS = s.ROOT / 'docs/ml/contracts'
FROZEN_FILES = ('approved-cohort.json', 'train.json', 'validation.json', 'calibration.json',
                'test.json', 'features.json', 'labels.json', 'feature-contract.json',
                'label-contract.json', 'source-manifest.json', 'chronology.json')
COUNTS = ('raw_observations', 'target_valid', 'PIT_valid', 'chronological_viable', 'approved_training')
CONDITIONS = tuple(e.admission([], {'chronology': {'viable': False}},
                               privacy=False, deterministic=False)['conditions']) + (
                                   'release_continuity', 'authoritative_history_closed')
ISSUES = ('MALFORMED_RECEIPT', 'EVIDENCE_HASH_MISMATCH', 'EVIDENCE_INCOMPLETE',
          'BUNDLE_INVALID', 'NONDETERMINISTIC')


def private_root(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.is_relative_to(s.ROOT.resolve()):
        raise ValueError('private_location_outside_repository_required')
    # A different checkout is still Git. Check the closest existing ancestor.
    ancestor = resolved
    while not ancestor.exists():
        ancestor = ancestor.parent
    result = subprocess.run(['git', '-C', str(ancestor), 'rev-parse', '--show-toplevel'],
                            capture_output=True)
    if result.returncode == 0:
        raise ValueError('private_location_outside_git_required')
    return resolved


def validate_receipts(receipts, root: Path) -> dict:
    """Classify missing/unproven authority separately from malformed/corrupt input.

    Only bounded codes/counts leave this function; schema messages and retained
    paths may contain private data and must never reach a report or terminal.
    """
    result = {'invalid': False, 'blocked': False, 'supplied': 0, 'accepted': 0, 'issues': []}
    if not isinstance(receipts, list) or len(receipts) > 1024:
        return {**result, 'invalid': True, 'issues': ['MALFORMED_RECEIPT']}
    result['supplied'] = len(receipts)
    ids = set()
    semantic_fields = {'published_at', 'effective_at', 'proof_class', 'exact_byte_publication_binding',
        'verification', 'license', 'scope', 'stable_across_releases', 'ambiguous',
        'correction_key_policy', 'cancellation_key_policy', 'replacement_key_policy',
        'serial_reuse_policy', 'identifier_field', 'complete_revision_history', 'complete_cancellation_history',
        'replacement_links_complete', 'complete', 'gaps', 'previous_version_id', 'replaces_family_id'}
    for r in receipts:
        kind = r.get('receipt_type') if isinstance(r, dict) else None
        if not isinstance(kind, str) or kind not in e.VALIDATORS:
            result['invalid'] = True
            result['issues'].append('MALFORMED_RECEIPT')
            continue
        errors = list(e.VALIDATORS[kind].iter_errors(r))
        malformed = False
        for error in errors:
            field = str(list(error.absolute_path)[-1]) if error.absolute_path else None
            if error.validator == 'required':
                missing = set(error.validator_value) - set(error.instance)
                malformed |= not missing <= semantic_fields
            else:
                malformed |= field not in semantic_fields
        rid = r.get('receipt_id')
        if not isinstance(rid, str) or rid in ids:
            malformed = True
        else:
            ids.add(rid)
        if malformed:
            result['invalid'] = True
            result['issues'].append('MALFORMED_RECEIPT')
            continue
        if errors:
            result['blocked'] = True
            continue
        validation = e.validate_receipt(r, root)
        if validation['valid']:
            result['accepted'] += 1
        else:
            integrity = {'RETAINED_BYTES_MISMATCH', 'RETAINED_PATH_INVALID',
                         'RETAINED_ARTIFACT_UNAVAILABLE_OR_UNBOUNDED', 'EVIDENCE_HASH_INVALID',
                         'SYNTHETIC_NOT_REAL_EVIDENCE', 'PERSONAL_DATA_FORBIDDEN'}
            if set(validation['reasons']) & integrity:
                result['invalid'] = True
                result['issues'].append('EVIDENCE_HASH_MISMATCH' if 'RETAINED_BYTES_MISMATCH' in validation['reasons'] else 'MALFORMED_RECEIPT')
            else:
                result['blocked'] = True
    if result['invalid']:
        result['issues'] = sorted(set(result['issues']))
    elif result['blocked']:
        result['issues'] = ['EVIDENCE_INCOMPLETE']
    return result


def continuity_valid(receipts: list, sources: list, cutoff: str, ledger: list) -> bool:
    matches = [r for r in receipts if r['receipt_type'] == 'ReleaseContinuityReceipt']
    if len(matches) != 1:
        return False
    r = matches[0]
    if (r['complete'] is not True or r['gaps'] or l.timestamp(r['complete_through']) < l.timestamp(cutoff)
            or l.timestamp(r['complete_through']) > l.timestamp(r['retrieved_at'])
            or r['coverage_begin'] > r['coverage_end']):
        return False
    expected = {(x['source_archive_id'], x['sha256']) for x in sources}
    entries = r['releases']
    if (len(entries) != len(expected) or {(x['release_id'], x['archive_sha256']) for x in entries} != expected
            or set(r['scope']['release_ids']) != {x[0] for x in expected}
            or set(r['scope']['county_codes']) != {'a', 'f'}):
        return False
    # Explicit provider manifest order/edges; never derive edges from hashes/dates.
    previous = None
    for entry in entries:
        if entry['predecessor_release_id'] != previous:
            return False
        previous = entry['release_id']
    for x in ledger:
        day = s.parse_roc_date(x['raw'].get('交易年月日'))
        if day and not r['coverage_begin'] <= day['value'] <= r['coverage_end']:
            # Out-of-target rows still belong in history. The attestation must
            # cover them rather than silently filtering them before lineage.
            return False
    return True


def empty_report() -> dict:
    return {'version': VERSION, 'status': 'BLOCKED', 'dry_run': False, 'ml_b_authorized': False,
        'target_a': 'BLOCKED', 'counts': {k: 0 for k in COUNTS},
        'evidence': {**{k: 'MISSING_REAL_EVIDENCE' for k in ('E1', 'E2', 'E3', 'E4')},
                     'E5': 'NOT_REQUIRED_FOR_TARGET_B'},
        'admission': {'version': e.admission_policy()['version'],
                      'conditions': {k: False for k in CONDITIONS}},
        'receipt_validation': {'supplied': 0, 'accepted': 0}, 'issues': [],
        'reproducibility': {'python_version': sys.version.split()[0],
            'receipt_contract_version': e.VERSION, 'target_contract_version': b.TARGET_VERSION,
            'source_manifest_sha256': '0'*64, 'receipt_manifest_sha256': '0'*64,
            'bundle_manifest_sha256': '0'*64,
            'admission_contract_sha256': file_sha256(e.POLICY_PATH),
            'contracts_sha256': l.digest({p.name: repository_text_sha256(p) for p in sorted(CONTRACTS.glob('*.json'))}),
            'code_sha256': l.digest({p.name: repository_text_sha256(p) for p in sorted((s.ROOT/'scripts/ml').glob('*.py'))}),
            'chronology_sha256': '0'*64, 'output_hashes': {}},
        'double_build_equal': False}


def evaluate(ledger, certificates, coverage, diagnostics, *, continuity_valid: bool,
             cutoff: str, deterministic: bool):
    gate = h.data_gate(ledger, cutoff, history_certificate=certificates,
                       coverage_evidence=coverage if continuity_valid else None, pit_v3=True)
    selected = h.select_pit_v3(ledger, cutoff, history_certificate=certificates)['selected']
    admission = e.admission(selected, gate, privacy=True, deterministic=deterministic)
    allowed = {'after_availability_cutoff', 'superseded_version', 'cancelled_as_of_cutoff',
               'exact_duplicate', 'republication', 'TARGET_B_OR_PARKING_INVALID'}
    def closed(boundary, exclusions):
        if any(count and reason not in allowed for reason, count in exclusions.items()):
            return False
        visible = [x for x in ledger if h.publication(x)['available_at']
                   and l.timestamp(h.publication(x)['available_at']) <= l.timestamp(boundary)]
        versions = {l.identify(x)['version_id']: l.identify(x)['transaction_family_id'] for x in visible}
        for x in visible:
            parent = x.get('supersedes_version_id')
            if parent is not None and (parent not in versions
                    or versions[parent] != l.identify(x)['transaction_family_id']):
                return False
            if x.get('replaces_family_id') is not None:
                return False  # explicit changed-ID edges remain quarantined by the frozen selector
        return bool(visible)
    history_closed = closed(cutoff, gate['asof_exclusions'])
    for freeze in sorted({x['selection_cutoff'] for x in gate['chronology']['assignments']}):
        selection = h.select_as_of(ledger, freeze, history_certificate=certificates)
        history_closed = history_closed and closed(freeze, selection['excluded_reasons'])
    conditions = {**admission['conditions'], 'release_continuity': continuity_valid,
                  'authoritative_history_closed': history_closed}
    passed = all(v is True for v in conditions.values())
    report = empty_report()
    report.update(status='PASS' if passed else 'BLOCKED', ml_b_authorized=passed,
                  double_build_equal=deterministic)
    report['counts'].update({k: gate['counts'][k] for k in COUNTS if k in gate['counts']})
    report['counts']['approved_training'] = gate['counts']['approved_training'] if passed else 0
    report['admission']['conditions'] = conditions
    report['receipt_validation'] = {k: diagnostics.get(k, 0) for k in ('supplied', 'accepted')}
    report['evidence'].update(E1='IMPLEMENTED_VALIDATION' if ledger and all(h.publication(x)['available_at'] for x in ledger) else 'MISSING_REAL_EVIDENCE',
        E2='IMPLEMENTED_VALIDATION' if ledger and all(x.get('identity_evidence') for x in ledger) else 'MISSING_REAL_EVIDENCE',
        E3='IMPLEMENTED_VALIDATION' if certificates and not diagnostics.get('rejection_reasons') else 'MISSING_REAL_EVIDENCE',
        E4='IMPLEMENTED_VALIDATION' if continuity_valid else 'MISSING_REAL_EVIDENCE')
    # Keep all frozen rows private. Their hashes alone may enter the public report.
    private = {'chronology.json': gate['chronology']}
    assignments = gate['chronology']['assignments']
    for name in ('TRAIN', 'VALIDATION', 'CALIBRATION', 'TEST'):
        private[name.lower()+'.json'] = [x for x in assignments if x['split'] == name]
    private['features.json'] = [{**l.identify(x), 'values': b.feature_values(x, b.classify(x, cutoff)['target'])} for x in selected]
    private['labels.json'] = [{**l.identify(x), 'target': b.classify(x, cutoff)['target']} for x in selected]
    private['approved-cohort.json'] = [l.identify(x) for x in selected] if passed else []
    private['feature-contract.json'] = {'version': b.TARGET_VERSION, 'columns': list(b.FEATURE_COLUMNS)}
    private['label-contract.json'] = read_json(staging.CONTRACT_PATH)
    report['reproducibility']['chronology_sha256'] = l.digest(gate['chronology'])
    return report, private


def public_bytes(report: dict) -> bytes:
    """Closed shape and value vocabulary, including nested fields; no raw text."""
    template = empty_report()
    def check(value, sample, path=()):
        if isinstance(sample, dict):
            if not isinstance(value, dict): raise ValueError('public_shape')
            if path == ('reproducibility', 'output_hashes'):
                if not set(value) <= set(FROZEN_FILES): raise ValueError('public_hash_scope')
                if not all(e.hash_valid(x) for x in value.values()): raise ValueError('public_hash')
            else:
                if set(value) != set(sample): raise ValueError('public_keys')
                for key in sample: check(value[key], sample[key], path+(key,))
        elif isinstance(sample, bool):
            if type(value) is not bool: raise ValueError('public_boolean')
        elif isinstance(sample, int):
            if type(value) is not int or not 0 <= value <= 100000000: raise ValueError('public_count')
        elif isinstance(sample, list):
            if not isinstance(value, list) or any(x not in ISSUES for x in value): raise ValueError('public_issues')
        elif path[0] == 'evidence':
            if value not in {'MISSING_REAL_EVIDENCE', 'IMPLEMENTED_VALIDATION', 'NOT_REQUIRED_FOR_TARGET_B'}: raise ValueError('public_evidence')
        elif path[-1] == 'status':
            if value not in {'PASS', 'BLOCKED', 'INVALID_EVIDENCE'}: raise ValueError('public_status')
        elif path[-1].endswith('sha256'):
            if not e.hash_valid(value): raise ValueError('public_hash')
        elif value != sample:
            raise ValueError('public_string')
    check(report, template)
    check_privacy(report)
    return l.canonical_bytes(report) + b'\n'


def load_bundle(root: Path):
    config = read_json(root/'bundle.json')
    schema = read_json(CONTRACTS/'data-gate-bundle-v1.schema.json')
    if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(config):
        raise ValueError('bundle_schema')
    if l.timestamp(config['cutoff']) > l.timestamp(config['observation_at']):
        raise ValueError('bundle_time_order')
    sources = config['sources']
    ids = [x['source_archive_id'] for x in sources]
    if len(set(ids)) != len(ids) or len({x['local_recovered_path'] for x in sources}) != len(sources):
        raise ValueError('bundle_duplicate_sources')
    for source in sources:
        path = Path(source['local_recovered_path'])
        resolved = (root/path).resolve()
        if (path.is_absolute() or '..' in path.parts or ':' in str(path)
                or not resolved.is_relative_to(root) or not resolved.is_file()
                or not official_url(source['official_url'])
                or source['official_url'].split('/')[2] not in e.AUTHORITY_HOSTS['MOI_LAND']
                or l.timestamp(source['retrieved_at']) > l.timestamp(config['observation_at'])
                or resolved.stat().st_size != source['byte_size']
                or file_sha256(resolved) != source['sha256']):
            raise ValueError('bundle_source_integrity')
        if _archive_status(resolved, source['sha256'])[0] != 'AVAILABLE':
            raise ValueError('bundle_source_package')
    return config


def apply_intake_clock(items: list, config: dict) -> None:
    """Use only an explicitly supplied operator execution observation.

    Legacy logical snapshots retain null execution clocks. This clock describes
    the new intake run and never supplies historical availability or publication.
    """
    observation = l.timestamp(config['observation_at'])
    receipts = config['receipts']
    retrievals = [l.timestamp(x.get('retrieved_at')) for x in config['sources'] + receipts
                  if isinstance(x, dict) and l.timestamp(x.get('retrieved_at')) is not None]
    if any(stamp > observation for stamp in retrievals):
        raise ValueError('observation_before_evidence_retrieval')
    if 'execution_observed_at' not in config:
        return
    execution = l.timestamp(config['execution_observed_at'])
    if execution is None or execution > observation or any(stamp > execution for stamp in retrievals):
        raise ValueError('explicit_ordered_execution_observation_required')
    for x in items:
        x.update(ingested_at=config['execution_observed_at'], transformed_at=config['execution_observed_at'])


def build_once(root: Path):
    config = load_bundle(root)
    validation = validate_receipts(config['receipts'], root)
    manifest = {'schema_version': 'private-source-manifest-v1', 'sources': [
        {**x, 'checksum_status': 'EXACT_MATCH', 'package_valid': True,
         'expected_sha256': x['sha256']} for x in config['sources']]}
    items, manifest, _ = staging.stage_manifest(manifest, config['observation_at'], root)
    if len(items) > 100000: raise ValueError('bounded_ledger')
    apply_intake_clock(items, config)
    receipts = config['receipts'] if not validation['invalid'] and not validation['blocked'] else []
    ledger, certificates, coverage, diagnostics = e.ingest(items, receipts, root)
    continuous = continuity_valid(receipts, config['sources'], config['cutoff'], ledger)
    continuity = next((r for r in receipts if r['receipt_type'] == 'ReleaseContinuityReceipt'), None)
    report, private = evaluate(ledger, certificates, e.reference(continuity) if continuous else coverage,
        diagnostics, continuity_valid=continuous, cutoff=config['cutoff'], deterministic=False)
    if validation['invalid']:
        report['status'] = 'INVALID_EVIDENCE'
    report['receipt_validation'] = {k: validation[k] for k in ('supplied', 'accepted')}
    report['issues'] = validation['issues']
    report['reproducibility'].update(source_manifest_sha256=l.digest(manifest),
        receipt_manifest_sha256=l.digest(config['receipts']), bundle_manifest_sha256=l.digest(config))
    private['source-manifest.json'] = manifest
    # The full unfiltered ledger is compared too, although never exported.
    return report, private, h.ledger_digest(ledger)


def rebuild(root: Path, *, dry_run=False):
    """Two fresh byte/hash/parser/receipt/PIT/chronology builds, no caller flags."""
    root = private_root(root)
    first = build_once(root)
    second = build_once(root)
    if l.canonical_bytes(first) != l.canonical_bytes(second):
        report = empty_report(); report.update(dry_run=dry_run, issues=['NONDETERMINISTIC'])
        return report, {}
    report, private, _ = second
    report['double_build_equal'] = True
    report['admission']['conditions']['independent_determinism'] = True
    passed = report['status'] != 'INVALID_EVIDENCE' and all(report['admission']['conditions'].values())
    # Dry-run may validate complete inputs but can never authorize/freeze a cohort.
    passed = passed and not dry_run
    report.update(dry_run=dry_run, status='INVALID_EVIDENCE' if report['status'] == 'INVALID_EVIDENCE' else 'PASS' if passed else 'BLOCKED',
                  ml_b_authorized=passed)
    if passed:
        private['approved-cohort.json'] = [
            {k: v for k, v in row.items() if k != 'target'} for row in private['labels.json']]
        report['counts']['approved_training'] = len(private['approved-cohort.json'])
    else:
        private['approved-cohort.json'] = []
        report['counts']['approved_training'] = 0
    report['reproducibility']['output_hashes'] = {k: hashlib.sha256(l.canonical_bytes(v)+b'\n').hexdigest()
                                                 for k, v in sorted(private.items())}
    public_bytes(report)
    return report, private


def artifacts(report, private):
    decision = public_bytes(report)
    lines = [f"Decision: {report['status']}", f"ML-B authorized: {str(report['ml_b_authorized']).lower()}",
             f"Target B candidates: {report['counts']['target_valid']}",
             f"PIT-valid: {report['counts']['PIT_valid']}",
             f"Approved cohort: {report['counts']['approved_training']}"]
    lines += [f'{key}: {value}' for key, value in report['evidence'].items()]
    lines += ['Unsatisfied admission conditions:'] + [key for key, value in report['admission']['conditions'].items() if not value]
    result = {'decision.json': decision, 'summary.md': ('\n'.join(lines)+'\n').encode('utf-8')}
    if report['ml_b_authorized']:
        result.update({k: l.canonical_bytes(v)+b'\n' for k, v in private.items()})
    result['output-hashes.json'] = l.canonical_bytes({k: hashlib.sha256(v).hexdigest() for k, v in sorted(result.items())})+b'\n'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        root, output = private_root(args.bundle), private_root(args.output)
        if output == root or output.is_relative_to(root) or root.is_relative_to(output):
            raise ValueError('separate_evidence_output_required')
        report, private = rebuild(root, dry_run=args.dry_run)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, zipfile.BadZipFile):
        report, private = empty_report(), {}
        report.update(status='INVALID_EVIDENCE', dry_run=args.dry_run, issues=['BUNDLE_INVALID'])
    payloads = artifacts(report, private)
    try:
        output = private_root(args.output)
        # Precheck every file before writing anything. Never mix stale PASS files.
        if output.exists() and {p.name for p in output.iterdir()} != set(payloads):
            raise ValueError('clean_output_required')
        if output.exists() and any((output/k).read_bytes() != v for k, v in payloads.items()):
            raise ValueError('create_only_output_required')
        output.mkdir(parents=True, exist_ok=True)
        for key, value in payloads.items():
            if not (output/key).exists():
                with (output/key).open('xb') as handle: handle.write(value)
    except (OSError, ValueError):
        parser.exit(2, 'INVALID_EVIDENCE: private create-only output contract\n')
    print(payloads['decision.json'].decode('utf-8'), end='')
    return 0 if report['status'] == 'PASS' else 2 if report['status'] == 'INVALID_EVIDENCE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
