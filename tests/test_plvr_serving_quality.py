from pathlib import Path
import sqlite3

from services.plvr_serving_quality import PlvrQualityReconciler, serving_relation


def fact(**changes):
    row = dict(id=38652, source='official_plvr_opendata', city='新北市', district='新莊區',
               transaction_period='2026-05', road='中華路一段',
               address_text='新北市新莊區中華路一段６３巷６號二樓',
               building_type='華廈(10層含以下有電梯)', area_ping=34.06,
               total_price=345.59, unit_price_per_ping=10.15, floor=2)
    return {**row, **changes}


def reconciler(tmp_path):
    return PlvrQualityReconciler(tmp_path/'private.sqlite', as_of='2026-10')


def test_known_special_maps_uniquely_without_dedupe_key(tmp_path):
    r = reconciler(tmp_path)
    r.add_serving(fact(dedupe_key='old-import-key'))
    r.add_raw(fact(dedupe_key='different-official-key'), official_id='RPWNMLNKNHLGFBF78EA',
              has_note=True, source_file='115S2/f_lvr_land_a.csv', source_row=42)
    rows = list(r.classifications())
    assert len(rows) == 1
    assert rows[0]['classification'] == 'UNIQUE_MATCH'
    assert rows[0]['serving_transaction_id'] == 38652
    assert 'address_text' not in rows[0]


def test_same_facts_different_serving_rows_are_ambiguous(tmp_path):
    r = reconciler(tmp_path)
    r.add_serving(fact())
    r.add_serving(fact(id=2))
    r.add_raw(fact(), official_id='A', has_note=True)
    assert next(r.classifications())['classification'] == 'MULTIPLE_MATCH'


def test_same_facts_different_official_ids_are_ambiguous(tmp_path):
    r = reconciler(tmp_path)
    r.add_serving(fact())
    for serial in ['A', 'B']:
        r.add_raw(fact(), official_id=serial, has_note=True)
    assert {v['classification'] for v in r.classifications()} == {'MULTIPLE_MATCH'}


def test_repeated_release_is_one_evidence_group(tmp_path):
    r = reconciler(tmp_path)
    r.add_serving(fact())
    for _ in range(3):
        r.add_raw(fact(), official_id='A', has_note=True)
    rows = list(r.classifications())
    assert len(rows) == 1
    assert rows[0]['occurrences'] == 3
    assert rows[0]['classification'] == 'UNIQUE_MATCH'


def test_revised_facts_or_removed_note_do_not_auto_exclude(tmp_path):
    r = reconciler(tmp_path)
    r.add_serving(fact())
    r.add_raw(fact(), official_id='A', has_note=True)
    r.add_raw(fact(total_price=400), official_id='A', has_note=False)
    assert next(r.classifications())['classification'] == 'MULTIPLE_MATCH'
    r.add_raw(fact(), official_id='A', has_note=False)
    assert next(r.classifications())['classification'] == 'MULTIPLE_MATCH'


def test_missing_identity_never_auto_excludes_and_demo_future_are_distinct(tmp_path):
    r = reconciler(tmp_path)
    r.add_serving(fact())
    r.add_serving(fact(id=2, source='sample'))
    r.add_serving(fact(id=3, transaction_period='2026-12'))
    r.add_raw(fact(), official_id='', has_note=True, source_file='f.csv', source_row=1)
    assert next(r.classifications())['classification'] == 'MULTIPLE_MATCH'
    r.add_raw(fact(transaction_period='2026-12'), official_id='future', has_note=True)
    assert any(v['classification'] == 'NO_MATCH' for v in r.classifications())


def test_changed_strong_fact_does_not_match(tmp_path):
    r = reconciler(tmp_path)
    r.add_serving(fact())
    r.add_raw(fact(total_price=345.60), official_id='A', has_note=True)
    assert next(r.classifications())['classification'] == 'NO_MATCH'


def test_local_serving_relation_is_explicit_and_fail_closed(monkeypatch):
    monkeypatch.delenv('PLVR_SERVING_EXCLUSIONS_ENABLED', raising=False)
    assert serving_relation() == 'real_price_transactions'
    monkeypatch.setenv('PLVR_SERVING_EXCLUSIONS_ENABLED', 'true')
    assert serving_relation() == 'market_serving_transactions'
    monkeypatch.setenv('PLVR_SERVING_EXCLUSIONS_ENABLED', 'typo')
    import pytest
    with pytest.raises(ValueError):
        serving_relation()


