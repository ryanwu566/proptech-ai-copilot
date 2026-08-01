"""Centralized defensive security primitives for the pilot and public API.

The helpers in this module intentionally deal only in bounded, categorical
values.  Bootstrap secrets are accepted at the server boundary and are never
placed in a session payload, response, log record, or browser bundle.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit

from fastapi import HTTPException, Request


SESSION_COOKIE_NAME = "pilot_scoped_session"
CSRF_COOKIE_NAME = "pilot_csrf"
SESSION_MAX_AGE_SECONDS = 15 * 60
MIN_SECRET_LENGTH = 16
MIN_SESSION_SIGNING_KEY_LENGTH = 32
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
SAFE_ROLES = frozenset({"participant", "reviewer", "administrator", "public_aggregate_reader"})


class SecurityConfigurationError(ValueError):
    """Raised when a security-sensitive runtime configuration is unsafe."""


class PersistenceConfigurationError(SecurityConfigurationError):
    """Raised when a production persistence choice would be unsafe."""


def constant_time_secret_equals(candidate: str | None, configured: str | None) -> bool:
    candidate = candidate or ""
    configured = configured or ""
    if not candidate or not configured:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), configured.encode("utf-8"))


def _decode_base64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def validate_secret_strength(value: str | None, *, name: str, minimum: int = MIN_SECRET_LENGTH) -> str:
    value = (value or "").strip()
    if len(value) < minimum or any(ord(char) < 32 for char in value):
        raise SecurityConfigurationError(f"{name} is not configured safely")
    return value


def safe_identifier(value: str, *, field: str = "identifier") -> str:
    value = str(value or "").strip()
    if not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


def safe_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    parsed = urlsplit(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def require_same_origin(request: Request, allowed_origins: Iterable[str], *, cookie_authenticated: bool = False) -> None:
    """Reject unsafe cross-origin state changes without reflecting attacker input."""

    origin = safe_origin(request.headers.get("origin"))
    if origin and origin not in {item.lower().rstrip("/") for item in allowed_origins}:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    if cookie_authenticated:
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get("X-CSRF-Token")
        if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
            raise HTTPException(status_code=403, detail="Request protection is unavailable.")


def safe_external_url(value: str, *, allowed_hosts: Iterable[str] = ()) -> str:
    """Validate a user-visible link; never resolve or fetch it here."""

    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("external link is not allowed")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.startswith(("127.", "10.", "192.168.")) or host == "::1" or host.startswith("169.254."):
        raise ValueError("private link is not allowed")
    allowed = {item.lower().rstrip(".") for item in allowed_hosts}
    if allowed and host not in allowed:
        raise ValueError("link host is not allowed")
    return parsed.geturl()


@dataclass(frozen=True)
class ScopedSession:
    session_id: str
    role: str
    expires_at: int


class ScopedSessionManager:
    """Short-lived signed sessions with explicit role scope.

    Revocation is process-local by design; production deployments should use a
    durable session store or a shared signing key and revoke at the operator
    boundary.  The bootstrap secret is never encoded in the signed payload.
    """

    def __init__(self, signing_key: str | None = None, *, now=time.time) -> None:
        self.signing_key = validate_secret_strength(signing_key, name="PILOT_SESSION_SIGNING_KEY", minimum=MIN_SESSION_SIGNING_KEY_LENGTH)
        self._now = now
        self._revoked: set[str] = set()

    def issue(self, role: str, *, max_age: int = SESSION_MAX_AGE_SECONDS) -> str:
        if role not in SAFE_ROLES or role == "participant":
            raise ValueError("unsupported session role")
        payload = {"sid": secrets.token_urlsafe(18), "role": role, "exp": int(self._now()) + max(60, min(int(max_age), SESSION_MAX_AGE_SECONDS))}
        body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        signature = hmac.new(self.signing_key.encode(), body.encode(), hashlib.sha256).digest()
        return f"{body}.{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"

    def verify(self, token: str | None, *, role: str) -> ScopedSession | None:
        if role not in SAFE_ROLES or not token or len(token) > 600:
            return None
        try:
            body, encoded_signature = token.split(".", 1)
            expected = hmac.new(self.signing_key.encode(), body.encode(), hashlib.sha256).digest()
            supplied = _decode_base64(encoded_signature)
            if not hmac.compare_digest(supplied, expected):
                return None
            payload = json.loads(_decode_base64(body).decode())
            session = ScopedSession(str(payload["sid"]), str(payload["role"]), int(payload["exp"]))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        if session.role != role or session.session_id in self._revoked or session.expires_at <= int(self._now()):
            return None
        return session

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        try:
            body = token.split(".", 1)[0]
            payload = json.loads(_decode_base64(body).decode())
            session_id = str(payload.get("sid", ""))
            if session_id:
                self._revoked.add(session_id)
        except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
            return


def security_headers(*, production: bool = False, private: bool = False) -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=(), microphone=(self)",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        "X-Frame-Options": "DENY",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-site",
        "Cache-Control": "private, no-store" if private else "no-store",
    }
    if production:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


def is_serverless_runtime(environ: dict[str, str] | None = None) -> bool:
    values = environ if environ is not None else os.environ
    mode = values.get("APP_RUNTIME", "").strip().lower()
    return mode in {"serverless", "vercel", "lambda"} or values.get("VERCEL", "").strip() == "1"
