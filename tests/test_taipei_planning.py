from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone

import pytest

from services.vnext.errors import ErrorCode, VNextError
from services.vnext.feature_flags import VNextFeatureFlags
from services.vnext.taipei_planning import (
    AuthorityClass,
    CoverageStatus,
    DocumentKind,
    ManualPlanningReference,
    PlanningStatus,
    VerificationStatus,
    normalize_manual_reference,
    normalize_reported_text,
)


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def test_taipei_planning_feature_flag_defaults_off_and_uses_dedicated_name() -> None:
    assert VNextFeatureFlags.from_environment({}).taipei_planning_read_v1 is False
    assert VNextFeatureFlags.from_environment(
        {"TAIPEI_PLANNING_READ_V1": "true"}
    ).taipei_planning_read_v1 is True
    assert VNextFeatureFlags.from_environment(
        {"FEATURE_TAIPEI_PLANNING_READ_V1": "true"}
    ).taipei_planning_read_v1 is False


def test_taipei_planning_feature_flag_enabled_lookup_is_default_deny() -> None:
    flags = VNextFeatureFlags(taipei_planning_read_v1=True)
    assert flags.enabled("taipei_planning_read_v1") is True
    assert flags.enabled("taipei_planning_read_v2") is False


def test_manual_announcement_is_always_limited_user_provided_and_unverified() -> None:
    observation = normalize_manual_reference(
        ManualPlanningReference(
            jurisdiction="Taipei City",
            scope="urban_plan_non_national_park",
            document_kind=DocumentKind.OFFICIAL_URBAN_PLAN_ANNOUNCEMENT,
            reported_document_reference="府都規字第1150001號/附件一",
            reported_plan_identifier="臺北市都市計畫（第115次通盤檢討）",
            reported_effective_date=date(2026, 9, 19),
        ),
        clock=lambda: NOW,
    )

    assert (observation.status, observation.authority_class, observation.coverage_status) == (
        PlanningStatus.LIMITED,
        AuthorityClass.USER_PROVIDED,
        CoverageStatus.LIMITED,
    )
    assert observation.verification_required is True
    assert observation.verification_status is VerificationStatus.UNVERIFIED
    assert observation.normalized_at == NOW
    assert observation.reported_effective_date == date(2026, 9, 19)
    assert observation.source_portal == "https://udd.gov.taipei/announcement/biwfsm8"
    assert (
        "Current legal effect requires confirmation against later amendments, "
        "supersession, revocation, and the competent authority."
    ) in observation.limitations


def test_manual_certificate_never_claims_current_property_or_case_applicability() -> None:
    observation = normalize_manual_reference(
        ManualPlanningReference(
            jurisdiction="Taipei City",
            scope="urban_plan_non_national_park",
            document_kind=DocumentKind.ISSUED_ZONING_CERTIFICATE,
            reported_document_reference="都規證字第115-001號",
            reported_zone_code="住三",
            reported_zone_label="第三種住宅區",
        ),
        clock=lambda: NOW,
    )

    limitations = " ".join(observation.limitations).lower()
    assert observation.source_portal == "https://zone.udd.gov.taipei/new_index1.aspx"
    assert observation.issuing_authority == "Taipei City Department of Urban Development"
    assert "authenticity" in limitations
    assert "currency" in limitations
    assert "loaded property" in limitations
    assert "entire case" in limitations
    assert "lui_002" in limitations
    assert not {
        "far",
        "bcr",
        "buildability",
        "ownership",
        "entitlement",
        "approval",
        "parcel_confirmation",
    }.intersection(asdict(observation))


def test_optional_blank_values_normalize_to_none_and_slash_punctuation_is_data() -> None:
    observation = normalize_manual_reference(
        ManualPlanningReference(
            jurisdiction="Taipei City",
            scope="urban_plan_non_national_park",
            document_kind=DocumentKind.OFFICIAL_URBAN_PLAN_ANNOUNCEMENT,
            reported_document_reference="  公告字號A\\B/附表（二）  ",
            reported_plan_identifier="  ",
            reported_zone_code=None,
            reported_zone_label="　",
        ),
        clock=lambda: NOW,
    )

    assert observation.reported_document_reference == "公告字號A\\B/附表（二）"
    assert observation.reported_plan_identifier is None
    assert observation.reported_zone_code is None
    assert observation.reported_zone_label is None


@pytest.mark.parametrize(
    "value",
    [
        "https://evil.invalid/x",
        "HTTPS://evil.invalid/x",
        "www.evil.invalid",
        "prefix://evil.invalid",
        "https:evil.invalid",
        r"http:\\evil.invalid\x",
        r"file:\\server\share",
        "C:\\secret",
        "\\\\server\\share",
        "/etc/passwd",
        "..",
        "../../secret",
        "safe/../secret",
        "<b>x</b>",
        "bad\x00value",
        "bad\x1fvalue",
        "bad\u0085value",
        "bad\u009fvalue",
        "\ttrimmed-control",
        "trimmed-control\n",
    ],
)
def test_reported_text_rejects_urls_absolute_paths_traversal_html_and_controls(value: str) -> None:
    with pytest.raises(VNextError) as error:
        normalize_reported_text(value, required=True, maximum=200)
    assert error.value.code is ErrorCode.VALIDATION_FAILED


@pytest.mark.parametrize("value", ["", "   ", "x" * 201])
def test_required_reported_text_is_bounded(value: str) -> None:
    with pytest.raises(VNextError) as error:
        normalize_reported_text(value, required=True, maximum=200)
    assert error.value.code is ErrorCode.VALIDATION_FAILED


@pytest.mark.parametrize(
    ("jurisdiction", "scope"),
    [
        ("New Taipei City", "urban_plan_non_national_park"),
        ("Taipei", "urban_plan_non_national_park"),
        ("Taipei City", "national_park"),
    ],
)
def test_unsupported_jurisdiction_and_scope_are_bounded_422(
    jurisdiction: str,
    scope: str,
) -> None:
    with pytest.raises(VNextError) as error:
        normalize_manual_reference(
            ManualPlanningReference(
                jurisdiction=jurisdiction,
                scope=scope,
                document_kind=DocumentKind.ISSUED_ZONING_CERTIFICATE,
                reported_document_reference="都規證字第115-001號",
            ),
            clock=lambda: NOW,
        )
    assert error.value.code is ErrorCode.UNSUPPORTED_INPUT
    assert error.value.status_code == 422


def test_normalization_requires_an_aware_clock() -> None:
    with pytest.raises(VNextError) as error:
        normalize_manual_reference(
            ManualPlanningReference(
                jurisdiction="Taipei City",
                scope="urban_plan_non_national_park",
                document_kind=DocumentKind.ISSUED_ZONING_CERTIFICATE,
                reported_document_reference="都規證字第115-001號",
            ),
            clock=lambda: datetime(2026, 9, 20, 12, 0),
        )
    assert error.value.code is ErrorCode.VALIDATION_FAILED


def test_not_available_is_future_vocabulary_and_never_a_normalized_success() -> None:
    assert PlanningStatus.NOT_AVAILABLE.value == "NOT_AVAILABLE"
    assert AuthorityClass.NOT_AVAILABLE.value == "NOT_AVAILABLE"
    assert CoverageStatus.NOT_AVAILABLE.value == "NOT_AVAILABLE"
    assert tuple(VerificationStatus) == (VerificationStatus.UNVERIFIED,)
