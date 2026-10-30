"""Required provider storage policy. Host operations are operator-only.

No provider API, application startup, Compose apply, service recreation or
credential generation. Existing Stage2 input/storage/scanner contracts are reused.
"""
from __future__ import annotations

import fcntl
import hmac
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit

from scripts.ops import professor_server_secrets as stage2
from services.professor_credentials import ACTIVE
from services.professor_activation_scan import SecretScanner, ScanRefused
from services.selfhost_secret_files import SecretRefused

OWNER, STORE_GID, GID = 0, 0, 10001
ROOT = Path(__file__).resolve().parents[2]
STAGE = stage2.STAGING/'providers'
PROVIDER_CONFIG = stage2.STORE.parent/'provider-config'
BACKUPS = Path('/var/backups/proptech-selfhost/stage5-provider-credentials')
LOCK = Path('/run/proptech-selfhost/provider-migration.lock')


def spec(filename, group):
    return {'file':filename, 'group':group}


SECRETS = {
    'GOOGLE_MAPS_API_KEY':spec('google_maps_api_key','google'),
    'GOOGLE_APPLICATION_CREDENTIALS':spec('earth_engine_adc_json','earth_engine'),
    'TGOS_APP_ID':spec('tgos_app_id','tgos'), 'TGOS_API_KEY':spec('tgos_api_key','tgos'),
    'TDX_CLIENT_ID':spec('tdx_client_id','tdx'), 'TDX_CLIENT_SECRET':spec('tdx_client_secret','tdx'),
    'R2_ACCESS_KEY_ID':spec('r2_access_key_id','r2'), 'R2_SECRET_ACCESS_KEY':spec('r2_secret_access_key','r2'),
    'OPENAI_API_KEY':spec('openai_api_key','openai'),
}
CONFIG = {'EARTH_ENGINE_PROJECT':spec('earth_engine_project','earth_engine'),
          'R2_ENDPOINT':spec('r2_endpoint','r2'), 'R2_BUCKET':spec('r2_bucket','r2'),
          'R2_REGION':spec('r2_region','r2')}
ALL = {**SECRETS, **CONFIG}
GROUPS = {g:tuple(n for n,s in ALL.items() if s['group']==g) for g in sorted({s['group'] for s in ALL.values()})}
PROVIDERS = {'google':'google','tgos':'tgos','tdx':'tdx','r2':'r2','openai':'openai','earth-engine':'earth_engine'}
DISABLED = {**{'ANTI_ABUSE_'+n+'_DISABLED':'true' for n in ('MARKET_OPS','GEOCODING','PLACES','ROUTES','SATELLITE','TGOS')},
            'EARTH_ENGINE_SATELLITE_REFERENCE_V1':'false'}
AUTH = {'SUPABASE_URL':'https://flyhsjcynreuofbcdxod.supabase.co',
        'SUPABASE_JWT_ISSUER':'https://flyhsjcynreuofbcdxod.supabase.co/auth/v1',
        'SUPABASE_JWT_AUDIENCE':'authenticated'}


def require(ok, reason):
    if not ok: raise SecretRefused(reason)


def provider_groups(provider=None):
    if provider is None:return tuple(GROUPS)
    require(isinstance(provider,str) and provider in PROVIDERS,'provider_selection_invalid')
    return (PROVIDERS[provider],)


def safe_reason(error):
    if isinstance(error,(SecretRefused,ScanRefused)) and re.fullmatch('[a-z0-9_]+',str(error)):
        return str(error)
    return 'provider_migration_failed_details_suppressed'


def covers_provider_storage(source):
    path=Path(source)
    require(path.is_absolute() and '..' not in path.parts,'provider_mount_source_invalid')
    boundaries=(stage2.STORE,PROVIDER_CONFIG,STAGE,*(stage2.STAGING/s['file'] for s in ALL.values()))
    return any(path==boundary or path in boundary.parents or boundary in path.parents for boundary in boundaries)


def private_dir(path):
    parent=stage2.open_directory(path.parent, owner=OWNER)
    try:
        try:os.mkdir(path.name,0o700,dir_fd=parent)
        except FileExistsError:pass
    finally:os.close(parent)
    os.close(stage2.open_directory(path,owner=OWNER,private=True))


