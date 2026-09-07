"""Idempotent application service for explicit SavedCase v1 copy imports."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Mapping, Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.legacy_case_import import (
    LEGACY_FORMAT,
    LEGACY_IMPORT_MODE,
    LegacySavedCaseV1Parser,
)
from services.vnext.legacy_case_import_repository import LegacyImportWriteResult
from services.vnext.persistence import CASE_WRITE_ROLES, IdempotencyDecision, IdempotencyReservation


_CLIENT_ID = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
_CANONICAL_ROUTE = "/v1/cases/import-legacy"


class LegacyImportWriter(Protocol):
    def import_case(self, **kwargs: object) -> LegacyImportWriteResult: ...

    def get_import_by_id(self, **kwargs: object) -> LegacyImportWriteResult: ...


class IdempotencyWriter(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...

    def mark_failed(self, **kwargs: object) -> None: ...


@dataclass(frozen=True)
class LegacyCaseImportOutcome:
    result: LegacyImportWriteResult
    replayed: bool


def _canonical(payload: Mapping[str, object]) -> bytes:
    try:
        return json.dumps(
            payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise VNextError.validation_failed() from None


class LegacyCaseImportApplicationService:
    def __init__(
        self,
        *,
        authorizer: WorkspaceAuthorizer,
        repository: LegacyImportWriter,
        idempotency_repository: IdempotencyWriter,
        parser: LegacySavedCaseV1Parser | None = None,
    ) -> None:
        self._authorizer = authorizer
        self._repository = repository
        self._idempotency_repository = idempotency_repository
        self._parser = parser or LegacySavedCaseV1Parser()

    def _mark_failed(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        reservation: IdempotencyReservation,
        error: VNextError,
    ) -> None:
        try:
            self._idempotency_repository.mark_failed(
                principal=principal,
                workspace_id=workspace_id,
                idempotency_record_id=reservation.idempotency_record_id,
                response_status_code=error.status_code,
                response_error_code=error.code.value,
            )
        except Exception:
            pass

    @staticmethod
    def _replay_reference(reservation: IdempotencyReservation) -> UUID:
        if reservation.operation_status == "pending":
            raise VNextError(ErrorCode.MAINTENANCE)
        if reservation.operation_status == "failed":
            try:
                code = ErrorCode(str(reservation.response_error_code))
            except ValueError:
                raise VNextError(ErrorCode.INTERNAL_ERROR) from None
            raise VNextError(code)
        if (
            reservation.operation_status != "succeeded"
            or reservation.response_reference_type != "legacy_case_import"
            or reservation.response_reference_id is None
        ):
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        return reservation.response_reference_id

    def import_case(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        legacy_format: str,
        legacy_client_id: str,
        payload: Mapping[str, object],
        import_mode: str,
        consent: bool,
        idempotency_key: str,
        request_id: str,
    ) -> LegacyCaseImportOutcome:
        if (
            legacy_format != LEGACY_FORMAT
            or import_mode != LEGACY_IMPORT_MODE
            or consent is not True
        ):
            raise VNextError.unsupported_input()
        if not _CLIENT_ID.fullmatch(legacy_client_id):
            raise VNextError.validation_failed()
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        parsed = self._parser.parse(payload)
        legacy_client_id_hash = hashlib.sha256(legacy_client_id.encode("utf-8")).hexdigest()
        canonical_request = _canonical(
            {
                "workspace_id": str(workspace_id),
                "legacy_format": legacy_format,
                "legacy_client_id": legacy_client_id,
                "payload": payload,
                "import_mode": import_mode,
                "consent": consent,
            }
        )
        reservation = self._idempotency_repository.reserve(
            principal=principal,
            workspace_id=workspace_id,
            method="POST",
            canonical_route=_CANONICAL_ROUTE,
            idempotency_key=idempotency_key,
            canonical_request=canonical_request,
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            import_id = self._replay_reference(reservation)
            return LegacyCaseImportOutcome(
                result=self._repository.get_import_by_id(
                    principal=principal, legacy_case_import_id=import_id
                ),
                replayed=True,
            )
        try:
            result = self._repository.import_case(
                principal=principal,
                workspace_id=workspace_id,
                legacy_client_id_hash=legacy_client_id_hash,
                parsed=parsed,
                request_id=request_id,
                idempotency_record_id=reservation.idempotency_record_id,
            )
        except VNextError as error:
            self._mark_failed(
                principal=principal,
                workspace_id=workspace_id,
                reservation=reservation,
                error=error,
            )
            raise
        except Exception:
            error = VNextError(ErrorCode.INTERNAL_ERROR)
            self._mark_failed(
                principal=principal,
                workspace_id=workspace_id,
                reservation=reservation,
                error=error,
            )
            raise error from None
        return LegacyCaseImportOutcome(result=result, replayed=False)
