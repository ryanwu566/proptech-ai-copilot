#!/usr/bin/env python3
"""Loopback-only local ML companion. Healthy port 8080 need not be restarted."""
import os
import json
import socket
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes_valuation_ml import router
from backend.api.ingress_middleware import IngressMiddleware
from backend.api.abuse_middleware import AbuseMiddleware

def health():
    return {'status':'ok','capability':'valuation-ml','model_dependency':'independent'}


def create_app():
    from services.professor_ingress import origin
    origins=[]
    try:
        for item in os.getenv('CORS_ALLOWED_ORIGINS','').split(','):
            value=item.strip()
            if not value:continue
            try:origin(value)
            except ValueError:origin(value,development=True)
            if value not in origins:origins.append(value)
    except ValueError:raise RuntimeError('ml_cors_configuration_invalid') from None
    result=FastAPI(title='Local PLVR gross-transfer ML',docs_url='/docs',redoc_url=None)
    result.add_middleware(AbuseMiddleware)
    result.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,
        allow_methods=['GET','POST','OPTIONS'],
        allow_headers=['Content-Type','Accept','Authorization','X-Correlation-ID'],
        expose_headers=['X-Correlation-ID','Retry-After'])
    result.add_middleware(IngressMiddleware)
    result.include_router(router)
    result.add_api_route('/health',health,methods=['GET'])
    return result


app=create_app()


def _duplicate_socket(fd):
    os.set_inheritable(fd,False)
    duplicate=os.dup(fd)
    try:return socket.socket(fileno=duplicate)
    except BaseException:
        os.close(duplicate)
        raise


def inherited_sockets(environ=None):
    """Admit only the fixed systemd loopback+Unix pair, never arbitrary FDs."""
    env=os.environ if environ is None else environ
    if 'LISTEN_PID' not in env and 'LISTEN_FDS' not in env:return None
    handles=[]
    try:
        if env.get('LISTEN_PID')!=str(os.getpid()) or env.get('LISTEN_FDS')!='2':raise ValueError()
        for fd in (3,4):handles.append(_duplicate_socket(fd))
        families=set()
        for handle in handles:
            if handle.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_STREAM or not handle.getsockopt(socket.SOL_SOCKET,socket.SO_ACCEPTCONN):raise ValueError()
            families.add(handle.family)
            name=handle.getsockname()
            if handle.family==socket.AF_INET:
                if name!=('127.0.0.1',8081):raise ValueError()
            elif handle.family==socket.AF_UNIX:
                if name!='/run/proptech-ml/inference.sock':raise ValueError()
            else:raise ValueError()
        if families!={socket.AF_INET,socket.AF_UNIX}:raise ValueError()
        return handles
    except Exception:
        for handle in handles:handle.close()
        raise ValueError('ml_socket_activation_invalid') from None


def main():
    import uvicorn
    try:handles=inherited_sockets()
    except ValueError:
        print(json.dumps({'status':'REFUSED','reason_code':'ml_socket_activation_invalid'}));return 1
    if handles is None:
        uvicorn.run(app,host='127.0.0.1',port=8081,workers=1,proxy_headers=False,limit_concurrency=8,access_log=False)
    else:
        try:
            config=uvicorn.Config(app,workers=1,proxy_headers=False,limit_concurrency=8,access_log=False)
            uvicorn.Server(config).run(sockets=handles)
        finally:
            for handle in handles:handle.close()
    return 0


if __name__=='__main__':raise SystemExit(main())
