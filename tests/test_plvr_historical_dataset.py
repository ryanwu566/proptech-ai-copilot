"""Small synthetic fixtures only; no serving DB, provider or real source writes."""
import csv
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import zipfile

import pytest


def engine():
    assert importlib.util.find_spec('services.plvr_historical_dataset') is not None, 'historical builder is required'
    return importlib.import_module('services.plvr_historical_dataset')


def row(serial='RP00000000000000001', **changes):
    value={'鄉鎮市區':'新莊區','交易標的':'房地(土地+建物)',
      '土地位置建物門牌':'新北市新莊區中正路100號三樓','交易年月日':'1130115',
      '交易筆棟數':'土地1建物1車位0','移轉層次':'三層','總樓層數':'五層',
      '建物型態':'公寓(5樓含以下無電梯)','主要用途':'住家用','建築完成年月':'1030101',
      '建物移轉總面積平方公尺':'100','總價元':'10000000','單價元平方公尺':'100000',
      '車位類別':'','車位移轉總面積(平方公尺)':'0','車位總價元':'0','備註':'','編號':serial}
    value.update(changes);return value


def source(root, releases, descriptor=True):
    (root/'00_manifest').mkdir(parents=True)
    (root/'01_raw_zip').mkdir()
    fields=list(row());manifest=[]
    for season, rows in releases:
        buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=fields);w.writeheader()
        # Production recognizes this official English descriptor row.
        if descriptor:
            english={k:'english field description' for k in fields}
            english.update({'鄉鎮市區':'The villages and towns urban district','交易標的':'transaction sign',
                '交易年月日':'transaction year month and day','編號':'serial number','總價元':'total price NTD'})
            w.writerow(english)
        for item in rows:w.writerow(item)
        members={'f_lvr_land_a.csv':buf.getvalue().encode('utf-8-sig'),
                 'schema-main.csv':b'field,description\npublic,public\n',
                 'f_lvr_land_b.csv':b'presale,ignored\n'}
        archive=root/'01_raw_zip'/f'plvr_{season}_lvr_landcsv.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,body in members.items():
                info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,body)
                target=root/'02_extracted'/season/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        raw=archive.read_bytes()
        manifest.append({'Season':season,'Filename':archive.name,'Bytes':len(raw),'Entries':len(members),
                         'Sale_A':1,'SHA256':hashlib.sha256(raw).hexdigest(),'Status':'PASS'})
    with (root/'00_manifest/plvr_10y_40q_manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(manifest[0]));w.writeheader();w.writerows(manifest)
    return root


def build(tmp_path, releases, name='out'):
    root=source(tmp_path/'source',releases)
    result=engine().build_dataset(root,tmp_path/name,as_of='2026-10-29',expected_releases=len(releases),county_codes=('f',))
    return root,result


def test_repeated_release_is_one_transaction_with_all_provenance(tmp_path):
    _,result=build(tmp_path,[('113S1',[row()]),('113S2',[row()])])
    assert result['counts']['raw_sale_rows']==2
    assert result['counts']['canonical_identities']==1
    assert result['counts']['clean_transactions']==1
    assert result['counts']['duplicate_occurrences_removed']==1
    artifact=Path(result['artifact_dir'])
    with sqlite3.connect(f'file:{artifact / "lineage.sqlite"}?mode=ro',uri=True) as db:
        assert db.execute('select count(*) from occurrences').fetchone()==(2,)
        assert db.execute('select count(*) from clean_transactions').fetchone()==(1,)
    assert result['training_authorized'] is False


def test_related_party_note_cannot_be_laundered_by_later_blank_revision(tmp_path):
    noted=row('RPWNMLNKNHLGFBF78EA',備註='親友、員工、共有人或其他特殊關係間之交易；')
    _,r=build(tmp_path,[('113S1',[noted]),('113S2',[row('RPWNMLNKNHLGFBF78EA')])])
    assert r['counts']['clean_transactions']==0
    assert r['known_special_serial']['excluded'] is True
    assert r['exclusions_by_reason']['known_related_party_serial']==1


def test_conflicting_revision_is_quarantined_not_latest_wins(tmp_path):
    _,r=build(tmp_path,[('113S1',[row()]),('113S2',[row(總價元='9000000',單價元平方公尺='90000')])])
    assert r['counts']['canonical_identities']==1 and r['counts']['clean_transactions']==0
    assert r['counts']['conflicting_identity_groups']==1
    assert r['exclusions_by_reason']['ambiguous_revision']==1


def test_ambiguous_note_fact_matches_protect_all_ids(tmp_path):
    _,r=build(tmp_path,[('113S1',[row(),row('RP00000000000000002',備註='特殊關係交易')])])
    assert r['counts']['clean_transactions']==0
    assert r['exclusions_by_reason']['ambiguous_special_note_match']==1
    assert r['exclusions_by_reason']['special_note_requires_review']==1


def test_exact_future_day_invalid_dates_demo_and_missing_serial_excluded(tmp_path):
    values=[row(),row('RP00000000000000002',交易年月日='1151030'),
            row('RP00000000000000003',交易年月日='1130230'),row('DEMO00000000000001'),row('')]
    _,r=build(tmp_path,[('113S1',values)])
    assert r['counts']['raw_sale_rows']==5 and r['counts']['clean_transactions']==1
    assert r['raw_quality_reasons']['future_transaction_date']==1
    assert r['raw_quality_reasons']['invalid_transaction_day']==1
    assert r['counts']['unidentified_occurrences']==2


def test_corrupt_extracted_copy_fails_closed_no_complete_marker(tmp_path):
    root=source(tmp_path/'source',[('113S1',[row()])])
    (root/'02_extracted/113S1/f_lvr_land_a.csv').write_bytes(b'altered')
    with pytest.raises(ValueError,match='extracted_member_mismatch'):
        engine().build_dataset(root,tmp_path/'out',as_of='2026-10-29',expected_releases=1,county_codes=('f',))
    assert not list((tmp_path/'out').rglob('COMPLETE.json'))


def test_output_under_source_refused_and_source_never_modified(tmp_path):
    root=source(tmp_path/'source',[('113S1',[row()])])
    before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='unsafe_output'):
        engine().build_dataset(root,root/'out',as_of='2026-10-29',expected_releases=1,county_codes=('f',))
    engine().build_dataset(root,tmp_path/'out',as_of='2026-10-29',expected_releases=1,county_codes=('f',))
    after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    assert before==after


