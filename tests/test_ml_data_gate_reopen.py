"""Software-only synthetic contracts. None of these fixtures are real evidence."""
from copy import deepcopy
import importlib
import json
from pathlib import Path

import pytest

from scripts.ml import external_evidence as e, historical as h, lineage as l
from tests.test_ml_external_evidence import bundle, receipt
from tests.test_ml_target_reframing import item, CUTOFF


def reopen():
    return importlib.import_module('scripts.ml.reopen_data_gate')


def continuity(tmp_path, xs):
    r = receipt(tmp_path)
    r.update(receipt_type='ReleaseContinuityReceipt', receipt_id='continuity',
             complete=True, gaps=[], complete_through=CUTOFF,
             coverage_begin='2024-06-01', coverage_end='2024-06-30',
             releases=[{'release_id': x['release_id'], 'archive_sha256': x['archive_sha256'],
                        'predecessor_release_id': None} for x in xs])
    for key in ('release_id', 'archive_sha256', 'proof_class', 'exact_byte_publication_binding',
                'time_quality', 'original_filename', 'immutable_version_id'):
        r.pop(key)
    return r


def evaluate(tmp_path, xs=None, change=None):
    xs = xs or [item()]
    rs = bundle(tmp_path, xs) + [continuity(tmp_path, xs)]
    if change:
        change(rs)
    # Synthetic acceptance stays in the existing validator, never in the CLI.
    ledger, certificates, coverage, diagnostics = e.ingest(xs, rs[:-1], tmp_path, synthetic_test=True)
    return reopen().evaluate(ledger, certificates, coverage, diagnostics,
        continuity_valid=e.validate_receipt(rs[-1], tmp_path, synthetic_test=True)['valid'],
        cutoff=CUTOFF, deterministic=True)


def test_complete_synthetic_bundle_reaches_frozen_admission(tmp_path):
    report, private = evaluate(tmp_path)
    assert report['status'] == 'BLOCKED'  # one row does not relax 840/21-month rules
    assert report['counts']['PIT_valid'] == 1
    assert report['admission']['version'] == e.admission_policy()['version']
    assert report['ml_b_authorized'] is False


@pytest.mark.parametrize('case', ['publication', 'namespace', 'lineage', 'changed_id', 'continuity'])
def test_missing_authority_blocks(tmp_path, case):
    def change(rs):
        if case == 'publication': rs[:] = [r for r in rs if r['receipt_type'] != 'HistoricalPublicationReceipt']
        elif case == 'namespace': rs[:] = [r for r in rs if r['receipt_type'] != 'TransactionNamespaceAuthority']
        elif case == 'lineage': rs[-2]['events'] = []
        elif case == 'changed_id': rs[-2]['events'][0].update(event_kind='REPLACEMENT', replaces_family_id='f'*64)
        else: rs[-1]['complete'] = False
    report, _ = evaluate(tmp_path, change=change)
    assert report['status'] == 'BLOCKED'
    assert not report['ml_b_authorized']
    assert report['counts']['approved_training'] == 0


def test_hash_mismatch_is_invalid_and_diagnostics_never_echo_private_text(tmp_path):
    r = receipt(tmp_path)
    r.update(evidence_sha256='f'*64, original_filename='PRIVATE-APPLICANT Taipei road 123',
             receipt_id='OFFICIAL-TRANSACTION-SECRET')
    result = reopen().validate_receipts([r], tmp_path)
    assert result['invalid'] is True
    assert result['issues'] == ['EVIDENCE_HASH_MISMATCH']
    assert 'PRIVATE' not in json.dumps(result) and 'SECRET' not in json.dumps(result)


@pytest.mark.parametrize('bad', [None, {}, [None], [{'receipt_type': []}], [{'receipt_id': {}}]])
def test_malformed_bundle_is_invalid_without_traceback(tmp_path, bad):
    assert reopen().validate_receipts(bad, tmp_path)['invalid']


