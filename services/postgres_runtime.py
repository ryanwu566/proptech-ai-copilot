"""Small, shared Postgres connection and readiness boundary."""

from __future__ import annotations

import os
from typing import Any, Callable


def connect(
    database_url: str,
    *,
    connection_factory: Callable[..., Any] | None = None,
    row_factory: Any | None = None,
    connect_timeout: int = 5,
    sslmode: str | None = None,
) -> Any:
    if connection_factory is not None:
        return connection_factory(database_url)
    import psycopg

    kwargs: dict[str, Any] = {"connect_timeout": max(1, min(int(connect_timeout), 30)), "prepare_threshold": None}
    selected_sslmode = (sslmode or os.getenv("POSTGRES_SSLMODE", "")).strip().lower()
    if selected_sslmode:
        if selected_sslmode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
            raise ValueError("unsupported Postgres SSL mode")
        kwargs["sslmode"] = selected_sslmode
    if row_factory is not None:
        kwargs["row_factory"] = row_factory
    return psycopg.connect(database_url, **kwargs)


def check_connection(database_url: str, *, connection_factory: Callable[..., Any] | None = None, connect_timeout: int = 5, sslmode: str | None = None) -> str:
    if not database_url:
        return "not_configured"
    try:
        with connect(database_url, connection_factory=connection_factory, connect_timeout=connect_timeout, sslmode=sslmode) as connection:
            connection.execute("SELECT 1").fetchone()
    except Exception:
        return "unavailable"
    return "available"
