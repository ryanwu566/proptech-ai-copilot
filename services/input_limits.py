"""Shared resource ceilings for public query DTOs."""
from pydantic import BaseModel, ConfigDict


class BoundedInputModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_max_length=512)
