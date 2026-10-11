"""ML-0 receipt tests. All positive proof material is synthetic and temporary."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json

import pytest

from scripts.ml import historical as h, lineage as l, semantics as s
from tests.test_ml_target_reframing import item, CUTOFF


def module():
    return importlib.import_module('scripts.ml.external_evidence')


def receipt(tmp_path, kind='HistoricalPublicationReceipt'):
    body = b'SYNTHETIC official proof fixture; never historical evidence'
    (tmp_path / 'proof.txt').write_bytes(body)
    x = item()
    common = dict(contract_version='ml-external-evidence-v1', receipt_type=kind,
        receipt_id='synthetic-receipt', source_authority='MOI_LAND',
        official_url='https://plvr.land.moi.gov.tw/synthetic',
        retained_path='proof.txt', evidence_sha256=sha256(body).hexdigest(),
        evidence_bytes=len(body), retrieved_at='2026-10-11T00:00:00+08:00',
        published_at='2024-07-01T00:00:00+08:00', effective_at='2024-07-01T00:00:00+08:00',
        scope={'dataset_id': s.SOURCE_DATASET_ID, 'county_codes': ['a', 'f'],
               'release_ids': [x['release_id']]}, version='synthetic-v1',
        limitations=['SYNTHETIC ONLY'], synthetic=True, privacy='NON_PERSONAL',
        license={'status': 'RESEARCH_ALLOWED', 'terms_url': 'https://data.gov.tw/licenses',
                 'reuse_scope': 'RESEARCH_ONLY'},
        verification={'status': 'REVIEWED_AUTHORITY', 'reviewer_role': 'DATA_STEWARD',
                      'basis': 'SYNTHETIC reviewer exercise, no real attestation'})
    if kind == 'HistoricalPublicationReceipt':
        common.update(release_id=x['release_id'], archive_sha256=x['archive_sha256'],
            proof_class='AUTHENTICATED_HISTORICAL', exact_byte_publication_binding=True,
            time_quality='EXACT_PUBLICATION_TIME', original_filename='synthetic.zip',
            immutable_version_id='synthetic-official-version')
    elif kind == 'TransactionNamespaceAuthority':
        common.update(identifier_field='編號', stable_across_releases=True,
            correction_key_policy='PRESERVE', cancellation_key_policy='TOMBSTONE',
            replacement_key_policy='EXPLICIT_MAPPING', serial_reuse_policy='NO_REUSE',
            ambiguous=False)
    elif kind == 'TransactionLineageReceipt':
        common.update(cutoff=CUTOFF, visible_ledger_sha256='a'*64,
            complete_revision_history=True, complete_cancellation_history=True,
            replacement_links_complete=True, events=[])
    else:
        common.update(occurrence_id=l.identify(x)['occurrence_id'],
            main_sha256=l.digest(x['raw']), build_sha256=l.digest(x['details']['build']),
            land_sha256=l.digest(x['details']['land']),
            mapping_scope={'archive_sha256':x['archive_sha256'], 'member_name':x['member_name'],
                'physical_row_number':x['physical_row_number'], 'schema_sha256':x['context']['schema_evidence']['sha256']},
            registered_unit_count=1, building_objects=[], land_interests=[])
    return common


def test_valid_fixture_checks_bytes_but_cannot_enter_real_ingestion(tmp_path):
    r = receipt(tmp_path)
    assert module().validate_receipt(r, tmp_path, synthetic_test=True)['valid']
    assert 'SYNTHETIC_NOT_REAL_EVIDENCE' in module().validate_receipt(r, tmp_path)['reasons']


@pytest.mark.parametrize('change,reason', [
    ({'published_at': None}, 'PUBLICATION_TIME_REQUIRED'),
    ({'effective_at': '2024-01-01'}, 'EFFECTIVE_TIME_REQUIRED'),
    ({'evidence_sha256': 'z'*64}, 'EVIDENCE_HASH_INVALID'),
    ({'evidence_sha256': 'f'*64}, 'RETAINED_BYTES_MISMATCH'),
    ({'proof_class': 'CURRENT_ONLY'}, 'HISTORICAL_PUBLICATION_UNPROVEN'),
    ({'exact_byte_publication_binding': False}, 'HISTORICAL_PUBLICATION_UNPROVEN'),
    ({'license': {'status': 'UNKNOWN'}}, 'LICENSE_UNPROVEN'),
    ({'verification': {'status': 'UNREVIEWED'}}, 'AUTHORITY_UNREVIEWED'),
    ({'retained_path': '../proof.txt'}, 'RETAINED_PATH_INVALID'),
    ({'official_url': 'https://plvr.land.moi.gov.tw.evil.test/'}, 'OFFICIAL_SOURCE_INVALID'),
    ({'scope': {'dataset_id': 'wrong'}}, 'SCOPE_INVALID'),
    ({'privacy': 'PERSONAL'}, 'PERSONAL_DATA_FORBIDDEN'),
])
def test_fail_closed(tmp_path, change, reason):
    r = receipt(tmp_path); r.update(change)
    result = module().validate_receipt(r, tmp_path, synthetic_test=True)
    assert not result['valid'] and reason in result['reasons']


def test_path_symlink_outside_root_is_rejected(tmp_path):
    r = receipt(tmp_path); r['retained_path'] = str(tmp_path / 'proof.txt')
    assert not module().validate_receipt(r, tmp_path, synthetic_test=True)['valid']


@pytest.mark.parametrize('field,value', [('ambiguous', True), ('stable_across_releases', False),
    ('correction_key_policy', 'UNKNOWN'), ('serial_reuse_policy', 'UNKNOWN')])
def test_ambiguous_or_unknown_namespace(tmp_path, field, value):
    r = receipt(tmp_path, 'TransactionNamespaceAuthority'); r[field] = value
    assert not module().validate_receipt(r, tmp_path, synthetic_test=True)['valid']


def test_unknown_lineage_is_not_complete_history(tmp_path):
    r = receipt(tmp_path, 'TransactionLineageReceipt'); r['complete_cancellation_history'] = False
    assert not module().validate_receipt(r, tmp_path, synthetic_test=True)['valid']


@pytest.mark.parametrize('event_kind', ['CANCELLATION', 'REPLACEMENT'])
def test_event_requires_explicit_predecessor_and_timestamp(tmp_path, event_kind):
    r = receipt(tmp_path, 'TransactionLineageReceipt')
    r['events'] = [{'event_kind': event_kind, 'version_id': 'b'*64}]
    assert not module().validate_receipt(r, tmp_path, synthetic_test=True)['valid']


def test_multi_portion_requires_object_roles_and_registered_units(tmp_path):
    r = receipt(tmp_path, 'RightsUnitMappingReceipt')
    assert not module().validate_receipt(r, tmp_path, synthetic_test=True)['valid']


def test_unknown_keys_cannot_hide_personal_fields(tmp_path):
    r = receipt(tmp_path); r['owner_name'] = 'fixture'
    assert 'UNDECLARED_FIELDS' in module().validate_receipt(r, tmp_path, synthetic_test=True)['reasons']


def test_receipts_do_not_mutate_or_manufacture_evidence(tmp_path):
    x = item(); original = deepcopy(x)
    enriched, certificates, coverage, diagnostics = module().ingest([x], [], tmp_path)
    assert x == original
    assert h.data_gate(enriched, CUTOFF, history_certificate=certificates,
                       coverage_evidence=coverage, pit_v3=True)['counts']['PIT_valid'] == 0
    assert diagnostics['accepted_receipts'] == 0


def test_synthetic_bundle_is_rejected_as_a_whole_in_real_mode(tmp_path):
    enriched, cert, _, result = module().ingest([item()], [receipt(tmp_path)], tmp_path)
    assert cert is None and result['accepted_receipts'] == 0
    assert h.publication(enriched[0])['available_at'] is None


def test_capture_accepts_only_explicit_official_https_urls():
    acquire = importlib.import_module('scripts.ml.acquire_external_metadata')
    assert acquire.official_url('https://www.nlsc.gov.tw/cp.aspx?n=16739')
    for url in ['http://plvr.land.moi.gov.tw/', 'https://gov.tw.evil.test/',
                'https://user:secret@plvr.land.moi.gov.tw/', 'https://localhost/']:
        assert not acquire.official_url(url)


def test_admission_policy_retains_existing_minima_and_both_cities():
    policy = module().admission_policy()
    assert policy['minimum_pit_rows'] == 840
    assert policy['minimum_contiguous_months'] == 21
    assert policy['block_months'] == {'TRAIN':12, 'VALIDATION':3, 'CALIBRATION':3, 'TEST':3}
    assert policy['minimum_city_month_rows'] == 20
    assert not module().admission([], {'chronology': {'viable':False}},
        privacy=True, deterministic=True)['may_begin']


@pytest.mark.parametrize('field,value', [('scope',{'county_codes':[[1]],'release_ids':[{}]}),
    ('source_authority', []), ('proof_class', []), ('license', []), ('verification', []),
    ('events', [None]), ('evidence_bytes', True)])
def test_malformed_receipt_returns_rejection_without_exception(tmp_path, field, value):
    r = receipt(tmp_path); r[field] = value
    assert not module().validate_receipt(r,tmp_path,synthetic_test=True)['valid']


def test_schema_has_only_supported_availability_precision():
    from scripts.ml import temporal as t
    schema=json.loads(module().SCHEMA_PATH.read_text(encoding='utf-8'))
    quality=schema['$defs']['HistoricalPublicationReceipt']['properties']['time_quality']['enum']
    assert set(quality) <= t.QUALITIES


def test_real_refresh_empty_receipts_preserves_zero_and_is_idempotent(tmp_path):
    refresh=importlib.import_module('scripts.ml.refresh_external_evidence')
    report=refresh.refresh([item()], [], tmp_path, CUTOFF)
    assert report['counts']['PIT_valid']==0 and report['counts']['approved_training']==0
    assert report['ml_b_admission']['may_begin'] is False
    assert l.canonical_bytes(report)==l.canonical_bytes(refresh.refresh([item()],[],tmp_path,CUTOFF))


def test_real_refresh_never_accepts_a_caller_synthetic_override():
    refresh=importlib.import_module('scripts.ml.refresh_external_evidence')
    with pytest.raises(TypeError):
        refresh.refresh([],[],None,CUTOFF,synthetic_test=True)


def bundle(tmp_path, xs, cutoff=CUTOFF, kinds=None):
    """Synthetic provider/reviewer binding exercise, not acquired authority."""
    m=module(); pubs=[]; releases=sorted({x['release_id'] for x in xs})
    for index,x in enumerate(xs):
        r=receipt(tmp_path); r.update(receipt_id=f'pub-{index}',release_id=x['release_id'],
            archive_sha256=x['archive_sha256'],published_at=x['source_release_available_at'])
        r['scope']['release_ids']=releases
        if not any(p['release_id']==r['release_id'] for p in pubs): pubs.append(r)
    ns=receipt(tmp_path,'TransactionNamespaceAuthority'); ns['receipt_id']='namespace'
    ns['scope']['release_ids']=releases
    enriched,_,_,result=m.ingest(xs,pubs+[ns],tmp_path,synthetic_test=True)
    assert result['accepted_receipts']==len(pubs)+1
    lr=receipt(tmp_path,'TransactionLineageReceipt'); lr.update(receipt_id='lineage',cutoff=cutoff)
    lr['scope']['release_ids']=releases
    kinds=kinds or ['ORIGINAL']*len(xs)
    expected=deepcopy(enriched)
    for index,(x,kind) in enumerate(zip(expected,kinds)):
        x['cancelled']=kind=='CANCELLATION'; x['cancellation_state_evidenced']=True
        previous=l.identify(expected[index-1])['version_id'] if index else None
        x['supersedes_version_id']=previous
        if kind in {'REVISION','CANCELLATION','REPLACEMENT'}:
            x['revision_kind']={'REVISION':'CORRECTION','CANCELLATION':'CANCELLATION','REPLACEMENT':'SUPERSESSION'}[kind]
            x['revision_evidence']=m.reference(lr)
        replaced=l.identify(expected[0])['transaction_family_id'] if kind=='REPLACEMENT' else None
        if replaced: x['replaces_family_id']=replaced
        lr['events'].append(dict(event_kind=kind,occurrence_id=l.identify(x)['occurrence_id'],
            version_id=l.identify(x)['version_id'],previous_version_id=previous,
            later_version_id=l.identify(x)['version_id'],release_id=x['release_id'],
            archive_sha256=x['archive_sha256'],effective_at=xs[index]['source_release_available_at'],
            published_at=xs[index]['source_release_available_at'],cancelled=x['cancelled'],
            replaces_family_id=replaced,reason_public=None,duplicate_of_occurrence_id=None))
    visible=[x for x in expected if h.publication(x)['available_at']
             and l.timestamp(h.publication(x)['available_at'])<=l.timestamp(cutoff)]
    lr['visible_ledger_sha256']=h.ledger_digest(visible)
    return pubs+[ns,lr]


def test_valid_synthetic_bundle_runs_the_existing_pit_gate(tmp_path):
    xs=[item()]; receipts=bundle(tmp_path,xs)
    enriched,cert,coverage,result=module().ingest(xs,receipts,tmp_path,synthetic_test=True)
    assert result['accepted_receipts']==3
    gate=h.data_gate(enriched,CUTOFF,history_certificate=cert,coverage_evidence=coverage,pit_v3=True)
    assert gate['counts']['PIT_valid']==1
    assert gate['counts']['approved_training']==0
    assert gate['target_a']=='BLOCKED'


@pytest.mark.parametrize('kind', ['REVISION','CANCELLATION','REPLACEMENT'])
def test_later_event_cannot_leak_into_earlier_freeze(tmp_path,kind):
    x=item(); y=deepcopy(x)
    y.update(release_id='synthetic-later',archive_sha256='d'*64,
             source_release_available_at='2024-09-01T00:00:00+08:00')
    y['raw']['總價元']='11000000'
    y['raw']['單價元平方公尺']='110000'
    if kind=='REPLACEMENT': y['raw']['編號']='SYNTHETIC-NEW-KEY'
    for cutoff,expected in [(CUTOFF,1),('2024-10-01T00:00:00+08:00',0 if kind!='REVISION' else 1)]:
        rs=bundle(tmp_path,[x,y],cutoff,kinds=['ORIGINAL',kind])
        enriched,cert,_,diagnostics=module().ingest([x,y],rs,tmp_path,synthetic_test=True)
        assert diagnostics['accepted_receipts']==4
        result=h.select_pit_v3(enriched,cutoff,history_certificate=cert)
        assert len(result['selected'])==expected
        if cutoff==CUTOFF: assert result['selected'][0]['raw']['總價元']=='10000000'


def test_missing_event_cannot_resurrect_a_cancelled_predecessor(tmp_path):
    xs=[item()]; rs=bundle(tmp_path,xs); rs[-1]['events']=[]
    enriched,cert,_,result=module().ingest(xs,rs,tmp_path,synthetic_test=True)
    assert cert is None and result['accepted_receipts']==0
    assert h.select_pit_v3(enriched,CUTOFF,history_certificate=cert)['selected']==[]


def test_wrong_ledger_certificate_and_duplicate_receipts_revoke_bundle(tmp_path):
    rs=bundle(tmp_path,[item()]); rs[-1]['visible_ledger_sha256']='f'*64
    assert module().ingest([item()],rs,tmp_path,synthetic_test=True)[1] is None
    rs=bundle(tmp_path,[item()]); rs.append(deepcopy(rs[0]))
    assert module().ingest([item()],rs,tmp_path,synthetic_test=True)[1] is None


def test_expanded_release_staging_requires_explicit_bounded_inventory():
    from scripts.ml import audit_target_reframing as staging
    for releases in [(), ('112S3','112S3'), tuple(f'{year}S1' for year in range(90,120))]:
        with pytest.raises(ValueError,match='bounded_release_scope'):
            staging.stage_sources({},[],'2026-10-11T00:00:00+08:00',required_releases=releases)


def test_matching_reports_cannot_self_certify_ml_b_without_fresh_sources(tmp_path):
    refresh=importlib.import_module('scripts.ml.refresh_external_evidence')
    report=refresh.refresh([item()],[],tmp_path,CUTOFF)
    report['ml_b_admission']['conditions']={k:True for k in report['ml_b_admission']['conditions']}
    report['existing_gate']['eligible_before_independent_determinism']=99999
    first,second=tmp_path/'first.json',tmp_path/'second.json'
    for p in (first,second): p.write_bytes(l.canonical_bytes(report)+b'\n')
    assert refresh.verify(first,second)['may_ml_b_begin'] is False
    assert refresh.verify(first,second)['approved_cohort']==0


def test_verification_rejects_report_that_differs_from_fresh_receipt_gate(tmp_path):
    refresh=importlib.import_module('scripts.ml.refresh_external_evidence')
    report=refresh.refresh([item()],[],tmp_path,CUTOFF)
    report['counts']['PIT_valid']=10
    first,second=tmp_path/'first.json',tmp_path/'second.json'
    for p in (first,second): p.write_bytes(l.canonical_bytes(report)+b'\n')
    with pytest.raises(ValueError,match='fresh_source'):
        refresh.verify(first,second,items=[item()],receipts=[],evidence_root=tmp_path)


def test_fresh_verification_binds_cli_recovery_manifest_metadata(tmp_path):
    refresh=importlib.import_module('scripts.ml.refresh_external_evidence')
    report=refresh.refresh([item()],[],tmp_path,CUTOFF)
    report['inputs']['source_recovery_manifest_sha256']='a'*64
    first,second=tmp_path/'first.json',tmp_path/'second.json'
    for p in (first,second): p.write_bytes(l.canonical_bytes(report)+b'\n')
    verified=refresh.verify(first,second,items=[item()],receipts=[],evidence_root=tmp_path,
        recovery_manifest_sha256='a'*64)
    assert verified['conditions']['fresh_sources_revalidated'] is True
    assert verified['may_ml_b_begin'] is False and verified['approved_cohort']==0
    with pytest.raises(ValueError,match='fresh_source'):
        refresh.verify(first,second,items=[item()],receipts=[],evidence_root=tmp_path,
            recovery_manifest_sha256='b'*64)


def test_rights_mapping_passes_roles_and_cannot_backdate_late_supplement(tmp_path):
    from tests.test_ml_semantic_temporal_closure import details
    x=item(); builds,lands=details()
    x['details']['build']=builds; x['details']['land']=lands
    x['raw']['交易筆棟數']='土地1建物1車位0'
    r=receipt(tmp_path,'RightsUnitMappingReceipt')
    r.update(receipt_id='rights',main_sha256=l.digest(x['raw']),build_sha256=l.digest(builds),
        land_sha256=l.digest(lands))
    r['building_objects']=[{'object_id':'SYNTHETIC-UNIT','role':'PRIVATE_DWELLING','dwelling_units':1,
        'unit_id':'SYNTHETIC-UNIT','transferred_fraction':['1','1'],'required_fraction':['1','1']}]
    r['land_interests']=[{'unit_id':'SYNTHETIC-UNIT','required_fraction':['1','1']}]
    assert module().validate_receipt(r,tmp_path,synthetic_test=True)['valid']
    enriched,_,_,diagnostics=module().ingest([x],[r],tmp_path,synthetic_test=True)
    assert diagnostics['accepted_receipts']==1
    assert enriched[0]['semantic']['rights']=='FULL_RIGHTS_CONFIRMED'
    assert enriched[0]['semantic']['dwelling']=='SINGLE_DWELLING_CONFIRMED'
    assert h.dependencies_available(enriched[0],CUTOFF)
    r['published_at']='2024-09-01T00:00:00+08:00'
    enriched,_,_,_=module().ingest([x],[r],tmp_path,synthetic_test=True)
    assert not h.dependencies_available(enriched[0],CUTOFF)


def test_unreviewed_staged_dependency_is_not_erased_and_cannot_enter_pit(tmp_path):
    x=item(); rs=bundle(tmp_path,[x])
    x['required_source_dependencies']=[{'source_id':'synthetic-future','sha256':'e'*64,
        'publication_evidence':{'classification':'AUTHENTICATED','release_id':'synthetic-future',
            'archive_sha256':'e'*64,'quality':'EXACT_PUBLICATION_TIME',
            'value':'2025-01-01T00:00:00+08:00','evidence':{'sha256':'b'*64,'locator':'synthetic','version':'1'}}}]
    enriched,cert,_,result=module().ingest([x],rs,tmp_path,synthetic_test=True)
    assert enriched[0]['required_source_dependencies']==x['required_source_dependencies']
    assert cert is None and result['accepted_receipts']==0
    assert h.select_pit_v3(enriched,CUTOFF,history_certificate=cert)['selected']==[]


def test_duplicate_release_keeps_same_version_without_supersession(tmp_path):
    x=item(); y=deepcopy(x)
    y.update(release_id='synthetic-repeat',archive_sha256='d'*64,
             source_release_available_at='2024-07-11T00:00:00+08:00')
    rs=bundle(tmp_path,[x,y],kinds=['ORIGINAL','ORIGINAL'])
    lr=rs[-1]; event=lr['events'][1]
    event.update(event_kind='DUPLICATE_RELEASE',previous_version_id=None,
                 duplicate_of_occurrence_id=l.identify(x)['occurrence_id'])
    # The duplicate does not change version lineage, including its true parent.
    preliminary,_,_,_=module().ingest([x,y],rs[:-1],tmp_path,synthetic_test=True)
    for row in preliminary: row['cancellation_state_evidenced']=True
    lr['visible_ledger_sha256']=h.ledger_digest(preliminary)
    enriched,cert,_,result=module().ingest([x,y],rs,tmp_path,synthetic_test=True)
    assert result['accepted_receipts']==4
    selected=h.select_pit_v3(enriched,CUTOFF,history_certificate=cert)
    assert len(selected['selected'])==1


def test_unbound_duplicate_reference_fails_closed(tmp_path):
    rs=bundle(tmp_path,[item()]); rs[-1]['events'][0].update(event_kind='DUPLICATE_RELEASE',
        previous_version_id=None,duplicate_of_occurrence_id='f'*64)
    assert module().ingest([item()],rs,tmp_path,synthetic_test=True)[1] is None
