"""Central, value-free runtime configuration checks.

This module deliberately returns categories and booleans only.  It never
prints environment values and it does not load dotenv files.  The production
database contract is ``DATABASE_URL``; the existing pilot-specific variable is
accepted as a compatibility alias while operators migrate configuration.
"""

from __future__ import annotations

import ipaddress
import os
import re
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit

from services.metrics import valid_scrape_token
from services.security import MIN_SESSION_SIGNING_KEY_LENGTH, is_serverless_runtime


DATABASE_URL_ENV = "DATABASE_URL"
PILOT_DATABASE_URL_ENV = "PILOT_EVIDENCE_DATABASE_URL"
APP_ENV_ENV = "APP_ENV"
APP_RUNTIME_ENV = "APP_RUNTIME"
CORS_ALLOWED_ORIGINS_ENV = "CORS_ALLOWED_ORIGINS"
PUBLIC_APP_BASE_URL_ENV = "PUBLIC_APP_BASE_URL"
RELEASE_VERSION_ENV = "RELEASE_VERSION"
API_CONTRACT_VERSION_ENV = "API_CONTRACT_VERSION"
SCHEMA_VERSION_ENV = "SCHEMA_VERSION"
MAINTENANCE_MODE_ENV = "MAINTENANCE_MODE"
NLSC_GATEWAY_BASE_URL_ENV = "NLSC_GATEWAY_BASE_URL"
NLSC_GATEWAY_CLIENT_TOKEN_ENV = "NLSC_GATEWAY_CLIENT_TOKEN"
METRICS_SCRAPE_TOKEN_ENV = "METRICS_SCRAPE_TOKEN"

PRODUCTION_MODES = frozenset({"production", "preview"})
_GATEWAY_TOKEN = re.compile(r"[A-Za-z0-9._~+/-]+={0,2}\Z")
_DNS_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_NONPUBLIC_GATEWAY_SUFFIXES = frozenset({
    "localhost", "local", "localdomain", "internal", "lan", "home",
    "invalid", "test", "example",
})


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
    try:
        _ = parsed.port
    except ValueError:
        return "malformed"
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or parsed.username is None and parsed.password is not None:
        return "malformed"
    return "configured"


def _origin_status(value: str | None, *, reject_local: bool = False) -> str:
    values = [item.strip().rstrip("/") for item in (value or "").split(",") if item.strip()]
    if not values or any(item == "*" for item in values):
        return "not_configured" if not values else "malformed"
    for item in values:
        parsed = urlsplit(item)
        try:
            port = parsed.port
        except ValueError:
            return "malformed"
        host = (parsed.hostname or "").lower().rstrip(".")
        is_local = host in {"localhost", "localhost.localdomain", "127.0.0.1", "::1"}
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or not host or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or (reject_local and is_local):
            return "malformed"
    return "configured"


def _base_url_status(value: str | None) -> str:
    value = (value or "").strip()
    if not value:
        return "not_configured"
    parsed = urlsplit(value)
    try:
        _ = parsed.port
    except ValueError:
        return "malformed"
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return "malformed"
    return "configured"


def nlsc_gateway_configuration_status(values: Mapping[str, str], *, production_like: bool) -> str:
    """Validate a fixed gateway origin and credential, without inferring location."""

    raw_url = values.get(NLSC_GATEWAY_BASE_URL_ENV, "")
    raw_token = values.get(NLSC_GATEWAY_CLIENT_TOKEN_ENV, "")
    if not raw_url or not raw_token:
        return "not_configured"
    url = raw_url.strip()
    token = raw_token.strip()
    if not url or not token:
        return "not_configured"
    if raw_url != url or raw_token != token or len(token) < 16 or len(token) > 512 or not _GATEWAY_TOKEN.fullmatch(token):
        return "malformed"
    if any(char.isspace() or ord(char) < 32 for char in url) or "\\" in url:
        return "malformed"
    try:
        parsed = urlsplit(url)
        port = parsed.port
        host = parsed.hostname
    except ValueError:
        return "malformed"
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not host or parsed.username or parsed.password:
        return "malformed"
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment or port == 0:
        return "malformed"
    if production_like and parsed.scheme != "https":
        return "malformed"
    host = host.lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        labels = host.split(".")
        if not all(_DNS_LABEL.fullmatch(label) for label in labels):
            return "malformed"
        if production_like and (
            len(labels) < 2
            or labels[0] == "localhost"
            or labels[-1] in _NONPUBLIC_GATEWAY_SUFFIXES
            or labels[-2:] == ["home", "arpa"]
            or not any(char.isalpha() for char in labels[-1])
        ):
            return "malformed"
    else:
        if production_like and not address.is_global:
            return "malformed"
    return "configured"


