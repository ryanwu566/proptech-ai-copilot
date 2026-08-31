from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from services.vnext.identity_resolution import (
    AmbiguityStatus,
    CandidateRankingFactors,
    IdentityCandidateStatus,
    IdentityCandidateType,
    IdentityConflictSeverity,
    IdentityConflictType,
    IdentityResolutionEngine,
    ProviderCandidateObservation,
    ProviderConflictObservation,
    ProviderResolutionResult,
    ResolutionAttemptStatus,
    ResolutionErrorCategory,
    ResolutionInputType,
    ResolutionStatus,
    normalize_resolution_input,
)
from services.vnext.property_graph import CoverageStatus, SourceEnvironment


NOW = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
EVIDENCE_ID = UUID("60000000-0000-4000-8000-000000000001")
REFERENCE_ID = UUID("30000000-0000-4000-8000-000000000001")
PROPERTY_ID = UUID("10000000-0000-4000-8000-000000000001")


@dataclass(frozen=True)
class _Provider:
    provider_id: str
    result: ProviderResolutionResult
    source_id: str = "vnext-test"
    source_environment: SourceEnvironment = SourceEnvironment.TEST
    strategy_id: str = "fixture-lookup-v1"

    def resolve(self, _resolution_input):
        return self.result


class _ExplodingProvider:
    provider_id = "exploding-fixture"
    source_id = "vnext-test"
    source_environment = SourceEnvironment.TEST
    strategy_id = "fixture-lookup-v1"

    def resolve(self, _resolution_input):
        raise RuntimeError("secret provider detail must not be retained")


def _factors(*, confidence_099: bool = False) -> CandidateRankingFactors:
    return CandidateRankingFactors(
        source_reliability=1,
        match_quality=1,
        identifier_agreement=1,
        geometry_agreement=1,
        temporal_validity=1,
        coverage_quality=0.9 if confidence_099 else 1,
    )


def _candidate(
    observation_id: str,
    candidate_type: IdentityCandidateType = IdentityCandidateType.ADDRESS,
    *,
    normalized_key: str | None = None,
    confidence_099: bool = False,
    coverage_status: CoverageStatus = CoverageStatus.KNOWN,
    evidence_ids: tuple[UUID, ...] = (),
    reference_ids: tuple[UUID, ...] = (),
    existing_property_id: UUID | None = None,
) -> ProviderCandidateObservation:
    key = normalized_key or f"{candidate_type.value}:{observation_id}"
    return ProviderCandidateObservation(
        observation_id=observation_id,
        candidate_type=candidate_type,
        normalized_key=key,
        normalized_identity={"key": key},
        display_identity=f"Candidate {observation_id}",
        source_record_id=f"fixture-record-{observation_id}",
        retrieved_at=NOW,
        ranking_factors=_factors(confidence_099=confidence_099),
        coverage_status=coverage_status,
        coverage={"geography": "fixture", "completeness": coverage_status.value},
        supporting_evidence_ids=evidence_ids,
        supporting_reference_ids=reference_ids,
        possible_existing_property_entity_id=existing_property_id,
    )


def _result(
    status: ResolutionAttemptStatus,
    *candidates: ProviderCandidateObservation,
    conflicts: tuple[ProviderConflictObservation, ...] = (),
    coverage_status: CoverageStatus | None = None,
) -> ProviderResolutionResult:
    successful = status in {
        ResolutionAttemptStatus.AVAILABLE,
        ResolutionAttemptStatus.LIMITED,
        ResolutionAttemptStatus.NO_MATCH,
    }
    category = None
    retryable = None
    code = None
    if not successful:
        category = {
            ResolutionAttemptStatus.UNAVAILABLE: ResolutionErrorCategory.PROVIDER_UNAVAILABLE,
            ResolutionAttemptStatus.TIMEOUT: ResolutionErrorCategory.TIMEOUT,
            ResolutionAttemptStatus.UNSUPPORTED: ResolutionErrorCategory.UNSUPPORTED_INPUT,
            ResolutionAttemptStatus.ERROR: ResolutionErrorCategory.INTERNAL_ERROR,
        }[status]
        retryable = status in {ResolutionAttemptStatus.UNAVAILABLE, ResolutionAttemptStatus.TIMEOUT}
        code = f"fixture_{status.value}"
    selected_coverage = coverage_status or (
        CoverageStatus.KNOWN if successful else CoverageStatus.UNAVAILABLE
    )
    return ProviderResolutionResult(
        status=status,
        started_at=NOW,
        completed_at=NOW,
        retrieved_at=NOW if successful else None,
        coverage_status=selected_coverage,
        coverage={"scope": "fixture", "status": selected_coverage.value},
        candidates=tuple(candidates),
        conflicts=conflicts,
        error_category=category,
        error_code=code,
        error_retryable=retryable,
    )


def _resolve(*providers: _Provider | _ExplodingProvider):
    return IdentityResolutionEngine(providers, clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市 信義路 1 號"},
    )