def test_rebuild_hash_is_stable_across_source_roots_and_output_paths(tmp_path):
    root=source(tmp_path/'one',[('113S1',[row()]),('113S2',[row()])])
    second=tmp_path/'two';shutil.copytree(root,second)
    first=engine().build_dataset(root,tmp_path/'out1',as_of='2026-10-29',expected_releases=2,county_codes=('f',))
    other=engine().build_dataset(second,tmp_path/'out2',as_of='2026-10-29',expected_releases=2,county_codes=('f',))
    assert first['dataset_fingerprint']==other['dataset_fingerprint']
    assert first['dataset_gzip_sha256']==other['dataset_gzip_sha256']
    assert first['logical_dataset_sha256']==other['logical_dataset_sha256']
    assert engine().verify_artifact(Path(first['artifact_dir']))['status']=='PASS'


def test_integrity_verifier_detects_dataset_corruption(tmp_path):
    _,r=build(tmp_path,[('113S1',[row()])])
    path=Path(r['artifact_dir'])/'transactions.jsonl.gz'
    path.chmod(0o600);path.write_bytes(path.read_bytes()[:-10])
    with pytest.raises(ValueError):engine().verify_artifact(Path(r['artifact_dir']))


@pytest.mark.parametrize('output',[
 '/run/media/andy/Crucial X9','/run/media/andy/Crucial X9/ml-output',
 '/run/media/andy/Crucial X9/DB/new','/srv/proptech-data','/srv/proptech-data/other',
 '/home/andy/proptech-ai-copilot/reports/out','/dev','/dev/forbidden-target'])
def test_entire_source_mount_serving_root_and_main_tree_are_write_forbidden(output):
    with pytest.raises(ValueError,match='unsafe_output'):
        engine().validate_output(Path('/some/source'),Path(output))


def test_unidentified_special_note_still_taints_matching_valid_identity(tmp_path):
    _,r=build(tmp_path,[('113S1',[row(),row('',備註='特殊關係交易')])])
    assert r['counts']['clean_transactions']==0
    assert r['exclusions_by_reason']['ambiguous_special_note_match']==1
    assert r['unidentified_exclusions_by_reason']['missing_official_serial']==1


def test_note_matching_normalizes_width_and_whitespace_without_legacy_key(tmp_path):
    noted=row('RP00000000000000002',備註='特殊關係交易',土地位置建物門牌='新北市新莊區中正路１００號 三樓')
    _,r=build(tmp_path,[('113S1',[row(),noted])])
    assert r['counts']['clean_transactions']==0
    assert r['exclusions_by_reason']['ambiguous_special_note_match']==1


@pytest.mark.parametrize('variant',['3層','三層','３層'])
def test_equivalent_floor_does_not_split_special_note_taint(tmp_path,variant):
    _,r=build(tmp_path,[('113S1',[row(),row('RP00000000000000002',備註='特殊關係交易',移轉層次=variant)])])
    assert r['counts']['clean_transactions']==0
    assert r['exclusions_by_reason']['ambiguous_special_note_match']==1