def test_missing_timestamp_or_unknown_namespace_is_blocked_not_corrupt(tmp_path):
    for kind, changes in [('HistoricalPublicationReceipt', {'published_at': None}),
                          ('TransactionNamespaceAuthority', {'ambiguous': True})]:
        r = receipt(tmp_path, kind); r.update(synthetic=False, **changes)
        result = reopen().validate_receipts([r], tmp_path)
        assert not result['invalid'] and result['blocked']


def test_public_artifact_schema_rejects_private_fields_and_values(tmp_path):
    report, _ = evaluate(tmp_path)
    reopen().public_bytes(report)
    for key, value in [('address', 'Taipei road 123'), ('applicant', 'PRIVATE-NAME'),
                       ('raw_document', 'PRIVATE-BODY'), ('official_transaction_id', 'SECRET')]:
        bad = deepcopy(report); bad[key] = value
        with pytest.raises(ValueError): reopen().public_bytes(bad)
    bad = deepcopy(report); bad['status'] = 'Taipei road 123'
    with pytest.raises(ValueError): reopen().public_bytes(bad)


def test_future_revision_and_family_separation_keep_existing_rules(tmp_path):
    x = item(); y = deepcopy(x)
    y.update(release_id='synthetic-later', archive_sha256='d'*64,
             source_release_available_at='2024-09-01T00:00:00+08:00')
    y['raw']['總價元'] = '11000000'; y['raw']['單價元平方公尺'] = '110000'
    rs = bundle(tmp_path, [x, y], kinds=['ORIGINAL', 'REVISION'])
    ledger, cert, _, _ = e.ingest([x, y], rs, tmp_path, synthetic_test=True)
    selected = h.select_pit_v3(ledger, CUTOFF, history_certificate=cert)['selected']
    assert len(selected) == 1 and selected[0]['raw']['總價元'] == '10000000'
    from scripts.ml import chronology, observed_transaction as b
    cohort = b.build_candidates([x], CUTOFF)['selected_rows']
    rows = chronology.split_rows_from_items(cohort)
    splits = chronology.design_splits(rows + rows, coverage_evidence=None,
        ledger_items=ledger, label_observation_cutoff=CUTOFF)
    assert 'DUPLICATE_FAMILY' in splits['blockers'] and not splits['assignments']


def test_private_bundle_must_resolve_outside_repository(tmp_path):
    from scripts.ml import semantics as s
    with pytest.raises(ValueError): reopen().private_root(s.ROOT / 'artifacts')
    assert reopen().private_root(tmp_path) == tmp_path.resolve()


def test_training_guard_refuses_absent_blocked_and_self_asserted_pass(tmp_path):
    guard = importlib.import_module('scripts.ml.check_training_authorization')
    for report in [None, {'status': 'BLOCKED'}, {'status': 'PASS', 'ml_b_authorized': True}]:
        if report: (tmp_path/'decision.json').write_text(json.dumps(report))
        assert guard.authorized(tmp_path) is False


def test_continuity_requires_exact_manifest_chain_and_attested_cutoff(tmp_path):
    xs = [item()]; r = continuity(tmp_path, xs)
    sources = [{'source_archive_id': xs[0]['release_id'], 'sha256': xs[0]['archive_sha256']}]
    assert reopen().continuity_valid([r], sources, CUTOFF, xs)
    for change in ({'complete_through': '2024-07-01T00:00:00+08:00'},
                   {'complete_through': '2030-01-01T00:00:00+08:00'},
                   {'coverage_end': '2024-06-01'}, {'gaps': ['missing']}):
        bad = deepcopy(r); bad.update(change)
        assert not reopen().continuity_valid([bad], sources, CUTOFF, xs)
    bad = deepcopy(r); bad['releases'][0]['archive_sha256'] = 'f'*64
    assert not reopen().continuity_valid([bad], sources, CUTOFF, xs)
    bad = deepcopy(r); bad['releases'][0]['predecessor_release_id'] = 'inferred'
    assert not reopen().continuity_valid([bad], sources, CUTOFF, xs)


