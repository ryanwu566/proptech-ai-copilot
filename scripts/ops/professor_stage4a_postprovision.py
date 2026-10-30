#!/usr/bin/env python3
"""Read-only Stage 4A verification. Never opens credentials or activates runtime.

Operator --inspect uses SELECTs in a READ ONLY transaction via existing local
PostgreSQL peer auth. Writes only a newly generated sanitized /tmp receipt.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
import json
import os
from pathlib import Path
import resource
import re
import stat
import subprocess
import sys
import tempfile
sys.dont_write_bytecode=True

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from services.selfhost_secret_files import SecretRefused, open_directory, DISABLED, OFF_FEATURES
from scripts.ops.professor_server_secrets import check_backing_storage

EXPECTED=ROOT/'reports/professor-stage4a-auth-userdb/expected-catalog.json'
ISSUER='https://flyhsjcynreuofbcdxod.supabase.co/auth/v1'
ROLE='professor_user_runtime'
CATALOG_SQL="""
SELECT jsonb_build_object(
 'relations',(SELECT jsonb_agg(jsonb_build_array(c.relname,c.relkind,c.relrowsecurity,c.relforcerowsecurity) ORDER BY c.relname)
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='professor_user'),
 'columns',(SELECT jsonb_agg(jsonb_build_array(c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_get_expr(d.adbin,d.adrelid)) ORDER BY c.relname,a.attnum)
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
  LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname='professor_user' AND c.relkind='r'),
 'constraints',(SELECT jsonb_agg(jsonb_build_array(c.relname,k.conname,k.contype,k.convalidated,pg_get_constraintdef(k.oid)) ORDER BY c.relname,k.conname)
  FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='professor_user'),
 'policies',(SELECT jsonb_agg(jsonb_build_array(tablename,policyname,permissive,roles,cmd,qual,with_check) ORDER BY tablename,policyname)
  FROM pg_policies WHERE schemaname='professor_user'),
 'functions',(SELECT jsonb_agg(jsonb_build_array(p.proname,oidvectortypes(p.proargtypes),p.prosecdef,p.provolatile,p.proconfig,p.prosrc,l.lanname,has_function_privilege('professor_user_runtime',p.oid,'EXECUTE')) ORDER BY p.proname)
  FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname='professor_user'),
 'triggers',(SELECT jsonb_agg(jsonb_build_array(c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid)) ORDER BY c.relname,t.tgname)
  FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='professor_user' AND NOT t.tgisinternal),
 'indexes',(SELECT jsonb_agg(jsonb_build_array(tablename,indexname,indexdef) ORDER BY tablename,indexname) FROM pg_indexes WHERE schemaname='professor_user'),
 'grants',(SELECT jsonb_agg(jsonb_build_array(c.relname,a.attname,
   has_table_privilege('professor_user_runtime',c.oid,'SELECT'),has_table_privilege('professor_user_runtime',c.oid,'DELETE'),
   has_table_privilege('professor_user_runtime',c.oid,'TRUNCATE,TRIGGER,REFERENCES'),
   has_column_privilege('professor_user_runtime',c.oid,a.attnum,'SELECT'),has_column_privilege('professor_user_runtime',c.oid,a.attnum,'INSERT'),
   has_column_privilege('professor_user_runtime',c.oid,a.attnum,'UPDATE'),has_column_privilege('professor_user_runtime',c.oid,a.attnum,'REFERENCES')) ORDER BY c.relname,a.attnum)
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped WHERE n.nspname='professor_user' AND c.relkind='r'),
 'schema_usage',has_schema_privilege('professor_user_runtime','professor_user','USAGE'),
 'schema_create',has_schema_privilege('professor_user_runtime','professor_user','CREATE')
);
"""
ROLE_SQL="""
SELECT jsonb_build_object(
 'database_connect',has_database_privilege('professor_user_runtime',current_database(),'CONNECT'),
 'role_safe',(SELECT has_database_privilege(r.oid,current_database(),'CONNECT') AND rolcanlogin AND NOT rolsuper AND NOT rolbypassrls AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication
   AND NOT EXISTS(SELECT FROM pg_auth_members m WHERE m.member=r.oid)
   AND NOT has_database_privilege(r.oid,current_database(),'CREATE')
   AND r.oid<>(SELECT datdba FROM pg_database WHERE datname=current_database())
   AND NOT EXISTS(SELECT FROM pg_namespace n WHERE left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema' AND (n.nspowner=r.oid OR has_schema_privilege(r.oid,n.oid,'CREATE')))
   AND NOT EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema' AND c.relowner=r.oid)
   AND NOT EXISTS(SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema' AND p.proowner=r.oid)
   FROM pg_roles r WHERE rolname='professor_user_runtime'),
 'no_external_reads',NOT EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname<>'professor_user' AND left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema' AND c.relkind IN ('r','p','v','m','f')
   AND has_schema_privilege('professor_user_runtime',n.oid,'USAGE') AND has_any_column_privilege('professor_user_runtime',c.oid,'SELECT')),
 'no_external_writes',NOT EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname<>'professor_user' AND left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema' AND c.relkind IN ('r','p','v','f')
   AND (has_table_privilege('professor_user_runtime',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE') OR has_any_column_privilege('professor_user_runtime',c.oid,'INSERT,UPDATE,REFERENCES'))),
 'no_callable_definer',NOT EXISTS(SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema' AND p.prosecdef
   AND has_schema_privilege('professor_user_runtime',n.oid,'USAGE') AND has_function_privilege('professor_user_runtime',p.oid,'EXECUTE')),
 'configuration_rows',(SELECT count(*) FROM professor_user.configuration),
 'issuer_matches',(SELECT issuer='https://flyhsjcynreuofbcdxod.supabase.co/auth/v1' AND migration_version=1 FROM professor_user.configuration WHERE singleton),
 'authority_reviewed',(SELECT authority_reviewed FROM professor_user.configuration WHERE singleton),
 'user_count',(SELECT count(*) FROM professor_user.users),
 'case_count',(SELECT count(*) FROM professor_user.saved_cases),
 'database_matches',current_database()='proptech_app',
 'server_version_num',current_setting('server_version_num')
);
"""


def require(condition,reason):
    if not condition:raise SecretRefused(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()



def catalog_for_server(expected,server_version):
    """Exact expected catalog for supported PostgreSQL 17/18 representations.

    PostgreSQL 18 additionally records table NOT NULL in pg_constraint. Both
    versions record actual column nullability in pg_attribute.attnotnull, which
    remains in the exact columns comparison. Never remove rows from live data.
    """
    require(isinstance(server_version,str) and re.fullmatch(r'[0-9]{6}',server_version),
            'unsupported_postgres_catalog_version')
    major=int(server_version)//10000
    require(major in {17,18},'unsupported_postgres_catalog_version')
    native=deepcopy(expected)
    if major==18:return native
    required={(r[0],r[1]) for r in expected['columns'] if r[3] is True}
    represented=set()
    constraints=[]
    for row in expected['constraints']:
        if row[2]!='n':
            constraints.append(row)
            continue
        require(len(row)==5 and row[3] is True and isinstance(row[4],str)
                and row[4].startswith('NOT NULL '),'not_null_baseline_invalid')
        key=(row[0],row[4].removeprefix('NOT NULL '))
        require(key in required and key not in represented,'not_null_baseline_invalid')
        represented.add(key)
    require(represented==required,'not_null_baseline_invalid')
    native['constraints']=constraints
    return native


def run(args,source=None):
    result=subprocess.run(args,input=source,capture_output=True,timeout=60,env={'PATH':os.defpath,'HOME':'/root'})
    require(result.returncode==0,'readonly_command_failed_details_suppressed')
    return result.stdout


def peer_command(container):
    # libpq treats PGSERVICE='' as a configured empty service, not as unset.
    # Start the diagnostic child with a minimal environment instead. This also
    # removes inherited hostaddr/service/password routing without changing the
    # container's configuration or weakening peer/READ ONLY boundaries.
    return ['docker','exec','-i','--user','70:70',container,'env','-i',
            'PATH=/usr/local/bin:/usr/bin:/bin','PGCLIENTENCODING=UTF8',
            'PGPASSFILE=/dev/null','PGOPTIONS=-c default_transaction_read_only=on',
            'psql','-X','-w','-h','/var/run/postgresql','-p','5432','-qAt',
            '-v','ON_ERROR_STOP=1','-U','postgres','-d','proptech_app']


def metadata(path,uid,gid,mode):
    parent=None
    try:
        parent=open_directory(path.parent,owner=uid,private=True)
        s=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        return stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid==uid and s.st_gid==gid and stat.S_IMODE(s.st_mode)==mode and 0<s.st_size<=8192
    except (OSError,SecretRefused):return False
    finally:
        if parent is not None:os.close(parent)


def guard_expectations():
    return [*['ANTI_ABUSE_'+name+'_DISABLED=true' for name in DISABLED],
            *[name+'=false' for name in OFF_FEATURES],
            'EARTH_ENGINE_SATELLITE_REFERENCE_V1=false',
            'PLVR_SERVING_EXCLUSIONS_ENABLED=true','PLVR_DATA_BACKEND=blue','VALUATION_DEMO_MODE=false']


def inspect():
    require(os.geteuid()==0,'operator_readonly_access_required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    result={'schema':'professor-stage4a-postprovision-v1','status':'PARTIAL','activation_performed':False,
            'database_writes':False,'credential_files_opened':False,'secret_values_returned':False}
    try:
        folder=Path('/var/backups/proptech-selfhost/stage4a-userdb')
        os.close(open_directory(folder,private=True))
        records=[]
        for child in folder.iterdir():
            if child.is_symlink() or not child.is_dir():continue
            os.close(open_directory(child,private=True))
            p=child/'apply-report.json'
            s=p.lstat()
            require(stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1 and not s.st_mode&0o077 and s.st_size<65536,'receipt_metadata_invalid')
            data=json.loads(p.read_text())
            if data.get('status')=='PASS_PROVISIONED_NOT_ACTIVE':records.append((p.stat().st_mtime_ns,p,data))
        require(len(records)==1,'successful_provision_receipt_ambiguous')
        _,receipt,data=records[0]
        result['provision_receipt']=str(receipt)
        result['provision_receipt_valid']=(data.get('schema_applied') is True and data.get('activation_performed') is False
            and data.get('migration_sha256')==hashlib.sha256((ROOT/'database/userdb/001_professor_users.sql').read_bytes()).hexdigest())
        result['new_secret_metadata_valid']=all(metadata(base/'professor_user_database_url',0,gid,mode) for base,gid,mode in [
            (Path('/etc/proptech-selfhost/secrets'),0,0o600),(Path('/run/proptech-selfhost/secrets'),10001,0o440)])
        def service(name):
            ids=run(['docker','ps','--filter','label=com.docker.compose.project=proptech-selfhost','--filter','label=com.docker.compose.service='+name,'--format','{{.ID}}']).decode().split()
            require(len(ids)==1,'service_selection_ambiguous')
            return ids[0]
        db=service('postgres_app');api=service('api')
        result['active_api_image_id']=json.loads(run(['docker','inspect','--format','{{json .Image}}',api]))
        result['active_compose_files']=json.loads(run(['docker','inspect','--format','{{json (index .Config.Labels "com.docker.compose.project.config_files")}}',api]))
        result['containers_healthy']=all(json.loads(run(['docker','inspect','--format','{{json .State.Health.Status}}',i]))=='healthy' for i in [db,api,service('postgres_usage'),service('reverse_proxy')])
        result['postgres_no_host_bindings']=all(not json.loads(run(['docker','inspect','--format','{{json .HostConfig.PortBindings}}',i])) for i in [db,service('postgres_usage')])
        proxy=json.loads(run(['docker','inspect','--format','{{json .HostConfig.PortBindings}}',service('reverse_proxy')]))
        result['proxy_8080_loopback']=proxy.get('8080/tcp')==[{'HostIp':'127.0.0.1','HostPort':'8080'}]
        guards=guard_expectations()
        result['disabled_guards_preserved']=all(run(['docker','inspect','--format','{{range .Config.Env}}{{if eq . '+json.dumps(g)+'}}ok{{end}}{{end}}',api]).strip()==b'ok' for g in guards)
        result['stage4a_runtime_inactive']=not run(['docker','inspect','--format','{{range .Config.Env}}{{if eq . "PROFESSOR_USERDB_ENABLED=true"}}active{{end}}{{end}}',api]).strip()
        mounts=json.loads(run(['docker','inspect','--format','{{json .Mounts}}',api]))
        result['x9_runtime_dependency_absent']=not any('/run/media/andy/Crucial X9' in m.get('Source','') for m in mounts)
        result['new_user_secret_not_mounted']=not any('professor_user_database_url' in m.get('Destination','') for m in mounts)
        sql="BEGIN READ ONLY; SET LOCAL statement_timeout='5s'; SET LOCAL lock_timeout='1s';\n"+CATALOG_SQL+ROLE_SQL+"\nROLLBACK;"
        raw=run(peer_command(db),sql.encode())
        rows=raw.decode().strip().splitlines();require(len(rows)==2,'catalog_result_invalid')
        catalog,role=map(json.loads,rows)
        expected=json.loads(EXPECTED.read_text())
        result['catalog_sha256']=digest(catalog)
        native_expected=catalog_for_server(expected['catalog'],role.get('server_version_num'))
        result['catalog_server_major']=int(role['server_version_num'])//10000
        result['expected_native_catalog_sha256']=digest(native_expected)
        result['catalog_matches_tested_schema']=catalog==native_expected and expected['migration_sha256']==data['migration_sha256']
        result['role_checks']=role
        result['ownership_verified']=result['catalog_matches_tested_schema'] and all(role.get(k) is True for k in ['role_safe','no_external_writes','no_external_reads','no_callable_definer'])
        result['live_cross_user_write_probe']='not_run_readonly_only'
        result['ownership_basis']='exact_schema_policies_grants_match_disposable_multi_user_tests'
        gates=['provision_receipt_valid','new_secret_metadata_valid','containers_healthy','postgres_no_host_bindings','proxy_8080_loopback','disabled_guards_preserved','stage4a_runtime_inactive','x9_runtime_dependency_absent','new_user_secret_not_mounted','catalog_matches_tested_schema','ownership_verified']
        result['postprovision_pass']=all(result[k] for k in gates) and role.get('issuer_matches') is True and role.get('configuration_rows')==1 and role.get('database_matches') is True and role.get('authority_reviewed') is False
        result['status']='PASS_PROVISIONED_INACTIVE' if result['postprovision_pass'] else 'REFUSED'
    except Exception:
        result.update(status='REFUSED',reason_code='readonly_verification_incomplete_details_suppressed')
    check_backing_storage(Path('/tmp'))
    output=Path(tempfile.mkdtemp(prefix='professor-stage4a-postprovision-',dir='/tmp'))
    target=output/'diagnosis.json';target.write_text(json.dumps(result,indent=2)+'\n')
    target.chmod(0o644);output.chmod(0o755)
    print(json.dumps({'status':result['status'],'sanitized_receipt':str(target),'activation_performed':False,'secret_values_returned':False}))
    return 0 if result.get('postprovision_pass') else 1


def main():
    try:
        args=sys.argv[1:]
        if not args or args==['--plan']:
            print(json.dumps({'status':'PLAN_ONLY','read_only':True,'credential_files_opened':False,'activation_performed':False,'writes':'new_sanitized_tmp_receipt_only'}));return 0
        require(args==['--inspect'],'invalid_arguments')
        return inspect()
    except Exception:
        print(json.dumps({'status':'REFUSED','reason_code':'readonly_verification_unavailable','secret_values_returned':False}));return 1


if __name__=='__main__':raise SystemExit(main())