def test_one_clear_candidate_is_resolved_candidate_set_but_not_confirmed() -> None:
    result = _resolve(_Provider("clear-fixture", _result(ResolutionAttemptStatus.AVAILABLE, _candidate("a"))))

    assert result.status is ResolutionStatus.CANDIDATES_FOUND
    assert result.ambiguity_status is AmbiguityStatus.NONE
    assert result.needs_human_confirmation is True
    assert len(result.candidates) == 1
    assert result.candidates[0].candidate_status is IdentityCandidateStatus.PLAUSIBLE
    assert result.candidates[0].needs_human_confirmation is True


def test_multiple_candidates_are_ambiguous_and_rank_deterministically() -> None:
    lower = ProviderCandidateObservation(
        **{
            **_candidate("parcel-b", IdentityCandidateType.PARCEL).__dict__,
            "ranking_factors": CandidateRankingFactors(0.7, 0.7, 0.7, 0.7, 0.7, 0.7),
        }
    )
    result = _resolve(
        _Provider(
            "multiple-fixture",
            _result(
                ResolutionAttemptStatus.AVAILABLE,
                lower,
                _candidate("parcel-a", IdentityCandidateType.PARCEL),
            ),
        )
    )

    assert result.status is ResolutionStatus.AMBIGUOUS
    assert result.ambiguity_status is AmbiguityStatus.MULTIPLE_CANDIDATES
    assert [item.observation_id for item in result.candidates] == ["parcel-a", "parcel-b"]
    assert [item.rank for item in result.candidates] == [1, 2]
    assert result.candidates[0].ranking_factors["method"] == "identity-ranking-v1"


def test_no_match_is_unresolved_and_never_inferrs_nonexistent_property() -> None:
    result = _resolve(_Provider("no-match-fixture", _result(ResolutionAttemptStatus.NO_MATCH)))

    assert result.status is ResolutionStatus.UNRESOLVED
    assert result.candidates == ()
    assert result.attempts[0].status is ResolutionAttemptStatus.NO_MATCH
    assert "exists" not in result.coverage


def test_unavailable_provider_is_unresolved_or_partial_when_another_candidate_exists() -> None:
    unavailable = _Provider("unavailable-fixture", _result(ResolutionAttemptStatus.UNAVAILABLE))
    unresolved = _resolve(unavailable)
    partial = _resolve(
        _Provider("available-fixture", _result(ResolutionAttemptStatus.AVAILABLE, _candidate("a"))),
        unavailable,
    )

    assert unresolved.status is ResolutionStatus.UNRESOLVED
    assert unresolved.ambiguity_status is AmbiguityStatus.PROVIDER_LIMITATION
    assert partial.status is ResolutionStatus.PARTIALLY_RESOLVED
    assert len(partial.candidates) == 1


def test_conflicting_sources_retain_both_candidates_and_conflict_basis() -> None:
    conflict = ProviderConflictObservation(
        left_observation_id="source-a",
        right_observation_id="source-b",
        conflict_type=IdentityConflictType.PROVIDER_DISAGREEMENT,
        severity=IdentityConflictSeverity.BLOCKING,
        source_basis={"left": "fixture-source-a", "right": "fixture-source-b"},
        conflict_basis={"dimension": "normalized_address", "agreement": False},
        related_evidence_id=EVIDENCE_ID,
    )
    result = _resolve(
        _Provider("source-a-provider", _result(ResolutionAttemptStatus.AVAILABLE, _candidate("source-a"))),
        _Provider(
            "source-b-provider",
            _result(
                ResolutionAttemptStatus.AVAILABLE,
                _candidate("source-b", normalized_key="address:different"),
                conflicts=(conflict,),
            ),
        ),
    )

    assert result.status is ResolutionStatus.AMBIGUOUS
    assert result.ambiguity_status is AmbiguityStatus.MATERIAL_CONFLICT
    assert {item.observation_id for item in result.candidates} == {"source-a", "source-b"}
    assert {item.candidate_status for item in result.candidates} == {
        IdentityCandidateStatus.CONFLICTING
    }
    assert result.conflicts[0].source_basis == {
        "left": "fixture-source-a",
        "right": "fixture-source-b",
    }


def test_confidence_point_99_still_requires_human_and_creates_no_entity() -> None:
    result = _resolve(
        _Provider(
            "high-confidence-fixture",
            _result(ResolutionAttemptStatus.AVAILABLE, _candidate("high", confidence_099=True)),
        )
    )

    assert result.candidates[0].confidence == 0.99
    assert result.needs_human_confirmation is True
    assert result.candidates[0].needs_human_confirmation is True
    assert not hasattr(result, "property_entity_id")
    assert "confirmed" not in {status.value for status in IdentityCandidateStatus}


def test_existing_property_hypothesis_is_retained_without_merge() -> None:
    result = _resolve(
        _Provider(
            "existing-hypothesis-fixture",
            _result(
                ResolutionAttemptStatus.AVAILABLE,
                _candidate("possible-existing", existing_property_id=PROPERTY_ID),
            ),
        )
    )

    assert result.candidates[0].possible_existing_property_entity_id == PROPERTY_ID
    assert result.candidates[0].needs_human_confirmation is True
    assert not hasattr(result, "merged_property_entity_id")