def metadata(path, gid, mode):
    try:info=path.lstat()
    except FileNotFoundError:return None
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==OWNER
            and info.st_gid==gid and stat.S_IMODE(info.st_mode)==mode
            and 0<info.st_size<=1024*1024,'provider_metadata_unsafe')
    return {'uid':info.st_uid,'gid':info.st_gid,'mode':oct(mode),'bytes':info.st_size,
            'device':info.st_dev,'inode':info.st_ino,'mtime_ns':info.st_mtime_ns,'ctime_ns':info.st_ctime_ns}


def validate(name,value):
    if name in SECRETS:
        return stage2.validate_credential(ALL[name]['file'],value)
    require(isinstance(value,str) and value and len(value)<=1024 and value==value.strip()
            and not any(ord(c)<32 or ord(c)==127 for c in value),'provider_config_invalid')
    if name=='R2_ENDPOINT':
        try:
            p=urlsplit(value)
            ok=(p.scheme=='https' and not p.username and not p.password and p.port in {None,443}
                and p.path in {'','/'} and not p.query and not p.fragment
                and re.fullmatch(r'[a-z0-9-]+[.]r2[.]cloudflarestorage[.]com',p.hostname or ''))
        except ValueError:ok=False
        require(ok,'provider_config_invalid')
    elif name=='R2_REGION':require(value=='auto','provider_config_invalid')
    elif name=='R2_BUCKET':require(re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',value) and '..' not in value,'provider_config_invalid')
    elif name=='EARTH_ENGINE_PROJECT':require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:._-]{0,127}',value),'provider_config_invalid')
    return value


class Storage:
    def __init__(self,store=None,staging=None,*,groups=None):
        self.groups=tuple(GROUPS) if groups is None else tuple(groups)
        require(self.groups and all(g in GROUPS for g in self.groups)
                and len(self.groups)==len(set(self.groups)),'provider_selection_invalid')
        self.items={n:s for n,s in ALL.items() if s['group'] in self.groups}
        self.store=Path(store) if store is not None else stage2.STORE
        self.config=self.store.parent/'provider-config'
        self.staging=Path(staging) if staging is not None else STAGE
        self.legacy=self.staging.parent

    def stored_path(self,name):
        return (self.store if name in SECRETS else self.config)/ALL[name]['file']

    def read(self,name,path,gid,mode):
        if metadata(path,gid,mode) is None:return None
        value=stage2.read_secret(path.parent,path.name,owner=OWNER,gid=gid,mode=mode,
            limit=1024*1024 if name=='GOOGLE_APPLICATION_CREDENTIALS' else 8192,
            multiline=name=='GOOGLE_APPLICATION_CREDENTIALS')
        return validate(name,value)

    def collect(self,prompt=None):
        values={}
        for name,item in self.items.items():
            stored=self.read(name,self.stored_path(name),STORE_GID,0o600)
            staged=self.read(name,self.staging/item['group']/item['file'],GID,0o440)
            old=self.read(name,self.legacy/item['file'],GID,0o440)
            candidates=[v for v in (stored,staged,old) if v is not None]
            if candidates:
                require(all(hmac.compare_digest(candidates[0].encode(),v.encode()) for v in candidates),'provider_credential_conflict')
                values[name]=candidates[0]
            elif prompt is not None:values[name]=validate(name,prompt(name))
        return values

    def persist_and_stage(self,values):
        require(set(values)==set(self.items),'provider_population_incomplete')
        for name in self.items:validate(name,values[name])
        paths=(self.store,*((self.config,) if set(values)&set(CONFIG) else ()),self.staging)
        for path in paths:
            stage2.check_backing_storage(path)
            private_dir(path)
        for group in self.groups:private_dir(self.staging/group)
        # Recheck the complete population, including concurrent changes, before writes.
        for name,item in self.items.items():
            for path,gid,mode in [(self.stored_path(name),STORE_GID,0o600),
                                  (self.staging/item['group']/item['file'],GID,0o440)]:
                current=self.read(name,path,gid,mode)
                require(current is None or hmac.compare_digest(current.encode(),values[name].encode()),'provider_credential_conflict')
        for name,item in self.items.items():
            for path,gid,mode in [(self.stored_path(name),STORE_GID,0o600),
                                  (self.staging/item['group']/item['file'],GID,0o440)]:
                current=self.read(name,path,gid,mode)
                if current is None:
                    stage2.atomic_secret_write(path.parent,path.name,values[name],owner=OWNER,gid=gid,mode=mode,replace=False)
                else:require(hmac.compare_digest(current.encode(),values[name].encode()),'provider_credential_conflict')
        self.verify(values)

    def restore_staged_from_store(self):
        """Reboot preparation only: no prompts, adoption, Docker or token calls."""
        values={name:self.read(name,self.stored_path(name),STORE_GID,0o600) for name in self.items}
        require(all(value is not None for value in values.values()),'provider_persistent_population_incomplete')
        try:
            self.persist_and_stage(values)
        finally:
            values.clear()

    def verify(self,values):
        require(set(values)==set(self.items),'provider_population_incomplete')
        for name,item in self.items.items():
            for path,gid,mode in [(self.stored_path(name),STORE_GID,0o600),
                                  (self.staging/item['group']/item['file'],GID,0o440)]:
                current=self.read(name,path,gid,mode)
                require(current is not None and hmac.compare_digest(current.encode(),values[name].encode()),'provider_credential_conflict')
            old=self.read(name,self.legacy/item['file'],GID,0o440)
            require(old is None or hmac.compare_digest(old.encode(),values[name].encode()),'provider_credential_conflict')
        return self.receipt()

    def receipt(self):
        return {name:{'stored':metadata(self.stored_path(name),STORE_GID,0o600),
                      'staged':metadata(self.staging/s['group']/s['file'],GID,0o440)} for name,s in self.items.items()}

    def incomplete_classification(self):
        """Metadata only; never equate inaccessible storage with proven absence."""
        states={};filesystem={}
        for name,item in self.items.items():
            present=False;unknown=False
            for path in (self.stored_path(name),self.staging/item['group']/item['file'],self.legacy/item['file']):
                try:path.lstat();present=True
                except FileNotFoundError:pass
                except OSError:unknown=True
            states[name]='PRESENT_NOT_VALIDATED' if present else 'MISSING'
            filesystem[name]='PRESENT' if present else 'UNKNOWN' if unknown else 'ABSENT'
        return states,filesystem


