"""Transaction-local propagation of a validated application principal.

This abstraction does not provision the future ``vnext_api`` database role.
Instead it verifies that the checked-out connection already uses the expected
non-owner, non-BYPASSRLS role, then installs only the validated JWT subject as
transaction-local Postgres settings. PostgreSQL clears those settings on
commit or rollback before the connection is returned to its pool.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator, Protocol

from services.vnext.auth import AuthenticatedPrincipal


FORBIDDEN_REQUEST_ROLES = frozenset({"postgres", "service_role"})
VNEXT_DATABASE_URL_ENV = "VNEXT_DATABASE_URL"


class DatabasePrincipalContextError(RuntimeError):
    pass


class ConnectionPool(Protocol):
    def connection(self) -> Any: ...


class DatabasePrincipalContext:
    """Open one safe tenant transaction for one authenticated principal."""

    def __init__(self, pool: ConnectionPool, *, expected_role: str = "vnext_api") -> None:
        if not expected_role or expected_role in FORBIDDEN_REQUEST_ROLES:
            raise ValueError("unsafe expected database role")
        self._pool = pool
        self._expected_role = expected_role

    def close(self) -> None:
        close = getattr(self._pool, "close", None)
        if callable(close):
            close()

    def _verify_database_role(self, connection: Any) -> None:
        row = connection.execute(
            "SELECT rolname, rolsuper, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
        if row is None:
            raise DatabasePrincipalContextError("database_request_role_unavailable")
        role_name, is_superuser, bypasses_rls = str(row[0]), bool(row[1]), bool(row[2])
        if (
            role_name != self._expected_role
            or role_name in FORBIDDEN_REQUEST_ROLES
            or is_superuser
            or bypasses_rls
        ):
            raise DatabasePrincipalContextError("database_request_role_unsafe")
        # The request credential is a direct login with no parent roles. In
        # particular, 022's Admin executor privileges must not be inherited or
        # reachable through SET ROLE. Reject all membership edges (including
        # NOINHERIT / SET-only edges), so transitive privilege drift cannot hide
        # behind an otherwise unprivileged current_user.
        authority = connection.execute("""
            SELECT EXISTS (
              SELECT 1 FROM pg_roles r WHERE r.rolname=current_user AND (
                current_user<>session_user OR NOT r.rolcanlogin
                OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
                OR EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid)
                OR r.oid=(SELECT datdba FROM pg_database WHERE datname=current_database())
                OR has_database_privilege(r.oid,current_database(),'CREATE')
                OR EXISTS(SELECT 1 FROM pg_namespace n
                    WHERE left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema'
                    AND (n.nspowner=r.oid OR has_schema_privilege(r.oid,n.oid,'CREATE')))
                OR EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND c.relowner=r.oid)
                OR EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND p.proowner=r.oid)
              )
            )
        """).fetchone()
        if authority is None or bool(authority[0]):
            raise DatabasePrincipalContextError("database_request_role_unsafe")

    @contextmanager
    def transaction(
        self,
        principal: AuthenticatedPrincipal,
    ) -> Iterator[Any]:
        with self._pool.connection() as connection:
            with connection.transaction():
                self._verify_database_role(connection)
                subject = str(principal.user_id)
                claims = json.dumps({"sub": subject}, separators=(",", ":"))
                connection.execute(
                    "SELECT set_config('request.jwt.claim.sub', %s, true)",
                    (subject,),
                )
                connection.execute(
                    "SELECT set_config('request.jwt.claims', %s, true)",
                    (claims,),
                )
                established = connection.execute(
                    "SELECT current_setting('request.jwt.claim.sub', true)"
                ).fetchone()
                if established is None or established[0] != subject:
                    raise DatabasePrincipalContextError(
                        "database_principal_context_unavailable"
                    )
                yield connection


@lru_cache(maxsize=1)
def get_vnext_database_principal_context() -> DatabasePrincipalContext:
    """Build the dedicated VNext request pool, never the legacy owner pool.

    ``VNEXT_DATABASE_URL`` must authenticate directly as ``vnext_api``.  It is
    intentionally not allowed to fall back to the repository's legacy
    ``DATABASE_URL`` because that credential may own tables or bypass RLS.
    """

    database_url = os.getenv(VNEXT_DATABASE_URL_ENV, "").strip()
    if not database_url:
        raise DatabasePrincipalContextError("database_request_role_unavailable")
    try:
        from psycopg_pool import ConnectionPool as PsycopgConnectionPool

        pool = PsycopgConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"prepare_threshold": None},
        )
    except Exception:
        raise DatabasePrincipalContextError(
            "database_request_role_unavailable"
        ) from None
    return DatabasePrincipalContext(pool, expected_role="vnext_api")


def close_vnext_database_pool() -> None:
    """Close the VNext request pool without creating it during shutdown."""

    if get_vnext_database_principal_context.cache_info().currsize:
        try:
            get_vnext_database_principal_context().close()
        finally:
            get_vnext_database_principal_context.cache_clear()
