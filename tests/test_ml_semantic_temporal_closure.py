"""Synthetic evidence only. Positive fixtures are not official source attestations."""
from copy import deepcopy
from decimal import Decimal
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ml import lineage as l, semantics as s
from tests.test_ml_dataset_foundation import row, context, occurrence, proof


def module(name):
    assert importlib.util.find_spec('scripts.ml.' + name), name + ' must be implemented'
    return importlib.import_module('scripts.ml.' + name)


def details():
    return ([{'主要用途':'住家用','移轉情形':'全筆移轉',
              '建物移轉面積平方公尺':'100','建物分層':'三層'}],
            [{'移轉情形':'全筆移轉','權利人持分分子':'1','權利人持分分母':'1',
              '土地移轉面積平方公尺':'20'}])


def semantic_scope():
    return {'archive_sha256':'a'*64,'member_name':'h_lvr_land_a.csv',
            'physical_row_number':1,'schema_sha256':'b'*64}


def semantic_proof(raw, builds, lands):
    return {'evidence':proof(), 'scope':semantic_scope(), 'main_sha256':l.digest(raw),
            'build_sha256':l.digest(builds), 'land_sha256':l.digest(lands),
            'building_objects':[{'role':'PRIVATE_DWELLING','object_id':'SYNTHETIC-UNIT',
                                 'dwelling_units':1,'transferred_fraction':['1','1'],
                                 'required_fraction':['1','1']}],
            'land_interests':[{'unit_id':'SYNTHETIC-UNIT','required_fraction':['1','1']}],
            'special_transaction':False}


def assess(raw=None, builds=None, lands=None, supplement=True, **kwargs):
    raw = raw or row(**{'交易筆棟數':'土地1建物1車位0'})
    b, d = details()
    builds = b if builds is None else builds
    lands = d if lands is None else lands
    supplied = semantic_proof(raw,builds,lands) if supplement else None
    return module('rights_dwelling').classify(raw,builds,lands,complete=True,
                                             unique=True,supplement=supplied,scope=semantic_scope(),**kwargs)


def test_full_rights_needs_exact_bound_object_and_land_evidence():
    result=assess()
    assert result['rights']=='FULL_RIGHTS_CONFIRMED'
    assert result['dwelling']=='SINGLE_DWELLING_CONFIRMED'
    assert assess(supplement=False)['rights'] != 'FULL_RIGHTS_CONFIRMED'
    assert assess(supplement=False)['dwelling'] != 'SINGLE_DWELLING_CONFIRMED'


@pytest.mark.parametrize('field,value,want',[
    ('權利人持分分子','', 'RIGHTS_UNKNOWN'),
    ('權利人持分分母','', 'RIGHTS_UNKNOWN'),
    ('權利人持分分母','0','RIGHTS_UNKNOWN'),
    ('權利人持分分母','NaN','RIGHTS_UNKNOWN'),
    ('權利人持分分子','2','RIGHTS_AMBIGUOUS'),
])
def test_land_denominator_and_inconsistent_whole_status_fail_closed(field,value,want):
    b,d=details(); d[0][field]=value
    assert assess(builds=b,lands=d)['rights']==want


def test_fractional_land_is_not_automatically_partial_dwelling():
    b,d=details(); d[0].update({'權利人持分分子':'1','權利人持分分母':'10','移轉情形':'持分移轉'})
    assert assess(builds=b,lands=d,supplement=False)['rights']=='RIGHTS_AMBIGUOUS'
    raw=row(**{'交易筆棟數':'土地1建物1車位0'})
    att=semantic_proof(raw,b,d)
    att['land_interests'][0]['required_fraction']=['1','10']
    assert module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,supplement=att,scope=semantic_scope())['rights']=='FULL_RIGHTS_CONFIRMED'
    att['land_interests'][0]['required_fraction']=['2','10']
    assert module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,supplement=att,scope=semantic_scope())['rights']=='PARTIAL_RIGHTS'


