"""Pure normalization for user-provided Taipei planning references.

This module intentionally performs no retrieval, provider, browser, database,
repository, persistence, or job work. Reported values remain unverified data.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Callable

from services.vnext.errors import VNextError


class DocumentKind(str, Enum):
    ISSUED_ZONING_CERTIFICATE = "issued_zoning_certificate"
    OFFICIAL_URBAN_PLAN_ANNOUNCEMENT = "official_urban_plan_announcement"


class PlanningStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class AuthorityClass(str, Enum):
    AUTHORITATIVE_LOCAL = "AUTHORITATIVE_LOCAL"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    USER_PROVIDED = "USER_PROVIDED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class CoverageStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"


ISSUING_AUTHORITY = "Taipei City Department of Urban Development"
SOURCE_PORTALS = MappingProxyType(
    {
        DocumentKind.ISSUED_ZONING_CERTIFICATE: "https://zone.udd.gov.taipei/new_index1.aspx",
        DocumentKind.OFFICIAL_URBAN_PLAN_ANNOUNCEMENT: "https://udd.gov.taipei/announcement/biwfsm8",
    }
)

DISCLAIMER = (
    "Planning evidence must be confirmed against the competent local authority "
    "and current legally effective plan/certificate."
)

_COMMON_LIMITATIONS = (
    "Manual metadata is unverified and user-provided.",
    "The reference is not bound to any current PropertyEntity, parcel, or Case.",
    "No FAR, BCR, buildability, entitlement, ownership, development approval, "
    "permitted-use, or parcel-confirmation conclusion is produced.",
    "LUI_002 is separate REFERENCE_ONLY land-use survey evidence and is not statutory zoning.",
)
_CERTIFICATE_LIMITATION = (
    "The runtime has not confirmed the certificate's authenticity, currency, validity period, "
    "applicability to a loaded property, or coverage of an entire case."
)
_ANNOUNCEMENT_LIMITATION = (
    "Current legal effect requires confirmation against later amendments, "
    "supersession, revocation, and the competent authority."
)
_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_PATH_SEPARATOR = re.compile(r"[\\/]+")
_DISALLOWED_LEADING_SCHEME = re.compile(r"^(?:https?|file):", re.IGNORECASE)


@dataclass(frozen=True)
class ManualPlanningReference:
    jurisdiction: str
    scope: str
    document_kind: DocumentKind
    reported_document_reference: str
    reported_plan_identifier: str | None = None
    reported_zone_code: str | None = None
    reported_zone_label: str | None = None
    reported_effective_date: date | None = None


@dataclass(frozen=True)
class PlanningObservation:
    status: PlanningStatus
    jurisdiction: str
    scope: str
    authority_class: AuthorityClass
    document_kind: DocumentKind
    issuing_authority: str
    source_portal: str
    reported_document_reference: str
    reported_plan_identifier: str | None
    reported_zone_code: str | None
    reported_zone_label: str | None
    reported_effective_date: date | None
    coverage_status: CoverageStatus
    verification_required: bool
    verification_status: VerificationStatus
    limitations: tuple[str, ...]
    normalized_at: datetime
    disclaimer: str


def normalize_reported_text(
    value: str | None,
    *,
    required: bool,
    maximum: int,
) -> str | None:
    """Trim a bounded identifier while rejecting executable/path-like forms."""

    if value is None:
        if required:
            raise VNextError.validation_failed()
        return None
    if not isinstance(value, str) or maximum < 1:
        raise VNextError.validation_failed()
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise VNextError.validation_failed()

    normalized = value.strip()
    if not normalized:
        if required:
            raise VNextError.validation_failed()
        return None
    if len(normalized) > maximum:
        raise VNextError.validation_failed()
    if "<" in normalized or ">" in normalized:
        raise VNextError.validation_failed()

    folded = normalized.casefold()
    if (
        "://" in folded
        or folded.startswith("www.")
        or _DISALLOWED_LEADING_SCHEME.match(normalized)
    ):
        raise VNextError.validation_failed()
    if (
        normalized.startswith(("/", "\\"))
        or _WINDOWS_DRIVE_PATH.match(normalized)
    ):
        raise VNextError.validation_failed()

    path_segments = _PATH_SEPARATOR.split(normalized)
    if normalized == ".." or (len(path_segments) > 1 and ".." in path_segments):
        raise VNextError.validation_failed()
    return normalized


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_manual_reference(
    reference: ManualPlanningReference,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> PlanningObservation:
    """Normalize a reported reference without verifying or upgrading authority."""

    if not isinstance(reference, ManualPlanningReference):
        raise VNextError.validation_failed()
    if reference.jurisdiction != "Taipei City" or reference.scope != "urban_plan_non_national_park":
        raise VNextError.unsupported_input()
    if not isinstance(reference.document_kind, DocumentKind):
        raise VNextError.unsupported_input()
    if reference.reported_effective_date is not None and (
        not isinstance(reference.reported_effective_date, date)
        or isinstance(reference.reported_effective_date, datetime)
    ):
        raise VNextError.validation_failed()

    normalized_at = clock()
    if not isinstance(normalized_at, datetime) or normalized_at.utcoffset() is None:
        raise VNextError.validation_failed()

    limitations = _COMMON_LIMITATIONS + (
        _CERTIFICATE_LIMITATION
        if reference.document_kind is DocumentKind.ISSUED_ZONING_CERTIFICATE
        else _ANNOUNCEMENT_LIMITATION,
    )
    return PlanningObservation(
        status=PlanningStatus.LIMITED,
        jurisdiction="Taipei City",
        scope="urban_plan_non_national_park",
        authority_class=AuthorityClass.USER_PROVIDED,
        document_kind=reference.document_kind,
        issuing_authority=ISSUING_AUTHORITY,
        source_portal=SOURCE_PORTALS[reference.document_kind],
        reported_document_reference=normalize_reported_text(
            reference.reported_document_reference,
            required=True,
            maximum=200,
        ),
        reported_plan_identifier=normalize_reported_text(
            reference.reported_plan_identifier,
            required=False,
            maximum=200,
        ),
        reported_zone_code=normalize_reported_text(
            reference.reported_zone_code,
            required=False,
            maximum=80,
        ),
        reported_zone_label=normalize_reported_text(
            reference.reported_zone_label,
            required=False,
            maximum=200,
        ),
        reported_effective_date=reference.reported_effective_date,
        coverage_status=CoverageStatus.LIMITED,
        verification_required=True,
        verification_status=VerificationStatus.UNVERIFIED,
        limitations=limitations,
        normalized_at=normalized_at.astimezone(timezone.utc),
        disclaimer=DISCLAIMER,
    )
