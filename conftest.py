"""Repository-wide pytest safety boundary for database configuration.

Application database URLs are runtime configuration, not test configuration.
They are removed before test-module collection so an inherited shell or CI
environment can never make an ordinary pytest run contact an external database.

Real database tests must use a dedicated, allow-listed URL and an independent
destructive/disposable confirmation.  The VNext RLS proof is currently the only
such test contract.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from urllib.parse import unquote, urlsplit

import pytest


APPLICATION_DATABASE_URL_SUFFIX = "_DATABASE_URL"
APPLICATION_DATABASE_URL_NAME = "DATABASE_URL"

VNEXT_RLS_DATABASE_URL_ENV = "VNEXT_RLS_POSTGRES_URL"
VNEXT_RLS_DISPOSABLE_ENV = "VNEXT_RLS_POSTGRES_DISPOSABLE"
VNEXT_RLS_DATABASE_PREFIX = "vnext_rls_test"

_removed_inherited_database_variables: tuple[str, ...] = ()


def remove_application_database_urls(
    environ: MutableMapping[str, str],
) -> tuple[str, ...]:
    """Remove inherited application URLs while leaving dedicated test URLs alone."""

    removed = tuple(
        sorted(
            name
            for name in environ
            if name == APPLICATION_DATABASE_URL_NAME
            or name.endswith(APPLICATION_DATABASE_URL_SUFFIX)
        )
    )
    for name in removed:
        environ.pop(name, None)
    return removed


def validate_vnext_rls_test_contract(environ: MutableMapping[str, str]) -> None:
    """Fail closed before collection when the disposable RLS target is unsafe."""

    database_url = environ.get(VNEXT_RLS_DATABASE_URL_ENV, "").strip()
    disposable = environ.get(VNEXT_RLS_DISPOSABLE_ENV) == "1"
    if not database_url:
        return
    if not disposable:
        # An incomplete integration contract behaves like no integration target:
        # the test skips and no connection can be attempted.
        environ.pop(VNEXT_RLS_DATABASE_URL_ENV, None)
        return

    parsed = urlsplit(database_url)
    database_name = unquote(parsed.path.lstrip("/")).split("/", 1)[0]
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.hostname
        or not database_name.startswith(VNEXT_RLS_DATABASE_PREFIX)
    ):
        raise pytest.UsageError(
            "VNEXT_RLS_POSTGRES_URL must be a PostgreSQL URL for a dedicated "
            "database beginning with vnext_rls_test"
        )


def pytest_configure(config: pytest.Config) -> None:
    """Sanitize inherited database configuration before tests are collected."""

    config.addinivalue_line(
        "markers",
        "external_database: explicitly gated test using a dedicated disposable database URL",
    )
    global _removed_inherited_database_variables
    _removed_inherited_database_variables = remove_application_database_urls(os.environ)
    validate_vnext_rls_test_contract(os.environ)


def pytest_report_header(config: pytest.Config) -> str:
    """Make active protection visible without ever printing secret values."""

    del config
    if not _removed_inherited_database_variables:
        return "hermetic database safety: no inherited application URLs present"
    names = ", ".join(_removed_inherited_database_variables)
    return f"hermetic database safety: removed inherited {names}"
