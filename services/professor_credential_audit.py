"""Expanded dependency audit: identifiers, stat metadata and accepted receipts.

No dotenv/private credential content, environment values or cloud secret APIs.
Repository declarations never prove live cloud presence or safe retirement.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from services.professor_credentials import (ACTIVE,AUTH_METADATA,CLOUD_ONLY,EXPECTED_RESOURCES,
    NAME,NON_ENVIRONMENT_NAMES,build_matrix,environment_names,protected_source_path,require)

PRODUCTION_CORE=set(ACTIVE)|AUTH_METADATA|{'NEXT_PUBLIC_SUPABASE_URL','NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY',
    'NEXT_PUBLIC_API_BASE_URL','API_ALLOWED_HOSTS','CORS_ALLOWED_ORIGINS','PROFESSOR_USERDB_ENABLED',
    'API_USAGE_GUARD_MODE','API_USAGE_LEDGER_REQUIRED','ANTI_ABUSE_ENFORCEMENT_MODE',
    'VALUATION_ML_ARTIFACT_DIR','VALUATION_ML_MANIFEST_SHA256','NLSC_VILLAGE_BOUNDARY_ARTIFACT_PATH',
    'NLSC_VILLAGE_BOUNDARY_ARTIFACT_SHA256','WRA_FLOOD_LOCAL_ROOT','PLVR_SERVING_EXCLUSIONS_ENABLED'}
SUFFIXES={'.py','.ts','.tsx','.js','.mjs','.json','.yaml','.yml','.md','.sql','.sh','.toml','.example','.ps1','.conf','.ini','.cfg','.tf','.hcl'}
ENV_EXAMPLES=('.env.example','.env.selfhost.example','frontend_next/.env.example','infra/selfhost/professor-secrets.env.example')


def template_identifier_evidence(root):
    """Git emits assignment prefixes only; Python never receives RHS bytes.

    Git scans indexed example blobs, not worktree/host envfiles. No textconv,
    shell expansion, external filter or credential command is invoked.
    """
    env={'PATH':os.defpath,'LANG':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_OPTIONAL_LOCKS':'0'}
    base=['git','-c','core.quotePath=false','-C',str(root)]
    listed=subprocess.run([*base,'ls-files','--stage','-z','--',*ENV_EXAMPLES],env=env,capture_output=True,timeout=15)
    require(listed.returncode==0 and len(listed.stdout)<=16384,'template_index_metadata_unavailable')
    templates={};objects={}
    for record in listed.stdout.decode().split('\0'):
        if not record:continue
        metadata,path=record.split('\t',1);mode,oid,stage=metadata.split()
        require(path in ENV_EXAMPLES and mode=='100644' and stage=='0' and re.fullmatch('[a-f0-9]{40,64}',oid),'template_index_metadata_invalid')
        templates[path]=[];objects[path]=oid
    pattern=r'^[[:space:]]*(#[[:space:]]*)?(export[[:space:]]+)?[A-Z][A-Z0-9_]{1,127}[[:space:]]*='
    projected=subprocess.run([*base,'grep','--cached','--no-textconv','-I','-o','-E',pattern,'--',*ENV_EXAMPLES],
        env=env,capture_output=True,timeout=15)
    require(projected.returncode in {0,1} and len(projected.stdout)<=128000,'template_projection_failed')
    from services.professor_activation_scan import SecretScanner,ScanRefused
    scanner=SecretScanner(())
    for line in projected.stdout.decode().splitlines():
        path,separator,prefix=line.partition(':')
        require(separator and path in templates,'template_projection_invalid')
        match=re.fullmatch(r'\s*(?:#\s*)?(?:export\s+)?([A-Z][A-Z0-9_]{1,127})\s*=',prefix)
        require(match,'template_projection_invalid');name=match.group(1)
        try:scanner.check_bytes(name.encode())
        except ScanRefused:raise ValueError('template_identifier_credential_literal_forbidden') from None
        templates[path].append(name)
    return {'source':'git_index_assignment_prefix_projection','templates':{p:sorted(set(v)) for p,v in templates.items()},
        'git_blob_ids':objects,'allowlisted_examples_present':len(templates),'all_four_examples_present':len(templates)==len(ENV_EXAMPLES),
        'template_values_materialized':False,'template_assignment_values_parsed':False,'host_envfiles_opened':False,
        'projection_process_scans_index_blob_bytes':True,'auditor_receives_values':False}


def accepted_profile_configuration_names(root):
    """Evaluate only public identifier expressions, never execute operator code."""
    names=set()
    def identifier(node,bindings):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):return node.value
        if isinstance(node,ast.Name) and node.id in bindings:return bindings[node.id]
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):return identifier(node.left,bindings)+identifier(node.right,bindings)
        raise ValueError('profile_identifier_expression_unsupported')
    for filename,target in [('professor_stage2_activation.py','REQUIRED_ENV'),('professor_stage4a_activation.py','ENV_DELTA')]:
        tree=ast.parse((Path(root)/'scripts/ops'/filename).read_text())
        node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==target for t in n.targets))
        require(isinstance(node,ast.Dict),'profile_dictionary_unsupported')
        for key,value in zip(node.keys,node.values):
            if key is not None:names.add(identifier(key,{}));continue
            require(isinstance(value,ast.DictComp) and len(value.generators)==1,'profile_dictionary_unsupported')
            gen=value.generators[0]
            require(isinstance(gen.target,ast.Name) and not gen.ifs and not gen.is_async,'profile_dictionary_unsupported')
            for item in ast.literal_eval(gen.iter):names.add(identifier(value.key,{gen.target.id:item}))
    require(all(NAME.fullmatch(n) for n in names),'profile_identifier_invalid')
    return names


def reference_names(filename,text):
    javascript=Path(filename).suffix in {'.ts','.tsx','.js','.mjs'}
    names=set(re.findall(r'process\.env\.([A-Z][A-Z0-9_]+)',text)) if javascript else environment_names(filename,text)
    names.update(re.findall(r'process\.env\[[\'"]([A-Z][A-Z0-9_]+)[\'"]\]',text))
    if not javascript:names.update(re.findall(r'\$\{([A-Z][A-Z0-9_]+)(?=[:}])',text))
    names.update(re.findall(r'\bvars\.([A-Z][A-Z0-9_]+)',text))
    if filename.endswith(('.yml','.yaml')):
        names.update(re.findall(r'^\s+(?:-\s+)?([A-Z][A-Z0-9_]+)\s*:',text,re.M))
        names.update(re.findall(r'^\s*-\s*key:\s*([A-Z][A-Z0-9_]+)\s*$',text,re.M))
    if Path(filename).name.startswith(('Dockerfile','Containerfile')):
        names.update(re.findall(r'^\s*(?:ARG|ENV)\s+([A-Z][A-Z0-9_]+)(?=[ =]|$)',text,re.M))
    if filename.endswith('.ps1'):names.update(re.findall(r'\$env:([A-Z][A-Z0-9_]+)',text))
    names={n for n in names if NAME.fullmatch(n) and n not in NON_ENVIRONMENT_NAMES}
    from services.professor_activation_scan import SecretScanner,ScanRefused
    try:
        scanner=SecretScanner(())
        for name in names:scanner.check_bytes(name.encode())
    except ScanRefused:raise ValueError('source_identifier_credential_literal_forbidden') from None
    return names


def validate_accepted_credentials(receipt,host,mounts,expected_image):
    require(receipt.get('status')=='PASS' and receipt.get('api_image_id')==expected_image,'accepted_receipt_identity_invalid')
    require(receipt.get('identity_provider')=='supabase' and receipt.get('application_data_authority')=='professor_postgresql','accepted_authority_invalid')
    for name in ('profile_installed','loopback_8080','postgresql_private','market_ops_disabled','paid_providers_disabled'):
        require(receipt.get(name) is True,'accepted_receipt_safety_invalid')
    require(receipt.get('secret_values_returned') is False,'accepted_receipt_safety_invalid')
    names=set(ACTIVE.values());require(set(host)==set(mounts)==names,'accepted_secret_set_invalid')
    for name in names:
        row=host[name]
        require(set(row)=={'device','gid','inode','mode','size','uid'},'accepted_secret_metadata_invalid')
        require(row==mounts[name] and row['uid']==0 and row['gid']==10001 and row['mode']=='0o440','accepted_secret_metadata_invalid')
        require(all(type(row[k]) is int and row[k]>0 for k in ('device','inode','size')) and row['size']<=65536,'accepted_secret_metadata_invalid')
    return {'status':'PASS_ACCEPTED_RECEIPT','verified_secret_files':sorted(names),
        'fresh_host_inspection':False,'values_read':False,'source_commit':receipt.get('source_commit'),
        'snapshot_time':receipt.get('completed_at'),'basis':'accepted Stage4A receipt and matching host/container metadata; no present-time root inspection'}


def accepted_credential_evidence(root):
    root=Path(root);folder=root/'reports/professor-stage4a-auth-userdb'
    manifest=json.loads((folder/'successful-activation-evidence-manifest.json').read_text())
    authority=json.loads((folder/'acceptance.json').read_text())
    source=Path(manifest['sanitized_source'])
    require(source.is_absolute() and str(source).startswith('/tmp/professor-stage4a-activation-') and not source.is_symlink(),'accepted_receipt_path_invalid')
    indexed={row['file']:row for row in manifest['artifacts']};data={}
    for name in ('acceptance.json','secret-host-metadata.json','secret-mounts-after.json','containers-after.json','database-after.json'):
        path=source/name
        try:
            info=path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_size<=128000,'accepted_receipt_file_invalid')
            raw=path.read_bytes()
        except (FileNotFoundError,PermissionError):
            return {'status':'UNAVAILABLE_ACCEPTED_RECEIPT','verified_secret_files':[],'fresh_host_inspection':False,'values_read':False}
        require(hashlib.sha256(raw).hexdigest()==indexed[name]['sha256'] and len(raw)==indexed[name]['bytes'],'accepted_receipt_digest_mismatch')
        data[name]=json.loads(raw)
    result=validate_accepted_credentials(data['acceptance.json'],data['secret-host-metadata.json'],
        data['secret-mounts-after.json'],authority['active_api_image_id'])
    result['database_mount_evidence']=validate_database_mounts(data['containers-after.json'])
    require(data['database-after.json'].get('status')=='PASS','accepted_database_probe_invalid')
    result['database_security_probe']='PASS_ACCEPTED_RECEIPT_NOT_FRESH'
    result['manifest']='reports/professor-stage4a-auth-userdb/successful-activation-evidence-manifest.json'
    return result


def validate_database_mounts(services):
    files=[]
    for kind in ('app','usage'):
        item=services['postgres_'+kind];require(not item['ports'],'accepted_database_host_exposure')
        name=kind+'_admin_password'
        expected={'Source':'/run/proptech-selfhost/secrets/'+name,'Destination':'/run/secrets/'+name,'RW':False,'Type':'bind'}
        tls={'Source':'/run/proptech-selfhost/tls/'+kind,'Destination':'/run/postgres-tls','RW':False,'Type':'bind'}
        require(expected in item['mounts'] and tls in item['mounts'],'accepted_database_mount_invalid')
        files.append(name)
    forbidden=set(files)|{'app_runtime_password','usage_migration_password'}
    private_files=[root/name for root in (Path('/run/proptech-selfhost/secrets'),Path('/etc/proptech-selfhost/secrets')) for name in forbidden]
    private_files.append(Path('/run/proptech-selfhost/tls/ca.key'))
    private_directories=[Path('/run/proptech-selfhost/tls')/kind for kind in ('app','usage')]
    for service,item in services.items():
        if service in {'postgres_app','postgres_usage'}:continue
        for row in item['mounts']:
            source=Path(row['Source'])
            require(source.is_absolute() and '..' not in source.parts,'accepted_mount_path_invalid')
            reaches_private_file=any(target==source or target.is_relative_to(source) for target in private_files)
            reaches_private_directory=any(source.is_relative_to(target) or target.is_relative_to(source) for target in private_directories)
            require(not reaches_private_file and not reaches_private_directory and row['Destination']!='/run/postgres-tls','accepted_admin_credential_in_non_db')
    return {'db_admin_files':files,'read_only_db_tls_directories':True,'api_admin_or_initialization_credentials':False,
        'individual_live_key_metadata':'NOT_FRESHLY_INSPECTED','basis':'hash-bound accepted Stage4A container metadata'}


def file_metadata(path):
    """No content open. Unknown permissions must never be reported absent."""
    try:row=Path(path).lstat()
    except FileNotFoundError:return {'state':'MISSING'}
    except PermissionError:return {'state':'UNKNOWN'}
    mode=stat.S_IMODE(row.st_mode)
    staged=Path(path).parent==Path('/run/proptech-selfhost/secrets')
    access=(row.st_gid==10001 and mode==0o440) if staged else (row.st_gid==0 and mode==0o600)
    limit=1024*1024 if Path(path).name=='earth_engine_adc_json' else 8192
    safe=stat.S_ISREG(row.st_mode) and row.st_uid==0 and row.st_nlink==1 and 0<row.st_size<=limit and access
    return {'state':'PRESENT_SAFE' if safe else 'PRESENT_UNSAFE','uid':row.st_uid,'gid':row.st_gid,'mode':oct(mode)}


def credential_state(accepted,metadata,*,required=False):
    state=metadata['state']
    if state=='MISSING':return 'MISSING_REQUIRED' if required else 'ABSENT_METADATA_ONLY'
    if state=='PRESENT_UNSAFE':return 'UNSAFE_METADATA'
    if state=='PRESENT_SAFE':return 'PRESENT_METADATA_ONLY'
    return 'PRESENT_ACCEPTED_RECEIPT' if accepted else 'UNKNOWN'


def build_dependency_matrix(root,cloud_metadata=()):
    root=Path(root);base=build_matrix(root,cloud_metadata)
    catalog=json.loads((root/'config/professor-server-credentials.json').read_text())
    manifest=json.loads((root/'config/hosted-environment-manifest.json').read_text())
    evidence=accepted_credential_evidence(root)
    records={r['name']:dict(r) for r in base['credentials']}
    declared={r['name']:r for r in [*catalog['configuration_variables'],*manifest['variables']]}
    required_names=PRODUCTION_CORE|accepted_profile_configuration_names(root)|{r['name'] for r in manifest['variables'] if r.get('required') is True}
    for name,row in declared.items():
        records.setdefault(name,{'name':name,'side':row.get('side',row.get('scope','backend')),
            'provider':row.get('capability','application/runtime configuration'),'purpose':row.get('purpose','Declared hosted/runtime configuration'),
            'classification':'VERCEL_BROWSER_PUBLIC' if name.startswith('NEXT_PUBLIC_') else 'LEGACY_CLOUD_ONLY' if name in CLOUD_ONLY else 'PROFESSOR_SERVER_OPTIONAL',
            'source_references':row.get('source_references',[]),'secret_file':None,'active_api_secret_mount':False})
    examples=template_identifier_evidence(root)
    for path,names in examples['templates'].items():
        for name in names:
            row=records.setdefault(name,{'name':name,'side':'frontend' if name.startswith('NEXT_PUBLIC_') else 'backend_or_operations',
                'provider':'repository env example','purpose':'Example identifier only; not evidence of configuration or activation',
                'classification':'VERCEL_BROWSER_PUBLIC' if name.startswith('NEXT_PUBLIC_') else 'UNKNOWN',
                'source_references':[],'secret_file':None,'active_api_secret_mount':False})
            row['source_references']=sorted(set(row['source_references'])|{path+' (Git prefix projection)'})
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0');scanned=[];skipped=[];oversized=[]
    for name in paths:
        if not name:continue
        path=root/name
        if protected_source_path(name):skipped.append(name);continue
        if path.is_symlink() or not path.is_file() or Path(name).parts[0] in {'tests','reports','data','models'} or (path.suffix not in SUFFIXES and not path.name.startswith(('Dockerfile','Containerfile'))):continue
        if path.stat().st_size>1_000_000:oversized.append(name);continue
        scanned.append(name)
        for variable in reference_names(name,path.read_text(errors='replace')):
            row=records.setdefault(variable,{'name':variable,'side':'frontend' if variable.startswith('NEXT_PUBLIC_') else 'backend_or_operations',
                'provider':'source/configuration reference','purpose':'Exact source identifier; no inferred activation',
                'classification':'VERCEL_BROWSER_PUBLIC' if variable.startswith('NEXT_PUBLIC_') else 'UNKNOWN',
                'source_references':[],'secret_file':None,'active_api_secret_mount':False})
            row['source_references']=sorted(set(row['source_references'])|{name})
    rows=[];missing=[];unverified=[]
    for name,row in sorted(records.items()):
        required=name in required_names
        if name in ACTIVE:
            staged=Path('/run/proptech-selfhost/secrets')/ACTIVE[name]
            observed=file_metadata(staged)
            presence=credential_state(ACTIVE[name] in evidence['verified_secret_files'],observed,required=True)
            row['professor_secret_presence']=presence;row['current_file_metadata']=observed
            if presence=='MISSING_REQUIRED':row['classification']='MISSING_REQUIRED';missing.append(name)
            if presence in {'UNKNOWN','UNSAFE_METADATA','PRESENT_METADATA_ONLY'}:unverified.append(name)
            location='Professor Stage2 protected store/staging; '+presence
            migration='VERIFIED_ACCEPTED_STAGE4A_NOT_FRESH' if presence=='PRESENT_ACCEPTED_RECEIPT' else presence
        else:
            location='Repository declarations only; live location UNKNOWN'
            migration='NOT_ADMITTED_OPTIONAL' if not required else 'NONSECRET_CONFIGURATION_REVIEW'
            if row.get('secret_file'):
                observed=file_metadata(Path('/etc/proptech-selfhost/secrets')/row['secret_file'])
                row['professor_secret_presence']=credential_state(False,observed);row['current_file_metadata']=observed
                location='Professor optional protected store: '+row['professor_secret_presence']+'; actual cloud presence UNKNOWN'
            if name in AUTH_METADATA:location='Professor protected nonsecret configuration per accepted Stage4A';migration='ACCEPTED_METADATA_NO_PRIVATE_AUTH_KEY'
            if name.startswith('NEXT_PUBLIC_'):location='Vercel browser/build declarations; accepted auth project metadata; actual env inventory UNKNOWN';migration='FRONTEND_ONLY_NO_SERVER_SECRET'
            if name in {'API_ALLOWED_HOSTS','CORS_ALLOWED_ORIGINS','NEXT_PUBLIC_API_BASE_URL'}:migration='AWAITING_APPROVED_PUBLIC_API_ORIGIN'
            if name in CLOUD_ONLY or row['classification']=='LEGACY_CLOUD_ONLY':location='Legacy cloud/CI/unsupported references; actual presence UNKNOWN';migration='NOT_PROFESSOR_API_RUNTIME'
        if name in ACTIVE:row['classification']='MISSING_REQUIRED' if name in missing else 'PROFESSOR_SERVER_ACTIVE'
        elif required and not name.startswith('NEXT_PUBLIC_'):row['classification']='PROFESSOR_SERVER_ACTIVE'
        refs=row.get('source_references',[])
        operator_only=bool(refs) and not any(p.startswith(('services/','backend/','frontend_next/')) or p=='docker-compose.selfhost.yml' for p in refs)
        row.update(consumer=refs or [row.get('side','backend')+' (declared metadata)'],current_location=location,
            target_location=row.get('destination') or ('Vercel frontend public build configuration' if name.startswith('NEXT_PUBLIC_') else
                '/etc/proptech-selfhost/runtime.env (nonsecret, reviewed consumer only)' if not row.get('secret_file') else
                '/etc/proptech-selfhost/secrets/'+row['secret_file']),
            required_for_production='YES' if required else 'NO',required_scope='accepted local profile + eventual direct HTTPS; optional providers require separate admission',
            migration_state=migration,retirement_state='NOT_APPROVED_KEEP_UNTIL_RETIREMENT_GATE',retirement_approved=False,
            automatic_activation=False,identifier_kind='credential' if row.get('secret_file') or name in ACTIVE else 'configuration_or_legacy_reference')
        if name in CLOUD_ONLY or row['classification']=='LEGACY_CLOUD_ONLY':row['target_location']='Operator/CI only if separately retained; never Professor API'
        elif operator_only and not required and not row.get('secret_file'):
            row['target_location']='Approved CI/operator task only; never add to API environment'
            row['migration_state']='REFERENCE_OR_OPERATOR_ONLY_NOT_API_RUNTIME'
        if name.startswith('NEXT_PUBLIC_') and re.search(r'SERVICE_ROLE|PRIVATE|SECRET|PASSWORD|DATABASE',name):
            row.update(classification='UNKNOWN',target_location='NOT_ADMITTED_SERVER_CREDENTIAL_MUST_NEVER_ENTER_BROWSER',
                migration_state='REJECT_SERVER_SECRET_PUBLIC_CONFIGURATION')
        unmapped_secret=not row.get('secret_file') and (name in {'PGPASSWORD','PASSWORD','TOKEN','SECRET'} or re.search(
            r'(?:_KEY|_API_KEY|_ACCESS_KEY_ID|_SECRET_ACCESS_KEY|_SECRET|_PASSWORD|_TOKEN|_SIGNING_KEY|_HMAC_KEY|_CREDENTIALS|_PRIVATE_KEY|(?:DATABASE|DB)_URL|DATABASE_URI|CONNECTION_STRING)$',name))
        if unmapped_secret and row['classification']!='LEGACY_CLOUD_ONLY' and not name.startswith('NEXT_PUBLIC_'):
            row.update(classification='UNKNOWN',target_location='NOT_ADMITTED_FILE_ONLY_SECRET_REVIEW_REQUIRED',
                migration_state='UNMAPPED_SECRET_NAME_REQUIRES_EXPLICIT_FILE_CONTRACT',identifier_kind='credential')
        if unmapped_secret and name.startswith('NEXT_PUBLIC_'):
            row.update(classification='UNKNOWN',target_location='NOT_ADMITTED_SERVER_CREDENTIAL_MUST_NEVER_ENTER_BROWSER',
                migration_state='UNREVIEWED_PUBLIC_CREDENTIAL_NAME',identifier_kind='credential')
        if row['classification']=='UNKNOWN' and row['identifier_kind']!='credential':
            row.update(target_location='NOT_ADMITTED_IDENTIFIER_TYPE_OR_CONSUMER_REVIEW_REQUIRED',
                migration_state='UNREVIEWED_IDENTIFIER_NOT_RUNTIME_CONFIGURATION')
        rows.append(row)
    file_only=[]
    for row in base['file_only_credentials']:
        item=dict(row);active=row['active_runtime_admission'] in {'DB_ONLY','DB_TLS_ONLY'}
        filename=row['filename'];target=filename if filename.startswith('/') else '/etc/proptech-selfhost/secrets/'+filename
        item.update(name=filename,provider='PostgreSQL isolated credential/TLS file',
            current_location=('PRESENT_DB_ONLY_ACCEPTED_RECEIPT' if filename in evidence.get('database_mount_evidence',{}).get('db_admin_files',[]) else
                'DB_TLS_DIRECTORY_AND_TLS_PROBE_ACCEPTED; individual current file metadata UNKNOWN' if row['active_runtime_admission']=='DB_TLS_ONLY' else
                'Accepted Stage2/4A file-only contract; no fresh private content inspection'),target_location=target,
            required_for_production='YES' if active else 'NO',classification='PROFESSOR_SERVER_ACTIVE' if active else 'PROFESSOR_SERVER_OPTIONAL',
            migration_state='PRESERVE_DB_ONLY' if active else 'NOT_API_RUNTIME_OR_INITIALIZATION_ONLY',
            retirement_state='NOT_APPROVED_KEEP_UNTIL_RETIREMENT_GATE',retirement_approved=False)
        file_only.append(item)
    return {'schema':'professor-stage5-provider-dependencies-v2','values_included':False,'secret_values_opened':False,
        'dependencies':rows,'credential_identifier_count':len(base['credentials']),'configuration_and_credential_identifier_count':len(rows),
        'accepted_required_credential_evidence':evidence,'missing_required_credentials':missing,'unverified_current_profile_credentials':unverified,
        'known_current_profile_credentials_on_server':not missing and not unverified and len(evidence['verified_secret_files'])==6,
        'production_critical_credentials_on_server':'PARTIAL_LIVE_CLOUD_DEPENDENCY_INVENTORIES_UNVERIFIED',
        'live_cloud_scopes':{p:'SUPPLIED_NAMES_ONLY' if base['platform_scopes'][p]=='SUPPLIED_ALL_DEPLOYMENT_NAMES' else 'UNKNOWN_NAMES_INVENTORY_NOT_SUPPLIED' for p in EXPECTED_RESOURCES},
        'all_requested_audit_scopes_complete':base['all_requested_audit_scopes_complete'] and not oversized and not missing and not unverified,
        'repository_scanned_file_count':len(scanned),'repository_scanned_files':scanned,
        'protected_files_not_opened':sorted(skipped),'oversized_files_not_scanned':oversized,
        'env_example_names_projection':examples,
        'private_host_envfiles':'NOT_OPENED; names from accepted catalogs/receipts only',
        'file_only_credentials':file_only,'no_credential_providers':base['no_credential_providers'],
        'ready_to_retire_credentials':[],'optional_providers_enabled':False,'market_ops_enabled':False,
        'ingress_apply_allowed':False,'retirement_allowed':False}
