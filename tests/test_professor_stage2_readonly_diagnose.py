"""Synthetic-only diagnosis tests. Never access Docker, credentials, or live DBs."""
import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.test_professor_stage2_probe import FakeDB, KNOWN_FACT_SHA256

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'scripts/ops/professor_stage2_readonly_diagnose.py'


def module():
    spec=importlib.util.spec_from_file_location('readonly_diagnose',PATH)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def payload_namespace():
    source=module().database_payload((ROOT/'scripts/ops/professor_stage2_probe.py').read_bytes())
    ast.parse(source)
    namespace={'__name__':'synthetic_diagnostic'}
    exec(compile(source,'<synthetic-probe>','exec'),namespace)
    return namespace


def collect(ns,changes=None,connect_error=None):
    def connect(kind,**options):
        assert options['sslmode']=='verify-full'
        assert 'default_transaction_read_only=on' in options['options']
        if connect_error:raise connect_error
        return FakeDB(kind,changes)
    return ns['_collect_diagnostic'](connect=connect,reader=lambda p:p.name.removesuffix('_database_url'),
        regions=tuple(f'r{i}' for i in range(368)),hasher=lambda r:KNOWN_FACT_SHA256)


def test_generated_payload_does_not_run_original_cli_or_activate_anything():
    source=module().database_payload((ROOT/'scripts/ops/professor_stage2_probe.py').read_bytes())
    assert 'raise SystemExit(main())' not in source
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and 'subprocess' in ast.unparse(n) for n in ast.walk(ast.parse(source)))
    assert 'probe_databases(connect=' in source


def test_success_keeps_all_readonly_security_checks_and_never_returns_raw_facts():
    ns=payload_namespace();data=collect(ns)
    assert data['database_contract_status']=='PASS'
    assert data['collection_status']=='COLLECTED'
    assert not any(row.get('failure') for row in data['databases'].values())
    raw=json.dumps(data)
    assert 'canary-private' not in raw
    assert data['read_only'] and data['credential_values_returned'] is False


def test_failed_gate_and_changed_fields_are_identified_without_raw_values():
    data=collect(payload_namespace(),{'population':(451744,451672,72,0,1,1,117986,0,1,True,True)})
    assert data['database_contract_status']=='BLOCKED'
    failure=data['databases']['valuation']['failure']
    assert failure['gate']=='population'
    assert failure['mismatched_fields']==['known_serving_rows']
    assert 'canary-private' not in json.dumps(data)


def test_permissions_failure_names_only_fixed_serving_object():
    data=collect(payload_namespace(),{'permissions':(True,True,False,False,False,False,False)})
    assert data['databases']['app']['failure']['gate']=='permissions.public.ris_village_demographics'


def test_sqlstate_and_exception_category_are_sanitized():
    class OperationalError(Exception):
        sqlstate='28000'
    data=collect(payload_namespace(),connect_error=OperationalError('postgres://canary-password@private-host/db'))
    failure=data['databases']['app']['failure']
    assert failure=={'gate':'tls_connect','category':'OperationalError','sqlstate':'28000'}
    assert 'canary-password' not in json.dumps(data)


def test_query_exception_records_fixed_gate_not_exception_message():
    ns=payload_namespace()
    class ProgrammingError(Exception):sqlstate='42883'
    class Broken(FakeDB):
        def execute(self,sql,params=None):
            if '/* escalation */' in sql:raise ProgrammingError('private SQL and credentials')
            return super().execute(sql,params)
    data=ns['_collect_diagnostic'](connect=lambda kind,**kw:Broken(kind),reader=lambda p:p.name.removesuffix('_database_url'),
        regions=tuple(f'r{i}' for i in range(368)),hasher=lambda r:KNOWN_FACT_SHA256)
    assert data['databases']['usage']['failure']=={'gate':'escalation','category':'ProgrammingError','sqlstate':'42883'}
    assert 'private SQL' not in json.dumps(data)


def test_altered_probe_source_is_refused():
    m=module()
    with pytest.raises(m.DiagnosticRefused):m.database_payload(b'print("unreviewed")')


def test_no_activation_or_configuration_mutation_commands_exist():
    source=PATH.read_text()
    ast.parse(source)
    assert 'force-recreate' not in source and "'up'" not in source and "'stop'" not in source
    assert 'compose.env' not in source and 'runtime.env' not in source
    assert "'/dev/sda'" in source


def test_failed_aggregate_security_predicates_expose_only_fixed_boolean_conditions():
    for tag,kind in [('escalation','app'),('usage','usage')]:
        data=collect(payload_namespace(),{tag:((True,) if tag=='escalation' else (False,))})
        detail=data['databases'][kind]
        assert detail['failure']['gate']==tag
        assert detail['condition_details_complete']
        assert len(detail['failed_conditions'])==(8 if tag=='escalation' else 6)
        assert 'canary-private' not in json.dumps(detail)


def test_partial_coverage_is_not_reported_as_failed_when_another_field_drifts():
    data=collect(payload_namespace(),{'coverage':(322,7500,0,0,368,0,False)})
    assert data['databases']['valuation']['failure']['mismatched_fields']==['metadata_consistency']
