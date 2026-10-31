"""Pure plan tests; no router, firewall, certificate order or live changes."""
import copy
import importlib
import json
from pathlib import Path
import subprocess
from datetime import datetime,timezone

import pytest


@pytest.fixture
def api():
    try:return importlib.import_module('services.professor_ingress')
    except ImportError:pytest.fail('Stage5 direct-ingress validators are not implemented')


def network(wan=None):
    return {'lan_ipv4':'192.168.200.215','gateway':'192.168.200.1','interface':'enp2s0',
        'public_ipv4_observations':['140.119.55.43','140.119.55.43'],
        'router_wan_ipv4':wan,'global_ipv6':[],'ipv6_default_route':False,
        'outside_lan_inbound_confirmed':False}


def plan():
    return {'schema':'professor-direct-ingress-plan-v1',
        'identity':{'kind':'domain','name':'api.example.com','control_verified':True,'dns_addresses':['140.119.55.43']},
        'network':network('140.119.55.43'),
        'origins':{'production':'https://proptech-ai-copilot.vercel.app','previews':[], 'development':[]},
        'acme':{'client':'certbot','version':'5.9.0','staging_passed':True,'production_chain_verified':True,'renewal_tested':True},
        'approvals':{'host_change':True,'firewall':True,'router':True,'dns':True},
        'host':{'port443_free':True,'effective_firewall_reviewed':True,'runtime_safe':True,'runtime_tls_recovery_verified':True,'boot_plan_reviewed':True},
        'credentials':{'current_local_profile_on_server':True,'remote_stores_audited':False}}


def test_observed_egress_is_not_inbound_or_cgnat_proof(api):
    result=api.classify_network(network())
    assert result['public_ipv4']=='YES' and result['public_ip_status']=='PUBLIC_IP_OBSERVED'
    assert result['inbound_reachability']=='PENDING' and result['cgnat']=='UNKNOWN'
    assert result['public_ipv6']=='NO'


@pytest.mark.parametrize('wan,cgnat,nat',[
    ('100.64.10.2','YES','CGNAT_BLOCKED'),('10.0.0.2','UNKNOWN','UPSTREAM_PRIVATE_NAT'),
    ('140.119.55.43','NO','PUBLIC_WAN_MATCHES_EGRESS'),('8.8.8.8','UNKNOWN','WAN_EGRESS_MISMATCH')])
def test_wan_classification_requires_actual_router_metadata(api,wan,cgnat,nat):
    result=api.classify_network(network(wan));assert result['cgnat']==cgnat and result['nat_assessment']==nat


def test_disagreeing_or_non_global_observations_remain_unknown(api):
    data=network();data['public_ipv4_observations']=['140.119.55.43','8.8.8.8']
    assert api.classify_network(data)['public_ipv4']=='UNKNOWN'
    data['public_ipv4_observations']=['192.168.1.1'];assert api.classify_network(data)['public_ipv4']=='NO'


def test_ipv6_requires_global_address_and_route(api):
    data=network();data['global_ipv6']=['fe80::1234'];data['ipv6_default_route']=True
    assert api.classify_network(data)['public_ipv6']=='NO'
    data['global_ipv6']=['2606:4700:4700::1111']
    assert api.classify_network(data)['public_ipv6']=='YES'
    assert api.classify_network(data)['inbound_reachability']=='PENDING'


def test_missing_facts_do_not_release_apply_or_retirement(api):
    data=plan();data['identity']['name']=None;data['identity']['control_verified']=False
    data['network']['router_wan_ipv4']=None
    data['acme']['version']=None;data['host']['effective_firewall_reviewed']=False
    result=api.readiness(data)
    assert result['ready_for_operator_apply'] is False and result['cloud_retirement_allowed'] is False
    assert {'identity_not_verified','wan_control_unknown','acme_tooling_unverified','firewall_not_reviewed'}<=set(result['blockers'])


@pytest.mark.parametrize('name',['*','api.example.com; include x;','api.example.com\nserver{}','http://example.com','example.com:443','a/b','127.0.0.1'])
def test_identity_injection_and_private_ip_rejected(api,name):
    data=plan();data['identity']['name']=name
    with pytest.raises(ValueError):api.validate_plan(data)


@pytest.mark.parametrize('origin',['*','https://*.vercel.app','https://user:pass@example.com','https://example.com/path','http://example.com'])
def test_browser_origins_fail_closed(api,origin):
    data=plan();data['origins']['production']=origin
    with pytest.raises(ValueError):api.validate_plan(data)


