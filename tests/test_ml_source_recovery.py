"""Synthetic packages exercise offline recovery; no real row fixtures are committed."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import zipfile
from uuid import uuid4

import pytest


def recovery():
    spec = importlib.util.find_spec('scripts.ml.source_recovery')
    assert spec is not None, 'offline source recovery implementation required'
    return importlib.import_module('scripts.ml.source_recovery')


def package(path, missing=None):
    with zipfile.ZipFile(path, 'w') as z:
        for name in ['manifest.csv', 'schema-main.csv', 'schema-build.csv', 'schema-land.csv', 'schema-park.csv']:
            if name != missing:
                z.writestr(name, 'name,title\n')
        z.writestr('a_lvr_land_a.csv', 'synthetic\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_hash_is_required_even_when_filename_reused(tmp_path):
    r = recovery()
    p = tmp_path / 'same.zip'
    expected = package(p)
    assert r.inspect_candidate(p, expected)['checksum_status'] == 'EXACT_MATCH'
    assert r.inspect_candidate(p, expected)['recovery_status'] == 'RECOVERABLE_EXACT'
    p.write_bytes(p.read_bytes() + b'changed')
    result = r.inspect_candidate(p, expected)
    assert result['checksum_status'] == 'HASH_MISMATCH'
    assert result['recovery_status'] == 'SOURCE_CHANGED'
    assert result['expected_sha256'] == expected


def test_missing_and_unhashed_source_do_not_claim_exact(tmp_path):
    r = recovery()
    assert r.inspect_candidate(tmp_path / 'absent.zip', 'a'*64)['checksum_status'] == 'UNVERIFIABLE'
    p = tmp_path / 'no-prior.zip'
    package(p)
    result = r.inspect_candidate(p, None)
    assert result['checksum_status'] == 'RECOVERED_NO_PRIOR_HASH'
    assert result['recovery_status'] == 'RECOVERABLE_BUT_IDENTITY_UNCERTAIN'


def test_exact_bytes_without_schema_are_not_onboarded(tmp_path):
    r = recovery()
    p = tmp_path / 'missing-schema.zip'
    h = package(p, 'schema-park.csv')
    result = r.inspect_candidate(p, h)
    assert result['checksum_status'] == 'EXACT_MATCH'
    assert result['package_valid'] is False
    assert result['recovery_status'] != 'RECOVERABLE_EXACT'


def test_preflight_does_not_invent_publication_or_exactness():
    r = recovery()
    entry = json.loads(Path('docs/ml/valuation-source-release-ledger-v1.json').read_text(encoding='utf-8'))['releases'][0]
    result = r.classify_probe(entry, {'status_code': 200, 'final_url': entry['source_url'],
                                    'content_length': entry['declared_archive_bytes']})
    assert result == 'RECOVERABLE_BUT_IDENTITY_UNCERTAIN'
    changed = {'status_code': 200, 'final_url': entry['source_url'], 'content_length': 441}
    assert r.classify_probe(entry, changed) == 'SOURCE_CHANGED'
    assert r.classify_probe(entry, {'status_code':404,'final_url':entry['source_url']}) == 'NOT_FOUND'


def test_download_failure_is_persisted_and_not_retried(tmp_path):
    r = recovery()
    ledger = json.loads(Path('docs/ml/valuation-source-release-ledger-v1.json').read_text(encoding='utf-8'))
    entry = next(x for x in ledger['releases'] if x['release_label']=='112S3')
    class FailingTransport:
        def download(self, *args, **kwargs):
            raise OSError('PRIVATE_INPUT_MUST_NOT_LEAK')
    # Use an ignored workspace destination: raw bytes never go in an arbitrary path.
    destination = Path('artifacts/ml/plvr-source-recovery/test-failure') / uuid4().hex
    result = r.download_once(entry, destination, FailingTransport())
    assert result['checksum_status'] == 'UNVERIFIABLE'
    assert result['download_attempts'] == 1
    assert 'PRIVATE_INPUT' not in json.dumps(result)
    with pytest.raises(ValueError, match='attempt_already_recorded'):
        r.download_once(entry, destination, FailingTransport())


def test_scope_and_destination_cannot_be_expanded(tmp_path):
    r = recovery()
    entry = next(x for x in json.loads(Path('docs/ml/valuation-source-release-ledger-v1.json').read_text(encoding='utf-8'))['releases'] if x['release_label']=='112S3')
    bad = deepcopy(entry)
    bad['source_url'] = 'https://example.com/unrelated.zip'
    with pytest.raises(ValueError, match='outside_recovery_set'):
        r.download_once(bad, Path('artifacts/ml/plvr-source-recovery'), None)
    class NoNetwork:
        def download(self, *args, **kwargs):
            raise AssertionError('test_transport_must_never_access_network')
    outside = r.s.ROOT / '.pytest-temp-recovery-outside' / uuid4().hex
    with pytest.raises(ValueError, match='ignored_workspace_destination_required'):
        r.download_once(entry, outside, NoNetwork())


@pytest.mark.parametrize('mutation', [
    {'retrieved_at':'not-a-timestamp'}, {'download_attempts':100},
    {'http':{'status_code':404}}, {'http':{'status_code':200,'final_url':'https://example.com/'}},
    {'expected_sha256':'0'*64}, {'byte_size':1},
])
def test_manifest_rejects_unverified_retrieval_evidence(tmp_path, monkeypatch, mutation):
    r = recovery()
    ledger = json.loads(r.LEDGER.read_text(encoding='utf-8'))
    entry = next(x for x in ledger['releases'] if x['release_label']=='112S3')
    archive = tmp_path / entry['local_archive_filename']
    sha = package(archive)
    entry['archive_sha256'] = sha
    entry['declared_archive_bytes'] = archive.stat().st_size
    ledger_path = tmp_path / 'test-ledger.json'
    ledger_path.write_text(json.dumps(ledger), encoding='utf-8')
    monkeypatch.setattr(r, 'LEDGER', ledger_path)
    stamp = '2026-10-07T00:00:00+00:00'
    probes = [{'source_release_id':x['source_release_id'], 'source_url':x['source_url'],
               'expected_sha256':x['archive_sha256'], 'expected_bytes':x['declared_archive_bytes'],
               'probe_attempts':1, 'observation_finished_at':stamp,
               'http':{'status_code':200, 'final_url':x['source_url'], 'content_length':x['declared_archive_bytes']}}
              for x in ledger['releases']]
    record = {'source_release_id':entry['source_release_id'], 'sha256':sha, 'expected_sha256':sha,
              'byte_size':archive.stat().st_size, 'download_attempts':1, 'started_at':stamp,
              'retrieved_at':stamp, 'http':{'status_code':200, 'final_url':entry['source_url'],
                                           'content_length':archive.stat().st_size}}
    record.update(mutation)
    with pytest.raises(ValueError, match='retrieval_evidence_invalid'):
        r.build_manifest({'sources':probes}, [record], root=tmp_path)


def test_unretrieved_sources_have_no_archive_retrieval_claim(tmp_path):
    r = recovery()
    ledger = json.loads(r.LEDGER.read_text(encoding='utf-8'))
    stamp = '2026-10-07T00:00:00+00:00'
    probes = [{'source_release_id':x['source_release_id'], 'source_url':x['source_url'],
               'expected_sha256':x['archive_sha256'], 'expected_bytes':x['declared_archive_bytes'],
               'probe_attempts':1, 'observation_finished_at':stamp,
               'http':{'status_code':200,'final_url':x['source_url'],'content_length':x['declared_archive_bytes']}}
              for x in ledger['releases']]
    manifest = r.build_manifest({'sources':probes}, [], root=tmp_path)
    assert all(x['retrieved_at'] is None for x in manifest['sources'])
    assert all('No archive retrieval' in x['availability_evidence'] for x in manifest['sources'])
