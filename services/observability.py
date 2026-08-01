"""Bounded, privacy-safe request and client-error observability helpers."""

from __future__ import annotations

import re
import secrets
from typing import Any


CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
MAX_ERROR_CODE_LENGTH = 80
ALLOWED_CLIENT_ERROR_CODES = {
    "render_failure",
    "unhandled_rejection",
    "network_failure",
    "pilot_submission_failure",
    "unsupported_browser",
}


def new_correlation_id() -> str:
    return secrets.token_hex(16)


def normalize_correlation_id(value: str | None) -> str:
    """Accept only bounded header-safe IDs; never reuse a token or session ID."""

    if value and CORRELATION_ID_PATTERN.fullmatch(value):
        return value
    return new_correlation_id()


def safe_error_code(value: str) -> str:
    code = str(value or "").strip()
    if code in ALLOWED_CLIENT_ERROR_CODES:
        return code
    return "client_error"


def build_observation(*, correlation_id: str, route: str, method: str, status_code: int, duration_ms: int, release_version: str = "0.1.0", pilot_mode: str = "normal", environment: str = "runtime", dependency_status: str = "unknown", error_code: str | None = None) -> dict[str, Any]:
    return {
        "correlation_id": normalize_correlation_id(correlation_id),
        "route": str(route)[:120],
        "method": str(method)[:12],
        "status_class": f"{int(status_code) // 100}xx",
        "duration_ms": max(0, min(int(duration_ms), 120000)),
        "release_version": str(release_version)[:40],
        "pilot_mode": str(pilot_mode)[:40],
        "environment": str(environment)[:40],
        "dependency_status": str(dependency_status)[:40],
        "error_code": safe_error_code(error_code) if error_code else None,
    }


def sanitize_client_error(code: str, route: str, boundary: str) -> dict[str, str]:
    """Allow only categorical client-error fields; never accept error objects."""

    safe_route = route.strip()[:120] if isinstance(route, str) else "unknown"
    safe_boundary = boundary.strip()[:40] if isinstance(boundary, str) else "unknown"
    return {"error_code": safe_error_code(code), "route": safe_route, "boundary": safe_boundary}
