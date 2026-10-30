"""Descriptor validation only. No real TCP sockets or runtime process changes."""
import importlib
import os
import socket

import pytest


def module():
    return importlib.import_module('scripts.ops.serve_valuation_ml')


def test_manual_mode_still_uses_loopback_and_does_not_inspect_fds():
    m=module()
    assert hasattr(m,'inherited_sockets'), 'systemd descriptor validation is missing'
    assert m.inherited_sockets({}) is None


class Handle:
    def __init__(self,family,name,listening=True):
        self.family=family;self.name=name;self.listening=listening;self.closed=False
    def getsockopt(self,level,option):return socket.SOCK_STREAM if option==socket.SO_TYPE else int(self.listening)
    def getsockname(self):return self.name
    def close(self):self.closed=True


def descriptors(monkeypatch,handles):
    m=module()
    monkeypatch.setattr(m,'_duplicate_socket',lambda fd:handles[fd-3])
    return m


def test_exact_private_pair_is_accepted(monkeypatch):
    handles=[Handle(socket.AF_INET,('127.0.0.1',8081)),Handle(socket.AF_UNIX,'/run/proptech-ml/inference.sock')]
    m=descriptors(monkeypatch,handles)
    assert m.inherited_sockets({'LISTEN_PID':str(os.getpid()),'LISTEN_FDS':'2'})==handles


@pytest.mark.parametrize('kind',['wildcard','wrong_port','wrong_unix','not_listening','duplicate_inet'])
def test_foreign_sockets_fail_closed_and_close_duplicates(monkeypatch,kind):
    handles=[Handle(socket.AF_INET,('127.0.0.1',8081)),Handle(socket.AF_UNIX,'/run/proptech-ml/inference.sock')]
    if kind=='wildcard':handles[0].name=('0.0.0.0',8081)
    if kind=='wrong_port':handles[0].name=('127.0.0.1',5432)
    if kind=='wrong_unix':handles[1].name='/tmp/other.sock'
    if kind=='not_listening':handles[0].listening=False
    if kind=='duplicate_inet':handles[1]=Handle(socket.AF_INET,('127.0.0.1',8081))
    m=descriptors(monkeypatch,handles)
    with pytest.raises(ValueError):m.inherited_sockets({'LISTEN_PID':str(os.getpid()),'LISTEN_FDS':'2'})
    assert all(h.closed for h in handles)


@pytest.mark.parametrize('env',[{'LISTEN_PID':'1','LISTEN_FDS':'2'},{'LISTEN_PID':str(os.getpid()),'LISTEN_FDS':'1'},{'LISTEN_FDS':'2'},{'LISTEN_PID':str(os.getpid())},{'LISTEN_PID':'invalid','LISTEN_FDS':'2'}])
def test_invalid_activation_metadata_never_falls_back_to_tcp(env):
    with pytest.raises(ValueError):module().inherited_sockets(env)


def test_partly_duplicated_pair_is_closed_on_second_fd_failure(monkeypatch):
    first=Handle(socket.AF_INET,('127.0.0.1',8081));m=module()
    def duplicate(fd):
        if fd==3:return first
        raise OSError('synthetic invalid descriptor')
    monkeypatch.setattr(m,'_duplicate_socket',duplicate)
    with pytest.raises(ValueError):m.inherited_sockets({'LISTEN_PID':str(os.getpid()),'LISTEN_FDS':'2'})
    assert first.closed


def test_browser_ml_uses_exact_origin_without_cookie_credentials(monkeypatch):
    from fastapi.testclient import TestClient
    m=module()
    assert hasattr(m,'create_app'),'companion CORS application factory missing'
    monkeypatch.setenv('CORS_ALLOWED_ORIGINS','https://proptech-ai-copilot.vercel.app')
    monkeypatch.setenv('APP_ENV','development')
    client=TestClient(m.create_app())
    allowed='https://proptech-ai-copilot.vercel.app'
    preflight=client.options('/valuation/ml/v1/estimate',headers={'Origin':allowed,
        'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type,authorization'})
    assert preflight.status_code==200
    assert preflight.headers['access-control-allow-origin']==allowed
    assert 'access-control-allow-credentials' not in preflight.headers
    status=client.get('/health',headers={'Origin':allowed})
    assert status.headers['access-control-allow-origin']==allowed
    denied=client.options('/valuation/ml/v1/estimate',headers={'Origin':'https://evil.example',
        'Access-Control-Request-Method':'POST'})
    assert denied.status_code==400 and 'access-control-allow-origin' not in denied.headers


@pytest.mark.parametrize('origin',['*','https://*.vercel.app','https://example.com/path'])
def test_invalid_companion_cors_configuration_fails_closed(monkeypatch,origin):
    m=module();assert hasattr(m,'create_app')
    monkeypatch.setenv('CORS_ALLOWED_ORIGINS',origin)
    with pytest.raises(RuntimeError):m.create_app()
