"""Authenticated read-only normalization of Taipei planning references."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from backend.api.v1.errors import vnext_error_responses
from services.production_config import load_runtime_configuration
from services.vnext.errors import VNextError
from services.vnext.feature_flags import VNextFeatureFlags, get_vnext_feature_flags
from services.vnext.taipei_planning import (
    DocumentKind,
    ManualPlanningReference,
    normalize_manual_reference,
    normalize_reported_text,
)


router = APIRouter(tags=["vnext-taipei-planning"])

ReportedReference = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
OptionalReportedText200 = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=200),
]
OptionalReportedText80 = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=80),
]
_FORGED_IDENTITY_HEADERS = frozenset({"x-user-id", "x-role", "x-workspace-role"})


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _normalize_request_text(
    value: object,
    *,
    required: bool,
    maximum: int,
) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValueError("reported text is invalid")
    try:
        return normalize_reported_text(value, required=required, maximum=maximum)
    except VNextError:
        raise ValueError("reported text is invalid") from None


class PlanningObservationRequest(_StrictModel):
    jurisdiction: Annotated[str, Field(min_length=1, max_length=32)]
    scope: Annotated[str, Field(min_length=1, max_length=64)]
    document_kind: DocumentKind
    reported_document_reference: ReportedReference
    reported_plan_identifier: OptionalReportedText200 | None = None
    reported_zone_code: OptionalReportedText80 | None = None
    reported_zone_label: OptionalReportedText200 | None = None
    reported_effective_date: date | None = None

    @field_validator("reported_document_reference", mode="before")
    @classmethod
    def validate_reported_document_reference(cls, value: object) -> str:
        normalized = _normalize_request_text(value, required=True, maximum=200)
        assert normalized is not None
        return normalized

    @field_validator("reported_plan_identifier", "reported_zone_label", mode="before")
    @classmethod
    def validate_optional_reported_text_200(cls, value: object) -> str | None:
        return _normalize_request_text(value, required=False, maximum=200)

    @field_validator("reported_zone_code", mode="before")
    @classmethod
    def validate_optional_reported_text_80(cls, value: object) -> str | None:
        return _normalize_request_text(value, required=False, maximum=80)

    @field_validator("reported_effective_date", mode="before")
    @classmethod
    def require_exact_iso_calendar_date(cls, value: object) -> date | None:
        if value is None:
            return None
        if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
            raise ValueError("reported_effective_date must be an ISO calendar date")
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError("reported_effective_date must be an ISO calendar date") from None


class PlanningObservationV1(_StrictModel):
    status: Literal["LIMITED"]
    jurisdiction: Literal["Taipei City"]
    scope: Literal["urban_plan_non_national_park"]
    authority_class: Literal["USER_PROVIDED"]
    document_kind: DocumentKind
    issuing_authority: Literal["Taipei City Department of Urban Development"]
    source_portal: Literal[
        "https://zone.udd.gov.taipei/new_index1.aspx",
        "https://udd.gov.taipei/announcement/biwfsm8",
    ]
    reported_document_reference: str
    reported_plan_identifier: str | None
    reported_zone_code: str | None
    reported_zone_label: str | None
    reported_effective_date: date | None
    coverage_status: Literal["LIMITED"]
    verification_required: Literal[True]
    verification_status: Literal["unverified"]
    limitations: tuple[str, ...]
    normalized_at: datetime
    disclaimer: Literal[
        "Planning evidence must be confirmed against the competent local authority and current legally effective plan/certificate."
    ]


def reject_client_identity_overrides(request: Request) -> None:
    header_names = {name.lower() for name in request.headers}
    if header_names & _FORGED_IDENTITY_HEADERS or request.query_params:
        raise VNextError.validation_failed()


def require_taipei_planning_feature(
    flags: VNextFeatureFlags = Depends(get_vnext_feature_flags),
) -> None:
    if not flags.taipei_planning_read_v1:
        raise VNextError.not_found()


def require_taipei_planning_source_mode() -> None:
    if load_runtime_configuration().taipei_planning_source_mode_status != "configured":
        raise VNextError.coverage_unavailable()


@router.post(
    "/planning/taipei/observe",
    response_model=PlanningObservationV1,
    responses=vnext_error_responses(401, 404, 422, 503),
    dependencies=[
        Depends(reject_client_identity_overrides),
        Depends(require_taipei_planning_feature),
        Depends(require_taipei_planning_source_mode),
    ],
)
def observe_taipei_planning_reference(
    request: PlanningObservationRequest,
) -> PlanningObservationV1:
    observation = normalize_manual_reference(
        ManualPlanningReference(
            jurisdiction=request.jurisdiction,
            scope=request.scope,
            document_kind=request.document_kind,
            reported_document_reference=request.reported_document_reference,
            reported_plan_identifier=request.reported_plan_identifier,
            reported_zone_code=request.reported_zone_code,
            reported_zone_label=request.reported_zone_label,
            reported_effective_date=request.reported_effective_date,
        )
    )
    return PlanningObservationV1(
        status=observation.status.value,
        jurisdiction=observation.jurisdiction,
        scope=observation.scope,
        authority_class=observation.authority_class.value,
        document_kind=observation.document_kind,
        issuing_authority=observation.issuing_authority,
        source_portal=observation.source_portal,
        reported_document_reference=observation.reported_document_reference,
        reported_plan_identifier=observation.reported_plan_identifier,
        reported_zone_code=observation.reported_zone_code,
        reported_zone_label=observation.reported_zone_label,
        reported_effective_date=observation.reported_effective_date,
        coverage_status=observation.coverage_status.value,
        verification_required=observation.verification_required,
        verification_status=observation.verification_status.value,
        limitations=observation.limitations,
        normalized_at=observation.normalized_at,
        disclaimer=observation.disclaimer,
    )
