"""Offline tests for the TEST-only TGOS identity observation provider seam.

No live TGOS call is made: a fake adapter is injected. These tests prove the
provider conforms to the IdentityResolutionProvider contract, preserves TGOS
provenance/coverage/quality, fails closed, keeps tgos-address out of production
identity authority, and always reaches the engine as human-confirmable
candidates/conflicts (never auto-merge, never materialization).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_resolution import (
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
    _source_definition,
    _validate_provider_result,
    normalize_resolution_input,
)
from services.vnext.property_graph import (
    CoverageStatus,
    DATA_SOURCE_REGISTRY,
    SourceEnvironment,
    SourceType,
)
from services.vnext.tgos_observation_provider import (
    OBSERVATION_SOURCE_ID,
    TGOS_SOURCE_ID,
    TgosIdentityObservationProvider,
)


NOW = datetime(2026, 9, 18, 8, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Offline fake for the reused backend-only TGOS geocoding adapter.
# --------------------------------------------------------------------------- #
@dataclass
class _FakeTgosAdapter:
    available: bool = True
    last_error: str = ""
    item: dict[str, Any] | None = None
    raises: bool = False
    calls: list[str] = field(default_factory=list)

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None:
        self.calls.append(query)
        if self.raises:
            raise RuntimeError("secret provider internals must never leak")
        return self.item


def _rooftop_item() -> dict[str, Any]:
    return {
        "id": "tgos-台北市信義區信義路五段7號",
        "city": "台北市",
        "district": "信義區",
        "road": "信義路五段",
        "formatted_address": "台北市信義區信義路五段7號",
        "place_id": "",
        "center": {"lat": 25.033, "lng": 121.5645},
        "geocoding_metadata": {
            "location_type": "ROOFTOP",
            "partial_match": False,
        },
    }


def _partial_item() -> dict[str, Any]:
    item = _rooftop_item()
    item["geocoding_metadata"] = {"location_type": "GEOMETRIC_CENTER", "partial_match": True}
    return item


def _provider(adapter: _FakeTgosAdapter) -> TgosIdentityObservationProvider:
    return TgosIdentityObservationProvider(adapter, clock=lambda: NOW)


def _address_input():
    return normalize_resolution_input(
        ResolutionInputType.ADDRESS, {"address": "台北市信義區信義路五段7號"}
    )


# --------------------------------------------------------------------------- #
# 1. Valid TGOS fixture -> valid ProviderResolutionResult with a candidate.
# --------------------------------------------------------------------------- #
def test_valid_fixture_yields_valid_result() -> None:
    provider = _provider(_FakeTgosAdapter(item=_rooftop_item()))
    result = provider.resolve(_address_input())

    # Must pass the engine's own contract validator.
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.AVAILABLE
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.candidate_type is IdentityCandidateType.ADDRESS
    assert candidate.normalized_identity["formatted_address"] == "台北市信義區信義路五段7號"


# --------------------------------------------------------------------------- #
# 2 & 3. source id and source environment.
# --------------------------------------------------------------------------- #
def test_source_id_and_environment() -> None:
    provider = _provider(_FakeTgosAdapter(item=_rooftop_item()))
    # Declared official provenance is tgos-address.
    assert provider.tgos_source_id == TGOS_SOURCE_ID == "tgos-address"
    # Engine-facing appendable source is the TEST namespace.
    assert provider.source_id == OBSERVATION_SOURCE_ID == "vnext-test"
    assert provider.source_environment is SourceEnvironment.TEST


# --------------------------------------------------------------------------- #
# 4. Production provider verification still rejects TGOS.
#    a) The registry keeps tgos-address non-appendable / non-production.
#    b) A provider that (wrongly) presents tgos-address as the engine-facing
#       source id is rejected by _source_definition (permission_denied).
# --------------------------------------------------------------------------- #
def test_registry_keeps_tgos_address_locked_down() -> None:
    definition = DATA_SOURCE_REGISTRY["tgos-address"]
    assert definition.source_type is SourceType.OFFICIAL
    assert definition.readiness == "prototype_partial"  # not production_accepted
    assert definition.request_appendable is False
    assert SourceEnvironment.PRODUCTION in definition.environments


def test_engine_rejects_provider_declaring_tgos_address_source() -> None:
    @dataclass
    class _MisdeclaredProvider:
        provider_id: str = "tgos-address-observation"
        strategy_id: str = "tgos-address-observation-v1"
        source_id: str = "tgos-address"  # appendable=False -> must be denied
        source_environment: SourceEnvironment = SourceEnvironment.TEST

    with pytest.raises(VNextError) as excinfo:
        _source_definition(_MisdeclaredProvider())
    assert excinfo.value.code is ErrorCode.PERMISSION_DENIED


# --------------------------------------------------------------------------- #
# 5. Partial TGOS data remains partial.
# --------------------------------------------------------------------------- #
def test_partial_data_remains_partial() -> None:
    provider = _provider(_FakeTgosAdapter(item=_partial_item()))
    result = provider.resolve(_address_input())
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.LIMITED
    assert result.coverage_status is CoverageStatus.PARTIAL
    assert result.candidates[0].coverage_status is CoverageStatus.PARTIAL


# --------------------------------------------------------------------------- #
# 6. Unavailable remains unavailable (credentials absent).
# --------------------------------------------------------------------------- #
def test_unavailable_remains_unavailable() -> None:
    provider = _provider(_FakeTgosAdapter(available=False))
    result = provider.resolve(_address_input())
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.UNAVAILABLE
    assert result.coverage_status is CoverageStatus.UNAVAILABLE
    assert result.candidates == ()
    assert result.error_category is ResolutionErrorCategory.NOT_CONFIGURED
    assert result.retrieved_at is None


def test_recorded_transport_error_maps_to_unavailable() -> None:
    # The legacy adapter collapses timeout/transport failures into a recorded
    # last_error with a None result. We report that honestly as UNAVAILABLE
    # rather than guessing a timeout subtype from a localized message.
    provider = _provider(_FakeTgosAdapter(item=None, last_error="TGOS 暫時無法回應"))
    result = provider.resolve(_address_input())
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.UNAVAILABLE
    assert result.error_category is ResolutionErrorCategory.PROVIDER_UNAVAILABLE
    assert result.candidates == ()


# --------------------------------------------------------------------------- #
# 7. Malformed provider output fails closed (no candidate).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bad_item",
    [
        {"formatted_address": "地址", "center": {"lat": "x", "lng": 121.0}},
        {"formatted_address": "", "center": {"lat": 25.0, "lng": 121.0}},
        {"formatted_address": "地址", "center": {}},
        {"center": {"lat": 25.0, "lng": 121.0}},  # missing formatted_address
    ],
)
def test_malformed_output_fails_closed(bad_item: dict[str, Any]) -> None:
    provider = _provider(_FakeTgosAdapter(item=bad_item))
    result = provider.resolve(_address_input())
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.ERROR
    assert result.error_category is ResolutionErrorCategory.INVALID_RESPONSE
    assert result.candidates == ()


def test_provider_exception_fails_closed_without_leaking() -> None:
    provider = _provider(_FakeTgosAdapter(raises=True))
    result = provider.resolve(_address_input())
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.ERROR
    assert result.error_category is ResolutionErrorCategory.TRANSPORT_ERROR
    # No raw provider detail retained anywhere in the result.
    assert "secret" not in result.error_code
    assert "secret" not in str(result.coverage)


# --------------------------------------------------------------------------- #
# 8. No-result does not fabricate a candidate.
# --------------------------------------------------------------------------- #
def test_no_result_does_not_fabricate_candidate() -> None:
    provider = _provider(_FakeTgosAdapter(item=None, last_error=""))
    result = provider.resolve(_address_input())
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.NO_MATCH
    assert result.candidates == ()


def test_non_address_input_is_unsupported() -> None:
    provider = _provider(_FakeTgosAdapter(item=_rooftop_item()))
    coordinate_input = normalize_resolution_input(
        ResolutionInputType.COORDINATES,
        {"latitude": 25.0, "longitude": 121.0, "crs": "EPSG:4326"},
    )
    result = provider.resolve(coordinate_input)
    _validate_provider_result(result)
    assert result.status is ResolutionAttemptStatus.UNSUPPORTED
    assert result.candidates == ()
    # The adapter was never consulted for an unsupported input.
    assert provider._adapter.calls == []  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# 9. Provenance / retrieved_at preserved.
# --------------------------------------------------------------------------- #
def test_provenance_and_retrieved_at_preserved() -> None:
    provider = _provider(_FakeTgosAdapter(item=_rooftop_item()))
    result = provider.resolve(_address_input())
    assert result.retrieved_at == NOW
    candidate = result.candidates[0]
    assert candidate.retrieved_at == NOW
    provenance = candidate.normalized_identity["provenance"]
    assert provenance["provider"] == "tgos"
    assert provenance["declared_source_id"] == "tgos-address"
    assert result.coverage["provenance"]["declared_source_id"] == "tgos-address"


# --------------------------------------------------------------------------- #
# 10. License metadata is explicit (owner_review_required, not implied-allowed).
# --------------------------------------------------------------------------- #
def test_license_metadata_is_explicit() -> None:
    from services.vnext.tgos_observation_provider import _TGOS_LICENSE

    assert _TGOS_LICENSE["status"] == "owner_review_required"
    assert _TGOS_LICENSE["commercial_use"] == "owner_review_required"
    assert _TGOS_LICENSE["redistribution"] == "owner_review_required"
    assert _TGOS_LICENSE["source"] == "tgos-address"


def test_license_metadata_is_attached_to_result_candidate() -> None:
    # The license must live on engine-visible data, not only as a module const.
    provider = _provider(_FakeTgosAdapter(item=_rooftop_item()))
    result = provider.resolve(_address_input())
    candidate = result.candidates[0]
    license_on_candidate = candidate.normalized_identity["provenance"]["license"]
    license_on_coverage = candidate.coverage["provenance"]["license"]
    for lic in (license_on_candidate, license_on_coverage):
        assert lic["status"] == "owner_review_required"
        assert lic["commercial_use"] == "owner_review_required"
        assert lic["redistribution"] == "owner_review_required"
        assert lic["source"] == "tgos-address"


@pytest.mark.parametrize(
    ("item", "last_error", "expected_status"),
    [
        (None, "", ResolutionAttemptStatus.NO_MATCH),
        (None, "provider unavailable", ResolutionAttemptStatus.UNAVAILABLE),
    ],
)
def test_license_metadata_is_attached_to_engine_visible_empty_attempt(
    item: dict[str, Any] | None,
    last_error: str,
    expected_status: ResolutionAttemptStatus,
) -> None:
    provider = _provider(_FakeTgosAdapter(item=item, last_error=last_error))
    draft = IdentityResolutionEngine((provider,), clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市信義區信義路五段7號"},
    )

    assert draft.attempts[0].status is expected_status
    assert draft.attempts[0].coverage["provenance"]["license"]["status"] == "owner_review_required"
    assert draft.candidates == ()


# --------------------------------------------------------------------------- #
# 11. Multiple/conflicting observations reach the engine as candidates/
#     conflicts, not auto-merge.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _EngineProvider:
    """A TEST provider that feeds pre-built observations through the engine.

    It reuses the TGOS provider's translated candidate but presents the
    engine-facing appendable TEST source, exactly as the real provider does.
    """

    result: ProviderResolutionResult
    provider_id: str = "tgos-address-observation"
    strategy_id: str = "tgos-address-observation-v1"
    source_id: str = OBSERVATION_SOURCE_ID
    source_environment: SourceEnvironment = SourceEnvironment.TEST

    def resolve(self, _resolution_input):
        return self.result


def _observation(observation_id: str, key: str) -> ProviderCandidateObservation:
    from services.vnext.identity_resolution import CandidateRankingFactors

    return ProviderCandidateObservation(
        observation_id=observation_id,
        candidate_type=IdentityCandidateType.ADDRESS,
        normalized_key=key,
        normalized_identity={"formatted_address": key},
        display_identity=key,
        source_record_id=observation_id,
        retrieved_at=NOW,
        ranking_factors=CandidateRankingFactors(
            source_reliability=0.7,
            match_quality=1.0,
            identifier_agreement=0.0,
            geometry_agreement=1.0,
            temporal_validity=0.0,
            coverage_quality=1.0,
        ),
        coverage_status=CoverageStatus.KNOWN,
        coverage={"subject_scope": "address"},
    )


def test_multiple_conflicting_observations_reach_engine_as_conflicts() -> None:
    left = _observation("tgos:a", "台北市A路1號")
    right = _observation("tgos:b", "台北市B路2號")
    conflict = ProviderConflictObservation(
        left_observation_id="tgos:a",
        right_observation_id="tgos:b",
        conflict_type=IdentityConflictType.PROVIDER_DISAGREEMENT,
        severity=IdentityConflictSeverity.BLOCKING,
        source_basis={"provider": "tgos"},
        conflict_basis={"reason": "two_distinct_addresses"},
    )
    result = ProviderResolutionResult(
        status=ResolutionAttemptStatus.AVAILABLE,
        started_at=NOW,
        completed_at=NOW,
        retrieved_at=NOW,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
        candidates=(left, right),
        conflicts=(conflict,),
    )
    draft = IdentityResolutionEngine(
        (_EngineProvider(result),), clock=lambda: NOW
    ).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市"},
    )
    # Engine, not the provider, owns conflict state and ranking.
    assert draft.status is ResolutionStatus.AMBIGUOUS
    assert len(draft.conflicts) == 1
    # Conflicting candidates are marked conflicting, never merged away.
    assert len(draft.candidates) == 2
    assert all(
        candidate.candidate_status is IdentityCandidateStatus.CONFLICTING
        for candidate in draft.candidates
    )


# --------------------------------------------------------------------------- #
# 12 & 13. Engine output still requires human confirmation; no materialization.
# --------------------------------------------------------------------------- #
def test_engine_output_requires_human_confirmation_and_no_materialization() -> None:
    observation = _observation("tgos:single", "台北市信義區信義路五段7號")
    result = ProviderResolutionResult(
        status=ResolutionAttemptStatus.AVAILABLE,
        started_at=NOW,
        completed_at=NOW,
        retrieved_at=NOW,
        coverage_status=CoverageStatus.KNOWN,
        coverage={"scope": "fixture"},
        candidates=(observation,),
    )
    draft = IdentityResolutionEngine(
        (_EngineProvider(result),), clock=lambda: NOW
    ).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市信義區信義路五段7號"},
    )
    assert draft.needs_human_confirmation is True
    for candidate in draft.candidates:
        assert candidate.needs_human_confirmation is True
        # A candidate is never a confirmed PropertyEntity.
        assert candidate.candidate_status in {
            IdentityCandidateStatus.PLAUSIBLE,
            IdentityCandidateStatus.INSUFFICIENT,
            IdentityCandidateStatus.CONFLICTING,
        }
    # The draft carries no confirmed property entity id / materialization hook.
    assert not hasattr(draft, "confirmed_property_entity_id")


# --------------------------------------------------------------------------- #
# Reused-adapter proof: no HTTP duplication; the provider delegates to search().
# --------------------------------------------------------------------------- #
def test_provider_delegates_to_injected_adapter() -> None:
    adapter = _FakeTgosAdapter(item=_rooftop_item())
    provider = _provider(adapter)
    provider.resolve(_address_input())
    assert adapter.calls == ["台北市信義區信義路五段7號"]



# --------------------------------------------------------------------------- #
# P1 HARDENING
# --------------------------------------------------------------------------- #
class _IncrementingClock:
    """Aware clock that advances one second each call (proves timestamp use)."""

    def __init__(self, start: datetime) -> None:
        self._current = start

    def __call__(self) -> datetime:
        value = self._current
        self._current = self._current + timedelta(seconds=1)
        return value


def test_real_provider_reaches_engine_with_license_and_provenance() -> None:
    # The REAL TgosIdentityObservationProvider is passed to the engine. No
    # _EngineProvider fake is used here; this proves the seam-to-engine path.
    provider = TgosIdentityObservationProvider(
        _FakeTgosAdapter(item=_rooftop_item()), clock=lambda: NOW
    )
    draft = IdentityResolutionEngine((provider,), clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市信義區信義路五段7號"},
    )
    # Resolution succeeds with exactly one engine-validated, ranked candidate.
    assert draft.status is ResolutionStatus.CANDIDATES_FOUND
    assert len(draft.candidates) == 1
    candidate = draft.candidates[0]
    assert candidate.rank == 1
    # Engine stamped the appendable TEST source; provenance still names TGOS.
    assert candidate.source_id == "vnext-test"
    assert candidate.source_type is SourceType.TEST
    assert candidate.source_environment is SourceEnvironment.TEST
    assert draft.attempts[0].source_id == "vnext-test"
    assert draft.attempts[0].source_environment is SourceEnvironment.TEST
    provenance = candidate.normalized_identity["provenance"]
    assert provenance["provider"] == "tgos"
    assert provenance["declared_source_id"] == "tgos-address"
    # License survives all the way into the ranked candidate.
    assert provenance["license"]["status"] == "owner_review_required"
    assert candidate.coverage["provenance"]["license"]["source"] == "tgos-address"
    # Human confirmation still required; nothing confirmed/materialized.
    assert draft.needs_human_confirmation is True
    assert candidate.needs_human_confirmation is True
    assert candidate.candidate_status is IdentityCandidateStatus.PLAUSIBLE
    assert not hasattr(draft, "confirmed_property_entity_id")
    assert not hasattr(draft, "property_entity_id")
    assert candidate.possible_existing_property_entity_id is None


def test_retrieved_at_is_one_coherent_instant_under_incrementing_clock() -> None:
    clock = _IncrementingClock(NOW)
    provider = TgosIdentityObservationProvider(
        _FakeTgosAdapter(item=_rooftop_item()), clock=clock
    )
    result = provider.resolve(_address_input())
    _validate_provider_result(result)
    candidate = result.candidates[0]
    # Result and candidate must reference the SAME observation instant.
    assert result.retrieved_at == candidate.retrieved_at
    # And that instant is the completion tick, strictly after started_at.
    assert result.started_at < result.retrieved_at == result.completed_at


def test_observation_id_prefers_source_record_id() -> None:
    provider = _provider(_FakeTgosAdapter(item=_rooftop_item()))
    result = provider.resolve(_address_input())
    candidate = result.candidates[0]
    assert candidate.source_record_id == "tgos-台北市信義區信義路五段7號"
    assert candidate.observation_id == "tgos:tgos-台北市信義區信義路五段7號"


def test_observation_id_falls_back_to_deterministic_hash() -> None:
    item = _rooftop_item()
    item.pop("id")  # no source_record_id available
    provider = _provider(_FakeTgosAdapter(item=item))
    first = provider.resolve(_address_input()).candidates[0]
    second = provider.resolve(_address_input()).candidates[0]
    assert first.source_record_id is None
    assert first.observation_id.startswith("tgos:sha256:")
    assert len(first.observation_id) <= 120
    # Deterministic: same observation -> same id.
    assert first.observation_id == second.observation_id


def test_observation_id_avoids_long_prefix_collision() -> None:
    # Two distinct long addresses sharing the first 120+ characters must not
    # collapse to the same observation id.
    shared_prefix = "台北市信義區信義路五段" + ("一" * 130)
    item_a = _rooftop_item()
    item_b = _rooftop_item()
    item_a.pop("id")
    item_b.pop("id")
    item_a["formatted_address"] = shared_prefix + "甲號"
    item_b["formatted_address"] = shared_prefix + "乙號"

    id_a = _provider(_FakeTgosAdapter(item=item_a)).resolve(_address_input()).candidates[0].observation_id
    id_b = _provider(_FakeTgosAdapter(item=item_b)).resolve(_address_input()).candidates[0].observation_id
    assert id_a != id_b
    assert len(id_a) <= 120 and len(id_b) <= 120


def test_observation_id_ignores_query_for_same_source_observation() -> None:
    item = _rooftop_item()
    item.pop("id")
    provider = _provider(_FakeTgosAdapter(item=item))
    first = provider.resolve(_address_input()).candidates[0]
    alternate_query = normalize_resolution_input(
        ResolutionInputType.ADDRESS,
        {"address": "台北市 信義區 信義路五段7號"},
    )
    second = provider.resolve(alternate_query).candidates[0]

    assert first.normalized_identity["provenance"]["query"] != second.normalized_identity["provenance"]["query"]
    assert first.observation_id == second.observation_id


def test_long_record_ids_with_shared_prefix_remain_distinct_and_engine_valid() -> None:
    prefix = "tgos-" + ("一" * 250)
    first_item = _rooftop_item()
    second_item = _rooftop_item()
    first_item["id"] = prefix + "甲"
    second_item["id"] = prefix + "乙"
    first_provider = _provider(_FakeTgosAdapter(item=first_item))
    second_provider = _provider(_FakeTgosAdapter(item=second_item))

    first = IdentityResolutionEngine((first_provider,), clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市信義區信義路五段7號"},
    )
    second = IdentityResolutionEngine((second_provider,), clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "台北市信義區信義路五段7號"},
    )

    assert first.status is second.status is ResolutionStatus.CANDIDATES_FOUND
    assert first.candidates[0].source_record_id is None
    assert second.candidates[0].source_record_id is None
    assert first.candidates[0].observation_id != second.candidates[0].observation_id


def test_observation_id_changes_with_source_location_when_record_id_absent() -> None:
    first_item = _rooftop_item()
    second_item = _rooftop_item()
    first_item.pop("id")
    second_item.pop("id")
    second_item["center"] = {"lat": 25.034, "lng": 121.5645}

    first_id = _provider(_FakeTgosAdapter(item=first_item)).resolve(_address_input()).candidates[0].observation_id
    second_id = _provider(_FakeTgosAdapter(item=second_item)).resolve(_address_input()).candidates[0].observation_id
    assert first_id != second_id


def test_oversized_source_address_fails_closed_before_engine_validation() -> None:
    item = _rooftop_item()
    item["formatted_address"] = "甲" * 513
    provider = _provider(_FakeTgosAdapter(item=item))

    result = provider.resolve(_address_input())
    assert result.status is ResolutionAttemptStatus.ERROR
    assert result.error_category is ResolutionErrorCategory.INVALID_RESPONSE
    assert result.candidates == ()


def test_nonfinite_source_coordinates_fail_closed() -> None:
    item = _rooftop_item()
    item["center"] = {"lat": float("nan"), "lng": 121.5645}
    provider = _provider(_FakeTgosAdapter(item=item))

    result = provider.resolve(_address_input())
    assert result.status is ResolutionAttemptStatus.ERROR
    assert result.error_category is ResolutionErrorCategory.INVALID_RESPONSE
    assert result.candidates == ()


def test_normalized_key_is_test_seam_only_not_production_identity_truth() -> None:
    # REQUIREMENT (P1 #5): the TEST-only seam keeps the current normalized_key
    # for compatibility, but it is the raw TGOS DISPLAY address only. It is NOT
    # a production identity key: no NFKC / full-width-half-width folding, no
    # Taiwan token canonicalization, no whitespace normalization. This test
    # pins that TEST-seam behavior so a future reader cannot mistake it for
    # canonical identity truth.
    address = "台北市信義區信義路五段7號"
    provider = _provider(_FakeTgosAdapter(item=_rooftop_item()))
    candidate = provider.resolve(_address_input()).candidates[0]

    # It is exactly the prefixed raw display address, not a canonicalized key.
    assert candidate.normalized_key == f"tgos-address:{address}"
    # The stored form is the raw display string, unchanged (no folding applied).
    assert candidate.normalized_key.endswith(address)

    # A full-width digit variant of the SAME logical address does NOT fold to
    # the same key. This proves the seam does not perform production identity
    # normalization and must not be treated as identity truth.
    fullwidth_item = _rooftop_item()
    fullwidth_item["formatted_address"] = "台北市信義區信義路五段７號"  # full-width 7
    fullwidth_key = (
        _provider(_FakeTgosAdapter(item=fullwidth_item))
        .resolve(_address_input())
        .candidates[0]
        .normalized_key
    )
    assert fullwidth_key != candidate.normalized_key
