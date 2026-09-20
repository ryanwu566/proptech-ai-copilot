"""Idempotent application boundary for Case-local parcel-set review."""

from __future__ import annotations

import json
import re
from typing import Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.case_parcel_set import (
    CaseParcelSetOutcome,
    CaseParcelSetRecord,
    ParcelMemberReviewStatus,
)
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.persistence import (
    CASE_WRITE_ROLES,
    IdempotencyDecision,
    IdempotencyReservation,
)


_RESPONSE_TYPE = "case_parcel_set"
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")


class CaseParcelSetWriter(Protocol):
    def require_case(self, **kwargs: object) -> None: ...

    def get(self, **kwargs: object) -> CaseParcelSetRecord: ...

    def initialize(self, **kwargs: object) -> CaseParcelSetRecord: ...

    def add_member(self, **kwargs: object) -> CaseParcelSetRecord: ...

    def review_member(self, **kwargs: object) -> CaseParcelSetRecord: ...

    def set_active_member(self, **kwargs: object) -> CaseParcelSetRecord: ...

    def reorder(self, **kwargs: object) -> CaseParcelSetRecord: ...

    def mark_case_reviewed(self, **kwargs: object) -> CaseParcelSetRecord: ...


class IdempotencyWriter(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...

    def mark_failed(self, **kwargs: object) -> None: ...


def _canonical(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _validate_command_metadata(idempotency_key: str, request_id: str) -> None:
    if not _IDEMPOTENCY_KEY.fullmatch(idempotency_key):
        raise VNextError.validation_failed()
    if not request_id.strip() or len(request_id) > 128 or "\x00" in request_id:
        raise VNextError.validation_failed()


class CaseParcelSetApplicationService:
    def __init__(
        self,
        *,
        authorizer: WorkspaceAuthorizer,
        writer: CaseParcelSetWriter,
        idempotency_repository: IdempotencyWriter,
    ) -> None:
        self._authorizer = authorizer
        self._writer = writer
        self._idempotency_repository = idempotency_repository

    def get(
        self,
        *,
        principal: AuthenticatedPrincipal,
        case_id: UUID,
    ) -> CaseParcelSetRecord:
        return self._writer.get(principal=principal, case_id=case_id)

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
            or reservation.response_reference_type != _RESPONSE_TYPE
            or reservation.response_reference_id is None
        ):
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        return reservation.response_reference_id

    def _execute(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        expected_version: int,
        idempotency_key: str,
        request_id: str,
        canonical_route: str,
        canonical_fields: dict[str, object],
        operation: str,
        operation_fields: dict[str, object],
    ) -> CaseParcelSetOutcome:
        _validate_command_metadata(idempotency_key, request_id)
        self._authorizer.require_workspace_role(
            principal,
            workspace_id,
            allowed_roles=CASE_WRITE_ROLES,
        )
        self._writer.require_case(
            principal=principal,
            workspace_id=workspace_id,
            case_id=case_id,
        )
        reservation = self._idempotency_repository.reserve(
            principal=principal,
            workspace_id=workspace_id,
            method="POST",
            canonical_route=canonical_route,
            idempotency_key=idempotency_key,
            canonical_request=_canonical(
                {
                    "workspace_id": str(workspace_id),
                    "case_id": str(case_id),
                    "expected_version": expected_version,
                    **canonical_fields,
                }
            ),
            conflict_scope="case_parcel_set",
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            parcel_set_id = self._replay_reference(reservation)
            record = self._writer.get(principal=principal, case_id=case_id)
            if (
                record.parcel_set_id != parcel_set_id
                or record.workspace_id != workspace_id
                or record.case_id != case_id
            ):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            return CaseParcelSetOutcome(record=record, replayed=True)

        try:
            writer_method = getattr(self._writer, operation)
            record = writer_method(
                principal=principal,
                workspace_id=workspace_id,
                case_id=case_id,
                expected_version=expected_version,
                idempotency_record_id=reservation.idempotency_record_id,
                request_id=request_id,
                **operation_fields,
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
        return CaseParcelSetOutcome(record=record, replayed=False)

    def initialize(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        expected_version: int,
        idempotency_key: str,
        request_id: str,
    ) -> CaseParcelSetOutcome:
        if expected_version != 0:
            raise VNextError.validation_failed()
        return self._execute(
            principal=principal,
            workspace_id=workspace_id,
            case_id=case_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            canonical_route=f"/v1/cases/{case_id}/parcel-set",
            canonical_fields={},
            operation="initialize",
            operation_fields={},
        )

    def add_member(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        parcel_identity_reference_id: UUID,
        expected_version: int,
        idempotency_key: str,
        request_id: str,
    ) -> CaseParcelSetOutcome:
        self._require_existing_version(expected_version)
        return self._execute(
            principal=principal,
            workspace_id=workspace_id,
            case_id=case_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            canonical_route=f"/v1/cases/{case_id}/parcel-set/members",
            canonical_fields={
                "parcel_identity_reference_id": str(parcel_identity_reference_id)
            },
            operation="add_member",
            operation_fields={
                "parcel_identity_reference_id": parcel_identity_reference_id
            },
        )

    def review_member(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        member_id: UUID,
        review_status: ParcelMemberReviewStatus,
        expected_version: int,
        idempotency_key: str,
        request_id: str,
    ) -> CaseParcelSetOutcome:
        self._require_existing_version(expected_version)
        if not isinstance(review_status, ParcelMemberReviewStatus):
            raise VNextError.validation_failed()
        return self._execute(
            principal=principal,
            workspace_id=workspace_id,
            case_id=case_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            canonical_route=(
                f"/v1/cases/{case_id}/parcel-set/members/{member_id}/review"
            ),
            canonical_fields={
                "member_id": str(member_id),
                "review_status": review_status.value,
            },
            operation="review_member",
            operation_fields={"member_id": member_id, "review_status": review_status},
        )

    def set_active_member(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        active_member_id: UUID | None,
        expected_version: int,
        idempotency_key: str,
        request_id: str,
    ) -> CaseParcelSetOutcome:
        self._require_existing_version(expected_version)
        return self._execute(
            principal=principal,
            workspace_id=workspace_id,
            case_id=case_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            canonical_route=f"/v1/cases/{case_id}/parcel-set/active-member",
            canonical_fields={
                "active_member_id": (
                    None if active_member_id is None else str(active_member_id)
                )
            },
            operation="set_active_member",
            operation_fields={"active_member_id": active_member_id},
        )

    def reorder(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        ordered_member_ids: tuple[UUID, ...],
        expected_version: int,
        idempotency_key: str,
        request_id: str,
    ) -> CaseParcelSetOutcome:
        self._require_existing_version(expected_version)
        selected_ids = tuple(ordered_member_ids)
        if (
            not 1 <= len(selected_ids) <= 100
            or len(set(selected_ids)) != len(selected_ids)
        ):
            raise VNextError.validation_failed()
        return self._execute(
            principal=principal,
            workspace_id=workspace_id,
            case_id=case_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            canonical_route=f"/v1/cases/{case_id}/parcel-set/reorder",
            canonical_fields={
                "ordered_member_ids": [str(member_id) for member_id in selected_ids]
            },
            operation="reorder",
            operation_fields={"ordered_member_ids": selected_ids},
        )

    def mark_case_reviewed(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        case_id: UUID,
        expected_version: int,
        idempotency_key: str,
        request_id: str,
    ) -> CaseParcelSetOutcome:
        self._require_existing_version(expected_version)
        return self._execute(
            principal=principal,
            workspace_id=workspace_id,
            case_id=case_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
            request_id=request_id,
            canonical_route=f"/v1/cases/{case_id}/parcel-set/review",
            canonical_fields={},
            operation="mark_case_reviewed",
            operation_fields={},
        )

    @staticmethod
    def _require_existing_version(expected_version: int) -> None:
        if expected_version < 1:
            raise VNextError.validation_failed()