def test_unknown_fields_and_boolean_strings_are_refused(api):
    data=plan();data['upstream']='http://0.0.0.0:8080'
    with pytest.raises(ValueError):api.validate_plan(data)
    data=plan();data['approvals']['host_change']='true'
    with pytest.raises(ValueError):api.validate_plan(data)


def test_ip_certificate_needs_supported_client_and_control(api):
    data=plan();data['identity'].update(kind='public_ipv4',name='140.119.55.43',dns_addresses=[])
    data['acme']['version']='5.3.0'
    assert 'ip_certificate_client_unsupported' in api.readiness(data)['blockers']
    data['acme']['version']='5.4.0'
    command=api.certificate_command(data,staging=True)
    assert '--ip-address' in command and '--required-profile' in command and 'shortlived' in command and '--staging' in command
    assert '--preferred-profile' not in command
    assert '--config' in command and '/dev/null' in command and 'https://acme-staging-v02.api.letsencrypt.org/directory' in command
    assert '--standalone' not in command and '--nginx' not in command


def test_edge_uses_only_loopback8080_and_preserves_inner_boundary(api):
    data=api.validate_plan(plan());text=api.render_edge(data)
    assert 'proxy_pass http://127.0.0.1:8080;' in text and ':8081' not in text
    assert 'ssl_protocols TLSv1.2 TLSv1.3;' in text and 'ssl_reject_handshake on;' in text
    assert 'access_log off;' in text and 'error_log /dev/null crit;' in text
    assert '$http_authorization' not in text and '$http_x_forwarded_for' not in text
    assert 'proxy_set_header Host api.example.com;' in text
    assert 'proxy_set_header X-Forwarded-For $remote_addr;' in text
    assert 'Access-Control-Allow-Origin' not in text and 'client_max_body_size 1m;' in text
    assert 'market-insights/ops' in text and '/admin' in text
    inner=api.render_inner_proxy()
    assert 'unix:/run/proptech-ml/inference.sock' in inner and 'proxy_set_header X-Forwarded-For "";' in inner
    assert '/valuation/ml/v1/status' in inner and '/valuation/ml/v1/estimate' in inner


def test_certificates_staging_and_production_are_separate(api):
    p=plan();stage=api.certificate_command(p,staging=True);prod=api.certificate_command(p,staging=False)
    assert '--staging' in stage and '--staging' not in prod
    assert '/etc/proptech-selfhost/acme-staging' in stage and '/etc/proptech-selfhost/acme' in prod
    assert '--quiet' in stage and '--webroot' in stage
    units=api.render_units(p)
    assert '12h' in units['proptech-acme-renew.timer'] and 'Persistent=true' in units['proptech-acme-renew.timer']
    assert 'proptech-public-validate' in units['proptech-public-reload'] and 'systemctl reload proptech-public-ingress' in units['proptech-public-reload']
    assert 'openssl verify' in units['proptech-public-validate']


def test_expired_public_cert_cannot_disable_http01_or_start_public_tls(api):
    edge=api.render_edge(plan());http=api.render_http_challenge(plan());units=api.render_units(plan())
    assert 'listen 80;' not in edge and 'listen 80;' in http
    assert 'ssl_certificate' not in http
    assert 'ExecStartPre=/usr/local/libexec/proptech-public-validate' in units['proptech-public-ingress.service']
    assert 'checkend 86400' in units['proptech-public-validate']
    assert 'PrivateTmp=true' in units['proptech-public-ingress.service']
    assert 'public-nginx/nginx.conf' in units['proptech-public-ingress.service']


def test_valid_configuration_still_cannot_claim_unreleased_host_apply(api):
    p=plan();p['network'].update(outside_lan_inbound_confirmed=True,external_probe_source='1.1.1.1')
    p['network'].update(external_probe_target='api.example.com',external_probe_port=443,
        external_probe_on_professor=False,external_probe_tls_trusted=True,external_probe_health_passed=True,
        external_probe_utc=datetime.now(timezone.utc).isoformat())
    result=api.readiness(p)
    assert result['configuration_prerequisites_pass'] is True
    assert result['ready_for_operator_apply'] is False and result['operator_command'] is None


def test_bare_boolean_or_wrong_target_never_becomes_external_acceptance(api):
    p=plan();p['network'].update(outside_lan_inbound_confirmed=True,external_probe_source='1.1.1.1')
    with pytest.raises(ValueError):api.validate_plan(p)
    p['network'].update(external_probe_target='unrelated.example.com',external_probe_port=443,
        external_probe_on_professor=False,external_probe_tls_trusted=True,external_probe_health_passed=True,
        external_probe_utc=datetime.now(timezone.utc).isoformat())
    with pytest.raises(ValueError):api.validate_plan(p)