def _maintenance_status(value: str | None) -> str:
    value = (value or "").strip().lower()
    return "enabled" if value in {"1", "true", "yes", "on"} else "disabled"


def _metrics_scrape_token_status(value: str | None) -> str:
    if value is None or value == "":
        return "not_configured"
    return "configured" if valid_scrape_token(value) else "malformed"


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
    api_contract_version_status: str
    schema_version_status: str
    maintenance_status: str
    nlsc_gateway_status: str
    metrics_scrape_token_status: str
    serverless: bool

    @property
    def production_like(self) -> bool:
        return self.mode in PRODUCTION_MODES or self.serverless

    @property
    def ready(self) -> bool:
        if not self.production_like:
            return True
        required_configuration_ready = all(
            value == "configured"
            for value in (self.database_status, self.session_secret_status, self.cors_status, self.public_base_url_status)
        )
        return required_configuration_ready and self.metrics_scrape_token_status != "malformed"

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
            "api_contract_version": self.api_contract_version_status,
            "schema_version": self.schema_version_status,
            "maintenance": self.maintenance_status,
            "nlsc_gateway": self.nlsc_gateway_status,
            "metrics_scrape_token": self.metrics_scrape_token_status,
            "ready": self.ready,
        }


def load_runtime_configuration(environ: Mapping[str, str] | None = None) -> RuntimeConfiguration:
    values = environ if environ is not None else os.environ
    mode = values.get(APP_ENV_ENV, "development").strip().lower() or "development"
    runtime = values.get(APP_RUNTIME_ENV, "").strip().lower()
    database_url, database_source = _database_url(values)
    serverless = is_serverless_runtime(dict(values))
    production_like = mode in PRODUCTION_MODES or serverless
    return RuntimeConfiguration(
        mode=mode,
        runtime=runtime,
        database_status=_postgres_status(database_url),
        database_source=database_source,
        session_secret_status=_status(values.get("PILOT_SESSION_SIGNING_KEY"), minimum_length=MIN_SESSION_SIGNING_KEY_LENGTH),
        admin_token_status=_status(values.get("PILOT_ADMIN_TOKEN")),
        reviewer_token_status=_status(values.get("PILOT_REVIEW_TOKEN")),
        cors_status=_origin_status(values.get(CORS_ALLOWED_ORIGINS_ENV), reject_local=mode in PRODUCTION_MODES or serverless),
        public_base_url_status=_base_url_status(values.get(PUBLIC_APP_BASE_URL_ENV)),
        release_version_status=_status(values.get(RELEASE_VERSION_ENV)),
        api_contract_version_status=_status(values.get(API_CONTRACT_VERSION_ENV)),
        schema_version_status=_status(values.get(SCHEMA_VERSION_ENV)),
        maintenance_status=_maintenance_status(values.get(MAINTENANCE_MODE_ENV)),
        nlsc_gateway_status=nlsc_gateway_configuration_status(values, production_like=production_like),
        metrics_scrape_token_status=_metrics_scrape_token_status(values.get(METRICS_SCRAPE_TOKEN_ENV)),
        serverless=serverless,
    )


def database_url(environ: Mapping[str, str] | None = None) -> str:
    values = environ if environ is not None else os.environ
    return _database_url(values)[0]


def assert_startup_configuration(environ: Mapping[str, str] | None = None) -> RuntimeConfiguration:
    config = load_runtime_configuration(environ)
    if config.production_like and not config.ready:
        raise RuntimeError("Required production configuration is unavailable.")
    return config