def test_intake_rejects_unhashable_receipt_type_without_exception(tmp_path):
    assert not e.validate_receipt({'receipt_type': []}, tmp_path)['valid']


def full_panel(tmp_path):
    """840 fixture rows, actual frozen thresholds, two cities, 21 months."""
    from datetime import datetime, timedelta
    from scripts.ml import semantics as s
    xs = []
    for month in range(21):
        year, number = 2022 + month // 12, month % 12 + 1
        for city in range(2):
            for row in range(20):
                x = item(len(xs)+1, 交易年月日=f'{year-1911:03d}{number:02d}15')
                if city:
                    x['raw'].update(縣市='新北市', 鄉鎮市區='板橋區')
                    x['member_name'] = x['context']['member_name'] = 'f_lvr_land_a.csv'
                x.update(release_id=f'synthetic-{month}', archive_sha256=l.digest(month),
                         source_release_available_at=f'{year}-{number:02d}-20T00:00:00+08:00')
                xs.append(x)
    cutoff = '2023-10-01T00:00:00+08:00'
    rs = bundle(tmp_path, xs, cutoff)
    for event in rs[-1]['events']:
        event['previous_version_id'] = None
    # Independently certify each actual fitting freeze, with the same retained
    # authority reference; changing cutoff/hash never changes event reference.
    preliminary, _, _, _ = e.ingest(xs, rs[:-1], tmp_path, synthetic_test=True)
    for x in preliminary:
        x['cancellation_state_evidenced'] = True
    rs[-1]['visible_ledger_sha256'] = h.ledger_digest(preliminary)
    for freeze in ['2023-01-01', '2023-04-01', '2023-07-01']:
        cert = deepcopy(rs[-1])
        cert['cutoff'] = (datetime.fromisoformat(freeze+'T00:00:00+08:00')-timedelta(microseconds=1)).isoformat()
        visible = [x for x in preliminary if l.timestamp(h.publication(x)['available_at']) <= l.timestamp(cert['cutoff'])]
        cert['visible_ledger_sha256'] = h.ledger_digest(visible)
        # receipt_id must be unique; ORIGINAL events have no revision reference.
        cert['receipt_id'] = 'lineage-'+freeze
        rs.append(cert)
    cr = continuity(tmp_path, [xs[n*40] for n in range(21)])
    cr.update(complete_through=cutoff, coverage_begin='2022-01-01', coverage_end='2023-09-30')
    cr['scope']['release_ids'] = [x['release_id'] for x in xs[::40]]
    for previous, entry in zip([None]+cr['releases'][:-1], cr['releases']):
        entry['predecessor_release_id'] = previous['release_id'] if previous else None
    return xs, rs+[cr], cutoff


def test_full_synthetic_panel_passes_frozen_thresholds_and_freezes_all_four_blocks(tmp_path):
    xs, rs, cutoff = full_panel(tmp_path)
    ledger, certs, coverage, diagnostics = e.ingest(xs, rs, tmp_path, synthetic_test=True)
    assert diagnostics['accepted_receipts'] == len(rs)
    sources = [{'source_archive_id': x['release_id'], 'sha256': x['archive_sha256']} for x in xs[::40]]
    complete = reopen().continuity_valid(rs, sources, cutoff, ledger)
    report, private = reopen().evaluate(ledger, certs, coverage, diagnostics,
        continuity_valid=complete, cutoff=cutoff, deterministic=True)
    assert report['status'] == 'PASS' and report['counts']['approved_training'] == 840
    assert [len(private[name+'.json']) for name in ('train', 'validation', 'calibration', 'test')] == [480, 120, 120, 120]
    all_families = [x['family_id'] for name in ('train', 'validation', 'calibration', 'test') for x in private[name+'.json']]
    assert len(set(all_families)) == 840


