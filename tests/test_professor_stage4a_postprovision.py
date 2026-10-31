"""Read-only post-provision tool tests; no live host/database credentials."""
import json
from pathlib import Path
import os
import subprocess

import pytest
from tests.test_professor_userdb import pg  # noqa:F401
from scripts.ops import professor_stage4a_postprovision as probe


ROOT=Path(__file__).resolve().parents[1]


def test_catalog_matches_migration_and_disposable_multiuser_contract(pg):
    import psycopg
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('SET TRANSACTION READ ONLY')
        catalog=c.execute(probe.CATALOG_SQL).fetchone()[0]
    expected=json.loads(probe.EXPECTED.read_text())
    assert catalog==expected['catalog']
    assert expected['migration_sha256']==__import__('hashlib').sha256((ROOT/'database/userdb/001_professor_users.sql').read_bytes()).hexdigest()


def test_default_plan_cannot_contact_docker_or_open_credentials(monkeypatch,capsys):
    monkeypatch.setattr(probe.sys,'argv',['probe'])
    monkeypatch.setattr(probe,'run',lambda *a,**kw:pytest.fail('plan must be offline'))
    assert probe.main()==0
    result=json.loads(capsys.readouterr().out)
    assert result['activation_performed'] is False
    assert result['credential_files_opened'] is False


def test_metadata_does_not_read_file_contents(tmp_path,monkeypatch):
    file=tmp_path/'fixture';file.write_text('synthetic');file.chmod(0o600)
    monkeypatch.setattr(Path,'read_text',lambda *a,**kw:pytest.fail('metadata must not read contents'))
    assert probe.metadata(file,os.getuid(),os.getgid(),0o600)
    file.chmod(0o644)
    assert not probe.metadata(file,os.getuid(),os.getgid(),0o600)


def test_no_mutating_database_or_container_operations():
    source=(ROOT/'scripts/ops/professor_stage4a_postprovision.py').read_text()
    assert 'BEGIN READ ONLY' in source
    assert 'read_secret(' not in source
    assert not any(token in source for token in ['CREATE TABLE','INSERT INTO','UPDATE professor','ALTER TABLE','--force-recreate','docker compose','DROP ','TRUNCATE '])


def test_role_queries_are_readonly_and_safe_in_disposable_database(pg):
    import psycopg
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('SET TRANSACTION READ ONLY')
        value=c.execute(probe.ROLE_SQL).fetchone()[0]
    assert value['role_safe'] is True
    assert value['no_external_writes'] is True
    assert value['no_callable_definer'] is True
    assert value['configuration_rows']==1 and value['issuer_matches'] is False  # deliberately different fixture issuer
    assert value['user_count']==value['case_count']==0


def test_catalog_detects_runtime_function_revocation_and_added_owner_view(pg):
    import psycopg
    expected=json.loads(probe.EXPECTED.read_text())['catalog']
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('REVOKE EXECUTE ON FUNCTION professor_user.subject() FROM professor_user_runtime')
        assert c.execute(probe.CATALOG_SQL).fetchone()[0]!=expected
        c.rollback()
        c.execute('CREATE VIEW professor_user.unexpected_cross_tenant AS SELECT * FROM professor_user.saved_cases')
        c.execute('GRANT SELECT ON professor_user.unexpected_cross_tenant TO professor_user_runtime')
        assert c.execute(probe.CATALOG_SQL).fetchone()[0]!=expected
        c.rollback()


def test_catalog_detects_effective_connect_revocation(pg):
    import psycopg
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('REVOKE CONNECT ON DATABASE stage4a_userdb_test FROM PUBLIC,professor_user_runtime')
        role=c.execute(probe.ROLE_SQL).fetchone()[0]
        assert role['database_connect'] is False and role['role_safe'] is False
        c.rollback()


def test_external_owner_view_cannot_pass_isolation_gate(pg):
    import psycopg
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('CREATE VIEW public.stage4a_external_user_rows AS SELECT * FROM professor_user.saved_cases')
        c.execute('GRANT SELECT ON public.stage4a_external_user_rows TO professor_user_runtime')
        role=c.execute(probe.ROLE_SQL).fetchone()[0]
        assert role['no_external_reads'] is False
        c.rollback()


def test_secret_metadata_rejects_symlinked_and_unsafe_parents(tmp_path):
    folder=tmp_path/'store';folder.mkdir(mode=0o700)
    value=folder/'fixture';value.write_text('synthetic');value.chmod(0o600)
    alias=tmp_path/'alias';alias.symlink_to(folder,target_is_directory=True)
    assert not probe.metadata(alias/'fixture',os.getuid(),os.getgid(),0o600)
    folder.chmod(0o777)
    assert not probe.metadata(value,os.getuid(),os.getgid(),0o600)


def test_guard_comparisons_cover_all_established_disabled_capabilities():
    from services.selfhost_secret_files import DISABLED,OFF_FEATURES
    expected=set(probe.guard_expectations())
    assert {'ANTI_ABUSE_'+name+'_DISABLED=true' for name in DISABLED}<=expected
    assert {name+'=false' for name in OFF_FEATURES}<=expected
    assert 'PLVR_SERVING_EXCLUSIONS_ENABLED=true' in expected


