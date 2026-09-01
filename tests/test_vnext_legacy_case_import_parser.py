from __future__ import annotations

import json

import pytest

from services.vnext.errors import ErrorCode, VNextError
from services.vnext.legacy_case_import import LegacySavedCaseV1Parser


def saved_case_v1() -> dict[str, object]:
    return {
        "id": "browser-case-123",
        "title": "Synthetic legacy investigation",
        "createdAt": "2025-01-02T03:04:05Z",
        "updatedAt": "2025-02-03T04:05:06Z",
        "version": 1,
        "workflowMode": "buying_wizard",
        "activeWizardStep": "report",
        "progress": 92,
        "inputSummary": {
            "city": "Synthetic City",
            "district": "Test District",
            "road": "Example Road",
            "budgetMin": None,
            "budgetMax": 2500,
            "propertyPrice": 2200,
            "areaPing": 32.5,
        },
        "data": {
            "inputs": {
                "city": "Synthetic City",
                "district": "Test District",
                "road": "Example Road",
                "building_type": "apartment",
                "area_ping": 32.5,
                "building_age_years": 8,
                "floor": 6,
            },
            "propertySearch": {
                "summary": {
                    "matched_count": 4,
                    "city_count": 1,
                    "district_count": 1,
                    "road_count": 1,
                    "budget_min": None,
                    "budget_max": 2500,
                    "period_min": "2024-01",
                    "period_max": "2024-12",
                    "data_source_label": "synthetic compact summary",
                    "message": "reference only",
                    "disclaimer": "not current",
                },
                "matched_transactions": [{"raw_price": 999, "token": "do-not-store"}],
            },
            "valuationEvidence": {
                "status": "partial",
                "source": "official_valuation",
                "label": "legacy summary",
                "value": "2200",
                "range": "2100-2300",
                "confidence": "medium",
                "reason": "historical snapshot",
                "transferable": False,
            },
            "valuation": {
                "source": "postgres",
                "data_composition": "official_limited",
                "estimate_data_composition": "official_limited",
                "estimate_source_label": "synthetic",
                "candidate_pool_size": 4,
                "estimate_level": "district",
                "confidence_reason": "limited synthetic fixture",
                "estimate_total_price": 2200,
                "estimate_unit_price_per_ping": 67.7,
                "confidence": "medium",
                "confidence_score": 65,
                "comparables": [{"address": "raw comparable must be excluded"}],
                "source_details": {"provider_payload": "raw-provider-body"},
            },
            "trend": {
                "source": "official_plvr_opendata",
                "data_scope": "district",
                "period_min": "2024-01",
                "period_max": "2024-12",
                "sample_count": 8,
                "recent_median_unit_price": 66,
                "trend_annualized_rate": 0.03,
                "volatility": None,
                "confidence_level": "low",
                "confidence_reason": "small sample",
            },
            "loan": {
                "property_price_wan": 2200,
                "down_payment_ratio": 0.2,
                "down_payment_wan": 440,
                "loan_amount_wan": 1760,
                "annual_interest_rate": 2.2,
                "loan_years": 30,
                "grace_period_years": 2,
                "monthly_income_wan": None,
                "monthly_payment": 65000,
                "total_payment": 23_400_000,
                "total_interest": 5_800_000,
                "income_burden_ratio": None,
                "affordability_level": "unknown",
                "sensitivity": [{"raw": "excluded"}],
            },
            "holdingCost": {
                "property_price_wan": 2200,
                "loan_monthly_payment": 65000,
                "monthly_management_fee": 3200,
                "monthly_repair_reserve": 1500,
                "monthly_tax_estimate": 1200,
                "monthly_insurance": 500,
                "monthly_total_holding_cost": 71400,
                "annual_total_holding_cost": 856800,
                "income_burden_ratio": None,
                "affordability_level": "unknown",
            },
            "locationInsight": {
                "radius_m": 1000,
                "location_score": 72,
                "strengths": ["synthetic transit summary"],
                "weaknesses": ["freshness unknown"],
                "data_quality": {
                    "status": "limited",
                    "missing_sources": ["current source"],
                    "warnings": ["synthetic only"],
                },
                "resolved_location": {"latitude": 25.0, "longitude": 121.5},
                "nearest_pois": [{"raw": "excluded"}],
            },
            "terrainReference": {
                "schema_version": 1,
                "kind": "terrain_reference",
                "status": "partial",
                "summary": "legacy reference",
                "notice": "not a current safety conclusion",
                "layers": [
                    {
                        "layer_id": "synthetic-flood",
                        "display_name": "Synthetic flood layer",
                        "state": "no_match",
                        "source_name": "synthetic fixture",
                        "coverage_status": "unknown",
                        "caveat": "no_match is not safety evidence",
                        "source_url": "https://excluded.invalid/private",
                    }
                ],
            },
            "riskSummary": {
                "overallSignal": "green",
                "overallLabel": "legacy presentation only",
                "overallScore": 90,
                "decisionSuggestion": "must not become authoritative",
                "dataConfidence": "unknown",
                "missingChecks": ["current terrain"],
                "nextActions": ["revalidate"],
                "referenceNotes": ["presentation artifact"],
            },
            "taxOracle": {
                "eligibility_status": "manual_review",
                "risk_score": 3,
                "signal_color": "yellow",
                "hard_fail_rules": [],
                "manual_review_rules": ["fixture.rule"],
                "missing_docs": ["fixture-document"],
                "reminder_timeline": [],
                "tax_output_boundary": "preliminary_screening_only",
            },
            "reportCompleted": True,
            "unsupportedFutureSection": {"secret": "not persisted"},
        },
        "futureTopLevel": {"provider_payload": "not persisted"},
    }


