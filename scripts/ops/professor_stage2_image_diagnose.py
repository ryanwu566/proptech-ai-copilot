#!/usr/bin/env python3
"""Operator-only READ-ONLY diagnosis of the existing candidate image scan.

No image build/pull, deployment, provider operation, credential modification, or
container lifecycle action. No image archive/config/history is saved or echoed.
Only sanitized source locations, format metadata and current state are published.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import select
import subprocess
import sys
import tempfile
import time

REPO=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(REPO))
from services import professor_activation_scan as scan_module
from services.professor_activation_scan import ScanRefused,SecretScanner
from services.selfhost_secret_files import open_directory,read_secret

RUN_ID='20261029T104746Z-2993da4548b9'
RECEIPT=Path('/tmp/professor-stage2-activation-986412c2c9a24bf4b4508bc1e054fc79')
IMAGE='proptech-professor-api:stage2-'+RUN_ID.lower()
EXPECTED_IMAGE_ID='sha256:c06a1e4123743041cb31c4c12bdd87e1e0165c6303baefd3d3c6103a62445615'
SCANNER_PATH=Path(scan_module.__file__).resolve()
SCANNER_SHA256='bb8e65842e898d3d5de1189a08a0b9e5312024bb8134d8de894db52e78c1c2b8'


class DiagnosticRefused(Exception):
    pass


def module_available(name):
    try:return importlib.util.find_spec(name) is not None
    except (ImportError,ValueError):return False


def safe_media(value,scanner):
    if not isinstance(value,str) or not re.fullmatch(r'application/[A-Za-z0-9.+/_-]{1,180}',value):
        return '<nonstandard-media-type>'
    try:scanner.check_bytes(value.encode())
    except ScanRefused:return '<redacted>'
    return value


def metadata_summary(records,scanner):
    """Select format fields only, never config Env/Labels or attestation bodies."""
    counts=Counter();media=Counter();attestations=0;visited=0
    def inspect(value):
        nonlocal attestations,visited
        visited+=1
        if visited>20000:raise DiagnosticRefused('metadata_summary_limit')
        if isinstance(value,list):
            for child in value:inspect(child)
        elif isinstance(value,dict):
            if 'mediaType' in value:media[safe_media(value['mediaType'],scanner)]+=1
            annotations=value.get('annotations')
            if isinstance(annotations,dict) and annotations.get('vnd.docker.reference.type')=='attestation-manifest':attestations+=1
            for key in ('config','layers','manifests'):
                child=value.get(key)
                if isinstance(child,(dict,list)):inspect(child)
    for record in records.values():
        if not isinstance(record,dict):continue
        kind=record.get('kind')
        counts[kind if kind in {'layer','json','aux'} else 'other']+=1
        if kind=='json':inspect(record.get('json'))
    return {'archive_records':len(records),'layer_records':counts['layer'],'json_records':counts['json'],
        'media_types':dict(media),'attestation_markers':attestations,
        'docker_manifest_present':'manifest.json' in records,'oci_index_present':'index.json' in records,
        'oci_layout_present':'oci-layout' in records}


def diagnose_stream(scanner,stream):
    """Run the unchanged verifier and capture fixed metadata at its refusal site."""
    details={};old_trace=sys.gettrace()
    def trace(frame,event,arg):
        try:
            if event=='exception' and frame.f_code.co_filename==str(SCANNER_PATH) and isinstance(arg[1],ScanRefused):
                reason=arg[1].reason_code
                if 'origin' not in details:
                    origin={'source_file':'services/professor_activation_scan.py','function':frame.f_code.co_name,'line':frame.f_lineno}
                    if reason=='archive_unsupported':
                        local=frame.f_locals;name=frame.f_code.co_name
                        if name=='descriptor':
                            desc=local.get('desc',{})
                            origin['media_type']=safe_media(desc.get('mediaType'),scanner)
                            allowed=local.get('media')
                            origin['descriptor_role']=('layer' if allowed==scan_module._LAYER_MEDIA else
                                'config' if allowed in (scan_module._OCI_CONFIG,{scan_module._EMPTY_CONFIG}) else
                                'attestation_payload' if allowed=={scan_module._IN_TOTO} else 'index_or_manifest')
                            digest=desc.get('digest')
                            origin['sha256_descriptor']=isinstance(digest,str) and bool(re.fullmatch(r'sha256:[0-9a-f]{64}',digest))
                        elif name=='_pax':origin['sparse_extension_seen']='sparse' in str(local.get('key','')).lower()
                        elif name=='_tar':
                            kind=getattr(local.get('info'),'type',b'')
                            if isinstance(kind,bytes) and len(kind)==1:origin['tar_type_hex']=kind.hex()
                        elif name=='_decode':origin['compression']='zstd' if local.get('prefix',b'').startswith(b'\x28\xb5\x2f\xfd') else 'other'
                    details['origin']=origin
                if reason=='archive_unsupported' and 'structural_summary' not in details:
                    records=frame.f_locals.get('records')
                    if isinstance(records,dict):details['structural_summary']=metadata_summary(records,scanner)
        except BaseException:
            details['diagnostic_metadata_partial']=True
        return trace
    sys.settrace(trace)
    try:
        result=scanner.scan_image_archive(stream)
        return {'status':'PASS','scan':result,'image_archive_verification_complete':True}
    except ScanRefused as exc:
        # For a credential finding, never inspect or return surrounding data.
        if exc.reason_code=='credential_detected':details.pop('structural_summary',None)
        return {'status':'REJECTED','reason_code':exc.reason_code,'image_archive_verification_complete':False,**details}
    except BaseException:
        return {'status':'UNVERIFIED','reason_code':'diagnostic_scan_failed','image_archive_verification_complete':False}
    finally:sys.settrace(old_trace)


def installed_values():
    store=Path('/etc/proptech-selfhost/secrets');values=[]
    fd=open_directory(store,private=True)
    try:names=os.listdir(fd)
    finally:os.close(fd)
    for name in names:
        if name=='backups':
            folder=store/name;fd=open_directory(folder,private=True)
            try:backups=os.listdir(fd)
            finally:os.close(fd)
            values.extend(read_secret(folder,b,gid=0,mode=0o600,limit=1024*1024,multiline=True) for b in backups)
        else:values.append(read_secret(store,name,gid=0,mode=0o600,limit=1024*1024,multiline=True))
    return values


class TimedStream:
    def __init__(self,stream,timeout=1800):
        self.fd=stream.fileno();self.deadline=time.monotonic()+timeout;os.set_blocking(self.fd,False)
    def read(self,size=65536):
        while True:
            remaining=self.deadline-time.monotonic()
            if remaining<=0:raise DiagnosticRefused('image_export_timeout')
            ready,_,_=select.select([self.fd],[],[],min(remaining,1))
            if ready:return os.read(self.fd,min(max(size,1),65536))


INSPECT_TEMPLATE='''{"id":{{json .Id}},"image_id":{{json .Image}},"running":{{json .State.Running}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}}}'''


def main():
    if os.geteuid()!=0 or sys.argv[1:]:
        print('{"status":"REFUSED","reason_code":"operator_root_no_arguments_required"}');return 1
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    env={'PATH':os.defpath,'LANG':'C.UTF-8','DOCKER_HOST':'unix:///var/run/docker.sock'}
    def command(args,timeout=90):
        p=subprocess.run(args,capture_output=True,env=env,cwd=REPO,timeout=timeout)
        if p.returncode or len(p.stdout)>4*1024*1024:raise DiagnosticRefused('readonly_command_failed')
        return p.stdout
    def storage(path):
        raw=command(['findmnt','-rn','-o','SOURCE','--target',str(path)]).decode().strip().split('[',1)[0]
        if not raw or raw.startswith('/dev/sda') or raw.startswith('/dev/') and os.path.realpath(raw).startswith('/dev/sda'):
            raise DiagnosticRefused('forbidden_or_unknown_storage')
    try:
        if hashlib.sha256(SCANNER_PATH.read_bytes()).hexdigest()!=SCANNER_SHA256:raise DiagnosticRefused('scanner_source_changed')
        storage(Path('/tmp'))
        docker_root=json.loads(command(['docker','info','--format','{{json .DockerRootDir}}']))
        storage(Path(docker_root))
        for path in (Path('/var/lib/containerd'),Path('/run/containerd')):
            if path.exists():storage(path)
        scanner=SecretScanner(installed_values())
        selected=json.loads(command(['docker','image','inspect','--format','{"id":{{json .Id}},"layer_count":{{len .RootFS.Layers}},"architecture":{{json .Architecture}},"os":{{json .Os}}}',IMAGE]))
        image_id=selected['id']
        if image_id!=EXPECTED_IMAGE_ID:raise DiagnosticRefused('candidate_identity_changed')
        result={'schema':'professor-stage2-image-diagnosis-v1','checked_at':datetime.now(timezone.utc).isoformat(),
            'failed_run':RUN_ID,'image_tag':IMAGE,'image':selected,'scanner_sha256':SCANNER_SHA256,
            'python_version':list(sys.version_info[:3]),'stdlib_zstd_available':module_available('compression.zstd'),
            'optional_zstandard_available':module_available('zstandard'),
            'runtime_changes':False,'providers_enabled':False,'credentials_returned':False}
        process=subprocess.Popen(['docker','image','save',image_id],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env)
        try:
            result['archive_scan']=diagnose_stream(scanner,TimedStream(process.stdout))
            cancelled=result['archive_scan']['status']!='PASS' and process.poll() is None
            if cancelled:process.kill()
            result['export_exit_code']=process.wait(timeout=30)
            result['export_cancelled_after_refusal']=cancelled
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=10)
            process.stdout.close()
        for label,args in [('config',['docker','image','inspect',image_id]),
                           ('history',['docker','image','history','--no-trunc','--format','{{json .}}',image_id])]:
            try:scanner.check_bytes(command(args));result[label+'_credential_scan']='PASS'
            except ScanRefused as exc:result[label+'_credential_scan']=exc.reason_code
        before=json.loads((RECEIPT/'containers-before.json').read_text());containers={}
        for service in ('postgres_app','postgres_usage','api','reverse_proxy'):
            ids=command(['docker','ps','-aq','--no-trunc','--filter','label=com.docker.compose.project=proptech-selfhost',
                         '--filter','label=com.docker.compose.service='+service]).decode().split()
            if len(ids)!=1 or not re.fullmatch(r'[0-9a-f]{64}',ids[0]):raise DiagnosticRefused('current_container_identity_ambiguous')
            item=json.loads(command(['docker','inspect','--format',INSPECT_TEMPLATE,ids[0]]))
            item['same_container_as_before']=item['id']==before[service]['id']
            item['same_image_as_before']=item['image_id']==before[service]['image_id']
            if service.startswith('postgres_'):
                item['same_data_volume_as_before']=[m for m in item['mounts'] if m['Destination']=='/var/lib/postgresql/data']==before[service]['data_mount']
            containers[service]=item
        result['containers']=containers
        result['stage2_override_exists']=(Path('/etc/proptech-selfhost')/'stage2-secrets.override.yml').exists()
        # Scan the diagnostic too: no raw archive member, Env/Labels, match bytes,
        # exception text, credential value/hash, or image file contents are returned.
        raw=(json.dumps(result,indent=2)+'\n').encode();scanner.check_bytes(raw)
        folder=Path(tempfile.mkdtemp(prefix='professor-stage2-image-readonly-',dir='/tmp'))
        target=folder/'diagnosis.json'
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
        with os.fdopen(fd,'wb') as stream:stream.write(raw)
        os.chmod(target,0o644);os.chmod(folder,0o755)
        print(json.dumps({'status':'COLLECTED','archive_result':result['archive_scan']['status'],
            'sanitized_receipt':str(target),'runtime_changes':False}));return 0
    except BaseException:
        print('{"status":"REFUSED","reason_code":"image_diagnosis_failed_details_suppressed"}');return 1


if __name__=='__main__':raise SystemExit(main())