def scanner_values(values,core):
    from services.earth_engine_adc import credential_scalars
    require(set(values)<=set(ALL),'provider_scan_population_invalid')
    result=[*core,*(values[n] for n in SECRETS if n in values)]
    # A complete ADC JSON alone would miss exposed standalone refresh material.
    # Literal private keys remain forbidden by SecretScanner independently.
    if 'GOOGLE_APPLICATION_CREDENTIALS' in values:
        result.extend(credential_scalars(values['GOOGLE_APPLICATION_CREDENTIALS']))
    return result


PROBE = r'''import json,os,stat,sys
try:
 names=sys.argv[2:]
 for name in names:
  fd=os.open('/run/provider-verify/'+name,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   s=os.fstat(fd)
   if not(stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_gid==10001 and stat.S_IMODE(s.st_mode)==0o440 and s.st_nlink==1 and s.st_size>0):raise ValueError()
   if not os.read(fd,1):raise ValueError()
  finally:os.close(fd)
 if sys.argv[1]=='earth_engine':
  import google.auth
  from google.auth import impersonated_credentials
  def no_network(*args,**kwargs):raise ValueError()
  os.environ['GOOGLE_APPLICATION_CREDENTIALS']='/run/provider-verify/earth_engine_adc_json'
  os.environ['GOOGLE_CLOUD_PROJECT']='project-3bd34c3e-daee-493f-ad6'
  credentials,_=google.auth.default(
   scopes=('https://www.googleapis.com/auth/earthengine','https://www.googleapis.com/auth/cloud-platform'),request=no_network)
  if not isinstance(credentials,impersonated_credentials.Credentials) or credentials.service_account_email!='proptech-render-earth-engine@project-3bd34c3e-daee-493f-ad6.iam.gserviceaccount.com':raise ValueError()
 print(json.dumps({'status':'PASS','group':sys.argv[1],'readable_files':len(names),'values_returned':False}))
except BaseException:
 print(json.dumps({'status':'REFUSED','values_returned':False}));sys.exit(1)
'''


