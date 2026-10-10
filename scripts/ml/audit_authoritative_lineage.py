"""Offline ML-A3 extension of existing verified staging and aggregate contracts."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import json
import sys

from . import audit_authoritative_history as a2, audit_target_reframing as previous
from . import historical as h, lineage as l, observed_transaction as b
from . import semantics as s, source_recovery as r, temporal as t
from .audit_foundation import file_sha256, read_json, repository_text_sha256
from .verify_authoritative_history_builds import check_privacy

STARTING_SHA = '8469c1f22b64a0e03be03a0099c59a8483d9e0c8'
VERSION = 'ml-authoritative-source-lineage-evidence-v1'
CONTRACT = s.ROOT/'docs/ml/contracts/authoritative-source-lineage-v1.json'
NOTES = s.ROOT/'docs/ml/authoritative-source-lineage-source-notes-v1.json'


def build(preflight: dict, downloads: list[dict], destination: Path, cutoff: str, observation_at: str) -> dict:
    if (l.timestamp(cutoff) is None or l.timestamp(observation_at) is None
            or l.timestamp(cutoff) > l.timestamp(observation_at)):
        raise ValueError('explicit_ordered_timezone_instants_required')
    out = r.ignored_destination(destination)
    if out.exists():
        raise ValueError('clean_build_destination_required')
    notes = read_json(NOTES, limit=1024*1024)
    contract = read_json(CONTRACT)
    # This lane acquires metadata only. No external target/rights supplement
    # enters staging and no history/namespace certificate is manufactured.
    items, manifest, source = previous.stage_sources(preflight, downloads, observation_at)
    for x in items:
        x['required_source_dependencies'] = []
    gate = h.data_gate(items, cutoff, history_certificate=None, coverage_evidence=None, pit_v3=True)
    candidates = [x for x in items if b.classify(x, cutoff)['target_valid']]
    if any(not h.parking_treatment(x)['target_b_allowed'] for x in candidates):
        raise ValueError('STOP_CANDIDATE_PARKING_CONTRADICTION')
    historic = [x for x in candidates if t.available_by(h.publication(x), cutoff)]
    selection = h.select_pit_v3(items, cutoff, history_certificate=None)
    pit = selection['selected']
    counts = {**gate['counts'], 'official_main': len(items),
              'historical_publication_valid': len(historic)}
    gate['counts'] = counts
    waterfall = [{'stage': 'official_main', 'input_count': len(items),
                  'accepted_count': len(items), 'excluded_count': 0, 'reason_counts': {}}]
    waterfall.extend({**step, 'stage': 'historical_publication_valid'
                      if step['stage'] == 'historically_supported' else step['stage']}
                     for step in gate['waterfall'])
    gate['waterfall'] = waterfall
    inventory = list(notes['sources'])
    for entry in manifest['sources']:
        restored = entry['checksum_status'] == 'EXACT_MATCH' and entry['package_valid']
        inventory.append({'source_id': entry['source_archive_id'], 'source_type': 'OFFICIAL_ARCHIVE',
            'publication_period': entry['release_version'], 'publication_timestamp': None,
            'retrieval_timestamp': entry['retrieved_at'] if restored else None,
            'official_url': entry['official_url'], 'hash': entry['sha256'] if restored else None,
            'expected_hash': entry['expected_sha256'], 'verified_bytes': entry['byte_size'] if restored else None,
            'proof_class': 'CURRENT_ONLY' if restored else 'UNVERIFIED',
            'exact_byte_publication_binding': False,
            'proof_basis': 'Exact stored bytes reverified; original historical publication unproven.' if restored
                           else 'Inherited checksum/release metadata; no bytes recovered in this worktree.',
            'limitations': ['Period label and current checksum are not a historical publication binding.'],
            'local_bytes_status': 'AVAILABLE_EXACT' if restored else 'UNAVAILABLE'})
    profiles = {label: previous.coverage(xs) for label, xs in
                [('candidates', candidates), ('historical_proof', historic), ('PIT_valid', pit)]}
    month_profiles = {label: h.month_profile(profile.get('month', {})) for label, profile in profiles.items()}
    parking = {label: dict(sorted(Counter(h.parking_treatment(x)['category'] for x in xs).items()))
               for label, xs in [('raw', items), ('candidates', candidates)]}
    admission = h.ml_b_admission(approved_cohort=counts['approved_training'],
        historical_publication=bool(candidates) and len(historic) == len(candidates),
        lineage=bool(candidates) and counts['lineage_valid'] == len(candidates),
        stable_namespace=bool(candidates) and counts['namespace_valid'] == len(candidates),
        no_known_temporal_leakage=selection['history_certificate_valid'],
        chronological_coverage=gate['chronology']['viable'], deterministic_rebuild=False,
        privacy=True, target_contract_frozen=True)
    configuration = {'prediction_cutoff': cutoff, 'logical_observation_at': observation_at,
        'timezone': 'Asia/Taipei', 'releases': ['112S3', '115S2'], 'main_members': list(previous.MEMBERS),
        'max_main_observations': 100000, 'archive_network_downloads': 0,
        'chronology_thresholds': contract['minimum_chronology']}
    report = {'schema_version': VERSION, 'starting_sha': STARTING_SHA,
        'branch': 'research/ml-authoritative-source-lineage-v1', 'configuration': configuration,
        'source_inventory': inventory, 'proof_class_summary': dict(sorted(Counter(x['proof_class'] for x in inventory).items())),
        'source_bindings': source['source_bindings'], 'detail_joins': source['joins'],
        'raw_detail_observations': source['raw_detail_count'], 'acquisition': notes,
        'historical_publication_proofs_recovered': 0,
        'namespace': h.namespace_analysis(items), 'candidate_namespace': h.namespace_analysis(candidates),
        'lineage': {'revision_verdict': 'UNPROVEN', 'cancellation_verdict': 'UNPROVEN',
            'replacement_verdict': 'UNPROVEN', 'authoritative_revision_edges': 0,
            'authoritative_cancellation_events': 0, 'authoritative_replacement_edges': 0,
            'complete_history_certificates': 0, 'unknown_lineage_candidates': len(candidates),
            'event_class_counts': {'UNKNOWN': len(items)},
            'first_observed_physical_occurrences': len(items), 'first_public_versions_proven': 0,
            'missing_rows_are_cancellations': False},
        'target_a': {'verdict': gate['target_a'], 'complete_rights_recovered': 0,
            'registered_single_dwelling_recovered': 0,
            'multiple_building_portion_candidates': sum(len(x['details']['build']) > 1 for x in candidates),
            'single_building_portion_candidates': sum(len(x['details']['build']) == 1 for x in candidates),
            'existing_gates_changed': False,
            'authoritative_resolution': 'None: parcel reference/georeference/manual proposed relations lack registered object/unit/rights linkage.'},
        'target_b': {'target_name': 'Observed Residential Transaction Unit Price', 'verdict': gate['target_b'],
            'target_contract_version': b.TARGET_VERSION,
            'candidate_distribution': a2.distributions(candidates, cutoff)},
        'parking': {'profiles': parking, 'deductions_performed': 0,
            'candidate_verdict': 'CONFIRMED_NO_PARKING_SUBSET_ONLY', 'contradictions': 0},
        'coverage_profiles': profiles, 'month_profiles': month_profiles,
        'per_month_waterfall': [{'month': month, 'candidate_rows': count,
            'historical_publication_valid': profiles['historical_proof'].get('month', {}).get(month, 0),
            'PIT_valid': profiles['PIT_valid'].get('month', {}).get(month, 0),
            'sparse_candidate_month': count < 20, 'sparse_PIT_month': profiles['PIT_valid'].get('month', {}).get(month, 0) < 20}
            for month, count in sorted(profiles['candidates'].get('month', {}).items())],
        'chronological_feasibility': {'result': 'PASS' if gate['chronology']['viable'] else 'BLOCKED',
            'minimums': contract['minimum_chronology'], 'blockers': gate['chronology']['blockers'],
            'folds': gate['chronology']['blocks'], 'thresholds_tuned_to_counts': False},
        'data_gate': gate, 'counts': counts, 'ml_b_admission': admission,
        'rebuild_admission_policy': 'deterministic_rebuild remains false here until external five-file comparison; final validation records the verified conjunction.',
        'owner_actions': notes['owner_actions'], 'privacy': {'status': 'PASS',
            'row_level_outputs_created': 0, 'policy': 'Allow only bounded aggregate research outputs.'},
        'constraints': {'models_trained': 0, 'production_valuation_changed': False,
            'ML_UI_created': False, 'deployed': False, 'pushed': False, 'merged': False},
        'future_ml_b_handoff_prepared': False, 'ml_b_may_begin': admission['may_begin']}
    provenance = {'schema_version': VERSION+'-manifest', 'code_git_base_sha': STARTING_SHA,
        'code_sha256': l.digest({f.name: repository_text_sha256(f) for f in sorted((s.ROOT/'scripts/ml').glob('*.py'))}),
        'configuration': configuration, 'configuration_sha256': l.digest(configuration),
        'data_gate_version': gate['version'], 'target_contract_version': b.TARGET_VERSION,
        'input_sha256': {'preflight': l.digest(preflight), 'downloads': l.digest(downloads),
            'release_ledger': file_sha256(r.LEDGER), 'lane_contract': file_sha256(CONTRACT),
            'inherited_history_contract': file_sha256(a2.CONTRACT), 'source_notes': file_sha256(NOTES),
            'target_b_contract': file_sha256(previous.CONTRACT_PATH),
            'target_a_contract': file_sha256(s.ROOT/'docs/ml/contracts/semantic-temporal-closure-v1.json'),
            'geography_registry': file_sha256(s.REGISTRY)},
        'source_bindings': source['source_bindings'], 'python_version': sys.version.split()[0],
        'normalization': 'Frozen source observations; LF code digest; no output path, filesystem clock or build-time timestamp. Final Git SHA delivered outside its own content.'}
    artifacts = {'evidence.json': report, 'data-gate.json': gate, 'source-inventory.json': inventory,
                 'build-manifest.json': provenance}
    for value in artifacts.values():
        check_privacy(value)
    out.mkdir(parents=True)
    for name, value in artifacts.items():
        (out/name).write_bytes(l.canonical_bytes(value)+b'\n')
    hashes = {name: file_sha256(out/name) for name in sorted(artifacts)}
    (out/'output-hashes.json').write_bytes(l.canonical_bytes(hashes)+b'\n')
    return {'counts': counts, 'ml_b_admission': admission['result'], 'output_hashes': hashes}


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
        parser.exit(2, 'authoritative_lineage_build_failed: bounded input/proof/privacy/parking contract\n')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
