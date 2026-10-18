"""Closed command DTOs; callers supply a retry key and a bounded reason."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid')
    command_id: UUID
    reason: Annotated[str, Field(min_length=1, max_length=500)]

    @field_validator('reason')
    @classmethod
    def valid_reason(cls, value):
        if not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError('A bounded reason is required')
        return value


class AccountCommand(Command):
    field: Literal['status', 'platform_role']
    value: Literal['active', 'suspended', 'consumer', 'platform_admin']

    @model_validator(mode='after')
    def field_value(self):
        if self.value not in ({'active','suspended'} if self.field == 'status' else {'consumer','platform_admin'}):
            raise ValueError('Invalid field value')
        return self


class QuotaCommand(Command):
    principal_class: Literal['authenticated', 'anonymous']
    request_hour: Annotated[int, Field(strict=True, ge=1, le=100000)]
    operation_hour: Annotated[int, Field(strict=True, ge=1, le=100000)]
    operation_day: Annotated[int, Field(strict=True, ge=1, le=1000000)]


class QuotaPolicy(BaseModel):
    principal_class: Literal['authenticated', 'anonymous']
    request_hour: int
    operation_hour: int
    operation_day: int