@pytest.mark.parametrize('as_of',['20261029','2026-W44-4'])
def test_as_of_alternative_iso_forms_cannot_admit_future_days(tmp_path,as_of):
    root=source(tmp_path/'source',[('113S1',[row(交易年月日='1151030')])])
    r=engine().build_dataset(root,tmp_path/'out',as_of=as_of,expected_releases=1,county_codes=('f',))
    assert r['as_of']=='2026-10-29'
    assert r['counts']['clean_transactions']==0
    assert r['raw_quality_reasons']['future_transaction_date']==1


def test_missing_descriptor_cannot_discard_a_first_related_party_record(tmp_path):
    values=[row('RPABC00000000000001',備註='special related-party sale',土地位置建物門牌='新北市新莊區中正路ABC100號三樓'),
            row('RPABC00000000000001')]
    root=source(tmp_path/'source',[('113S1',values)],descriptor=False)
    with pytest.raises(ValueError,match='english_descriptor_missing'):
        engine().build_dataset(root,tmp_path/'out',as_of='2026-10-29',expected_releases=1,county_codes=('f',))
    assert not list((tmp_path/'out').rglob('COMPLETE.json'))


def test_completion_later_in_same_month_is_unknown_age():
    result=engine().row_evidence(row(建築完成年月='1130131'),'f','2026-10-29')
    assert result['features']['building_age_months_at_transaction'] is None


@pytest.mark.parametrize('case',['future','arithmetic','source_locator','training','availability','raw_address'])
def test_semantic_integrity_guards_reject_rehashed_but_invalid_records(tmp_path,case):
    import gzip
    _,result=build(tmp_path,[('113S1',[row()])])
    folder=Path(result['artifact_dir']);schema=json.loads((folder/'schema.json').read_text())
    manifest=json.loads((folder/'provenance-manifest.json').read_text())
    files={x['file_id']:x for x in manifest['members']}
    with gzip.open(folder/'transactions.jsonl.gz','rt') as stream:value=json.loads(next(stream))
    if case=='future':value.update(transaction_date='2026-10-30',transaction_period='2026-10')
    elif case=='arithmetic':value['gross_unit_price_ntd_ping']='1'
    elif case=='source_locator':value['provenance']['record_number']=9999999
    elif case=='training':value['training_authorized']=True
    elif case=='availability':value['source_release_available_at']='2024-01-01T00:00:00Z'
    elif case=='raw_address':value['address_text']='synthetic-private-address'
    with pytest.raises(ValueError):engine()._validate_record(value,schema,files,'2026-10-29')


@pytest.mark.parametrize('price',[-1,0,float('nan'),float('inf')])
def test_independent_verifier_rejects_invalid_production_unit_prices(tmp_path,price):
    import gzip
    _,result=build(tmp_path,[('113S1',[row()])]);folder=Path(result['artifact_dir'])
    schema=json.loads((folder/'schema.json').read_text());manifest=json.loads((folder/'provenance-manifest.json').read_text())
    with gzip.open(folder/'transactions.jsonl.gz','rt') as stream:value=json.loads(next(stream))
    value['production_unit_price_wan_ping']=price
    with pytest.raises(ValueError,match='production_price_invariant'):
        engine()._validate_record(value,schema,{x['file_id']:x for x in manifest['members']},'2026-10-29')


@pytest.mark.parametrize('table',['occurrences','dispositions','identity_stats','fact_stats'])
def test_independent_verifier_rejects_orphan_clean_provenance(tmp_path,table):
    _,result=build(tmp_path,[('113S1',[row()])]);folder=Path(result['artifact_dir']);folder.chmod(0o700)
    dbpath=folder/'lineage.sqlite';dbpath.chmod(0o600)
    with sqlite3.connect(dbpath) as db:db.execute('delete from '+table)
    summary=json.loads((folder/'summary.json').read_text())
    summary['artifact_hashes']['lineage.sqlite']=hashlib.sha256(dbpath.read_bytes()).hexdigest()
    summarypath=folder/'summary.json';summarypath.chmod(0o600);summarypath.write_bytes(engine().canonical(summary)+b'\n')
    completepath=folder/'COMPLETE.json';complete=json.loads(completepath.read_text());completepath.chmod(0o600)
    complete['summary_sha256']=hashlib.sha256(summarypath.read_bytes()).hexdigest();completepath.write_bytes(engine().canonical(complete)+b'\n')
    with pytest.raises(ValueError):engine().verify_artifact(folder)