def test_unroutable_or_foreign_dns_addresses_are_not_admitted(api):
    p=plan();p['identity']['dns_addresses'].append('8.8.8.8')
    assert 'dns_address_not_controlled' in api.readiness(p)['blockers']
    p=plan();p['identity']['dns_addresses'].append('2606:4700:4700::1111')
    assert 'ipv6_ingress_not_admitted' in api.readiness(p)['blockers']


def test_ml_lifecycle_is_private_and_has_no_database_or_secrets(api):
    units=api.render_units(plan())
    socket=units['proptech-ml.socket'];service=units['proptech-ml.service']
    assert 'ListenStream=127.0.0.1:8081' in socket and 'ListenStream=/run/proptech-ml/inference.sock' in socket
    assert 'SocketMode=0660' in socket and 'SocketGroup=101' in socket
    assert 'User=andy' in service and 'NoNewPrivileges=true' in service and 'Restart=on-failure' in service
    assert 'DATABASE_URL' not in service and 'secret' not in service.lower()


def test_readonly_inner_proxy_uses_only_writable_temporary_paths(api):
    inner=api.render_inner_proxy()
    edge=api.render_edge(plan())
    for name in ('client_body','proxy','fastcgi','uwsgi','scgi'):
        assert name+'_temp_path /tmp/' in inner
        assert name+'_temp_path /run/proptech-public/' in edge


def test_inner_ml_routes_admit_browser_preflight_but_not_other_methods(api):
    inner=api.render_inner_proxy()
    assert 'limit_except GET OPTIONS { deny all; }' in inner
    assert 'limit_except POST OPTIONS { deny all; }' in inner


def test_nginx_master_can_signal_different_uid_workers_on_reload(api):
    service=api.render_units(plan())['proptech-public-ingress.service']
    capabilities=next(line.partition('=')[2].split() for line in service.splitlines() if line.startswith('CapabilityBoundingSet='))
    assert 'CAP_KILL' in capabilities


def test_health_monitor_is_sanitized_and_not_external_acceptance(api):
    units=api.render_units(plan())
    assert 'proptech-public-health' in units
    monitor=units['proptech-public-health']
    assert 'create_default_context' in monitor and '127.0.0.1' in monitor
    assert 'outside_lan_acceptance' in monitor and 'False' in monitor
    assert 'except Exception' in monitor and 'print(exc' not in monitor
    assert 'OnUnitActiveSec=5min' in units['proptech-public-health.timer']


def test_firewall_never_resets_or_opens_internal_or_admin_ports(api):
    result=api.firewall_plan(plan())
    assert result['public_tcp_ports']==[80,443] and result['preserve_remote_administration'] is True
    assert set(result['never_forward']) >= {5432,8080,8081,2375,2376,3322}
    assert result['apply_performed'] is False and result['requires_effective_rule_review'] is True


def test_outside_lan_evidence_cannot_be_claimed_from_localhost(api):
    data=plan();data['network']['outside_lan_inbound_confirmed']=True
    data['network']['external_probe_source']='192.168.200.215'
    with pytest.raises(ValueError):api.validate_plan(data)


def merge_models():
    from tests.test_professor_stage2_activation import models
    _,before=models();before['name']='proptech-selfhost'
    before['services']['api']['environment'].update(API_ALLOWED_HOSTS='localhost,127.0.0.1',CORS_ALLOWED_ORIGINS='http://localhost:3000')
    before['services']['reverse_proxy']['volumes']=[{'type':'bind','source':'/original/nginx.conf','target':'/etc/nginx/nginx.conf','read_only':True}]
    after=copy.deepcopy(before)
    after['services']['api']['environment'].update(API_ALLOWED_HOSTS='localhost,127.0.0.1,api.example.com',CORS_ALLOWED_ORIGINS='https://proptech-ai-copilot.vercel.app')
    after['services']['reverse_proxy']['volumes']=[
        {'type':'bind','source':'/etc/proptech-selfhost/public-inner-nginx.conf','target':'/etc/nginx/nginx.conf','read_only':True,'bind':{'create_host_path':False}},
        {'type':'bind','source':'/run/proptech-ml','target':'/run/proptech-ml','read_only':True,'bind':{'create_host_path':False}}]
    return before,after