def test_bundle_paths_hashes_and_schema_are_checked_before_parser(tmp_path):
    from scripts.ml.audit_foundation import _archive_status
    from tests.test_ml_source_recovery import package
    archive = tmp_path/'source.zip'; package(archive)
    source = {'source_archive_id': 'bounded-release', 'release_version': '112S3',
        'local_recovered_path': 'source.zip', 'sha256': e.file_sha256(archive),
        'byte_size': archive.stat().st_size, 'official_url': 'https://plvr.land.moi.gov.tw/archive',
        'retrieved_at': CUTOFF}
    config = {'version': 'ml-data-gate-bundle-v1', 'cutoff': CUTOFF, 'observation_at': CUTOFF,
              'sources': [source], 'receipts': []}
    path = tmp_path/'bundle.json'
    path.write_text(json.dumps(config), encoding='utf-8')
    assert reopen().load_bundle(tmp_path) == config
    for changes in ({'sha256': 'f'*64}, {'local_recovered_path': '../source.zip'},
                    {'official_url': 'https://evil.test/source'}, {'byte_size': 1}):
        bad = deepcopy(config); bad['sources'][0].update(changes)
        path.write_text(json.dumps(bad), encoding='utf-8')
        with pytest.raises(ValueError): reopen().load_bundle(tmp_path)


def test_real_cli_cannot_enable_synthetic_receipts():
    import subprocess, sys
    result = subprocess.run([sys.executable, '-m', 'scripts.ml.reopen_data_gate', '--synthetic-test'],
                            capture_output=True, text=True)
    assert result.returncode != 0


def test_dangling_changed_id_correction_blocks_otherwise_sufficient_panel(tmp_path):
    xs, rs, cutoff = full_panel(tmp_path)
    ledger, certs, coverage, diagnostics = e.ingest(xs, rs, tmp_path, synthetic_test=True)
    # An unbound predecessor cannot certify the other families unaffected.
    # Rebind the test certificate after the corruption to exercise closure,
    # rather than merely testing a certificate digest mismatch.
    x = deepcopy(ledger[0])
    x['raw']['編號'] = 'SYNTHETIC-DANGLING-NEW-ID'
    x['physical_row_number'] = 10001
    x.update(supersedes_version_id='f'*64, revision_kind='CORRECTION', revision_evidence=e.reference(rs[-2]))
    ledger.append(x)
    for cert in certs['certificates']:
        visible = [r for r in ledger if l.timestamp(h.publication(r)['available_at']) <= l.timestamp(cert['cutoff'])]
        cert['visible_ledger_sha256'] = h.ledger_digest(visible)
    report, _ = reopen().evaluate(ledger, certs, coverage, diagnostics,
        continuity_valid=True, cutoff=cutoff, deterministic=True)
    assert report['status'] == 'BLOCKED' and not report['ml_b_authorized']
    assert report['admission']['conditions']['minimum_pit_rows']
    assert not report['admission']['conditions']['authoritative_history_closed']


def test_operator_intake_clock_is_explicit_ordered_and_never_publication(tmp_path):
    xs = [item()]
    xs[0].update(ingested_at=None, transformed_at=None)
    config = {'sources': [{'retrieved_at': CUTOFF}], 'receipts': [],
              'observation_at': '2026-10-17T21:00:00+08:00'}
    reopen().apply_intake_clock(xs, config)
    assert xs[0]['ingested_at'] is None
    config['execution_observed_at'] = '2026-10-17T20:00:00+08:00'
    reopen().apply_intake_clock(xs, config)
    assert xs[0]['ingested_at'] == config['execution_observed_at']
    assert xs[0]['source_release_available_at'] == '2024-07-01T00:00:00+08:00'
    config['receipts'] = [{'retrieved_at': '2026-10-17T20:30:00+08:00'}]
    with pytest.raises(ValueError): reopen().apply_intake_clock(xs, config)
    config['receipts'] = []
    config['execution_observed_at'] = '2030-01-01T00:00:00+08:00'
    with pytest.raises(ValueError): reopen().apply_intake_clock(xs, config)