def test_partial_building_and_mixed_common_interests():
    raw=row(**{'交易筆棟數':'土地1建物1車位0'})
    b,d=details(); b[0]['移轉情形']='持分移轉'
    att=semantic_proof(raw,b,d)
    att['building_objects'][0]['transferred_fraction']=['1','2']
    assert module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,supplement=att,scope=semantic_scope())['rights']=='PARTIAL_RIGHTS'
    b,d=details(); b.append({'主要用途':'共有部分','移轉情形':'持分移轉','建物移轉面積平方公尺':'10'})
    raw['建物移轉總面積平方公尺']='110'
    att=semantic_proof(raw,b,d)
    att['building_objects'].append({'role':'COMMON_ANCILLARY','object_id':'SYNTHETIC-COMMON',
        'unit_id':'SYNTHETIC-UNIT','dwelling_units':0,
        'transferred_fraction':['1','10'],'required_fraction':['1','10']})
    assert module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,supplement=att,scope=semantic_scope())['rights']=='FULL_RIGHTS_CONFIRMED'


@pytest.mark.parametrize('case,want',[
    ('count_two','MULTI_DWELLING'),('missing_count','DWELLING_UNKNOWN'),
    ('target','DWELLING_AMBIGUOUS'),('repeated','DWELLING_AMBIGUOUS'),
    ('two_details','DWELLING_AMBIGUOUS'),('two_units','MULTI_DWELLING'),
    ('wrong_binding','DWELLING_AMBIGUOUS'),('area_disagreement','DWELLING_AMBIGUOUS'),
])
def test_dwelling_never_uses_main_row_count_as_unit_proof(case,want):
    raw=row(**{'交易筆棟數':'土地1建物1車位0'}); b,d=details()
    if case=='count_two': raw['交易筆棟數']='土地1建物2車位0'
    if case=='missing_count': raw['交易筆棟數']=''
    if case=='target': raw['交易標的']='建物'
    if case=='repeated': b.append(dict(b[0]))
    if case=='two_details': b.append({**b[0],'建物移轉面積平方公尺':'1'})
    if case=='area_disagreement': b[0]['建物移轉面積平方公尺']='99'
    att=semantic_proof(raw,b,d)
    if case=='two_units': att['building_objects'][0]['dwelling_units']=2
    if case=='wrong_binding': att['main_sha256']='0'*64
    result=module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,supplement=att,scope=semantic_scope())
    assert result['dwelling']==want


def test_ambiguous_or_incomplete_join_overrides_positive_supplement():
    raw=row(**{'交易筆棟數':'土地1建物1車位0'}); b,d=details()
    for complete,unique in [(False,True),(True,False)]:
        result=module('rights_dwelling').classify(raw,b,d,complete=complete,unique=unique,
                                               supplement=semantic_proof(raw,b,d),scope=semantic_scope())
        assert result['rights'] != 'FULL_RIGHTS_CONFIRMED'
        assert result['dwelling'] != 'SINGLE_DWELLING_CONFIRMED'


def availability(kind='EXACT_PUBLICATION_TIME',value='2024-07-01T00:00:00+08:00'):
    return {'quality':kind,'value':value,'archive_sha256':'a'*64,'release_id':'r1',
            'evidence':proof()}


@pytest.mark.parametrize('kind,value,expected',[
    ('EXACT_PUBLICATION_TIME','2024-07-01T00:00:00+08:00','2024-06-30T16:00:00+00:00'),
    ('DATE_ONLY_PUBLICATION','2024-07-01','2024-07-01T16:00:00+00:00'),
    ('CONSERVATIVE_UPPER_BOUND','2026-10-08T08:00:00+08:00','2026-10-08T00:00:00+00:00'),
    ('SYSTEM_FIRST_SEEN','2024-07-01T00:00:00+08:00',None),
    ('UNKNOWN',None,None),
])
def test_availability_preserves_quality_and_conservative_day_boundary(kind,value,expected):
    result=module('temporal').resolve_availability(availability(kind,value),'r1','a'*64)
    assert result['available_at']==expected
    assert result['quality']==kind


def test_content_reuse_and_unverified_fetch_never_supply_historical_availability():
    t=module('temporal')
    assert t.resolve_availability(availability(),'r1','b'*64)['available_at'] is None
    assert t.resolve_availability({'retrieved_at':'2026-10-08T00:00:00Z'},'r1','a'*64)['available_at'] is None
    result=t.resolve_availability(availability('CONSERVATIVE_UPPER_BOUND','2026-10-08T00:00:00Z'),'r1','a'*64)
    assert not t.available_by(result,'2024-07-02T00:00:00Z')
    assert t.available_by(result,'2026-10-08T00:00:00Z')


