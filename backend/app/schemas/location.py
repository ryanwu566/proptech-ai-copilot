from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class LocationResolveRequest(BaseModel):
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class LocationResolveResponse(BaseModel):
    status: Literal["resolved", "unresolved", "unavailable"]
    source: Literal["tgos", "google", "none"]
    formatted_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: Literal["high", "medium", "unknown"]
    message: str