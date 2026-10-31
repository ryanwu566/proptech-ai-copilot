"""Server-controlled consumer account authority, separate from workspace roles."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol
from uuid import UUID

from fastapi import Depends

from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal
from services.vnext.db_principal import DatabasePrincipalContext, get_vnext_database_principal_context
from services.vnext.errors import ErrorCode, VNextError


@dataclass(frozen=True)
class Account:
    user_id: UUID
    status: str
    platform_role: str
    created_at: datetime
    updated_at: datetime


class AccountRepository(Protocol):
    def get_account(self, *, principal: AuthenticatedPrincipal) -> Account | None: ...


class PostgresAccountRepository:
    def __init__(self, context_provider: Callable[[], DatabasePrincipalContext] = get_vnext_database_principal_context):
        self._context_provider = context_provider

    def get_account(self, *, principal: AuthenticatedPrincipal) -> Account | None:
        # Request role can INSERT only user_id; defaults and RLS pin consumer/active.
        # Conflict never overwrites suspension or any existing authoritative role.
        with self._context_provider().transaction(principal) as connection:
            connection.execute(
                "INSERT INTO vnext_private.consumer_accounts (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (principal.user_id,),
            )
            row = connection.execute(
                "SELECT user_id, status, platform_role, created_at, updated_at "
                "FROM vnext_private.consumer_accounts WHERE user_id = %s", (principal.user_id,),
            ).fetchone()
        return Account(UUID(str(row[0])), str(row[1]), str(row[2]), row[3], row[4]) if row else None


class AccountAuthorizer:
    def __init__(self, repository: AccountRepository):
        self._repository = repository

    def get_account(self, principal: AuthenticatedPrincipal) -> Account:
        try:
            value = self._repository.get_account(principal=principal)
            if (value is None or value.user_id != principal.user_id
                or value.status not in {"active", "suspended"}
                or value.platform_role not in {"consumer", "platform_admin"}
                or not isinstance(value.created_at, datetime) or not isinstance(value.updated_at, datetime)):
                raise ValueError("unavailable account")
            return value
        except Exception:
            raise VNextError(ErrorCode.ACCOUNT_UNAVAILABLE) from None

    def require_active(self, principal: AuthenticatedPrincipal) -> Account:
        value = self.get_account(principal)
        if value.status != "active":
            raise VNextError(ErrorCode.ACCOUNT_SUSPENDED)
        return value

    def require_platform_admin(self, principal: AuthenticatedPrincipal) -> Account:
        value = self.require_active(principal)
        if value.platform_role != "platform_admin":
            raise VNextError.permission_denied()
        return value


_DEFAULT_AUTHORIZER = AccountAuthorizer(PostgresAccountRepository())


def get_account_authorizer() -> AccountAuthorizer:
    from services.professor_userdb import enabled, get_repository
    if enabled():
        return AccountAuthorizer(get_repository())
    return _DEFAULT_AUTHORIZER


def require_active_account(
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    authorizer: AccountAuthorizer = Depends(get_account_authorizer),
) -> Account:
    account = authorizer.require_active(principal)
    from services.api_usage import admit_authenticated_usage
    admit_authenticated_usage(principal)
    return account