def probe_command(image,group,staging):
    require(re.fullmatch(r'sha256:[a-f0-9]{64}',image) and group in GROUPS,'provider_probe_identity_invalid')
    args=['docker','run','--rm','--pull=never','--network=none','--read-only','--user=10001:10001',
          '--cap-drop=ALL','--security-opt=no-new-privileges','--log-driver=none',
          '--pids-limit=32','--memory=128m','--cpus=0.5','--entrypoint','python']
    files=[]
    for name in GROUPS[group]:
        filename=ALL[name]['file'];files.append(filename)
        args+=['--mount','type=bind,src='+str(Path(staging)/group/filename)+',dst=/run/provider-verify/'+filename+',readonly']
    return [*args,image,'-I','-B','-c',PROBE,group,*files]


class Docker:
    """Local-daemon read operations and isolated throwaway probes only."""
    def __init__(self,folder):
        private_dir(folder/'docker-cli')
        self.prefix=['docker','--host','unix:///var/run/docker.sock','--config',str(folder/'docker-cli')]
        self.env={'PATH':os.defpath,'LANG':'C','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'}

    def capture(self,args,scanner=None,timeout=60,limit=2*1024*1024):
        from scripts.ops.professor_stage2_activation import DeadlineReader
        p=subprocess.Popen([*self.prefix,*args],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=self.env)
        try:
            reader=DeadlineReader(p.stdout,timeout);chunks=[];size=0
            while chunk:=reader.read(65536):
                size+=len(chunk);require(size<=limit,'provider_metadata_limit');chunks.append(chunk)
            raw=b''.join(chunks)
            require(p.wait(timeout=10)==0,'provider_docker_operation_failed')
            if scanner:scanner.check_bytes(raw)
            return raw
        except BaseException:
            p.kill();p.wait();raise
        finally:p.stdout.close()

    def stream(self,args,scanner,image=False):
        from scripts.ops.professor_stage2_activation import DeadlineReader
        p=subprocess.Popen([*self.prefix,*args],stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT if args and args[0]=='logs' else subprocess.DEVNULL,env=self.env)
        try:
            reader=DeadlineReader(p.stdout,1800 if image else 180)
            result=scanner.scan_image_archive(reader) if image else scanner.check_stream(reader)
            require(p.wait(timeout=10)==0,'provider_docker_operation_failed')
            return result
        except BaseException:
            p.kill();p.wait();raise
        finally:p.stdout.close()

    def preflight(self):
        self.preflight_diagnostics={}
        ids=self.capture(['ps','-q','--no-trunc','--filter','label=com.docker.compose.project=proptech-selfhost',
                          '--filter','label=com.docker.compose.service=api']).decode().split()
        require(len(ids)==1 and re.fullmatch('[a-f0-9]{64}',ids[0]),'provider_api_identity_unavailable')
        ident=ids[0]
        image=self.capture(['inspect','--format','{{.Image}}',ident]).decode().strip()
        require(re.fullmatch(r'sha256:[a-f0-9]{64}',image),'provider_image_identity_invalid')
        require(json.loads(self.capture(['image','inspect','--format','{{json .Config.Volumes}}',image])) in (None,{}),
                'provider_probe_image_has_implicit_volumes')
        # Read only the fixed nonsecret configuration fields for the early guard.
        selected={}
        for name in {**DISABLED,**AUTH}:
            template='{{range .Config.Env}}{{if eq (index (split . "=") 0) "'+name+'"}}{{println .}}{{end}}{{end}}'
            line=self.capture(['inspect','--format',template,ident]).decode().strip()
            # Stage4A's accepted profile trusts the explicit issuer/audience.
            # SUPABASE_URL is only an optional legacy alias; a present conflict
            # must still fail, never silently override the canonical authority.
            if name=='SUPABASE_URL' and not line:
                self.preflight_diagnostics['legacy_supabase_url']='ABSENT_ALLOWED_WITH_EXPLICIT_ISSUER'
                continue
            key,sep,value=line.partition('=')
            if not (sep and key==name):self.preflight_diagnostics['missing_configuration_name']=name
            require(sep and key==name,'provider_guard_unavailable');selected[name]=value
        names=self.capture(['inspect','--format','{{range .Config.Env}}{{println (index (split . "=") 0)}}{{end}}',ident]).decode().split()
        require(not any(n in SECRETS or n.removesuffix('_FILE') in SECRETS or n.startswith('NEXT_PUBLIC_')
                        or n=='GOOGLE_SERVICE_ACCOUNT_JSON' for n in names),'provider_credential_in_live_environment')
        require(all(selected[k]==v for k,v in DISABLED.items()),'provider_must_remain_disabled')
        require(all(selected.get(k)==v for k,v in AUTH.items() if k!='SUPABASE_URL')
                and ('SUPABASE_URL' not in selected or selected['SUPABASE_URL']==AUTH['SUPABASE_URL']),
                'provider_auth_authority_changed')
        mounts=json.loads(self.capture(['inspect','--format','{{json .Mounts}}',ident]))
        require(not any(covers_provider_storage(str(m.get('Source',''))) for m in mounts),
                'provider_already_mounted_in_live_api')
        return ident,image

    def probe(self,image,group,scanner,folder):
        cidfile=folder/(group+'.cid')
        require(not cidfile.exists(),'provider_probe_cid_conflict')
        args=probe_command(image,group,STAGE)[1:]
        pos=args.index(image);args[pos:pos]=['--cidfile',str(cidfile),
            '--label','proptech.provider-receipt='+folder.name,'--label','proptech.provider-group='+group]
        try:
            return json.loads(self.capture(args,scanner,timeout=45))
        finally:
            if cidfile.exists():
                info=cidfile.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1 and info.st_size<=128,
                        'provider_probe_cid_unsafe')
                ident=cidfile.read_text().strip();require(re.fullmatch('[a-f0-9]{64}',ident),'provider_probe_cid_unsafe')
                listed=self.capture(['ps','-aq','--no-trunc','--filter','id='+ident]).decode().split()
                require(set(listed)<={ident},'provider_probe_cleanup_identity_invalid')
                if listed:
                    labels=json.loads(self.capture(['inspect','--format','{{json .Config.Labels}}',ident]))
                    require(labels.get('proptech.provider-receipt')==folder.name
                            and labels.get('proptech.provider-group')==group
                            and 'com.docker.compose.project' not in labels,'provider_probe_cleanup_identity_invalid')
                    self.capture(['rm','-f',ident])
                require(not self.capture(['ps','-aq','--no-trunc','--filter','id='+ident]).strip(),'provider_probe_cleanup_failed')


