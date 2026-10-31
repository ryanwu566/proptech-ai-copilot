#!/usr/bin/env python3
"""Operator-only additive user schema provisioning. Default: value-free plan.

No image builds, configuration activation, container recreation or volume changes.
Generated credentials travel only via private files and command stdin.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import resource
import subprocess
import sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from services.selfhost_secret_files import SecretRefused, atomic_secret_write, open_directory, read_secret
from scripts.ops.professor_server_secrets import check_backing_storage, ensure_private

ISSUER='https://flyhsjcynreuofbcdxod.supabase.co/auth/v1'
ROLE='professor_user_runtime'
STORE=Path('/etc/proptech-selfhost/secrets')
STAGED=Path('/run/proptech-selfhost/secrets')
EVIDENCE=Path('/var/backups/proptech-selfhost/stage4a-userdb')
MIGRATION=ROOT/'database/userdb/001_professor_users.sql'


def require(condition,reason):
    if not condition: raise SecretRefused(reason)


def plan():
    return {'status':'PLAN_ONLY','database':'proptech_app','schema':'professor_user',
            'runtime_role':ROLE,'identity_provider':'existing_supabase',
            'existing_auth_users_modified':False,'container_recreation':False,
            'serving_tables_modified':False,'secret_values_returned':False,
            'authority_approval':'separate_gate_false_until_reconciled',
            'changes':['private full app backup','fresh schema and direct-login role',
                       'new isolated runtime URL files','sanitized receipt and rollback guide']}


def run(args,data=None,timeout=60):
    p=subprocess.run(args,input=data,capture_output=True,timeout=timeout,
                     env={'PATH':os.defpath,'HOME':'/root'})
    require(p.returncode==0,'operator_command_failed_details_suppressed')
    return p.stdout


def scram(password):
    salt=secrets.token_bytes(16); iterations=32768
    salted=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,iterations)
    stored=hashlib.sha256(hmac.new(salted,b'Client Key','sha256').digest()).digest()
    server=hmac.new(salted,b'Server Key','sha256').digest()
    enc=lambda x:base64.b64encode(x).decode()
    return f'SCRAM-SHA-256${iterations}:{enc(salt)}${enc(stored)}:{enc(server)}'


def stage_existing(store,staging,*,owner=0,gid=10001,store_gid=0):
    """Restore only the missing staged file; never rotate an existing mount."""
    name='professor_user_database_url'
    value=read_secret(store,name,owner=owner,gid=store_gid,mode=0o600)
    try:
        p=urlsplit(value)
        require(p.scheme in {'postgres','postgresql'} and p.username==ROLE
            and p.hostname=='postgres_app' and p.path=='/proptech_app'
            and p.port in {None,5432} and p.password and len(p.password)>=32
            and not p.query and not p.fragment,'stored_userdb_url_invalid')
    except ValueError: raise SecretRefused('stored_userdb_url_invalid') from None
    try: (staging/name).lstat()
    except FileNotFoundError:
        atomic_secret_write(staging,name,value,owner=owner,gid=gid,mode=0o440)
        return {'status':'STAGED','values_returned':False,'database_mutations':False}
    existing=read_secret(staging,name,owner=owner,gid=gid,mode=0o440)
    require(hmac.compare_digest(existing,value),'staged_userdb_secret_conflict')
    return {'status':'UNCHANGED','values_returned':False,'database_mutations':False}


def restage():
    require(os.geteuid()==0,'operator_root_required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    import fcntl
    lock=os.open('/run/proptech-stage4a-provision.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        check_backing_storage(STAGED)
        ensure_private(STAGED.parent)
        ensure_private(STAGED)
        for p in [STORE,STAGED]:
            check_backing_storage(p)
            os.close(open_directory(p,private=True))
        print(json.dumps(stage_existing(STORE,STAGED)))
    finally:os.close(lock)


def validate_mounts(mounts):
    for mount in mounts:
        if mount['Type']=='tmpfs':
            require(mount.get('Destination') in {'/tmp','/var/run/postgresql'}
                and not mount.get('Source'),'database_tmpfs_mount_unsupported')
            continue
        require(mount['Type'] in {'bind','volume'},'database_mount_type_unsupported')
        require(bool(mount.get('Source')),'database_mount_source_missing')
        check_backing_storage(Path(mount['Source']))


def provision():
    require(os.geteuid()==0,'operator_root_required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    os.umask(0o077)
    import fcntl
    lock=os.open('/run/proptech-stage4a-provision.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for path in [ROOT,STORE,STAGED,EVIDENCE]:
            check_backing_storage(path)
        for path in [STORE,STAGED]:
            os.close(open_directory(path,private=True))
        ensure_private(EVIDENCE)
        target=EVIDENCE/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4))
        target.mkdir(mode=0o700)
        report=plan(); report['status']='PARTIAL'; report['phase']='preflight'
        try:
            docker_root=Path(json.loads(run(['docker','info','--format','{{json .DockerRootDir}}'])))
            check_backing_storage(docker_root)
            ids=run(['docker','ps','--filter','label=com.docker.compose.project=proptech-selfhost',
                     '--filter','label=com.docker.compose.service=postgres_app','--format','{{.ID}}']).decode().split()
            require(len(ids)==1,'app_database_container_ambiguous')
            container=ids[0]
            inspect=json.loads(run(['docker','inspect',container]))[0]
            require(not inspect['HostConfig'].get('PortBindings'),'postgres_host_binding_forbidden')
            validate_mounts(inspect['Mounts'])
            base=['docker','exec','-i','--user','70:70',container,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','postgres','-d','proptech_app']
            probe=run(base,b"SELECT current_database(),current_user,to_regnamespace('professor_user') IS NULL,NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='professor_user_runtime');").decode().strip()
            require(probe=='proptech_app|postgres|t|t','fresh_userdb_or_role_required')
            for folder in [STORE,STAGED]:
                require(not (folder/'professor_user_database_url').exists(),'userdb_secret_already_exists')
            report['phase']='database_backup'
            with (target/'proptech_app.pgdump').open('xb') as out:
                backup=subprocess.run(['docker','exec','--user','70:70',container,'pg_dump','-U','postgres','-d','proptech_app','-Fc'],stdout=out,stderr=subprocess.PIPE,timeout=600,env={'PATH':os.defpath})
                require(backup.returncode==0,'backup_failed')
                out.flush(); os.fsync(out.fileno())
            # Check a nonempty custom-format header without displaying user data.
            with (target/'proptech_app.pgdump').open('rb') as src:
                require(src.read(5)==b'PGDMP','backup_format_invalid')
            with (target/'proptech_app.pgdump').open('rb') as src:
                verified=subprocess.run(['docker','exec','-i','--user','70:70',container,'pg_restore','--list'],stdin=src,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=120,env={'PATH':os.defpath})
                require(verified.returncode==0,'backup_directory_invalid')
            (target/'ROLLBACK.md').write_text('No activation performed. Leave additive schema/data and private credential files intact. If later API activation fails, restore previous API image/profile only; no database/volume removal. App backup retained as proptech_app.pgdump for separately reviewed recovery. authority_reviewed remains false.\n')
            report['phase']='additive_schema'
            password=secrets.token_urlsafe(48)
            url='postgresql://'+ROLE+':'+password+'@postgres_app/proptech_app'
            verifier=scram(password)
            # Token-safe generated verifier, not plaintext; psql receives stdin only.
            sql=("BEGIN; SET LOCAL lock_timeout='2s'; SET LOCAL statement_timeout='30s'; "
                 "CREATE ROLE professor_user_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '"+verifier+"';\n"+
                 MIGRATION.read_text()+"\nINSERT INTO professor_user.configuration(issuer) VALUES ('"+ISSUER+"');\nGRANT CONNECT ON DATABASE proptech_app TO professor_user_runtime;\nCOMMIT;")
            # Persist recovery material before database commit; never overwrite on retry.
            atomic_secret_write(STORE,'professor_user_database_url',url)
            run(base,sql.encode())
            report['schema_applied']=True
            stage_existing(STORE,STAGED)
            report.update(status='PASS_PROVISIONED_NOT_ACTIVE',phase='complete',
                          authority_reviewed=False,activation_performed=False,
                          migration_sha256=hashlib.sha256(MIGRATION.read_bytes()).hexdigest())
        except Exception:
            report['status']='REFUSED'; report['reason_code']='provision_failed_review_receipt_before_retry'
            raise
        finally:
            (target/'apply-report.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({'status':report['status'],'evidence':str(target),'activation_performed':False,'values_returned':False}))
    finally: os.close(lock)


def main():
    try:
        # No free-text secret arguments; only an explicit operator apply flag.
        if sys.argv[1:]==['--plan'] or not sys.argv[1:]: print(json.dumps(plan())); return 0
        if sys.argv[1:]==['--stage']: restage(); return 0
        require(sys.argv[1:]==['--apply'],'invalid_arguments')
        provision(); return 0
    except Exception:
        print(json.dumps({'status':'REFUSED','reason_code':'stage4a_provisioning_refused','values_returned':False})); return 1


if __name__=='__main__': raise SystemExit(main())
