"""Synthetic archive diagnostics only; no Docker, root or credential files."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest
from services.professor_activation_scan import SecretScanner
from tests.test_professor_activation_scan import attested_image,docker_image,oci_image,tar_bytes

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'scripts/ops/professor_stage2_image_diagnose.py'


def module():
    spec=importlib.util.spec_from_file_location('image_diagnose',PATH)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def unsupported_media_archive():
    with tarfile.open(fileobj=io.BytesIO(oci_image(tar_bytes([('public',b'public')])))) as src:
        entries={m.name:src.extractfile(m).read() for m in src}
    for name,body in list(entries.items()):
        try:value=json.loads(body)
        except (ValueError,UnicodeDecodeError):continue
        if isinstance(value,dict) and 'layers' in value:
            value['layers'][0]['mediaType']='application/x-unsupported-layer'
            body=json.dumps(value).encode();digest=hashlib.sha256(body).hexdigest()
            del entries[name];entries['blobs/sha256/'+digest]=body
            index=json.loads(entries['index.json'])
            index['manifests'][0].update(digest='sha256:'+digest,size=len(body))
            entries['index.json']=json.dumps(index).encode();break
    return tar_bytes(list(entries.items()))


def test_valid_archive_scan_remains_pass_and_trace_is_restored():
    before=sys.gettrace()
    data=module().diagnose_stream(SecretScanner([]),io.BytesIO(docker_image([tar_bytes([('public',b'hello')])])))
    assert data['status']=='PASS' and data['scan']['layers']==1
    assert sys.gettrace() is before


def test_supported_existing_host_attestation_format_remains_fully_scanned():
    data=module().diagnose_stream(SecretScanner([]),io.BytesIO(attested_image()))
    assert data['status']=='PASS' and data['image_archive_verification_complete'] is True
    assert data['scan']['format']=='docker_oci' and data['scan']['images']==1


def test_operator_rescan_is_pinned_to_the_reviewed_verifier():
    m=module()
    assert m.SCANNER_SHA256==hashlib.sha256(m.SCANNER_PATH.read_bytes()).hexdigest()
    assert m.EXPECTED_IMAGE_ID=='sha256:c06a1e4123743041cb31c4c12bdd87e1e0165c6303baefd3d3c6103a62445615'


def test_unsupported_media_reports_exact_source_branch_without_archive_contents():
    data=module().diagnose_stream(SecretScanner([]),io.BytesIO(unsupported_media_archive()))
    assert data['status']=='REJECTED' and data['reason_code']=='archive_unsupported'
    assert data['origin']['function']=='descriptor'
    assert data['origin']['media_type']=='application/x-unsupported-layer'
    assert data['origin']['descriptor_role']=='layer'
    assert data['origin']['line']>0
    assert data['structural_summary']['layer_records']==1
    assert 'application/x-unsupported-layer' in data['structural_summary']['media_types']
    assert 'contents' not in data


def test_known_secret_never_exposes_content_or_filename():
    secret='synthetic-private-material-abcdef0123456789'
    archive=docker_image([tar_bytes([('file-'+secret,secret.encode())])])
    data=module().diagnose_stream(SecretScanner([secret]),io.BytesIO(archive))
    assert data['reason_code']=='credential_detected'
    assert data['status']=='REJECTED'
    assert secret not in json.dumps(data)
    assert 'structural_summary' not in data


def test_structural_metadata_filters_env_labels_and_untrusted_fields():
    records={'opaque':{'kind':'json','json':{'mediaType':'application/example',
        'config':{'Env':['CANARY=do-not-return'],'Labels':{'private':'do-not-return'}},
        'predicate':{'private':'do-not-return'},'annotations':{'vnd.docker.reference.type':'attestation-manifest'}}}}
    data=module().metadata_summary(records,SecretScanner([]))
    assert data['attestation_markers']==1
    assert 'do-not-return' not in json.dumps(data)
    assert data['media_types']=={'application/example':1}


def test_media_type_that_contains_known_value_is_redacted():
    key='synthetic-client-material-0123456789'
    records={'a':{'kind':'json','json':{'mediaType':'application/'+key}}}
    data=module().metadata_summary(records,SecretScanner([key]))
    assert key not in json.dumps(data)


def test_sparse_extension_reports_only_fixed_feature():
    body=io.BytesIO()
    with tarfile.open(fileobj=body,mode='w',format=tarfile.PAX_FORMAT) as archive:
        member=tarfile.TarInfo('public');member.size=1;member.pax_headers={'GNU.sparse.major':'1'}
        archive.addfile(member,io.BytesIO(b'x'))
    data=module().diagnose_stream(SecretScanner([]),io.BytesIO(docker_image([body.getvalue()])))
    assert data['reason_code']=='archive_unsupported'
    assert data['origin']['function']=='_pax' and data['origin']['sparse_extension_seen'] is True


def test_readonly_tool_has_no_activation_or_container_mutation_path():
    source=PATH.read_text();ast.parse(source)
    assert 'professor_stage2_activation' not in source
    assert "'build'" not in source and "'pull'" not in source and "'stop'" not in source
    assert 'force-recreate' not in source


def test_missing_compression_parent_is_reported_not_raised(monkeypatch):
    m=module()
    def missing(name):raise ModuleNotFoundError('synthetic missing optional package')
    monkeypatch.setattr(m.importlib.util,'find_spec',missing)
    assert m.module_available('compression.zstd') is False