def test_view_retains_original_but_removes_known_market_comparable():
    # Execute the same anti-join used by the PostgreSQL migration on synthetic
    # records. Live PostgreSQL privilege/DDL proof remains a separate check.
    source = Path('database/migrations/023_add_market_serving_exclusions.sql').read_text()
    select = source.split('-- BEGIN PORTABLE VIEW SELECT\n')[1].split('-- END PORTABLE VIEW SELECT')[0]
    select = select.replace('public.', '')
    db = sqlite3.connect(':memory:')
    db.execute('create table real_price_transactions (id integer primary key, source text, unit_price_per_ping real)')
    db.execute('create table market_serving_exclusions (serving_transaction_id integer primary key)')
    db.executemany('insert into real_price_transactions values (?,?,?)', [(38652,'official_plvr_opendata',10.15),(2,'official_plvr_opendata',50),(3,'sample',99)])
    db.execute('create view market_serving_transactions as '+select)
    db.execute('insert into market_serving_exclusions values (38652)')
    assert db.execute('select count(*) from real_price_transactions where id=38652').fetchone()[0] == 1
    assert db.execute('select count(*) from market_serving_transactions where id=38652').fetchone()[0] == 0
    assert db.execute("select avg(unit_price_per_ping),count(*) from market_serving_transactions where source='official_plvr_opendata'").fetchone() == (50.0,1)
    assert db.execute("select count(*) from market_serving_transactions where source='sample'").fetchone()[0] == 1


def test_all_blue_serving_consumers_select_exclusion_view(monkeypatch):
    from services.valuation_providers.postgres_provider import PostgresValuationProvider, _comparable_query
    from services.plvr_market_aggregate_service import PostgresMarketReadModelRepository
    from tests.test_postgres_valuation_provider import _ScopeConnection
    monkeypatch.setenv('PLVR_SERVING_EXCLUSIONS_ENABLED','true')
    sql, _ = _comparable_query({'city':'新北市','district':'新莊區'}, 'district', 10)
    assert 'from market_serving_transactions' in sql
    assert 'transaction_period <= %s' in sql
    connection = _ScopeConnection()
    monkeypatch.setattr(PostgresValuationProvider,'_connect',lambda self: connection)
    provider=PostgresValuationProvider('postgresql://test')
    provider.query_trend_rows({'city':'新北市','district':'新莊區'})
    assert 'from market_serving_transactions' in connection.cursor_instance.query
    provider.query_property_search_rows({'city':'新北市'})
    assert 'from market_serving_transactions' in connection.cursor_instance.query


def test_market_and_segment_sql_preserve_parameters_and_use_view(monkeypatch):
    from services.plvr_serving_quality import serving_sql
    from services import plvr_market_aggregate_service as market
    from services import market_segmentation_service as segment
    monkeypatch.setenv('PLVR_SERVING_EXCLUSIONS_ENABLED','true')
    for statement in [market.DIRECT_SUMMARY_DISTRICT_LATEST_SQL,market.DIRECT_HISTORY_DISTRICT_SQL,
                      market.DIRECT_COVERAGE_DISTRICT_SQL,market.MARKET_ROAD_EVIDENCE_SQL,
                      market.REFRESH_TEMP_AGGREGATES_SQL,segment.SEGMENT_SQL,segment.COMPARABLES_SQL]:
        rewritten=serving_sql(statement)
        assert 'from market_serving_transactions' in rewritten
        assert 'from real_price_transactions' not in rewritten
        assert rewritten.count('%s')==statement.count('%s')


def test_private_reconciliation_cli_preserves_sources_and_requires_review(tmp_path):
    import csv, json
    from services.plvr_import_service import normalize_row
    from scripts.ops.reconcile_plvr_special_notes import reconcile
    raw_root=tmp_path/'raw';raw_root.mkdir()
    raw={'鄉鎮市區':'新莊區','土地位置建物門牌':'新北市新莊區中華路一段６３巷６號二樓',
         '交易標的':'房地(土地+建物)','交易年月日':'1150501',
         '建物移轉總面積平方公尺':'112.6','總價元':'3455932','單價元平方公尺':'30692',
         '建物型態':'華廈(10層含以下有電梯)','移轉層次':'二層','總樓層數':'八層',
         '編號':'RPWNMLNKNHLGFBF78EA','備註':'親友、員工、共有人或其他特殊關係間之交易；'}
    raw_file=raw_root/'f_lvr_land_a.csv'
    with raw_file.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(raw));writer.writeheader();writer.writerow(raw)
    before=raw_file.read_bytes()
    normalized,reason=normalize_row(raw,city_hint='新北市')
    assert reason is None
    snapshot=tmp_path/'serving.jsonl'
    snapshot.write_text(json.dumps({**normalized,'id':38652},ensure_ascii=False)+'\n')
    result=reconcile(serving_export=snapshot,raw_root=raw_root,output=tmp_path/'evidence',as_of='2026-10',
                     expected_official_rows=1,expected_total_rows=1,expected_raw_files=1)
    assert result['status']=='REVIEW_REQUIRED'
    assert result['known_serial_unique_match_to_38652'] is True
    assert result['classifications']=={'UNIQUE_MATCH':1,'MULTIPLE_MATCH':0,'NO_MATCH':0}
    assert result['database_changes_applied'] is False
    assert raw_file.read_bytes()==before
    assert (tmp_path/'evidence/fact-index.sqlite').stat().st_mode & 0o777 == 0o600
    evidence=(tmp_path/'evidence/classifications.jsonl').read_text()
    assert '中華路' not in evidence


