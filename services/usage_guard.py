"""Synchronous atomic PostgreSQL quota boundary, separate from lossy telemetry."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from urllib.parse import urlsplit
from uuid import UUID

from services.postgres_runtime import connect
from services.usage_quota import QuotaExceeded


@dataclass(frozen=True)
class GuardConfiguration:
    mode: str
    database_url: str


def guard_configuration():
    from services.production_guardrails import production_like
    production = production_like(os.environ)
    url = os.getenv("API_USAGE_DATABASE_URL", "").strip()
    mode = os.getenv("API_USAGE_GUARD_MODE", "postgres" if production or url else "local").strip()
    try:
        parsed = urlsplit(url)
        if mode not in {"local", "postgres"} or (production and mode != "postgres"):
            raise ValueError()
        if mode == "postgres" and (not url or parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path.strip("/") or parsed.port == 0):
            raise ValueError()
    except ValueError:
        raise RuntimeError("Invalid API usage guard configuration.") from None
    return GuardConfiguration(mode, url)


class PostgresQuotaGuard:
    def __init__(self, database_url, *, connection_factory=None):
        self.database_url = database_url
        self.connection_factory = connection_factory

    def _connect(self):
        return connect(self.database_url, connection_factory=self.connection_factory, connect_timeout=2)

    def check(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT r.rolsuper OR s.rolsuper, r.rolbypassrls OR s.rolbypassrls, r.rolcreaterole OR s.rolcreaterole, "
                "pg_has_role(current_user, 'proptech_usage_executor', 'MEMBER') OR pg_has_role(session_user, 'proptech_usage_executor', 'MEMBER'), "
                "pg_has_role(current_user, 'proptech_usage_guard', 'USAGE'), "
                "EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='api_usage' AND c.relowner IN (r.oid,s.oid)) "
                "FROM pg_roles r JOIN pg_roles s ON s.rolname=session_user WHERE r.rolname=current_user"
            ).fetchone()
            if row is None or any(row[i] for i in (0, 1, 2, 3, 5)) or not row[4]:
                raise RuntimeError("Unsafe API usage database principal.")
            # Verify signature/grants without consuming a subject or a marker.
            connection.execute("SELECT api_usage.consume(NULL,NULL,NULL,NULL,NULL)").fetchone()

    def consume(self, principal, capability, kind, marker: UUID):
        if kind not in {"request", "operation"} or not isinstance(marker, UUID):
            raise ValueError("Invalid usage reservation")
        with self._connect() as connection:
            with connection.transaction():
                connection.execute("SET LOCAL statement_timeout = '2000ms'")
                connection.execute("SET LOCAL lock_timeout = '500ms'")
                row = connection.execute(
                    "SELECT * FROM api_usage.consume(%s,%s,%s,%s,%s)",
                    (principal.key, principal.principal_class, capability, kind, marker),
                ).fetchone()
        # Commit a rejection's separate observation before rendering 429.
        if row is None or row[0] not in {"admitted", "duplicate", "quota", "capacity"}:
            raise RuntimeError("Unavailable API usage guard.")
        if row[0] == "quota":
            raise QuotaExceeded(f"{principal.principal_class}_quota", row[1])
        if row[0] == "capacity":
            raise RuntimeError("Unavailable API usage guard.")
        return row[0]


@lru_cache(maxsize=2)
def _guard(config):
    return PostgresQuotaGuard(config.database_url) if config.mode == "postgres" else None


def configured_guard():
    return _guard(guard_configuration())


def validate_usage_startup():
    from services.usage_principal import peer_key
    peer_key()
    guard = configured_guard()
    if guard is not None:
        try:
            guard.check()
        except Exception:
            raise RuntimeError("Required API usage guard is unavailable.") from None
