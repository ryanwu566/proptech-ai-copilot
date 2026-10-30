#!/usr/bin/env python3
"""Stage5 preparation/audits only. No deployment, firewall, certificate orders.

Root --host-audit is a metadata-only inspection, never a public apply. A public
apply entrypoint is intentionally not offered before real network/identity facts.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.request import build_opener,ProxyHandler,Request
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[2]
EXEC_PATH='/usr/sbin:/usr/bin:/sbin:/bin'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from services.professor_ingress import classify_network,readiness,render_edge,render_http_challenge,render_inner_proxy,render_units,certificate_command,firewall_plan
from services.professor_credentials import build_matrix,validate_cloud_metadata,ACTIVE
from services.professor_credential_audit import build_dependency_matrix
from services.professor_router_plan import conditional_https_plan
from services.professor_retirement_inventory import retirement_inventory
from services.professor_adoption_plan import adoption_retirement_plan


def require(value,reason):
    if not value:raise ValueError(reason)


def run(args,timeout=30):
    result=subprocess.run(args,capture_output=True,timeout=timeout,
        env={'PATH':EXEC_PATH,'LANG':'C.UTF-8','DOCKER_HOST':'unix:///var/run/docker.sock',
             'DOCKER_CONFIG':'/run/proptech-selfhost/unused-readonly-docker-config'})
    require(len(result.stdout)+len(result.stderr)<=2_000_000,'audit_output_exceeds_bound')
    return result.returncode,result.stdout


def json_command(args):
    code,raw=run(args);require(code==0,'audit_command_unavailable')
    return json.loads(raw)


def tool_version(tool):
    executable=shutil.which(tool)
    if not executable:return None
    # nginx writes its version to stderr; this diagnostic contains no config.
    result=subprocess.run([executable,'-v'] if tool=='nginx' else [executable,'--version'],
        capture_output=True,timeout=10,env={'PATH':os.defpath,'LANG':'C.UTF-8'})
    match=re.search(rb'\b([0-9]+\.[0-9]+\.[0-9]+)\b',result.stdout+result.stderr)
    return match.group(1).decode() if result.returncode==0 and match else 'UNVERIFIED'


def public_ip(url,family):
    try:
        opener=build_opener(ProxyHandler({}))
        with opener.open(url,timeout=6) as response:raw=response.read(128).decode().strip()
        value=ipaddress.ip_address(raw)
        require(value.version==family and value.is_global,'non_global_observation')
        return {'status':'PUBLIC_IP_OBSERVED','address':str(value),'family':family,'source':url,'inbound_confirmed':False}
    except Exception:return {'status':'UNAVAILABLE','family':family,'source':url,'inbound_confirmed':False}


def network_audit():
    links=json_command(['ip','-j','address','show']);routes=json_command(['ip','-j','route','show','table','main'])
    v6routes=json_command(['ip','-j','-6','route','show','table','main'])
    defaults=[r for r in routes if r.get('dst')=='default' and r.get('gateway')]
    require(defaults,'default_route_unknown');default=min(defaults,key=lambda r:r.get('metric',0))
    link=next(r for r in links if r['ifname']==default['dev'])
    v4=[r['local'] for r in link['addr_info'] if r['family']=='inet']
    v6=[r['local'] for r in link['addr_info'] if r['family']=='inet6']
    require(len(v4)==1,'lan_address_ambiguous')
    observations=[public_ip('https://api.ipify.org',4),public_ip('https://checkip.amazonaws.com',4)]
    facts={'lan_ipv4':v4[0],'gateway':default['gateway'],'interface':default['dev'],
        'public_ipv4_observations':[r['address'] for r in observations if r['status']=='PUBLIC_IP_OBSERVED'],
        'router_wan_ipv4':None,'global_ipv6':[v for v in v6 if ipaddress.ip_address(v).is_global],
        'ipv6_default_route':any(r.get('dst')=='default' for r in v6routes),'outside_lan_inbound_confirmed':False}
    code,raw=run(['ss','-H','-lnt']);require(code==0,'listener_audit_unavailable')
    listeners=[]
    for line in raw.decode().splitlines():
        parts=line.split()
        if len(parts)>=4:listeners.append(parts[3])
    ufw_config=None
    try:
        for line in Path('/etc/ufw/ufw.conf').read_text().splitlines():
            if line.startswith('ENABLED='):ufw_config=line=='ENABLED=yes'
    except PermissionError:pass
    code,_=run(['ufw','status','verbose']);effective='AVAILABLE' if code==0 else 'ROOT_READONLY_INSPECTION_REQUIRED'
    return {'schema':'professor-stage5-network-audit-v1','checked_at':datetime.now(timezone.utc).isoformat(),
        'facts':facts,'classification':classify_network(facts),'default_interface_ipv6':v6,
        'all_interface_ipv6':[a['local'] for row in links for a in row['addr_info'] if a['family']=='inet6'],
        'public_observations':observations,'tcp_listeners':listeners,
        'port80_occupied':any(v.endswith(':80') for v in listeners),'port443_occupied':any(v.endswith(':443') for v in listeners),
        'postgres_listener_present':any(v.endswith(':5432') for v in listeners),
        '8080_loopback_only':bool([v for v in listeners if v.endswith(':8080')]) and all(v=='127.0.0.1:8080' for v in listeners if v.endswith(':8080')),
        'ufw_enabled_in_configuration':ufw_config,'effective_firewall':effective,
        'tools':{n:tool_version(n) for n in ('nginx','caddy','certbot')},
        'cloud_control_plane_cli_available':{n:shutil.which(n) is not None for n in ('gcloud','render','vercel')},
        'configuration_values_returned':False,'host_changes':False,'external_vantage_used':False}


def metadata(path):
    try:
        s=path.lstat()
        return {'present':True,'regular':stat.S_ISREG(s.st_mode),'symlink':stat.S_ISLNK(s.st_mode),
                'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode)),'links':s.st_nlink}
    except FileNotFoundError:return {'present':False}
    except PermissionError:return {'present':'UNKNOWN_PERMISSION_DENIED'}


def firewall_summary(value):
    """No comments, log prefixes or opaque expression strings are returned."""
    chains=[];dnat=[];rules=0
    for entry in value.get('nftables',[]):
        if 'chain' in entry:
            c=entry['chain'];chains.append({k:c.get(k) for k in ('family','table','name','type','hook','policy')})
        if 'rule' in entry:
            rules+=1
            for expr in entry['rule'].get('expr',[]):
                if isinstance(expr,dict) and isinstance(expr.get('dnat'),dict):
                    item=expr['dnat'];address=item.get('addr');port=item.get('port')
                    try:address=str(ipaddress.ip_address(address))
                    except (TypeError,ValueError):address='UNRESOLVED_EXPRESSION'
                    dnat.append({'address':address,'port':port if type(port) is int else 'UNRESOLVED_EXPRESSION'})
    return {'chains':chains,'rule_count':rules,'dnat_targets':dnat,'full_effective_policy_reviewed':False,
            'comments_or_log_prefixes_exported':False,'complex_rules_require_operator_review':True}


def host_audit():
    require(os.geteuid()==0,'operator_readonly_access_required')
    result=network_audit()
    result.update(schema='professor-stage5-host-audit-v1',credential_files_opened=False,
                  configuration_values_returned=False,activation_performed=False,firewall_changes=False)
    catalog=json.loads((ROOT/'config/professor-server-credentials.json').read_text())
    names=sorted(set(ACTIVE.values())|{r['secret_file'] for r in catalog['credentials'] if r.get('secret_file')})
    result['credential_file_metadata']={str(root/name):metadata(root/name) for root in (Path('/etc/proptech-selfhost/secrets'),Path('/run/proptech-selfhost/secrets')) for name in names}
    result['tls_metadata']={str(root/name):metadata(root/name) for root in (Path('/run/proptech-selfhost/tls'),Path('/etc/proptech-selfhost/tls')) for name in ('ca.crt','app/server.crt','app/server.key','usage/server.crt','usage/server.key')}
    code,raw=run(['nft','-j','list','ruleset'])
    result['effective_firewall_metadata']=firewall_summary(json.loads(raw)) if code==0 else {'status':'UNAVAILABLE'}
    services={}
    for service in ('api','postgres_app','postgres_usage','reverse_proxy'):
        code,raw=run(['docker','ps','-aq','--no-trunc','--filter','label=com.docker.compose.project=proptech-selfhost','--filter','label=com.docker.compose.service='+service])
        ids=raw.decode().split();require(code==0 and len(ids)==1 and re.fullmatch('[a-f0-9]{64}',ids[0]),'container_identity_ambiguous')
        ident=ids[0];item={'id':ident}
        # Query only explicit metadata. Never inspect/dump the Config.Env values.
        for field,template in [('image','{{json .Image}}'),('health','{{json .State.Health.Status}}'),
            ('ports','{{json .HostConfig.PortBindings}}'),('mounts','{{json .Mounts}}'),
            ('restart_policy','{{json .HostConfig.RestartPolicy}}')]:
            item[field]=json_command(['docker','inspect','--format',template,ident])
        if service=='api':
            code,raw=run(['docker','inspect','--format','{{range .Config.Env}}{{println (index (split . "=") 0)}}{{end}}',ident])
            require(code==0,'environment_name_audit_failed');names=raw.decode().split()
            require(all(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',n) for n in names),'environment_name_invalid')
            item['environment_names_only']=names
            guards=['PROFESSOR_USERDB_ENABLED=true','ANTI_ABUSE_MARKET_OPS_DISABLED=true','PLVR_SERVING_EXCLUSIONS_ENABLED=true']
            for guard in guards:
                template='{{range .Config.Env}}{{if eq . '+json.dumps(guard)+'}}{{println "MATCH"}}{{end}}{{end}}'
                code,raw=run(['docker','inspect','--format',template,ident])
                item[guard.partition('=')[0]+'_expected']=code==0 and raw.decode().strip()=='MATCH'
        services[service]=item
    result['containers']=services
    code,raw=run(['systemctl','list-unit-files','--no-pager','--no-legend','proptech*','professor*'])
    result['project_systemd_unit_metadata']=raw.decode().splitlines() if code==0 else []
    return result


def load_json(path):
    path=Path(path)
    require(path.suffix=='.json' and not path.is_symlink() and not any(x in {'secrets','.env'} for x in path.parts),'metadata_input_path_invalid')
    require(path.is_file() and path.stat().st_size<=256000,'metadata_input_invalid')
    return json.loads(path.read_text())


def save(path,value):
    from scripts.ops.professor_server_secrets import check_backing_storage
    path=validate_evidence_destination(path);check_backing_storage(path)
    require(path.parent.is_dir() and not path.parent.is_symlink(),'evidence_parent_invalid')
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw)
    os.chmod(path,0o644)


def validate_evidence_destination(path):
    path=Path(path).resolve()
    reports=(ROOT/'reports/professor-stage5-ingress').resolve()
    temporary=path.is_relative_to('/tmp') and path.relative_to('/tmp').parts[0].startswith('professor-stage5-')
    require(path.is_relative_to(reports) or temporary,'evidence_destination_forbidden')
    require(path.suffix=='.json','evidence_filename_invalid')
    return path


class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('invalid_arguments')


def main(argv=None):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    parser=Parser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--network-audit',action='store_true');group.add_argument('--host-audit',action='store_true')
    group.add_argument('--matrix',action='store_true');group.add_argument('--plan',type=Path)
    group.add_argument('--dependency-matrix',action='store_true')
    group.add_argument('--router-plan',type=Path)
    group.add_argument('--retirement-inventory',action='store_true')
    group.add_argument('--adoption-plan',action='store_true')
    parser.add_argument('--cloud-metadata',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path)
    try:
        args=parser.parse_args(argv)
        if args.network_audit:result=network_audit()
        elif args.host_audit:result=host_audit()
        elif args.matrix:result=build_matrix(ROOT,[validate_cloud_metadata(load_json(p)) for p in args.cloud_metadata])
        elif args.dependency_matrix:result=build_dependency_matrix(ROOT,[validate_cloud_metadata(load_json(p)) for p in args.cloud_metadata])
        elif args.router_plan:result=conditional_https_plan(load_json(args.router_plan))
        elif args.retirement_inventory:result=retirement_inventory(ROOT)
        elif args.adoption_plan:
            dependencies=build_dependency_matrix(ROOT,[validate_cloud_metadata(load_json(p)) for p in args.cloud_metadata])
            result=adoption_retirement_plan(dependencies,load_json(ROOT/'reports/professor-stage5-ingress/local-runtime-checks.json'))
        else:
            plan=load_json(args.plan);result=readiness(plan)
            result['firewall_plan']=firewall_plan(plan)
            result['prepared_inner_proxy']=render_inner_proxy()
            if plan['identity']['name'] and plan['identity']['control_verified']:
                result['prepared_public_tls_config']=render_edge(plan)
                result['prepared_existing_http01_site']=render_http_challenge(plan)
                result['prepared_systemd_units']=render_units(plan)
                if plan['acme']['version']:
                    result['staging_command']=certificate_command(plan,staging=True)
                    result['production_command']=certificate_command(plan,staging=False)
        if args.output:
            save(args.output,result)
            print(json.dumps({'status':'BLOCKED_PLAN' if args.plan and not result['ready_for_operator_apply'] else 'PASS_AUDIT_ONLY','evidence':str(args.output),'configuration_values_returned':False,'activation_performed':False}))
        elif args.host_audit:
            from scripts.ops.professor_server_secrets import check_backing_storage
            check_backing_storage(Path('/tmp'))
            folder=Path(tempfile.mkdtemp(prefix='professor-stage5-host-',dir='/tmp'))
            save(folder/'diagnosis.json',result);folder.chmod(0o755)
            print(json.dumps({'status':'PASS_READONLY_AUDIT','evidence':str(folder/'diagnosis.json'),'configuration_values_returned':False,'activation_performed':False}))
        else:print(json.dumps(result,sort_keys=True))
        return 2 if args.plan and not result['ready_for_operator_apply'] else 0
    except Exception as exc:
        reason=str(exc) if isinstance(exc,ValueError) and re.fullmatch('[a-z0-9_]+',str(exc)) else 'audit_failed_details_suppressed'
        print(json.dumps({'status':'REFUSED','reason_code':reason,'configuration_values_returned':False,'activation_performed':False}));return 1


if __name__=='__main__':raise SystemExit(main())
