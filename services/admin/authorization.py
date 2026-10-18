"""Admin authorization reuses the Wave 1A authoritative account contract."""
from fastapi import Depends
from services.vnext.accounts import AccountAuthorizer, get_account_authorizer
from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal


def require_platform_admin(
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    authorizer: AccountAuthorizer = Depends(get_account_authorizer),
) -> AuthenticatedPrincipal:
    authorizer.require_active(principal)
    authorizer.require_platform_admin(principal)
    return principal