@pytest.mark.parametrize(
    ("input_type", "raw_input", "candidate_type"),
    [
        (
            ResolutionInputType.ADDRESS,
            {"address": "台北市信義路1號"},
            IdentityCandidateType.PARCEL,
        ),
        (
            ResolutionInputType.LOT_NUMBER,
            {"jurisdiction": "台北市", "section": "信義段", "lot_number": "1"},
            IdentityCandidateType.BUILDING,
        ),
        (
            ResolutionInputType.BUILDING_NUMBER,
            {"jurisdiction": "台北市", "building_number": "建號1"},
            IdentityCandidateType.PARCEL,
        ),
    ],
)
def test_resolution_cardinality_allows_one_input_to_multiple_candidates(
    input_type: ResolutionInputType,
    raw_input: dict[str, object],
    candidate_type: IdentityCandidateType,
) -> None:
    provider = _Provider(
        "cardinality-fixture",
        _result(
            ResolutionAttemptStatus.AVAILABLE,
            _candidate("first", candidate_type),
            _candidate("second", candidate_type),
        ),
    )
    result = IdentityResolutionEngine((provider,), clock=lambda: NOW).resolve(
        input_type=input_type,
        raw_input=raw_input,
    )

    assert result.status is ResolutionStatus.AMBIGUOUS
    assert [item.candidate_type for item in result.candidates] == [candidate_type, candidate_type]


def test_candidate_provenance_retains_source_record_retrieval_coverage_and_support() -> None:
    result = _resolve(
        _Provider(
            "provenance-fixture",
            _result(
                ResolutionAttemptStatus.LIMITED,
                _candidate(
                    "provenance",
                    coverage_status=CoverageStatus.PARTIAL,
                    evidence_ids=(EVIDENCE_ID,),
                    reference_ids=(REFERENCE_ID,),
                ),
                coverage_status=CoverageStatus.PARTIAL,
            ),
        )
    )
    candidate = result.candidates[0]

    assert result.status is ResolutionStatus.PARTIALLY_RESOLVED
    assert candidate.source_id == "vnext-test"
    assert candidate.source_environment is SourceEnvironment.TEST
    assert candidate.source_record_id == "fixture-record-provenance"
    assert candidate.retrieved_at == NOW
    assert candidate.coverage_status is CoverageStatus.PARTIAL
    assert candidate.confidence_method == "identity-ranking-v1"
    assert candidate.supporting_evidence_ids == (EVIDENCE_ID,)
    assert candidate.supporting_reference_ids == (REFERENCE_ID,)


def test_unknown_coverage_is_not_promoted_to_positive_authority() -> None:
    result = _resolve(
        _Provider(
            "unknown-fixture",
            _result(
                ResolutionAttemptStatus.AVAILABLE,
                _candidate("unknown", coverage_status=CoverageStatus.UNKNOWN),
                coverage_status=CoverageStatus.UNKNOWN,
            ),
        )
    )

    assert result.candidates[0].candidate_status is IdentityCandidateStatus.INSUFFICIENT
    assert result.candidates[0].needs_human_confirmation is True


def test_provider_exception_becomes_bounded_attempt_without_raw_error() -> None:
    result = _resolve(_ExplodingProvider())

    assert result.status is ResolutionStatus.UNRESOLVED
    assert result.attempts[0].status is ResolutionAttemptStatus.ERROR
    assert result.attempts[0].error_category is ResolutionErrorCategory.INTERNAL_ERROR
    assert result.attempts[0].error_code == "provider_exception"
    assert "secret" not in str(result.attempts[0])


def test_normalization_is_deterministic_preserves_raw_and_does_not_reproject() -> None:
    first = normalize_resolution_input(
        ResolutionInputType.ADDRESS,
        {"address": "  台北市  ＡＢＣ路  1號  "},
    )
    second = normalize_resolution_input(
        ResolutionInputType.ADDRESS,
        {"address": "  台北市  ＡＢＣ路  1號  "},
    )

    assert first == second
    assert first.raw_input["address"] == "  台北市  ＡＢＣ路  1號  "
    assert first.normalized_input["address"] == "台北市 ABC路 1號"

    with pytest.raises(Exception):
        normalize_resolution_input(
            ResolutionInputType.COORDINATES,
            {"latitude": 25.0, "longitude": 121.5, "crs": "EPSG:3826"},
        )


def test_resolution_modules_have_no_entity_creation_or_llm_ranking_path() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (
        (root / "services/vnext/identity_resolution.py").read_text(encoding="utf-8")
        + (root / "services/vnext/identity_resolution_repository.py").read_text(
            encoding="utf-8"
        )
    ).lower()

    assert "create_property_entity" not in source
    assert "insert into vnext_core.property_entities" not in source
    assert "update vnext_core.cases" not in source
    assert "openai" not in source
    assert "chat_completion" not in source
    assert "language_model" not in source
