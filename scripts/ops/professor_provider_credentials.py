#!/usr/bin/env python3
"""Operator-only missing-required credential storage. Never activates services.

Values may enter only the existing Stage2 hidden-TTY/protected-file primitives.
The agent must never execute a nonempty installation against the host.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import resource
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from scripts.ops import professor_server_secrets as stage2
from services.professor_credentials import ACTIVE, AUTH_METADATA, NAME
from services.professor_activation_scan import SecretScanner, ScanRefused
from services.selfhost_secret_files import SecretRefused

PLAN = ROOT/'config/professor-provider-install.plan.json'


def require(condition, reason):
    if not condition:
        raise SecretRefused(reason)


def migration_rows(source):
    """Translate admitted names-only source evidence, never infer live presence."""
    require(source.get('schema') == 'professor-stage5-provider-dependencies-v2'
            and source.get('values_included') is False, 'migration_source_scope_invalid')
    result = []
    proof = source.get('accepted_required_credential_evidence', {})
    verified = proof.get('verified_secret_files', [])
    accepted = (proof.get('status') == 'PASS_ACCEPTED_RECEIPT' and isinstance(verified, list)
                and all(isinstance(n, str) for n in verified) and set(verified) == set(ACTIVE.values()))
    conflicted = set(source.get('missing_required_credentials', [])) | set(source.get('unverified_current_profile_credentials', []))
    for row in source['dependencies']:
        name = row['name']; require(isinstance(name, str) and NAME.fullmatch(name), 'migration_name_invalid')
        original = row['classification']; presence = row.get('professor_secret_presence')
        require(not (name in conflicted and presence == 'PRESENT_ACCEPTED_RECEIPT'), 'migration_evidence_contradiction')
        if accepted and ((name in ACTIVE and presence == 'PRESENT_ACCEPTED_RECEIPT'
                          and ACTIVE[name] in verified) or name in AUTH_METADATA):
            category = 'ALREADY_ON_PROFESSOR_SERVER'
        elif original == 'VERCEL_BROWSER_PUBLIC':
            category = 'BROWSER_PUBLIC_ON_VERCEL'
        elif original == 'PROFESSOR_SERVER_OPTIONAL':
            category = 'OPTIONAL_NOT_ENABLED'
        elif original == 'LEGACY_CLOUD_ONLY':
            category = 'LEGACY_CLOUD_ONLY'
        elif (original == 'MISSING_REQUIRED' and presence == 'MISSING_REQUIRED'
              and row.get('required_for_production') == 'YES' and row.get('side') == 'backend'):
            category = 'MISSING_REQUIRED'
        else:
            category = 'UNKNOWN_LIVE_METADATA'
        result.append({k: row.get(k) for k in ('name', 'provider', 'side', 'identifier_kind',
            'required_for_production', 'current_location', 'target_location', 'secret_file')}
            | {'migration_class': category, 'presence_evidence': presence,
               'activation_performed': False, 'retirement_approved': False})
    require(len({r['name'] for r in result}) == len(result), 'migration_name_duplicate')
    try:
        SecretScanner(()).check_bytes(json.dumps(result).encode())
    except ScanRefused:
        raise SecretRefused('migration_credential_literal_forbidden') from None
    return result


def validate_plan(plan):
    require(isinstance(plan, dict) and set(plan) == {'schema', 'values_included', 'operation', 'required'}, 'install_plan_fields_invalid')
    require(plan['schema'] == 'professor-provider-install-plan-v1'
            and plan['values_included'] is False and plan['operation'] == 'store_only', 'install_plan_scope_invalid')
    entries = plan['required']
    require(isinstance(entries, list) and len(entries) <= 64, 'install_plan_population_invalid')
    seen = set()
    for row in entries:
        require(isinstance(row, dict) and set(row) == {'name', 'classification', 'required_consumer_approved', 'absence_confirmed', 'input_mode'}, 'install_entry_fields_invalid')
        name = row['name']
        require(isinstance(name, str) and NAME.fullmatch(name) and name not in seen, 'install_name_invalid')
        spec = stage2.credential_spec(name)
        require(spec.get('side') == 'backend' and not name.startswith('NEXT_PUBLIC_'), 'server_credential_required')
        require(row['classification'] == 'MISSING_REQUIRED' and row['required_consumer_approved'] is True
                and row['absence_confirmed'] is True, 'required_absence_not_approved')
        require(row['input_mode'] in {'hidden', 'protected_file'}, 'install_input_mode_invalid')
        require(name not in ACTIVE or row['input_mode'] == 'protected_file', 'core_protected_recovery_required')
        require(spec['classification'] != 'credential_file' or row['input_mode'] == 'protected_file', 'protected_import_file_required')
        seen.add(name)
    return entries


def load_plan():
    info = PLAN.lstat()
    require(stat.S_ISREG(info.st_mode) and not PLAN.is_symlink() and info.st_size <= 65536, 'install_plan_file_invalid')
    return validate_plan(json.loads(PLAN.read_text()))


def install(entries, sources, stored):
    """Called only by the operator; reuse Stage2 storage and input boundaries."""
    require(os.geteuid() == 0, 'operator_root_required')
    stage2.storage_boundary()
    stage2.ensure_private(stage2.STORE)
    parent = stage2.open_directory(stage2.STORE, private=True)
    values = {}
    try:
        # Validate the entire target population before asking for values.
        for row in entries:
            filename = stage2.credential_spec(row['name'])['secret_file']
            try:
                os.stat(filename, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise SecretRefused('existing_credential_will_not_be_replaced')
        # Validate every supplied value before writing any credential.
        for row in entries:
            name = row['name']; spec = stage2.credential_spec(name)
            value = (stage2.import_file(sources[name], multiline=spec['classification'] == 'credential_file')
                     if row['input_mode'] == 'protected_file'
                     else stage2.hidden_input('Enter ' + name + ' (hidden): '))
            values[name] = stage2.validate_credential(spec['secret_file'], value)
        for row in entries:
            name = row['name']; filename = stage2.credential_spec(name)['secret_file']
            stage2.put_credential(filename, values[name], replace=False)
            stored.append(name)
    finally:
        values.clear()
        os.close(parent)


def main(argv=None):
    stored = []
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); os.umask(0o077)
        parser = stage2.SafeParser(description=__doc__)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--plan', action='store_true')
        group.add_argument('--install-required', action='store_true')
        group.add_argument('--migration-plan', action='store_true')
        group.add_argument('--migrate-all', action='store_true')
        group.add_argument('--stage-stored-providers', action='store_true')
        providers=('google','tgos','tdx','r2','openai','earth-engine')
        group.add_argument('--provider',choices=providers)
        group.add_argument('--stage-provider',choices=providers)
        parser.add_argument('--from-file', action='append', default=[], metavar='NAME=PROTECTED_PATH')
        args = parser.parse_args(argv)
        if args.stage_stored_providers or args.stage_provider:
            require(not args.from_file,'restore_does_not_accept_imports')
            from scripts.ops.professor_provider_storage import stage_stored_providers
            print(json.dumps(stage_stored_providers(args.stage_provider) if args.stage_provider else stage_stored_providers()));return 0
        if args.provider:
            from scripts.ops.professor_provider_storage import GROUPS,provider_groups,migrate_provider
            names={name for group in provider_groups(args.provider) for name in GROUPS[group]}
            sources={}
            for item in args.from_file:
                name,separator,path=item.partition('=')
                require(separator and name in names and name not in sources,'provider_import_name_invalid')
                sources[name]=Path(path)
            ok,evidence=migrate_provider(args.provider,sources)
            print(json.dumps({'status':'PASS_MIGRATED_PROVIDER_DISABLED' if ok else 'REFUSED','provider':args.provider,
                              'evidence':str(evidence),'activation_performed':False,'credential_values_returned':False}))
            return 0 if ok else 1
        if args.migrate_all or args.migration_plan:
            from scripts.ops.professor_provider_storage import ALL, SECRETS, migrate_all
            sources={}
            for item in args.from_file:
                name,separator,path=item.partition('=')
                require(separator and name in ALL and name not in sources,'provider_import_name_invalid')
                sources[name]=Path(path)
            if args.migration_plan:
                require(not sources,'plan_does_not_accept_imports')
                print(json.dumps({'status':'REQUIRED_PROVIDER_STORAGE_PLAN','required_secret_names':list(SECRETS),
                                  'required_config_names':[n for n in ALL if n not in SECRETS],
                                  'activation_performed':False,'credential_values_returned':False}));return 0
            ok,evidence=migrate_all(sources)
            print(json.dumps({'status':'PASS_MIGRATED_PROVIDERS_DISABLED' if ok else 'REFUSED',
                              'evidence':str(evidence),'activation_performed':False,'credential_values_returned':False}))
            return 0 if ok else 1
        entries = load_plan()
        sources = {}
        for item in args.from_file:
            name, separator, path = item.partition('=')
            require(separator and name in {r['name'] for r in entries} and name not in sources, 'import_name_invalid')
            sources[name] = Path(path)
        file_names = {r['name'] for r in entries if r['input_mode'] == 'protected_file'}
        if args.plan:
            require(not sources, 'plan_does_not_accept_imports')
        else:
            require(set(sources) == file_names, 'protected_import_population_invalid')
            if entries:
                install(entries, sources, stored)
        result = {'status': 'PLAN_ONLY' if args.plan else 'STORED_NOT_ACTIVE' if entries else 'NO_INSTALLATION_REQUIRED',
                  'scope':'legacy_missing_core_plan_only_not_required_provider_migration',
                  'required_names': [r['name'] for r in entries], 'stored_names': stored,
                  'activation_performed': False, 'runtime_files_changed': False, 'credential_values_returned': False}
        print(json.dumps(result)); return 0
    except (Exception, KeyboardInterrupt) as error:
        reason = str(error) if isinstance(error, SecretRefused) and re.fullmatch('[a-z0-9_]+', str(error)) else 'operation_failed_details_suppressed'
        print(json.dumps({'status': 'REFUSED', 'reason_code': reason, 'stored_names': stored,
                          'activation_performed': False, 'credential_values_returned': False})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