def test_strict_target_requires_all_semantic_and_temporal_prerequisites():
    closure=module('strict_cohort')
    verdict={'rights':'FULL_RIGHTS_CONFIRMED','dwelling':'SINGLE_DWELLING_CONFIRMED',
             'parking':'NO_PARKING_CONFIRMED','source_valid':True,'revision_valid':True,
             'availability_valid':True,'area_unit':'m²','area_field':'建物移轉總面積平方公尺'}
    result=closure.strict_target(row(),context(),verdict)
    assert result['valid'] and Decimal(result['area_ping'])==Decimal('30.25')
    for key,value in [('rights','RIGHTS_AMBIGUOUS'),('dwelling','MULTI_DWELLING'),
                      ('parking','PARKING_PRESENT'),('revision_valid',False),
                      ('availability_valid',False),('source_valid',False),
                      ('area_unit','ping'),('area_field','interior'),]:
        assert not closure.strict_target(row(),context(),{**verdict,key:value})['valid']
    for changes in [{'主要用途':'住商用'},{'建物型態':'透天厝'},
                    {'交易標的':'土地'},{'單價元平方公尺':'1'}]:
        assert not closure.strict_target(row(**changes),context(),verdict)['valid']


def test_revision_dispositions_preserve_all_physical_occurrences_and_edges():
    old=occurrence(); duplicate=occurrence(number=2)
    new=occurrence(row(**{'總價元':'11000000'}),release='r2',available='2024-08-01T00:00:00Z',
                   supersedes_version_id=l.identify(old)['version_id'])
    result=l.select_as_of([new,duplicate,old],'2024-07-15T00:00:00Z')
    assert 'dispositions' in result, 'per-occurrence revision ledger required'
    assert len(result['dispositions'])==3
    assert sum(x['selected_as_of_cutoff'] for x in result['dispositions'])==1
    assert next(x for x in result['dispositions'] if x['release_id']=='r2')['reason']=='after_availability_cutoff'
    late=l.select_as_of([old,new],'2024-09-01T00:00:00Z')
    assert late['relations']==[{'predecessor_version_id':l.identify(old)['version_id'],
                               'successor_version_id':l.identify(new)['version_id'],
                               'classification':'CORRECTION'}]


def test_post_cutoff_cancellation_retains_earlier_record():
    old=occurrence(); canceled=occurrence(release='r2',available='2024-08-01T00:00:00Z',
        cancelled=True,supersedes_version_id=l.identify(old)['version_id'])
    early=l.select_as_of([old,canceled],'2024-07-15T00:00:00Z')
    assert len(early['selected'])==1
    assert not l.select_as_of([old,canceled],'2024-08-01T00:00:00Z')['selected']


def candidate(number=1, **changes):
    item=occurrence(row(**{'編號':'SYNTHETIC-'+str(number)}),number=number,**changes)
    item['semantic']={'rights':'FULL_RIGHTS_CONFIRMED','dwelling':'SINGLE_DWELLING_CONFIRMED',
                      'parking':'NO_PARKING_CONFIRMED'}
    item['area_contract']={'field':'建物移轉總面積平方公尺','unit':'m²'}
    return item


def test_real_cohort_pipeline_preserves_exclusions_and_hashable_features():
    c=module('strict_cohort')
    good=candidate(); bad=candidate(2)
    bad['semantic']['rights']='RIGHTS_UNKNOWN'
    before=deepcopy([good,bad])
    result=c.build_cohort([bad,good],'2024-09-01T00:00:00Z')
    assert len(result['membership'])==1
    assert len(result['exclusions'])==1
    assert result['exclusions'][0]['first_reason']=='RIGHTS_UNKNOWN'
    assert len(result['features'])==len(result['targets'])==1
    assert set(result['features'][0]['values'])=={'county_district','building_type','area_ping','floor','prediction_year','prediction_month'}
    assert [good,bad]==before
    assert result==c.build_cohort([good,bad],'2024-09-01T00:00:00Z')
    for stage in result['funnel']:
        assert stage['input_count']==stage['accepted_count']+stage['excluded_count']