def test_local_view_zero_candidates_does_not_resurrect_stale_coverage(monkeypatch):
    from services.plvr_market_aggregate_service import PostgresMarketReadModelRepository
    class Cursor:
        query=''
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,query,params=None): self.query=query
        def fetchone(self):
            if 'from market_region_coverage' in self.query:
                return {'coverage_status':'covered','valid_market_candidate_count':99,'source_updated_at':'2026-06-08'}
            return {'valid_market_candidate_count':0,'excluded_future_period_count':0,'source_updated_at':None}
    class Connection:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def cursor(self): return Cursor()
    monkeypatch.setenv('PLVR_SERVING_EXCLUSIONS_ENABLED','true')
    monkeypatch.setattr(PostgresMarketReadModelRepository,'_connect',lambda self:Connection())
    result=PostgresMarketReadModelRepository('postgresql://test').coverage('新北市','新莊區')
    assert result['coverage_status']=='coverage_unknown'
    assert result['valid_market_candidate_count']==0
    assert result['source_updated_at'] is None


def test_unparseable_revision_and_unknown_floor_block_automation(tmp_path):
    r=reconciler(tmp_path)
    r.add_serving(fact())
    r.add_raw(fact(),official_id='A',has_note=True)
    r.add_raw(fact(total_price='unparseable'),official_id='A',has_note=False)
    assert next(r.classifications())['classification']=='MULTIPLE_MATCH'
    r.add_serving(fact(id=2,floor=0,total_price=500))
    r.add_raw(fact(floor=0,total_price=500),official_id='B',has_note=True)
    assert all(item['classification']=='MULTIPLE_MATCH' for item in r.classifications())



def test_raw_floor_fidelity_is_required():
    from scripts.ops.reconcile_plvr_special_notes import reliable_floor
    assert reliable_floor('二層',2)
    assert reliable_floor('30層',30)
    assert not reliable_floor('一層，二層',1)
    assert not reliable_floor('地下二層',-1)
    assert not reliable_floor('三十一層',11)
    assert not reliable_floor('',0)


def test_high_cardinality_classification_uses_bounded_indexed_work(tmp_path):
    """Distinct serial/fact groups must not form an identities×facts scan."""
    r=reconciler(tmp_path)
    try:
        for number in range(2000):
            row=fact(id=number+1,address_text=f'合成測試地址{number}')
            r.add_serving(row)
            r.add_raw(row,official_id=f'SYNTHETIC-{number:06d}',has_note=True)
        r.db.commit()
        instructions=0
        def bounded_work():
            nonlocal instructions
            instructions+=1000
            return instructions>2_000_000
        r.db.set_progress_handler(bounded_work,1000)
        results=list(r.classifications())
        assert len(results)==2000
        assert {row['classification'] for row in results}=={'UNIQUE_MATCH'}
        assert instructions<=2_000_000
    finally:
        r.db.set_progress_handler(None,0)
        r.close()


def test_failure_diagnostics_are_specific_without_exception_values():
    from scripts.ops.reconcile_plvr_special_notes import safe_reconciliation_error, safe_process_report
    import json
    error=sqlite3.OperationalError('sensitive SQL payload must not be logged')
    error.sqlite_errorcode=sqlite3.SQLITE_CANTOPEN
    error.sqlite_errorname='SQLITE_CANTOPEN'
    diagnostic=safe_reconciliation_error(error)
    assert diagnostic['reason_code']=='sqlite_cannot_open'
    assert diagnostic['sqlite_errorcode']==sqlite3.SQLITE_CANTOPEN
    assert 'sensitive' not in json.dumps(diagnostic)
    diagnostic['raw_note']='must not be copied'
    diagnostic['database_url']='must not be copied'
    report=safe_process_report(json.dumps(diagnostic).encode(),1)
    assert report['reason_code']=='sqlite_cannot_open'
    assert report['exit_code']==1
    assert 'raw_note' not in report and 'database_url' not in report
    malformed=safe_process_report(b'not JSON; credentials might be here',1)
    assert malformed['reason_code']=='invalid_child_report'
    assert 'credentials' not in json.dumps(malformed)
    count=safe_reconciliation_error(ValueError('raw source file count does not match reviewed baseline'))
    assert count['reason_code']=='raw_source_file_count_mismatch'



def test_process_diagnostics_reject_malformed_types_without_echoing_values():
    import json
    from scripts.ops.reconcile_plvr_special_notes import safe_process_report
    for value in [[],None,{'status':[]},{'status':'BLOCKED','reason_code':{},'error_class':[]}]:
        report=safe_process_report(json.dumps(value).encode(),1)
        assert report['status']=='BLOCKED'
        assert report['exit_code']==1
        assert not isinstance(report.get('reason_code'),dict)
