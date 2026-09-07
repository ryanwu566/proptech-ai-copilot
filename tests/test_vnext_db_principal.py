from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.db_principal import (
    DatabasePrincipalContext,
    DatabasePrincipalContextError,
    get_vnext_database_principal_context,
)


def _principal(value: str) -> AuthenticatedPrincipal:
    user_id = UUID(value)
    return AuthenticatedPrincipal(
        user_id=user_id,
        token_subject=str(user_id),
        issuer="https://fixture.supabase.co/auth/v1",
        token_issued_at=datetime.now(timezone.utc),
    )


PRINCIPAL_A = _principal("11111111-1111-4111-8111-111111111111")
PRINCIPAL_B = _principal("22222222-2222-4222-8222-222222222222")


class _Result:
    def __init__(self, row=None) -> None:
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(
        self,
        *,
        role: str = "vnext_api",
        superuser: bool = False,
        bypass_rls: bool = False,
        owns_vnext: bool = False,
    ) -> None:
        self.role = role
        self.superuser = superuser
        self.bypass_rls = bypass_rls
        self.owns_vnext = owns_vnext
        self.local_settings: dict[str, str] = {}
        self.transaction_count = 0
        self.rollback_count = 0
        self.sql: list[tuple[str, tuple[object, ...] | None]] = []

    @contextmanager
    def transaction(self):
        self.transaction_count += 1
        try:
            yield
        except Exception:
            self.rollback_count += 1
            raise
        finally:
            # Models SET LOCAL: commit and rollback both discard the settings.
            self.local_settings.clear()

    def execute(self, statement: str, params: tuple[object, ...] | None = None):
        normalized = " ".join(statement.lower().split())
        self.sql.append((normalized, params))
        if normalized.startswith("select rolname, rolsuper, rolbypassrls"):
            return _Result((self.role, self.superuser, self.bypass_rls))
        if normalized.startswith("select exists") and "pg_namespace" in normalized:
            return _Result((self.owns_vnext,))
        if "set_config('request.jwt.claim.sub'" in normalized:
            assert params is not None
            self.local_settings["request.jwt.claim.sub"] = str(params[0])
            return _Result((str(params[0]),))
        if "set_config('request.jwt.claims'" in normalized:
            assert params is not None
            self.local_settings["request.jwt.claims"] = str(params[0])
            return _Result((str(params[0]),))
        if "current_setting('request.jwt.claim.sub'" in normalized:
            return _Result((self.local_settings.get("request.jwt.claim.sub"),))
        raise AssertionError(f"unexpected SQL: {normalized}")


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.shared_connection = connection
        self.checkout_count = 0
        self.closed = False

    @contextmanager
    def connection(self):
        self.checkout_count += 1
        yield self.shared_connection

    def close(self) -> None:
        self.closed = True


def test_principals_are_transaction_local_on_a_reused_pool_connection() -> None:
    connection = _Connection()
    context = DatabasePrincipalContext(_Pool(connection))

    with context.transaction(PRINCIPAL_A) as transaction_a:
        assert transaction_a.local_settings["request.jwt.claim.sub"] == str(
            PRINCIPAL_A.user_id
        )
        assert json.loads(transaction_a.local_settings["request.jwt.claims"]) == {
            "sub": str(PRINCIPAL_A.user_id)
        }
    assert connection.local_settings == {}

    with context.transaction(PRINCIPAL_B) as transaction_b:
        assert transaction_b.local_settings["request.jwt.claim.sub"] == str(
            PRINCIPAL_B.user_id
        )
        assert str(PRINCIPAL_A.user_id) not in transaction_b.local_settings.values()
    assert connection.local_settings == {}
    assert connection.transaction_count == 2


def test_principal_context_is_cleared_after_exception() -> None:
    connection = _Connection()
    context = DatabasePrincipalContext(_Pool(connection))

    with pytest.raises(RuntimeError):
        with context.transaction(PRINCIPAL_A) as transaction:
            assert transaction.local_settings["request.jwt.claim.sub"] == str(
                PRINCIPAL_A.user_id
            )
            raise RuntimeError("synthetic handler failure")

    assert connection.local_settings == {}
    assert connection.rollback_count == 1
    with context.transaction(PRINCIPAL_B) as transaction:
        assert transaction.local_settings["request.jwt.claim.sub"] == str(
            PRINCIPAL_B.user_id
        )


@pytest.mark.parametrize(
    ("role", "superuser", "bypass_rls", "owns_vnext"),
    [
        ("postgres", True, True, True),
        ("service_role", False, True, False),
        ("vnext_api", True, False, False),
        ("vnext_api", False, True, False),
        ("vnext_api", False, False, True),
        ("legacy_owner", False, False, False),
    ],
)
def test_privileged_or_unexpected_database_roles_are_rejected(
    role: str,
    superuser: bool,
    bypass_rls: bool,
    owns_vnext: bool,
) -> None:
    connection = _Connection(
        role=role,
        superuser=superuser,
        bypass_rls=bypass_rls,
        owns_vnext=owns_vnext,
    )
    context = DatabasePrincipalContext(_Pool(connection))

    with pytest.raises(DatabasePrincipalContextError) as error:
        with context.transaction(PRINCIPAL_A):
            raise AssertionError("unsafe role entered request transaction")

    assert error.value.args == ("database_request_role_unsafe",)
    assert connection.local_settings == {}


def test_principal_settings_are_explicitly_transaction_local() -> None:
    connection = _Connection()
    context = DatabasePrincipalContext(_Pool(connection))

    with context.transaction(PRINCIPAL_A):
        pass

    set_config_calls = [item for item in connection.sql if "set_config" in item[0]]
    assert len(set_config_calls) == 2
    assert all(call[0].endswith(", %s, true)") for call in set_config_calls)


def test_vnext_pool_never_falls_back_to_legacy_owner_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_vnext_database_principal_context.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql://legacy-owner.invalid/database")
    monkeypatch.delenv("VNEXT_DATABASE_URL", raising=False)
    try:
        with pytest.raises(DatabasePrincipalContextError) as error:
            get_vnext_database_principal_context()
    finally:
        get_vnext_database_principal_context.cache_clear()

    assert error.value.args == ("database_request_role_unavailable",)


def test_principal_context_closes_its_pool() -> None:
    pool = _Pool(_Connection())
    context = DatabasePrincipalContext(pool)

    context.close()

    assert pool.closed is True
