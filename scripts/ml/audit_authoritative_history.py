"""Create-only, offline ML-A2 aggregate evidence; no model/database operations."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sys

from . import audit_target_reframing as previous, historical as h, lineage as l
from . import observed_transaction as b, semantics as s, source_recovery as r
from .audit_foundation import file_sha256, read_json, repository_text_sha256

VERSION = 'ml-authoritative-history-evidence-v1'
STARTING_SHA = 'b4eb441a8ccf90965102f0646006dc4b0e145491'
INTEGRATION_BASELINE = '602830c8d4d405bb401afa902d5bf69f2c61066f'
CONTRACT = s.ROOT/'docs/ml/contracts/authoritative-history-v1.json'
NOTES = s.ROOT/'docs/ml/authoritative-history-source-notes-v1.json'


def distributions(items: list[dict], cutoff: str) -> dict:
    values = Counter()
    boundaries = [Decimal(x) for x in ('10000', '200000', '400000', '600000', '800000', '1000000', '2000000', '5000000')]
    for x in items:
        target = b.classify(x, cutoff)['target']
        if target is None:
            continue
        price = Decimal(target['unit_price_ntd_ping'])
        for i, (low, high) in enumerate(zip(boundaries, boundaries[1:])):
            if low <= price < high or (i == len(boundaries)-2 and price == high):
                values[f'{low}-{high}'+(' inclusive_upper' if i == len(boundaries)-2 else ' exclusive_upper')] += 1
                break
    return {'unit': 'NTD/ping', 'fixed_bin_counts': dict(sorted(values.items())),
            'policy': 'Fixed aggregate bins; no individual values, fitted quantiles or model metrics.'}


def build(preflight: dict, downloads: list[dict], destination: Path, cutoff: str, observation_at: str) -> dict:
    if l.timestamp(cutoff) is None or l.timestamp(observation_at) is None:
        raise ValueError('explicit_timezone_instants_required')
    if l.timestamp(cutoff) > l.timestamp(observation_at):
        raise ValueError('cutoff_after_observation')
    out = r.ignored_destination(destination)
    if out.exists():
        raise ValueError('clean_build_destination_required')
    items, manifest, source = previous.stage_sources(preflight, downloads, observation_at)
    # Captures prove current bytes only; no publication_evidence/history
    # certificate is invented from release labels or local/repository clocks.
    gate = h.data_gate(items, cutoff, history_certificate=None, coverage_evidence=None)
    candidates = [x for x in items if b.classify(x, cutoff)['target_valid']]
    counts = gate['counts']
    source_inventory = []
    for entry in manifest['sources']:
        restored = entry['checksum_status'] == 'EXACT_MATCH' and entry['package_valid']
        source_inventory.append({
            'release_id': entry['source_archive_id'], 'release_version': entry['release_version'],
            'official_url': entry['official_url'], 'expected_sha256': entry['expected_sha256'],
            'verified_sha256': entry['sha256'] if restored else None,
            'verified_bytes': entry['byte_size'] if restored else None,
            'classification': 'CURRENT_ONLY' if restored else 'UNVERIFIED',
            'local_bytes_status': 'AVAILABLE_EXACT' if restored else 'UNAVAILABLE',
            'retrieval_upper_bound': entry['retrieved_at'] if restored else None,
            'historical_publication_at': None,
            'reason': 'EXACT_BYTES_AT_LATE_VERIFIED_CAPTURE_ONLY' if restored else 'INHERITED_METADATA_WITHOUT_RESTORED_BYTES',
        })
    parking = {label: dict(sorted(Counter(h.parking_treatment(x)['category'] for x in xs).items()))
               for label, xs in [('raw', items), ('candidates', candidates)]}
    coverage = previous.coverage(candidates)
    report = {
        'schema_version': VERSION, 'starting_sha': STARTING_SHA,
        'original_implementation_baseline': STARTING_SHA,
        'integration_baseline': INTEGRATION_BASELINE,
        'branch': 'research/ml-authoritative-history-evidence-v1',
        'configuration': {'prediction_cutoff': cutoff, 'logical_observation_at': observation_at,
                          'timezone': 'Asia/Taipei', 'releases': ['112S3', '115S2'],
                          'main_members': list(previous.MEMBERS), 'max_main_observations': 100000,
                          'archive_network_downloads': 0},
        'source_inventory': source_inventory, 'source_bindings': source['source_bindings'],
        'detail_joins': source['joins'], 'raw_detail_observations': source['raw_detail_count'],
        'historical_publication_evidence_recovered': 0,
        'evidence_class_definitions': {
            'AUTHENTICATED': 'Independent exact-byte historical publication/version proof.',
            'SUPPORTED': 'Independently justified conservative historical exact-byte upper bound.',
            'CURRENT_ONLY': 'Exact bytes or explanatory content available only at current capture.',
            'UNVERIFIED': 'Historical claim or metadata without sufficient recoverable proof.',
            'UNAVAILABLE': 'No evidence/bytes available in the bounded inventory; not a claim about all external sources.'},
        'namespace': h.namespace_analysis(items), 'candidate_namespace': h.namespace_analysis(candidates),
        'lineage': {'verdict': 'COMPLETE_HISTORY_UNPROVEN', 'first_observed_versions': len(items),
                    'first_observed_meaning': 'Physical occurrences in restored captures; not first public transaction versions.',
                    'authoritative_revision_edges': 0, 'authoritative_cancellation_events': 0,
                    'authoritative_replacement_edges': 0, 'complete_history_certificates': 0,
                    'unknown_lineage_candidates': len(candidates),
                    'absence_is_cancellation': False},
        'parking': {'profiles': parking, 'deductions_performed': 0,
                    'separable_meaning': 'Positive separately reported price/area and compatible joined count; not independently certified dwelling allocation.',
                    'candidate_verdict': 'CONFIRMED_NO_PARKING_SUBSET_ONLY'},
        'target_a': {'verdict': gate['target_a'], 'complete_rights_recovered': 0,
                     'registered_single_dwelling_recovered': 0,
                     'multiple_building_portion_candidates': sum(len(x['details']['build']) > 1 for x in candidates),
                     'single_building_portion_candidates': sum(len(x['details']['build']) == 1 for x in candidates),
                     'existing_gates_changed': False,
                     'finding': 'Build schema has reported transferred portions, not registered unit count, numeric building rights or authoritative object roles. Land fractions and reported count one do not fill these gaps.'},
        'target_b': {'verdict': gate['target_b'], 'target_contract_version': b.TARGET_VERSION,
                     'candidate_distribution': distributions(candidates, cutoff),
                     'rights_status': 'UNVERIFIED_COMPLETE_DWELLING_RIGHTS',
                     'registered_unit_status': 'UNVERIFIED_REGISTERED_UNIT_COUNT'},
        'candidate_coverage': coverage, 'candidate_chronology': h.month_profile(coverage.get('month', {})),
        'pit_chronology': h.month_profile({}), 'approved_chronology': h.month_profile({}),
        'per_month_waterfall': [{'month': month, 'candidate_rows': count, 'PIT_valid': 0, 'approved_training': 0}
                               for month, count in sorted(coverage.get('month', {}).items())],
        'data_gate': gate, 'counts': counts,
        'ml_b_may_begin': gate['ml_b_may_begin'],
        'remaining_blockers': ['EXACT_BYTE_HISTORICAL_PUBLICATION_UNPROVEN',
                               'STABLE_CROSS_RELEASE_NAMESPACE_UNPROVEN',
                               'COMPLETE_REVISION_CANCELLATION_REPLACEMENT_HISTORY_UNPROVEN',
                               'AUTHORITATIVE_CONTIGUOUS_MATURE_FROZEN_FOLDS_UNPROVEN',
                               'TARGET_A_COMPLETE_RIGHTS_REGISTERED_UNIT_OBJECT_ROLES_UNPROVEN'],
        'privacy': {'output_policy': 'Bounded aggregate evidence only; no raw rows, official serials, addresses, notes or individual target values.',
                    'row_level_outputs_created': 0},
        'baseline': {'new_contracts_prepared': False, 'models_trained': 0, 'headline_metrics_computed': False},
    }
    provenance = {
        'schema_version': VERSION+'-manifest', 'starting_sha': STARTING_SHA,
        'original_implementation_baseline': STARTING_SHA,
        'integration_baseline': INTEGRATION_BASELINE,
        'code_sha256': l.digest({f.name: repository_text_sha256(f) for f in sorted((s.ROOT/'scripts/ml').glob('*.py'))}),
        'configuration': report['configuration'], 'data_gate_version': h.GATE_VERSION,
        'target_contract_version': b.TARGET_VERSION,
        'input_sha256': {'preflight': l.digest(preflight), 'downloads': l.digest(downloads),
                         'release_ledger': file_sha256(r.LEDGER), 'history_contract': file_sha256(CONTRACT),
                         'target_b_contract': file_sha256(previous.CONTRACT_PATH), 'source_notes': file_sha256(NOTES),
                         'target_a_contract': file_sha256(s.ROOT/'docs/ml/contracts/semantic-temporal-closure-v1.json'),
                         'registry': file_sha256(s.REGISTRY)},
        'source_bindings': source['source_bindings'], 'python_version': sys.version.split()[0],
        'normalization': 'Repository code text normalized LF; no absolute paths or filesystem/Git timestamps in artifact content.',
    }
    out.mkdir(parents=True)
    artifacts = {'evidence.json': report, 'data-gate.json': gate, 'source-inventory.json': source_inventory,
                 'build-manifest.json': provenance}
    for name, value in artifacts.items():
        (out/name).write_bytes(l.canonical_bytes(value)+b'\n')
    hashes = {name: file_sha256(out/name) for name in sorted(artifacts)}
    (out/'output-hashes.json').write_bytes(l.canonical_bytes(hashes)+b'\n')
    return {'counts': counts, 'target_a': gate['target_a'], 'target_b': gate['target_b'], 'output_hashes': hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', type=Path, default=r.ARTIFACT_ROOT/'preflight.json')
    parser.add_argument('--downloads', type=Path, default=r.ARTIFACT_ROOT/'downloads.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cutoff', required=True)
    parser.add_argument('--observation-at', required=True)
    args = parser.parse_args()
    try:
        result = build(read_json(args.preflight), read_json(args.downloads), args.output, args.cutoff, args.observation_at)
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(2, 'authoritative_history_build_failed: invalid or unavailable bounded inputs\n')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
