"""Opt-in proof against a private disposable Unix-socket PostgreSQL cluster."""
from datetime import date
import os
from pathlib import Path

import pytest

pytestmark=pytest.mark.skipif(os.getenv('PLVR_QUALITY_DISPOSABLE')!='1',reason='private disposable PostgreSQL not enabled')


def test_exclusion_view_actual_queries_and_runtime_privileges(monkeypatch):
    import psycopg
    from services.valuation_providers.postgres_provider import PostgresValuationProvider
    from services.plvr_market_aggregate_service import PostgresMarketReadModelRepository
    from services.market_segmentation_service import PostgresMarketSegmentationRepository
    socket=Path(os.environ['PLVR_QUALITY_TEST_SOCKET']).resolve()
    assert socket.is_relative_to(Path('/tmp')) and socket.name.startswith('professor-quality-')
    database=os.environ['PLVR_QUALITY_TEST_DATABASE']
    assert database.startswith('professor_quality_test_')
    admin=psycopg.connect(host=str(socket),dbname=database,user='quality_admin',sslmode='disable')
    with admin:
        admin.execute(Path('database/valuation_schema.sql').read_text())
        admin.execute(Path('database/market_read_model_schema.sql').read_text())
        admin.execute(Path('database/migrations/003_add_market_region_coverage.sql').read_text())
        admin.execute(Path('database/migrations/023_add_market_serving_exclusions.sql').read_text())
        admin.execute("do $$ begin if not exists(select from pg_roles where rolname='quality_runtime') then create role quality_runtime login nosuperuser nocreatedb nocreaterole nobypassrls; end if; end $$")
        admin.execute('grant usage on schema public to quality_runtime')
        admin.execute('grant select on real_price_transactions,market_serving_exclusions,market_serving_transactions,market_serving_district_periods,market_read_model_metadata,market_region_coverage,valuation_import_runs,community_buildings to quality_runtime')
        for identifier,period,source,price in [(38652,'2026-05','official_plvr_opendata',10.15),(2,'2026-05','official_plvr_opendata',50),(3,'2026-12','sample',99),(4,'2026-12','official_plvr_opendata',500)]:
            admin.execute('''insert into real_price_transactions
             (id,transaction_period,city,district,road,address_text,building_type,area_ping,
              building_age_years,floor,total_floor,unit_price_per_ping,total_price,source)
             values (%s,%s,'新北市','新莊區','中華路一段','合成測試地址','華廈',34.06,20,2,8,%s,%s,%s)''',
             [identifier,period,price,price*34.06,source])
        admin.execute("insert into market_serving_exclusions values (38652,'special_note_requires_review','UNIQUE_MATCH','synthetic-official-id','test-v1',%s,now())",['a'*64])
        admin.execute("insert into market_region_coverage values ('新北市','新莊區','covered',99,null,now())")
        admin.execute("insert into market_read_model_metadata values ('v1','ready','partial','synthetic',null,null,null,0,0,0,now(),'test only')")
    monkeypatch.setenv('PLVR_SERVING_EXCLUSIONS_ENABLED','true')
    monkeypatch.setenv('POSTGRES_SSLMODE','disable') # private test cluster, not server TLS acceptance
    target='host='+str(socket)+' dbname='+database+' user=quality_runtime'
    provider=PostgresValuationProvider(target)
    comparables=provider.query_comparables({'city':'新北市','district':'新莊區','road':'中華路一段'})
    assert [row['id'] for row in comparables]==[2]
    trend=provider.query_trend_rows({'city':'新北市','district':'新莊區'})
    assert len(trend)==1 and trend[0]['unit_price_per_ping']==50
    finder=provider.query_property_search_rows({'city':'新北市'})
    assert len(finder)==1 and finder[0]['unit_price_per_ping']==50
    market=PostgresMarketReadModelRepository(target,as_of=date(2026,10,28))
    summary=market.summary('新北市','新莊區','2026-05')
    assert summary['transaction_count']==1 and float(summary['average_unit_price'])==50
    assert market.catalog()==[{'county':'新北市'}]
    assert market.regions('新北市')[0]['latest_period']=='2026-05'
    assert market.status()['aggregate_region_count']==1
    status=provider.data_status()
    assert status['official_records_count']==3 # retained forensic population
    assert status['sample_records_count']==1
    assert status['coverage']['records_count']==3 # serving view, including distinct demo row
    assert status['effective_trend_period_max']=='2026-05'
    assert status['raw_official_period_max']=='2026-12'
    coverage=market.coverage('新北市','新莊區')
    assert coverage['valid_market_candidate_count']==1
    with psycopg.connect(host=str(socket),dbname=database,user='quality_runtime',sslmode='disable') as connection:
        assert connection.execute('select count(*) from real_price_transactions').fetchone()[0]==4
        assert connection.execute('select count(*) from real_price_transactions where id=38652').fetchone()[0]==1
        assert connection.execute('select count(*) from market_serving_transactions where id=38652').fetchone()[0]==0
        assert connection.execute("select count(*) from market_serving_transactions where source='sample'").fetchone()[0]==1
        for privilege in ['INSERT','UPDATE','DELETE']:
            assert connection.execute("select has_table_privilege(current_user,'market_serving_exclusions',%s)",[privilege]).fetchone()[0] is False
        assert connection.execute("select rolsuper,rolbypassrls,rolcreatedb,rolcreaterole from pg_roles where rolname=current_user").fetchone()==(False,False,False,False)
