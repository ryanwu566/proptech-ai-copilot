"""Own-account status remains readable while consumer operations are suspended."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from datetime import datetime
from typing import Literal
from uuid import UUID

from backend.api.v1.errors import vnext_error_responses
from backend.api.v1.router import reject_client_identity_overrides
from services.vnext.accounts import AccountAuthorizer, get_account_authorizer
from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal

router = APIRouter(tags=["consumer-account"])


class AccountDTO(BaseModel):
    user_id: UUID
    status: Literal["active", "suspended"]
    platform_role: Literal["consumer", "platform_admin"]
    created_at: datetime
    updated_at: datetime


@router.get("/v1/account", response_model=AccountDTO, responses=vnext_error_responses(401, 422, 503))
def own_account(
    response: Response,
    _identity_boundary: None = Depends(reject_client_identity_overrides),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    authorizer: AccountAuthorizer = Depends(get_account_authorizer),
) -> AccountDTO:
    value = authorizer.get_account(principal)
    response.headers["Cache-Control"] = "no-store"
    return AccountDTO(**value.__dict__)
