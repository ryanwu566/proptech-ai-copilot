"""Idempotent application services for explicit Slice 6 human commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_command_repository import (
    IDENTITY_DECISION_ROLES, AttachmentWriteResult, CasePropertyLinkRecord,
    ConfirmationWriteResult)
from services.vnext.identity_resolution_repository import (
    IdentityDecisionRecord, IdentityResolutionRecord)
from services.vnext.persistence import (CASE_WRITE_ROLES, CasePurpose,
                                        CaseRecord, IdempotencyDecision,
                                        IdempotencyReservation)


class ResolutionReader(Protocol):
    def get_resolution_by_id(self, **kwargs: object) -> IdentityResolutionRecord: ...

    def get_decision_by_id(self, **kwargs: object) -> IdentityDecisionRecord: ...


class IdentityCommandWriter(Protocol):
    def confirm(self, **kwargs: object) -> ConfirmationWriteResult: ...

    def reject(self, **kwargs: object) -> IdentityDecisionRecord: ...

    def attach_resolution(self, **kwargs: object) -> AttachmentWriteResult: ...

    def get_case_property_link_by_id(self, **kwargs: object) -> CasePropertyLinkRecord: ...


class IdempotencyWriter(Protocol):
    def reserve(self, **kwargs: object) -> IdempotencyReservation: ...

    def mark_failed(self, **kwargs: object) -> None: ...


class CaseWriter(Protocol):
    def create_case(self, **kwargs: object) -> CaseRecord: ...

    def get_case_by_id(self, **kwargs: object) -> CaseRecord: ...


@dataclass(frozen=True)
class IdentityDecisionOutcome:
    resolution: IdentityResolutionRecord
    decision: IdentityDecisionRecord
    replayed: bool


@dataclass(frozen=True)
class CaseCreateOutcome:
    case: CaseRecord
    replayed: bool


@dataclass(frozen=True)
class CaseAttachmentOutcome:
    case: CaseRecord
    link: CasePropertyLinkRecord
    replayed: bool


def _canonical(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


class IdentityCommandApplicationService:
    def __init__(
        self,
        *,
        authorizer: WorkspaceAuthorizer,
        resolution_repository: ResolutionReader,
        command_repository: IdentityCommandWriter,
        idempotency_repository: IdempotencyWriter,
        case_repository: CaseWriter,
    ) -> None:
        self._authorizer = authorizer
        self._resolution_repository = resolution_repository
        self._command_repository = command_repository
        self._idempotency_repository = idempotency_repository
        self._case_repository = case_repository

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
    def _replay_guard(reservation: IdempotencyReservation, reference_type: str) -> UUID:
        if reservation.operation_status == "pending":
            raise VNextError(ErrorCode.MAINTENANCE)
        if reservation.operation_status == "failed":
            try:
                error_code = ErrorCode(str(reservation.response_error_code))
            except ValueError:
                raise VNextError(ErrorCode.INTERNAL_ERROR) from None
            raise VNextError(error_code)
        if reservation.operation_status != "succeeded":
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        if (
            reservation.response_reference_type != reference_type
            or reservation.response_reference_id is None
        ):
            raise VNextError(ErrorCode.INTERNAL_ERROR)
        return reservation.response_reference_id

    def confirm(
        self,
        *,
        principal: AuthenticatedPrincipal,
        identity_resolution_id: UUID,
        identity_candidate_id: UUID,
        expected_version: int,
        confirmation_reason: str,
        idempotency_key: str,
        request_id: str,
    ) -> IdentityDecisionOutcome:
        resolution = self._resolution_repository.get_resolution_by_id(
            principal=principal, identity_resolution_id=identity_resolution_id
        )
        self._authorizer.require_workspace_role(
            principal,
            resolution.workspace_id,
            allowed_roles=IDENTITY_DECISION_ROLES,
        )
        route = f"/v1/property-resolutions/{identity_resolution_id}/confirm"
        reservation = self._idempotency_repository.reserve(
            principal=principal,
            workspace_id=resolution.workspace_id,
            method="POST",
            canonical_route=route,
            idempotency_key=idempotency_key,
            canonical_request=_canonical(
                {
                    "candidate_id": str(identity_candidate_id),
                    "version": expected_version,
                    "confirmation_reason": confirmation_reason,
                }
            ),
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            decision_id = self._replay_guard(reservation, "identity_decision")
            decision = self._resolution_repository.get_decision_by_id(
                principal=principal, identity_decision_id=decision_id
            )
            if (
                decision.identity_resolution_id != identity_resolution_id
                or decision.decision_type != "confirmed"
            ):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            return IdentityDecisionOutcome(
                resolution=self._resolution_repository.get_resolution_by_id(
                    principal=principal,
                    identity_resolution_id=identity_resolution_id,
                ),
                decision=decision,
                replayed=True,
            )
        try:
            written = self._command_repository.confirm(
                principal=principal,
                workspace_id=resolution.workspace_id,
                identity_resolution_id=identity_resolution_id,
                identity_candidate_id=identity_candidate_id,
                expected_version=expected_version,
                confirmation_reason=confirmation_reason,
                request_id=request_id,
                idempotency_record_id=reservation.idempotency_record_id,
            )
        except VNextError as error:
            self._mark_failed(
                principal=principal,
                workspace_id=resolution.workspace_id,
                reservation=reservation,
                error=error,
            )
            raise
        except Exception:
            error = VNextError(ErrorCode.INTERNAL_ERROR)
            self._mark_failed(
                principal=principal,
                workspace_id=resolution.workspace_id,
                reservation=reservation,
                error=error,
            )
            raise error from None
        return IdentityDecisionOutcome(
            resolution=self._resolution_repository.get_resolution_by_id(
                principal=principal, identity_resolution_id=identity_resolution_id
            ),
            decision=written.decision,
            replayed=False,
        )

    def reject(
        self,
        *,
        principal: AuthenticatedPrincipal,
        identity_resolution_id: UUID,
        identity_candidate_id: UUID | None,
        expected_version: int,
        reason_code: str,
        idempotency_key: str,
        request_id: str,
    ) -> IdentityDecisionOutcome:
        resolution = self._resolution_repository.get_resolution_by_id(
            principal=principal, identity_resolution_id=identity_resolution_id
        )
        self._authorizer.require_workspace_role(
            principal,
            resolution.workspace_id,
            allowed_roles=IDENTITY_DECISION_ROLES,
        )
        route = f"/v1/property-resolutions/{identity_resolution_id}/reject"
        reservation = self._idempotency_repository.reserve(
            principal=principal,
            workspace_id=resolution.workspace_id,
            method="POST",
            canonical_route=route,
            idempotency_key=idempotency_key,
            canonical_request=_canonical(
                {
                    "candidate_id": (
                        None if identity_candidate_id is None else str(identity_candidate_id)
                    ),
                    "version": expected_version,
                    "reason_code": reason_code,
                }
            ),
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            decision_id = self._replay_guard(reservation, "identity_decision")
            decision = self._resolution_repository.get_decision_by_id(
                principal=principal, identity_decision_id=decision_id
            )
            if decision.identity_resolution_id != identity_resolution_id or not decision.decision_type.endswith(
                "rejected"
            ):
                raise VNextError(ErrorCode.INTERNAL_ERROR)
            return IdentityDecisionOutcome(
                resolution=self._resolution_repository.get_resolution_by_id(
                    principal=principal,
                    identity_resolution_id=identity_resolution_id,
                ),
                decision=decision,
                replayed=True,
            )
        try:
            decision = self._command_repository.reject(
                principal=principal,
                workspace_id=resolution.workspace_id,
                identity_resolution_id=identity_resolution_id,
                identity_candidate_id=identity_candidate_id,
                expected_version=expected_version,
                reason_code=reason_code,
                request_id=request_id,
                idempotency_record_id=reservation.idempotency_record_id,
            )
        except VNextError as error:
            self._mark_failed(
                principal=principal,
                workspace_id=resolution.workspace_id,
                reservation=reservation,
                error=error,
            )
            raise
        except Exception:
            error = VNextError(ErrorCode.INTERNAL_ERROR)
            self._mark_failed(
                principal=principal,
                workspace_id=resolution.workspace_id,
                reservation=reservation,
                error=error,
            )
            raise error from None
        return IdentityDecisionOutcome(
            resolution=self._resolution_repository.get_resolution_by_id(
                principal=principal, identity_resolution_id=identity_resolution_id
            ),
            decision=decision,
            replayed=False,
        )

    def create_case(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        purpose: CasePurpose,
        title: str,
        idempotency_key: str,
        request_id: str,
    ) -> CaseCreateOutcome:
        self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        reservation = self._idempotency_repository.reserve(
            principal=principal,
            workspace_id=workspace_id,
            method="POST",
            canonical_route="/v1/cases",
            idempotency_key=idempotency_key,
            canonical_request=_canonical(
                {
                    "workspace_id": str(workspace_id),
                    "purpose": purpose.value,
                    "title": title,
                }
            ),
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            case_id = self._replay_guard(reservation, "case")
            return CaseCreateOutcome(
                case=self._case_repository.get_case_by_id(
                    principal=principal, case_id=case_id
                ),
                replayed=True,
            )
        try:
            case = self._case_repository.create_case(
                principal=principal,
                workspace_id=workspace_id,
                purpose=purpose,
                title=title,
                request_id=request_id,
                idempotency_record_id=reservation.idempotency_record_id,
                idempotency_response_status_code=201,
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
        return CaseCreateOutcome(case=case, replayed=False)

    def attach_resolution(
        self,
        *,
        principal: AuthenticatedPrincipal,
        case_id: UUID,
        identity_resolution_id: UUID,
        expected_case_version: int,
        idempotency_key: str,
        request_id: str,
    ) -> CaseAttachmentOutcome:
        case = self._case_repository.get_case_by_id(principal=principal, case_id=case_id)
        self._authorizer.require_workspace_role(
            principal, case.workspace_id, allowed_roles=IDENTITY_DECISION_ROLES
        )
        resolution = self._resolution_repository.get_resolution_by_id(
            principal=principal, identity_resolution_id=identity_resolution_id
        )
        if resolution.workspace_id != case.workspace_id:
            raise VNextError.not_found()
        confirmations = [
            decision
            for decision in resolution.decisions
            if decision.decision_type == "confirmed"
            and decision.property_entity_id is not None
        ]
        if len(confirmations) != 1:
            raise VNextError(ErrorCode.AMBIGUOUS_IDENTITY)
        confirmation = confirmations[0]
        route = f"/v1/cases/{case_id}/attach-resolution"
        reservation = self._idempotency_repository.reserve(
            principal=principal,
            workspace_id=case.workspace_id,
            method="POST",
            canonical_route=route,
            idempotency_key=idempotency_key,
            canonical_request=_canonical(
                {
                    "resolution_id": str(identity_resolution_id),
                    "case_version": expected_case_version,
                }
            ),
        )
        if reservation.decision is IdempotencyDecision.REPLAY:
            link_id = self._replay_guard(reservation, "case_property_link")
            return CaseAttachmentOutcome(
                case=self._case_repository.get_case_by_id(
                    principal=principal, case_id=case_id
                ),
                link=self._command_repository.get_case_property_link_by_id(
                    principal=principal, case_property_link_id=link_id
                ),
                replayed=True,
            )
        try:
            written = self._command_repository.attach_resolution(
                principal=principal,
                workspace_id=case.workspace_id,
                case_id=case_id,
                identity_resolution_id=identity_resolution_id,
                identity_confirmation_id=confirmation.identity_decision_id,
                property_entity_id=confirmation.property_entity_id,
                expected_case_version=expected_case_version,
                request_id=request_id,
                idempotency_record_id=reservation.idempotency_record_id,
            )
        except VNextError as error:
            self._mark_failed(
                principal=principal,
                workspace_id=case.workspace_id,
                reservation=reservation,
                error=error,
            )
            raise
        except Exception:
            error = VNextError(ErrorCode.INTERNAL_ERROR)
            self._mark_failed(
                principal=principal,
                workspace_id=case.workspace_id,
                reservation=reservation,
                error=error,
            )
            raise error from None
        return CaseAttachmentOutcome(
            case=written.case,
            link=written.link,
            replayed=False,
        )