def test_empty_pgservice_reproduces_the_failed_peer_probe(pg):
    """The old Docker -e PGSERVICE= was not equivalent to unsetting it."""
    import pwd
    binary=Path('/tmp/proptech-pg18-package/usr/lib/postgresql/18/bin/psql')
    environ={'PATH':os.defpath,'LD_LIBRARY_PATH':str(binary.parent.parents[3]/'lib/x86_64-linux-gnu'),
             'PGSERVICE':'','PGSERVICEFILE':'/dev/null','PGPASSFILE':'/dev/null'}
    result=subprocess.run([str(binary),'-X','-w','-h',pg,'-p','5432','-qAt','-U',pwd.getpwuid(os.getuid()).pw_name,'-d','stage4a_userdb_test'],
        input=b'BEGIN READ ONLY; SELECT 1; ROLLBACK;',capture_output=True,env=environ,timeout=15)
    assert result.returncode==2
    assert b'definition of service "" not found' in result.stderr
    assert result.stdout==b''


def test_peer_probe_clean_environment_executes_exact_readonly_catalog(pg):
    """Exercise actual psql with inherited libpq routing variables poisoned."""
    import pwd
    args=probe.peer_command('fixture-container')
    assert args[:6]==['docker','exec','-i','--user','70:70','fixture-container']
    assert args[6:8]==['env','-i']
    assert 'PGSERVICE=' not in args and 'PGHOSTADDR=' not in args
    tail=args[6:]
    binary=Path('/tmp/proptech-pg18-package/usr/lib/postgresql/18/bin/psql')
    tail[tail.index('psql')]=str(binary)
    tail[tail.index('/var/run/postgresql')]=pg
    tail[tail.index('postgres')]=pwd.getpwuid(os.getuid()).pw_name
    tail[tail.index('proptech_app')]='stage4a_userdb_test'
    tail.insert(2,'LD_LIBRARY_PATH='+str(binary.parent.parents[3]/'lib/x86_64-linux-gnu'))
    sql=("BEGIN READ ONLY; SET LOCAL statement_timeout='5s'; SET LOCAL lock_timeout='1s';\n"+
         probe.CATALOG_SQL+probe.ROLE_SQL+"SELECT jsonb_build_object('read_only',current_setting('transaction_read_only')='on','unix_socket',inet_server_addr() IS NULL); ROLLBACK;")
    result=subprocess.run(tail,input=sql.encode(),capture_output=True,timeout=15,
        env={'PATH':os.defpath,'PGSERVICE':'must-not-load','PGHOSTADDR':'192.0.2.1','PGSERVICEFILE':'/nonexistent/stage4a-service','PGDATABASE':'must-not-connect'})
    assert result.returncode==0,'sanitized_disposable_peer_probe_failed'
    rows=[json.loads(line) for line in result.stdout.decode().strip().splitlines()]
    assert len(rows)==3
    assert rows[0]==json.loads(probe.EXPECTED.read_text())['catalog']
    assert rows[1]['role_safe'] is True
    assert rows[2]=={'read_only':True,'unix_socket':True}


def test_pg17_live_receipt_is_exact_pg18_catalog_without_duplicate_not_null_rows():
    """The actual failed receipt pins ALL remaining metadata by SHA256."""
    from copy import deepcopy
    expected=json.loads(probe.EXPECTED.read_text())['catalog']
    pg17=deepcopy(expected)
    pg17['constraints']=[r for r in pg17['constraints'] if r[2]!='n']
    assert len(expected['constraints'])-len(pg17['constraints'])==58
    assert probe.digest(pg17)=='f04cbbd3748e1c146ba288cd951b56e5d6aef8b1111ddab46381812d59d2d289'
    native=probe.catalog_for_server(expected,'170010')
    assert native==pg17
    assert native['columns']==expected['columns']  # attnotnull stays exact
    assert len([r for r in expected['constraints'] if r[2]=='n'])==58
    assert probe.catalog_for_server(expected,'180006')==expected


@pytest.mark.parametrize('version',['160010','190000','not-a-version','170010 ',None,True])
def test_catalog_version_projection_refuses_unknown_versions(version):
    from services.selfhost_secret_files import SecretRefused
    expected=json.loads(probe.EXPECTED.read_text())['catalog']
    with pytest.raises(SecretRefused):probe.catalog_for_server(expected,version)


def test_pg17_projection_rejects_inconsistent_not_null_baseline():
    from copy import deepcopy
    from services.selfhost_secret_files import SecretRefused
    expected=json.loads(probe.EXPECTED.read_text())['catalog']
    broken=deepcopy(expected)
    row=next(r for r in broken['constraints'] if r[2]=='n')
    row[3]=False
    with pytest.raises(SecretRefused):probe.catalog_for_server(broken,'170010')
    broken=deepcopy(expected)
    broken['constraints']=[r for r in broken['constraints'] if not (r[0]=='users' and r[2]=='n')]
    with pytest.raises(SecretRefused):probe.catalog_for_server(broken,'170010')


def test_pg17_projection_still_detects_every_security_relevant_change():
    from copy import deepcopy
    expected=json.loads(probe.EXPECTED.read_text())['catalog']
    native=probe.catalog_for_server(expected,'170010')
    changed=deepcopy(native)
    target=next(c for c in changed['columns'] if c[0]=='saved_cases' and c[1]=='owner_id')
    target[3]=False  # drop actual NOT NULL must still fail exact comparison
    assert changed!=native
    changed=deepcopy(native);changed['policies'][0][5]='true'
    assert changed!=native
    changed=deepcopy(native);changed['grants'][0][2]=not changed['grants'][0][2]
    assert changed!=native
    changed=deepcopy(native);changed['constraints'].pop()
    assert changed!=native
