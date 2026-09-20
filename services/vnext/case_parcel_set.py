"""Case-local parcel-set review records with no Property Identity authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class ParcelSetStatus(str, Enum):
    DRAFT = "draft"
    CASE_REVIEWED = "case_reviewed"


class ParcelMemberReviewStatus(str, Enum):
    CANDIDATE = "candidate"
    CASE_SELECTED = "case_selected"
    CASE_REJECTED = "case_rejected"


@dataclass(frozen=True)
class CaseParcelSetMemberRecord:
    parcel_set_member_id: UUID
    workspace_id: UUID
    parcel_set_id: UUID
    parcel_identity_reference_id: UUID
    position: int
    review_status: ParcelMemberReviewStatus
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CaseParcelSetRecord:
    parcel_set_id: UUID
    workspace_id: UUID
    case_id: UUID
    status: ParcelSetStatus
    version: int
    active_member_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    members: tuple[CaseParcelSetMemberRecord, ...]


@dataclass(frozen=True)
class CaseParcelSetOutcome:
    record: CaseParcelSetRecord
    replayed: bool
