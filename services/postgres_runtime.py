"""Small, shared Postgres connection and readiness boundary."""

from __future__ import annotations

from typing import Any, Callable


def connect(database_url: str, *, connection_factory: Callable[..., Any] | None = None, row_factory: Any | None = None) -> Any:
    if connection_factory is not None:
        return connection_factory(database_url)
    import psycopg

    kwargs: dict[str, Any] = {"connect_timeout": 5, "prepare_threshold": None}
    if row_factory is not None:
        kwargs["row_factory"] = row_factory
    return psycopg.connect(database_url, **kwargs)


def check_connection(database_url: str, *, connection_factory: Callable[..., Any] | None = None) -> str:
    if not database_url:
        return "not_configured"
    try:
        with connect(database_url, connection_factory=connection_factory) as connection:
            connection.execute("SELECT 1").fetchone()
    except Exception:
        return "unavailable"
    return "available"
