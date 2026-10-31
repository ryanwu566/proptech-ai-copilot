#!/usr/bin/env python3
"""Operator-only READ-ONLY diagnosis of the failed Stage 2 database precheck.

No activation/build/recreation/rotation or secret-file readback. Only Docker
metadata, existing-container SELECT-only TLS probes, host file stat, and one new
sanitized temporary JSON receipt. The agent must not execute this as root.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys
import tempfile

REPO=Path(__file__).resolve().parents[2]
RECEIPT=Path('/tmp/professor-stage2-activation-78d77527ffee4d7db2ed8727a5bd4e8d')
PROBE_SHA256='2eba08fa2d2d9478515102969dc6e7f13684be8970395a902d383434cd5d5ab7'
SERVICES=('postgres_app','postgres_usage','api','reverse_proxy')
CORE=('app_database_url','usage_database_url','valuation_database_url','usage_peer_hmac_key','pilot_session_signing_key')
STAGING=Path('/run/proptech-selfhost/secrets')


class DiagnosticRefused(Exception):
    pass


# Appended to a verified copy of the original probe, with its CLI invocation
# removed. All comparisons/SQL/readonly connection options remain unchanged.
DIAGNOSTIC_HOOK=r'''
_DIAG_ERROR_CLASSES={'OperationalError','ProgrammingError','InterfaceError','InsufficientPrivilege',
 'SyntaxError','InvalidParameterValue','InvalidSchemaName','UndefinedTable','UndefinedFunction',
 'InvalidTextRepresentation','QueryCanceled','UndefinedColumn','InFailedSqlTransaction',
 'ImportError','ModuleNotFoundError','FileNotFoundError','PermissionError','ContractFailed'}
_DIAG_TAGS={'identity','tls','readonly','escalation','permissions','usage','ris','population','coverage','known_fingerprint'}
_DIAG_OBJECTS={'public.ris_village_demographics'}|{'public.'+s for s in VALUATION_OBJECTS}
_DIAG_FIELDS={
 'population':('raw_rows','official_rows','sample_rows','future_official_rows','known_raw_rows','known_serving_rows',
               'exclusion_rows','invalid_exclusion_evidence','known_official_id_exclusion','serving_ids_equal_expected','serving_view_security'),
 'coverage':('eligible_regions','active_groups','aggregate_mismatches','inactive_group_mismatches','coverage_regions','coverage_mismatches','metadata_consistency')}
_DIAG_EXPECT={'population':(451744,451672,72,0,1,0,117986,0,1,True,True), 'coverage':(None,7500,0,0,368,0,True)}


def _diagnostic_field_matches(tag,index,actual,wanted):
    if tag=='coverage':
        if index==0:return type(actual) is int and 0<actual<=368
        if index==6:return actual is True
        return type(actual) is int and actual==wanted
    return actual==wanted


def _collect_diagnostic(*,connect=None,reader=None,regions=None,hasher=None):
    events={}
    state={'kind':'setup','gate':'dependency_setup','row':None}
    original_require=_require
    def record(exc=None):
        item=events.setdefault(state['kind'],{'last_gate':state['gate']})
        if 'failure' in item:return
        category=type(exc).__name__ if exc else 'contract_mismatch'
        if category not in _DIAG_ERROR_CLASSES|{'contract_mismatch'}:category='other_exception'
        failure={'gate':state['gate'],'category':category}
        code=getattr(exc,'sqlstate',None)
        if isinstance(code,str) and re.fullmatch(r'[A-Z0-9]{5}',code):failure['sqlstate']=code
        tag=state['gate']
        row=state.get('row')
        if tag in _DIAG_EXPECT and isinstance(row,tuple) and len(row)==len(_DIAG_EXPECT[tag]):
            failure['mismatched_fields']=[key for index,(key,actual,wanted) in enumerate(zip(_DIAG_FIELDS[tag],row,_DIAG_EXPECT[tag]))
                if not _diagnostic_field_matches(tag,index,actual,wanted)]
        item['failure']=failure
    def require_instrumented(value):
        if not value:record()
        return original_require(value)
    def read_instrumented(path):
        kind=path.name.removesuffix('_database_url')
        if kind not in {'app','usage','valuation'}:raise ContractFailed()
        state.update(kind=kind,gate='secret_file',row=None)
        events[kind]={'last_gate':'secret_file'}
        try:return reader(path) if reader else path.read_text().strip()
        except Exception as exc:record(exc);raise
    class Cursor:
        def __init__(self,cursor,connection,params):self.cursor,self.connection,self.params=cursor,connection,params
        def fetchone(self):
            try:
                row=self.cursor.fetchone();state['row']=row
                tag=state['gate']
                if (tag=='escalation' and row==(True,)) or (tag=='usage' and row==(False,)):
                    # Explain a failed aggregate security predicate with boolean
                    # catalog SELECTs; never return rows, owners, URLs or SQL text.
                    labels=(('database_create','database_ownership','schema_authority','relation_ownership',
                             'routine_ownership','public_table_writes','unexpected_role_membership','admin_membership')
                            if tag=='escalation' else ('consume_execute','hourly_writer','flush_writer',
                             'scoped_membership','scoped_table_privileges','six_forced_rls_tables'))
                    sql=ESCALATION_SQL if tag=='escalation' else USAGE_SQL
                    fragments=sql.split('*/',1)[1].strip().split('\n OR ' if tag=='escalation' else '\n AND ')
                    details=[]
                    complete=False
                    try:
                        original_require(len(fragments)==len(labels))
                        for label,fragment in zip(labels,fragments):
                            params=self.params if '%s' in fragment else None
                            value=self.connection.execute('SELECT /* '+tag+' */ '+fragment,params).fetchone()
                            original_require(isinstance(value,tuple) and len(value)==1 and isinstance(value[0],bool))
                            if value[0] is (tag=='escalation'):details.append(label)
                        complete=True
                    except Exception:pass
                    events[state['kind']].update(failed_conditions=details,condition_details_complete=complete)
                return row
            except Exception as exc:record(exc);raise
    class Connection:
        def __init__(self,raw):self.raw=raw
        def __enter__(self):
            try:self.raw.__enter__();return self
            except Exception as exc:record(exc);raise
        def __exit__(self,*args):
            try:return self.raw.__exit__(*args)
            except Exception as exc:record(exc);raise
        def execute(self,sql,params=None):
            match=re.search(r'/\* ([a-z_]+) \*/',sql)
            tag=match.group(1) if match else 'unrecognized_query'
            original_require(tag in _DIAG_TAGS and sql.lstrip().startswith(('SELECT','WITH')))
            if tag=='permissions':
                original_require(params and params[0] in _DIAG_OBJECTS)
                tag+='.'+params[0]
            state.update(gate=tag,row=None)
            events[state['kind']]['last_gate']=tag
            try:return Cursor(self.raw.execute(sql,params),self.raw,params)
            except Exception as exc:record(exc);raise
    def connect_instrumented(url,**kwargs):
        state.update(gate='tls_connect',row=None)
        events[state['kind']]['last_gate']='tls_connect'
        # Never broaden what the reviewed probe can connect/write with.
        original_require(kwargs.get('sslmode')=='verify-full' and kwargs.get('sslrootcert')=='/run/selfhost-ca/ca.crt'
                         and 'default_transaction_read_only=on' in kwargs.get('options',''))
        try:return Connection(connect(url,**kwargs))
        except Exception as exc:record(exc);raise
    globals()['_require']=require_instrumented
    try:
        if connect is None:
            import psycopg
            connect=psycopg.connect
        if regions is None:
            from services.plvr_data_integrity import canonical_region_storage_keys
            regions=canonical_region_storage_keys()
        if hasher is None:
            from services.plvr_serving_quality import fact_fingerprint
            hasher=fact_fingerprint
        result=probe_databases(connect=connect_instrumented,read_secret=read_instrumented,region_keys=regions,fact_hasher=hasher)
        if result.get('status')!='PASS' and not any('failure' in row for row in events.values()):
            record()
        return {'collection_status':'COLLECTED','database_contract_status':result.get('status','BLOCKED'),
            'probe':result,'databases':events,'read_only':True,'credential_values_returned':False}
    except Exception as exc:
        record(exc)
        return {'collection_status':'COLLECTED','database_contract_status':'BLOCKED','databases':events,
                'read_only':True,'credential_values_returned':False}
    finally:globals()['_require']=original_require


if __name__=='__main__':
    print(json.dumps(_collect_diagnostic(),sort_keys=True))
'''


def database_payload(raw):
    if hashlib.sha256(raw).hexdigest()!=PROBE_SHA256:raise DiagnosticRefused('probe_source_changed')
    tree=ast.parse(raw)
    guards=[n for n in tree.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
        and isinstance(n.test.left,ast.Name) and n.test.left.id=='__name__'
        and any(isinstance(v,ast.Constant) and v.value=='__main__' for v in n.test.comparators)]
    if len(guards)!=1:raise DiagnosticRefused('probe_cli_shape_changed')
    tree.body.remove(guards[0])
    payload=ast.unparse(tree)+'\n'+DIAGNOSTIC_HOOK
    ast.parse(payload)
    return payload


INSPECT_TEMPLATE='''{"id":{{json .Id}},"image_id":{{json .Image}},"running":{{json .State.Running}},"status":{{json .State.Status}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}}}'''


def main():
    if sys.argv[1:] or os.geteuid()!=0:
        print('{"status":"REFUSED","reason_code":"operator_root_no_arguments_required"}');return 1
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    env={'PATH':os.defpath,'LANG':'C.UTF-8','DOCKER_HOST':'unix:///var/run/docker.sock'}
    def command(args,*,data=None,required=True,timeout=180):
        p=subprocess.run(args,input=data,capture_output=True,env=env,cwd=REPO,timeout=timeout)
        # All commands return only selected fixed metadata or bounded JSON.
        if len(p.stdout)>1024*1024 or required and p.returncode!=0:raise DiagnosticRefused('readonly_command_failed')
        return p.returncode,p.stdout
    try:
        # Refuse writing even the diagnostic receipt on forbidden backing storage.
        _,storage=command(['findmnt','-rn','-o','SOURCE','--target','/tmp'])
        source=storage.decode().strip().split('[',1)[0]
        if not source or source.startswith('/dev/sda') or source.startswith('/dev/') and os.path.realpath(source).startswith('/dev/sda'):
            raise DiagnosticRefused('forbidden_or_unknown_receipt_storage')
        before=json.loads((RECEIPT/'containers-before.json').read_text())
        result={'schema':'professor-stage2-readonly-diagnosis-v1','checked_at':datetime.now(timezone.utc).isoformat(),
            'failed_run':'20261029T094222Z-c65a7ae397ac','containers':{},'privileged_changes':False,'providers_enabled':False}
        for service in SERVICES:
            _,ids=command(['docker','ps','-aq','--no-trunc','--filter','label=com.docker.compose.project=proptech-selfhost',
                '--filter','label=com.docker.compose.service='+service])
            ids=ids.decode().split()
            if len(ids)!=1 or not re.fullmatch(r'[0-9a-f]{64}',ids[0]):raise DiagnosticRefused('container_identity_ambiguous')
            _,raw=command(['docker','inspect','--format',INSPECT_TEMPLATE,ids[0]])
            item=json.loads(raw)
            item['same_container_as_before']=item['id']==before[service]['id']
            item['same_image_as_before']=item['image_id']==before[service]['image_id']
            if service.startswith('postgres_'):
                item['same_data_volume_as_before']=[m for m in item['mounts'] if m['Destination']=='/var/lib/postgresql/data']==before[service]['data_mount']
            result['containers'][service]=item
        api=result['containers']['api']['id']
        payload=database_payload((REPO/'scripts/ops/professor_stage2_probe.py').read_bytes()).encode()
        _,raw=command(['docker','exec','-i',api,'python','-B','-'],data=payload,timeout=180)
        result['database_diagnostic']=json.loads(raw)
        code='import os,stat,json;print(json.dumps({n:{"uid":(s:=os.stat("/run/secrets/"+n)).st_uid,"gid":s.st_gid,"mode":oct(stat.S_IMODE(s.st_mode)),"device":s.st_dev,"inode":s.st_ino,"size":s.st_size} for n in '+repr(CORE)+'}))'
        _,raw=command(['docker','exec',api,'python','-B','-c',code])
        result['api_active_secret_metadata']=json.loads(raw)
        host={}
        for name in CORE:
            s=(STAGING/name).lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise DiagnosticRefused('host_secret_metadata_unsafe')
            host[name]={'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode)),'device':s.st_dev,'inode':s.st_ino,'size':s.st_size}
        result['host_secret_metadata']=host
        result['api_mounts_match_current_host_inodes']={n:host[n]==result['api_active_secret_metadata'].get(n) for n in CORE}
        candidate='proptech-professor-api:stage2-20261029t094222z-c65a7ae397ac'
        code,_=command(['docker','image','inspect','--format','{{json .Id}}',candidate],required=False)
        result['candidate_image_present']=code==0
        result['stage2_override_exists']=(Path('/etc/proptech-selfhost')/'stage2-secrets.override.yml').exists()
        output=Path(tempfile.mkdtemp(prefix='professor-stage2-readonly-',dir='/tmp'))
        target=output/'diagnosis.json'
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
        with os.fdopen(fd,'w') as stream:json.dump(result,stream,indent=2);stream.write('\n')
        os.chmod(target,0o644);os.chmod(output,0o755)
        print(json.dumps({'status':'COLLECTED','database_contract_status':result['database_diagnostic'].get('database_contract_status'),
            'sanitized_receipt':str(target),'activation_performed':False}));return 0
    except BaseException:
        print('{"status":"REFUSED","reason_code":"readonly_diagnosis_failed_details_suppressed"}');return 1


if __name__=='__main__':
    raise SystemExit(main())