def test_selected_ineligible_correction_never_resurrects_good_old_target():
    c=module('strict_cohort')
    old=candidate()
    new=deepcopy(old)
    new.update(release_id='r2',archive_sha256='d'*64,source_release_available_at='2024-08-01T00:00:00Z',
               supersedes_version_id=l.identify(old)['version_id'])
    new['raw']['主要用途']='住商用'
    result=c.build_cohort([old,new],'2024-09-01T00:00:00Z')
    assert not result['targets']
    assert len(result['exclusions'])==2
    assert 'superseded_version' in result['exclusions'][0]['all_reasons']+result['exclusions'][1]['all_reasons']


def test_effective_month_and_future_day_are_excluded_without_fabrication():
    c=module('strict_cohort')
    month=candidate(); month['raw']['交易年月日']='11306'
    future=candidate(2); future['raw']['交易年月日']='1130902'
    result=c.build_cohort([month,future],'2024-09-01T00:00:00Z')
    assert not result['membership']
    assert {x['first_reason'] for x in result['exclusions']}=={'TRANSACTION_DAY_REQUIRED','EFFECTIVE_AFTER_AVAILABILITY_OR_CUTOFF'}


def chronology_ledger():
    items=[]
    # 21 hand-defined consecutive months; 12 train, 3 each held-out block.
    for month in ['2023-01','2023-02','2023-03','2023-04','2023-05','2023-06','2023-07',
                  '2023-08','2023-09','2023-10','2023-11','2023-12',
                  '2024-01','2024-02','2024-03','2024-04','2024-05','2024-06',
                  '2024-07','2024-08','2024-09']:
        for i in range(20):
            item=candidate(len(items)+1,release=month,available=month+'-20T00:00:00+08:00')
            item['raw']['交易年月日']=str(int(month[:4])-1911)+month[5:]+'10'
            items.append(item)
    return items


def chronology_rows():
    selected=module('strict_cohort').build_cohort(chronology_ledger(),'2024-10-01T00:00:00+08:00')
    return module('chronology').split_rows_from_items(selected['selected_rows'])


def test_chronological_split_checks_lag_and_reserves_calibration():
    c=module('chronology')
    rows=chronology_rows()
    result=c.design_splits(rows,coverage_evidence=proof(),ledger_items=chronology_ledger(),label_observation_cutoff='2024-10-01T00:00:00+08:00')
    assert result['viable']
    assert result['blocks']=={'TRAIN':['2023-01','2023-12'],'VALIDATION':['2024-01','2024-03'],
                             'CALIBRATION':['2024-04','2024-06'],'TEST':['2024-07','2024-09']}
    assert len(result['assignments'])==420
    rows[0]['available_at']='2024-01-02T00:00:00+08:00'
    result=c.design_splits(rows,coverage_evidence=proof(),ledger_items=chronology_ledger(),label_observation_cutoff='2024-10-01T00:00:00+08:00')
    assert not result['viable'] and not result['assignments']
    assert 'RELEASE_LAG_AT_FREEZE' in result['blockers']


@pytest.mark.parametrize('case',['empty','tiny','gap','unknown_coverage','month_precision','duplicate_family','small_subgroup'])
def test_insufficient_or_unproven_chronology_never_forces_splits(case):
    c=module('chronology'); rows=chronology_rows(); coverage=proof()
    if case=='empty': rows=[]
    if case=='tiny': rows=rows[:5]
    if case=='gap': rows=[r for r in rows if not r['effective_date'].startswith('2023-06')]
    if case=='unknown_coverage': coverage=None
    if case=='month_precision': rows[0]['precision']='month'; rows[0]['effective_date']='2023-01'
    if case=='duplicate_family': rows[1]['family_id']=rows[0]['family_id']
    if case=='small_subgroup': rows[0]['county_district']='臺北市/中正區'
    result=c.design_splits(rows,coverage_evidence=coverage,ledger_items=chronology_ledger(),label_observation_cutoff='2024-10-01T00:00:00+08:00')
    assert not result['viable'] and not result['assignments']


