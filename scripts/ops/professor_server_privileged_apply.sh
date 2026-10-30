#!/usr/bin/env bash
# Operator-run local apply. Never access /dev/sda or write to the X9 source.
# No deployment, database removal, volume removal, source-row deletion or pulls.
set -euo pipefail
umask 077
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export DOCKER_HOST=unix:///var/run/docker.sock
unset DOCKER_CONTEXT DOCKER_TLS_VERIFY DOCKER_CERT_PATH
[[ ${EUID} -eq 0 ]] || { printf '%s\n' 'Run this script as root from the operator terminal.' >&2; exit 1; }
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
# Read mount metadata before the first lock/evidence write.
for checked_path in "$repo" /srv/proptech-data/DB /etc/proptech-selfhost /var/backups/proptech-selfhost /run/lock; do
    backing=$(findmnt -rn -o SOURCE --target "$checked_path") || exit 1
    case "$backing" in /dev/sda*) printf '%s\n' 'Forbidden backing device; no apply performed.' >&2; exit 1;; esac
done
exec 9>/run/lock/proptech-final-data-integration.lock
flock -n 9 || { printf '%s\n' 'Another integration apply holds the lock.' >&2; exit 1; }
install -d -m 0700 /var/backups/proptech-selfhost/final-data-integration
backup=$(mktemp -d /var/backups/proptech-selfhost/final-data-integration/apply-"$(date -u +%Y%m%dT%H%M%SZ)"-XXXXXXXX)
# Child stderr is captured/suppressed below: no command, URL or secret traceback.
python3 - "$repo" "$backup" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

REPO, OUT = map(Path, sys.argv[1:])
ROOT = Path('/srv/proptech-data/DB')
ETC = Path('/etc/proptech-selfhost')
PROJECT = 'proptech-selfhost'
RUN_ID = OUT.name.lower()
AS_OF = datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Taipei')).strftime('%Y-%m')
NLSC_SHA = '1b1db799708e61ee337d1ac6ae0fa359eafd8c28b8cf297d80b0c83cb5a2b03d'
NLSC = ROOT/'Cloudflare R2/proptech-government-data/processed/nlsc/village-boundary/v1/features.json.gz'
WRA = ROOT/'Cloudflare R2/proptech-government-data/processed/wra/flood/v1'
RAW = ROOT/'實價登錄 PLVR/02_extracted'
ROLE, DATABASE = 'valuation_runtime', 'proptech_valuation'
report = dict(schema='professor-server-apply-v1', run_id=RUN_ID,
              started_at=datetime.now(timezone.utc).isoformat(), status='RUNNING', phase='preflight',
              database_apply_attempted=False, database_committed=False, api_stopped=False,
              configuration_written=False, runtime_recreated=False, production_ready=False,
              evidence_directory=str(OUT), as_of=AS_OF)
api_id = None


def require(condition, reason):
    if not condition:
        report['reason_code']=reason
        raise RuntimeError(reason)