def test_complete_saved_case_is_allowlisted_without_raw_payload_retention() -> None:
    parsed = LegacySavedCaseV1Parser().parse(saved_case_v1())

    assert parsed.title == "Synthetic legacy investigation"
    assert "address_input" in parsed.accepted_field_classes
    assert "terrain_reference" in parsed.accepted_field_classes
    assert "raw_provider_payload" in parsed.dropped_field_classes
    assert "raw_comparable_rows" in parsed.dropped_field_classes
    assert "exact_coordinates" in parsed.dropped_field_classes
    assert "unsupported_fields_dropped" in parsed.warnings
    assert "terrain_reference_only" in parsed.warnings
    assert "risk_presentation_not_authoritative" in parsed.warnings
    persisted = json.dumps([item.value for item in parsed.evidence], sort_keys=True)
    for forbidden in (
        "do-not-store",
        "raw-provider-body",
        "raw comparable must be excluded",
        "excluded.invalid",
        "latitude",
        "longitude",
        "unsupportedFutureSection",
        "futureTopLevel",
    ):
        assert forbidden not in persisted


def test_minimal_partial_case_preserves_missing_as_missing() -> None:
    parsed = LegacySavedCaseV1Parser().parse(
        {"title": "Minimal synthetic case", "version": 1, "data": {}}
    )

    assert parsed.accepted_field_classes == ("title",)
    assert parsed.evidence == ()
    assert "missing_address" in parsed.warnings
    assert "missing_valuation" in parsed.warnings
    assert "0" not in json.dumps([item.value for item in parsed.evidence])


@pytest.mark.parametrize("version", [None, 0, 2, True, "1"])
def test_only_exact_saved_case_version_one_is_supported(version: object) -> None:
    with pytest.raises(VNextError) as error:
        LegacySavedCaseV1Parser().parse({"title": "Fixture", "version": version})

    assert error.value.code is ErrorCode.UNSUPPORTED_INPUT


@pytest.mark.parametrize(
    ("terrain", "expected_status", "has_value", "warning"),
    [
        ({"schema_version": 1, "kind": "terrain_reference", "status": "unknown", "layers": []}, "unknown", False, None),
        ({"schema_version": 1, "kind": "terrain_reference", "status": "unavailable", "layers": []}, "unavailable", False, None),
        ({"schema_version": 1, "kind": "terrain_reference", "status": "partial", "layers": []}, "limited", True, None),
        ({"schema_version": 1, "kind": "terrain_reference", "status": "limited", "layers": []}, "limited", True, None),
        ({"schema_version": 1, "kind": "terrain_reference", "status": "no_match", "layers": []}, "limited", True, None),
        ({"schema_version": 1, "kind": "terrain_reference", "status": "available", "layers": []}, "limited", True, "terrain_safe_conclusion_blocked"),
    ],
)
def test_terrain_states_remain_conservative(
    terrain: dict[str, object], expected_status: str, has_value: bool, warning: str | None
) -> None:
    parsed = LegacySavedCaseV1Parser().parse(
        {"title": "Terrain fixture", "version": 1, "data": {"terrainReference": terrain}}
    )
    evidence = next(item for item in parsed.evidence if item.fact_type.endswith("terrain_reference"))

    assert evidence.evidence_status == expected_status
    assert (evidence.value is not None) is has_value
    assert "terrain_reference_only" in parsed.warnings
    if warning:
        assert warning in parsed.warnings
    assert evidence.evidence_status != "available"


def test_legacy_low_terrain_presentation_never_becomes_safe() -> None:
    parsed = LegacySavedCaseV1Parser().parse(
        {
            "title": "Legacy low terrain fixture",
            "version": 1,
            "data": {
                "terrainRisk": {
                    "overall": {"level": "low", "label": "green", "summary": "safe"},
                    "data_quality": {"status": "good", "warnings": []},
                    "resolved_location": {"latitude": 25.0, "longitude": 121.5},
                }
            },
        }
    )
    evidence = next(item for item in parsed.evidence if item.fact_type.endswith("terrain_reference"))

    assert evidence.evidence_status == "limited"
    assert evidence.value == {
        "legacy_level": "low",
        "data_quality_status": "good",
        "conclusion": "reference_only",
    }
    assert "terrain_safe_conclusion_blocked" in parsed.warnings


def test_corrupt_and_oversized_optional_sections_are_dropped_with_bounded_codes() -> None:
    parsed = LegacySavedCaseV1Parser().parse(
        {
            "title": "Bounded fixture",
            "version": 1,
            "data": {
                "loan": "corrupt",
                "marketInsight": {"summary": "x" * 3000},
                "provider_payload": {"stack_trace": "sensitive"},
            },
        }
    )

    assert "corrupt_optional_section" in parsed.dropped_field_classes
    assert "oversized_fields" in parsed.dropped_field_classes
    assert "raw_provider_payload" in parsed.dropped_field_classes
    assert len(parsed.warnings) <= 15
    assert all("sensitive" not in item for item in parsed.warnings)


def test_unbounded_payload_is_rejected_before_persistence_draft() -> None:
    with pytest.raises(VNextError) as error:
        LegacySavedCaseV1Parser().parse(
            {"title": "Too large", "version": 1, "extra": "x" * 70_000}
        )

    assert error.value.code is ErrorCode.VALIDATION_FAILED
