"""Bounded offline strict cohort build from the merged recovery inputs.

Only aggregates go to stdout. All main/detail records, identities and exclusions
remain in create-only ignored local storage. This CLI never grants ML-B approval.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from . import audit_source_recovery as a, contracts as c, lineage as l
from . import plvr_raw_parser as p, rights_dwelling as d, semantics as s
from . import source_recovery as r, strict_cohort as cohort, temporal as t, chronology
from .audit_foundation import file_sha256, read_json, repository_text_sha256

VERSION='ml-semantic-temporal-closure-v1'
MEMBERS=('a_lvr_land_a.csv','f_lvr_land_a.csv')


def staging_clocks(logical_snapshot_at: str) -> dict:
    """Execution timestamps are not reconstructed from a logical snapshot clock."""
    if l.timestamp(logical_snapshot_at) is None: raise ValueError('explicit_timezone_required')
    return {'ingested_at':None,'transformed_at':None,'logical_snapshot_at':logical_snapshot_at}


def write_jsonl(path: Path, values: list[dict]) -> str:
    with path.open('xb') as handle:
        for value in sorted(l.canonical_bytes(x) for x in values):
            handle.write(value+b'\n')
    return file_sha256(path)


def build(preflight: dict, downloads: list[dict], destination: Path, cutoff: str,
          observation_at: str) -> dict:
    if l.timestamp(cutoff) is None or l.timestamp(observation_at) is None:
        raise ValueError('explicit_timezone_instants_required')
    if l.timestamp(cutoff)>l.timestamp(observation_at): raise ValueError('cutoff_after_observation')
    out=r.ignored_destination(destination)
    if out.exists(): raise ValueError('clean_build_destination_required')
    manifest=r.build_manifest(preflight,downloads)
    recovered=[x for x in manifest['sources'] if x['checksum_status']=='EXACT_MATCH' and x['package_valid']]
    if {x['release_version'] for x in recovered}!={'112S3','115S2'}:
        raise ValueError('exact_bounded_two_release_scope_required')
    acquisition_hash=l.digest(manifest)
    profiles=defaultdict(Counter); field_counts=defaultdict(Counter)
    items=[]; raw_records=[]; joins=[]; semantic_records=[]; source_bindings=[]
    for source in recovered:
        path=s.ROOT/source['local_recovered_path']
        availability_input=t.retrieval_evidence(source,manifest_sha256=acquisition_hash)
        resolved=t.resolve_availability(availability_input,source['source_archive_id'],source['sha256'])
        source['availability_quality']=resolved['quality']
        source['conservative_public_available_at']=resolved['available_at']
        source['release_published_at']=None
        profiles['availability_release'][resolved['quality']]+=1
        with zipfile.ZipFile(path) as archive:
            tables=a._load_members(archive,source,MEMBERS)
        for member,family in sorted(tables.items()):
            mains=family['main']['records']
            counts=Counter(s.text(x['raw'].get('編號')) for x in mains)
            indices={}; complete=True
            for kind in ('build','land','park'):
                index,valid=p.detail_index(family[kind]['records'])
                orphan=sum(len(v) for k,v in index.items() if k not in counts)
                complete &= valid and orphan==0
                indices[kind]=index
                joins.append({'release_id':source['source_archive_id'],'main_member':member,
                    'kind':kind,'main_rows':len(mains),'detail_rows':len(family[kind]['records']),
                    'ambiguous_main_keys':sum(v>1 for v in counts.values()),
                    'orphan_detail_rows':orphan,'complete_parse':valid,
                    'repeated_detail_excess':sum(len(v)-len({l.digest(x['raw']) for x in v}) for v in index.values())})
            for kind,table in sorted(family.items()):
                field_counts[kind].update({field:sum(s.text(x['raw'].get(field))!='' for x in table['records']) for field in table['header']})
                for record in table['records']:
                    raw_records.append({'release_id':source['source_archive_id'],'archive_sha256':source['sha256'],
                                        'member_name':table['member_name'],'member_sha256':table['sha256'],'record':record})
            source_bindings.append({'release_id':source['source_archive_id'],'main_member':member,
                                    'main_sha256':family['main']['sha256'],
                                    'detail_sha256':{kind:family[kind]['sha256'] for kind in indices},
                                    'schema_sha256':a.SCHEMA_HASHES})
            for record in mains:
                raw=record['raw']; key=s.text(raw.get('編號'))
                unique=bool(key) and counts[key]==1
                details={kind:[x['raw'] for x in index.get(key,[])] for kind,index in indices.items()}
                semantic=d.classify(raw,details['build'],details['land'],complete=complete,unique=unique,
                    scope={'archive_sha256':source['sha256'],'member_name':member,
                           'physical_row_number':record['record_number'],'schema_sha256':a.SCHEMA_HASHES['schema-main.csv']})
                context=p.unproven_context(member,a.SCHEMA_HASHES['schema-main.csv'],
                                           family['park']['sha256'] if complete and unique else None,
                                           len(details['park']) if complete and unique else None)
                parking=p.parking_state(raw,details['park'],details['build'],complete,unique,context=context)
                semantic['parking']=parking
                if parking!='NO_PARKING_CONFIRMED': context['parking_evidence']=None
                # The source field/unit is proved; compatible whole-dwelling
                # rights remain a separate guard. No interior-area assertion.
                context.update(area_basis=s.AREA_VERSION,
                    area_evidence={'sha256':a.SCHEMA_HASHES['schema-main.csv'],
                                   'locator':'schema-main.csv#建物移轉總面積平方公尺','version':VERSION})
                item={'raw':raw,'context':context,'source_dataset_id':c.SOURCE_ID,
                      'release_id':source['source_archive_id'],'archive_sha256':source['sha256'],
                      'member_name':member,'member_sha256':family['main']['sha256'],
                      'physical_row_number':record['record_number'],'physical_start_line':record['start_line'],
                      'physical_end_line':record['end_line'],'source_release_available_at':resolved['available_at'],
                      'availability_evidence':availability_input.get('evidence'),
                      'availability_quality':resolved['quality'],'release_published_at':None,
                      **staging_clocks(observation_at),
                      'import_batch_id':'offline-semantic-temporal-closure-v1','parser_version':s.PARSER_VERSION,
                      'transform_version':s.TRANSFORM_VERSION,'closure_transform_version':VERSION,
                      'identity_evidence':None,'supersedes_version_id':None,'cancelled':False,
                      'cancellation_state_evidenced':False,'semantic':semantic,
                      'area_contract':{'field':'建物移轉總面積平方公尺','unit':'m²'},
                      'parse_error':record['parse_error'],
                      'detail_payload_sha256':{kind:l.digest(rows) for kind,rows in details.items()},
                      'detail_member_sha256':{kind:family[kind]['sha256'] for kind in indices}}
                items.append(item)
                identity=l.identify(item)
                semantic_records.append({**identity,'release_id':item['release_id'],'semantic':semantic,
                                         'detail_payload_sha256':item['detail_payload_sha256']})
                for label in ('rights','dwelling','parking'): profiles[label][semantic[label]]+=1
                profiles['rights_reason'][semantic['rights_reason'] or 'CONFIRMED']+=1
                profiles['dwelling_reason'][semantic['dwelling_reason'] or 'CONFIRMED']+=1
                effective=s.parse_roc_date(raw.get('交易年月日'))
                profiles['transaction_month'][effective['value'][:7] if effective else 'INVALID']+=1
                profiles['date_precision'][effective['precision'] if effective else 'INVALID']+=1
                geo=s.normalize_geography(raw.get('縣市',''),raw.get('鄉鎮市區',''),member)
                profiles['county'][geo['source_county'] or 'UNKNOWN']+=1
                profiles['district'][geo['city']+'/'+geo['district'] if geo['source_proven'] else 'INVALID']+=1
                profiles['geography'][geo['reason']]+=1
                profiles['building_type'][s.TYPES.get(s.text(raw.get('建物型態')),'UNSUPPORTED')]+=1
                profiles['release'][item['release_id']]+=1
                profiles['availability_occurrence'][resolved['quality']]+=1
                diagnostic=cohort.numeric_diagnostic(raw)
                if (raw.get('交易標的')=='房地(土地+建物)' and raw.get('主要用途')=='住家用'
                        and s.text(raw.get('建物型態')) in s.TYPES and parking=='NO_PARKING_CONFIRMED'):
                    profiles['no_parking_residential_reconciliation'][diagnostic['reconciliation']]+=1
    result=cohort.build_cohort(items,cutoff)
    split_rows=chronology.split_rows_from_items(result['selected_rows'])
    splits=chronology.design_splits(split_rows,coverage_evidence=None,ledger_items=items,
                                   label_observation_cutoff=cutoff)
    out.mkdir(parents=True)
    outputs={'source-records.jsonl':raw_records,'occurrences.jsonl':items,
             'semantic-classifications.jsonl':semantic_records,
             'revision-lineage.jsonl':result['revision_dispositions'],'revision-edges.jsonl':result['relations'],
             'exclusions.jsonl':result['exclusions'],'cohort-membership.jsonl':result['membership'],
             'targets.jsonl':result['targets'],'features.jsonl':result['features'],'splits.jsonl':splits['assignments']}
    hashes={name:write_jsonl(out/name,values) for name,values in outputs.items()}
    selected_count=len(result['membership'])
    code_hash=l.digest({f.name:repository_text_sha256(f) for f in sorted((s.ROOT/'scripts/ml').glob('*.py'))})
    dataset_manifest={'schema_version':VERSION+'-build-manifest','dataset_contract':cohort.VERSION,
        'readiness_approval':False,'candidate_count':selected_count,'raw_main_count':len(items),
        'excluded_count':len(result['exclusions']),'source_manifest_sha256':l.digest(manifest),
        'acquisition_manifest_sha256':acquisition_hash,'source_bindings':source_bindings,
        'hashes':hashes,'cutoff':cutoff,'logical_observation_at':observation_at,
        'timezone':'Asia/Taipei','code_sha256':code_hash,'python_version':sys.version.split()[0],
        'source_contract_sha256':l.digest(read_json(s.ROOT/'docs/ml/contracts/source-contract-v1.json')),
        'closure_contract_sha256':l.digest(read_json(s.ROOT/'docs/ml/contracts/semantic-temporal-closure-v1.json')),
        'registry_sha256':l.digest(read_json(s.REGISTRY)),
        'feature_columns':['county_district','building_type','area_ping','floor','prediction_year','prediction_month'],
        'target_version':s.TARGET_VERSION,'area_version':s.AREA_VERSION,
        'rights_version':d.VERSION,'availability_version':t.VERSION,'split_version':chronology.VERSION}
    report={'schema_version':VERSION+'-aggregate-evidence','starting_sha':'d06ed4f062a212fed4ce0adf092c2fdc515a3f62',
        'branch':'research/ml-valuation-semantic-temporal-closure-v1','gate':'BLOCKED' if not selected_count or not splits['viable'] else 'REVIEW_REQUIRED',
        'ml_b_may_begin':False,'scope':{'releases':[x['release_version'] for x in recovered],'members':list(MEMBERS)},
        'raw_main_rows':len(items),'raw_main_detail_rows':len(raw_records),'profiles':{k:dict(sorted(v.items())) for k,v in sorted(profiles.items())},
        'field_nonblank_counts':{k:dict(sorted(v.items())) for k,v in sorted(field_counts.items())},
        'joins':joins,'funnel':result['funnel'],'first_exclusion_counts':dict(sorted(Counter(x['first_reason'] for x in result['exclusions']).items())),
        'approved_candidate_count':selected_count,'approved_coverage':{'county':{},'district':{},'month':{},'building_type':{},'release':{}},
        'split_design':splits,'baseline_readiness':{'global_median':False,'district_type_median':False,'historical_comparables':False},
        'availability':{'authenticated_historical_publication_releases':0,'verified_current_upper_bound_releases':sum(x['conservative_public_available_at'] is not None for x in recovered),
            'policy':'Current verified exact HTTPS retrieval only; no earlier historical eligibility; system first-seen alone is insufficient.',
            'release_bounds':[{'release_id':x['source_archive_id'],'archive_sha256':x['sha256'],'quality':x['availability_quality'],
                              'available_at':x['conservative_public_available_at'],'release_published_at':None} for x in recovered]},
        'revisions':{'classifications':dict(sorted(Counter('REVISION_UNVERIFIED' if x['reason']=='lineage_unverified' else
            'AMBIGUOUS_COLLISION' if x['reason'] in {'revision_ambiguous','occurrence_conflict','immutable_lineage_conflict','semantic_evidence_conflict'} else
            'EXACT_REPUBLICATION' if x['reason'] in {'exact_duplicate','republication'} else 'DISTINCT_TRANSACTION' if x['selected_as_of_cutoff'] else 'EXCLUDED'
            for x in result['revision_dispositions']).items())),
            'provisional_family_count':len({l.identify(x)['transaction_family_id'] for x in items}),
            'predecessor_edges':len(result['relations']),'supersession_attested':0,'cancellation_attested':0,
            'namespace_evidenced':0,'note':'Absent repeats do not establish stable namespace or complete correction/cancellation history.'},
        'reconciliation':{'all_raw_counts':result['reconciliation_counts'],
                          'basis':'Diagnostic only; mixed parking, partial rights and multiple objects can explain differences; no target substitution.',
                          'tolerance':'max(1 NTD/m², 0.001 * total_price / registered_area)'},
        'deterministic_hashes':{**hashes,'source_manifest':l.digest(manifest),'dataset_manifest':l.digest(dataset_manifest)},
        'nonempty_build_proven':False,'blockers':[
            'Building detail has no building identifier, private/common object role or numeric building transfer fraction; no reviewed whole-dwelling interest evidence.',
            'No dwelling-unit/object-count evidence beyond main building count; detail multiplicity includes unresolved common portions.',
            'Only current availability upper bounds recovered; no exact-byte authenticated availability for 2023–2026 historical fold freezes.',
            'No stable cross-release official ID namespace, complete predecessor/cancellation evidence or supported changed-ID linkage.',
            'Zero approved rows; no nonempty reproducibility or mature contiguous four-block evaluation.'],
        'contract':dataset_manifest}
    for filename,value in [('source-manifest.json',manifest),('dataset-manifest.json',dataset_manifest),('evidence.json',report)]:
        with (out/filename).open('xb') as handle: handle.write(l.canonical_bytes(value)+b'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight',type=Path,default=r.ARTIFACT_ROOT/'preflight.json')
    parser.add_argument('--downloads',type=Path,default=r.ARTIFACT_ROOT/'downloads.json')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cutoff',required=True)
    parser.add_argument('--observation-at',required=True)
    args=parser.parse_args()
    try:
        result=build(read_json(args.preflight),read_json(args.downloads),args.output,args.cutoff,args.observation_at)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False))
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile):
        parser.exit(2,'semantic_temporal_build_failed: invalid or unavailable bounded inputs\n')


if __name__=='__main__': main()