def scan_checkout(scanner):
    """Scan tracked current bytes without filters, symlinks or raw output export."""
    env={'PATH':os.defpath,'LANG':'C','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'}
    cmd=['git','-c','safe.directory='+str(ROOT),'-c','core.fsmonitor=false','-C',str(ROOT),'ls-files','--stage','-z']
    result=subprocess.run(cmd,env=env,capture_output=True,timeout=30)
    require(result.returncode==0 and len(result.stdout)<=8*1024*1024,'provider_checkout_inventory_failed')
    count=total=0
    for record in result.stdout.decode().split('\0'):
        if not record:continue
        header,name=record.split('\t',1);mode,_,stage=header.split()
        parts=Path(name).parts
        require(mode in {'100644','100755'} and stage=='0' and not Path(name).is_absolute()
                and all(p not in {'.','..'} for p in parts),'provider_checkout_source_unsafe')
        directory=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        fd=None
        try:
            for part in parts[:-1]:
                new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory);os.close(directory);directory=new
            fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
            info=os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=512*1024*1024,'provider_checkout_file_unsafe')
            total+=info.st_size;require(total<=5*1024**3,'provider_checkout_scan_limit')
            with os.fdopen(fd,'rb') as stream:fd=None;scanner.check_stream(stream)
            count+=1
        finally:
            if fd is not None:os.close(fd)
            os.close(directory)
    return {'files':count,'bytes':total,'status':'PASS'}


def core_values():
    values=[]
    for name,filename in ACTIVE.items():
        value=stage2.read_secret(stage2.STORE,filename,owner=OWNER,gid=STORE_GID,mode=0o600)
        if name!='PROFESSOR_USER_DATABASE_URL':stage2.validate_credential(filename,value)
        else:
            try:
                p=urlsplit(value)
                ok=(p.scheme in {'postgres','postgresql'} and p.username=='professor_user_runtime'
                    and p.hostname=='postgres_app' and p.path=='/proptech_app' and p.port in {None,5432}
                    and bool(p.password) and not p.query and not p.fragment)
            except ValueError:ok=False
            require(ok,'provider_core_recovery_required')
        staged=stage2.read_secret(stage2.STAGING,filename,owner=OWNER,gid=GID,mode=0o440)
        require(hmac.compare_digest(value.encode(),staged.encode()),'provider_core_staging_conflict')
        values.append(value)
    for name in ('app_admin_password','usage_admin_password'):
        values.append(stage2.read_secret(stage2.STORE,name,owner=OWNER,gid=STORE_GID,mode=0o600))
    return values


