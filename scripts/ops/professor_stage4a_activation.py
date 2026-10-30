#!/usr/bin/env python3
"""Operator-only clean-image review and API-only Stage 4A activation.

--apply builds/scans/tests the exact candidate and actual Compose merge BEFORE
asking ACTIVATE. No provisioning, secret installation, provider activation or
database container recreation. The agent must never execute --apply.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import inspect
import json
import os
from pathlib import Path
import re
import resource
import shlex
import signal
import stat
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from scripts.ops import professor_stage2_activation as shared
from scripts.ops.professor_stage4a_authority import BACKEND_ISSUER as ISSUER, AUDIENCE, fingerprint, evaluate
from scripts.ops.professor_stage4a_postprovision import CATALOG_SQL, ROLE_SQL, catalog_for_server, peer_command, guard_expectations
from services.selfhost_secret_files import CORE, SecretRefused, sensitive_name, read_secret, open_directory

Refused=shared.Refused
require=shared.require
STAGED=shared.STAGED
ETC=shared.ETC
USER_SECRET='professor_user_database_url'
USER_TARGET='/run/professor-userdb/'+USER_SECRET
ENTRYPOINT='scripts/ops/professor_stage4a_entrypoint.py'
HOST_REPO=Path('/home/andy/proptech-ai-copilot')
DESTINATION=ETC/'stage4a-auth.override.yml'
APPROVAL=ETC/'stage4a-authority-approval.json'
EVIDENCE=Path('/var/backups/proptech-selfhost/stage4a-activation')
FILES=(HOST_REPO/'docker-compose.selfhost.yml',ETC/'datasets.override.yml',
       ETC/'valuation.override.yml',ETC/'local-frontend.override.yml',ETC/'stage2-secrets.override.yml')
ENV_DELTA={'PROFESSOR_USERDB_ENABLED':'true','SUPABASE_JWT_ISSUER':ISSUER,'SUPABASE_JWT_AUDIENCE':AUDIENCE}
FINGERPRINT=fingerprint(ISSUER.removesuffix('/auth/v1'))[1]
MODEL='plvr-gross-v1-bccf2ec1bc-dcc6587c76b3-6493b5f7'
MODEL_SHA='54eba6a04069b0f8d569c2fe62bbe1ca70771b5594cb220e908e9f7e3524fac4'
ACCEPTED_API_IMAGE='sha256:035a049691b0038f7508acc00c3e9bb82c101a295c9f45edcea8d1b03b3d42a0'
RECREATE_TIMEOUT=240
API_PHASE_TIMEOUT=300  # 240-second health deadline plus bounded Docker reads
PROXY_PHASE_TIMEOUT=150  # 120-second recovery deadline plus in-flight requests
ROLLBACK_TIMEOUT=RECREATE_TIMEOUT+API_PHASE_TIMEOUT+PROXY_PHASE_TIMEOUT+120


def override_bytes(image,commit):
    require(re.fullmatch(r'(?:sha256:)[a-f0-9]{64}',image),'immutable_image_required')
    require(re.fullmatch(r'[a-f0-9]{40}',commit),'commit_invalid')
    raw=(ROOT/'infra/selfhost/professor-userdb.override.yml').read_text()
    token='${PROFESSOR_STAGE4A_API_IMAGE:?reviewed clean Stage 4A image required}'
    require(raw.count(token)==1,'image_template_contract_changed')
    raw=raw.replace(token,image)
    raw=raw.replace('    environment:\n','    environment:\n      RELEASE_COMMIT_SHA: "'+commit+'"\n')
    return raw.encode()


def validate_models(before,after,image,commit):
    """Only one API image/profile delta; every other service byte-for-byte same."""
    require(before.get('name')==after.get('name')=='proptech-selfhost','project_name_mismatch')
    require(set(before)==set(after),'compose_topology_changed')
    require({k:v for k,v in before.items() if k not in {'services','secrets'}}==
            {k:v for k,v in after.items() if k not in {'services','secrets'}},'compose_global_changed')
    expected_secrets=deepcopy(before['secrets'])
    require(USER_SECRET not in expected_secrets,'user_secret_already_declared')
    expected_secrets[USER_SECRET]={'file':str(STAGED/USER_SECRET)}
    if 'name' in after['secrets'].get(USER_SECRET,{}):
        expected_secrets[USER_SECRET]['name']='proptech-selfhost_'+USER_SECRET
    require(after['secrets']==expected_secrets,'unreviewed_secret_definition')
    require(set(before['services'])==set(after['services']),'service_set_changed')
    for service in set(before['services'])-{'api'}:
        require(before['services'][service]==after['services'][service],'non_api_service_changed')
    for kind in ('app','usage'):
        db=after['services']['postgres_'+kind]
        require(not db.get('ports') and db.get('network_mode')!='host','postgres_public')
        require(set(db['networks'])=={kind+'_db'} and after['networks'][kind+'_db'].get('internal') is True,'postgres_network')
        require(shared.secret_names(db)=={kind+'_admin_password'},'database_admin_separation')
        require(len([m for m in db['volumes'] if m['target']=='/var/lib/postgresql/data' and m['type']=='volume'])==1,'database_volume_invalid')
    proxy=after['services']['reverse_proxy']
    ports=proxy.get('ports',[])
    require(len(ports)==1 and ports[0].get('host_ip')=='127.0.0.1' and str(ports[0].get('published'))=='8080' and ports[0].get('target')==8080,'proxy_not_loopback')
    old,new=before['services']['api'],after['services']['api']
    mutable={'image','pull_policy','entrypoint','command','environment','secrets','healthcheck'}
    require({k:v for k,v in old.items() if k not in mutable}=={k:v for k,v in new.items() if k not in mutable},'api_infrastructure_changed')
    require(new.get('image')==image and new.get('pull_policy')=='never' and not new.get('ports') and new.get('network_mode')!='host','api_image_or_port_invalid')
    require(new.get('entrypoint')==['python',ENTRYPOINT] and new.get('command')==['api'],'entrypoint_invalid')
    expected_health=deepcopy(old['healthcheck']);expected_health['test']=['CMD','python',ENTRYPOINT,'health']
    require(new.get('healthcheck')==expected_health,'healthcheck_changed')
    expected_env={**old['environment'],**ENV_DELTA,'RELEASE_COMMIT_SHA':commit}
    require(new['environment']==expected_env,'unreviewed_environment_change')
    guards=[x.partition('=') for x in guard_expectations()]
    require(all(new['environment'].get(k)==v for k,_,v in guards),'provider_or_local_guard_invalid')
    require(not any(sensitive_name(k) or k.startswith('NEXT_PUBLIC_') or (k.startswith('PG') and k!='PGSSLROOTCERT') for k in new['environment']),'credential_environment_forbidden')
    # Old configuration may not silently carry a second Supabase origin.
    for env in (old['environment'],new['environment']):
        for k in ('SUPABASE_URL','SUPABASE_JWT_ISSUER','SUPABASE_JWT_AUDIENCE'):
            expected={'SUPABASE_URL':ISSUER.removesuffix('/auth/v1'),**ENV_DELTA}
            require(k not in env or env[k]==expected[k],'identity_authority_conflict')
    require(shared.secret_names(old)==set(CORE),'old_api_secret_set_invalid')
    mounts=new['secrets']; require(len(mounts)==6,'api_secret_count_invalid')
    expected_targets={**{n:'/run/secrets/'+n for n in CORE},USER_SECRET:USER_TARGET}
    seen=set()
    for m in mounts:
        n=m.get('source');require(n in expected_targets and n not in seen,'api_secret_set_invalid');seen.add(n)
        require(m.get('target',n) in {n,expected_targets[n]} and (n!=USER_SECRET or m.get('target')==USER_TARGET),'secret_alias_forbidden')
        require(after['secrets'][n].get('file')==str(STAGED/n),'secret_source_invalid')
    for service in after['services'].values():
        for mount in service.get('volumes',[]):
            require('Crucial X9' not in str(mount) and not str(mount.get('source','')).startswith('/dev/'),'forbidden_runtime_mount')
    require(all(m.get('type')=='bind' and m.get('read_only') is True for m in new.get('volumes',[])),'api_mount_not_readonly')
    for target in ('/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz','/srv/proptech/datasets/wra/flood/v1'):
        m=[m for m in new['volumes'] if m['target']==target]
        require(len(m)==1 and m[0]['source'].startswith('/srv/proptech-data/DB/'),'local_dataset_missing')


def recreate_command(prefix):
    return [*prefix,'up','-d','--no-deps','--no-build','--pull','never','--force-recreate','api']


def validate_secret_snapshot(stored,staged,baseline=None):
    """Operator-process memory only: no values, lengths or hashes in receipts."""
    names=set(CORE)|{USER_SECRET}
    require(set(stored)==set(staged)==names,'secret_set_changed')
    if baseline is not None:require(set(baseline)==names,'secret_set_changed')
    for n in names:
        require(hmac.compare_digest(stored[n].encode(),staged[n].encode()),'staged_secret_differs_from_store')
        if baseline is not None:
            require(hmac.compare_digest(staged[n].encode(),baseline[n].encode()),'secret_content_changed')


def approval_sql(already_approved):
    # No identity records are read or changed. The setting is a reviewed local
    # application-authority decision, not authentication or password migration.
    condition="issuer='"+ISSUER+"' AND migration_version=1 AND singleton"
    check="IF (SELECT count(*) FROM professor_user.configuration)<>1 THEN RAISE EXCEPTION 'configuration_cardinality'; END IF; "
    if already_approved:
        body=check+"IF NOT EXISTS(SELECT FROM professor_user.configuration WHERE "+condition+" AND authority_reviewed) THEN RAISE EXCEPTION 'approval_drift'; END IF;"
    else:
        body=check+"UPDATE professor_user.configuration SET authority_reviewed=true WHERE "+condition+" AND NOT authority_reviewed; GET DIAGNOSTICS changed=ROW_COUNT; IF changed<>1 THEN RAISE EXCEPTION 'approval_precondition'; END IF;"
    return "SET LOCAL lock_timeout='2s'; SET LOCAL statement_timeout='5s'; DO $approval$ DECLARE changed integer; BEGIN "+body+" END $approval$;"


def candidate_probe_code(commit,approved):
    body='''import json,os
from pathlib import Path
from uuid import UUID
from scripts.ops.professor_stage4a_entrypoint import environment
from services.selfhost_secret_files import CORE,install_log_redaction
from services.professor_userdb import DATABASE_ENV,UserRepository,close_pool,validate_grants
from services.vnext.db_principal import DatabasePrincipalContext
from psycopg_pool import ConnectionPool
from services.vnext.auth import AuthenticatedPrincipal,get_supabase_jwt_verifier
from services.production_identity import backend_identity
env=environment(Path('/run/secrets'),Path('/run/professor-userdb'),dict(os.environ))
install_log_redaction([env[k] for k in (*CORE.values(),DATABASE_ENV)])
os.environ.clear();os.environ.update(env)
assert backend_identity()['commit_sha']=='''+repr(commit)+'''
verifier=get_supabase_jwt_verifier()
assert verifier.issuer=='''+repr(ISSUER)+'''
pool=ConnectionPool(conninfo=env[DATABASE_ENV],min_size=0,max_size=1,timeout=5,
 kwargs={'prepare_threshold':None,'connect_timeout':3,'sslmode':'verify-full','sslrootcert':'/run/selfhost-ca/ca.crt',
         'options':'-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000'})
repo=UserRepository(DatabasePrincipalContext(pool,expected_role='professor_user_runtime'))
p=AuthenticatedPrincipal(UUID(int=0),str(UUID(int=0)),verifier.issuer)
with repo.transaction(p) as c:
 assert c.execute('SHOW transaction_read_only').fetchone()==('on',)
 assert c.execute('SELECT issuer,migration_version,authority_reviewed FROM professor_user.configuration WHERE singleton').fetchone()==('''+repr(ISSUER)+''',1,'''+repr(approved)+''')
 assert c.execute('SELECT current_user,session_user,current_database()').fetchone()==('professor_user_runtime','professor_user_runtime','proptech_app')
 assert c.execute('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()==(True,)
 validate_grants(c)
'''+('from services.professor_userdb import validate_configuration\nvalidate_configuration()\n' if approved else '')+'''
import backend.api_main
pool.close()
close_pool()
print(json.dumps({'status':'PASS','configuration_approved':''' + repr(approved)+''','tls':True,'role':'professor_user_runtime','values_returned':False}))
'''
    return ('import json,sys\ntry:\n'+''.join(' '+line+'\n' for line in body.splitlines())+
            'except Exception:\n print(json.dumps({"status":"REFUSED","reason_code":"candidate_validation_failed","values_returned":False}))\n sys.exit(1)\n')


def wait_proxy_recovery(proxy_id,*,state=None,fetch=None,clock=None,sleep=None,timeout=120):
    """Bounded Docker health AND loopback readiness after asynchronous reload."""
    import json
    import re
    import subprocess
    import time
    from urllib.request import build_opener,ProxyHandler
    if not re.fullmatch('[a-f0-9]{64}',proxy_id):raise RuntimeError('proxy_identity_invalid')
    clock=clock or time.monotonic;sleep=sleep or time.sleep
    if state is None:
        def state():
            result=subprocess.run(['docker','inspect','--format','{{json .State}}',proxy_id],capture_output=True,timeout=10)
            if result.returncode:raise RuntimeError('proxy_state_unavailable')
            return json.loads(result.stdout)
    if fetch is None:
        opener=build_opener(ProxyHandler({}))
        def fetch(path):
            with opener.open('http://127.0.0.1:8080'+path,timeout=3) as response:
                raw=response.read(65537)
                if len(raw)>65536:raise RuntimeError('proxy_response_too_large')
                return json.loads(raw)
    deadline=clock()+timeout
    while clock()<deadline:
        try:
            current=state()
            if current.get('Status') in {'dead','exited'} or current.get('Running') is False:
                raise RuntimeError('proxy_not_running')
            if current.get('Health',{}).get('Status')=='healthy':
                health=fetch('/health');readiness=fetch('/readiness')
                if health.get('status')=='ok' and health.get('readiness')=='ready' and readiness.get('status')=='ready':
                    return {'status':'PASS','proxy_healthy':True,'loopback_readiness':True}
        except Exception:
            pass  # Bounded handoff/health retries; no exception values emitted.
        sleep(1)
    raise RuntimeError('proxy_recovery_timeout')


def proxy_recovery_code(proxy_id):
    require(re.fullmatch('[a-f0-9]{64}',proxy_id),'proxy_identity_invalid')
    return ('import json\n'+inspect.getsource(wait_proxy_recovery)+
            '\ntry:\n print(json.dumps(wait_proxy_recovery('+repr(proxy_id)+')))\n'
            'except Exception:\n print("{\\"status\\":\\"REFUSED\\",\\"reason_code\\":\\"proxy_recovery_timeout\\"}")\n raise SystemExit(1)\n')


def rollback_script(prefix,folder,old_image,override_sha,proxy_id):
    require(re.fullmatch(r'sha256:[a-f0-9]{64}',old_image),'rollback_image_invalid')
    require(re.fullmatch(r'[a-f0-9]{64}',proxy_id),'rollback_proxy_invalid')
    command=recreate_command([*prefix,'-f',str(folder/'rollback-image.json')])
    # Check every original config and the exact new override before moving it.
    inactive=ETC/('.stage4a-inactive-'+folder.name+'.yml')
    move=('import hashlib,os\nfrom pathlib import Path\n'
          'p=Path('+repr(str(DESTINATION))+')\nq=Path('+repr(str(inactive))+')\n'
          'def valid(path):\n return not path.is_symlink() and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()=='+repr(override_sha)+'\n'
          'if p.exists():\n'
          ' if not valid(p) or q.exists() or q.is_symlink():raise RuntimeError("rollback_override_changed")\n'
          ' os.rename(p,q)\n'
          'elif not valid(q):raise RuntimeError("rollback_override_unverified")\n')
    wait='''import json,subprocess,time
deadline=time.monotonic()+240
while time.monotonic()<deadline:
 ids=subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project=proptech-selfhost','--filter','label=com.docker.compose.service=api'],timeout=15).decode().split()
 if len(ids)!=1:raise RuntimeError('rollback_api_ambiguous')
 state=json.loads(subprocess.check_output(['docker','inspect','--format','{{json .State}}',ids[0]],timeout=15))
 if state.get('Health',{}).get('Status')=='healthy':break
 if state.get('Status') in {'dead','exited'}:raise RuntimeError('rollback_api_failed')
 time.sleep(2)
else:raise RuntimeError('rollback_health_timeout')
'''
    clean_env=['/usr/bin/env','-i','PATH=/usr/bin:/bin','HOME=/root','LANG=C.UTF-8',
        'DOCKER_HOST=unix:///var/run/docker.sock','DOCKER_CONFIG='+str(folder/'docker-config'),'COMPOSE_PROFILES=','/bin/bash','-s']
    return ('#!/bin/bash\nset -euo pipefail\nexec '+shlex.join(clean_env)+" <<'PROFESSOR_STAGE4A_ROLLBACK_V1'\nset -euo pipefail\n"
        'test "$(id -u)" = 0\nsha256sum --check --status '+shlex.quote(str(folder/'original-config.sha256'))+'\n'
        'docker image inspect '+shlex.quote(old_image)+' >/dev/null\n'
        'python3 -I -B -c '+shlex.quote(move)+'\n'
        'timeout --signal=TERM --kill-after=10s '+str(RECREATE_TIMEOUT)+'s '+shlex.join(command)+'\n'
        'timeout --signal=TERM --kill-after=10s '+str(API_PHASE_TIMEOUT)+'s python3 -I -B -c '+shlex.quote(wait)+'\n'
        'timeout --signal=TERM --kill-after=10s 30s docker exec '+shlex.quote(proxy_id)+' nginx -s reload\n'
        'timeout --signal=TERM --kill-after=10s '+str(PROXY_PHASE_TIMEOUT)+'s python3 -I -B -c '+shlex.quote(proxy_recovery_code(proxy_id))+'\n'
        'PROFESSOR_STAGE4A_ROLLBACK_V1\n')


class Activation(shared.Activation):
    def __init__(self):
        super().__init__()
        self.image='proptech-professor-api:stage4a-'+self.run_id.lower()
        self.backend='proptech-professor-backend:stage4a-'+self.run_id.lower()
        self.report={'schema':'professor-stage4a-activation-v1','status':'PARTIAL','run_id':self.run_id,
                     'stage4a_complete':False,'activation_performed':False,'identity_provider':'supabase',
                     'profile_installed':False,'api_recreation_attempted':False,
                     'application_data_authority':'professor_postgresql','authority_sha256':FINGERPRINT,
                     'secret_values_returned':False,'secret_files_modified':False,
                     'database_container_or_volume_recreation':False,'source_transactions_modified':False}
        self.env['GIT_OPTIONAL_LOCKS']='0'

    def prefix(self,extra=None):
        command=['docker','compose','--project-name','proptech-selfhost','--project-directory',str(HOST_REPO),'--env-file',str(ETC/'compose.env')]
        for path in (*FILES,*((extra,) if extra else ())):command.extend(['-f',str(path)])
        return command

    def write(self,name,raw,mode=0o600):
        self.scanner.check_bytes(raw)
        fd=os.open(self.root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())

    def peer(self,sql,write=False):
        command=peer_command(self.before['postgres_app']['Id'])
        if write:
            command=[v.replace('default_transaction_read_only=on','default_transaction_read_only=off') for v in command]
        return self.run(command,data=('BEGIN;\n'+sql+'\nCOMMIT;\n').encode())

    def schema(self):
        catalog=json.loads(self.peer(CATALOG_SQL))
        role=json.loads(self.peer(ROLE_SQL))
        expected=json.loads((ROOT/'reports/professor-stage4a-auth-userdb/expected-catalog.json').read_text())
        require(expected['migration_sha256']==shared.digest(ROOT/'database/userdb/001_professor_users.sql'),'migration_source_changed')
        require(catalog==catalog_for_server(expected['catalog'],role.get('server_version_num')),'catalog_drift')
        required=('database_connect','role_safe','no_external_reads','no_external_writes','no_callable_definer','issuer_matches','database_matches')
        require(all(role.get(k) is True for k in required) and role.get('configuration_rows')==1,'role_or_configuration_drift')
        require(type(role.get('authority_reviewed')) is bool,'approval_state_invalid')
        return role

    def stable(self):
        for path,digest in self.original_hashes.items():
            require(shared.digest(Path(path))==digest,'original_configuration_changed')
        require(self.run(['git','rev-parse','HEAD']).decode().strip()==self.commit,'source_commit_changed')
        self.run(['git','diff','--exit-code','HEAD','--','.'])
        require(shared.digest(HOST_REPO/'frontend_next/next-env.d.ts')==self.frontend_sha,'frontend_changed')
        for name,metadata in self.host_secrets.items():
            require(shared.file_metadata(STAGED/name)==metadata,'secret_metadata_changed')
        stored={n:read_secret(shared.STORE,n,gid=0,mode=0o600) for n in (*CORE,USER_SECRET)}
        staged={n:read_secret(STAGED,n) for n in (*CORE,USER_SECRET)}
        validate_secret_snapshot(stored,staged,self.private_staged_values)

    def assert_unchanged(self):
        # Includes all project/companion containers, not just database services.
        require(self.container_state()==self.before_state,'containers_changed_concurrently')
        self.assert_live(self.snapshot())

    def container_state(self):
        raw=self.docker('ps','-aq','--no-trunc').decode().split()
        require(raw and all(re.fullmatch('[a-f0-9]{64}',x) for x in raw),'container_inventory_invalid')
        result={}
        for item in json.loads(self.docker('inspect',*raw)):
            if item['Config'].get('Labels',{}).get('proptech.stage2.run')==self.run_id:continue
            # No environment, labels or log contents in the saved inventory.
            result[item['Id']]={'image':item['Image'],'started':item['State']['StartedAt'],
                'running':item['State']['Running'],'mounts':item['Mounts']}
        return result

    def preflight(self):
        from scripts.ops.professor_server_secrets import check_backing_storage,ensure_private
        from services.professor_activation_scan import SecretScanner
        require(os.geteuid()==0,'operator_root_required')
        require(not DESTINATION.exists() and not DESTINATION.is_symlink(),'activation_override_already_exists')
        self.commit=self.run(['git','rev-parse','HEAD']).decode().strip()
        require(re.fullmatch('[a-f0-9]{40}',self.commit),'commit_invalid')
        # Root never imports uncommitted code or exports a dirty source snapshot.
        self.run(['git','diff','--exit-code','HEAD','--','.'])
        require(not self.run(['git','ls-files','--others','--exclude-standard']).strip(),'untracked_source_present')
        require(self.run(['git','branch','--show-current']).decode().strip()=='server/stage4a-auth-userdb-20261030','source_branch_invalid')
        self.frontend_sha=shared.digest(HOST_REPO/'frontend_next/next-env.d.ts')
        require(self.frontend_sha==shared.FRONTEND_SHA256,'frontend_hash_changed')
        values=shared.installed_values()  # internally only, never returned or logged
        self.private_staged_values={n:read_secret(STAGED,n) for n in (*CORE,USER_SECRET)}
        stored={n:read_secret(shared.STORE,n,gid=0,mode=0o600) for n in (*CORE,USER_SECRET)}
        validate_secret_snapshot(stored,self.private_staged_values)
        self.scanner=SecretScanner([*values.values(),*self.private_staged_values.values()])
        require(USER_SECRET in {Path(k).name for k in values},'installed_user_credential_missing')
        for path in (ROOT,HOST_REPO,EVIDENCE,ETC,STAGED):check_backing_storage(path)
        os.close(open_directory(ETC))
        ensure_private(EVIDENCE)
        self.root=EVIDENCE/self.run_id;self.root.mkdir(mode=0o700)
        configdir=self.root/'docker-config';configdir.mkdir(mode=0o700)
        self.env['DOCKER_CONFIG']=str(configdir)
        info=json.loads(self.docker('info','--format','{{json .}}'))
        check_backing_storage(Path(info['DockerRootDir']))
        for path in (Path('/var/lib/containerd'),Path('/run/containerd')):
            if path.exists():check_backing_storage(path)
        require('rootless' not in str(info.get('SecurityOptions',[])),'unexpected_docker_daemon')
        self.host_secrets={n:shared.file_metadata(STAGED/n) for n in (*CORE,USER_SECRET)}
        for n,m in self.host_secrets.items():
            require(m['uid']==0 and m['gid']==10001 and m['mode']=='0o440' and m['size']>0,'secret_metadata_invalid')
        os.close(open_directory(STAGED,private=True))
        authority=json.loads((ROOT/'reports/professor-stage4a-auth-userdb/auth-authority.json').read_text())
        require(authority.get('status')=='PASS' and authority.get('authority_sha256')==FINGERPRINT and authority.get('issuer_conflict',False) is False,'authority_evidence_invalid')
        base=ROOT/'reports/professor-stage4a-auth-userdb'
        for name,d in authority['proof_source_hashes'].items():
            require(Path(name).name==name and shared.digest(base/name)==d,'authority_evidence_drift')
        evaluated=evaluate(json.loads((base/'frontend-authority-observation.json').read_text()),json.loads((base/'provider-authority-metadata.json').read_text()))
        require(evaluated.get('status')=='PASS' and evaluated.get('authority_sha256')==FINGERPRINT,'authority_reconciliation_failed')
        self.before=self.snapshot();self.data_mounts={s:[m for m in self.before[s]['Mounts'] if m['Destination']=='/var/lib/postgresql/data'] for s in ('postgres_app','postgres_usage')}
        self.assert_live(self.before)
        self.docker('exec',self.before['reverse_proxy']['Id'],'nginx','-t')
        require(self.before['api']['Image']==ACCEPTED_API_IMAGE,'accepted_api_image_changed')
        require(self.before['api']['Config']['Labels'].get('com.docker.compose.project.config_files','').split(',')==[str(p) for p in FILES],'active_compose_chain_changed')
        self.before_model=self.json_command([*self.prefix(),'config','--format','json'])
        self.original_hashes={}
        for i,path in enumerate((*FILES,ETC/'compose.env',ETC/'runtime.env')):
            m=shared.file_metadata(path)
            if path.is_relative_to(ETC):require(m['uid']==0 and m['mode'] in {'0o600','0o640'},'configuration_permissions_invalid')
            require(not path.is_symlink(),'configuration_symlink')
            raw=path.read_bytes();self.scanner.check_bytes(raw)
            self.original_hashes[str(path)]=shared.digest(path)
            self.write('original-'+str(i)+'-'+path.name,raw)
        self.original_hashes[str(HOST_REPO/'frontend_next/next-env.d.ts')]=self.frontend_sha
        hashes=self.config_hashes()
        require(all(self.before[s]['Config']['Labels'].get('com.docker.compose.config-hash')==hashes[s] for s in shared.SERVICES),'live_compose_drift')
        for s in shared.SERVICES:
            require(self.before_model['services'][s]['image']==self.before[s]['Config']['Image'],'live_image_config_drift')
        for s,mounts in self.data_mounts.items():
            require(len(mounts)==1,'database_volume_missing')
            check_backing_storage(Path(mounts[0]['Source']))
        self.before_state=self.container_state()
        self.before_schema=self.schema();self.approved=self.before_schema['authority_reviewed']
        if self.approved:
            m=shared.file_metadata(APPROVAL)
            require(m['uid']==0 and m['mode']=='0o600' and json.loads(APPROVAL.read_text())==self.approval_record(),'approval_receipt_invalid')
        self.probe_source=(ROOT/'scripts/ops/professor_stage2_probe.py').read_bytes()
        self.before_db=self.probe('--database');self.save('database-before.json',self.before_db)
        self.save('api-before.json',self.probe('--api-host'))
        self.save('stage3-before.json',self.stage3())
        self.save('schema-before.json',self.before_schema)
        self.save('containers-before.json',self.sanitized_containers(self.before))
        self.save('secret-host-metadata.json',self.host_secrets)
        self.save('approval-review.json',self.approval_record())
        self.report.update(source_commit=self.commit,source_worktree=str(ROOT),
            database_authority_approval='RECORDED_AND_APPLIED' if self.approved else 'RECORDED_REVIEW_PENDING_OPERATOR_SQL',frontend_sha256=self.frontend_sha)

    def approval_record(self):
        return {'schema':'professor-stage4a-authority-approval-v1','identity_authority':'supabase',
                'issuer':ISSUER,'audience':AUDIENCE,'authority_sha256':FINGERPRINT,
                'application_data_authority':'professor_postgresql','database':'proptech_app','schema_name':'professor_user',
                'existing_users_preserved':True,'identity_or_password_migration':False,
                'review_basis':'accepted public frontend, provider metadata and exact local catalog reconciliation',
                'operator_authorization':'Stage 4A final controlled API activation; ACTIVATE required for SQL flag'}

    def stage3(self):
        # Existing standalone inference consumer is observed, never recreated.
        source='''import json
from urllib.request import build_opener,ProxyHandler,Request
o=build_opener(ProxyHandler({}))
def get(p):
 with o.open('http://127.0.0.1:8081'+p,timeout=15) as r:return json.load(r)
h=get('/health');s=get('/valuation/ml/v1/status')
assert h['status'] in {'ok','healthy'}
payload={'transaction_date':'2026-10-29','city':'新北市','district':'新莊區',
 'building_type':'公寓(5樓含以下無電梯)','main_use':'住家用','area_ping':30.0,
 'floor':3,'total_floor':5,'building_age_years':20.0}
request=Request('http://127.0.0.1:8081/valuation/ml/v1/estimate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
with o.open(request,timeout=15) as response:estimate=json.load(response)
assert estimate['status']=='available' and estimate['is_actionable'] is False
assert estimate['model_version']==s['model_version'] and estimate['model_manifest_sha256']==s['manifest_sha256']
print(json.dumps({'health':h,'data_status':s,'estimate':estimate}))
'''
        result=json.loads(self.run([sys.executable,'-B','-'],data=source.encode()))
        # Schema is checked against the actual accepted data-status contract.
        status=result['data_status']
        require(status.get('status')=='available' and status.get('model_version')==MODEL and status.get('manifest_sha256')==MODEL_SHA and status.get('is_actionable') is False,'stage3_model_identity_drift')
        return result

    def prepare(self):
        self.preflight()
        super().build(source_commit=self.commit)
        self.override_bytes=override_bytes(self.image_id,self.commit)
        self.candidate_override=self.root/'candidate.override.yml';self.write('candidate.override.yml',self.override_bytes)
        self.after_model=self.json_command([*self.prefix(self.candidate_override),'config','--format','json'])
        validate_models(self.before_model,self.after_model,self.image_id,self.commit)
        self.after_hashes=self.config_hashes(self.candidate_override)
        require(all(self.after_hashes[k]==self.config_hashes()[k] for k in self.after_hashes if k!='api'),'non_api_hash_changed')
        self.save('compose-before.json',self.before_model);self.save('compose-after.json',self.after_model)
        self.candidate(self.approved)
        self.prepare_rollback()
        self.stable();self.assert_unchanged()
        self.plan={'status':'PASS','source_commit':self.commit,'candidate_image_id':self.image_id,
            'compose_files_before':[str(p) for p in FILES],'compose_file_added':str(DESTINATION),
            'recreate_only':['api'],'unchanged_consumers':['postgres_app','postgres_usage','reverse_proxy','stage3_companion'],
            'reverse_proxy_operation':'nginx configuration test and worker reload after API healthy; no container restart/recreation',
            'database_volumes_recreated':False,'secret_files_modified':False,'secret_mounts':'existing core five plus dedicated user runtime URL, read-only',
            'authority_approval_record':self.approval_record(),'database_write':'conditional authority_reviewed flag only',
            'ports_changed':False,'postgres_private':True,'8080_loopback':True,'paid_providers_disabled':True,'market_ops_disabled':True,
            'rollback':str(self.root/'ROLLBACK.sh'),'evidence':str(self.root),'activation_performed':False}
        self.save('change-plan.json',self.plan)
        print(json.dumps(self.plan,sort_keys=True),flush=True)

    def flags(self,network):
        flags=['--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges',
               '--pids-limit','128','--memory','2g','--cpus','1','--tmpfs','/tmp:rw,noexec,nosuid,size=128m,uid=10001,gid=10001']
        for n in CORE:flags+=['--mount','type=bind,src='+str(STAGED/n)+',dst=/run/secrets/'+n+',readonly']
        flags+=['--mount','type=bind,src='+str(STAGED/USER_SECRET)+',dst='+USER_TARGET+',readonly']
        for m in self.after_model['services']['api']['volumes']:
            flags+=['--mount','type=bind,src='+m['source']+',dst='+m['target']+',readonly']
        for k,v in self.after_model['services']['api']['environment'].items():flags+=['--env',k+'='+v]
        return flags

    def candidate(self,approved):
        self.checkpoint('approved-candidate' if approved else 'pending-authority-candidate')
        network=self.after_model['networks']['app_db']['name']
        result=json.loads(self.start_transient([*self.flags(network),'--entrypoint','python',self.image_id,'-E','-B','-c',candidate_probe_code(self.commit,approved)]))
        require(result.get('status')=='PASS' and result.get('configuration_approved') is approved,'candidate_configuration_refused')
        self.start_transient([*self.flags('none'),'--entrypoint','python',self.image_id,'-I','-m','pip','check'])
        reference=json.loads((ROOT/'reports/professor-final-integration/reference-artifact-validation.json').read_text())
        artifacts=json.loads(self.start_transient([*self.flags('none'),'--entrypoint','python',self.image_id,'-B','-c',shared.artifact_probe_code(reference)]))
        require(artifacts.get('status')=='PASS','candidate_artifact_refused')
        name='candidate-approved.json' if approved else 'candidate-pending-approval.json'
        if (self.root/name).exists():name='candidate-approved-revalidated.json'
        self.save(name,result)
        if not (self.root/'candidate-artifacts.json').exists():self.save('candidate-artifacts.json',artifacts)

    def prepare_rollback(self):
        old=self.before['api']['Image']
        require(json.loads(self.docker('image','inspect',old))[0]['Id']==old,'rollback_image_unavailable')
        self.write('rollback-image.json',json.dumps({'services':{'api':{'image':old,'pull_policy':'never'}}}).encode())
        self.write('original-config.sha256',''.join(d+'  '+p+'\n' for p,d in self.original_hashes.items()).encode())
        raw=rollback_script(self.prefix(),self.root,old,hashlib.sha256(self.override_bytes).hexdigest(),self.before['reverse_proxy']['Id'])
        self.write('ROLLBACK.sh',raw.encode(),0o700)
        self.run(['bash','-n',str(self.root/'ROLLBACK.sh')])
        self.write('ROLLBACK.md',('API-only rollback: sudo bash '+str(self.root/'ROLLBACK.sh')+'\n'
            'Restores the immutable previous API image and original five-file Compose chain.\n'
            'The exact Stage 4A override moves to a unique inactive file in /etc/proptech-selfhost (same filesystem). Repeating recovery after a Compose failure is safe.\n'
            'No PostgreSQL restart, schema reversal, data/volume deletion or credential changes.\n'
            'The separately reviewed authority approval remains recorded. All user data is retained.\n'
            'Run health/readiness and the existing Stage 2 read-only probes after manual recovery.\n').encode())

    def approve_authority(self):
        self.checkpoint('record-application-data-authority')
        expected=self.approval_record()
        if APPROVAL.exists():
            m=shared.file_metadata(APPROVAL)
            require(m['uid']==0 and m['mode']=='0o600' and not APPROVAL.is_symlink() and json.loads(APPROVAL.read_text())==expected,'approval_receipt_conflict')
        else:
            self.install_file(APPROVAL,(json.dumps(expected,sort_keys=True)+'\n').encode(),0o600)
        require(self.schema()==self.before_schema,'preapproval_schema_changed')
        self.report.update(authority_sql_attempted=True,database_authority_approval='SQL_RESULT_PENDING_VERIFICATION')
        self.peer(approval_sql(self.approved),write=True)
        after=self.schema();expected_schema={**self.before_schema,'authority_reviewed':True}
        require(after==expected_schema,'approval_changed_other_state')
        self.report.update(database_authority_approval='RECORDED_AND_APPLIED',authority_reviewed=True)
        self.save('authority-approved.json',{'status':'PASS','authority_sha256':FINGERPRINT,'authority_reviewed':True,'identity_users_changed':False})

    def install_file(self,path,raw,mode):
        temporary=ETC/('.stage4a-'+uuid.uuid4().hex)
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
        try:
            with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.link(temporary,path,follow_symlinks=False)
            directory=os.open(ETC,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:temporary.unlink(missing_ok=True)

    def install_override(self):
        self.install_file(DESTINATION,self.override_bytes,0o640)

    def recreate_api(self):
        self.run(recreate_command(self.prefix(DESTINATION)),timeout=RECREATE_TIMEOUT)

    def wait_api(self):self.wait_healthy('api')

    def reload_proxy(self):
        # Static proxy_pass resolves api at startup; refresh the upstream address
        # after recreation without changing proxy config/container identity.
        self.docker('exec',self.before['reverse_proxy']['Id'],'nginx','-t')
        self.docker('exec',self.before['reverse_proxy']['Id'],'nginx','-s','reload')
        result=json.loads(self.run([sys.executable,'-I','-B','-c',proxy_recovery_code(self.before['reverse_proxy']['Id'])],timeout=PROXY_PHASE_TIMEOUT))
        require(result.get('status')=='PASS','proxy_recovery_failed')
        self.save('proxy-recovery.json',result)

    def verify_active(self):
        after=self.snapshot();self.assert_live(after,after=True)
        require(after['api']['Image']==self.image_id,'active_image_mismatch')
        for name in ('postgres_app','postgres_usage','reverse_proxy'):
            require(after[name]['Id']==self.before[name]['Id'] and after[name]['State']['StartedAt']==self.before[name]['State']['StartedAt'],'non_api_consumer_restarted')
        expected_state={k:v for k,v in self.before_state.items() if k!=self.before['api']['Id']}
        current={k:v for k,v in self.container_state().items() if k!=after['api']['Id'] and k in expected_state}
        require(current==expected_state,'existing_companion_or_database_changed')
        require(self.config_hashes(DESTINATION)==self.after_hashes,'active_compose_hash_drift')
        require(after['api']['Config']['Labels'].get('com.docker.compose.config-hash')==self.after_hashes['api'],'active_api_config_drift')
        mounts=[m for m in after['api']['Mounts'] if m['Destination'].startswith(('/run/secrets/','/run/professor-userdb/'))]
        expected={**{n:'/run/secrets/'+n for n in CORE},USER_SECRET:USER_TARGET}
        require(len(mounts)==len(expected),'active_secret_set_mismatch')
        for n,target in expected.items():
            found=[m for m in mounts if m['Destination']==target]
            require(len(found)==1 and found[0]['Source']==str(STAGED/n) and not found[0]['RW'],'active_secret_source_mismatch')
        code='import os,stat,json;print(json.dumps({n:{"uid":(s:=os.stat(p,follow_symlinks=False)).st_uid,"gid":s.st_gid,"mode":oct(stat.S_IMODE(s.st_mode)),"device":s.st_dev,"inode":s.st_ino,"size":s.st_size} for n,p in '+repr(expected)+'.items()}))'
        mounted=json.loads(self.docker('exec',after['api']['Id'],'python','-B','-c',code))
        require(mounted==self.host_secrets,'active_secret_inode_mismatch')
        env=dict(x.split('=',1) for x in after['api']['Config']['Env'])
        require(all(env.get(k)==v for k,v in {**ENV_DELTA,'RELEASE_COMMIT_SHA':self.commit}.items()),'active_auth_authority_mismatch')
        require(not any(sensitive_name(k) or k.startswith('NEXT_PUBLIC_') for k in env),'active_credential_environment')
        self.save('secret-mounts-after.json',mounted)
        self.save('containers-after.json',self.sanitized_containers(after))
        self.docker('exec',after['api']['Id'],'python','-B',ENTRYPOINT,'validate')

    def verify_regressions(self):
        after_db=self.probe('--database');self.save('database-after.json',after_db)
        require(shared.stable_database_snapshot(after_db)==shared.stable_database_snapshot(self.before_db),'stage1_database_changed')
        self.save('api-after.json',self.probe('--api-host'))
        self.save('stage3-after.json',self.stage3())
        # No synthetic users or tokens are submitted to the real runtime.
        code='''import json
from urllib.request import build_opener,ProxyHandler
from urllib.error import HTTPError
o=build_opener(ProxyHandler({}))
for p in ['/v1/account','/v1/session','/v1/profile','/v1/saved-cases']:
 try:o.open('http://127.0.0.1:8080'+p,timeout=15);raise AssertionError()
 except HTTPError as e:assert e.code==401
print(json.dumps({'status':'PASS','unauthenticated_user_data_access':'denied','synthetic_users_created':False}))
'''
        self.save('user-api-after.json',json.loads(self.run([sys.executable,'-B','-'],data=code.encode())))
        for item in self.snapshot().values():self.docker('logs',item['Id'],timeout=120)
        self.stable()

    def activate(self):
        self.stable();self.assert_unchanged()
        self.approve_authority()
        self.candidate(True)
        self.stable();self.assert_unchanged()
        # Mark before file creation so any failure after the atomic link recovers.
        self.checkpoint('install-stage4a-profile')
        self.maintenance=True
        self.install_override();self.report['profile_installed']=True
        self.checkpoint('recreate-api-only')
        self.report.update(api_recreation_attempted=True,api_recreation_outcome='UNVERIFIED')
        self.recreate_api();self.report.update(activation_performed=True,api_recreation_outcome='COMPLETED')
        self.checkpoint('wait-api-health');self.wait_api()
        self.checkpoint('reload-proxy-workers');self.reload_proxy()
        self.checkpoint('post-activation-acceptance')
        self.verify_active();self.verify_regressions()
        self.report.update(status='PASS',activation_performed=True,phase='complete',
            api_image_id=getattr(self,'image_id',None),database_authority_approval='RECORDED_AND_APPLIED',
            only_api_recreated=True,postgresql_private=True,loopback_8080=True,
            completed_at=datetime.now(timezone.utc).isoformat(),
            paid_providers_disabled=True,market_ops_disabled=True,
            authenticated_browser_acceptance='pending frontend integration; no identity tokens supplied to operator tool')
        self.maintenance=False

    def rollback(self):
        self.checkpoint('api-only-rollback')
        signal.signal(signal.SIGINT,signal.SIG_IGN);signal.signal(signal.SIGTERM,signal.SIG_IGN)
        if DESTINATION.exists():
            self.run(['bash',str(self.root/'ROLLBACK.sh')],timeout=ROLLBACK_TIMEOUT)
        self.wait_api()
        restored=self.snapshot();self.assert_live(restored,after=True)
        require(restored['api']['Image']==self.before['api']['Image'],'rollback_image_mismatch')
        for s in ('postgres_app','postgres_usage','reverse_proxy'):
            require(restored[s]['Id']==self.before[s]['Id'] and restored[s]['State']['StartedAt']==self.before[s]['State']['StartedAt'],'rollback_non_api_changed')
        self.save('api-rollback.json',self.probe('--api-host'))
        self.report.update(rollback='PASS_API_ONLY',authority_approval_retained=True,runtime_profile='ORIGINAL_RESTORED')

    def publish(self):
        self.save('acceptance.json',self.report)
        # Whitelist metadata only; protected config/context/rollback stay private.
        from tempfile import mkdtemp
        from scripts.ops.professor_server_secrets import check_backing_storage
        check_backing_storage(Path('/tmp'))
        public=Path(mkdtemp(prefix='professor-stage4a-activation-',dir='/tmp'));os.chmod(public,0o755)
        self.public_receipt=public
        for name in ('acceptance.json','change-plan.json','approval-review.json','authority-approved.json','build.json','image-scan.json',
                     'candidate-pending-approval.json','candidate-approved.json','candidate-approved-revalidated.json','candidate-artifacts.json','containers-before.json','containers-after.json',
                     'secret-host-metadata.json','secret-mounts-after.json','database-before.json','database-after.json','api-before.json','api-after.json',
                     'schema-before.json','stage3-before.json','stage3-after.json','proxy-recovery.json','user-api-after.json','api-rollback.json','containers-failure.json'):
            path=self.root/name
            if path.exists():
                raw=path.read_bytes();self.scanner.check_bytes(raw)
                fd=os.open(public/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
                with os.fdopen(fd,'wb') as f:f.write(raw)
                os.chmod(public/name,0o644)
        print(json.dumps({'status':self.report['status'],'evidence':str(self.root),'sanitized_receipt':str(public),'secret_values_returned':False}),flush=True)


def main():
    if sys.argv[1:] not in (['--apply'],['--plan']):
        print('{"status":"REFUSED","reason_code":"invalid_arguments"}');return 1
    if os.geteuid()!=0:
        print('{"status":"REFUSED","reason_code":"operator_root_required"}');return 1
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.umask(0o077)
    runner=Activation();locks=[]
    try:
        from scripts.ops.professor_server_secrets import check_backing_storage
        check_backing_storage(Path('/run'))
        for name in ('proptech-stage2-activation.lock','proptech-stage4a-provision.lock','proptech-stage4a-activation.lock'):
            fd=os.open('/run/'+name,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600);locks.append(fd)
            s=os.fstat(fd);require(s.st_uid==0 and s.st_nlink==1 and stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode)==0o600,'lock_unsafe')
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if sys.argv[1]=='--apply':
            require(sys.stdin.isatty() and sys.stdout.isatty(),'interactive_terminal_required')
        def interrupted(signum,frame):raise Refused('operator_interrupted')
        signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
        runner.prepare()
        if sys.argv[1]=='--apply':
            print('Exact scanned candidate, Compose delta and rollback are ready. Type ACTIVATE for authority flag and API-only recreation:',flush=True)
            require(sys.stdin.readline().strip()=='ACTIVATE','operator_confirmation_missing')
            runner.activate()
        else:runner.report.update(status='PLAN_ONLY',activation_performed=False)
    except BaseException as exc:
        reason=str(exc) if isinstance(exc,(Refused,SecretRefused)) else getattr(exc,'reason_code','operation_failed_details_suppressed')
        if not isinstance(reason,str) or not re.fullmatch('[a-z0-9_]+',reason):reason='operation_failed_details_suppressed'
        runner.report.update(status='FAILED',reason_code=reason,failed_phase=runner.report.get('phase','preflight'))
        if runner.maintenance:
            try:runner.save('containers-failure.json',runner.sanitized_containers(runner.snapshot()))
            except BaseException:runner.report['failure_container_state']='UNVERIFIED'
            try:runner.rollback()
            except BaseException:
                runner.report['rollback']='FAILED'
                # Stop only the owned API; never databases or unrelated consumers.
                for ident in runner.service_ids('api'):
                    try:runner.docker('stop','--time','20',ident,timeout=45)
                    except BaseException:runner.report['api_stop']='UNVERIFIED'
    finally:
        try:runner.cleanup()
        except BaseException:runner.report.update(status='FAILED',cleanup='FAILED')
        if runner.root and runner.scanner:
            try:runner.publish()
            except BaseException:
                runner.report.update(status='FAILED',reason_code='receipt_unavailable')
                try:runner.invalidate_receipt()
                except BaseException:pass
                print('{"status":"FAILED","reason_code":"receipt_unavailable"}',flush=True)
        else:print(json.dumps({'status':'REFUSED','reason_code':runner.report.get('reason_code','preflight_failed')}),flush=True)
        for fd in locks:os.close(fd)
    return 0 if runner.report['status'] in {'PASS','PLAN_ONLY'} else 1


if __name__=='__main__':raise SystemExit(main())