def test_baseline_history_selects_asof_before_subject_and_future_filters():
    c=module('chronology')
    old=candidate(); new=deepcopy(old)
    new.update(release_id='r2',archive_sha256='d'*64,
        source_release_available_at='2024-08-01T00:00:00Z',supersedes_version_id=l.identify(old)['version_id'])
    new['raw']['主要用途']='住商用'
    another=candidate(2)
    history=c.baseline_history([old,new,another],prediction_at='2024-07-15T00:00:00Z',
        fitting_cutoff='2024-07-10T00:00:00Z',subject_family=l.identify(another)['transaction_family_id'],
        fitting_families={l.identify(old)['transaction_family_id'],l.identify(another)['transaction_family_id']})
    assert len(history)==1 and history[0]['raw']['主要用途']=='住家用'
    assert not c.baseline_history([old,new],prediction_at='2024-09-01T00:00:00Z',
        fitting_cutoff='2024-09-01T00:00:00Z',subject_family='other',fitting_families={l.identify(old)['transaction_family_id']})


def test_real_build_rejects_overwrites_and_unapproved_destinations(tmp_path):
    a=module('audit_semantic_temporal_closure')
    with pytest.raises(ValueError,match='ignored_workspace_destination_required'):
        a.build({},[],tmp_path/'outside','2026-10-08T08:00:00Z','2026-10-08T08:00:00Z')
    with pytest.raises(ValueError,match='explicit_timezone'):
        a.build({},[],tmp_path/'outside','2026-10-08','2026-10-08')


def test_changed_retrieval_filename_cannot_relabel_source_bytes():
    t=module('temporal')
    source={'checksum_status':'EXACT_MATCH','package_valid':True,
        'sha256':'b'*64,'expected_sha256':'a'*64,'source_archive_id':'r1',
        'official_url':'https://plvr.land.moi.gov.tw/DownloadSeason',
        'retrieval_started_at':'2026-10-08T00:00:00Z','retrieved_at':'2026-10-08T00:01:00Z',
        'download_attempts':1,'http_download':{'status_code':200,
            'final_url':'https://plvr.land.moi.gov.tw/DownloadSeason'}}
    assert t.retrieval_evidence(source,manifest_sha256='c'*64)['quality']=='UNKNOWN'


def test_strict_real_schema_cannot_attest_from_all_whole_details_or_blank_notes():
    b,d=details(); raw=row(**{'交易筆棟數':'土地1建物1車位0'})
    out=module('rights_dwelling').classify(raw,b,d,complete=True,unique=True)
    assert out['rights']=='RIGHTS_UNKNOWN'
    assert out['dwelling']=='DWELLING_UNKNOWN'
    assert out['supplement_valid'] is False


@pytest.mark.parametrize('change',[
    {'full_rights':False},{'one_dwelling':None},{'rights_evidence':None},
    {'parking_evidence':None},{'parking_detail_count':1},
])
def test_cohort_missing_proof_has_exclusion_instead_of_partial_build_failure(change):
    item=candidate(); item['context'].update(change)
    out=module('strict_cohort').build_cohort([item],'2024-09-01T00:00:00Z')
    assert not out['targets'] and len(out['exclusions'])==1


@pytest.mark.parametrize('key,value',[
    ('semantic',{'rights':'RIGHTS_UNKNOWN','dwelling':'DWELLING_UNKNOWN','parking':'UNKNOWN'}),
    ('detail_payload_sha256',{'build':'e'*64,'land':'f'*64}),
    ('area_contract',{'field':'interior','unit':'ping'}),
])
def test_conflicting_semantic_detail_version_is_quarantined_before_tiebreak(key,value):
    first=candidate(); second=deepcopy(first); second['physical_row_number']=2
    second[key]=value
    result=l.select_as_of([first,second],'2024-09-01T00:00:00Z')
    assert not result['selected']
    assert result['excluded_reasons']=={'semantic_evidence_conflict':2}


def test_common_role_cannot_hide_second_native_residential_object():
    raw=row(**{'交易筆棟數':'土地1建物1車位0','建物移轉總面積平方公尺':'110'})
    b,d=details(); b.append({'主要用途':'住家用','移轉情形':'持分移轉','建物移轉面積平方公尺':'10'})
    att=semantic_proof(raw,b,d)
    att['building_objects'].append({'role':'COMMON_ANCILLARY','object_id':'SYNTHETIC-COMMON',
        'unit_id':'SYNTHETIC-UNIT','dwelling_units':0,
        'transferred_fraction':['1','10'],'required_fraction':['1','10']})
    result=module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,supplement=att,scope=semantic_scope())
    assert result['rights']!='FULL_RIGHTS_CONFIRMED'
    assert result['dwelling']!='SINGLE_DWELLING_CONFIRMED'