def test_compose_merge_changes_only_exact_consumer_fields(api):
    before,after=merge_models()
    assert hasattr(api,'validate_compose_delta'),'actual merge guard missing'
    assert api.validate_compose_delta(before,after,plan())['recreate_only']==['api','reverse_proxy']


@pytest.mark.parametrize('mutation',['db','image','port','secret','paid','socket_write','auto_create','origin','project'])
def test_compose_guard_rejects_unsafe_or_unrelated_changes(api,mutation):
    before,after=merge_models()
    if mutation=='db':after['services']['postgres_app']['image']='postgres:latest'
    if mutation=='image':after['services']['api']['image']='unreviewed:latest'
    if mutation=='port':after['services']['reverse_proxy']['ports'][0]['host_ip']='0.0.0.0'
    if mutation=='secret':after['services']['api']['secrets'].append({'source':'app_admin_password'})
    if mutation=='paid':after['services']['api']['environment']['ANTI_ABUSE_PLACES_DISABLED']='false'
    if mutation=='socket_write':after['services']['reverse_proxy']['volumes'][-1]['read_only']=False
    if mutation=='auto_create':after['services']['reverse_proxy']['volumes'][-1]['bind']['create_host_path']=True
    if mutation=='origin':after['services']['api']['environment']['CORS_ALLOWED_ORIGINS']='*'
    if mutation=='project':
        before['name']='other';after['name']='other'
    with pytest.raises(ValueError):api.validate_compose_delta(before,after,plan())


def test_real_compose_merge_of_prepared_overlay(api,tmp_path):
    import os
    before,_=merge_models();existing=tmp_path/'existing.json';existing.write_text(json.dumps(before))
    override=Path(__file__).resolve().parents[1]/'infra/selfhost/professor-public-ingress.override.yml'
    cmd=['docker','compose','--project-name','proptech-selfhost','--project-directory',str(tmp_path),'--env-file','/dev/null','-f',str(existing)]
    env={'PATH':os.defpath,'PROFESSOR_APPROVED_API_HOSTS':'localhost,127.0.0.1,api.example.com','PROFESSOR_APPROVED_CORS_ORIGINS':'https://proptech-ai-copilot.vercel.app'}
    old=subprocess.run([*cmd,'config','--format','json'],env=env,capture_output=True,timeout=15)
    new=subprocess.run([*cmd,'-f',str(override),'config','--format','json'],env=env,capture_output=True,timeout=15)
    assert old.returncode==new.returncode==0
    assert api.validate_compose_delta(json.loads(old.stdout),json.loads(new.stdout),plan())['database_volumes_changed'] is False


def test_nginx_tls_and_inner_syntax_without_binding_ports(api,tmp_path):
    cert=tmp_path/'fixture.crt';key=tmp_path/'fixture.key'
    result=subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
        '-subj','/CN=api.example.com','-keyout',str(key),'-out',str(cert)],capture_output=True,timeout=30)
    assert result.returncode==0
    # Self-signed TEST fixture only; never used by a production trust gate.
    text=api.render_edge(plan()).replace('/etc/proptech-selfhost/acme/live/professor-api/fullchain.pem',str(cert)).replace('/etc/proptech-selfhost/acme/live/professor-api/privkey.pem',str(key)).replace('/run/proptech-public',str(tmp_path))
    # nginx -t can test-bind listeners. Use private temporary UNIX sockets only,
    # never443/8080 or another TCP listener, even during syntax verification.
    text=text.replace('listen 443 ssl','listen unix:'+str(tmp_path/'tls.sock')+' ssl')
    edge=tmp_path/'edge.conf';edge.write_text(text)
    result=subprocess.run(['nginx','-t','-p',str(tmp_path)+'/', '-c',str(edge)],capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr.decode()
    inner=tmp_path/'inner.conf';inner.write_text(api.render_inner_proxy().replace('http://api:8080','http://127.0.0.1:9').replace('/tmp/',str(tmp_path)+'/').replace('listen 8080;','listen unix:'+str(tmp_path/'inner.sock')+';'))
    result=subprocess.run(['nginx','-t','-p',str(tmp_path)+'/', '-c',str(inner)],capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr.decode()


def test_real_operator_endpoints_are_blocked_at_public_edge(api):
    text=api.render_edge(plan())
    assert 'location = /market-insights/refresh { return 404; }' in text
    assert 'coverage/(bootstrap|reconcile|audit)' in text
    assert 'professional-review' in text
