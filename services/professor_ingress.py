"""Pure, value-free direct-ingress planning. Never installs or changes a host."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timezone
import ipaddress
import re
from urllib.parse import urlsplit

PRODUCTION_ORIGIN='https://proptech-ai-copilot.vercel.app'
ML_SOCKET='/run/proptech-ml/inference.sock'
SHARED=ipaddress.ip_network('100.64.0.0/10')
PRIVATE=tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))


def require(value,reason):
    if not value:raise ValueError(reason)


def address(value,version=None):
    try:a=ipaddress.ip_address(value)
    except (ValueError,TypeError):raise ValueError('address_invalid') from None
    require(version is None or a.version==version,'address_family_invalid')
    return a


def classify_network(data):
    observations=[address(v,4) for v in data.get('public_ipv4_observations',[])]
    global_v4={str(v) for v in observations if v.is_global}
    public='YES' if len(global_v4)==1 and len(observations)>=2 and all(v.is_global for v in observations) else 'UNKNOWN' if global_v4 else 'NO'
    wan=data.get('router_wan_ipv4');cgnat='UNKNOWN';nat='ROUTER_WAN_UNKNOWN'
    if wan:
        wan=address(wan,4)
        if wan in SHARED:cgnat,nat='YES','CGNAT_BLOCKED'
        elif any(wan in n for n in PRIVATE):nat='UPSTREAM_PRIVATE_NAT'
        elif wan.is_global and public=='YES' and str(wan) in global_v4:cgnat,nat='NO','PUBLIC_WAN_MATCHES_EGRESS'
        else:nat='WAN_EGRESS_MISMATCH'
    v6=[str(address(v,6)) for v in data.get('global_ipv6',[]) if address(v,6).is_global]
    inbound='PENDING'
    if data.get('outside_lan_inbound_confirmed') is True:
        source=address(data.get('external_probe_source'))
        require(source.is_global and str(source) not in global_v4 and str(source) not in v6,'external_vantage_not_independent')
        require(data.get('external_probe_on_professor') is False and data.get('external_probe_tls_trusted') is True
                and data.get('external_probe_health_passed') is True and data.get('external_probe_port')==443,'external_probe_incomplete')
        require(isinstance(data.get('external_probe_target'),str),'external_probe_target_missing')
        try:observed=datetime.fromisoformat(data['external_probe_utc'].replace('Z','+00:00'))
        except (KeyError,TypeError,ValueError,AttributeError):raise ValueError('external_probe_time_invalid') from None
        require(observed.tzinfo is not None and -300<=(datetime.now(timezone.utc)-observed).total_seconds()<=86400,'external_probe_stale_or_future')
        inbound='CONFIRMED'
    elif cgnat=='YES':inbound='BLOCKED'
    return {'public_ipv4':public,'observed_public_ipv4':next(iter(global_v4)) if public=='YES' else None,
        'public_ip_status':'PUBLIC_IP_OBSERVED' if public=='YES' else 'PUBLIC_IP_UNCONFIRMED',
        'public_ipv6':'YES' if v6 and data.get('ipv6_default_route') is True else 'NO',
        'cgnat':cgnat,'nat_assessment':nat,'inbound_reachability':inbound,
        'inbound_reachability_confirmed':inbound=='CONFIRMED','router_inspection_required':cgnat=='UNKNOWN'}


def hostname(value):
    require(isinstance(value,str) and value==value.lower() and 1<len(value)<=253,'hostname_invalid')
    require(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+',value),'hostname_invalid')
    try:ipaddress.ip_address(value)
    except ValueError:return value
    raise ValueError('domain_cannot_be_ip')


def origin(value,development=False):
    require(isinstance(value,str),'origin_invalid')
    try:
        p=urlsplit(value);port=p.port
        require(p.scheme in {'http','https'} and p.hostname and not p.username and not p.password and not p.query and not p.fragment and p.path=='','origin_invalid')
        require(value==p.scheme+'://'+p.netloc and '*' not in value and not any(c.isspace() for c in value),'origin_invalid')
        if development:
            require(p.scheme=='http' and p.hostname in {'localhost','127.0.0.1'} and port in {3000,3001,5173},'development_origin_invalid')
        else:
            require(p.scheme=='https' and port in {None,443},'origin_https_required')
            hostname(p.hostname)
        return value
    except ValueError:raise ValueError('origin_invalid') from None


def validate_plan(plan):
    require(isinstance(plan,dict),'plan_invalid')
    allowed={'schema','identity','network','origins','acme','approvals','host','credentials'}
    require(set(plan)==allowed and plan['schema']=='professor-direct-ingress-plan-v1','plan_fields_invalid')
    p=deepcopy(plan)
    fields={'identity':{'kind','name','control_verified','dns_addresses'},
        'origins':{'production','previews','development'},'acme':{'client','version','staging_passed','production_chain_verified','renewal_tested'},
        'approvals':{'host_change','firewall','router','dns'},'host':{'port443_free','effective_firewall_reviewed','runtime_safe','runtime_tls_recovery_verified','boot_plan_reviewed'},
        'credentials':{'current_local_profile_on_server','remote_stores_audited'}}
    for k,names in fields.items():require(isinstance(p[k],dict) and set(p[k])==names,'plan_fields_invalid')
    for group,names in {'identity':['control_verified'],'approvals':list(fields['approvals']),
        'acme':['staging_passed','production_chain_verified','renewal_tested'],'host':list(fields['host']),'credentials':list(fields['credentials'])}.items():
        require(all(type(p[group][k]) is bool for k in names),'boolean_required')
    i=p['identity'];require(i['kind'] in {'domain','public_ipv4',None},'identity_kind_invalid')
    if i['name'] is not None:
        if i['kind']=='domain':hostname(i['name'])
        else:require(i['kind']=='public_ipv4' and address(i['name'],4).is_global,'public_ip_identity_invalid')
    require(isinstance(i['dns_addresses'],list) and len(i['dns_addresses'])<=16,'dns_metadata_invalid')
    for a in i['dns_addresses']:address(a)
    n=p['network'];require(isinstance(n,dict) and set(n)<={'lan_ipv4','gateway','interface','public_ipv4_observations','router_wan_ipv4','global_ipv6','ipv6_default_route','outside_lan_inbound_confirmed','external_probe_source','external_probe_target','external_probe_port','external_probe_on_professor','external_probe_tls_trusted','external_probe_health_passed','external_probe_utc'},'network_fields_invalid')
    address(n.get('lan_ipv4'),4);address(n.get('gateway'),4)
    require(re.fullmatch(r'[a-zA-Z0-9_.:-]{1,32}',n.get('interface','')),'interface_invalid')
    for key in ('ipv6_default_route','outside_lan_inbound_confirmed'):require(type(n.get(key)) is bool,'boolean_required')
    network=classify_network(n)
    if n.get('outside_lan_inbound_confirmed'):
        require(n.get('external_probe_source') and n.get('external_probe_target')==i['name'],'external_target_not_bound_to_plan')
    require(p['origins']['production']==PRODUCTION_ORIGIN,'production_frontend_authority_unreviewed')
    origin(p['origins']['production'])
    for group in ('previews','development'):
        require(isinstance(p['origins'][group],list) and len(p['origins'][group])<=8,'origin_list_invalid')
        for value in p['origins'][group]:
            origin(value,development=group=='development')
            if group=='previews':require(urlsplit(value).hostname.endswith('.vercel.app'),'preview_origin_unreviewed')
    combined=[p['origins']['production'],*p['origins']['previews'],*p['origins']['development']]
    require(len(set(combined))==len(combined),'duplicate_origin')
    require(p['acme']['client'] in {'certbot',None},'acme_client_unreviewed')
    if p['acme']['version'] is not None:require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',p['acme']['version']),'acme_version_invalid')
    return p


def readiness(plan):
    p=validate_plan(plan);n=classify_network(p['network']);blockers=[]
    i=p['identity'];a=p['acme'];h=p['host']
    if not i['name'] or not i['control_verified']:blockers.append('identity_not_verified')
    if n['cgnat']=='YES':blockers.append('CGNAT_BLOCKED')
    if n['nat_assessment']!='PUBLIC_WAN_MATCHES_EGRESS':blockers.append('wan_control_unknown')
    if n['inbound_reachability']!='CONFIRMED':blockers.append('outside_lan_inbound_pending')
    if i['kind']=='domain' and n['observed_public_ipv4'] not in i['dns_addresses']:blockers.append('dns_not_verified')
    if any(address(v).version==4 and v!=n['observed_public_ipv4'] for v in i['dns_addresses']):blockers.append('dns_address_not_controlled')
    if any(address(v).version==6 for v in i['dns_addresses']):blockers.append('ipv6_ingress_not_admitted')
    if i['kind']=='public_ipv4' and i['name']!=n['observed_public_ipv4']:blockers.append('public_ip_not_controlled')
    version=tuple(map(int,a['version'].split('.'))) if a['version'] else ()
    if a['client']!='certbot' or not version:blockers.append('acme_tooling_unverified')
    if i['kind']=='public_ipv4' and version<(5,4,0):blockers.append('ip_certificate_client_unsupported')
    for key,reason in [('staging_passed','acme_staging_not_verified'),('production_chain_verified','production_tls_unverified'),('renewal_tested','renewal_unverified')]:
        if not a[key]:blockers.append(reason)
    for key,reason in [('port443_free','port443_conflict'),('effective_firewall_reviewed','firewall_not_reviewed'),('runtime_safe','runtime_boundaries_unverified'),('runtime_tls_recovery_verified','reboot_tls_recovery_unverified'),('boot_plan_reviewed','boot_plan_not_reviewed')]:
        if not h[key]:blockers.append(reason)
    for key,value in p['approvals'].items():
        if not value:blockers.append(key+'_approval_missing')
    if not p['credentials']['current_local_profile_on_server']:blockers.append('current_profile_credentials_unverified')
    return {'ready_for_operator_apply':False,'configuration_prerequisites_pass':not blockers,
        'blockers':[*blockers,'controlled_apply_not_released'],'network':n,
        'production_ready':False,'cloud_retirement_allowed':False,
        'remote_credential_inventory_complete':p['credentials']['remote_stores_audited'],
        'actual_apply_implemented':False,'operator_command':None}


def _identity(plan):
    p=validate_plan(plan);require(p['identity']['name'] and p['identity']['control_verified'],'identity_not_verified')
    return p,p['identity']['name']


def render_http_challenge(plan):
    p,name=_identity(plan)
    escaped=re.escape(name).replace('\\.','[.]')
    return '''# Named HTTP-01 site for EXISTING host nginx; keep default80 unchanged.
server {
    listen 80;
    server_name '''+name+''';
    access_log off;
    error_log /dev/null crit;
    autoindex off;
    if ($http_host !~* "^'''+escaped+'''(?::80)?$") { return 444; }
    location ~ ^/[.]well-known/acme-challenge/[A-Za-z0-9_-]+$ {
        root /var/lib/proptech-acme;
        default_type text/plain;
        try_files $uri =404;
        limit_except GET HEAD { deny all; }
    }
    location / { return 308 https://'''+name+'''$request_uri; }
}
'''


def render_edge(plan):
    p,name=_identity(plan)
    escaped=re.escape(name).replace('\\.','[.]')
    common='''    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_tickets off;
    ssl_early_data off;
    access_log off;
    error_log /dev/null crit;
'''
    default=''
    if p['identity']['kind']=='domain':
        default='server {\n    listen 443 ssl default_server;\n    ssl_reject_handshake on;\n'+common+'}\n'
    suffix=' default_server' if p['identity']['kind']=='public_ipv4' else ''
    sni='    if ($ssl_server_name != '+name+') { return 444; }\n' if p['identity']['kind']=='domain' else ''
    return '''# PREPARED ONLY. Dedicated TLS-only instance of installed nginx.
# Existing host nginx keeps80 and the separate named HTTP-01 site.
user www-data;
worker_processes 1;
pid /run/proptech-public/nginx.pid;
error_log /dev/null crit;
events { worker_connections 256; }
http {
access_log off;
client_body_temp_path /run/proptech-public/body_temp;
proxy_temp_path /run/proptech-public/proxy_temp;
fastcgi_temp_path /run/proptech-public/fastcgi_temp;
uwsgi_temp_path /run/proptech-public/uwsgi_temp;
scgi_temp_path /run/proptech-public/scgi_temp;
limit_req_zone $binary_remote_addr zone=proptech_edge_rate:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=proptech_edge_connections:10m;
'''+default+'''server {
    listen 443 ssl'''+suffix+''';
    server_name '''+name+''';
'''+common+'''    ssl_certificate /etc/proptech-selfhost/acme/live/professor-api/fullchain.pem;
    ssl_certificate_key /etc/proptech-selfhost/acme/live/professor-api/privkey.pem;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    if ($http_host !~* "^'''+escaped+'''(?::443)?$") { return 444; }
'''+sni+'''    server_tokens off;
    autoindex off;
    client_max_body_size 1m;
    client_header_timeout 10s;
    client_body_timeout 15s;
    send_timeout 30s;
    keepalive_timeout 15s;
    large_client_header_buffers 4 32k;
    limit_req zone=proptech_edge_rate burst=20 nodelay;
    limit_req_status 429;
    limit_conn proptech_edge_connections 20;
    limit_conn_status 429;
    location ~* ^/(admin|v1/admin|internal|ops|metrics|docs|redoc|openapi[.]json|pilot/admin|pilot/reviewer|professional-review)(/|$) { return 404; }
    location ~* ^/(market-insights/ops|commute/refresh)(/|$) { return 404; }
    location = /market-insights/refresh { return 404; }
    location ~* ^/market-insights/coverage/(bootstrap|reconcile|audit)(/|$) { return 404; }
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host '''+name+''';
        proxy_set_header X-Forwarded-Host '''+name+''';
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Forwarded "";
        proxy_connect_timeout 3s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
        proxy_buffering off;
        proxy_cache off;
        proxy_next_upstream off;
        proxy_hide_header Server;
        proxy_redirect http://'''+name+'''/ https://'''+name+'''/;
    }
}
}
'''


def render_inner_proxy():
    return '''# PREPARED replacement, not installed. Existing port8080 stays loopback.
worker_processes 1;
pid /tmp/nginx.pid;
error_log /dev/null crit;
events { worker_connections 256; }
http {
    access_log off;
    server_tokens off;
    client_body_temp_path /tmp/client_temp;
    proxy_temp_path /tmp/proxy_temp;
    fastcgi_temp_path /tmp/fastcgi_temp;
    uwsgi_temp_path /tmp/uwsgi_temp;
    scgi_temp_path /tmp/scgi_temp;
    client_max_body_size 1m;
    client_header_timeout 10s;
    client_body_timeout 15s;
    large_client_header_buffers 4 32k;
    keepalive_timeout 15s;
    server {
        listen 8080;
        server_name _;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For "";
        proxy_set_header X-Real-IP "";
        proxy_set_header X-Forwarded-Proto "";
        proxy_set_header Forwarded "";
        proxy_connect_timeout 3s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
        proxy_next_upstream off;
        location = /valuation/ml/v1/status {
            limit_except GET OPTIONS { deny all; }
            proxy_pass http://unix:/run/proptech-ml/inference.sock:;
        }
        location = /valuation/ml/v1/estimate {
            limit_except POST OPTIONS { deny all; }
            proxy_pass http://unix:/run/proptech-ml/inference.sock:;
        }
        location /valuation/ml/ { return 404; }
        location / { proxy_pass http://api:8080; }
    }
}
'''


def certificate_command(plan,*,staging):
    p,name=_identity(plan);a=p['acme'];require(a['client']=='certbot' and a['version'],'acme_tooling_unverified')
    if p['identity']['kind']=='public_ipv4':require(tuple(map(int,a['version'].split('.')))>=(5,4,0),'ip_certificate_client_unsupported')
    base='/etc/proptech-selfhost/acme'+('-staging' if staging else '')
    args=['certbot','--config','/dev/null','certonly','--quiet','--non-interactive','--agree-tos','--register-unsafely-without-email',
        '--server','https://acme-'+('staging-' if staging else '')+'v02.api.letsencrypt.org/directory',
        '--webroot','--webroot-path','/var/lib/proptech-acme','--cert-name','professor-api',
        '--config-dir',base,'--work-dir','/var/lib/proptech-acme-client'+('-staging' if staging else ''),
        '--logs-dir','/var/log/proptech-acme'+('-staging' if staging else '')]
    if staging:args+=['--staging']
    if p['identity']['kind']=='public_ipv4':args+=['--required-profile','shortlived','--ip-address',name]
    else:args+=['--domain',name]
    return args


def render_units(plan):
    p,name=_identity(plan)
    verify='-verify_ip '+name if p['identity']['kind']=='public_ipv4' else '-verify_hostname '+name
    validate='''#!/bin/bash
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin
test "$(id -u)" = 0
cert=/etc/proptech-selfhost/acme/live/professor-api/cert.pem
chain=/etc/proptech-selfhost/acme/live/professor-api/chain.pem
openssl verify -CApath /etc/ssl/certs -untrusted "$chain" '''+verify+''' "$cert" >/dev/null 2>&1
openssl x509 -in "$cert" -noout -checkend 86400 >/dev/null 2>&1
nginx -t -c /etc/proptech-selfhost/public-nginx/nginx.conf >/dev/null 2>&1
'''
    reload='''#!/bin/bash
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin
if systemctl is-active --quiet proptech-public-ingress; then
    /usr/local/libexec/proptech-public-validate
    systemctl reload proptech-public-ingress
else
    systemctl start proptech-public-ingress
fi
'''
    units={'proptech-public-reload':reload,'proptech-public-validate':validate,
        'proptech-public-ingress.service':'''[Unit]
Description=Direct Professor TLS edge (installed nginx, separate from existing80)
After=network-online.target docker.service proptech-ml.socket
Wants=network-online.target
[Service]
Type=simple
User=root
Group=www-data
RuntimeDirectory=proptech-public
RuntimeDirectoryMode=0750
ExecStartPre=/usr/local/libexec/proptech-public-validate
ExecStart=/usr/sbin/nginx -c /etc/proptech-selfhost/public-nginx/nginx.conf -g "daemon off;"
ExecReload=/usr/local/libexec/proptech-public-validate
ExecReload=/usr/sbin/nginx -c /etc/proptech-selfhost/public-nginx/nginx.conf -s reload
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/run/proptech-public
CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_SETUID CAP_SETGID CAP_CHOWN CAP_KILL
MemoryMax=128M
CPUQuota=50%
TasksMax=32
UMask=0077
StandardOutput=null
StandardError=null
[Install]
WantedBy=multi-user.target
''',
        'proptech-acme-renew.service':'''[Unit]
Description=Renew Professor public TLS certificate
After=network-online.target
Wants=network-online.target
ConditionPathExists=/etc/proptech-selfhost/acme/renewal/professor-api.conf
[Service]
Type=oneshot
User=root
UMask=0077
ExecStart=/usr/bin/certbot --config /dev/null renew --quiet --non-interactive --server https://acme-v02.api.letsencrypt.org/directory --cert-name professor-api --config-dir /etc/proptech-selfhost/acme --work-dir /var/lib/proptech-acme-client --logs-dir /var/log/proptech-acme --deploy-hook /usr/local/libexec/proptech-public-reload
TimeoutStartSec=300
''',
        'proptech-acme-renew.timer':'''[Unit]
Description=Check Professor certificate renewal twice daily
[Timer]
OnBootSec=5min
OnUnitActiveSec=12h
RandomizedDelaySec=15min
Persistent=true
[Install]
WantedBy=timers.target
''',
        'proptech-ml.socket':'''[Unit]
Description=Private Professor ML listeners
[Socket]
ListenStream=127.0.0.1:8081
ListenStream=/run/proptech-ml/inference.sock
Accept=no
SocketMode=0660
SocketUser=andy
SocketGroup=101
DirectoryMode=0755
RemoveOnStop=true
[Install]
WantedBy=sockets.target
''',
        'proptech-ml.service':'''[Unit]
Description=Professor observational ML companion
Requires=proptech-ml.socket
After=proptech-ml.socket local-fs.target
[Service]
User=andy
Group=andy
WorkingDirectory=/opt/proptech-selfhost/ml
EnvironmentFile=/etc/proptech-selfhost/ml-runtime.env
ExecStart=/home/andy/proptech-ai-copilot/.venv/bin/python -B /opt/proptech-selfhost/ml/scripts/ops/serve_valuation_ml.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=tmpfs
BindReadOnlyPaths=/home/andy/proptech-ai-copilot/.venv /home/andy/proptech-ai-copilot/.local/python /home/andy/proptech-model-artifacts
PrivateTmp=true
RestrictSUIDSGID=true
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET
MemoryMax=2G
CPUQuota=100%
TasksMax=32
UMask=0077
StandardOutput=null
StandardError=null
'''}
    units['proptech-public-health']='''#!/usr/bin/python3 -I
import json,socket,ssl
from urllib.request import build_opener,ProxyHandler
checks={}
try:
 context=ssl.create_default_context()
 with socket.create_connection(('127.0.0.1',443),timeout=3) as raw:
  with context.wrap_socket(raw,server_hostname='''+repr(name)+''') as encrypted:
   certificate=encrypted.getpeercert()
   import time
   assert ssl.cert_time_to_seconds(certificate['notAfter'])-time.time()>86400
 checks['trusted_local_tls']=True
except Exception:checks['trusted_local_tls']=False
opener=build_opener(ProxyHandler({}))
for path,expected in [('/health','ok'),('/readiness','ready'),('/valuation/ml/v1/status','available')]:
 try:
  with opener.open('http://127.0.0.1:8080'+path,timeout=3) as response:
   body=response.read(65537)
   assert len(body)<=65536
   value=json.loads(body)
   assert value['status']==expected
   if path.endswith('/status'):assert value['is_actionable'] is False
  checks[path]=True
 except Exception:checks[path]=False
passed=all(checks.values())
print(json.dumps({'status':'PASS' if passed else 'DEGRADED','checks':checks,'outside_lan_acceptance':False}))
raise SystemExit(0 if passed else 1)
'''
    units['proptech-public-health.service']='''[Unit]
Description=Value-free local Professor ingress monitoring
After=proptech-public-ingress.service
[Service]
Type=oneshot
User=nobody
Group=nogroup
ExecStart=/usr/local/libexec/proptech-public-health
TimeoutStartSec=20
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
MemoryMax=96M
StandardOutput=journal
StandardError=null
'''
    units['proptech-public-health.timer']='''[Unit]
Description=Monitor Professor TLS and local backend contracts
[Timer]
OnBootSec=60s
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
'''
    return units


def firewall_plan(plan):
    p=validate_plan(plan)
    return {'public_tcp_ports':[80,443],'interface':p['network']['interface'],
        'forward_to_lan_ipv4':p['network']['lan_ipv4'],'port80_reason':'HTTP-01 issuance AND every renewal; challenge/redirect only',
        'never_forward':[5432,8080,8081,2375,2376,22,3322],
        'preserve_remote_administration':True,'requires_effective_rule_review':True,
        'no_ufw_reset_or_flush':True,'docker_published_ports_require_independent_check':True,
        'ipv6_public_rules_admitted':False,'apply_performed':False}


def validate_compose_delta(before,after,plan):
    """Only two nonsecret API settings and two inner-proxy binds may change."""
    p,name=_identity(plan)
    require(before.get('name')==after.get('name')=='proptech-selfhost','compose_project_unreviewed')
    require({k:v for k,v in before.items() if k!='services'}=={k:v for k,v in after.items() if k!='services'},'compose_global_changed')
    require(set(before['services'])==set(after['services']),'compose_services_changed')
    for key in set(before['services'])-{'api','reverse_proxy'}:
        require(before['services'][key]==after['services'][key],'non_consumer_service_changed')
    for key in ('postgres_app','postgres_usage'):
        require(not after['services'][key].get('ports') and after['services'][key].get('network_mode')!='host','postgres_public')
    old,new=before['services']['api'],after['services']['api']
    require({k:v for k,v in old.items() if k!='environment'}=={k:v for k,v in new.items() if k!='environment'},'api_image_secret_or_infrastructure_changed')
    mutable={'API_ALLOWED_HOSTS','CORS_ALLOWED_ORIGINS'}
    old_env,new_env=old['environment'],new['environment']
    require({k:v for k,v in old_env.items() if k not in mutable}=={k:v for k,v in new_env.items() if k not in mutable},'unexpected_environment_change')
    old_hosts={x.strip().lower() for x in old_env.get('API_ALLOWED_HOSTS','').split(',') if x.strip()}
    new_hosts={x.strip().lower() for x in new_env.get('API_ALLOWED_HOSTS','').split(',') if x.strip()}
    require(new_hosts==old_hosts|{name} and '*' not in new_hosts,'api_host_delta_invalid')
    origins=[p['origins']['production'],*p['origins']['previews'],*p['origins']['development']]
    require(new_env.get('CORS_ALLOWED_ORIGINS')==','.join(origins),'cors_delta_invalid')
    old,new=before['services']['reverse_proxy'],after['services']['reverse_proxy']
    require({k:v for k,v in old.items() if k!='volumes'}=={k:v for k,v in new.items() if k!='volumes'},'proxy_infrastructure_changed')
    ports=new.get('ports',[])
    require(len(ports)==1 and ports[0].get('host_ip')=='127.0.0.1' and str(ports[0].get('published'))=='8080','proxy_not_loopback')
    old_mounts=old.get('volumes',[])
    require(len([m for m in old_mounts if m.get('target')=='/etc/nginx/nginx.conf' and m.get('type')=='bind'])==1,'original_proxy_config_missing')
    wanted=[deepcopy(m) for m in old_mounts if m['target']!='/etc/nginx/nginx.conf']
    wanted.extend([{'type':'bind','source':'/etc/proptech-selfhost/public-inner-nginx.conf','target':'/etc/nginx/nginx.conf','read_only':True},
        {'type':'bind','source':'/run/proptech-ml','target':'/run/proptech-ml','read_only':True}])
    actual=deepcopy(new.get('volumes',[]))
    for mount in actual:
        if mount.get('target') in {'/etc/nginx/nginx.conf','/run/proptech-ml'}:
            bind=mount.pop('bind',{})
            require(set(bind)<={'create_host_path'} and bind.get('create_host_path',False) is False,'automatic_bind_creation_forbidden')
    require(sorted(actual,key=lambda m:m['target'])==sorted(wanted,key=lambda m:m['target']),'unexpected_proxy_mount')
    return {'status':'PASS','recreate_only':['api','reverse_proxy'],'database_volumes_changed':False,'public_ports_added_to_compose':False}
