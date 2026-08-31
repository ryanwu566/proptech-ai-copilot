"""Application orchestration for non-confirming identity-resolution commands."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_resolution import (
    IdentityResolutionEngine,
    ResolutionAttemptStatus,
    ResolutionErrorCategory,
    ResolutionInputType,
    normalize_resolution_input,
)
from services.vnext.identity_resolution_repository import (
    IDENTITY_WRITE_ROLES,
    IdentityResolutionRecord,
)
from services.vnext.persistence import IdempotencyDecision, IdempotencyReservation
from services.vnext.property_graph import DATA_SOURCE_REGISTRY, SourceEnvironment

CANONICAL_RESOLUTION_ROUTE = "/v1/property-resolutions"


class ResolutionRepository(Protocol):
    def append_resolution(self, **kwargs: object) -> IdentityResolutionRecord: ...

    def get_resolution_by_id(
        self,
        *,
        principal: AuthenticatedPrincipal,
        identity_resolution_id: UUID,
    ) -> IdentityResolutionRecord: ...


class IdempotencyRepository(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...

    def mark_failed(self, **kwargs: object) -> None: ...


class CaseReader(Protocol):
    def get_case(self, **kwargs: object) -> object: ...


@dataclass(frozen=True)
class ResolutionCreateOutcome:
    resolution: IdentityResolutionRecord
    status_code: int
    replayed: bool


class _AttemptView(Protocol):
    status: ResolutionAttemptStatus
    error_category: ResolutionErrorCategory | None


def _canonical_request(
    *,
    workspace_id: UUID,
    input_type: ResolutionInputType,
    raw_input: Mapping[str, object],
    case_id: UUID | None,
) -> bytes:
    payload = {
        "workspace_id": str(workspace_id),
        "input": {"kind": input_type.value, "value": dict(raw_input)},
        "case_id": None if case_id is None else str(case_id),
    }
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _completion_error_values(
    *,
    resolution_id: UUID | None,
    state: str,
    attempts: Sequence[_AttemptView],
    candidate_count: int,
) -> VNextError | None:
    if candidate_count or any(
        attempt.status is ResolutionAttemptStatus.NO_MATCH for attempt in attempts
    ):
        return None
    details = (
        {}
        if resolution_id is None
        else {
            "resolution_id": str(resolution_id),
            "state": state,
        }
    )
    if any(
        attempt.error_category is ResolutionErrorCategory.RATE_LIMITED
        for attempt in attempts
    ):
        return VNextError(ErrorCode.RATE_LIMITED, details=details)
    if attempts and all(
        attempt.status is ResolutionAttemptStatus.UNSUPPORTED for attempt in attempts
    ):
        return VNextError(ErrorCode.UNSUPPORTED_INPUT, details=details)
    if any(
        attempt.status
        in {
            ResolutionAttemptStatus.UNAVAILABLE,
            ResolutionAttemptStatus.TIMEOUT,
            ResolutionAttemptStatus.ERROR,
        }
        for attempt in attempts
    ):
        return VNextError.provider_unavailable(details=details)
    return None


def _completion_error(record: IdentityResolutionRecord) -> VNextError | None:
    return _completion_error_values(
        resolution_id=record.identity_resolution_id,
        state=record.status.value,
        attempts=record.attempts,
        candidate_count=len(record.candidates),
    )


class IdentityResolutionApplicationService:
    """Authorize, deduplicate, resolve, persist, and replay one POST command."""

    def __init__(
        self,
        *,
        authorizer: WorkspaceAuthorizer,
        engine: IdentityResolutionEngine,
        resolution_repository: ResolutionRepository,
        idempotency_repository: IdempotencyRepository,
        case_repository: CaseReader,
        runtime_environment: str | None = None,
    ) -> None:
        self._authorizer = authorizer
        self._engine = engine
        self._resolution_repository = resolution_repository
        self._idempotency_repository = idempotency_repository
        self._case_repository = case_repository
        self._runtime_environment = (
            (runtime_environment or os.getenv("APP_ENV", "development")).strip().lower()
        )

    def _verify_provider_boundary(self) -> None:
        production = self._runtime_environment in {"production", "preview"}
        for provider in self._engine.providers:
            environment = provider.source_environment
            source = DATA_SOURCE_REGISTRY.get(str(provider.source_id).strip())
            if (
                environment is SourceEnvironment.TEST
                and self._runtime_environment != "test"
            ):
                raise VNextError.provider_unavailable()
            if (
                environment is SourceEnvironment.DEMO
                and self._runtime_environment
                not in {
                    "demo",
                    "development",
                }
            ):
                raise VNextError.provider_unavailable()
            if production and (
                environment is not SourceEnvironment.PRODUCTION
                or source is None
                or source.readiness != "production_accepted"
            ):
                raise VNextError.provider_unavailable()

    def _safe_mark_failed(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        reservation: IdempotencyReservation,
        status_code: int,
    ) -> None:
        try:
            self._idempotency_repository.mark_failed(
                principal=principal,
                workspace_id=workspace_id,
                idempotency_record_id=reservation.idempotency_record_id,
                response_status_code=status_code,
            )
        except Exception:
            # The original error remains the safe client result. A pending key
            # still fails closed and is never reused for another request body.
            pass

    def get(
        self,
        *,
        principal: AuthenticatedPrincipal,
        identity_resolution_id: UUID,
    ) -> IdentityResolutionRecord:
        return self._resolution_repository.get_resolution_by_id(
            principal=principal,
            identity_resolution_id=identity_resolution_id,
        )

    def create(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        input_type: ResolutionInputType,
        raw_input: Mapping[str, object],
        case_id: UUID | None,
        idempotency_key: str,
    ) -> ResolutionCreateOutcome:
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=IDENTITY_WRITE_ROLES,
        )
        # Validate normalization and an optional Case before reserving a key or
        # calling any provider. The repository/RLS remains the second boundary.
        normalize_resolution_input(input_type, raw_input)
        if case_id is not None:
            self._case_repository.get_case(
                principal=principal,
                workspace_id=workspace_id,
                case_id=case_id,
            )
        canonical_request = _canonical_request(
            workspace_id=workspace_id,
            input_type=input_type,
            raw_input=raw_input,
            case_id=case_id,
        )
        reservation = self._idempotency_repository.reserve(
            principal=principal,
            workspace_id=workspace_id,
            method="POST",
            canonical_route=CANONICAL_RESOLUTION_ROUTE,
            idempotency_key=idempotency_key,
            canonical_request=canonical_request,
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            if reservation.operation_status == "pending":
                raise VNextError(ErrorCode.MAINTENANCE)
            if (
                reservation.response_reference_type != "identity_resolution"
                or reservation.response_reference_id is None
            ):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            record = self.get(
                principal=principal,
                identity_resolution_id=reservation.response_reference_id,
            )
            error = _completion_error(record)
            if error is not None:
                raise error
            return ResolutionCreateOutcome(
                resolution=record,
                status_code=reservation.response_status_code or 201,
                replayed=True,
            )

        try:
            self._verify_provider_boundary()
            draft = self._engine.resolve(
                input_type=input_type,
                raw_input=raw_input,
            )
            provisional_error = _completion_error_values(
                resolution_id=None,
                state=draft.status.value,
                attempts=draft.attempts,
                candidate_count=len(draft.candidates),
            )
            response_status = (
                201 if provisional_error is None else provisional_error.status_code
            )
            record = self._resolution_repository.append_resolution(
                principal=principal,
                workspace_id=workspace_id,
                case_id=case_id,
                draft=draft,
                idempotency_record_id=reservation.idempotency_record_id,
                idempotency_response_status_code=response_status,
                idempotency_operation_status=(
                    "succeeded" if provisional_error is None else "failed"
                ),
            )
        except VNextError as error:
            self._safe_mark_failed(
                principal=principal,
                workspace_id=workspace_id,
                reservation=reservation,
                status_code=error.status_code,
            )
            raise
        except Exception:
            self._safe_mark_failed(
                principal=principal,
                workspace_id=workspace_id,
                reservation=reservation,
                status_code=500,
            )
            raise VNextError(ErrorCode.INTERNAL_ERROR) from None

        error = _completion_error(record)
        if error is not None:
            raise error
        return ResolutionCreateOutcome(
            resolution=record,
            status_code=201,
            replayed=False,
        )