def test_frozen_guard_checks_every_artifact_against_fresh_rebuild(tmp_path, monkeypatch):
    # The real admission path is exercised above. Isolate frozen-file checking
    # here: remove/corrupt an artifact and the guard must revoke authorization.
    guard = importlib.import_module('scripts.ml.check_training_authorization')
    report = reopen().empty_report()
    report.update(status='PASS', ml_b_authorized=True)
    private = {key: [] for key in reopen().FROZEN_FILES}
    monkeypatch.setattr(guard.gate, 'rebuild', lambda *args: (report, private))
    frozen = tmp_path/'frozen'; frozen.mkdir()
    for key, value in reopen().artifacts(report, private).items(): (frozen/key).write_bytes(value)
    assert guard.authorized(frozen, tmp_path/'evidence')
    for key in reopen().FROZEN_FILES:
        original = (frozen/key).read_bytes()
        (frozen/key).write_bytes(b'[]\nCORRUPTION')
        assert not guard.authorized(frozen, tmp_path/'evidence')
        (frozen/key).write_bytes(original)
    (frozen/'test.json').unlink()
    assert not guard.authorized(frozen, tmp_path/'evidence')


def test_double_rebuild_and_dry_run_with_complete_synthetic_authority(tmp_path, monkeypatch):
    xs, rs, cutoff = full_panel(tmp_path)
    for r in rs: r['synthetic'] = False  # test-only simulated reviewed provider input
    config = {'version': 'ml-data-gate-bundle-v1', 'sources': [
        {'source_archive_id': x['release_id'], 'sha256': x['archive_sha256'],
         'retrieved_at': x['source_release_available_at']} for x in xs[::40]],
        'receipts': rs, 'cutoff': cutoff, 'observation_at': '2026-10-17T21:00:00+08:00'}
    # Only the archive/parser boundary is substituted. Existing parser/source
    # integrity tests exercise that boundary independently; receipt, PIT,
    # chronology, thresholds and double-build orchestration execute unchanged.
    monkeypatch.setattr(reopen(), 'load_bundle', lambda root: deepcopy(config))
    calls = []
    def stage(manifest, observed, root):
        calls.append(1)
        return deepcopy(xs), manifest, {}
    monkeypatch.setattr(reopen().staging, 'stage_manifest', stage)
    report, private = reopen().rebuild(tmp_path)
    assert len(calls) == 2 and report['double_build_equal']
    assert report['status'] == 'PASS' and len(private['approved-cohort.json']) == 840
    assert set(reopen().artifacts(report, private)) == set(reopen().FROZEN_FILES) | {
        'decision.json', 'summary.md', 'output-hashes.json'}
    # Reuse the independently verified result to isolate dry-run suppression.
    base = deepcopy(report); base['status'] = 'BLOCKED'; base['ml_b_authorized'] = False
    monkeypatch.setattr(reopen(), 'build_once', lambda root: (deepcopy(base), deepcopy(private), 'a'*64))
    dry, frozen = reopen().rebuild(tmp_path, dry_run=True)
    assert dry['status'] == 'BLOCKED' and dry['dry_run'] and not dry['ml_b_authorized']
    assert frozen['approved-cohort.json'] == [] and dry['counts']['approved_training'] == 0


def test_nondeterministic_builds_never_authorize(tmp_path, monkeypatch):
    results = iter([(reopen().empty_report(), {}, 'a'*64), (reopen().empty_report(), {}, 'b'*64)])
    monkeypatch.setattr(reopen(), 'build_once', lambda root: next(results))
    report, private = reopen().rebuild(tmp_path, dry_run=True)
    assert report['status'] == 'BLOCKED' and report['dry_run']
    assert report['issues'] == ['NONDETERMINISTIC'] and not private
