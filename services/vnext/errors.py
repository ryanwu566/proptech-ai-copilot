"""Safe, structured VNext application errors."""

from __future__ import annotations

from enum import Enum
from typing import Mapping


class ErrorCode(str, Enum):
    AUTHENTICATION_REQUIRED = "authentication_required"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_FAILED = "validation_failed"
    UNSUPPORTED_INPUT = "unsupported_input"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    COVERAGE_UNAVAILABLE = "coverage_unavailable"
    AMBIGUOUS_IDENTITY = "ambiguous_identity"
    STALE_EVIDENCE = "stale_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    NOT_FOUND = "not_found"
    VERSION_CONFLICT = "version_conflict"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    DUPLICATE_LEGACY_IMPORT = "duplicate_legacy_import"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"
    INTERNAL_ERROR = "internal_error"


_DEFAULTS: dict[ErrorCode, tuple[int, str, bool]] = {
    ErrorCode.AUTHENTICATION_REQUIRED: (401, "Authentication is required.", False),
    ErrorCode.PERMISSION_DENIED: (403, "Permission is denied.", False),
    ErrorCode.VALIDATION_FAILED: (422, "The request is invalid.", False),
    ErrorCode.UNSUPPORTED_INPUT: (422, "The input is not supported.", False),
    ErrorCode.PROVIDER_UNAVAILABLE: (503, "An identity provider is unavailable.", True),
    ErrorCode.COVERAGE_UNAVAILABLE: (503, "Source coverage is unavailable.", True),
    ErrorCode.AMBIGUOUS_IDENTITY: (409, "Identity requires confirmation.", False),
    ErrorCode.STALE_EVIDENCE: (409, "Identity evidence is stale.", False),
    ErrorCode.CONFLICTING_EVIDENCE: (409, "Identity evidence is conflicting.", False),
    ErrorCode.NOT_FOUND: (404, "The requested resource was not found.", False),
    ErrorCode.VERSION_CONFLICT: (409, "The resource version has changed.", False),
    ErrorCode.IDEMPOTENCY_CONFLICT: (409, "The idempotency key conflicts with an earlier request.", False),
    ErrorCode.DUPLICATE_LEGACY_IMPORT: (409, "This legacy case was already imported.", False),
    ErrorCode.RATE_LIMITED: (429, "The request rate limit was reached.", True),
    ErrorCode.MAINTENANCE: (503, "The service is temporarily unavailable.", True),
    ErrorCode.INTERNAL_ERROR: (500, "The request could not be completed.", False),
}


class VNextError(Exception):
    """An allowlisted client error with no provider or exception payload."""

    def __init__(
        self,
        code: ErrorCode,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        status_code, message, retryable = _DEFAULTS[code]
        super().__init__(code.value)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.retryable = retryable
        # Details are supplied only by bounded application call sites. Never
        # put an exception, SQL, token, provider body, or credential here.
        self.details = dict(details or {})

    @classmethod
    def authentication_required(cls) -> "VNextError":
        return cls(ErrorCode.AUTHENTICATION_REQUIRED)

    @classmethod
    def permission_denied(cls) -> "VNextError":
        return cls(ErrorCode.PERMISSION_DENIED)

    @classmethod
    def validation_failed(cls) -> "VNextError":
        return cls(ErrorCode.VALIDATION_FAILED)

    @classmethod
    def unsupported_input(cls) -> "VNextError":
        return cls(ErrorCode.UNSUPPORTED_INPUT)

    @classmethod
    def provider_unavailable(
        cls,
        *,
        details: Mapping[str, object] | None = None,
    ) -> "VNextError":
        return cls(ErrorCode.PROVIDER_UNAVAILABLE, details=details)

    @classmethod
    def stale_evidence(cls) -> "VNextError":
        return cls(ErrorCode.STALE_EVIDENCE)

    @classmethod
    def conflicting_evidence(cls) -> "VNextError":
        return cls(ErrorCode.CONFLICTING_EVIDENCE)

    @classmethod
    def not_found(cls) -> "VNextError":
        return cls(ErrorCode.NOT_FOUND)

    @classmethod
    def version_conflict(cls) -> "VNextError":
        return cls(ErrorCode.VERSION_CONFLICT)

    @classmethod
    def idempotency_conflict(cls) -> "VNextError":
        return cls(ErrorCode.IDEMPOTENCY_CONFLICT)

    @classmethod
    def duplicate_legacy_import(
        cls,
        *,
        details: Mapping[str, object] | None = None,
    ) -> "VNextError":
        return cls(ErrorCode.DUPLICATE_LEGACY_IMPORT, details=details)
