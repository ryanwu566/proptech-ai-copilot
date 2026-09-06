"""FastAPI rendering for the VNext error envelope."""

from __future__ import annotations

from typing import Annotated

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from services.observability import normalize_correlation_id
from services.vnext.errors import ErrorCode, VNextError


class VNextErrorDTO(BaseModel):
    """The complete allowlisted public error payload."""

    model_config = ConfigDict(extra="forbid")
    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=512)]
    request_id: Annotated[str, Field(min_length=1, max_length=128)]
    retryable: bool
    details: dict[str, object] | None = None


class VNextErrorEnvelopeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: VNextErrorDTO


def vnext_error_responses(*status_codes: int) -> dict[int, dict[str, object]]:
    """Attach one bounded error contract to every declared VNext failure."""

    return {status_code: {"model": VNextErrorEnvelopeDTO} for status_code in status_codes}


def request_id(request: Request) -> str:
    return getattr(
        request.state,
        "correlation_id",
        normalize_correlation_id(request.headers.get("X-Correlation-ID")),
    )


def structured_error_response(
    request: Request,
    error: VNextError,
) -> JSONResponse:
    payload: dict[str, object] = {
        "code": error.code.value,
        "message": error.message,
        "request_id": request_id(request),
        "retryable": error.retryable,
    }
    if error.details:
        payload["details"] = error.details
    headers = {"Cache-Control": "private, no-store"}
    if error.code == ErrorCode.AUTHENTICATION_REQUIRED:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=error.status_code,
        content={"error": payload},
        headers=headers,
    )


async def vnext_error_handler(request: Request, error: VNextError) -> JSONResponse:
    return structured_error_response(request, error)