def test_land_partial_status_cannot_claim_one_over_one_whole_interest():
    b,d=details(); d[0]['移轉情形']='持分移轉'
    assert assess(builds=b,lands=d)['rights']=='RIGHTS_AMBIGUOUS'


def test_single_dwelling_requires_single_consistent_transferred_floor():
    b,d=details(); b[0]['建物分層']='三層,四層'
    assert assess(builds=b,lands=d)['dwelling']!='SINGLE_DWELLING_CONFIRMED'


def test_real_build_does_not_invent_ingestion_instants():
    a=module('audit_semantic_temporal_closure')
    assert hasattr(a,'staging_clocks'), 'explicit logical clock separation required'
    clocks=a.staging_clocks('2026-10-08T06:30:00Z')
    assert clocks['ingested_at'] is None and clocks['transformed_at'] is None
    assert clocks['logical_snapshot_at']=='2026-10-08T06:30:00Z'


def test_explicit_supersession_is_classified_without_changed_id_invention():
    old=occurrence(); new=occurrence(row(**{'總價元':'11000000'}),release='r2',
        available='2024-08-01T00:00:00Z',supersedes_version_id=l.identify(old)['version_id'],
        revision_kind='SUPERSESSION',revision_evidence=proof())
    result=l.select_as_of([old,new],'2024-09-01T00:00:00Z')
    assert result['relations'][0]['classification']=='SUPERSESSION'
    new['raw']['編號']='SYNTHETIC-DIFFERENT'
    assert not l.select_as_of([old,new],'2024-09-01T00:00:00Z')['relations']


def test_supplement_cannot_cross_archive_member_or_occurrence_namespace():
    raw=row(**{'交易筆棟數':'土地1建物1車位0'}); b,d=details()
    att=semantic_proof(raw,b,d)
    for changed in [{'archive_sha256':'b'*64},{'member_name':'a_lvr_land_a.csv'},
                    {'physical_row_number':2},{'schema_sha256':'c'*64}]:
        result=module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,
            supplement=att,scope={**semantic_scope(),**changed})
        assert result['rights']!='FULL_RIGHTS_CONFIRMED'
        assert result['dwelling']!='SINGLE_DWELLING_CONFIRMED'


def test_split_labels_cannot_mature_after_observation_cutoff():
    rows=chronology_rows(); rows[-1]['available_at']='2024-09-29T00:00:00+08:00'
    result=module('chronology').design_splits(rows,coverage_evidence=proof(),ledger_items=chronology_ledger(),
        label_observation_cutoff='2024-09-25T00:00:00+08:00')
    assert not result['viable'] and not result['assignments']
    result=module('chronology').design_splits(chronology_rows(),coverage_evidence=proof(),ledger_items=chronology_ledger(),
        label_observation_cutoff=None)
    assert not result['viable']


def test_split_assignment_retains_version_occurrence_and_freeze():
    result=module('chronology').design_splits(chronology_rows(),coverage_evidence=proof(),ledger_items=chronology_ledger(),
        label_observation_cutoff='2024-10-01T00:00:00+08:00')
    assert result['viable']
    assignment=result['assignments'][0]
    assert {'family_id','source_record_version_id','physical_occurrence_id','block_freeze_at',
            'label_observation_cutoff'}<=assignment.keys()


def test_baseline_must_use_frozen_fit_membership():
    old=candidate(); new=candidate(2)
    history=module('chronology').baseline_history([old,new],prediction_at='2024-09-01T00:00:00Z',
        fitting_cutoff='2024-09-01T00:00:00Z',subject_family='subject',
        fitting_families={l.identify(old)['transaction_family_id']})
    assert len(history)==1 and history[0]['transaction_family_id']==l.identify(old)['transaction_family_id']
    with pytest.raises(ValueError,match='frozen_fit_membership'):
        module('chronology').baseline_history([old,new],prediction_at='2024-09-01T00:00:00Z',
            fitting_cutoff='2024-09-01T00:00:00Z',subject_family='subject',fitting_families=None)


