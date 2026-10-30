"""Owner-only application data; Supabase remains the identity provider."""
from datetime import datetime
import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.api.durable_cases import no_store
from backend.api.v1.errors import vnext_error_responses
from backend.api.v1.router import reject_client_identity_overrides
from services.professor_userdb import UserRepository, get_repository
from services.vnext.accounts import require_active_account
from services.vnext.auth import AuthenticatedPrincipal, require_authenticated_principal
from services.vnext.durable_cases import get_case_service, validate_safe_json
from services.vnext.errors import VNextError


router = APIRouter(prefix='/v1', tags=['user-data'],
    dependencies=[Depends(require_authenticated_principal), Depends(require_active_account),
                  Depends(reject_client_identity_overrides),Depends(no_store)],
    responses=vnext_error_responses(401,403,404,409,422,429,503))


class StrictBody(BaseModel):
    model_config=ConfigDict(extra='forbid')


class ProfileUpdate(StrictBody):
    expected_revision: int=Field(strict=True,ge=1)
    display_name: str | None=Field(None,max_length=80)
    locale: Literal['zh-TW','en','ja','ko'] | None=None

    @model_validator(mode='after')
    def bounded(self):
        fields=self.model_fields_set & {'display_name','locale'}
        if not fields or any(getattr(self,k) is None for k in fields):
            raise ValueError('profile_fields_required')
        validate_safe_json(self.display_name)
        return self


class PreferencesUpdate(StrictBody):
    expected_revision: int=Field(strict=True,ge=1)
    data: dict

    @model_validator(mode='after')
    def bounded(self):
        validate_safe_json(self.data)
        if len(json.dumps(self.data,ensure_ascii=False,allow_nan=False).encode())>24576:
            raise ValueError('preferences_too_large')
        return self


class ReportCreate(StrictBody):
    case_id: UUID
    title: str=Field(min_length=1,max_length=200)
    payload: dict

    @model_validator(mode='after')
    def bounded(self):
        validate_safe_json([self.title,self.payload])
        if len(json.dumps(self.payload,ensure_ascii=False,allow_nan=False).encode())>131072:
            raise ValueError('report_too_large')
        return self


class ProfileView(BaseModel):
    user_id: UUID
    revision: int
    display_name: str
    locale: Literal['zh-TW','en','ja','ko']
    created_at: datetime
    updated_at: datetime


class PreferencesView(BaseModel):
    user_id: UUID
    revision: int
    data: dict
    created_at: datetime
    updated_at: datetime


class ReportView(BaseModel):
    id: UUID
    case_id: UUID
    title: str
    payload: dict
    provenance: Literal['user_supplied_unverified']
    created_at: datetime


@router.get('/session')
def session(p: AuthenticatedPrincipal=Depends(require_authenticated_principal), repo: UserRepository=Depends(get_repository)):
    return {'status':'authenticated','user_id':p.user_id,'session_id':p.session_id,'expires_at':p.token_expires_at}


@router.post('/session/logout')
def logout(p: AuthenticatedPrincipal=Depends(require_authenticated_principal), repo: UserRepository=Depends(get_repository)):
    repo.logout(p)
    return {'status':'revoked'}


@router.get('/profile',response_model=ProfileView)
def profile(p: AuthenticatedPrincipal=Depends(require_authenticated_principal), repo: UserRepository=Depends(get_repository)):
    return repo.profile(p)


@router.patch('/profile',response_model=ProfileView)
def update_profile(body: ProfileUpdate, p: AuthenticatedPrincipal=Depends(require_authenticated_principal), repo: UserRepository=Depends(get_repository)):
    return repo.update_profile(p,body.expected_revision,body.model_dump(include=body.model_fields_set & {'display_name','locale'}))


@router.get('/preferences',response_model=PreferencesView)
def preferences(p: AuthenticatedPrincipal=Depends(require_authenticated_principal), repo: UserRepository=Depends(get_repository)):
    return repo.preferences(p)


@router.put('/preferences',response_model=PreferencesView)
def update_preferences(body: PreferencesUpdate,p: AuthenticatedPrincipal=Depends(require_authenticated_principal),repo: UserRepository=Depends(get_repository)):
    return repo.update_preferences(p,body.expected_revision,body.data)


@router.delete('/saved-cases/{case_id}',status_code=204)
def delete_case(case_id: UUID, expected_revision: int=Query(ge=1),
                p: AuthenticatedPrincipal=Depends(require_authenticated_principal),service=Depends(get_case_service)):
    if not hasattr(service,'delete'): raise VNextError.unsupported_input()
    service.delete(p,case_id,expected_revision)
    return Response(status_code=204,headers={'Cache-Control':'no-store'})


@router.post('/reports',response_model=ReportView,status_code=201)
def create_report(body: ReportCreate,p: AuthenticatedPrincipal=Depends(require_authenticated_principal),repo: UserRepository=Depends(get_repository)):
    return repo.create_report(p,body.case_id,body.title,body.payload)


@router.get('/reports',response_model=list[ReportView])
def reports(offset: int=Query(0,ge=0,le=10000),limit: int=Query(20,ge=1,le=100),
            p: AuthenticatedPrincipal=Depends(require_authenticated_principal),repo: UserRepository=Depends(get_repository)):
    return repo.reports(p,offset,limit)


@router.get('/reports/{report_id}',response_model=ReportView)
def report(report_id: UUID,p: AuthenticatedPrincipal=Depends(require_authenticated_principal),repo: UserRepository=Depends(get_repository)):
    return repo.report(p,report_id)


@router.delete('/reports/{report_id}',status_code=204)
def delete_report(report_id: UUID,p: AuthenticatedPrincipal=Depends(require_authenticated_principal),repo: UserRepository=Depends(get_repository)):
    repo.delete_report(p,report_id)
    return Response(status_code=204,headers={'Cache-Control':'no-store'})
