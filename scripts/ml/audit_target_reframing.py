"""Offline exact-source Target A/B audit; stdout contains bounded aggregates only.

All occurrence rows, official identifiers and detail cells stay in create-only
ignored storage. This command never grants training or production approval.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
import zipfile

from . import audit_source_recovery as a, chronology, contracts as c, lineage as l
from . import observed_transaction as b, plvr_raw_parser as p, rights_dwelling as d
from . import semantics as s, source_recovery as r, strict_cohort, temporal as t
from .audit_foundation import file_sha256, read_json, repository_text_sha256
from .audit_semantic_temporal_closure import staging_clocks, write_jsonl

VERSION = 'ml-target-reframing-evidence-v1'
MEMBERS = ('a_lvr_land_a.csv', 'f_lvr_land_a.csv')
CONTRACT_PATH = s.ROOT/'docs/ml/contracts/observed-transaction-target-v1.json'


def stage_sources(preflight: dict, downloads: list[dict], observation_at: str) -> tuple[list, dict, dict]:
    """Reuse verified recovery, strict raw parser and existing evidence classifiers."""
    manifest = r.build_manifest(preflight, downloads)
    recovered = [x for x in manifest['sources'] if x['checksum_status'] == 'EXACT_MATCH' and x['package_valid']]
    if {x['release_version'] for x in recovered} != {'112S3', '115S2'} or len(recovered) != 2:
        raise ValueError('exact_bounded_two_release_scope_required')
    acquisition_hash = l.digest(manifest)
    items, bindings, joins, bounds = [], [], [], []
    detail_count = 0
    for source in recovered:
        evidence = t.retrieval_evidence(source, manifest_sha256=acquisition_hash)
        resolved = t.resolve_availability(evidence, source['source_archive_id'], source['sha256'])
        bounds.append({'release_id': source['source_archive_id'], 'archive_sha256': source['sha256'],
                       **resolved, 'historical_publication_proven': False})
        with zipfile.ZipFile(s.ROOT/source['local_recovered_path']) as archive:
            tables = a._load_members(archive, source, MEMBERS)
        for member, family in sorted(tables.items()):
            mains = family['main']['records']
            keys = Counter(s.text(x['raw'].get('編號')) for x in mains)
            indices = {}; complete = True
            for kind in ('build', 'land', 'park'):
                index, valid = p.detail_index(family[kind]['records'])
                orphan = sum(len(v) for k, v in index.items() if k not in keys)
                complete &= valid and orphan == 0
                indices[kind] = index
                count = len(family[kind]['records']); detail_count += count
                joins.append({'release_id': source['source_archive_id'], 'member': member, 'kind': kind,
                              'main_count': len(mains), 'detail_count': count, 'orphan_count': orphan,
                              'complete_parse': valid, 'ambiguous_main_keys': sum(v > 1 for v in keys.values())})
            bindings.append({'release_id': source['source_archive_id'], 'archive_sha256': source['sha256'],
                             'member': member, 'main_sha256': family['main']['sha256'],
                             'detail_sha256': {k: family[k]['sha256'] for k in indices},
                             'schema_sha256': a.SCHEMA_HASHES})
            for record in mains:
                raw = record['raw']; key = s.text(raw.get('編號'))
                unique = bool(key) and keys[key] == 1
                details = {k: [x['raw'] for x in index.get(key, [])] for k, index in indices.items()}
                context = p.unproven_context(member, a.SCHEMA_HASHES['schema-main.csv'],
                                             family['park']['sha256'] if complete and unique else None,
                                             len(details['park']) if complete and unique else None)
                context.update(area_basis=s.AREA_VERSION,
                               area_evidence={'sha256': a.SCHEMA_HASHES['schema-main.csv'],
                                              'locator': 'schema-main.csv#建物移轉總面積平方公尺', 'version': VERSION})
                semantic = d.classify(raw, details['build'], details['land'], complete=complete, unique=unique,
                                      scope={'archive_sha256': source['sha256'], 'member_name': member,
                                             'physical_row_number': record['record_number'],
                                             'schema_sha256': a.SCHEMA_HASHES['schema-main.csv']})
                semantic['parking'] = p.parking_state(raw, details['park'], details['build'], complete, unique, context=context)
                items.append({'raw': raw, 'context': context, 'details': details,
                              'details_complete': complete, 'main_key_unique': unique, 'semantic': semantic,
                              'source_dataset_id': c.SOURCE_ID, 'release_id': source['source_archive_id'],
                              'archive_sha256': source['sha256'], 'member_name': member,
                              'member_sha256': family['main']['sha256'], 'physical_row_number': record['record_number'],
                              'physical_start_line': record['start_line'], 'physical_end_line': record['end_line'],
                              'parse_error': record['parse_error'], 'source_release_available_at': resolved['available_at'],
                              'availability_evidence': evidence.get('evidence'), 'availability_quality': resolved['quality'],
                              'release_published_at': None, **staging_clocks(observation_at),
                              'import_batch_id': 'offline-target-reframing-v1', 'parser_version': s.PARSER_VERSION,
                              'transform_version': s.TRANSFORM_VERSION, 'target_b_transform_version': b.VERSION,
                              'identity_evidence': None, 'supersedes_version_id': None,
                              'cancelled': False, 'cancellation_state_evidenced': False,
                              'area_contract': {'field': '建物移轉總面積平方公尺', 'unit': 'm²'},
                              'detail_payload_sha256': {k: l.digest(v) for k, v in details.items()},
                              'detail_member_sha256': {k: family[k]['sha256'] for k in indices}})
    # Member/schema onboarding enriches the manifest in place. Bind every
    # retrieval reference to the final persisted object, never a discarded
    # intermediate hash that a future auditor cannot reconstruct.
    final_manifest_hash = l.digest(manifest)
    for item in items:
        if item['availability_evidence'] is not None:
            item['availability_evidence'] = {**item['availability_evidence'], 'sha256': final_manifest_hash}
    return items, manifest, {'source_bindings': bindings, 'joins': joins, 'raw_detail_count': detail_count,
                             'availability_bounds': bounds}


def coverage(rows: list[dict]) -> dict:
    """Bounded marginal histograms only; no transaction IDs/addresses/row records."""
    profiles = defaultdict(Counter)
    for row in rows:
        raw = row['raw']
        geo = s.normalize_geography(raw.get('縣市', ''), raw.get('鄉鎮市區', ''), row['member_name'])
        effective = s.parse_roc_date(raw.get('交易年月日'))
        profiles['county'][geo['city'] or 'UNKNOWN'] += 1
        profiles['district'][geo['city']+'/'+geo['district'] if geo['source_proven'] else 'INVALID'] += 1
        profiles['month'][effective['value'][:7] if effective else 'INVALID'] += 1
        profiles['building_type'][s.TYPES.get(s.text(raw.get('建物型態')), 'UNSUPPORTED')] += 1
        profiles['release'][row['release_id']] += 1
    return {k: dict(sorted(v.items())) for k, v in sorted(profiles.items())}


def build(preflight: dict, downloads: list[dict], destination: Path, cutoff: str, observation_at: str) -> dict:
    if l.timestamp(cutoff) is None or l.timestamp(observation_at) is None:
        raise ValueError('explicit_timezone_instants_required')
    if l.timestamp(cutoff) > l.timestamp(observation_at):
        raise ValueError('cutoff_after_observation')
    out = r.ignored_destination(destination)
    if out.exists():
        raise ValueError('clean_build_destination_required')
    items, manifest, source = stage_sources(preflight, downloads, observation_at)
    result = b.build_candidates(items, cutoff)
    target_a = strict_cohort.build_cohort(items, cutoff)
    splits = chronology.design_splits(chronology.split_rows_from_items(result['selected_rows']),
                                     coverage_evidence=None, ledger_items=items,
                                     label_observation_cutoff=cutoff, cohort_selector=b.build_candidates)
    candidates = [x for x, ledger in zip(sorted(items, key=lambda x: l.canonical_bytes(l.identify(x))), result['ledger'])
                  if ledger['target_valid']]
    family_counts = Counter(l.identify(x)['transaction_family_id'] for x in items)
    profiles = {label: dict(sorted(Counter(x.get('semantic', {}).get(label, 'UNKNOWN') for x in items).items()))
                for label in ('rights', 'dwelling', 'parking')}
    out.mkdir(parents=True)
    outputs = {'occurrences.jsonl': items, 'eligibility-ledger.jsonl': result['ledger'],
               'candidate-membership.jsonl': [{k: v for k, v in x.items() if k not in {'target', 'features'}} for x in result['candidates']],
               'candidate-targets.jsonl': [{**l.identify(x), 'target': b.classify(x, cutoff)['target']} for x in candidates],
               'candidate-features.jsonl': [{**l.identify(x), 'values': b.feature_values(x, b.classify(x, cutoff)['target'])} for x in candidates],
               'candidate-exclusions.jsonl': result['candidate_exclusions'],
               'revision-dispositions.jsonl': result['revision_dispositions'], 'revision-edges.jsonl': result['relations'],
               'pit-membership.jsonl': [l.identify(x) for x in result['selected_rows']],
               'splits.jsonl': splits['assignments'], 'approved-membership.jsonl': []}
    hashes = {name: write_jsonl(out/name, values) for name, values in outputs.items()}
    counts = {**result['counts'], 'raw_detail_observations': source['raw_detail_count'],
              'chronologically_evaluable_observations': len(splits['assignments']), 'approved_training_cohort': 0}
    dataset_manifest = {'schema_version': VERSION+'-build-manifest', 'source_manifest_sha256': l.digest(manifest),
                        'source_bindings': source['source_bindings'], 'hashes': dict(hashes), 'counts': counts,
                        'feature_columns': list(b.FEATURE_COLUMNS), 'target_version': b.TARGET_VERSION,
                        'area_version': b.AREA_VERSION, 'cutoff': cutoff, 'logical_observation_at': observation_at,
                        'python_version': sys.version.split()[0], 'timezone': 'Asia/Taipei',
                        'code_sha256': l.digest({f.name: repository_text_sha256(f) for f in sorted((s.ROOT/'scripts/ml').glob('*.py'))}),
                        'target_b_contract_sha256': l.digest(read_json(CONTRACT_PATH)),
                        'target_a_contract_sha256': l.digest(read_json(s.ROOT/'docs/ml/contracts/semantic-temporal-closure-v1.json')),
                        'source_contract_sha256': l.digest(read_json(s.ROOT/'docs/ml/contracts/source-contract-v1.json')),
                        'registry_sha256': l.digest(read_json(s.REGISTRY)),
                        'readiness_approval': False, 'production_valuation_approval': False}
    for name, value in [('source-manifest.json', manifest), ('dataset-manifest.json', dataset_manifest)]:
        (out/name).write_bytes(l.canonical_bytes(value)+b'\n')
        hashes[name] = file_sha256(out/name)
    raw_coverage, candidate_coverage = coverage(items), coverage(candidates)
    candidate_months = candidate_coverage.get('month', {})
    current_available = sum(t.available_by({'available_at': x.get('source_release_available_at')}, cutoff) for x in candidates)
    report = {'schema_version': VERSION+'-aggregate',
              'starting_sha': '95018f6fc2a366656cb798414dc54860d009e536',
              'branch': 'research/ml-target-reframing-evidence-v1', 'target_a_status': 'BLOCKED',
              'target_b_status': 'BLOCKED', 'ml_b_may_begin': False, 'counts': counts,
              'target_a': {'approved_count': len(target_a['membership']), 'funnel': target_a['funnel'], 'gates_changed': False},
              'scope': {'releases': ['112S3', '115S2'], 'members': list(MEMBERS),
                        'archive_downloads_this_wave': 0, 'acquisition': 'Local restore of prior exact bytes; prior HTTP observations preserved.'},
              'recovered_archives': [{k: x[k] for k in ('source_archive_id', 'release_version', 'sha256', 'byte_size', 'official_url', 'retrieved_at')}
                                    for x in manifest['sources'] if x['checksum_status'] == 'EXACT_MATCH'],
              'source_bindings': source['source_bindings'], 'joins': source['joins'],
              'target_b_funnel': result['funnel'], 'raw_coverage': raw_coverage,
              'candidate_coverage': candidate_coverage, 'pit_coverage': coverage(result['selected_rows']),
              'candidate_first_exclusion_counts': dict(sorted(Counter(x['first_reason'] for x in result['candidate_exclusions']).items())),
              'candidate_all_exclusion_counts': dict(sorted(Counter(reason for x in result['candidate_exclusions'] for reason in x['all_reasons']).items())),
              'semantic_profiles': profiles,
              'candidate_detail_composition': dict(sorted(Counter(x['detail_composition'] for x in result['candidates']).items())),
              'candidate_rights_status': 'UNVERIFIED_COMPLETE_DWELLING_RIGHTS',
              'candidate_dwelling_status': 'UNVERIFIED_REGISTERED_UNIT_COUNT',
              'candidate_reported_transfer_labels': dict(sorted(Counter(s.text(part.get('移轉情形')) or 'BLANK'
                                                                      for x in candidates for part in x['details']['build']).items())),
              'identity': {'provisional_family_count': len(family_counts),
                           'repeated_provisional_family_count': sum(v > 1 for v in family_counts.values()),
                           'repeated_family_excess': sum(v-1 for v in family_counts.values()),
                           'namespace_attested_count': 0, 'cancellation_history_attested_count': 0,
                           'revision_edge_count': len(result['relations']),
                           'candidate_pit_exclusion_counts': dict(sorted(Counter(x['pit_reason'] for x in result['ledger'] if x['target_valid'] and x['pit_reason']).items()))},
              'availability': {'bounds': source['availability_bounds'], 'historical_publication_proven_releases': 0,
                               'candidates_public_by_current_cutoff_only': current_available,
                               'historical_evaluation_availability_proven_count': 0},
              'viability': {'split_design': splits, 'maximum_candidate_month_share':
                            str(max(candidate_months.values())/len(candidates)) if candidates else None,
                            'nonzero_research_candidates': bool(candidates), 'complete_mature_panel_proven': False},
              'baseline_readiness': {'global_median': False, 'district_building_type_median': False,
                                     'historical_comparable_estimator': False, 'contracts_prepared': True,
                                     'frozen_asof_history_implemented': True},
              'hashes': hashes, 'candidate_outputs_nonempty': bool(candidates), 'training_outputs_nonempty': False,
              'blockers': ['TARGET_A_COMPLETE_RIGHTS_AND_REGISTERED_SINGLE_DWELLING_UNPROVEN',
                           'STABLE_CROSS_RELEASE_NAMESPACE_AND_COMPLETE_REVISION_CANCELLATION_HISTORY_UNPROVEN',
                           'EXACT_BYTE_HISTORICAL_AVAILABILITY_AT_FOLD_FREEZES_UNPROVEN',
                           'COMPLETE_MATURE_CONTIGUOUS_PANEL_AND_NONEMPTY_FOUR_BLOCKS_UNPROVEN'],
              'recommendation': 'Retain Target B candidates for offline source research only. No ML-B training or product valuation change.'}
    (out/'evidence.json').write_bytes(l.canonical_bytes(report)+b'\n')
    return report


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
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        parser.exit(2, 'target_reframing_build_failed: invalid or unavailable bounded inputs\n')


if __name__ == '__main__':
    main()