def core_metadata():
    result={}
    for filename in [*ACTIVE.values(),'app_admin_password','usage_admin_password']:
        result['stored/'+filename]=metadata(stage2.STORE/filename,STORE_GID,0o600)
    for filename in ACTIVE.values():result['staged/'+filename]=metadata(stage2.STAGING/filename,GID,0o440)
    require(all(result.values()),'provider_core_recovery_required')
    return result


def stage_stored_providers(provider=None):
    """Operator/boot hook after core secret restore; no services are changed."""
    groups=provider_groups(provider)
    require(os.geteuid()==0,'operator_root_required')
    stage2.storage_boundary()
    for path in (PROVIDER_CONFIG,STAGE):stage2.check_backing_storage(path)
    parent=stage2.open_directory(LOCK.parent,owner=OWNER)
    try:lock=os.open(LOCK.name,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600,dir_fd=parent)
    finally:os.close(parent)
    try:
        info=os.fstat(lock)
        require(stat.S_ISREG(info.st_mode) and info.st_uid==OWNER and info.st_nlink==1
                and stat.S_IMODE(info.st_mode)==0o600,'provider_lock_unsafe')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        storage=Storage(groups=groups)
        storage.restore_staged_from_store()
    finally:
        os.close(lock)
    return {'status':'PASS_STAGED_PROVIDERS_NOT_ACTIVE','staged_file_count':len(storage.items),
            'provider':provider,'selected_groups':list(groups),
            'activation_performed':False,'credential_values_returned':False,
            'requires_core_restore_first':True,'provider_functional_tests':'NOT_RUN'}


def migrate_all(imports):
    return _migrate(imports)


def migrate_provider(provider,imports):
    require(provider is not None,'provider_selection_invalid')
    return _migrate(imports,provider)