@pytest.mark.parametrize('changes',[
    {'交易筆棟數':'土地1建物2車位0'},{'交易筆棟數':''},
])
def test_raw_building_count_conflict_cannot_bypass_positive_context(changes):
    item=candidate(); item['raw'].update(changes)
    out=module('strict_cohort').build_cohort([item],'2024-09-01T00:00:00Z')
    assert not out['membership'] and out['exclusions']


def test_null_semantic_class_is_a_stable_exclusion():
    item=candidate(); item['semantic']['rights']=None
    out=module('strict_cohort').build_cohort([item],'2024-09-01T00:00:00Z')
    assert out['exclusions'][0]['first_reason']=='RIGHTS_UNKNOWN'


def test_nonempty_synthetic_artifacts_are_deterministic_across_process_environments():
    code="""
from tests.test_ml_semantic_temporal_closure import candidate
from scripts.ml.strict_cohort import build_cohort
from scripts.ml.lineage import canonical_bytes
import sys
items=[candidate(),candidate(2)]
if sys.argv[1]=='reverse': items.reverse()
sys.stdout.buffer.write(canonical_bytes(build_cohort(items,'2024-09-01T00:00:00Z')))
"""
    outputs=[]
    for seed,tz,order in [('11','UTC','normal'),('91','Asia/Taipei','reverse')]:
        result=subprocess.run([sys.executable,'-c',code,order],cwd=s.ROOT,capture_output=True,
            env={**os.environ,'PYTHONUTF8':'1','PYTHONHASHSEED':seed,'TZ':tz})
        assert result.returncode==0,result.stderr.decode('utf-8')
        assert len(json.loads(result.stdout)['membership'])==2
        outputs.append(result.stdout)
    assert outputs[0]==outputs[1]


def test_last_test_month_must_have_completed_by_label_observation_cutoff():
    rows=chronology_rows()
    result=module('chronology').design_splits(rows,coverage_evidence=proof(),ledger_items=chronology_ledger(),
        label_observation_cutoff='2024-09-25T00:00:00+08:00')
    assert not result['viable'] and not result['assignments']
    assert 'INCOMPLETE_TEST_OBSERVATION_PERIOD' in result['blockers']


@pytest.mark.parametrize('field,value',[('object_id',[]),('role',[]),('object_id',1)])
def test_malformed_supplement_object_identity_returns_ambiguity(field,value):
    raw=row(**{'交易筆棟數':'土地1建物1車位0'}); b,d=details()
    att=semantic_proof(raw,b,d); att['building_objects'][0][field]=value
    out=module('rights_dwelling').classify(raw,b,d,complete=True,unique=True,
        supplement=att,scope=semantic_scope())
    assert out['rights']=='RIGHTS_AMBIGUOUS'


def test_split_requires_historical_full_ledger_selection():
    result=module('chronology').design_splits(chronology_rows(),coverage_evidence=proof(),
        label_observation_cutoff='2024-10-01T00:00:00+08:00')
    assert not result['viable']
    assert 'HISTORICAL_MEMBERSHIP_UNPROVEN' in result['blockers']


@pytest.mark.parametrize('kind',['cancellation','correction'])
def test_post_freeze_revision_cannot_change_historical_training_population(kind):
    items=chronology_ledger()
    extra=deepcopy(items[0]); extra['raw']['編號']='SYNTHETIC-EXTRA'; extra['physical_row_number']=421
    items.append(extra)
    new=deepcopy(items[0])
    new.update(release_id='late',archive_sha256='e'*64,
        source_release_available_at='2024-10-15T00:00:00+08:00',
        supersedes_version_id=l.identify(items[0])['version_id'])
    if kind=='cancellation': new['cancelled']=True
    else:
        new['raw']['總價元']='11000000'
        new['raw']['單價元平方公尺']='110000'
    items.append(new)
    c=module('chronology')
    latest=module('strict_cohort').build_cohort(items,'2024-10-20T00:00:00+08:00')
    rows=c.split_rows_from_items(latest['selected_rows'])
    result=c.design_splits(rows,coverage_evidence=proof(),ledger_items=items,
        label_observation_cutoff='2024-10-20T00:00:00+08:00')
    assert not result['viable'] and not result['assignments']
    assert 'HISTORICAL_MEMBERSHIP_DIFFERS' in result['blockers']