def save(name, value):
    path = OUT/name
    temporary = OUT/(name+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    temporary.chmod(0o600)
    os.replace(temporary, path)


def checkpoint(phase):
    report['phase'] = phase
    save('apply-report.json', report)
    print('Professor Server apply: '+phase, flush=True)


def run(argv, *, payload=None, stdin=None, stdout=None, timeout=180, check=True):
    result = subprocess.run([str(x) for x in argv], input=payload, stdin=stdin,
                            stdout=stdout if stdout is not None else subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout, cwd=REPO)
    # Do not print or persist stderr; tools can interpolate secrets into errors.
    if check and result.returncode:
        report['reason_code']='command_failed_'+str(result.returncode)
        raise RuntimeError(report['reason_code'])
    return result


def decode(result):
    return json.loads(result.stdout)


def inspect(identifier):
    return decode(run(['docker', 'inspect', identifier]))[0]


def psql(container, database, text=None, *, source=None, output=None, timeout=180):
    return run(['docker', 'exec', '-i', '-u', 'postgres', container,
                'psql', '-X', '-w', '-v', 'ON_ERROR_STOP=1', '-qAt', '-h', '/var/run/postgresql', '-p', '5432', '-U', 'postgres', '-d', database],
               payload=text.encode() if text is not None else None, stdin=source, stdout=output, timeout=timeout)


def db_json(container, database, sql):
    return decode(psql(container, database, sql))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def storage_boundary(path):
    path=Path(path)
    require(not str(path).startswith('/dev/sda'),'forbidden_storage_path')
    # Resolve symlinks and inspect mount metadata, not device contents.
    resolved=path.resolve(strict=True)
    require(not str(resolved).startswith('/dev/sda'),'forbidden_storage_path')
    data=decode(run(['findmnt','--json','--target',resolved,'-o','SOURCE']))
    source=data['filesystems'][0]['source'].split('[',1)[0]
    require(not source.startswith('/dev/sda'),'forbidden_backing_device')
    if source.startswith('/dev/'):
        require(not os.path.realpath(source).startswith('/dev/sda'),'forbidden_backing_device_alias')


def safe_host():
    for path in [REPO, ROOT, ETC, OUT]:
        storage_boundary(path)
    require(shutil.disk_usage(OUT).free >= 5*1024**3, 'insufficient_snapshot_space')
    lines = run(['ss', '-H', '-lnt']).stdout.decode().splitlines()
    for line in lines:
        address = line.split()[3]
        host, _, port = address.rpartition(':')
        require(port != '5432', 'postgres_host_listener_present')
        if port == '8080':
            require(host in {'127.0.0.1', '[::1]', '::1'}, 'public_api_listener_present')
    save('listeners.json', {'listeners': lines})


def postgres_boundary(container):
    value = inspect(container)
    for mount in value.get('Mounts',[]):
        if mount.get('RW') and mount.get('Source'): storage_boundary(mount['Source'])
    require(value['HostConfig'].get('NetworkMode') != 'host', 'postgres_host_network')
    require(not any((value['HostConfig'].get('PortBindings') or {}).values()), 'postgres_published_port')
    networks = list(value['NetworkSettings']['Networks'])
    require(networks, 'postgres_without_private_network')
    require(all(decode(run(['docker', 'network', 'inspect', n]))[0]['Internal'] for n in networks),
            'postgres_network_not_internal')


def proxy_boundary(container):
    value = inspect(container)
    bindings = value['HostConfig'].get('PortBindings') or {}
    require(set(bindings) == {'8080/tcp'}, 'unexpected_proxy_ports')
    require(bindings['8080/tcp'] and all(p['HostIp']=='127.0.0.1' and p['HostPort']=='8080'
            for p in bindings['8080/tcp']), 'proxy_not_loopback_only')


def verify_database_identity(owners, security):
    import ipaddress
    def canonical(value):
        address=ipaddress.ip_address(value)
        return str(getattr(address,'ipv4_mapped',None) or address)
    for kind,database in [('app','proptech_app'),('usage','proptech_api_usage'),('valuation',DATABASE)]:
        addresses={canonical(address) for n in inspect(owners[database])['NetworkSettings']['Networks'].values()
                   for address in [n.get('IPAddress'),n.get('GlobalIPv6Address')] if address}
        require(security[kind]['server_port']==5432 and canonical(security[kind]['server_ip']) in addresses,
                'runtime_database_container_identity_mismatch')


def fail_closed_stop():
    errors=[]
    stopped=[]
    try:
        identifiers=run(['docker','ps','-aq','--filter','label=com.docker.compose.project='+PROJECT],
                        check=False,timeout=30).stdout.decode().split()
        for identifier in identifiers:
            try:
                value=inspect(identifier)
                service=value['Config'].get('Labels',{}).get('com.docker.compose.service')
                if service not in {'api','reverse_proxy'}:
                    continue
                run(['docker','stop','--time','20',identifier],check=False,timeout=45)
                if inspect(identifier)['State']['Running']:
                    errors.append('container_still_running')
                else:
                    stopped.append(service)
            except BaseException:
                errors.append('container_stop_unverified')
    except BaseException:
        errors.append('container_discovery_unverified')
    report['maintenance_cleanup']={'confirmed_stopped_services':sorted(set(stopped)),
                                   'errors':errors,'verified':not errors and {'api','reverse_proxy'}<=set(stopped)}
    report['api_stopped']='api' in stopped and not errors
    report['proxy_stopped']='reverse_proxy' in stopped and not errors


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = build_opener(ProxyHandler({}), NoRedirect())
def api_request(path, payload=None):
    request = Request('http://127.0.0.1:8080'+path,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Host':'localhost','Content-Type':'application/json'})
    try:
        with opener.open(request, timeout=45) as response:
            body=response.read(8*1024*1024+1)
            require(len(body)<=8*1024*1024, 'api_response_size')
            value=json.loads(body)
            require(isinstance(value,dict), 'api_response_schema')
            return response.status,value
    except HTTPError as error:
        return error.code,{}


# These programs run only inside the existing/new API image, never on the host
# without its dependencies. No credentials are copied into the image context.
ENTRYPOINT = r'''
import os,runpy,sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,unquote
try:
    value=Path('/run/secrets/valuation_database_url').read_text().strip()
    parts=urlsplit(value)
    assert parts.scheme in {'postgres','postgresql'}
    assert unquote(parts.username or '')=='valuation_runtime'
    assert unquote(parts.path)=='/proptech_valuation'
    query=[(k,v) for k,v in parse_qsl(parts.query) if k not in {'sslmode','sslrootcert'}]
    query.extend([('sslmode','verify-full'),('sslrootcert','/run/selfhost-ca/ca.crt')])
    os.environ['VALUATION_DATABASE_URL']=urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),''))
    sys.argv=['scripts/ops/selfhost_runtime.py','api']
except Exception:
    raise SystemExit('runtime_configuration_invalid') from None
runpy.run_path('scripts/ops/selfhost_runtime.py',run_name='__main__')
'''

SECURITY = r'''
import json,os
from pathlib import Path
import psycopg
result={}
for kind,filename,role,database in [
 ('app','app_database_url','app_runtime','proptech_app'),
 ('usage','usage_database_url','proptech_usage_runtime_v1','proptech_api_usage'),
 ('valuation','valuation_database_url','valuation_runtime','proptech_valuation')]:
    url=Path('/run/secrets/'+filename).read_text().strip()
    with psycopg.connect(url,connect_timeout=5,sslmode='verify-full',sslrootcert='/run/selfhost-ca/ca.crt',
         options='-c default_transaction_read_only=on -c statement_timeout=20000') as db:
        row=db.execute(''' + '"""' + r'''select current_user,session_user,current_database(),rolcanlogin,rolsuper,
          rolbypassrls,rolcreatedb,rolcreaterole,rolreplication
          from pg_roles where rolname=current_user''' + '"""' + r''').fetchone()
        assert row==(role,role,database,True,False,False,False,False,False)
        ssl=db.execute('select ssl,version,cipher from pg_stat_ssl where pid=pg_backend_pid()').fetchone()
        assert ssl and ssl[0]
        checks={}
        tables=['public.ris_village_demographics'] if kind=='app' else (
          ['public.real_price_transactions','public.valuation_import_runs','public.market_district_period_aggregates',
           'public.market_region_coverage','public.market_read_model_metadata','public.community_buildings'] if kind=='valuation' else [])
        if kind=='valuation' and os.getenv('PLVR_SERVING_EXCLUSIONS_ENABLED')=='true':
            tables+=['public.market_serving_exclusions','public.market_serving_transactions','public.market_serving_district_periods']
        for table in tables:
            permissions={p:db.execute('select has_table_privilege(current_user,%s,%s)',[table,p]).fetchone()[0]
                         for p in ['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','TRIGGER']}
            assert permissions['SELECT'] and not any(v for k,v in permissions.items() if k!='SELECT')
            checks[table]=permissions
        if kind=='valuation':
            assert not db.execute("select has_schema_privilege(current_user,'public','CREATE')").fetchone()[0]
            assert not db.execute("select exists(select from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind in ('r','p') and (has_table_privilege(current_user,c.oid,'INSERT') or has_table_privilege(current_user,c.oid,'UPDATE') or has_table_privilege(current_user,c.oid,'DELETE')))").fetchone()[0]
        result[kind]={'role':role,'database':database,'tls':True,'tls_version':ssl[1],
                      'least_privilege':True,'table_privileges':checks,
                      'server_ip':str(db.execute('select inet_server_addr()').fetchone()[0]),
                      'server_port':db.execute('select inet_server_port()').fetchone()[0]}
print(json.dumps(result))
'''

VERIFY_ARTIFACTS = r'''
import gzip,hashlib,json
from pathlib import Path
from services.wra_flood_runtime import WraFloodRuntime,CANONICAL_SCENARIOS
expected=json.loads(Path('/evidence/expected-wra.json').read_text())
def forbidden(): raise AssertionError('local_mode_attempted_r2')
runtime=WraFloodRuntime(client_factory=forbidden,local_root='/srv/proptech/datasets/wra/flood/v1')
rows=[]
for scenario in CANONICAL_SCENARIOS:
    loaded=runtime.load_scenario(scenario)
    assert loaded.artifact_sha256==expected[scenario]['sha256']
    assert loaded.feature_count==expected[scenario]['count']
    point=loaded.geometries[0].representative_point()
    hit=runtime.query_point(scenario,point.x,point.y)
    miss=runtime.query_point(scenario,0,0)
    assert hit['matched'] and hit['storage_backend']=='local'
    assert miss['status']=='no_match' and not miss['matched'] and 'safe' not in miss
    rows.append({'scenario':scenario,'sha256':loaded.artifact_sha256,'feature_count':loaded.feature_count,
                 'matched_point':[point.x,point.y],'no_match_point':[0,0],'r2_calls':0})
    runtime.clear_cache()
p=Path('/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz')
payload=p.read_bytes()
assert hashlib.sha256(payload).hexdigest()=='1b1db799708e61ee337d1ac6ae0fa359eafd8c28b8cf297d80b0c83cb5a2b03d'
assert len(json.loads(gzip.decompress(payload))['features'])==7691
print(json.dumps({'status':'PASS','nlsc_features':7691,'wra':rows}))
'''


def wait_healthy(container):
    for _ in range(90):
        state=inspect(container)['State']
        if state.get('Health',{}).get('Status')=='healthy':
            return
        require(state.get('Running'), 'api_not_running')
        time.sleep(2)
    raise RuntimeError('api_health_timeout')


def plan_configuration(compose, files, image):
    target=ETC/'datasets.override.yml'
    last=files[-1]
    require(last.parent==ETC,'last_compose_file_not_operator_override')
    before=decode(run(compose+['config','--format','json']))
    environment={
      'WRA_FLOOD_LOCAL_ROOT':'/srv/proptech/datasets/wra/flood/v1',
      'PLVR_SERVING_EXCLUSIONS_ENABLED':'true','POSTGRES_SSLMODE':'verify-full',
      'ANTI_ABUSE_TERRAIN_DISABLED':'false','ANTI_ABUSE_VALUATION_DISABLED':'false',
      'ANTI_ABUSE_TREND_DISABLED':'false','ANTI_ABUSE_FINDER_DISABLED':'false','ANTI_ABUSE_MARKET_DISABLED':'false',
      'GSMMA_GEOLOGICAL_SENSITIVITY_LOCAL_ROOT':'/srv/proptech/datasets/gsmma/geological-sensitivity/v1',
      'ANTI_ABUSE_MARKET_OPS_DISABLED':'true','EARTH_ENGINE_SATELLITE_REFERENCE_V1':'false'}
    for operation in ['GEOCODING','PLACES','ROUTES','SATELLITE','LOCATION','PARCEL','ARDSWC','LIQUEFACTION','NLSC','TGOS']:
        environment['ANTI_ABUSE_'+operation+'_DISABLED']='true'
    def volume(source,destination):
        return {'type':'bind','source':str(source),'target':destination,'read_only':True,'bind':{'create_host_path':False}}
    local_volumes=[volume(NLSC,'/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz'),
                   volume(WRA,'/srv/proptech/datasets/wra/flood/v1')]
    targets={v['target'] for v in local_volumes}
    def destination(value):
        if isinstance(value,dict): return value['target']
        fields=value.split(':')
        require(len(fields) in {2,3} and fields[1].startswith('/'),'unsupported_volume_declaration')
        return fields[1]
    def merge(path):
        original=decode(run(['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
            '--security-opt','no-new-privileges:true','--entrypoint','python',
            '--mount',f'type=bind,src={path},dst=/input.yml,readonly',image,'-c',
            "import json,yaml;print(json.dumps(yaml.safe_load(open('/input.yml')) or {}))"]))
        require(isinstance(original,dict),'override_shape')
        service=original.setdefault('services',{}).setdefault('api',{})
        old_env=service.get('environment',{})
        if isinstance(old_env,list):
            old_env={entry.partition('=')[0]:entry.partition('=')[2] if '=' in entry else None for entry in old_env}
        require(isinstance(old_env,dict),'override_environment_shape')
        service['environment']={**old_env,**environment}
        service['volumes']=[v for v in service.get('volumes',[]) if destination(v) not in targets]+local_volumes
        service.update(image=image,pull_policy='never',
            entrypoint=['python','scripts/ops/professor_runtime_entrypoint.py'],command=[])
        return original
    replacements={path:merge(path) for path in dict.fromkeys([target,last])}
    # The last override is previewed in its real position, with only our known
    # API keys added. It preserves every unrelated declaration from that file.
    previews=[]
    for index,path in enumerate(files):
        if path in replacements:
            preview=OUT/('planned-'+path.name)
            preview.write_text(json.dumps(replacements[path],ensure_ascii=False,indent=2)+'\n')
            previews.append(preview)
        else:
            previews.append(path)
    preview_command=compose[:compose.index('-f')]
    for path in previews: preview_command+=['-f',str(path)]
    planned=decode(run(preview_command+['config','--format','json']))
    # Config declares relative paths against the project directory explicitly.
    require(set(planned['services'])==set(before['services']),'compose_services_changed')
    for name in before['services']:
        if name!='api': require(planned['services'][name]==before['services'][name],'unrelated_service_changed')
    old,new=before['services']['api'],planned['services']['api']
    for key in set(old)|set(new):
        if key not in {'image','pull_policy','environment','entrypoint','command','volumes'}:
            require(old.get(key)==new.get(key),'unrelated_api_setting_changed')
    require(old.get('secrets')==new.get('secrets'),'runtime_secrets_changed')
    for key,value in old.get('environment',{}).items():
        if key not in environment: require(new['environment'].get(key)==value,'unrelated_environment_changed')
    for key,value in environment.items(): require(str(new['environment'].get(key))==value,'runtime_guard_merge_failed')
    require(new['image']==image,'new_image_override_lost')
    require(new['environment'].get('NLSC_VILLAGE_BOUNDARY_ARTIFACT_PATH')==local_volumes[0]['target'], 'nlsc_runtime_path_unexpected')
    require(new['environment'].get('NLSC_VILLAGE_BOUNDARY_ARTIFACT_SHA256')==NLSC_SHA,'nlsc_runtime_checksum_unexpected')
    old_mounts={v['target']:v for v in old.get('volumes',[])}
    new_mounts={v['target']:v for v in new.get('volumes',[])}
    for target_name,value in old_mounts.items():
        if target_name not in targets: require(new_mounts.get(target_name)==value,'unrelated_mount_changed')
    for value in local_volumes:
        actual=new_mounts.get(value['target'],{})
        require(actual.get('source')==value['source'] and actual.get('read_only') is True
                and actual.get('bind',{}).get('create_host_path') is False,'dataset_mount_merge_failed')
    require(all('Crucial X9' not in v.get('source','') for v in new_mounts.values()),'x9_binding_survives_compose_merge')
    require(not new.get('ports'),'api_port_published_in_compose')
    return replacements,planned


def stage_image_context(repo, context, filenames, entrypoint):
    """Stage only public application code; keep evidence/context parents private.

    COPY --chown changes ownership but preserves directory permissions. The
    cap-dropped UID0 reconciliation job therefore needs ordinary traversal
    permissions even though the runtime owner is UID10001.
    """
    app=context/'app'
    app.mkdir(parents=True,mode=0o700)
    for name in filenames:
        destination=app/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(repo/name,destination)
        destination.chmod(0o644)
    wrapper=app/'scripts/ops/professor_runtime_entrypoint.py'
    wrapper.parent.mkdir(parents=True,exist_ok=True)
    wrapper.write_text(entrypoint);wrapper.chmod(0o644)
    for directory in [app,*(p for p in app.rglob('*') if p.is_dir())]:
        directory.chmod(0o755)


def main():
    global api_id
    safe_host()
    docker_root=decode(run(['docker','info','--format','{{json .DockerRootDir}}']))
    storage_boundary(docker_root)
    if Path('/var/lib/containerd').exists(): storage_boundary('/var/lib/containerd')
    report['docker_storage_checked']=True
    require(ROOT.is_dir() and RAW.is_dir() and WRA.is_dir() and not ROOT.is_symlink(), 'server_dataset_missing')
    require(digest(NLSC)==NLSC_SHA, 'nlsc_server_checksum')
    ids=run(['docker','ps','-q']).stdout.decode().split()
    containers=[inspect(i) for i in ids]
    apis=[c for c in containers if (c['Config'].get('Labels') or {}).get('com.docker.compose.project')==PROJECT
          and c['Config']['Labels'].get('com.docker.compose.service')=='api']
    proxies=[c for c in containers if (c['Config'].get('Labels') or {}).get('com.docker.compose.project')==PROJECT
          and c['Config']['Labels'].get('com.docker.compose.service')=='reverse_proxy']
    require(len(apis)==len(proxies)==1, 'project_container_identity')
    api,proxy=apis[0],proxies[0]
    api_id=api['Id']
    require(not any((api['HostConfig'].get('PortBindings') or {}).values()), 'api_host_port_binding')
    require(api['Config']['User']=='10001:10001', 'unexpected_api_user')
    proxy_boundary(proxy['Id'])
    report['old_api_id']=api_id
    report['old_image_id']=api['Image']
    report['proxy_id']=proxy['Id']
    save('containers-before.json',[{'id':c['Id'],'name':c['Name'],'image':c['Image'],
        'running':c['State']['Running'],'health':c['State'].get('Health',{}).get('Status'),
        'environment_names':sorted(x.split('=',1)[0] for x in c['Config'].get('Env',[]))}
        for c in containers])
    labels=api['Config']['Labels']
    require(Path(labels['com.docker.compose.project.working_dir']).resolve()==REPO, 'compose_working_directory')
    files=[Path(p).resolve() for p in labels['com.docker.compose.project.config_files'].split(',')]
    permitted={REPO/'docker-compose.selfhost.yml',ETC/'datasets.override.yml',
               ETC/'valuation.override.yml',ETC/'local-frontend.override.yml'}
    require(set(files)<=permitted and REPO/'docker-compose.selfhost.yml' in files
            and ETC/'datasets.override.yml' in files and ETC/'valuation.override.yml' in files,
            'unreviewed_compose_files')
    compose=['docker','--host','unix:///var/run/docker.sock','compose','--project-directory',str(REPO),'--env-file',str(ETC/'compose.env'),'-p',PROJECT]
    for file in files:
        compose+=['-f',str(file)]
    # Retain exact startup/rollback command arguments, never resolved env values.
    save('compose-command.json',{'prefix':compose,'previous_image_id':api['Image']})
    report['compose_files']=[str(p) for p in files]
    snapshot_dir=OUT/'etc-before';snapshot_dir.mkdir(mode=0o700)
    config_hashes={}
    for path in [ETC/'compose.env',ETC/'runtime.env',*(f for f in files if f.parent==ETC)]:
        require(path.is_file() and not path.is_symlink(), 'unexpected_config_path')
        shutil.copy2(path,snapshot_dir/path.name)
        config_hashes[str(path)]=digest(path)
        require(digest(snapshot_dir/path.name)==config_hashes[str(path)],'configuration_changed_during_backup')
    save('configuration-sha256-before.json',config_hashes)
    # Discover the owning private databases; never guess a valuation container.
    owners={}
    for c in containers:
        if (Path(c.get('Path','')).name!='postgres'
            and not c['Config']['Image'].split('/')[-1].startswith('postgres')
            and not (c['Config'].get('Labels') or {}).get('com.docker.compose.service','').startswith('postgres')):
            continue
        postgres_boundary(c['Id'])
        probe=psql(c['Id'],'postgres',"select coalesce(json_agg(datname),'[]') from pg_database where datname in ('proptech_app','proptech_api_usage','proptech_valuation');")
        for database in decode(probe):
            require(database not in owners, 'ambiguous_database_owner')
            owners[database]=c['Id']
    require(set(owners)=={'proptech_app','proptech_api_usage','proptech_valuation'}, 'database_ownership_incomplete')
    for container in set(owners.values()):
        postgres_boundary(container)
    save('database-containers.json',owners)
    db=owners[DATABASE]
    require(int(psql(db,DATABASE,'show server_version_num;').stdout)>=150000, 'postgres_version_requires_15')
    security_before=decode(run(['docker','exec',api_id,'python','-c',SECURITY]))
    verify_database_identity(owners,security_before)
    save('security-before.json',security_before)
    baseline=db_json(db,DATABASE,"""select json_build_object(
      'total',count(*),'official',count(*) filter(where source='official_plvr_opendata'),
      'nonofficial',count(*) filter(where source<>'official_plvr_opendata'),
      'future_official',count(*) filter(where source='official_plvr_opendata' and transaction_period>to_char(current_date,'YYYY-MM')),
      'known_row',count(*) filter(where id=38652 and source='official_plvr_opendata')) from real_price_transactions;""")
    require(baseline=={'total':451744,'official':451672,'nonofficial':72,'future_official':0,'known_row':1}, 'serving_population_changed')
    save('population-before.json',baseline)
    checkpoint('database-backup')
    archive=OUT/'valuation-before.dump'
    with archive.open('xb') as stream:
        run(['docker','exec','-u','postgres',db,'pg_dump','-h','/var/run/postgresql','-p','5432','-U','postgres','-d',DATABASE,'-Fc','--no-owner','--no-acl'],stdout=stream,timeout=1200)
    require(archive.stat().st_size>0 and archive.open('rb').read(5)==b'PGDMP', 'backup_archive_invalid')
    with archive.open('rb') as stream:
        toc=run(['docker','exec','-i','-u','postgres',db,'pg_restore','--list'],stdin=stream,timeout=120)
    require(bool(toc.stdout.strip()), 'backup_toc_missing')
    save('backup-verification.json',{'sha256':digest(archive),'bytes':archive.stat().st_size,'toc_verified':True})
    snapshot=OUT/'serving-before.jsonl'
    with snapshot.open('xb') as stream:
        psql(db,DATABASE,"set timezone='UTC'; select row_to_json(t) from (select * from real_price_transactions order by id) t;",output=stream,timeout=1200)
    require(sum(1 for _ in snapshot.open('rb'))==451744,'snapshot_population_mismatch')
    checkpoint('offline-image-and-artifact-verification')
    # Copy ONLY reviewed application patches, not datasets, dotfiles or secrets.
    patched=[
      'services/local_artifact_store.py','services/wra_flood_runtime.py',
      'services/gsmma_geological_sensitivity_runtime.py','services/provider_config_contract.py',
      'services/production_artifact_registry.py','services/plvr_serving_quality.py',
      'services/valuation_providers/postgres_provider.py','services/plvr_market_aggregate_service.py',
      'services/market_segmentation_service.py','services/terrain_risk_providers/wra_flood_provider.py',
      'services/terrain_risk_providers/gsmma_geological_sensitivity_provider.py',
      'scripts/ops/reconcile_plvr_special_notes.py','frontend_next/lib/taiwan-admin-areas.json',
      'services/plvr_import_service.py','services/taiwan_admin_registry.py','services/plvr_data_integrity.py']
    dependencies=patched+['database/migrations/023_add_market_serving_exclusions.sql']
    hashes={name:digest(REPO/name) for name in dependencies}
    save('application-sha256.json',hashes)
    context=OUT/'image-context'
    stage_image_context(REPO,context,patched,ENTRYPOINT)
    base_tag='proptech-professor-base:'+RUN_ID
    image='proptech-professor-api:'+RUN_ID
    run(['docker','tag',api['Image'],base_tag])
    (context/'Dockerfile').write_text('FROM '+base_tag+'\nUSER root\nCOPY --chown=10001:10001 app/ /app/\nRUN chmod 0755 /app\nWORKDIR /app\nUSER 10001:10001\n')
    run(['docker','build','--pull=false','--network=none','-t',image,context],timeout=1200)
    report['new_image']=image
    report['new_image_id']=decode(run(['docker','image','inspect',image]))[0]['Id']
    # Match the privileged offline job's UID and capability restrictions. This
    # only parses --help: no data scan, database access or host apply occurs.
    launch=run(['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
       '--security-opt','no-new-privileges:true','--user','0:0','--memory','256m','--pids-limit','64',
       '--entrypoint','python',image,'scripts/ops/reconcile_plvr_special_notes.py','--help'],check=False)
    report['reconciliation_launch_check']={'exit_code':launch.returncode,'user':'0:0','cap_drop_all':True}
    save('apply-report.json',report)
    require(launch.returncode==0,'reconciliation_launch_check_failed')
    expected={entry['scenario']:{'sha256':entry['artifact_sha256'],'count':entry['feature_count']}
              for entry in json.loads((REPO/'reports/professor-final-integration/reference-artifact-validation.json').read_text())['wra']}
    require(len(expected)==10,'wra_reference_incomplete')
    # This one nonsecret fixture is readable only inside the test container mount.
    expected_path=OUT/'expected-wra.json';expected_path.write_text(json.dumps(expected));expected_path.chmod(0o644)
    verification=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
      '--security-opt','no-new-privileges:true','--user','10001:10001','--memory','1g','--cpus','1',
      '--pids-limit','64','--entrypoint','python',
      '--mount',f'type=bind,src={WRA},dst=/srv/proptech/datasets/wra/flood/v1,readonly',
      '--mount',f'type=bind,src={NLSC},dst=/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz,readonly',
      '--mount',f'type=bind,src={expected_path},dst=/evidence/expected-wra.json,readonly',image,'-c',VERIFY_ARTIFACTS]
    artifacts=decode(run(verification,timeout=900))
    save('local-artifact-verification.json',artifacts)
    checkpoint('plvr-strong-fact-reconciliation')
    scratch=OUT/'sqlite-temp'
    scratch.mkdir(mode=0o700)
    # The tested reconciler scans all releases, including blank-note revisions.
    # It writes a private disk-backed index and never changes source files.
    reconciliation=run(['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
       '--security-opt','no-new-privileges:true','--user','0:0','--memory','2g','--cpus','1','--pids-limit','64',
       '--env','SQLITE_TMPDIR=/evidence/sqlite-temp','--env','TMPDIR=/evidence/sqlite-temp',
       '--entrypoint','python','--mount',f'type=bind,src={RAW},dst=/raw,readonly',
       '--mount',f'type=bind,src={snapshot},dst=/snapshot.jsonl,readonly',
       '--mount',f'type=bind,src={OUT},dst=/evidence',image,
       'scripts/ops/reconcile_plvr_special_notes.py','--serving-export','/snapshot.jsonl',
       '--raw-root','/raw','--output','/evidence/reconciliation','--as-of',AS_OF],timeout=7200,check=False)
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(REPO))
    from scripts.ops.reconcile_plvr_special_notes import safe_process_report
    child_report=safe_process_report(reconciliation.stdout,reconciliation.returncode)
    save('reconciliation-result.json',child_report)
    report['reconciliation_process']=child_report
    save('apply-report.json',report)
    require(reconciliation.returncode==0,'reconciliation_process_failed')
    summary=json.loads((OUT/'reconciliation/summary.json').read_text())
    require(child_report.get('status')==summary.get('status'),'reconciliation_child_report_mismatch')
    require(summary['status']=='REVIEW_REQUIRED' and summary['known_serial_unique_match_to_38652'], 'known_transaction_not_unique')
    require(summary['serving_snapshot_sha256']==digest(snapshot),'reconciliation_snapshot_changed')
    report['reconciliation']={k:summary[k] for k in ['classifications','unique_serving_rows_eligible','known_serial_unique_match_to_38652']}
    # Validate every proposed identity against the private current-serving index.
    index=sqlite3.connect('file:'+str(OUT/'reconciliation/fact-index.sqlite')+'?mode=ro',uri=True)
    candidates=[];seen=set()
    for line in (OUT/'reconciliation/classifications.jsonl').open():
        item=json.loads(line)
        if item['classification']!='UNIQUE_MATCH':
            continue
        identity=item['serving_transaction_id']
        require(isinstance(identity,int) and identity not in seen and item['official_id'], 'duplicate_or_missing_exclusion_identity')
        require(index.execute('select fact_key from serving where id=?',[identity]).fetchone()==(item['fact_sha256'],),'exclusion_facts_not_in_snapshot')
        seen.add(identity);candidates.append(item)
    index.close()
    require(len(candidates)==summary['unique_serving_rows_eligible'] and 38652 in seen, 'exclusion_count_mismatch')
    for line in (OUT/'reconciliation/raw-file-sha256.jsonl').open():
        item=json.loads(line);path=(RAW/item['file']).resolve()
        require(path.is_relative_to(RAW.resolve()) and digest(path)==item['sha256'],'raw_evidence_changed_during_scan')
    require(all(digest(REPO/name)==sha for name,sha in hashes.items()),'application_changed_during_preparation')
    # Capture read models separately in the verified full archive; SQL below
    # updates aggregates/coverage only. It never deletes source transactions.
    sql_path=OUT/'apply-valuation.sql'
    sys.path.insert(0,str(REPO))
    from services.plvr_data_integrity import canonical_region_storage_keys
    keys=list(canonical_region_storage_keys())
    require(len(keys)==368,'canonical_region_registry_changed')
    def literal(value):
        return "'"+str(value).replace("'","''")+"'"
    key_array='ARRAY['+','.join(literal(key) for key in keys)+']::text[]'
    with sql_path.open('x') as sql:
        sql.write("begin; set local search_path=pg_catalog,public; set local standard_conforming_strings=on; set local timezone='UTC'; set local lock_timeout='10s'; set local statement_timeout='1200s'; set local work_mem='16MB';\n")
        sql.write('lock table public.real_price_transactions in share mode;\n')
        sql.write('create temporary table integration_snapshot(payload jsonb);\n')
        sql.write("copy integration_snapshot(payload) from stdin with (format csv, delimiter E'\\x02', quote E'\\x01');\n")
        with snapshot.open() as stream:
            for line in stream:
                require('\x01' not in line and '\x02' not in line,'snapshot_control_character')
                sql.write(line)
        sql.write('\\.\ncreate unique index on integration_snapshot(((payload->>\'id\')::bigint));\n')
        snapshot_guard="""
        do $$ begin
          if (select count(*) from public.real_price_transactions)<>451744 or
             exists(select from public.real_price_transactions t full join integration_snapshot s
               on t.id=(s.payload->>'id')::bigint where to_jsonb(t) is distinct from s.payload)
          then raise exception 'current_serving_snapshot_changed'; end if;
        end $$;
        """
        sql.write(snapshot_guard)
        sql.write((REPO/'database/migrations/023_add_market_serving_exclusions.sql').read_text()+'\n')
        sql.write('lock table public.market_serving_exclusions in share row exclusive mode;\n')
        sql.write('create temporary table integration_candidates(payload jsonb);\n')
        sql.write("copy integration_candidates(payload) from stdin with (format csv, delimiter E'\\x02', quote E'\\x01');\n")
        for item in candidates:
            sql.write(json.dumps(item,ensure_ascii=False)+'\n')
        sql.write('\\.\n')
        sql.write("""
        do $$ begin
          if (select count(*) from integration_candidates where (payload->>'serving_transaction_id')::bigint=38652
              and payload->>'official_id'='RPWNMLNKNHLGFBF78EA')<>1
          then raise exception 'known_transaction_not_unique'; end if;
          if exists(select from public.market_serving_exclusions e left join integration_candidates c
              on e.serving_transaction_id=(c.payload->>'serving_transaction_id')::bigint
              where c.payload is null
                 or e.fact_sha256 is distinct from (c.payload->>'fact_sha256')
                 or e.source_official_id is distinct from (c.payload->>'official_id'))
          then raise exception 'prior_exclusion_evidence_conflicts'; end if;
        end $$;
        """)
        sql.write("insert into public.market_serving_exclusions(serving_transaction_id,reason_code,source_evidence_class,source_official_id,evidence_version,fact_sha256) select (payload->>'serving_transaction_id')::bigint,'special_note_requires_review','UNIQUE_MATCH',payload->>'official_id',"+literal(RUN_ID)+",payload->>'fact_sha256' from integration_candidates where true on conflict(serving_transaction_id) do nothing;\n")
        sql.write('grant select on public.market_serving_exclusions,public.market_serving_transactions,public.market_serving_district_periods to valuation_runtime;\n')
        # Same canonical eligibility and ceiling as the serving Market queries.
        sql.write("create temporary table integration_aggregates as select p.*,now() as built_at from public.market_serving_district_periods p where (replace(regexp_replace(trim(county),'\\s+','','g'),'臺','台')||'|'||replace(regexp_replace(trim(district),'\\s+','','g'),'臺','台'))=any("+key_array+") and period<="+literal(AS_OF)+";\n")
        sql.write("do $$ begin if not exists(select from integration_aggregates) then raise exception 'no_eligible_market_rows'; end if; end $$;\n")
        sql.write("""
        insert into public.market_district_period_aggregates
          (county,district,period,average_unit_price,transaction_count,record_count,source_name,source_updated_at,coverage_status,data_status,aggregation_method,built_at)
        select county,district,period,average_unit_price,transaction_count,record_count,source_name,source_updated_at,coverage_status,data_status,aggregation_method,built_at
        from integration_aggregates where true on conflict(county,district,period) do update set
          average_unit_price=excluded.average_unit_price,transaction_count=excluded.transaction_count,
          record_count=excluded.record_count,source_name=excluded.source_name,source_updated_at=excluded.source_updated_at,
          coverage_status=excluded.coverage_status,data_status=excluded.data_status,
          aggregation_method=excluded.aggregation_method,built_at=excluded.built_at;
        update public.market_district_period_aggregates old set
          average_unit_price=null,transaction_count=0,record_count=0,source_updated_at=null,
          coverage_status='coverage_unknown',data_status='unavailable',built_at=now()
        where not exists(select from integration_aggregates n where (n.county,n.district,n.period)=(old.county,old.district,old.period));
        create temporary table integration_coverage as
          select county,district,sum(transaction_count)::integer n,max(source_updated_at) updated
          from integration_aggregates group by county,district;
        update public.market_region_coverage c set
          valid_market_candidate_count=coalesce((select n from integration_coverage a where
            replace(regexp_replace(trim(c.county),'\\s+','','g'),'臺','台')=replace(a.county,'臺','台') and
            replace(regexp_replace(trim(c.district),'\\s+','','g'),'臺','台')=replace(a.district,'臺','台')),0),
          source_updated_at=(select updated from integration_coverage a where
            replace(regexp_replace(trim(c.county),'\\s+','','g'),'臺','台')=replace(a.county,'臺','台') and
            replace(regexp_replace(trim(c.district),'\\s+','','g'),'臺','台')=replace(a.district,'臺','台')),
          reconciled_at=now();
        update public.market_region_coverage set coverage_status=case when valid_market_candidate_count>0 then 'covered' else 'coverage_unknown' end;
        insert into public.market_read_model_metadata
          (read_model_version,refresh_status,coverage_status,source_name,source_updated_at,earliest_period,latest_period,
           available_county_count,available_district_count,aggregate_region_count,built_at,caveat)
        select 'v1','ready','partial','Official PLVR OpenData aggregate',max(source_updated_at),min(period),max(period),
          count(distinct county),count(distinct(county,district)),count(*),now(),
          'Official PLVR aggregates exclude uniquely reconciled special-note transactions; coverage remains partial.'
        from integration_aggregates where true on conflict(read_model_version) do update set
          refresh_status=excluded.refresh_status,coverage_status=excluded.coverage_status,source_name=excluded.source_name,
          source_updated_at=excluded.source_updated_at,earliest_period=excluded.earliest_period,latest_period=excluded.latest_period,
          available_county_count=excluded.available_county_count,available_district_count=excluded.available_district_count,
          aggregate_region_count=excluded.aggregate_region_count,built_at=excluded.built_at,caveat=excluded.caveat;
        do $$ begin
          if (select count(*) from real_price_transactions where id=38652)<>1 or
             exists(select from market_serving_transactions where id=38652)
          then raise exception 'known_row_retention_or_exclusion_failed'; end if;
          if exists(select from market_region_coverage c full join integration_coverage a
            on replace(regexp_replace(trim(c.county),'\\s+','','g'),'臺','台')=replace(a.county,'臺','台')
           and replace(regexp_replace(trim(c.district),'\\s+','','g'),'臺','台')=replace(a.district,'臺','台')
            where c.county is null or c.valid_market_candidate_count<>coalesce(a.n,0)
               or c.source_updated_at is distinct from a.updated)
          then raise exception 'coverage_reconciliation_mismatch'; end if;
        end $$;
        """)
        sql.write(snapshot_guard)
        sql.write("select 'PROFESSOR_APPLY_RESULT:'||json_build_object('raw_rows',451744,'known_raw_row_retained',true,'known_row_excluded',true,'exclusions',(select count(*) from market_serving_exclusions),'aggregate_groups',(select count(*) from integration_aggregates),'coverage_rows',(select count(*) from market_region_coverage))::text;\ncommit;\n")
    report['sql_sha256']=digest(sql_path)
    replacements,planned_config=plan_configuration(compose,files,image)
    require(all(digest(REPO/name)==sha for name,sha in hashes.items()),'application_changed_before_apply')
    safe_host()
    require(all(digest(Path(path))==sha for path,sha in config_hashes.items()),'configuration_changed_before_maintenance')
    require(inspect(api_id)['State']['Running'] and inspect(api_id)['Image']==api['Image'],'api_changed_during_preparation')
    for container in set(owners.values()): postgres_boundary(container)
    proxy_boundary(proxy['Id'])
    # All offline gates passed. Stop proxy/API through the database transition.
    # No old image may serve unfiltered data after a successful/uncertain commit.
    checkpoint('api-maintenance-and-database-apply')
    report['transition_started']=True
    save('apply-report.json',report)
    run(['docker','stop','--time','30',proxy['Id']])
    report['proxy_stopped']=True
    run(['docker','stop','--time','30',api_id])
    report['api_stopped']=True
    report['database_apply_attempted']=True
    save('apply-report.json',report)
    with sql_path.open('rb') as stream:
        applied=psql(db,DATABASE,source=stream,timeout=1800)
    lines=[line for line in applied.stdout.decode().splitlines() if line.startswith('PROFESSOR_APPLY_RESULT:')]
    require(len(lines)==1,'database_apply_receipt_missing')
    report['database_committed']=True
    report['database_result']=json.loads(lines[0].split(':',1)[1])
    save('apply-report.json',report)
    checkpoint('runtime-configuration-and-recreation')
    require(all(digest(Path(path))==sha for path,sha in config_hashes.items()),'configuration_changed_before_install')
    for path,value in replacements.items():
        metadata=path.stat();temporary=path.with_name('.'+path.name+'.'+RUN_ID)
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        temporary.chmod(metadata.st_mode & 0o777);os.chown(temporary,metadata.st_uid,metadata.st_gid)
        os.replace(temporary,path)
    report['configuration_written']=True
    save('apply-report.json',report)
    checked=decode(run(compose+['config','--format','json']))
    require(checked==planned_config,'compose_configuration_changed_since_preview')
    run(compose+['up','-d','--no-deps','--no-build','--pull','never','--force-recreate','api'],timeout=240)
    api_id=run(compose+['ps','-q','api']).stdout.decode().strip()
    require(bool(api_id),'new_api_missing')
    report['new_api_id']=api_id;report['runtime_recreated']=True
    wait_healthy(api_id)
    report['api_stopped']=False
    checkpoint('post-apply-security')
    mounted=inspect(api_id)
    require(mounted['Image']==report['new_image_id'],'running_image_mismatch')
    require(not any((mounted['HostConfig'].get('PortBindings') or {}).values()),'new_api_published')
    for mount in mounted['Mounts']:
        require('Crucial X9' not in mount['Source'],'active_x9_bind')
        if mount['Destination'].startswith('/srv/proptech/datasets/'):
            require(not mount['RW'],'dataset_mount_writable')
    require(digest(NLSC)==NLSC_SHA,'nlsc_checksum_after_apply')
    for container in set(owners.values()): postgres_boundary(container)
    proxy_boundary(proxy['Id']);safe_host()
    security_after=decode(run(['docker','exec',api_id,'python','-c',SECURITY]))
    verify_database_identity(owners,security_after)
    save('security-after.json',security_after)
    usage=decode(run(['docker','exec',api_id,'python','scripts/ops/selfhost_runtime.py','health']))
    require(usage.get('status')=='pass','usage_runtime_health')
    # Verify private identities, TLS and mounts before restoring proxy traffic.
    # nginx resolves its upstream at startup; restart only this existing proxy.
    run(['docker','restart',proxy['Id']],timeout=90)
    wait_healthy(proxy['Id'])
    report['proxy_stopped']=False
    checkpoint('post-apply-api-acceptance')
    filtered_expected=db_json(db,DATABASE,"""select json_build_object('count',count(*),'average',round(avg(unit_price_per_ping)::numeric,2))
      from market_serving_transactions where source='official_plvr_opendata' and replace(trim(city),'臺','台')='新北市'
      and trim(district)='新莊區' and transaction_period='2026-05'
      and unit_price_per_ping>0 and unit_price_per_ping<=500 and total_price>0 and area_ping>0;""")
    checks={}
    for path in ['/health','/readiness']:
        code,value=api_request(path)
        require(code==200 and value.get('status')==('ok' if path=='/health' else 'ready'),'api_health_contract')
        checks[path]={'http':code,'status':value['status']}
    code,value=api_request('/demographics/villages/65000050016/latest')
    observation=value.get('observation',{})
    require(code==200 and observation.get('total_population')==6134 and observation.get('household_count')==3834,'ris_contract')
    checks['ris']={'population':6134,'households':3834,'month':observation.get('statistic_yyymm')}
    code,value=api_request('/demographics/location?'+urlencode({'latitude':25.035570879000026,'longitude':121.4525876531026}))
    require(code==200 and value.get('village_resolution',{}).get('district_code')=='65000050016'
            and value.get('demographics',{}).get('total_population')==6134,'nlsc_ris_contract')
    checks['nlsc_ris']={'district_code':'65000050016','population':6134}
    request={'city':'新北市','district':'新莊區','road':'中正路','building_type':'華廈','area_ping':34,'building_age_years':20,'floor':2}
    for path,payload,status_key in [('/valuation/estimate',request,'valuation_status'),
        ('/valuation/trend',{k:v for k,v in request.items() if k!='floor'},'trend_status'),
        ('/valuation/property-search',{'city':'新北市','districts':['新莊區'],'budget_max':2000,'limit':5},'search_status')]:
        code,value=api_request(path,payload)
        require(code==200 and value.get('source_details',{}).get('query_status')!='failed','valuation_query_failed')
        accepted=value.get(status_key)=='available'
        # Sparse official comparables are an explicit limitation, never provider
        # failure or a fabricated price. No-data is acceptable only with proof.
        if path=='/valuation/estimate' and value.get(status_key)=='no_data':
            accepted=(value.get('valuation_reason_code')=='official_comparables_insufficient'
                      and value.get('result_origin')=='official' and value.get('source')=='postgres'
                      and value.get('is_actionable') is False
                      and value.get('estimate_total_price') is None and value.get('estimate_unit_price_per_ping') is None
                      and not value.get('comparables'))
        require(accepted,'valuation_contract')
        checks[path]={'http':code,status_key:value[status_key]}
    code,value=api_request('/valuation/data-status')
    require(code==200 and value.get('official_records_count')==451672 and value.get('sample_records_count')==72,'forensic_population_status')
    checks['valuation_status']={k:value.get(k) for k in ['active_source','official_records_count','sample_records_count','freshness_status','is_full_taiwan']}
    for payload in [{'county':'新北市','district':'新莊區','road':'中正路'},
                    {'county':'新北市','district':'新莊區','period':'2026-05'}]:
        code,value=api_request('/market-insights/query',payload)
        require(code==200,'market_http_contract')
        if payload.get('period'):
            if filtered_expected['count']:
                require(value.get('data_status')=='available'
                        and value.get('transaction_count')==filtered_expected['count']
                        and value.get('average_unit_price')==filtered_expected['average'],'market_filtered_aggregate_mismatch')
            else:
                require(value.get('data_status')=='no_data'
                        and value.get('coverage_status')=='covered'
                        and value.get('average_unit_price') is None
                        and value.get('transaction_count') in {None,0}
                        and value.get('reason_code')=='market_summary_missing',
                        'market_empty_period_contract')
        else:
            require(value.get('data_status')=='available' and (value.get('transaction_count') or 0)>0,'market_populated_road_unavailable')
        checks['market_'+payload.get('period','road')]={k:value.get(k) for k in ['data_status','transaction_count','average_unit_price','coverage_status']}
    # Real Terrain endpoint, both a loaded hit and a distinct no-match; no R2.
    scenario=next(r for r in artifacts['wra'] if r['scenario']=='24h-350mm')
    for label,point in [('matched',scenario['matched_point']),('no_match',[0,0])]:
        code,value=api_request('/terrain-risk/analyze',{'latitude':point[1],'longitude':point[0],'include_layers':['flood']})
        flood=value.get('hazards',{}).get('flood',{})
        require(code==200 and flood.get('status')=='available' and flood.get('matched')==(label=='matched')
                and flood.get('source',{}).get('storage_backend')=='local'
                and flood.get('source',{}).get('artifact_sha256')==scenario['sha256'],'terrain_local_provenance')
        if label=='no_match': require(flood.get('level') not in {'safe','low'},'no_match_interpreted_safe')
        checks['wra_'+label]={'http':code,'matched':flood['matched'],'provenance':flood['source']}
    save('api-acceptance.json',checks)
    proxy_boundary(proxy['Id']);safe_host()
    report.update(status='PASS',phase='complete',ordinary_runtime_needs_x9=False,
                  known_raw_row_retained=True,known_row_excluded=True,coverage_reconciled=True,
                  unsupported_local_providers=['GSMMA sensitivity','ARDSWC','liquefaction'],
                  cwa_1897_1989_gap='accepted_untouched',production_ready=False,
                  completed_at=datetime.now(timezone.utc).isoformat())
    save('acceptance.json',report)


