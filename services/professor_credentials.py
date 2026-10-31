"""Credential NAME inventory only. No environment, credential store or API reads."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess

NAME=re.compile(r'[A-Z][A-Z0-9_]{1,127}')
ACTIVE={'DATABASE_URL':'app_database_url','API_USAGE_DATABASE_URL':'usage_database_url',
    'API_USAGE_PEER_HMAC_KEY':'usage_peer_hmac_key','PILOT_SESSION_SIGNING_KEY':'pilot_session_signing_key',
    'VALUATION_DATABASE_URL':'valuation_database_url','PROFESSOR_USER_DATABASE_URL':'professor_user_database_url'}
AUTH_METADATA={'SUPABASE_URL','SUPABASE_JWT_ISSUER','SUPABASE_JWT_AUDIENCE','PGSSLROOTCERT'}
CLOUD_ONLY={'CLOUDFLARE_API_TOKEN','CLOUDFLARE_TUNNEL_TOKEN','GCP_SERVICE_ACCOUNT_KEY','VERCEL_TOKEN',
    'RENDER_API_KEY','RENDER_API_BASE_URL','RENDER_GIT_COMMIT','SUPABASE_ACCESS_TOKEN',
    'GCP_SA_KEY','GCP_WORKLOAD_IDENTITY_PROVIDER','GCP_SERVICE_ACCOUNT'}
EXPECTED_RESOURCES={'cloud_run':'proptech-earth-engine-api','render':'proptech-ai-copilot-api',
    'vercel':'proptech-ai-copilot','github_actions':'ryanwu566/proptech-ai-copilot'}
# Documentation prefixes, a Python constant, an API URL segment and a shell
# placeholder are not environment-variable references.
NON_ENVIRONMENT_NAMES={'NEXT_PUBLIC_','NEXT_PUBLIC_SUPABASE','TGOS_MIN_REMAINING_SECONDS','TGOS_MAP_API','R2_REMOTE'}


def require(value,reason):
    if not value:raise ValueError(reason)


def environment_names(filename,text):
    """Return identifiers only, never lines, literals or assignment values."""
    names=set()
    if filename.endswith('.py'):
        try:tree=ast.parse(text)
        except SyntaxError:return names
        constants={}
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str) and NAME.fullmatch(node.value.value):
                for target in node.targets:
                    if isinstance(target,ast.Name):constants[target.id]=node.value.value
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and node.args:
                function=ast.unparse(node.func)
                if function in {'os.getenv','os.environ.get','environ.get','values.get'}:
                    arg=node.args[0]
                    value=arg.value if isinstance(arg,ast.Constant) else constants.get(arg.id) if isinstance(arg,ast.Name) else None
                    if isinstance(value,str) and NAME.fullmatch(value):names.add(value)
            if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Attribute) and ast.unparse(node.value)=='os.environ':
                if isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,str) and NAME.fullmatch(node.slice.value):names.add(node.slice.value)
    names.update(re.findall(r'process\.env\.([A-Z][A-Z0-9_]+)',text))
    names.update(re.findall(r'\bsecrets\.([A-Z][A-Z0-9_]+)',text))
    # Config/Compose/docs contain names in quoted fields and shell references.
    if not filename.endswith('.py'):
        candidates=re.findall(r'\b[A-Z][A-Z0-9_]{2,127}\b',text)
        names.update(n for n in candidates if re.search(r'(?:_API_KEY|_TOKEN|_SECRET|_PASSWORD|_CREDENTIALS|DATABASE_URL)$',n)
                     or n.startswith(('NEXT_PUBLIC_','TGOS_','TDX_CLIENT_','R2_','SUPABASE_')))
    return names


def validate_cloud_metadata(value):
    fields={'platform','source','environment_names','secret_reference_names','values_exported'}
    require(isinstance(value,dict) and fields<=set(value)<=fields|{'resource','environment_scope'},'metadata_fields_invalid')
    require(value['platform'] in EXPECTED_RESOURCES and value['source']=='operator_control_plane_metadata' and value['values_exported'] is False,'metadata_scope_invalid')
    for field,pattern in [('environment_names',NAME),('secret_reference_names',re.compile(r'[A-Za-z0-9._/-]{1,200}'))]:
        rows=value[field]
        require(isinstance(rows,list) and len(rows)<=500,'metadata_names_invalid')
        require(all(isinstance(n,str) and pattern.fullmatch(n) and not n.startswith(('sb_secret_','sb_publishable_','eyJ')) for n in rows),'metadata_names_invalid')
        require(len(rows)==len(set(rows)),'metadata_names_duplicate')
        from services.professor_activation_scan import SecretScanner,ScanRefused
        try:
            scanner=SecretScanner(())
            for name in rows:scanner.check_bytes(name.encode())
        except ScanRefused:raise ValueError('metadata_literal_credential_forbidden') from None
    if 'resource' in value:require(value['resource']==EXPECTED_RESOURCES[value['platform']],'metadata_resource_unreviewed')
    if 'environment_scope' in value:require(value['environment_scope']=='all_deployments','metadata_environment_incomplete')
    return {k:(sorted(v) if isinstance(v,list) else v) for k,v in value.items()}


def _relevant(name,known):
    if name in NON_ENVIRONMENT_NAMES:return False
    return name in known or name in ACTIVE or name in AUTH_METADATA or name in CLOUD_ONLY or bool(re.match(
        r'(?:GOOGLE_|GCP_|AWS_|TGOS_|TDX_CLIENT_|R2_|SUPABASE_|NEXT_PUBLIC_|PRODUCTION_.*DATABASE_URL$)',name))


def protected_source_path(name):
    """Deny before opening; only the public names-only catalog is exempt."""
    if name=='config/professor-server-credentials.json':return False
    path=Path(name);lower=path.name.lower();parts={v.lower() for v in path.parts}
    return (bool(parts & {'secrets','.secrets','credentials','.credentials','.aws','.config'})
        or lower.startswith('.env') or re.search(r'(?:^|[.])env(?:[.]|$)',lower) is not None
        or path.suffix.lower() in {'.pem','.key','.p12','.pfx'}
        or path.suffix.lower() in {'.json','.toml','.ini','.yaml','.yml'}
            and re.search(r'credential|service[-_]account|(?:^|[-_])adc(?:[.]|[-_])|secret|private[-_]key',lower) is not None)


def build_matrix(root,cloud_metadata=()):
    root=Path(root)
    catalog=json.loads((root/'config/professor-server-credentials.json').read_text())
    known={row['name']:row for row in catalog['credentials']}
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    references={n:set(r.get('source_references',[])) for n,r in known.items()};oversized=[];protected=[]
    for name in paths:
        if not name:continue
        path=root/name;parts=Path(name).parts
        if protected_source_path(name):protected.append(name);continue
        if path.is_symlink() or not path.is_file() or parts[0] in {'tests','reports','data','models'}:continue
        if path.suffix not in {'.py','.ts','.tsx','.js','.mjs','.json','.yaml','.yml','.md','.sql','.sh','.toml','.example'}:continue
        if path.stat().st_size>1_000_000:
            if path.suffix in {'.py','.ts','.tsx','.yaml','.yml','.sh','.sql'}:oversized.append(name)
            continue
        for n in environment_names(name,path.read_text(errors='replace')):
            if _relevant(n,known):references.setdefault(n,set()).add(name)
    references.setdefault('PROFESSOR_USER_DATABASE_URL',set()).update({'services/professor_userdb.py','scripts/ops/professor_stage4a_entrypoint.py'})
    # Explicit cloud administration names are NOT credentials to mount in API.
    for n in CLOUD_ONLY:references.setdefault(n,set())
    metadata={}
    for record in cloud_metadata:
        record=validate_cloud_metadata(record)
        require(record['platform'] not in metadata,'metadata_platform_duplicate')
        metadata[record['platform']]=record
        for name in record['environment_names']:references.setdefault(name,set())
    rows=[]
    for name in sorted(references):
        original=known.get(name,{})
        secret_file=ACTIVE.get(name,original.get('secret_file'))
        if name in ACTIVE or name in AUTH_METADATA or name=='POSTGRES_PASSWORD_FILE':classification='PROFESSOR_SERVER_ACTIVE'
        elif name.startswith('NEXT_PUBLIC_'):
            classification='UNKNOWN' if re.search(r'(?:SERVICE_ROLE|PRIVATE|SECRET|PASSWORD|DATABASE)',name) else 'VERCEL_BROWSER_PUBLIC'
        elif name in CLOUD_ONLY:classification='LEGACY_CLOUD_ONLY'
        elif name in known and original.get('classification')=='unsupported':classification='LEGACY_CLOUD_ONLY'
        elif secret_file or name.startswith(('TGOS_','TDX_CLIENT_','GOOGLE_APPLICATION','EARTH_ENGINE_','R2_')):classification='PROFESSOR_SERVER_OPTIONAL'
        else:classification='UNKNOWN'
        side=original.get('side','frontend' if name.startswith('NEXT_PUBLIC_') else 'operations' if name in CLOUD_ONLY else 'backend')
        destination=('protected_root_configuration' if name in AUTH_METADATA else
            '/etc/proptech-selfhost/secrets/'+secret_file if secret_file else
            'frontend_build_configuration' if side=='frontend' else 'not_admitted_or_no_runtime_file')
        if side=='frontend':destination='frontend_build_configuration'
        rows.append({'name':name,'provider':original.get('provider','Professor PostgreSQL application-user persistence' if name=='PROFESSOR_USER_DATABASE_URL' else 'TDX OAuth snapshot refresh' if name.startswith('TDX_CLIENT_') else 'source/control-plane metadata'),
            'classification':classification,'side':side,'purpose':original.get('runtime_purpose','See source references; no inferred active provider.'),
            'required_current_profile':name in ACTIVE or name in AUTH_METADATA or name=='POSTGRES_PASSWORD_FILE',
            'active_api_secret_mount':name in ACTIVE,'secret_file':secret_file,'destination':destination,
            'installer_support':name in known and original.get('classification') in {'secret','credential_file','public_client_credential'},
            'automatic_activation':False,'current_server_evidence':'Stage4A successful activation' if name in ACTIVE else 'not independently inspected; optional/metadata only',
            'cloud_presence':{p:('PRESENT_NAME_ONLY' if name in r['environment_names'] else 'NOT_LISTED_IN_SUPPLIED_SCOPE') for p,r in metadata.items()},
            'cloud_control_plane_inventory':'UNKNOWN' if len(metadata)<len(EXPECTED_RESOURCES) else 'SUPPLIED_NAME_METADATA_ONLY',
            'retirement_approved':False,'source_references':sorted(references[name])})
    complete=set(metadata)==set(EXPECTED_RESOURCES) and all(r.get('resource')==EXPECTED_RESOURCES[p] and r.get('environment_scope')=='all_deployments' for p,r in metadata.items())
    file_only=[]
    for original in catalog['file_only_credentials']:
        row=dict(original)
        row['legacy_catalog_ordinary_compose_required']=row.pop('ordinary_compose_required',None)
        row['active_runtime_admission']=('DB_ONLY' if row['filename'] in {'app_admin_password','usage_admin_password'} else
            'NOT_MOUNTED_INITIALIZATION_ONLY' if row['filename'] in {'app_runtime_password','usage_migration_password'} else
            'DB_TLS_ONLY' if row['filename'].endswith('/server.key') else 'OPERATOR_ONLY_NOT_API')
        file_only.append(row)
    return {'schema':'professor-stage5-provider-matrix-v1','values_included':False,
        'repository_audit_complete':not oversized,'oversized_code_files_not_scanned':oversized,
        'repository_audit_scope':'tracked admitted source/config/docs/CI identifiers plus public accepted catalog; envfiles and credential paths never opened',
        'protected_source_files_not_opened':sorted(protected),
        'non_environment_references_excluded':sorted(NON_ENVIRONMENT_NAMES),
        'remote_inventory_complete':complete,'all_requested_audit_scopes_complete':complete and not oversized,
        'platform_scopes':{p:('SUPPLIED_ALL_DEPLOYMENT_NAMES' if p in metadata and metadata[p].get('environment_scope')=='all_deployments' else 'UNKNOWN_CONTROL_PLANE_NOT_AVAILABLE') for p in EXPECTED_RESOURCES},
        'credentials':rows,'file_only_credentials':file_only,
        'no_credential_providers':catalog['no_credential_providers'],
        'current_local_api_secret_files':list(ACTIVE.values()),'optional_providers_enabled':False,
        'retirement_allowed':False,'forbidden_target_ingress':['Cloudflare Tunnel','Cloudflare Access','Cloud Run','Render','external VPS','ngrok','Tailscale Funnel']}
