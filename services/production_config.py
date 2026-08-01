"""Central, value-free runtime configuration checks.

This module deliberately returns categories and booleans only.  It never
prints environment values and it does not load dotenv files.  The production
database contract is ``DATABASE_URL``; the existing pilot-specific variable is
accepted as a compatibility alias while operators migrate configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit

from services.security import MIN_SESSION_SIGNING_KEY_LENGTH, is_serverless_runtime


DATABASE_URL_ENV = "DATABASE_URL"
PILOT_DATABASE_URL_ENV = "PILOT_EVIDENCE_DATABASE_URL"
APP_ENV_ENV = "APP_ENV"
APP_RUNTIME_ENV = "APP_RUNTIME"
CORS_ALLOWED_ORIGINS_ENV = "CORS_ALLOWED_ORIGINS"
PUBLIC_APP_BASE_URL_ENV = "PUBLIC_APP_BASE_URL"
RELEASE_VERSION_ENV = "RELEASE_VERSION"

PRODUCTION_MODES = frozenset({"production", "preview"})


def _status(value: str | None, *, minimum_length: int = 1) -> str:
    value = (value or "").strip()
    if not value:
        return "not_configured"
    if len(value) < minimum_length or any(ord(char) < 32 for char in value):
        return "malformed"
    return "configured"


def _postgres_status(value: str | None) -> str:
    value = (value or "").strip()
    if not value:
        return "not_configured"
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        return "malformed"
    return "configured"


def _origin_status(value: str | None) -> str:
    values = [item.strip().rstrip("/") for item in (value or "").split(",") if item.strip()]
    if not values or any(item == "*" for item in values):
        return "not_configured" if not values else "malformed"
    for item in values:
        parsed = urlsplit(item)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
            return "malformed"
    return "configured"


def _base_url_status(value: str | None) -> str:
    value = (value or "").strip()
    if not value:
        return "not_configured"
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        return "malformed"
    return "configured"


def _database_url(values: Mapping[str, str]) -> tuple[str, str]:
    primary = values.get(DATABASE_URL_ENV, "").strip()
    if primary:
        return primary, DATABASE_URL_ENV
    alias = values.get(PILOT_DATABASE_URL_ENV, "").strip()
    return alias, PILOT_DATABASE_URL_ENV if alias else DATABASE_URL_ENV


@dataclass(frozen=True)
class RuntimeConfiguration:
    mode: str
    runtime: str
    database_status: str
    database_source: str
    session_secret_status: str
    admin_token_status: str
    reviewer_token_status: str
    cors_status: str
    public_base_url_status: str
    release_version_status: str
    serverless: bool

    @property
    def production_like(self) -> bool:
        return self.mode in PRODUCTION_MODES or self.serverless

    @property
    def ready(self) -> bool:
        if not self.production_like:
            return True
        return all(
            value == "configured"
            for value in (self.database_status, self.session_secret_status, self.cors_status, self.public_base_url_status)
        )

    def safe_report(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "runtime": self.runtime or "standard",
            "production_like": self.production_like,
            "serverless": self.serverless,
            "database": self.database_status,
            "database_source": self.database_source,
            "session_secret": self.session_secret_status,
            "admin_token": self.admin_token_status,
            "reviewer_token": self.reviewer_token_status,
            "cors_origins": self.cors_status,
            "public_base_url": self.public_base_url_status,
            "release_version": self.release_version_status,
            "ready": self.ready,
        }


def load_runtime_configuration(environ: Mapping[str, str] | None = None) -> RuntimeConfiguration:
    values = environ if environ is not None else os.environ
    mode = values.get(APP_ENV_ENV, "development").strip().lower() or "development"
    runtime = values.get(APP_RUNTIME_ENV, "").strip().lower()
    database_url, database_source = _database_url(values)
    return RuntimeConfiguration(
        mode=mode,
        runtime=runtime,
        database_status=_postgres_status(database_url),
        database_source=database_source,
        session_secret_status=_status(values.get("PILOT_SESSION_SIGNING_KEY"), minimum_length=MIN_SESSION_SIGNING_KEY_LENGTH),
        admin_token_status=_status(values.get("PILOT_ADMIN_TOKEN")),
        reviewer_token_status=_status(values.get("PILOT_REVIEW_TOKEN")),
        cors_status=_origin_status(values.get(CORS_ALLOWED_ORIGINS_ENV)),
        public_base_url_status=_base_url_status(values.get(PUBLIC_APP_BASE_URL_ENV)),
        release_version_status=_status(values.get(RELEASE_VERSION_ENV)),
        serverless=is_serverless_runtime(dict(values)),
    )


def database_url(environ: Mapping[str, str] | None = None) -> str:
    values = environ if environ is not None else os.environ
    return _database_url(values)[0]


def assert_startup_configuration(environ: Mapping[str, str] | None = None) -> RuntimeConfiguration:
    config = load_runtime_configuration(environ)
    if config.production_like and not config.ready:
        raise RuntimeError("Required production configuration is unavailable.")
    return config
