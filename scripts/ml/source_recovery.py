"""Bounded official-source recovery. Default operations are offline and read-only."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from . import contracts as c
from . import lineage as l
from . import semantics as s
from .audit_foundation import _archive_status, file_sha256, read_json

LEDGER = s.ROOT / 'docs/ml/valuation-source-release-ledger-v1.json'
ARTIFACT_ROOT = s.ROOT / 'artifacts/ml/plvr-source-recovery'


def classify_probe(entry: dict, http: dict) -> str:
    if http.get('final_url') != entry['source_url']:
        return 'UNKNOWN'
    if http.get('status_code') in {404, 410}:
        return 'NOT_FOUND'
    if http.get('status_code') not in {200, 206}:
        return 'UNKNOWN'
    size = http.get('content_length')
    if size is not None and size != entry['declared_archive_bytes']:
        return 'SOURCE_CHANGED'
    return 'RECOVERABLE_BUT_IDENTITY_UNCERTAIN'


def inspect_candidate(path: Path, expected: str | None) -> dict:
    result = {'expected_sha256': expected, 'sha256': None, 'byte_size': None,
              'checksum_status': 'UNVERIFIABLE', 'package_valid': False,
              'recovery_status': 'NOT_FOUND', 'reason': 'local_bytes_missing'}
    if not path.is_file():
        return result
    result.update(sha256=file_sha256(path), byte_size=path.stat().st_size)
    if expected and result['sha256'] != expected:
        result.update(checksum_status='HASH_MISMATCH', recovery_status='SOURCE_CHANGED',
                      reason='historical_checksum_mismatch')
        return result
    result['checksum_status'] = 'EXACT_MATCH' if expected else 'RECOVERED_NO_PRIOR_HASH'
    status, reason = _archive_status(path, result['sha256'])
    result.update(package_valid=status == 'AVAILABLE', reason=reason,
                  recovery_status='RECOVERABLE_EXACT' if expected and status == 'AVAILABLE'
                  else 'RECOVERABLE_BUT_IDENTITY_UNCERTAIN')
    return result


def ignored_destination(destination: Path) -> Path:
    resolved = destination.resolve()
    if not resolved.is_relative_to(ARTIFACT_ROOT.resolve()):
        raise ValueError('ignored_workspace_destination_required')
    relative = (resolved / 'ignore-probe').relative_to(s.ROOT).as_posix()
    check = subprocess.run(['git', 'check-ignore', '-q', relative], cwd=s.ROOT, capture_output=True)
    if check.returncode != 0:
        raise ValueError('ignored_workspace_destination_required')
    return resolved


def download_once(entry: dict, destination: Path, transport=None) -> dict:
    """One attempt per release/destination, persisted before networking; no retries.

    Deliberately does not acquire the moving current object. A preflight for the
    complete bounded set must exist before any use of the CLI download operation.
    """
    ledger = read_json(LEDGER)
    known = {r['source_release_id']: r for r in ledger['releases']}
    original = known.get(entry.get('source_release_id'))
    if original is None or entry != original or entry['release_kind'] == 'current':
        raise ValueError('outside_recovery_set')
    target_dir = ignored_destination(destination)
    target_dir.mkdir(parents=True, exist_ok=True)
    marker = target_dir / (entry['source_release_id'] + '.attempt.json')
    if marker.exists():
        raise ValueError('attempt_already_recorded')
    target = target_dir / entry['local_archive_filename']
    if target.exists():
        raise ValueError('source_already_exists_no_overwrite')
    result = {'source_release_id': entry['source_release_id'], 'download_attempts': 1,
              'retrieval_started_at': datetime.now(timezone.utc).isoformat(),
              'expected_sha256':entry['archive_sha256'],
              'checksum_status': 'UNVERIFIABLE', 'recovery_status': 'UNKNOWN'}
    with marker.open('x', encoding='utf-8') as f:
        json.dump(result, f, sort_keys=True)
    if transport is None:
        from services.plvr_clean_shadow_rebuild import HttpxArtifactTransport
        transport = HttpxArtifactTransport()
    try:
        http = transport.download(entry['source_url'], target, timeout=45,
                                  max_bytes=32 * 1024 * 1024)
        if http.final_url != entry['source_url'] or http.status_code != 200:
            raise ValueError('unexpected_download_response')
        result['http'] = asdict(http)
        result.update(inspect_candidate(target, entry['archive_sha256']))
    except Exception as error:
        # Private exception text must never enter public evidence.
        result['failure_class'] = type(error).__name__
    result['retrieved_at'] = datetime.now(timezone.utc).isoformat()
    marker.write_bytes(l.canonical_bytes(result) + b'\n')
    return result


def build_manifest(preflight: dict, downloads: list[dict], root: Path = ARTIFACT_ROOT) -> dict:
    ledger = read_json(LEDGER)
    c.validate_ledger(ledger)
    probes = {r['source_release_id']: r for r in preflight['sources']}
    ids = {r['source_release_id'] for r in ledger['releases']}
    if len(preflight['sources']) != 17 or set(probes) != ids:
        raise ValueError('complete_bounded_preflight_required')
    retrieved = {r['source_release_id']: r for r in downloads}
    if len(retrieved) != len(downloads) or not set(retrieved) <= ids:
        raise ValueError('download_scope_or_duplicates')
    sources = []
    for entry in ledger['releases']:
        key = entry['source_release_id']
        probe = probes[key]
        if (probe['source_url'] != entry['source_url'] or probe['expected_sha256'] != entry['archive_sha256']
                or probe['expected_bytes'] != entry['declared_archive_bytes']):
            raise ValueError('preflight_identity_mismatch')
        local = root / entry['local_archive_filename']
        candidate = inspect_candidate(local, entry['archive_sha256'])
        status = classify_probe(entry, probe.get('http', {}))
        if key in retrieved:
            record = retrieved[key]
            http = record.get('http', {})
            start = l.timestamp(record.get('started_at') or record.get('retrieval_started_at'))
            end = l.timestamp(record.get('retrieved_at'))
            if (http.get('status_code') != 200 or http.get('final_url') != entry['source_url']
                    or record.get('download_attempts') != 1 or start is None or end is None or start > end
                    or record.get('expected_sha256') != entry['archive_sha256']
                    or record.get('byte_size') != candidate['byte_size']
                    or (http.get('content_length') is not None and http['content_length'] != candidate['byte_size'])):
                raise ValueError('retrieval_evidence_invalid')
            status = candidate['recovery_status']
            if candidate['sha256'] != retrieved[key].get('sha256'):
                raise ValueError('retrieval_checksum_conflict')
        elif local.exists():
            raise ValueError('unrecorded_local_candidate')
        sources.append({
            'source_archive_id': key, 'official_source': c.SOURCE_ID,
            'release_version': entry['release_label'], 'official_url': entry['source_url'],
            'expected_filename': entry['original_archive_filename'],
            'expected_sha256': entry['archive_sha256'], 'expected_bytes': entry['declared_archive_bytes'],
            'local_recovered_path': local.relative_to(s.ROOT).as_posix() if key in retrieved else None,
            'sha256': candidate['sha256'], 'byte_size': candidate['byte_size'],
            'checksum_status': candidate['checksum_status'], 'package_valid': candidate['package_valid'],
            'recovery_status': status, 'retrieved_at': retrieved.get(key, {}).get('retrieved_at'),
            'historical_retrieval_claim': entry['retrieved_at'],
            'release_published_at': None, 'public_available_at': None, 'system_available_at': None,
            'availability_bounds': {'historical_upper_bound': None, 'historical_lower_bound': None,
                                    'current_observation_upper_bound': retrieved.get(key, {}).get('retrieved_at')},
            'availability_evidence': ('current verified HTTPS retrieval only; historical publication remains unknown'
                                      if key in retrieved else 'No archive retrieval in this task; historical availability unknown'),
            'http_probe': probe.get('http'), 'probe_observation_finished_at': probe['observation_finished_at'],
            'http_download':retrieved.get(key, {}).get('http'),
            'retrieval_started_at':retrieved.get(key, {}).get('started_at') or retrieved.get(key, {}).get('retrieval_started_at'),
            'probe_attempts': probe['probe_attempts'], 'download_attempts': retrieved.get(key, {}).get('download_attempts',0),
            'schema_identity': [], 'source_county_members': [],
            'disposition': 'selected_for_bounded_semantic_audit' if key in retrieved else 'not_downloaded',
        })
    return {'schema_version': 'plvr-source-recovery-manifest-v1', 'historical_ledger_sha256': l.digest(ledger),
            'preflight_sha256': l.digest(preflight), 'sources': sources}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', type=Path, default=ARTIFACT_ROOT / 'preflight.json')
    parser.add_argument('--downloads', type=Path, default=ARTIFACT_ROOT / 'downloads.json')
    args = parser.parse_args()
    try:
        print(json.dumps(build_manifest(read_json(args.preflight), read_json(args.downloads)),
                         ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(2, 'source_recovery_failed: invalid bounded inputs\n')


if __name__ == '__main__':
    main()