def _migrate(imports,provider=None):
    groups=provider_groups(provider)
    selected={n for group in groups for n in GROUPS[group]}
    require(os.geteuid()==0,'operator_root_required')
    require(set(imports)<=selected,'provider_import_name_invalid')
    for path in (stage2.STORE,PROVIDER_CONFIG,STAGE,ROOT,BACKUPS):stage2.check_backing_storage(path)
    private_dir(BACKUPS)
    folder=Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'),dir=BACKUPS))
    report={'schema':'professor-required-provider-migration-v1','status':'RUNNING','values_returned':False,
            'provider':provider,'selected_groups':list(groups),'selected_names':sorted(selected),
            'earth_engine_iam_status':'PENDING_IAM',
            'activation_performed':False,'existing_api_recreated':False,'provider_functional_tests':'NOT_RUN',
            'new_provider_environment_or_live_mounts':False,'paid_provider_calls':0,'phases':[]}
    lock=None;values={};core=[];docker=None;scanned_values={}
    storage=Storage(groups=groups)
    try:
        parent=stage2.open_directory(LOCK.parent,owner=OWNER)
        try:lock=os.open(LOCK.name,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600,dir_fd=parent)
        finally:os.close(parent)
        info=os.fstat(lock);require(stat.S_ISREG(info.st_mode) and info.st_uid==OWNER and info.st_nlink==1
                                  and stat.S_IMODE(info.st_mode)==0o600,'provider_lock_unsafe')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        os.close(stage2.open_directory(stage2.STORE,owner=OWNER,private=True))
        docker=Docker(folder);ident,image=docker.preflight();report['image_id']=image
        report['core_secret_metadata_before']=core_metadata()
        core=core_values()
        def prompt(name):
            if name in imports:
                return stage2.import_file(Path(imports[name]),multiline=name=='GOOGLE_APPLICATION_CREDENTIALS')
            if name=='GOOGLE_APPLICATION_CREDENTIALS':
                path=stage2.hidden_input('Protected keyless impersonation ADC import path for GOOGLE_APPLICATION_CREDENTIALS (hidden): ')
                return stage2.import_file(Path(path),multiline=True)
            return stage2.hidden_input('Enter '+name+' (hidden): ')
        report['phases'].append('collect_existing_or_hidden_inputs')
        print(json.dumps({'phase':'collect_existing_or_hidden_inputs','values_returned':False}),flush=True)
        values=storage.collect(prompt)
        # Missing unselected providers never prompt or require IAM. Every valid
        # already-present provider still participates in the global leak scan.
        scanned_values=Storage().collect()
        for name,value in values.items():
            require(name not in scanned_values or hmac.compare_digest(scanned_values[name].encode(),value.encode()),
                    'provider_credential_conflict')
            scanned_values[name]=value
        report['known_provider_names_scanned']=sorted(scanned_values)
        scanner=SecretScanner(scanner_values(scanned_values,core))
        report['phases'].append('git-scan')
        print(json.dumps({'phase':'offline_credential_leak_scans','values_returned':False}),flush=True)
        report['checkout_scan']=scan_checkout(scanner)
        report['phases'].append('image-layer-scan')
        report['image_scan']=docker.stream(['image','save',image],scanner,image=True)
        report['phases'].append('image-history-scan')
        docker.stream(['image','history','--no-trunc','--format','{{json .}}',image],scanner)
        report['phases'].append('api-environment-scan')
        docker.stream(['inspect','--format','{{json .Config.Env}}',ident],scanner)
        report['phases'].append('project-logs-scan')
        container_ids=docker.capture(['ps','-aq','--no-trunc','--filter','label=com.docker.compose.project=proptech-selfhost']).decode().split()
        require(container_ids and all(re.fullmatch('[a-f0-9]{64}',c) for c in container_ids),'provider_log_population_invalid')
        for c in container_ids:docker.stream(['logs',c],scanner)
        report['project_container_logs_scanned']=len(container_ids)
        report['phases'].append('store_and_isolated_provider_stage')
        storage.persist_and_stage(values)
        report['provider_file_metadata']=storage.receipt()
        results={}
        for group in groups:
            report['phases'].append('isolated-visibility-'+group)
            result=docker.probe(image,group,scanner,folder)
            require(result=={'status':'PASS','group':group,'readable_files':len(GROUPS[group]),'values_returned':False},'provider_visibility_failed')
            results[group]=result
        # Ensure external concurrent work did not change image/guards/mounts mid-run.
        require(docker.preflight()==(ident,image),'provider_runtime_changed_during_migration')
        require(core_metadata()==report['core_secret_metadata_before'],'provider_core_changed_during_migration')
        report['provider_file_metadata']=storage.verify(values)
        current=Storage().collect()
        require(set(current)==set(scanned_values),'provider_scan_population_changed')
        require(all(hmac.compare_digest(current[n].encode(),v.encode()) for n,v in scanned_values.items()),
                'provider_scan_population_changed')
        report.update(status='PASS_MIGRATED_PROVIDERS_DISABLED' if provider is None else 'PASS_MIGRATED_PROVIDER_DISABLED',provider_visibility=results,
                      earth_engine_adc_loader='PASS_IMPERSONATION_OFFLINE_NO_REFRESH' if 'earth_engine' in groups else 'NOT_SELECTED_PENDING_IAM',
                      provider_classification={n:'PRESENT_AND_VALIDATED' for n in selected},
                      validation_scope='private stored/staged files, isolated readability and leak scans; provider authentication/API acceptance NOT_RUN',
                      ephemeral_validation_containers=True,network_calls=0,
                      core_database_hmac_session_material_preserved=True,
                      supabase_server_verification='PRESENT_AND_VALIDATED_PUBLIC_CONFIG_UNCHANGED',
                      browser_public_credentials_installed_by_this_workflow=False)
    except (Exception,KeyboardInterrupt) as error:
        report.update(status='REFUSED',reason_code=safe_reason(error))
        diagnostic=getattr(docker,'preflight_diagnostics',None)
        if diagnostic:report['preflight_diagnostics']=diagnostic
        report['provider_classification'],report['filesystem_presence']=storage.incomplete_classification()
        report['classification_scope']='MISSING means migration acceptance missing; consult filesystem_presence, UNKNOWN is not confirmed absence'
    finally:
        values.clear();core.clear();scanned_values.clear()
        if lock is not None:os.close(lock)
    stage2.atomic_secret_write(folder,'acceptance.json',json.dumps(report,indent=2)+'\n',owner=OWNER,gid=STORE_GID)
    return report['status'] in {'PASS_MIGRATED_PROVIDERS_DISABLED','PASS_MIGRATED_PROVIDER_DISABLED'},folder/'acceptance.json'
