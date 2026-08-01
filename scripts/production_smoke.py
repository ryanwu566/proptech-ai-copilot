"""Bounded local and hosted release smoke checks.

Hosted URLs are explicit inputs. The runner never prints URLs, headers, token
values, response bodies, or provider details. Local mode remains provider-free.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api_main import app
from fastapi.testclient import TestClient


def _safe_origin(value: str) -> str | None:
    from urllib.parse import urlsplit

    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _hosted_json(url: str, *, timeout: float, method: str = "GET", headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], dict[str, object] | None]:
    request = Request(url, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=max(1.0, min(float(timeout), 30.0))) as response:
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            if method == "OPTIONS":
                return response.status, response_headers, None
            body = response.read(256_000)
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            return response.status, response_headers, payload if isinstance(payload, dict) else None
    except Exception:
        return 0, {}, None


def _hosted_text(url: str, *, timeout: float) -> tuple[int, dict[str, str], str]:
    request = Request(url, method="GET", headers={"Accept": "text/html"})
    try:
        with urlopen(request, timeout=max(1.0, min(float(timeout), 30.0))) as response:
            body = response.read(256_000)
            return response.status, {key.lower(): value for key, value in response.headers.items()}, body.decode("utf-8", errors="replace")
    except Exception:
        return 0, {}, ""


def _local_run() -> dict[str, object]:
    checks: dict[str, str] = {}
    with TestClient(app) as client:
        for name, path in (("liveness", "/liveness"), ("health", "/health"), ("readiness", "/readiness"), ("release_version", "/release-version"), ("source_status", "/source-status"), ("compatibility", "/compatibility")):
            response = client.get(path)
            checks[name] = "pass" if response.status_code == 200 else "fail"
    return {"status": "pass" if all(value == "pass" for value in checks.values()) else "fail", "mode": "local", "checks": checks, "external_provider_called": False}


def run_hosted(*, frontend_url: str, backend_url: str, expected_environment: str | None = None, expected_release: str | None = None, timeout: float = 10.0, smoke_token: str | None = None) -> dict[str, object]:
    frontend = _safe_origin(frontend_url)
    backend = _safe_origin(backend_url)
    checks: dict[str, str] = {}
    if not frontend or not backend:
        return {"status": "fail", "mode": "hosted", "checks": {"configuration": "fail"}, "external_provider_called": False}

    status_code, frontend_headers, page_text = _hosted_text(f"{frontend}/", timeout=timeout)
    checks["frontend"] = "pass" if status_code == 200 else "fail"
    for name, path in (("privacy", "/privacy"), ("terms", "/terms")):
        code, _, _ = _hosted_text(f"{frontend}{path}", timeout=timeout)
        checks[name] = "pass" if code == 200 else "fail"
    lower_page = page_text.lower()
    checks["frontend_no_localhost"] = "fail" if any(value in lower_page for value in ("localhost", "127.0.0.1")) else "pass" if status_code == 200 else "fail"
    checks["offline_competition_disclosure"] = "pass" if any(value in lower_page for value in ("offline", "離線", "オフライン", "오프라인")) else "fail"
    checks["frontend_security_headers"] = "pass" if all(name in frontend_headers for name in ("content-security-policy", "referrer-policy", "x-content-type-options")) else "fail"

    request_headers = {"Accept": "application/json"}
    if smoke_token:
        request_headers["X-Production-Smoke-Token"] = smoke_token
    for name, path in (("liveness", "/liveness"), ("readiness", "/readiness"), ("release", "/release-version"), ("source_status", "/source-status"), ("compatibility", "/compatibility"), ("competition_demo", "/demo-cases"), ("taxoracle_sources", "/taxoracle/sources")):
        code, response_headers, body = _hosted_json(f"{backend}{path}", timeout=timeout, headers=request_headers)
        checks[name] = "pass" if code == 200 and isinstance(body, dict) else "fail"
        if name == "release":
            checks["backend_security_headers"] = "pass" if all(header in response_headers for header in ("content-security-policy", "referrer-policy", "x-content-type-options", "x-frame-options")) else "fail"
            checks["cache_safety"] = "pass" if "no-store" in response_headers.get("cache-control", "").lower() else "fail"
        if name == "release" and isinstance(body, dict):
            if expected_environment:
                checks["release_environment"] = "pass" if body.get("environment") == expected_environment else "fail"
            if expected_release:
                checks["release_identity"] = "pass" if body.get("release_version") == expected_release else "fail"

    cors_code, cors_headers, _ = _hosted_json(f"{backend}/health", timeout=timeout, method="OPTIONS", headers={"Origin": frontend, "Access-Control-Request-Method": "GET"})
    checks["cors"] = "pass" if cors_code in {200, 204} and cors_headers.get("access-control-allow-origin") == frontend else "fail"
    required = {"frontend", "liveness", "readiness", "release", "source_status", "compatibility", "competition_demo", "taxoracle_sources", "cors", "privacy", "terms", "frontend_no_localhost", "offline_competition_disclosure", "frontend_security_headers", "backend_security_headers", "cache_safety"}
    result = "pass" if all(checks.get(key) == "pass" for key in required) else "fail"
    return {"status": result, "mode": "hosted", "checks": checks, "external_provider_called": False}


def run(*, frontend_url: str | None = None, backend_url: str | None = None, expected_environment: str | None = None, expected_release: str | None = None, timeout: float = 10.0, smoke_token: str | None = None) -> dict[str, object]:
    if frontend_url or backend_url:
        if not frontend_url or not backend_url:
            return {"status": "fail", "mode": "hosted", "checks": {"configuration": "fail"}, "external_provider_called": False}
        return run_hosted(frontend_url=frontend_url, backend_url=backend_url, expected_environment=expected_environment, expected_release=expected_release, timeout=timeout, smoke_token=smoke_token)
    return _local_run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url")
    parser.add_argument("--backend-url")
    parser.add_argument("--expected-environment")
    parser.add_argument("--expected-release")
    parser.add_argument("--smoke-token")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    result = run(frontend_url=args.frontend_url, backend_url=args.backend_url, expected_environment=args.expected_environment, expected_release=args.expected_release, timeout=args.timeout, smoke_token=args.smoke_token)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
