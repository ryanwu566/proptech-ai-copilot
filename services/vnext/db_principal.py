"""Transaction-local propagation of a validated application principal.

This abstraction does not provision the future ``vnext_api`` database role.
Instead it verifies that the checked-out connection already uses the expected
non-owner, non-BYPASSRLS role, then installs only the validated JWT subject as
transaction-local Postgres settings. PostgreSQL clears those settings on
commit or rollback before the connection is returned to its pool.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator, Protocol

from services.vnext.auth import AuthenticatedPrincipal


FORBIDDEN_REQUEST_ROLES = frozenset({"postgres", "service_role"})


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
