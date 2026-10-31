"""Pure operator-visible WAN checklist. No router, firewall or DNS access."""
from __future__ import annotations

from services.professor_ingress import address,classify_network,require


def conditional_https_plan(observation):
    required={'schema','router_wan_ipv4','professor_lan_ipv4','default_gateway','observed_public_ipv4',
        'router_behind_router_or_modem','dhcp_reservation_exists','inbound_forwarding_authority_confirmed'}
    require(isinstance(observation,dict) and set(observation)==required,'router_fields_invalid')
    require(observation['schema']=='professor-router-observation-v1','router_schema_invalid')
    require(observation['professor_lan_ipv4']=='192.168.200.215' and observation['default_gateway']=='192.168.200.1','router_lan_drift_requires_review')
    public=address(observation['observed_public_ipv4'],4);require(public.is_global,'router_public_observation_invalid')
    for key in ('router_behind_router_or_modem','dhcp_reservation_exists','inbound_forwarding_authority_confirmed'):
        require(observation[key] is None or type(observation[key]) is bool,'router_boolean_invalid')
    wan=observation['router_wan_ipv4']
    if wan is not None:address(wan,4)
    classified=classify_network({'public_ipv4_observations':[str(public),str(public)],'router_wan_ipv4':wan})
    missing=[key for key in ('router_wan_ipv4','router_behind_router_or_modem','dhcp_reservation_exists','inbound_forwarding_authority_confirmed') if observation[key] is None]
    conditional=[]
    if classified['nat_assessment']=='PUBLIC_WAN_MATCHES_EGRESS':
        conditional=[{'protocol':'TCP','public_port':443,'target_ipv4':'192.168.200.215','target_port':443},
            {'protocol':'TCP','public_port':80,'target_ipv4':'192.168.200.215','target_port':80,'only_if':'selected ACME HTTP-01 issuance and renewal/redirect'}]
    return {'schema':'professor-conditional-https-plan-v1',**classified,'router_evidence_complete':not missing,
        'required_operator_values':missing,'decision_logic_ready':True,'wan_equals_observed_public_ipv4':None if wan is None else wan==str(public),
        'upstream_router_reported':observation['router_behind_router_or_modem'],
        'dhcp_reservation_confirmed':observation['dhcp_reservation_exists'] is True,
        'forwarding_authority_confirmed':observation['inbound_forwarding_authority_confirmed'] is True,
        'conditional_forwarding':conditional,'apply_prerequisites':['operator network authority approval','stable LAN reservation',
            'exact trusted HTTPS identity and renewal','effective firewall review','reviewed controlled installer','outside-LAN acceptance after activation'],
        'self_hosted_compatible_unblock_options':['ISP public IPv4','ISP static IPv4','separately approved routable/firewallable IPv6'],
        'path':['Internet TCP443','approved router forwarding','192.168.200.215:443','NGINX TLS edge','127.0.0.1:8080'],
        'private_only':[5432,8080,8081,2375,2376],'external_tunnel_allowed':False,
        'ingress_apply_allowed':False,'operator_command':None,'router_changes_performed':False}
