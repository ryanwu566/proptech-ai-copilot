"""Bounded local and hosted release smoke checks.

Hosted URLs are explicit inputs. The runner never prints URLs, headers, token
values, response bodies, or provider details. Local mode remains provider-free.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.request import Request, HTTPRedirectHandler, build_opener
import re


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Never forward smoke credentials or accept a different deployment target.
urlopen = build_opener(_NoRedirect()).open

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.provider_config_contract import valid_sha


def _safe_origin(value: str) -> str | None:
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.hostname in {"localhost", "127.0.0.1", "::1"} or port not in {None, 443} or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _hosted_json(url: str, *, timeout: float, method: str = "GET", headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], dict[str, object] | list[object] | None]:
    request = Request(url, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=max(1.0, min(float(timeout), 30.0))) as response:
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            if method == "OPTIONS":
                return response.status, response_headers, None
            body = response.read(256_001)
            if len(body) > 256_000:
                return 0, {}, None
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            return response.status, response_headers, payload if isinstance(payload, (dict, list)) else None
    except Exception:
        return 0, {}, None


def _hosted_text(url: str, *, timeout: float) -> tuple[int, dict[str, str], str]:
    request = Request(url, method="GET", headers={"Accept": "text/html"})
    try:
        with urlopen(request, timeout=max(1.0, min(float(timeout), 30.0))) as response:
            body = response.read(256_001)
            if len(body) > 256_000:
                return 0, {}, ""
            return response.status, {key.lower(): value for key, value in response.headers.items()}, body.decode("utf-8", errors="replace")
    except Exception:
        return 0, {}, ""


def _local_run() -> dict[str, object]:
    from backend.api_main import app
    from fastapi.testclient import TestClient

    checks: dict[str, str] = {}
    with TestClient(app) as client:
        for name, path in (("liveness", "/liveness"), ("health", "/health"), ("readiness", "/readiness"), ("release_version", "/release-version"), ("source_status", "/source-status"), ("compatibility", "/compatibility")):
            response = client.get(path)
            checks[name] = "pass" if response.status_code == 200 else "fail"
    return {"status": "pass" if all(value == "pass" for value in checks.values()) else "fail", "mode": "local", "checks": checks, "external_provider_called": False}


def run_hosted(*, frontend_url: str, backend_url: str, expected_environment: str | None = None, expected_release: str | None = None, expected_frontend_sha: str | None = None, expected_backend_sha: str | None = None, timeout: float = 10.0, smoke_token: str | None = None) -> dict[str, object]:
    frontend = _safe_origin(frontend_url)
    backend = _safe_origin(backend_url)
    checks: dict[str, str] = {}
    if not frontend or not backend:
        return {"status": "configuration_required", "reason_code": "configuration_required", "mode": "hosted", "checks": {"configuration": "fail"}, "external_provider_called": False, "classification": "CONFIGURATION REQUIRED", "network_requests": 0}
    if expected_environment not in {"preview", "production"} or not expected_release or not re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", expected_release) or expected_release in {"unconfigured", "pending"} or not expected_frontend_sha or not expected_backend_sha or expected_frontend_sha.lower() != expected_backend_sha.lower():
        return {"status": "configuration_required", "reason_code": "pinned_release_contract_required", "classification": "CONFIGURATION REQUIRED", "mode": "hosted", "checks": {"configuration": "fail"}, "external_provider_called": False, "network_requests": 0}
    for expected in (expected_frontend_sha, expected_backend_sha):
        if expected and not valid_sha(expected):
            return {"status": "configuration_required", "reason_code": "invalid_release_contract", "mode": "hosted", "checks": {"configuration": "fail"}, "external_provider_called": False, "classification": "CONFIGURATION REQUIRED", "network_requests": 0}

    identity = {"frontend_sha": "unconfigured", "backend_sha": "unconfigured"}
    code, _, front_release = _hosted_json(f"{frontend}/release-version", timeout=timeout)
    if code == 200 and isinstance(front_release, dict) and valid_sha(str(front_release.get("commit_sha", ""))):
        identity["frontend_sha"] = str(front_release["commit_sha"]).lower()

    checks["frontend_release_environment"] = "pass" if isinstance(front_release, dict) and front_release.get("environment") == expected_environment else "fail"
    checks["frontend_release_version"] = "pass" if isinstance(front_release, dict) and front_release.get("release_version") == expected_release else "fail"
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
    for name, path in (("health", "/health"), ("liveness", "/liveness"), ("readiness", "/readiness"), ("release", "/release-version"), ("source_status", "/source-status"), ("compatibility", "/compatibility"), ("competition_demo", "/demo-cases"), ("taxoracle_sources", "/taxoracle/sources")):
        code, response_headers, body = _hosted_json(f"{backend}{path}", timeout=timeout, headers=request_headers)
        checks[name] = "pass" if code == 200 and isinstance(body, dict) else "fail"
        if name == "competition_demo":
            checks[name] = "pass" if code == 200 and isinstance(body, list) and 0 < len(body) <= 20 and all(isinstance(row, dict) and isinstance(row.get("case_id"), str) for row in body) else "fail"
        if isinstance(body, dict):
            if name in {"health", "liveness"}:
                checks[name] = "pass" if code == 200 and body.get("status") in {"ok", "healthy"} else "fail"
            elif name == "readiness":
                checks[name] = "pass" if code == 200 and isinstance(body.get("runtime"), dict) and body["runtime"].get("ready") is True else "fail"
            elif name == "source_status":
                checks[name] = "pass" if code == 200 and body.get("status") == "available" and body.get("test_fixtures_excluded") is True else "fail"
            elif name == "compatibility":
                checks[name] = "pass" if code == 200 and body.get("status") == "compatible" else "fail"
        if name == "release":
            checks["backend_security_headers"] = "pass" if all(header in response_headers for header in ("content-security-policy", "referrer-policy", "x-content-type-options", "x-frame-options")) else "fail"
            checks["cache_safety"] = "pass" if "no-store" in response_headers.get("cache-control", "").lower() else "fail"
        if name == "release" and isinstance(body, dict):
            sha = str(body.get("commit_sha", ""))
            if valid_sha(sha):
                identity["backend_sha"] = sha.lower()
            if expected_environment:
                checks["release_environment"] = "pass" if body.get("environment") == expected_environment else "fail"
            if expected_release:
                checks["release_identity"] = "pass" if body.get("release_version") == expected_release else "fail"

    cors_code, cors_headers, _ = _hosted_json(f"{backend}/health", timeout=timeout, method="OPTIONS", headers={"Origin": frontend, "Access-Control-Request-Method": "GET"})
    checks["cors"] = "pass" if cors_code in {200, 204} and cors_headers.get("access-control-allow-origin") == frontend else "fail"
    checks["deployed_identity"] = "pass" if all(valid_sha(sha) for sha in identity.values()) else "fail"
    if expected_frontend_sha:
        checks["frontend_commit_sha"] = "pass" if identity["frontend_sha"] == expected_frontend_sha.lower() else "fail"
    if expected_backend_sha:
        checks["backend_commit_sha"] = "pass" if identity["backend_sha"] == expected_backend_sha.lower() else "fail"
    result = "pass" if all(value == "pass" for value in checks.values()) else "fail"
    return {"status": result, "mode": "hosted", "capability": "release_smoke", "target": {"frontend": "configured", "backend": "configured"}, "release_identity": identity, "classification": "PASS" if result == "pass" else "BLOCKED", "network_requests": 13, "reason_code": "release_checks_passed" if result == "pass" else "release_checks_failed", "checked_at": datetime.now(UTC).isoformat(), "checks": checks, "external_provider_called": False}


def run(*, frontend_url: str | None = None, backend_url: str | None = None, expected_environment: str | None = None, expected_release: str | None = None, expected_frontend_sha: str | None = None, expected_backend_sha: str | None = None, timeout: float = 10.0, smoke_token: str | None = None) -> dict[str, object]:
    if frontend_url or backend_url:
        if not frontend_url or not backend_url:
            return {"status": "configuration_required", "reason_code": "configuration_required", "mode": "hosted", "checks": {"configuration": "fail"}, "external_provider_called": False, "classification": "CONFIGURATION REQUIRED", "network_requests": 0}
        return run_hosted(frontend_url=frontend_url, backend_url=backend_url, expected_environment=expected_environment, expected_release=expected_release, expected_frontend_sha=expected_frontend_sha, expected_backend_sha=expected_backend_sha, timeout=timeout, smoke_token=smoke_token)
    return _local_run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url")
    parser.add_argument("--backend-url")
    parser.add_argument("--expected-environment")
    parser.add_argument("--expected-release")
    parser.add_argument("--smoke-token")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--hosted", action="store_true", help="Require hosted targets from args or environment; never silently run local")
    parser.add_argument("--expected-frontend-sha")
    parser.add_argument("--expected-backend-sha")
    args = parser.parse_args()
    if args.hosted:
        result = run_hosted(frontend_url=args.frontend_url or os.getenv("FRONTEND_PRODUCTION_URL", ""), backend_url=args.backend_url or os.getenv("BACKEND_PRODUCTION_URL", ""), expected_environment=args.expected_environment, expected_release=args.expected_release or os.getenv("EXPECTED_RELEASE_VERSION") or None, expected_frontend_sha=args.expected_frontend_sha or os.getenv("EXPECTED_FRONTEND_COMMIT_SHA") or None, expected_backend_sha=args.expected_backend_sha or os.getenv("EXPECTED_BACKEND_COMMIT_SHA") or None, timeout=args.timeout, smoke_token=args.smoke_token or os.getenv("PRODUCTION_SMOKE_TOKEN") or None)
    else:
        result = run(frontend_url=args.frontend_url, backend_url=args.backend_url, expected_environment=args.expected_environment, expected_release=args.expected_release, expected_frontend_sha=args.expected_frontend_sha, expected_backend_sha=args.expected_backend_sha, timeout=args.timeout, smoke_token=args.smoke_token)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 2 if result["status"] == "configuration_required" else 1)
