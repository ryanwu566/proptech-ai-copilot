"""Offline evaluation of sanitized PUBLIC auth authority observations.

No environment/credential reads, network, database updates or runtime activation.
A database/project identifier alone never establishes the frontend authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit

FRONTEND='https://proptech-ai-copilot.vercel.app'
BACKEND_ISSUER='https://flyhsjcynreuofbcdxod.supabase.co/auth/v1'
AUDIENCE='authenticated'
REVIEWED_RELEASE='9cc40d645757af4513d9afdf0c008939cc489a77'
REVIEWED_ASSET='/_next/static/immutable/chunks/28_mshq0x50li.js'
REVIEWED_SHA256='39cf21f28d4ca1104c5f229e12bc5e61003ed42db7d2c6a10aa09d0567a4c7ba'
REVIEWED_ORIGIN='https://flyhsjcynreuofbcdxod.supabase.co'


def public_origin(value):
    if not isinstance(value,str):raise ValueError('public_authority_invalid')
    try:
        p=urlsplit(value)
        if (p.scheme!='https' or not re.fullmatch(r'[a-z0-9]{20}\.supabase\.co',p.hostname or '')
            or p.username or p.password or p.query or p.fragment or p.port is not None or p.path not in {'','/'}):
            raise ValueError()
        return 'https://'+p.hostname
    except ValueError:raise ValueError('public_authority_invalid') from None


def fingerprint(project_url):
    origin=public_origin(project_url)
    fields={'identity_provider':'supabase','project_ref':urlsplit(origin).hostname.split('.')[0],
            'project_url':origin,'issuer':origin+'/auth/v1','audience':AUDIENCE,'subject_type':'uuid'}
    return fields,hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def evaluate(observation,provider,*,backend_issuer=BACKEND_ISSUER,audience=AUDIENCE,backend_project_url=None):
    result={'status':'PENDING','issuer_conflict':False,'existing_users_preserved':True,
            'credential_values_compared':False,'operator_metadata_needed':'Vercel Production NEXT_PUBLIC_SUPABASE_URL'}
    def conflict():return {**result,'status':'FAIL','issuer_conflict':True,'reason_code':'public_authority_conflict'}
    if (observation.get('schema')!='professor-public-auth-authority-observation-v1'
        or observation.get('frontend_origin')!=FRONTEND or observation.get('release_stable') is not True
        or observation.get('release_commit')!=REVIEWED_RELEASE
        or observation.get('read_only') is not True
        or any(observation.get(k) is not False for k in ['credential_values_returned','credential_values_compared','auth_requests_performed','frontend_modified'])):
        return {**result,'reason_code':'frontend_observation_incomplete'}
    origins=set()
    try:
        for asset in observation.get('assets',[]):
            if (asset.get('path')!=REVIEWED_ASSET
                or asset.get('sha256')!=REVIEWED_SHA256
                or asset.get('binding_proof')!='manually_reviewed_immutable_asset_sha256'
                or not all(asset.get(k) is True for k in ['authenticated_audience_marker','issuer_suffix_marker','password_signin_marker'])):continue
            for binding in asset.get('configuration_bindings',[]):
                if (all(binding.get(k) is True for k in ['url_constructor_returns_origin','client_uses_same_configuration_url_and_key','persist_session','auto_refresh'])
                    and binding.get('detect_session_in_url') is False):
                    origin=public_origin(binding.get('public_origin'))
                    if origin!=REVIEWED_ORIGIN:return conflict()
                    origins.add(origin)
    except ValueError:return {**result,'status':'FAIL','reason_code':'unsupported_public_authority'}
    if not origins:return {**result,'reason_code':'frontend_binding_not_proven'}
    if len(origins)!=1:return conflict()
    origin=next(iter(origins));identity,digest=fingerprint(origin)
    if (backend_issuer!=identity['issuer'] or audience!=AUDIENCE or provider.get('project_ref')!=identity['project_ref']):return conflict()
    if backend_project_url is not None:
        try:
            if public_origin(backend_project_url)!=origin:return conflict()
        except ValueError:return conflict()
    result.update(identity,authority_sha256=digest,subject_mapping='verified_supabase_sub_uuid_unchanged',password_migration_required=False)
    count_fields=['auth_users','confirmed_users','prior_signin_users','authenticated_audience_users','authenticated_role_users','banned_users','deleted_users','anonymous_users']
    if (any(type(provider.get(k)) is not int or provider[k]<0 for k in count_fields)
        or not 1<=provider['confirmed_users']<=provider['auth_users']
        or any(provider[k]>provider['auth_users'] for k in count_fields)
        or provider['authenticated_audience_users']!=provider['auth_users']
        or provider['authenticated_role_users']!=provider['auth_users']
        or provider.get('subject_storage_type')!='uuid'
        or any(provider[k]!=0 for k in ['banned_users','deleted_users','anonymous_users'])
        or provider.get('legacy_account_authority_present') is not False
        or provider.get('legacy_workspace_cases_present') is not False):
        return {**result,'reason_code':'account_metadata_review_required'}
    return {**result,'status':'PASS','reason_code':'public_frontend_provider_backend_authority_agree',
            'operator_metadata_needed':None,'runtime_activation_authorized':False}
