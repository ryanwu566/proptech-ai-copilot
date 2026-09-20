"""Offline Property Identity tests for NLSC CAD observation candidates."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from services.vnext.errors import ErrorCode, VNextError
from services.vnext.identity_resolution import (
    IdentityCandidateStatus,
    IdentityCandidateType,
    IdentityResolutionEngine,
    ResolutionAttemptStatus,
    ResolutionErrorCategory,
    ResolutionInputType,
    ResolutionStatus,
    _source_definition,
    _validate_provider_result,
    normalize_resolution_input,
)
from services.vnext.identity_resolution_service import (
    IdentityResolutionApplicationService,
)
from services.vnext.property_graph import (
    CoverageStatus,
    DATA_SOURCE_REGISTRY,
    SourceEnvironment,
    SourceType,
)


NOW = datetime(2026, 9, 19, 8, 30, tzinfo=timezone.utc)
RETRIEVED_AT = "2026-09-19T08:30:00+00:00"


def _module():
    return importlib.import_module("services.vnext.nlsc_cad_observation_provider")


def _cad_009_result() -> dict[str, object]:
    return {
        "status": "available",
        "source": "NLSC",
        "service_code": "CAD_009",
        "retrieved_at": RETRIEVED_AT,
        "coverage": "unknown",
        "source_record_id": None,
        "raw_confidence": None,
        "observations": [
            {
                "content": "臺中市南屯區黎明里００１鄰黎明路二段４９７號",
                "location": "120.634421,24.153412",
                "office_code": "BC",
                "section_code": "2013",
                "land_number": "03420000",
            },
            {
                "content": "臺中市南屯區黎明里黎明路二段４９７號",
                "location": "120.634500,24.153500",
                "office_code": "BC",
                "section_code": "2013",
                "land_number": "03430000",
            },
        ],
        "error_code": None,
    }


def _cad_001_result() -> dict[str, object]:
    return {
        "status": "available",
        "source": "NLSC",
        "service_code": "CAD_001",
        "retrieved_at": RETRIEVED_AT,
        "coverage": "unknown",
        "source_record_id": None,
        "raw_confidence": None,
        "observations": [
            {
                "representative_point": {
                    "x": 120.683552,
                    "y": 24.142313,
                    "crs": "EPSG:4326",
                },
                "bounds": {
                    "lower_left": {"x": 120.683471, "y": 24.142235},
                    "upper_right": {"x": 120.683633, "y": 24.142389},
                    "crs": "EPSG:4326",
                },
            }
        ],
        "error_code": None,
    }


@dataclass
class _FakeCadAdapter:
    cad_009_result: dict[str, object] = field(default_factory=_cad_009_result)
    cad_001_result: dict[str, object] = field(default_factory=_cad_001_result)
    available: bool = True
    calls: list[tuple[object, ...]] = field(default_factory=list)

    def cad_009_address_query_land(self, query: str, max_results: int = 1):
        self.calls.append(("CAD_009", query, max_results))
        return self.cad_009_result

    def cad_001_cadas_map_position(
        self,
        county_code: str,
        section_code: str,
        land_number: str,
        crs: str = "4326",
    ):
        self.calls.append(
            ("CAD_001", county_code, section_code, land_number, crs)
        )
        return self.cad_001_result


def _address_input():
    return normalize_resolution_input(
        ResolutionInputType.ADDRESS,
        {"address": "臺中市南屯區黎明路二段497號"},
    )


def _lot_input(*, subsection: str | None = None):
    value: dict[str, object] = {
        "jurisdiction": "B",
        "section": "0012",
        "lot_number": "00010000",
    }
    if subsection is not None:
        value["subsection"] = subsection
    return normalize_resolution_input(ResolutionInputType.LOT_NUMBER, value)


def test_cad_009_multiple_matches_remain_multiple_unknown_candidates() -> None:
    module = _module()
    adapter = _FakeCadAdapter()
    provider = module.NlscCad009ParcelObservationProvider(
        adapter,
        clock=lambda: NOW,
    )

    result = provider.resolve(_address_input())
    _validate_provider_result(result)

    assert result.status is ResolutionAttemptStatus.LIMITED
    assert result.coverage_status is CoverageStatus.UNKNOWN
    assert len(result.candidates) == 2
    assert {candidate.candidate_type for candidate in result.candidates} == {
        IdentityCandidateType.PARCEL
    }
    assert {candidate.normalized_identity["land_number"] for candidate in result.candidates} == {
        "03420000",
        "03430000",
    }
    assert all(candidate.source_record_id is None for candidate in result.candidates)
    assert adapter.calls == [
        ("CAD_009", "臺中市南屯區黎明路二段497號", 8)
    ]


def test_cad_009_engine_keeps_all_candidates_unverified_without_winner() -> None:
    module = _module()
    provider = module.NlscCad009ParcelObservationProvider(
        _FakeCadAdapter(),
        clock=lambda: NOW,
    )
    draft = IdentityResolutionEngine((provider,), clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.ADDRESS,
        raw_input={"address": "臺中市南屯區黎明路二段497號"},
    )

    assert draft.status is ResolutionStatus.AMBIGUOUS
    assert len(draft.candidates) == 2
    assert draft.needs_human_confirmation is True
    assert all(candidate.needs_human_confirmation for candidate in draft.candidates)
    assert all(
        candidate.candidate_status is IdentityCandidateStatus.INSUFFICIENT
        for candidate in draft.candidates
    )
    assert all(candidate.source_id == "vnext-test" for candidate in draft.candidates)
    assert all(candidate.source_type is SourceType.TEST for candidate in draft.candidates)
    assert all(candidate.confidence == 0.0 for candidate in draft.candidates)
    assert not hasattr(draft, "property_entity_id")
    assert not hasattr(draft, "selected_candidate_id")


def test_cad_009_provenance_is_exact_and_does_not_fabricate_source_fields() -> None:
    module = _module()
    result = module.NlscCad009ParcelObservationProvider(
        _FakeCadAdapter(),
        clock=lambda: NOW,
    ).resolve(_address_input())

    for candidate in result.candidates:
        provenance = candidate.normalized_identity["provenance"]
        assert provenance == {
            "source": "NLSC",
            "declared_source_id": "nlsc-cadastral",
            "service_code": "CAD_009",
            "retrieved_at": RETRIEVED_AT,
            "coverage": "unknown",
            "source_record_id": None,
            "raw_confidence": None,
            "identity_status": "proposed_unverified",
            "human_confirmation_required": True,
        }
        assert candidate.retrieved_at == NOW
        assert candidate.coverage["provenance"] == provenance


def test_cad_009_never_inferrs_or_calls_cad_001() -> None:
    module = _module()
    adapter = _FakeCadAdapter()
    provider = module.NlscCad009ParcelObservationProvider(
        adapter,
        clock=lambda: NOW,
    )

    provider.resolve(_address_input())

    assert adapter.calls == [
        ("CAD_009", "臺中市南屯區黎明路二段497號", 8)
    ]


def test_cad_001_requires_explicit_trusted_query_before_egress() -> None:
    module = _module()
    adapter = _FakeCadAdapter()
    provider = module.NlscCad001GeoreferenceObservationProvider(
        adapter,
        trusted_query=None,
        clock=lambda: NOW,
    )

    result = provider.resolve(_lot_input())
    _validate_provider_result(result)

    assert result.status is ResolutionAttemptStatus.UNSUPPORTED
    assert result.error_category is ResolutionErrorCategory.UNSUPPORTED_INPUT
    assert result.candidates == ()
    assert adapter.calls == []


def test_cad_001_runs_only_with_matching_explicit_codes_and_returns_georeference() -> None:
    module = _module()
    adapter = _FakeCadAdapter()
    query = module.TrustedCad001Query(
        county_code="B",
        section_code="0012",
        land_number="00010000",
        crs="4326",
    )
    provider = module.NlscCad001GeoreferenceObservationProvider(
        adapter,
        trusted_query=query,
        clock=lambda: NOW,
    )

    result = provider.resolve(_lot_input())
    _validate_provider_result(result)

    assert result.status is ResolutionAttemptStatus.LIMITED
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.candidate_type is IdentityCandidateType.GEO_REFERENCE
    assert candidate.normalized_identity["kind"] == "georeference_observation"
    assert candidate.normalized_identity["identity_effect"] == "does_not_confirm_parcel_identity"
    assert candidate.normalized_identity["parcel_query"] == {
        "county_code": "B",
        "section_code": "0012",
        "land_number": "00010000",
        "crs": "4326",
    }
    assert candidate.source_record_id is None
    assert candidate.normalized_identity["provenance"]["raw_confidence"] is None
    assert adapter.calls == [("CAD_001", "B", "0012", "00010000", "4326")]


@pytest.mark.parametrize(
    "resolution_input",
    [
        normalize_resolution_input(
            ResolutionInputType.LOT_NUMBER,
            {"jurisdiction": "A", "section": "0012", "lot_number": "00010000"},
        ),
        _lot_input(subsection="subsection-must-not-be-inferred"),
        _address_input(),
    ],
)
def test_cad_001_rejects_mismatched_or_non_exact_context_without_egress(
    resolution_input: Any,
) -> None:
    module = _module()
    adapter = _FakeCadAdapter()
    provider = module.NlscCad001GeoreferenceObservationProvider(
        adapter,
        trusted_query=module.TrustedCad001Query("B", "0012", "00010000"),
        clock=lambda: NOW,
    )

    result = provider.resolve(resolution_input)
    _validate_provider_result(result)

    assert result.status is ResolutionAttemptStatus.UNSUPPORTED
    assert adapter.calls == []


def test_cad_001_position_reaches_engine_as_insufficient_evidence_not_confirmation() -> None:
    module = _module()
    provider = module.NlscCad001GeoreferenceObservationProvider(
        _FakeCadAdapter(),
        trusted_query=module.TrustedCad001Query("B", "0012", "00010000"),
        clock=lambda: NOW,
    )
    draft = IdentityResolutionEngine((provider,), clock=lambda: NOW).resolve(
        input_type=ResolutionInputType.LOT_NUMBER,
        raw_input={
            "jurisdiction": "B",
            "section": "0012",
            "lot_number": "00010000",
        },
    )

    assert draft.status is ResolutionStatus.PARTIALLY_RESOLVED
    assert len(draft.candidates) == 1
    candidate = draft.candidates[0]
    assert candidate.candidate_type is IdentityCandidateType.GEO_REFERENCE
    assert candidate.candidate_status is IdentityCandidateStatus.INSUFFICIENT
    assert candidate.needs_human_confirmation is True
    assert candidate.possible_existing_property_entity_id is None
    assert not hasattr(draft, "confirmed_property_entity_id")


def test_malformed_adapter_result_fails_closed_without_candidate() -> None:
    module = _module()
    malformed = _cad_009_result()
    malformed["source"] = "not-NLSC"
    provider = module.NlscCad009ParcelObservationProvider(
        _FakeCadAdapter(cad_009_result=malformed),
        clock=lambda: NOW,
    )

    result = provider.resolve(_address_input())
    _validate_provider_result(result)

    assert result.status is ResolutionAttemptStatus.ERROR
    assert result.error_category is ResolutionErrorCategory.INVALID_RESPONSE
    assert result.candidates == ()
    assert "not-NLSC" not in str(result.coverage)


def test_registry_and_provider_keep_nlsc_production_acceptance_disabled() -> None:
    module = _module()
    definition = DATA_SOURCE_REGISTRY["nlsc-cadastral"]
    provider = module.NlscCad009ParcelObservationProvider(
        _FakeCadAdapter(),
        clock=lambda: NOW,
    )

    assert definition.source_type is SourceType.OFFICIAL
    assert definition.readiness == "metadata_only"
    assert definition.request_appendable is False
    assert provider.declared_source_id == "nlsc-cadastral"
    assert provider.source_id == "vnext-test"
    assert provider.source_environment is SourceEnvironment.TEST


def test_production_application_gate_rejects_the_test_scoped_nlsc_provider() -> None:
    module = _module()
    provider = module.NlscCad009ParcelObservationProvider(
        _FakeCadAdapter(),
        clock=lambda: NOW,
    )
    service = IdentityResolutionApplicationService(
        authorizer=object(),  # type: ignore[arg-type]
        engine=IdentityResolutionEngine((provider,), clock=lambda: NOW),
        resolution_repository=object(),  # type: ignore[arg-type]
        idempotency_repository=object(),  # type: ignore[arg-type]
        case_repository=object(),  # type: ignore[arg-type]
        runtime_environment="production",
    )

    with pytest.raises(VNextError) as excinfo:
        service._verify_provider_boundary()

    assert excinfo.value.code is ErrorCode.PROVIDER_UNAVAILABLE


def test_engine_rejects_nlsc_cadastral_as_appendable_authority() -> None:
    @dataclass
    class _MisdeclaredProvider:
        provider_id: str = "nlsc-cad-observation"
        strategy_id: str = "nlsc-cad-observation-v1"
        source_id: str = "nlsc-cadastral"
        source_environment: SourceEnvironment = SourceEnvironment.TEST

    with pytest.raises(VNextError) as excinfo:
        _source_definition(_MisdeclaredProvider())

    assert excinfo.value.code is ErrorCode.PERMISSION_DENIED
