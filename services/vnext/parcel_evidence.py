"""Provider-independent evidence about a parcel hypothesis, never identity authority."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.vnext.errors import VNextError
from services.vnext.property_graph import (
    CoverageStatus as StoredCoverageStatus, DATA_SOURCE_REGISTRY, EvidenceDraft,
    EvidenceStatus, LicenseStatus, QualityStatus as StoredQualityStatus,
    SourceEnvironment, SourceType, _validated_evidence_draft,
)

PARCEL_EVIDENCE_SCHEMA_VERSION = "parcel-evidence-v1"
PARCEL_EVIDENCE_FACT_TYPE = "parcel.hypothesis_observation.v1"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ParcelCoverageStatus(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    RESTRICTED = "restricted"


class ParcelQualityStatus(str, Enum):
    VERIFIED = "verified"
    AVAILABLE = "available"
    PARTIAL = "partial"
    STALE = "stale"
    CONFLICT = "conflict"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


class ParcelConfidenceMethod(str, Enum):
    PROVIDER = "provider"
    RESOLVER = "resolver"
    DERIVED = "derived"
    MANUAL = "manual"


class ParcelReviewState(str, Enum):
    UNREVIEWED = "unreviewed"
    USER_CONFIRM_REQUIRED = "user_confirm_required"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class ParcelUnknownReason(str, Enum):
    NOT_FOUND = "not_found"
    RESTRICTED = "restricted"
    AUTH_REQUIRED = "auth_required"
    RATE_LIMITED = "rate_limited"
    PROVIDER_ERROR = "provider_error"
    AMBIGUOUS = "ambiguous"
    STALE = "stale"
    NOT_COLLECTED = "not_collected"


class ParcelEvidenceSource(_StrictModel):
    # This slice can persist only existing request-appendable source classes.
    # A provider name is metadata and grants no authority.
    source_id: Literal["user-upload", "vnext-deterministic"]
    provider: str = Field(min_length=1, max_length=120)
    dataset: str = Field(min_length=1, max_length=160)
    record_id: str | None = Field(default=None, max_length=240)
    endpoint_class: str = Field(min_length=1, max_length=160)


class ParcelEvidenceCoverage(_StrictModel):
    spatial: str | None = Field(default=None, max_length=240)
    temporal: str | None = Field(default=None, max_length=240)
    status: ParcelCoverageStatus


class ParcelEvidenceConfidence(_StrictModel):
    score: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False, strict=True)
    method: ParcelConfidenceMethod | None = None
    basis: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def complete_or_absent(self) -> "ParcelEvidenceConfidence":
        if (self.score is None) != (self.method is None) or (self.score is None) != (self.basis is None):
            raise ValueError("confidence score, method and basis must be supplied together")
        if self.basis is not None and not self.basis.strip():
            raise ValueError("confidence basis is empty")
        return self


class ParcelEvidenceLicense(_StrictModel):
    name: str | None = Field(default=None, max_length=160)
    attribution: str | None = Field(default=None, max_length=500)
    retention: str = Field(min_length=1, max_length=160)
    display_constraints: tuple[str, ...] = Field(default=(), max_length=16)


class ParcelEvidenceTransformation(_StrictModel):
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=120)
    input_ref: str | None = Field(default=None, max_length=240)


class ParcelEvidenceEnvelope(_StrictModel):
    schema_version: Literal["parcel-evidence-v1"]
    value: dict[str, object] | None
    source: ParcelEvidenceSource
    retrieved_at: datetime
    effective_at: datetime | None = None
    coverage: ParcelEvidenceCoverage
    confidence: ParcelEvidenceConfidence
    quality_status: ParcelQualityStatus
    license: ParcelEvidenceLicense
    identity_scope: Literal["parcel"]
    review_state: ParcelReviewState
    transformations: tuple[ParcelEvidenceTransformation, ...] = Field(default=(), max_length=32)
    raw_evidence_ref: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,239}$")
    unknown_reason: ParcelUnknownReason | None = None

    @model_validator(mode="after")
    def bounded_semantics(self) -> "ParcelEvidenceEnvelope":
        if self.retrieved_at.utcoffset() is None or (
            self.effective_at is not None and self.effective_at.utcoffset() is None
        ):
            raise ValueError("timestamps must have an offset")
        if self.value is None:
            if self.unknown_reason is None or self.quality_status is not ParcelQualityStatus.UNAVAILABLE:
                raise ValueError("absent value requires unavailable quality and unknown reason")
        elif self.unknown_reason is not None or self.quality_status is ParcelQualityStatus.UNAVAILABLE:
            raise ValueError("present value cannot carry an unknown reason or unavailable quality")
        if self.quality_status is ParcelQualityStatus.CONFLICT and self.review_state is not ParcelReviewState.MANUAL_REVIEW_REQUIRED:
            raise ValueError("conflicting observations require manual review")
        if self.quality_status is ParcelQualityStatus.VERIFIED and not any(
            step.name == "payload-validation" for step in self.transformations
        ):
            raise ValueError("verified evidence requires a payload-validation trace")
        return self


_STORED_COVERAGE = {
    ParcelCoverageStatus.FULL: StoredCoverageStatus.KNOWN,
    ParcelCoverageStatus.PARTIAL: StoredCoverageStatus.PARTIAL,
    ParcelCoverageStatus.UNKNOWN: StoredCoverageStatus.UNKNOWN,
    ParcelCoverageStatus.RESTRICTED: StoredCoverageStatus.UNAVAILABLE,
}
_STORED_EVIDENCE = {
    ParcelQualityStatus.VERIFIED: EvidenceStatus.AVAILABLE,
    ParcelQualityStatus.AVAILABLE: EvidenceStatus.AVAILABLE,
    ParcelQualityStatus.PARTIAL: EvidenceStatus.LIMITED,
    ParcelQualityStatus.STALE: EvidenceStatus.STALE,
    ParcelQualityStatus.CONFLICT: EvidenceStatus.CONFLICTING,
    ParcelQualityStatus.INVALID: EvidenceStatus.UNVERIFIED,
}
_UNAVAILABLE_REASONS = frozenset({
    ParcelUnknownReason.RESTRICTED, ParcelUnknownReason.AUTH_REQUIRED,
    ParcelUnknownReason.RATE_LIMITED, ParcelUnknownReason.PROVIDER_ERROR,
})


def canonical_parcel_evidence(envelope: ParcelEvidenceEnvelope) -> tuple[bytes, str]:
    """Hash every contracted field, including raw reference and review metadata."""

    try:
        payload = json.dumps(
            envelope.model_dump(mode="json"), ensure_ascii=True,
            separators=(",", ":"), sort_keys=True, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise VNextError.validation_failed() from None
    if len(payload) > 32_768:
        raise VNextError.validation_failed()
    return payload, hashlib.sha256(payload).hexdigest()


def parcel_evidence_draft(envelope: ParcelEvidenceEnvelope) -> EvidenceDraft:
    """Adapt the contract to existing evidence_items without changing its schema."""

    definition = DATA_SOURCE_REGISTRY[envelope.source.source_id]
    if (definition.source_type not in {SourceType.USER, SourceType.DETERMINISTIC}
        or not definition.request_appendable
        or SourceEnvironment.PRODUCTION not in definition.environments):
        raise VNextError.permission_denied()
    if envelope.quality_status is ParcelQualityStatus.UNAVAILABLE:
        status = EvidenceStatus.UNAVAILABLE if envelope.unknown_reason in _UNAVAILABLE_REASONS else EvidenceStatus.UNKNOWN
    else:
        status = _STORED_EVIDENCE[envelope.quality_status]
    quality_status = {
        ParcelQualityStatus.VERIFIED: StoredQualityStatus.PASSED,
        ParcelQualityStatus.PARTIAL: StoredQualityStatus.LIMITED,
        ParcelQualityStatus.STALE: StoredQualityStatus.LIMITED,
        ParcelQualityStatus.CONFLICT: StoredQualityStatus.LIMITED,
        ParcelQualityStatus.INVALID: StoredQualityStatus.FAILED,
    }.get(envelope.quality_status, StoredQualityStatus.NOT_CHECKED)
    draft = EvidenceDraft(
        fact_type=PARCEL_EVIDENCE_FACT_TYPE,
        source_id=envelope.source.source_id,
        source_environment=SourceEnvironment.PRODUCTION,
        retrieved_at=envelope.retrieved_at,
        effective_from=envelope.effective_at,
        coverage_status=_STORED_COVERAGE[envelope.coverage.status],
        coverage=envelope.coverage.model_dump(mode="json"),
        evidence_status=status,
        quality_status=quality_status,
        quality={
            "contract_quality_status": envelope.quality_status.value,
            "confidence_basis": envelope.confidence.basis,
            "unknown_reason": None if envelope.unknown_reason is None else envelope.unknown_reason.value,
        },
        license_status=LicenseStatus.UNKNOWN,
        license=envelope.license.model_dump(mode="json"),
        value=envelope.value,
        value_schema=PARCEL_EVIDENCE_SCHEMA_VERSION,
        provider=envelope.source.provider,
        source_record_id=envelope.source.record_id,
        quality_confidence=envelope.confidence.score,
        quality_method=None if envelope.confidence.method is None else envelope.confidence.method.value,
        lineage={
            "schema_version": envelope.schema_version,
            "identity_scope": envelope.identity_scope,
            "review_state": envelope.review_state.value,
            "dataset": envelope.source.dataset,
            "endpoint_class": envelope.source.endpoint_class,
            "confidence": envelope.confidence.model_dump(mode="json"),
            "transformations": [item.model_dump(mode="json") for item in envelope.transformations],
        },
        raw_artifact_ref=envelope.raw_evidence_ref,
    )
    _validated_evidence_draft(draft)
    return draft
