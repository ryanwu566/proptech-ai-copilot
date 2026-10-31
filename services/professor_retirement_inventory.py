"""Source dependency evidence only; no provider, secret, router or cloud calls."""
from __future__ import annotations

from pathlib import Path
import os
import json
import re
import stat
import subprocess

from services.professor_credentials import protected_source_path,require


RENDER_JOBS=('.github/workflows/refresh-commute-snapshot.yml',
    '.github/workflows/refresh-market-read-model.yml','.github/workflows/reconcile-market-coverage.yml')


def reviewed_source(root,name):
    require(name=='render.yaml' or re.fullmatch(r'[.]github/workflows/[A-Za-z0-9_.-]+[.]ya?ml',name),'retirement_source_path_invalid')
    require(not protected_source_path(name),'retirement_private_source_forbidden')
    directory=None;descriptor=None
    try:
        directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        parts=Path(name).parts
        for part in parts[:-1]:
            new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=new
        descriptor=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        info=os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_size<=1_000_000,'retirement_source_size_or_type_invalid')
        with os.fdopen(descriptor,'rb') as stream:
            descriptor=None;raw=stream.read(1_000_001)
        require(len(raw)<=1_000_000,'retirement_source_exceeds_bound')
        return raw.decode('utf-8')
    except (OSError,UnicodeError):raise ValueError('retirement_source_unavailable') from None
    finally:
        if descriptor is not None:os.close(descriptor)
        if directory is not None:os.close(directory)


def retirement_inventory(root):
    root=Path(root);workflows=[];texts={}
    raw=subprocess.check_output(['git','-C',str(root),'ls-files','-z','--','render.yaml','.github/workflows/*.yml','.github/workflows/*.yaml'],
        env={'PATH':os.defpath,'LANG':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_OPTIONAL_LOCKS':'0'},timeout=15)
    require(len(raw)<=128000,'retirement_source_index_exceeds_bound')
    tracked=sorted(n for n in raw.decode().split('\0') if n)
    require('render.yaml' in tracked,'retirement_render_source_not_tracked')
    for name in tracked:
        text=reviewed_source(root,name);texts[name]=text
        if name=='render.yaml':continue
        workflows.append({'workflow':name,
            'secret_names':sorted(set(re.findall(r'\bsecrets\.([A-Z][A-Z0-9_]+)',text))),
            'variable_names':sorted(set(re.findall(r'\bvars\.([A-Z][A-Z0-9_]+)',text))),
            'environments':sorted(set(re.findall(r'^\s+environment:\s*([a-zA-Z0-9_.-]+)\s*$',text,re.M))),
            'live_secret_presence':'UNKNOWN','executed':False})
    protected=[]
    for workflow in workflows:
        if workflow['workflow'] not in RENDER_JOBS:continue
        text=texts[workflow['workflow']]
        protected.append({**workflow,'referenced_paths':sorted(set(re.findall(r'/(?:commute|market-insights)/[a-zA-Z0-9_/-]+',text))),
            'public_professor_retarget_allowed':False,'disposition':'separately reviewed local operator/scheduler maintenance, or retire explicitly; never reopen public ops',
            'approval_state':'PENDING_NOT_APPLIED'})
    render_text=texts['render.yaml']
    declared=sorted(set(re.findall(r'^\s*-\s*key:\s*([A-Z][A-Z0-9_]+)\s*$',render_text,re.M)))
    shared=[{'dependency':'frontend API origin and deployed callers','state':'PENDING_VERCEL_PREVIEW_AND_PRODUCTION_E2E'},
        {'dependency':'actual env/secret refs and IAM/ADC/provider restrictions','state':'UNKNOWN_DEPLOYED_METADATA_REQUIRED'},
        {'dependency':'legacy database and user/evidence writes, backups and authority','state':'PENDING_NO_UNIQUE_REMOTE_STATE_PROOF'},
        {'dependency':'reboot survival, TLS renewal, external acceptance and rollback','state':'PENDING_LIVE_ACCEPTANCE'}]
    result={'schema':'professor-cloud-retirement-dependencies-v1','values_included':False,
        'cloud_run':{'service':'proptech-earth-engine-api','historical_origin':'https://proptech-earth-engine-api-712372598609.asia-east1.run.app',
            'source_references':['Dockerfile.cloudrun','scripts/verify_cloud_run_guardrails.py','docs/operations/production-location-reliability-v1.md'],
            'dependencies':shared+[{'dependency':'attached service identity / implicit ADC and retained revision/image metadata','state':'UNKNOWN_CURRENT_CONTROL_PLANE'},
                {'dependency':'Google geocoding/Places/Routes and optional Earth Engine credential consumers','state':'UNKNOWN_CLOUD_CONSUMPTION_CURRENT_LOCAL_PROVIDERS_DISABLED'}],
            'retirement_allowed':False},
        'render':{'service':'proptech-ai-copilot-api','historical_origin':'https://proptech-ai-copilot-api.onrender.com',
            'declared_environment_names':declared,'source_references':['render.yaml',*RENDER_JOBS],
            'dependencies':shared+[{'dependency':'three protected maintenance workflows using RENDER_API_BASE_URL','state':'PENDING_SEPARATE_LOCAL_MAINTENANCE_REVIEW'},
                {'dependency':'RENDER_GIT_COMMIT release metadata fallback','state':'LEGACY_ALIAS_NOT_PROFESSOR_RUNTIME_REQUIREMENT'}],
            'protected_maintenance_workflows':protected,'retirement_allowed':False},
        'github_ci_workflows':workflows,'implicit_credentials_not_to_copy':['GITHUB_TOKEN workflow-scoped ephemeral identity','Cloud Run attached service identity / ADC metadata credential'],
        'live_cloud_configuration_proven':False,'ready_to_retire_credentials':[],'actions_executed':[],
        'public_maintenance_routes_enabled':False,'waiting_only_for_router_wan':False,
        'non_wan_blockers':['actual deployed credential/secret-reference inventories','fresh host metadata and trusted TLS reboot recovery source',
            'approved ACME tooling, issuance/renewal and controlled installer','local ML service handover and maintenance-job disposition','real Preview/Production authenticated E2E and reboot acceptance'],
        'ingress_apply_allowed':False,'retirement_allowed':False}
    from services.professor_activation_scan import SecretScanner,ScanRefused
    try:SecretScanner(()).check_bytes(json.dumps(result).encode())
    except ScanRefused:raise ValueError('retirement_identifier_credential_literal_forbidden') from None
    return result
