"""Local-only PG17 rehearsal with fresh containers and blocked external I/O.

No caller-supplied database URLs are used. Docker must already be available.
The pinned image must already exist locally; this script never pulls an image.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'postgres@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193'
FOCUSED = [
    'tests/test_usage_durable_guard.py','tests/test_api_usage_quota.py',
    'tests/test_api_usage_ledger.py','tests/test_usage_guard_postgres.py',
    'tests/test_apply_production_migrations.py','tests/test_pytest_database_safety.py',
]


def clean_environment():
    # Do not even copy inherited database/credential values into child tools.
    return {key:value for key,value in os.environ.items() if not (
        key.endswith(('_URL','_DSN')) or key.startswith(('PG','POSTGRES_','DOCKER_','USAGE_BOOTSTRAP_','API_USAGE_'))
        or any(part in key for part in ('PASSWORD','SECRET','TOKEN','API_KEY','HMAC_KEY'))
    )}


def local_docker_prefix(environment):
    """Inspect context metadata only, then pin every daemon call to local IPC."""
    endpoint = os.getenv('DOCKER_HOST','').strip()
    if not endpoint:
        command = ['docker','context','inspect','--format','{{.Endpoints.docker.Host}}']
        context = os.getenv('DOCKER_CONTEXT','').strip()
        if context:
            if not context.replace('-','').replace('_','').replace('.','').isalnum():
                raise RuntimeError('local_docker_endpoint_required')
            command.append(context)
        endpoint = subprocess.run(command,env=environment,text=True,capture_output=True,check=True).stdout.strip()
    if not (endpoint.startswith('unix:///') or endpoint in (
        'npipe:////./pipe/docker_engine','npipe:////./pipe/dockerDesktopLinuxEngine',
    )):
        raise RuntimeError('local_docker_endpoint_required')
    return ['docker','--host',endpoint]


def _worker(suite, port):
    sys.path.insert(0,str(ROOT))
    # conftest also strips application DB URLs. This boundary additionally
    # blocks libpq (which bypasses Python sockets) and ordinary network clients.
    import psycopg
    original_connect = psycopg.connect
    def validate_connection(conninfo, kwargs):
        from psycopg.conninfo import conninfo_to_dict
        info = conninfo_to_dict(conninfo, **{k:v for k,v in kwargs.items() if k in ('host','hostaddr','port','dbname','user')})
        if info.get('host')!='127.0.0.1' or info.get('hostaddr','127.0.0.1')!='127.0.0.1' or str(info.get('port'))!=str(port):
            raise RuntimeError('Rehearsal blocked a non-disposable PostgreSQL connection')
        allowed = ('usage_bootstrap_control',) if suite=='bootstrap' else ('api_usage_test_regression',)
        if info.get('dbname') not in allowed and not (suite=='bootstrap' and info.get('dbname','').startswith('api_usage_test_bootstrap_')):
            raise RuntimeError('Rehearsal blocked a non-disposable database name')
    def local_connect(conninfo='', **kwargs):
        validate_connection(conninfo,kwargs)
        return original_connect(conninfo, **kwargs)
    psycopg.connect = local_connect
    original_async_connect = psycopg.AsyncConnection.connect
    async def local_async_connect(conninfo='', **kwargs):
        validate_connection(conninfo,kwargs)
        return await original_async_connect(conninfo, **kwargs)
    psycopg.AsyncConnection.connect = local_async_connect
    original_socket_connect = socket.socket.connect
    original_socket_connect_ex = socket.socket.connect_ex
    def is_loopback(address):
        if not isinstance(address,tuple):
            return True  # Local Unix sockets / Windows AF_UNIX.
        host = str(address[0])
        if host=='localhost':
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False
    def local_socket_connect(sock,address):
        if not is_loopback(address):
            raise ConnectionRefusedError('Rehearsal blocked external network access')
        return original_socket_connect(sock,address)
    def local_socket_connect_ex(sock,address):
        if not is_loopback(address):
            raise ConnectionRefusedError('Rehearsal blocked external network access')
        return original_socket_connect_ex(sock,address)
    socket.socket.connect = local_socket_connect
    socket.socket.connect_ex = local_socket_connect_ex
    import pytest
    paths = ['tests/test_usage_database_bootstrap.py'] if suite=='bootstrap' else FOCUSED if suite=='regression' else []
    return pytest.main(['-q','--tb=short',*paths])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=('bootstrap','regression','all'),default='bootstrap')
    parser.add_argument('--worker',type=int,help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker is not None:
        return _worker(args.suite,args.worker)
    environment = clean_environment()
    name = 'proptech-usage-rehearsal-' + uuid4().hex[:12]
    started = False
    try:
        prefix = local_docker_prefix(environment)
        def docker(*command):
            return subprocess.run([*prefix,*command],cwd=ROOT,env=environment,text=True,capture_output=True,check=True).stdout.strip()
        docker('image','inspect',IMAGE,'--format','{{.Id}}')
        docker('run','--detach','--pull=never','--name',name,'--publish','127.0.0.1::5432',
               '--env','POSTGRES_HOST_AUTH_METHOD=trust','--env','POSTGRES_DB=usage_bootstrap_control',
               '--tmpfs','/var/lib/postgresql/data',IMAGE)
        started = True
        port = int(docker('port',name,'5432/tcp').rsplit(':',1)[1])
        for _ in range(60):
            ready = subprocess.run([*prefix,'exec',name,'pg_isready','-U','postgres','-d','usage_bootstrap_control'],env=environment,capture_output=True)
            if ready.returncode==0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('Disposable PostgreSQL did not become ready')
        print('Disposable '+docker('exec',name,'postgres','--version'),flush=True)
        if args.suite=='bootstrap':
            environment.update(USAGE_BOOTSTRAP_DISPOSABLE='1',USAGE_BOOTSTRAP_TEST_PORT=str(port))
        elif args.suite=='regression':
            docker('exec',name,'createdb','-U','postgres','api_usage_test_regression')
            environment.update(API_USAGE_TEST_DISPOSABLE='1',API_USAGE_TEST_POSTGRES_URL=f'postgresql://postgres@127.0.0.1:{port}/api_usage_test_regression')
        process = subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--suite',args.suite,'--worker',str(port)],cwd=ROOT,env=environment)
        return process.returncode
    except Exception:
        print('STOP: local rehearsal infrastructure failed; details suppressed')
        return 1
    finally:
        if started:
            # Exact UUID container created by this invocation only; no volumes
            # or caller-supplied container names can be removed.
            subprocess.run([*prefix,'rm','--force',name],env=environment,capture_output=True,check=True)


if __name__=='__main__':
    raise SystemExit(main())
