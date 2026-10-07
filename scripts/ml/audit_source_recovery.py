"""Build bounded private raw staging and aggregate evidence from exact PLVR inputs.

This is an offline proof build, not a training dataset builder. Unknown rights,
dwelling, namespace, revision order and historical availability remain unknown.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from . import contracts as c
from . import lineage as l
from . import semantics as s
from .audit_foundation import file_sha256, read_json, repository_text_sha256, audit_staging
from . import plvr_raw_parser as p
from . import source_recovery as r

SCHEMA_HASHES = {
    'schema-main.csv':'6103a05ac97f9b308d346d6a8b038d022ff5fbbfbbd090dccded77e03377d12a',
    'schema-build.csv':'2d77ea26d2470eb8db72791e62c0720c459a4b866ac5649edbafd686328cd116',
    'schema-land.csv':'77e2a663340c7ecefd280dad742c634871b6664b1761accedeb9dbd23fd31158',
    'schema-park.csv':'97eb5f6523255a9c8049b905368c02e2c53380b4ee1d2d8bea8cbae9e37b745e',
}
STAGES = ('schema','identity','geography','target','use','type','rights','dwelling',
          'parking','price_area','revision','pit')


def semantic_funnel(evaluations: list[dict]) -> tuple[list[dict], list[str | None]]:
    """Sequential first-reason partition; parallel diagnostics are not subtracted."""
    active = list(range(len(evaluations)))
    first = [None] * len(active)
    funnel = []
    for stage in STAGES:
        reasons = Counter()
        remaining = []
        for i in active:
            reason = evaluations[i].get(stage)
            if reason:
                reasons[reason] += 1
                first[i] = reason
            else:
                remaining.append(i)
        funnel.append({'stage':stage, 'input_count':len(active), 'accepted_count':len(remaining),
                       'excluded_count':sum(reasons.values()), 'reason_breakdown':dict(sorted(reasons.items()))})
        active = remaining
    assert len(evaluations) == len(active) + sum(x['excluded_count'] for x in funnel)
    return funnel, first


def _schema_header(archive, name):
    data = archive.read(name)
    if hashlib.sha256(data).hexdigest() != SCHEMA_HASHES[name]:
        raise ValueError('unreviewed_schema_identity')
    table = p.parse_csv(data, ['name','title'])
    if any(x['parse_error'] for x in table['records']):
        raise ValueError('schema_record_invalid')
    return [x['raw']['name'] for x in table['records']]


def _histogram(values):
    return dict(sorted(Counter(values).items()))


def _load_members(archive, source, members):
    bindings = p.parse_csv(archive.read('manifest.csv'), ['name','schema','description'])
    mapping = {}
    for row in bindings['records']:
        if row['parse_error']:
            raise ValueError('manifest_record_invalid')
        raw = row['raw']
        if raw['name'] in mapping:
            raise ValueError('manifest_duplicate_member')
        mapping[raw['name']] = raw
    tables = {}
    source['schema_identity'] = [{'member_name':name, 'sha256':value} for name,value in sorted(SCHEMA_HASHES.items())]
    source['package_manifest_sha256'] = hashlib.sha256(archive.read('manifest.csv')).hexdigest()
    source['release_time_member_sha256'] = hashlib.sha256(archive.read('build_time.xml')).hexdigest()
    source['release_time_member_interpretation'] = 'registration/contract windows; no publication instant'
    metadata = []
    for main in members:
        family = {}
        county = s.source_county(main)
        for kind in ('main','build','land','park'):
            name = main if kind == 'main' else main.replace('.csv', f'_{kind}.csv')
            schema = f'schema-{kind}.csv'
            binding = mapping.get(name)
            if not binding or binding['schema'] != schema or not binding['description'].startswith(county):
                raise ValueError('member_manifest_county_schema_mismatch')
            if name not in archive.namelist():
                raise ValueError('required_scoped_detail_member_missing')
            english = p.ENGLISH_MAIN if kind == 'main' else p.ENGLISH_DETAILS[kind]
            table = p.parse_csv(archive.read(name), _schema_header(archive, schema), english)
            table['member_name'] = name
            family[kind] = table
            metadata.append({'member_name':name, 'source_county':county, 'sha256':table['sha256'],
                             'schema_member':schema, 'schema_sha256':SCHEMA_HASHES[schema],
                             'raw_transaction_records':len(table['records']),
                             'csv_invalid_records':sum(x['parse_error'] is not None for x in table['records']),
                             'description_records':table['description_record_count'],
                             'blank_csv_records':table['blank_csv_record_count']})
        tables[main] = family
    source['source_county_members'] = metadata
    return tables


def _assess(raw, context, parsed, unique, parking):
    geo = s.normalize_geography(raw.get('縣市',''), raw.get('鄉鎮市區',''), context['member_name'])
    date = s.parse_roc_date(raw.get('交易年月日'))
    target_exact = s.text(raw.get('交易標的')) == '房地(土地+建物)'
    reasons = {'schema':parsed, 'identity':None if s.text(raw.get('編號')) else 'MISSING_OFFICIAL_ID',
               'geography':None if geo['source_proven'] else 'INVALID_GEOGRAPHY',
               'target':None if target_exact else 'INVALID_TARGET',
               'use':None if s.text(raw.get('主要用途')) == '住家用' else 'UNKNOWN_OR_NONRESIDENTIAL_USE',
               'type':None if s.text(raw.get('建物型態')) in s.TYPES else 'UNSUPPORTED_PROPERTY_TYPE',
               'rights':'RIGHTS_UNPROVEN', 'dwelling':'DWELLING_UNPROVEN',
               'parking':None if parking == 'NO_PARKING_CONFIRMED' else parking,
               'price_area':'AREA_RIGHTS_BASIS_UNPROVEN', 'revision':'IDENTITY_NAMESPACE_AND_REVISION_UNPROVEN',
               'pit':'MISSING_AVAILABILITY'}
    if parsed is None and (not date or date['precision'] != 'day'):
        reasons['schema'] = 'TRANSACTION_DAY_REQUIRED'
    if not unique:
        reasons['identity'] = 'AMBIGUOUS_DETAIL_JOIN_KEY'
    return reasons, geo, date


def build(preflight: dict, downloads: list[dict], destination: Path, cutoff: str,
          observation_at: str, members: tuple[str, ...] = ('a_lvr_land_a.csv','f_lvr_land_a.csv')) -> dict:
    if l.timestamp(cutoff) is None or l.timestamp(observation_at) is None:
        raise ValueError('explicit_timezone_instants_required')
    if l.timestamp(cutoff) > l.timestamp(observation_at):
        raise ValueError('cutoff_after_build_observation')
    if not members or len(set(members)) != len(members) or any(s.source_county(n) is None for n in members):
        raise ValueError('explicit_sale_members_required')
    out = r.ignored_destination(destination)
    if out.exists():
        raise ValueError('clean_build_destination_required')
    manifest = r.build_manifest(preflight, downloads)
    out.mkdir(parents=True)
    staging = []
    evaluations = []
    occurrences = []
    geographies = []
    raw_records = []
    profiles = defaultdict(Counter)
    field_coverage = Counter()
    joins = []
    families = defaultdict(list)
    raw_required_fields = read_json(s.ROOT / 'docs/ml/contracts/source-contract-v1.json')['raw_required_fields']
    staging_schema = read_json(s.ROOT / 'docs/ml/contracts/staging-occurrence-v1.schema.json')
    for source in manifest['sources']:
        if source['checksum_status'] != 'EXACT_MATCH' or not source['package_valid']:
            continue
        path = s.ROOT / source['local_recovered_path']
        with zipfile.ZipFile(path) as archive:
            tables = _load_members(archive, source, members)
        for main, family in sorted(tables.items()):
            rows = family['main']['records']
            main_keys = Counter(s.text(x['raw'].get('編號')) for x in rows)
            indices = {}
            complete = True
            for kind in ('build','land','park'):
                index, valid = p.detail_index(family[kind]['records'])
                indices[kind] = index
                complete = complete and valid
                multiplicity = Counter(len(index.get(key, [])) for key in main_keys if key)
                joins.append({'release_id':source['source_archive_id'], 'main_member':main, 'detail_kind':kind,
                              'join_key':'archive SHA256 + sale county member + 編號',
                              'main_rows':len(rows), 'detail_rows':len(family[kind]['records']),
                              'detail_counts_by_main_key':{str(k):v for k,v in sorted(multiplicity.items())},
                              'main_keys_with_multiple_rows':sum(v>1 for k,v in main_keys.items() if k),
                              'orphan_detail_rows':sum(len(v) for k,v in index.items() if k not in main_keys),
                              'repeated_identical_detail_excess':sum(len(v)-len({l.digest(x['raw']) for x in v}) for v in index.values()),
                              'detail_parse_and_keys_complete':valid,
                              'missing_detail_interpretation':'absence alone is not proof; requires complete file, unique key and agreement'})
            for kind, table in family.items():
                for record in table['records']:
                    raw_records.append({'release_id':source['source_archive_id'], 'archive_sha256':source['sha256'],
                                        'member_name':table['member_name'], 'member_sha256':table['sha256'],
                                        'record':record})
            for record in rows:
                raw = dict(record['raw'])
                for field in raw_required_fields:
                    raw.setdefault(field, None)
                    if field in record['raw'] and s.text(record['raw'][field]):
                        field_coverage[field] += 1
                key = s.text(raw.get('編號'))
                unique = bool(key) and main_keys[key] == 1
                details = {kind:[x['raw'] for x in index.get(key, [])] for kind,index in indices.items()}
                context = p.unproven_context(main, SCHEMA_HASHES['schema-main.csv'],
                                            family['park']['sha256'] if complete and unique else None,
                                            len(details['park']) if complete and unique else None)
                parking = p.parking_state(raw, details['park'], details['build'], complete, unique, context=context)
                # Diagnostic parking absence is withheld from foundation eligibility
                # whenever building detail ambiguity or a missing join was detected.
                if parking != 'NO_PARKING_CONFIRMED':
                    context['parking_evidence'] = None
                item = {'raw':raw, 'context':context, 'source_dataset_id':c.SOURCE_ID,
                        'release_id':source['source_archive_id'], 'archive_sha256':source['sha256'],
                        'member_sha256':family['main']['sha256'], 'member_name':main,
                        'physical_row_number':record['record_number'], 'source_release_available_at':None,
                        'availability_evidence':None, 'ingested_at':observation_at, 'transformed_at':observation_at,
                        'import_batch_id':'offline-recovery-v1', 'parser_version':s.PARSER_VERSION,
                        'transform_version':s.TRANSFORM_VERSION, 'identity_evidence':None,
                        'supersedes_version_id':None, 'cancelled':False}
                c.validate_shape(item, staging_schema)
                ids = l.identify(item)
                reasons, geo, date = _assess(raw, context, record['parse_error'], unique, parking)
                staging.append(item)
                evaluations.append(reasons)
                occurrences.append(ids)
                geographies.append({**geo, 'raw_county':geo['source_county'],
                                    'raw_county_basis':'embedded_manifest_member'})
                families[ids['transaction_family_id']].append(ids)
                profiles['parking'][parking] += 1
                profiles['geography'][geo['reason']] += 1
                profiles['county'][geo['source_county'] or 'UNKNOWN'] += 1
                profiles['district'][geo['city']+'/'+geo['district'] if geo['source_proven'] else 'INVALID'] += 1
                # Restrict free-text profiles to reviewed vocabularies / bounded categories.
                profiles['main_use'][s.text(raw.get('主要用途')) if s.text(raw.get('主要用途')) in {'住家用','住商用','商業用','辦公用','工業用','停車空間','其他',''} else 'OTHER_VOCABULARY'] += 1
                profiles['transaction_target'][s.text(raw.get('交易標的')) if s.text(raw.get('交易標的')) in {'房地(土地+建物)','房地(土地+建物)+車位','土地','建物','車位'} else 'OTHER_VOCABULARY'] += 1
                profiles['type'][s.TYPES.get(s.text(raw.get('建物型態')), 'UNSUPPORTED')] += 1
                profiles['month'][date['value'][:7] if date else 'INVALID'] += 1
                profiles['date_precision'][date['precision'] if date else 'INVALID'] += 1
                profiles['age'][ 'VALID_TRANSACTION_TIME_DIAGNOSTIC' if s.age_at_transaction(raw.get('交易年月日'),raw.get('建築完成年月')) else 'UNAVAILABLE'] += 1
                floor, total = s.parse_floor(raw.get('移轉層次')), s.parse_floor(raw.get('總樓層數'))
                profiles['floor']['VALID_SINGLE_ABOVE_GROUND' if floor and total and floor<=total else 'AMBIGUOUS_OR_INVALID'] += 1
                counts = s.parse_counts(raw.get('交易筆棟數'))
                profiles['building_count'][str(counts[1]) if counts else 'INVALID'] += 1
                price, area = s.number(raw.get('總價元')), s.number(raw.get('建物移轉總面積平方公尺'))
                profiles['positive_raw_price_area']['POSITIVE' if price and area and price>0 and area>0 else 'INVALID'] += 1
                for kind in ('build','land'):
                    for detail in details[kind]:
                        value = s.text(detail.get('移轉情形'))
                        profiles[kind+'_transfer_status'][value if value in {'全筆移轉','持分移轉',''} else 'OTHER'] += 1
    if len(staging) > 100000:
        raise ValueError('bounded_main_rows_exceeded')
    funnel, first = semantic_funnel(evaluations)
    exclusion = [{'occurrence_id':ids['occurrence_id'], 'transaction_family_id':ids['transaction_family_id'],
                  'source_record_version_id':ids['version_id'], 'raw_payload_sha256':ids['raw_payload_sha256'],
                  'geography':geo, 'first_reason':reason, 'all_reasons':sorted({v for v in ev.values() if v})}
                 for ids,geo,reason,ev in zip(occurrences,geographies,first,evaluations)]
    # This proof deliberately cannot emit training rows with unproved attestations.
    if any(reason is None for reason in first):
        raise ValueError('unreviewed_positive_cohort')
    output = {'source-records.jsonl':raw_records, 'occurrences.jsonl':staging,
              'exclusions.jsonl':exclusion, 'cohort-membership.jsonl':[],
              'targets.jsonl':[], 'features.jsonl':[], 'splits.jsonl':[]}
    checksums = {}
    for filename, values in output.items():
        ordered = sorted(l.canonical_bytes(x) for x in values)
        path = out / filename
        with path.open('xb') as handle:
            for value in ordered:
                handle.write(value + b'\n')
        checksums[filename] = file_sha256(path)
    repeat_families = [v for k,v in families.items() if k and len(v)>1]
    report = {
        'schema_version':'ml-source-recovery-aggregate-evidence-v1',
        'starting_sha':'b735c52f698de0355539cdcff170e3ccde5f8d7b',
        'branch':'research/ml-valuation-source-recovery-v1',
        'scope':{'sale_members':list(members), 'selected_exact_releases':[x['release_version'] for x in manifest['sources'] if x['checksum_status']=='EXACT_MATCH'],
                 'limit':'two quarterly packages; Taipei/New Taipei main and complete associated details only'},
        'source_status_counts':_histogram(x['recovery_status'] for x in manifest['sources']),
        'checksum_status_counts':_histogram(x['checksum_status'] for x in manifest['sources']),
        'source_manifest_sha256':l.digest(manifest), 'source_count':len(manifest['sources']),
        'raw_main_rows':len(staging), 'raw_main_detail_records':len(raw_records),
        'schema_valid_rows':sum(x['schema'] is None for x in evaluations),
        'field_nonblank_counts':dict(sorted(field_coverage.items())),
        'profiles':{k:dict(sorted(v.items())) for k,v in sorted(profiles.items())},
        'joins':joins, 'cohort_funnel':funnel, 'first_exclusion_counts':_histogram(first),
        'final_candidate_count':0, 'approved_geographic_coverage':[], 'approved_time_coverage':[],
        'identity_diagnostics':{'family_namespace':'provisional county + official 編號; namespace reuse not attested',
                                'physical_occurrences':len(occurrences),
                                'distinct_nonmissing_provisional_families':sum(k is not None for k in families),
                                'repeated_families':len(repeat_families),
                                'exact_payload_repeat_excess':sum(len(v)-len({x['version_id'] for x in v}) for v in repeat_families),
                                'changed_payload_families':sum(len({x['version_id'] for x in v})>1 for v in repeat_families),
                                'revision_order_attested':0, 'cancellation_attested':0},
        'foundation_staging_audit':audit_staging(staging, cutoff),
        'chronological_split_viability':'BLOCKED; zero approved cohort and historical availability unproved',
        'baseline_readiness':{'global_median':False, 'district_type_median':False, 'historical_comparables':False},
        'readiness':'BLOCKED', 'ml_b_may_begin':False,
        'age_feature':'DEFERRED; parsed diagnostic only',
        'hashes':checksums,
        'build_contract':{'cutoff':cutoff, 'observation_at':observation_at,
                          'code_sha256':l.digest({f.name:repository_text_sha256(f) for f in sorted((s.ROOT/'scripts/ml').glob('*.py'))}),
                          'source_contract_sha256':l.digest(read_json(s.ROOT/'docs/ml/contracts/source-contract-v1.json')),
                          'registry_sha256':l.digest(read_json(s.REGISTRY)),
                          'python_version':sys.version.split()[0],
                          'schema_review_version':'plvr-embedded-schema-detail-audit-v1'},
        'reproducibility_scope':'raw staging, exclusions and aggregate proof; empty output hashes are not a nonempty dataset proof',
    }
    proof_manifest = {'schema_version':'plvr-offline-recovery-proof-build-v1',
                      'source_manifest_sha256':report['source_manifest_sha256'], 'contract':report['build_contract'],
                      'hashes':checksums, 'raw_main_count':len(staging), 'candidate_count':0,
                      'excluded_count':len(exclusion), 'gate':'BLOCKED'}
    report['proof_build_manifest_sha256'] = l.digest(proof_manifest)
    for filename,value in [('source-manifest.json',manifest), ('proof-build-manifest.json',proof_manifest), ('evidence.json',report)]:
        (out / filename).write_bytes(l.canonical_bytes(value) + b'\n')
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
        report = build(read_json(args.preflight),read_json(args.downloads),args.output,args.cutoff,args.observation_at)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        parser.exit(2, 'recovery_audit_failed: invalid or unavailable bounded inputs\n')


if __name__ == '__main__':
    main()
