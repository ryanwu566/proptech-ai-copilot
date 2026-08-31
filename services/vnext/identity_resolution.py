"""Deterministic property-identity candidate generation for Stage 1 Slice 4.

The engine normalizes bounded inputs, invokes explicitly injected provider
adapters, records every safe provider outcome, and ranks hypotheses with a
fixed formula.  It never creates, confirms, selects or merges PropertyEntity
records.  Current production TGOS/Google/NLSC/PLVR implementations are
deliberately not adapted here: their readiness and semantics do not satisfy
this contract.  Only the provider protocol and pure coordinate validation
shape were suitable to ADAPT; location insight and search scoring are DO NOT
USE for identity authority.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Callable, Mapping, Protocol, Sequence
from uuid import UUID

from services.vnext.errors import VNextError
from services.vnext.property_graph import (
    CoverageStatus,
    DATA_SOURCE_REGISTRY,
    SourceDefinition,
    SourceEnvironment,
    SourceType,
)


NORMALIZATION_VERSION = "identity-input-normalization-v1"
RANKING_METHOD = "identity-ranking-v1"
MAX_ATTEMPTS = 64
MAX_CANDIDATES = 1000
MAX_SUPPORT_IDS = 32


class ResolutionInputType(str, Enum):
    ADDRESS = "address"
    LOT_NUMBER = "lot_number"
    BUILDING_NUMBER = "building_number"
    COORDINATES = "coordinates"
    MAP_CLICK = "map_click"


class ResolutionStatus(str, Enum):
    RECEIVED = "received"
    NORMALIZING = "normalizing"
    CANDIDATES_FOUND = "candidates_found"
    AMBIGUOUS = "ambiguous"
    PARTIALLY_RESOLVED = "partially_resolved"
    UNRESOLVED = "unresolved"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class AmbiguityStatus(str, Enum):
    NONE = "none"
    MULTIPLE_CANDIDATES = "multiple_candidates"
    MATERIAL_CONFLICT = "material_conflict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PROVIDER_LIMITATION = "provider_limitation"


class ResolutionAttemptStatus(str, Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    UNSUPPORTED = "unsupported"
    NO_MATCH = "no_match"
    ERROR = "error"


class ResolutionErrorCategory(str, Enum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    UNSUPPORTED_INPUT = "unsupported_input"
    PROVIDER_REJECTED = "provider_rejected"
    INVALID_RESPONSE = "invalid_response"
    TRANSPORT_ERROR = "transport_error"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    NOT_CONFIGURED = "not_configured"


class IdentityCandidateType(str, Enum):
    ADDRESS = "address"
    GEO_REFERENCE = "geo_reference"
    PARCEL = "parcel"
    BUILDING = "building"
    COMPOSITE_PROPERTY = "composite_property"


class IdentityCandidateStatus(str, Enum):
    PROPOSED = "proposed"
    PLAUSIBLE = "plausible"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class IdentityConflictType(str, Enum):
    NORMALIZED_IDENTITY_DISAGREEMENT = "normalized_identity_disagreement"
    IDENTIFIER_DISAGREEMENT = "identifier_disagreement"
    ADDRESS_PARCEL_MISMATCH = "address_parcel_mismatch"
    COORDINATE_PARCEL_MISMATCH = "coordinate_parcel_mismatch"
    PROVIDER_DISAGREEMENT = "provider_disagreement"
    CARDINALITY_DISAGREEMENT = "cardinality_disagreement"
    TEMPORAL_CONFLICT = "temporal_conflict"
    COVERAGE_LIMITATION = "coverage_limitation"
    EXISTING_PROPERTY_CONFLICT = "existing_property_conflict"


class IdentityConflictSeverity(str, Enum):
    INFORMATION = "information"
    WARNING = "warning"
    BLOCKING = "blocking"


class IdentityConflictState(str, Enum):
    OPEN = "open"
    REQUIRES_REVIEW = "requires_review"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class NormalizedResolutionInput:
    input_type: ResolutionInputType
    raw_input: Mapping[str, object]
    normalized_input: Mapping[str, object]
    normalized_key: str
    normalization_version: str = NORMALIZATION_VERSION


@dataclass(frozen=True)
class CandidateRankingFactors:
    source_reliability: float
    match_quality: float
    identifier_agreement: float
    geometry_agreement: float
    temporal_validity: float
    coverage_quality: float
    conflict_penalty: float = 0.0


@dataclass(frozen=True)
class ProviderCandidateObservation:
    observation_id: str
    candidate_type: IdentityCandidateType
    normalized_key: str
    normalized_identity: Mapping[str, object]
    display_identity: str
    source_record_id: str | None
    retrieved_at: datetime
    ranking_factors: CandidateRankingFactors
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    supporting_evidence_ids: tuple[UUID, ...] = ()
    supporting_reference_ids: tuple[UUID, ...] = ()
    possible_existing_property_entity_id: UUID | None = None
    supersedes_candidate_id: UUID | None = None


@dataclass(frozen=True)
class ProviderConflictObservation:
    left_observation_id: str
    right_observation_id: str | None
    conflict_type: IdentityConflictType
    severity: IdentityConflictSeverity
    source_basis: Mapping[str, object]
    conflict_basis: Mapping[str, object]
    related_identity_reference_id: UUID | None = None
    related_evidence_id: UUID | None = None
    related_property_entity_id: UUID | None = None


@dataclass(frozen=True)
class ProviderResolutionResult:
    status: ResolutionAttemptStatus
    started_at: datetime
    completed_at: datetime
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    candidates: tuple[ProviderCandidateObservation, ...] = ()
    conflicts: tuple[ProviderConflictObservation, ...] = ()
    retrieved_at: datetime | None = None
    error_category: ResolutionErrorCategory | None = None
    error_code: str | None = None
    error_retryable: bool | None = None


class IdentityResolutionProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def strategy_id(self) -> str: ...

    @property
    def source_id(self) -> str: ...

    @property
    def source_environment(self) -> SourceEnvironment: ...

    def resolve(self, resolution_input: NormalizedResolutionInput) -> ProviderResolutionResult: ...


@dataclass(frozen=True)
class ResolutionAttemptDraft:
    attempt_order: int
    strategy_id: str
    provider_id: str
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    status: ResolutionAttemptStatus
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    result_count: int
    started_at: datetime
    completed_at: datetime
    retrieved_at: datetime | None
    error_category: ResolutionErrorCategory | None
    error_code: str | None
    error_retryable: bool | None


@dataclass(frozen=True)
class RankedIdentityCandidate:
    observation_id: str
    candidate_type: IdentityCandidateType
    normalized_key: str
    normalized_identity: Mapping[str, object]
    display_identity: str
    source_id: str
    source_type: SourceType
    source_environment: SourceEnvironment
    source_record_id: str | None
    retrieved_at: datetime
    confidence: float
    confidence_method: str
    ranking_factors: Mapping[str, object]
    rank: int
    candidate_status: IdentityCandidateStatus
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    supporting_evidence_ids: tuple[UUID, ...]
    supporting_reference_ids: tuple[UUID, ...]
    possible_existing_property_entity_id: UUID | None
    supersedes_candidate_id: UUID | None
    needs_human_confirmation: bool = True


@dataclass(frozen=True)
class IdentityConflictDraft:
    left_observation_id: str
    right_observation_id: str | None
    conflict_type: IdentityConflictType
    severity: IdentityConflictSeverity
    source_basis: Mapping[str, object]
    conflict_basis: Mapping[str, object]
    resolution_state: IdentityConflictState = IdentityConflictState.REQUIRES_REVIEW
    related_identity_reference_id: UUID | None = None
    related_evidence_id: UUID | None = None
    related_property_entity_id: UUID | None = None


@dataclass(frozen=True)
class IdentityResolutionDraft:
    resolution_input: NormalizedResolutionInput
    status: ResolutionStatus
    attempts: tuple[ResolutionAttemptDraft, ...]
    candidates: tuple[RankedIdentityCandidate, ...]
    conflicts: tuple[IdentityConflictDraft, ...]
    coverage_status: CoverageStatus
    coverage: Mapping[str, object]
    ambiguity_status: AmbiguityStatus
    started_at: datetime
    completed_at: datetime
    needs_human_confirmation: bool = True


RANKING_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {
        "source_reliability": 0.20,
        "match_quality": 0.25,
        "identifier_agreement": 0.20,
        "geometry_agreement": 0.15,
        "temporal_validity": 0.10,
        "coverage_quality": 0.10,
    }
)
CONFLICT_PENALTY_WEIGHT = 0.25
_BOUNDED_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")
_ERROR_CODE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")


def _validation_failed() -> VNextError:
    return VNextError.validation_failed()


def _json_object(value: Mapping[str, object], *, maximum: int = 16_384) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _validation_failed()
    try:
        encoded = json.dumps(dict(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        decoded = json.loads(encoded)
    except (TypeError, ValueError):
        raise _validation_failed() from None
    if not isinstance(decoded, dict) or len(encoded.encode("utf-8")) > maximum:
        raise _validation_failed()
    return decoded


def _text(value: object, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise _validation_failed()
    selected = " ".join(unicodedata.normalize("NFKC", value).split())
    if not selected or len(selected) > maximum or "\x00" in selected:
        raise _validation_failed()
    return selected


def _optional_text(value: object | None, *, maximum: int) -> str | None:
    return None if value is None else _text(value, maximum=maximum)


def _coordinate(value: object, *, latitude: bool) -> float:
    if isinstance(value, bool):
        raise _validation_failed()
    try:
        selected = float(value)
    except (TypeError, ValueError):
        raise _validation_failed() from None
    lower, upper = (-90.0, 90.0) if latitude else (-180.0, 180.0)
    if not math.isfinite(selected) or not lower <= selected <= upper:
        raise _validation_failed()
    return 0.0 if selected == 0 else selected


def normalize_resolution_input(
    input_type: ResolutionInputType,
    raw_input: Mapping[str, object],
) -> NormalizedResolutionInput:
    """Normalize representation only; never infer an official identity."""

    raw = _json_object(raw_input)
    if input_type is ResolutionInputType.ADDRESS:
        address = _text(raw.get("address"), maximum=512)
        normalized = {"address": address}
        key = f"address:{address}"
    elif input_type is ResolutionInputType.LOT_NUMBER:
        jurisdiction = _text(raw.get("jurisdiction"), maximum=160)
        section = _text(raw.get("section"), maximum=160)
        subsection = _optional_text(raw.get("subsection"), maximum=160)
        lot_number = _text(raw.get("lot_number"), maximum=120)
        normalized = {
            "jurisdiction": jurisdiction,
            "section": section,
            "lot_number": lot_number,
        }
        if subsection is not None:
            normalized["subsection"] = subsection
        key = "lot:" + "|".join(
            (jurisdiction, section, subsection or "", lot_number)
        )
    elif input_type is ResolutionInputType.BUILDING_NUMBER:
        jurisdiction = _optional_text(raw.get("jurisdiction"), maximum=160)
        building_number = _text(raw.get("building_number"), maximum=160)
        normalized = {"building_number": building_number}
        if jurisdiction is not None:
            normalized["jurisdiction"] = jurisdiction
        key = f"building:{jurisdiction or ''}|{building_number}"
    elif input_type in {ResolutionInputType.COORDINATES, ResolutionInputType.MAP_CLICK}:
        latitude = _coordinate(raw.get("latitude"), latitude=True)
        longitude = _coordinate(raw.get("longitude"), latitude=False)
        crs = _text(raw.get("crs"), maximum=40).upper()
        if crs != "EPSG:4326":
            # Reprojection without an explicit reviewed adapter would be a guess.
            raise _validation_failed()
        normalized = {"latitude": latitude, "longitude": longitude, "crs": crs}
        if input_type is ResolutionInputType.MAP_CLICK:
            map_context = _optional_text(raw.get("map_context"), maximum=160)
            if map_context is not None:
                normalized["map_context"] = map_context
        key = f"geo:{latitude:.12g},{longitude:.12g};{crs.lower()}"
    else:  # pragma: no cover - Enum construction closes this path.
        raise _validation_failed()
    return NormalizedResolutionInput(
        input_type=input_type,
        raw_input=raw,
        normalized_input=_json_object(normalized),
        normalized_key=key,
    )


def _bounded_factor(value: float) -> float:
    try:
        selected = float(value)
    except (TypeError, ValueError):
        raise _validation_failed() from None
    if not math.isfinite(selected) or not 0 <= selected <= 1:
        raise _validation_failed()
    return selected


def rank_candidate(factors: CandidateRankingFactors) -> tuple[float, Mapping[str, object]]:
    values = {
        "source_reliability": _bounded_factor(factors.source_reliability),
        "match_quality": _bounded_factor(factors.match_quality),
        "identifier_agreement": _bounded_factor(factors.identifier_agreement),
        "geometry_agreement": _bounded_factor(factors.geometry_agreement),
        "temporal_validity": _bounded_factor(factors.temporal_validity),
        "coverage_quality": _bounded_factor(factors.coverage_quality),
        "conflict_penalty": _bounded_factor(factors.conflict_penalty),
    }
    positive = sum(values[name] * weight for name, weight in RANKING_WEIGHTS.items())
    penalty = values["conflict_penalty"] * CONFLICT_PENALTY_WEIGHT
    confidence = round(max(0.0, min(1.0, positive - penalty)), 4)
    return confidence, {
        "method": RANKING_METHOD,
        "factors": values,
        "weights": dict(RANKING_WEIGHTS),
        "weighted_positive": round(positive, 6),
        "conflict_penalty_weight": CONFLICT_PENALTY_WEIGHT,
        "final_confidence": confidence,
    }


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.utcoffset() is not None


def _source_definition(provider: IdentityResolutionProvider) -> SourceDefinition:
    provider_id = str(provider.provider_id).strip()
    strategy_id = str(provider.strategy_id).strip()
    source_id = str(provider.source_id).strip()
    if not all(_BOUNDED_ID.fullmatch(value) for value in (provider_id, strategy_id, source_id)):
        raise _validation_failed()
    definition = DATA_SOURCE_REGISTRY.get(source_id)
    if (
        definition is None
        or provider.source_environment not in definition.environments
        or not definition.request_appendable
    ):
        raise VNextError.permission_denied()
    return definition


def _validate_provider_result(result: ProviderResolutionResult) -> None:
    if (
        not _aware(result.started_at)
        or not _aware(result.completed_at)
        or result.completed_at < result.started_at
        or len(result.candidates) > MAX_CANDIDATES
    ):
        raise _validation_failed()
    _json_object(result.coverage)
    successful = result.status in {
        ResolutionAttemptStatus.AVAILABLE,
        ResolutionAttemptStatus.LIMITED,
        ResolutionAttemptStatus.NO_MATCH,
    }
    if successful:
        if (
            result.retrieved_at is None
            or not _aware(result.retrieved_at)
            or not result.started_at <= result.retrieved_at <= result.completed_at
            or result.error_category is not None
            or result.error_code is not None
            or result.error_retryable is not None
        ):
            raise _validation_failed()
    elif result.retrieved_at is not None or result.error_category is None:
        raise _validation_failed()
    if result.status in {ResolutionAttemptStatus.AVAILABLE, ResolutionAttemptStatus.LIMITED}:
        if not result.candidates:
            raise _validation_failed()
    elif result.candidates:
        raise _validation_failed()
    if result.status is ResolutionAttemptStatus.NO_MATCH and result.candidates:
        raise _validation_failed()
    if result.error_code is not None and not _ERROR_CODE.fullmatch(result.error_code):
        raise _validation_failed()


def _candidate(
    observation: ProviderCandidateObservation,
    *,
    source: SourceDefinition,
    environment: SourceEnvironment,
) -> RankedIdentityCandidate:
    observation_id = _text(observation.observation_id, maximum=120)
    normalized_key = _text(observation.normalized_key, maximum=512)
    display_identity = _text(observation.display_identity, maximum=512)
    source_record_id = _optional_text(observation.source_record_id, maximum=240)
    if not _aware(observation.retrieved_at):
        raise _validation_failed()
    evidence_ids = tuple(observation.supporting_evidence_ids)
    reference_ids = tuple(observation.supporting_reference_ids)
    if (
        len(evidence_ids) > MAX_SUPPORT_IDS
        or len(reference_ids) > MAX_SUPPORT_IDS
        or len(set(evidence_ids)) != len(evidence_ids)
        or len(set(reference_ids)) != len(reference_ids)
    ):
        raise _validation_failed()
    confidence, trace = rank_candidate(observation.ranking_factors)
    status = (
        IdentityCandidateStatus.INSUFFICIENT
        if observation.coverage_status in {CoverageStatus.UNKNOWN, CoverageStatus.UNAVAILABLE}
        else IdentityCandidateStatus.PLAUSIBLE
    )
    return RankedIdentityCandidate(
        observation_id=observation_id,
        candidate_type=observation.candidate_type,
        normalized_key=normalized_key,
        normalized_identity=_json_object(observation.normalized_identity),
        display_identity=display_identity,
        source_id=source.source_id,
        source_type=source.source_type,
        source_environment=environment,
        source_record_id=source_record_id,
        retrieved_at=observation.retrieved_at,
        confidence=confidence,
        confidence_method=RANKING_METHOD,
        ranking_factors=trace,
        rank=0,
        candidate_status=status,
        coverage_status=observation.coverage_status,
        coverage=_json_object(observation.coverage),
        supporting_evidence_ids=evidence_ids,
        supporting_reference_ids=reference_ids,
        possible_existing_property_entity_id=observation.possible_existing_property_entity_id,
        supersedes_candidate_id=observation.supersedes_candidate_id,
    )


def _aggregate_coverage(attempts: Sequence[ResolutionAttemptDraft]) -> CoverageStatus:
    if not attempts or all(item.coverage_status is CoverageStatus.UNAVAILABLE for item in attempts):
        return CoverageStatus.UNAVAILABLE
    statuses = {item.coverage_status for item in attempts}
    if statuses == {CoverageStatus.KNOWN}:
        return CoverageStatus.KNOWN
    if CoverageStatus.PARTIAL in statuses or CoverageStatus.UNAVAILABLE in statuses:
        return CoverageStatus.PARTIAL
    return CoverageStatus.UNKNOWN


class IdentityResolutionEngine:
    """Provider-independent orchestration with deterministic, explainable ranking."""

    def __init__(
        self,
        providers: Sequence[IdentityResolutionProvider] = (),
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if len(providers) > MAX_ATTEMPTS:
            raise _validation_failed()
        self._providers = tuple(providers)
        self._clock = clock

    @property
    def providers(self) -> tuple[IdentityResolutionProvider, ...]:
        """Expose the immutable configured set for the API environment gate."""

        return self._providers

    def resolve(
        self,
        *,
        input_type: ResolutionInputType,
        raw_input: Mapping[str, object],
    ) -> IdentityResolutionDraft:
        started_at = self._clock()
        if not _aware(started_at):
            raise _validation_failed()
        resolution_input = normalize_resolution_input(input_type, raw_input)
        attempts: list[ResolutionAttemptDraft] = []
        candidates: list[RankedIdentityCandidate] = []
        conflicts: list[IdentityConflictDraft] = []

        if not self._providers:
            completed = self._clock()
            attempts.append(
                ResolutionAttemptDraft(
                    attempt_order=1,
                    strategy_id="provider-registry",
                    provider_id="identity-provider-registry",
                    source_id="vnext-deterministic",
                    source_type=SourceType.DETERMINISTIC,
                    source_environment=SourceEnvironment.PRODUCTION,
                    status=ResolutionAttemptStatus.UNAVAILABLE,
                    coverage_status=CoverageStatus.UNAVAILABLE,
                    coverage={"reason": "no_approved_provider_configured"},
                    result_count=0,
                    started_at=started_at,
                    completed_at=completed,
                    retrieved_at=None,
                    error_category=ResolutionErrorCategory.NOT_CONFIGURED,
                    error_code="provider_not_configured",
                    error_retryable=False,
                )
            )
        else:
            for order, provider in enumerate(self._providers, start=1):
                source = _source_definition(provider)
                try:
                    result = provider.resolve(resolution_input)
                    _validate_provider_result(result)
                except Exception:
                    attempted_at = self._clock()
                    result = ProviderResolutionResult(
                        status=ResolutionAttemptStatus.ERROR,
                        started_at=attempted_at,
                        completed_at=attempted_at,
                        coverage_status=CoverageStatus.UNAVAILABLE,
                        coverage={"reason": "provider_error"},
                        error_category=ResolutionErrorCategory.INTERNAL_ERROR,
                        error_code="provider_exception",
                        error_retryable=False,
                    )
                attempts.append(
                    ResolutionAttemptDraft(
                        attempt_order=order,
                        strategy_id=str(provider.strategy_id).strip(),
                        provider_id=str(provider.provider_id).strip(),
                        source_id=source.source_id,
                        source_type=source.source_type,
                        source_environment=provider.source_environment,
                        status=result.status,
                        coverage_status=result.coverage_status,
                        coverage=_json_object(result.coverage),
                        result_count=len(result.candidates),
                        started_at=result.started_at,
                        completed_at=result.completed_at,
                        retrieved_at=result.retrieved_at,
                        error_category=result.error_category,
                        error_code=result.error_code,
                        error_retryable=result.error_retryable,
                    )
                )
                candidates.extend(
                    _candidate(
                        item,
                        source=source,
                        environment=provider.source_environment,
                    )
                    for item in result.candidates
                )
                conflicts.extend(
                    IdentityConflictDraft(
                        left_observation_id=_text(item.left_observation_id, maximum=120),
                        right_observation_id=_optional_text(item.right_observation_id, maximum=120),
                        conflict_type=item.conflict_type,
                        severity=item.severity,
                        source_basis=_json_object(item.source_basis),
                        conflict_basis=_json_object(item.conflict_basis),
                        related_identity_reference_id=item.related_identity_reference_id,
                        related_evidence_id=item.related_evidence_id,
                        related_property_entity_id=item.related_property_entity_id,
                    )
                    for item in result.conflicts
                )

        if len(candidates) > MAX_CANDIDATES:
            raise _validation_failed()
        observation_ids = [item.observation_id for item in candidates]
        if len(observation_ids) != len(set(observation_ids)):
            raise _validation_failed()
        known = set(observation_ids)
        conflicting_ids: set[str] = set()
        for conflict in conflicts:
            if (
                conflict.left_observation_id not in known
                or conflict.right_observation_id is not None
                and conflict.right_observation_id not in known
                or conflict.right_observation_id == conflict.left_observation_id
                or (
                    conflict.right_observation_id is None
                    and conflict.related_identity_reference_id is None
                    and conflict.related_evidence_id is None
                    and conflict.related_property_entity_id is None
                )
            ):
                raise _validation_failed()
            conflicting_ids.add(conflict.left_observation_id)
            if conflict.right_observation_id is not None:
                conflicting_ids.add(conflict.right_observation_id)

        candidates = [
            replace(item, candidate_status=IdentityCandidateStatus.CONFLICTING)
            if item.observation_id in conflicting_ids
            else item
            for item in candidates
        ]
        candidates.sort(
            key=lambda item: (
                -item.confidence,
                item.candidate_type.value,
                item.normalized_key,
                item.source_id,
                item.source_record_id or "",
                item.observation_id,
            )
        )
        candidates = [replace(item, rank=index) for index, item in enumerate(candidates, start=1)]

        limiting_statuses = {
            ResolutionAttemptStatus.LIMITED,
            ResolutionAttemptStatus.UNAVAILABLE,
            ResolutionAttemptStatus.TIMEOUT,
            ResolutionAttemptStatus.UNSUPPORTED,
            ResolutionAttemptStatus.ERROR,
        }
        has_limitation = any(item.status in limiting_statuses for item in attempts)
        if conflicts:
            status = ResolutionStatus.AMBIGUOUS
            ambiguity = AmbiguityStatus.MATERIAL_CONFLICT
        elif len(candidates) > 1:
            status = ResolutionStatus.AMBIGUOUS
            ambiguity = AmbiguityStatus.MULTIPLE_CANDIDATES
        elif len(candidates) == 1 and has_limitation:
            status = ResolutionStatus.PARTIALLY_RESOLVED
            ambiguity = AmbiguityStatus.PROVIDER_LIMITATION
        elif len(candidates) == 1:
            status = ResolutionStatus.CANDIDATES_FOUND
            ambiguity = AmbiguityStatus.NONE
        else:
            status = ResolutionStatus.UNRESOLVED
            ambiguity = (
                AmbiguityStatus.PROVIDER_LIMITATION
                if has_limitation
                else AmbiguityStatus.INSUFFICIENT_EVIDENCE
            )
        completed_at = self._clock()
        if not _aware(completed_at) or completed_at < started_at:
            raise _validation_failed()
        coverage_status = _aggregate_coverage(attempts)
        return IdentityResolutionDraft(
            resolution_input=resolution_input,
            status=status,
            attempts=tuple(attempts),
            candidates=tuple(candidates),
            conflicts=tuple(conflicts),
            coverage_status=coverage_status,
            coverage={
                "attempt_count": len(attempts),
                "available_attempt_count": sum(
                    item.status is ResolutionAttemptStatus.AVAILABLE for item in attempts
                ),
                "limited_or_failed_attempt_count": sum(
                    item.status in limiting_statuses for item in attempts
                ),
            },
            ambiguity_status=ambiguity,
            started_at=started_at,
            completed_at=completed_at,
        )
