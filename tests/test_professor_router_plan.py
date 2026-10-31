"""Operator-visible router metadata only; never contact a router."""
import importlib
import pytest


def module():
    try:return importlib.import_module('services.professor_router_plan')
    except ImportError:pytest.fail('conditional router/HTTPS plan missing')


def evidence(wan=None):
    return {'schema':'professor-router-observation-v1','router_wan_ipv4':wan,
        'professor_lan_ipv4':'192.168.200.215','default_gateway':'192.168.200.1',
        'observed_public_ipv4':'140.119.55.43','router_behind_router_or_modem':None,
        'dhcp_reservation_exists':None,'inbound_forwarding_authority_confirmed':None}


def test_unfilled_template_is_a_decision_plan_not_network_proof():
    r=module().conditional_https_plan(evidence())
    assert r['cgnat']=='UNKNOWN' and r['router_evidence_complete'] is False
    assert r['decision_logic_ready'] is True and r['ingress_apply_allowed'] is False
    assert r['inbound_reachability']=='PENDING'
    assert set(r['required_operator_values'])=={'router_wan_ipv4','router_behind_router_or_modem','dhcp_reservation_exists','inbound_forwarding_authority_confirmed'}


def test_public_wan_match_remains_conditional_and_requires_external_acceptance():
    e=evidence('140.119.55.43');e.update(router_behind_router_or_modem=False,dhcp_reservation_exists=True,inbound_forwarding_authority_confirmed=True)
    r=module().conditional_https_plan(e)
    assert r['cgnat']=='NO' and r['router_evidence_complete'] is True
    assert r['wan_equals_observed_public_ipv4'] is True
    assert r['inbound_reachability']=='PENDING' and r['ingress_apply_allowed'] is False
    assert r['conditional_forwarding'][0]=={'protocol':'TCP','public_port':443,'target_ipv4':'192.168.200.215','target_port':443}
    assert r['conditional_forwarding'][1]['public_port']==80


@pytest.mark.parametrize('wan,cgnat,assessment',[('100.64.12.3','YES','CGNAT_BLOCKED'),
    ('10.0.0.2','UNKNOWN','UPSTREAM_PRIVATE_NAT'),('140.119.55.44','UNKNOWN','WAN_EGRESS_MISMATCH')])
def test_nat_and_mismatched_egress_never_admit_forwarding(wan,cgnat,assessment):
    r=module().conditional_https_plan(evidence(wan))
    assert r['cgnat']==cgnat and r['nat_assessment']==assessment
    assert r['conditional_forwarding']==[] and r['ingress_apply_allowed'] is False
    assert r['external_tunnel_allowed'] is False


@pytest.mark.parametrize('field,value',[('router_wan_ipv4','value-with-credential'),
    ('dhcp_reservation_exists','YES'),('default_gateway','8.8.8.8'),('professor_lan_ipv4','192.168.201.215')])
def test_invalid_or_drifted_router_metadata_fails_closed(field,value):
    e=evidence();e[field]=value
    with pytest.raises(ValueError):module().conditional_https_plan(e)


def test_router_credentials_and_unknown_fields_are_rejected():
    e=evidence();e['password']='SYNTHETIC_CANARY'
    with pytest.raises(ValueError) as exc:module().conditional_https_plan(e)
    assert 'SYNTHETIC' not in str(exc.value)