rollback='''# Local apply rollback / recovery

The verified valuation-before.dump is a forensic/pre-change backup, not an
instruction to overwrite a running database. Keep it private. No raw source
transactions were changed. etc-before/ contains the original configuration.
compose-command.json records the exact original compose prefix and old image ID.

1. Read apply-report.json. If database_apply_attempted is true and no confirmed
   receipt exists, treat commit state as UNCERTAIN and leave API stopped.
2. Keep API stopped while restoring configuration: copy each file from
   etc-before/ back to its recorded /etc/proptech-selfhost filename, preserving
   permissions. Restoring dataset bindings may require keeping X9 attached.
3. Before starting any previous image, verify it still honors the exclusion view.
   Do not silently re-enable an older unfiltered Market/Valuation serving path.
   Prefer repairing/reapplying the new verified image from this run. All image
   tags are retained; no Docker volumes or databases were removed.
4. If failure preceded database_apply_attempted, original configuration/database
   remain valid. Start the original API container if it was stopped, then restart
   the existing reverse proxy. Use the exact prefix in compose-command.json if
   recreation is necessary; scope it to api only with --no-deps --no-build.
5. A database restore must first be rehearsed into a separate disposable target.
   No automatic destructive restore, source-row deletion or exclusion evidence
   deletion is supplied. Preserve the additive quarantine and its provenance.

This run does not alter DNS, Vercel, Cloud Run, public ingress, disks or X9 files.
Never use /dev/sda. Keep market_ops disabled and databases without published ports.
'''
(OUT/'ROLLBACK.md').write_text(rollback)

try:
    main()
except BaseException as exc:
    # A stopped API stays stopped if database commit is successful or uncertain.
    # Never silently restore an older image that ignores serving exclusions.
    report.update(status='FAILED',error_class=type(exc).__name__,failed_phase=report.get('phase'))
    if report.get('transition_started'):
        fail_closed_stop()
    save('apply-report.json',report)
    save('acceptance.json',report)
    print('Apply failed closed. Read private apply-report.json and ROLLBACK.md in '+str(OUT),flush=True)
    result=1
else:
    save('apply-report.json',report)
    print('Local apply accepted. Evidence: '+str(OUT),flush=True)
    result=0

raise SystemExit(result)
PY
