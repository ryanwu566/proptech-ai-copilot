"""Focused contracts for the provider-independent Stage 2A GIS foundation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from services.vnext.property_graph import (
    EvidenceStatus,
    LicenseStatus,
    PropertyRelationStatus,
    PropertyRelationType,
    SourceEnvironment,
    SourceType,
)
from services.vnext.spatial import (
    API_INTERCHANGE_CRS,
    CRSDefinition,
    CoordinateOrder,
    GeometryType,
    MapFeatureSelection,
    MapLegendItem,
    MapViewport,
    MapWorkspaceContract,
    OperationUnit,
    ParcelGeometry,
    ProviderError,
    ProviderResultStatus,
    RefreshSemantics,
    SpatialAuthority,
    SpatialAvailability,
    SpatialContractError,
    SpatialCoverage,
    SpatialCoverageStatus,
    SpatialLayer,
    SpatialLayerRegistry,
    SpatialObservationStatus,
    SpatialOperand,
    SpatialOperation,
    SpatialOperationRequest,
    SpatialPrecision,
    SpatialProvenance,
    SpatialProviderRequest,
    SpatialProviderResult,
    SpatialLicense,
    TemporalSemantics,
    execute_spatial_operation,
    normalize_provider_observation,
    observation_evidence_draft,
    parcel_geometry_evidence_draft,
    parcel_geometry_from_source,
    projected_crs,
    proposed_property_parcel_relation,
    transform_geometry,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vnext_spatial_synthetic.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
GEOMETRIES = FIXTURE["geometries"]
NOW = datetime(2026, 9, 8, 4, 5, 6, tzinfo=timezone.utc)
WORKSPACE_ID = UUID("10000000-0000-0000-0000-000000000001")
SUBJECT_ID = UUID("20000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("30000000-0000-0000-0000-000000000001")
LAYER_ID = UUID("40000000-0000-0000-0000-000000000001")


def coverage(
    status: SpatialCoverageStatus = SpatialCoverageStatus.COMPLETE,
    *,
    gaps: tuple[str, ...] = (),
) -> SpatialCoverage:
    return SpatialCoverage(
        status=status,
        geography={"kind": "synthetic_extent", "value": "fixture-alpha"},
        temporal={"status": "known", "as_of": "2026-09-08"},
        subject_scope="parcel",
        fields=("geometry", "layer.observation"),
        gaps=gaps,
    )


def license_metadata() -> SpatialLicense:
    return SpatialLicense(
        status=LicenseStatus.NOT_APPLICABLE,
        license_id="synthetic-test-fixture",
        attribution="Synthetic Stage 2A test fixture",
        commercial_use="not_applicable",
        redistribution="test_only",
    )


def provenance(
    *,
    environment: SourceEnvironment = SourceEnvironment.TEST,
    source_type: SourceType = SourceType.TEST,
    authority: SpatialAuthority = SpatialAuthority.SYNTHETIC,
) -> SpatialProvenance:
    return SpatialProvenance(
        source_id="vnext-test",
        source_type=source_type,
        authority=authority,
        environment=environment,
        provider_id="synthetic-spatial-provider",
        provider_version="fixture-v1",
        retrieved_at=NOW,
        effective_at=NOW,
        evidence_id=EVIDENCE_ID,
        source_record_id="fixture-record-alpha",
        source_ref="fixture:vnext-spatial-synthetic-v1",
    )


def layer() -> SpatialLayer:
    selected_license = license_metadata()
    return SpatialLayer(
        layer_id=LAYER_ID,
        layer_key="synthetic.parcel-context",
        title="Synthetic parcel context",
        category="parcel_context",
        provider_id="synthetic-spatial-provider",
        provider_version="fixture-v1",
        source_id="vnext-test",
        source_type=SourceType.TEST,
        source_environment=SourceEnvironment.TEST,
        authority=SpatialAuthority.SYNTHETIC,
        geometry_types=frozenset({GeometryType.POLYGON, GeometryType.MULTI_POLYGON}),
        source_crs=(API_INTERCHANGE_CRS, projected_crs("EPSG:3826")),
        supported_crs=(API_INTERCHANGE_CRS,),
        coverage=coverage(),
        temporal_semantics=TemporalSemantics.SNAPSHOT,
        refresh_semantics=RefreshSemantics.IMMUTABLE_RELEASE,
        license=selected_license,
        attribution=selected_license.attribution,
        evidence_requirements=("evidence_id", "retrieved_at", "coverage"),
        provenance_requirements=("source_crs", "normalized_crs", "processing_lineage"),
        availability=SpatialAvailability.LIMITED,
        limitations=("Synthetic fixture; never production authority.",),
    )


def operand(name: str, *, crs: CRSDefinition = API_INTERCHANGE_CRS) -> SpatialOperand:
    return SpatialOperand(feature_id=name, geometry=GEOMETRIES[name], crs=crs)


def request(
    *, layer_key: str | None = "synthetic.parcel-context"
) -> SpatialProviderRequest:
    return SpatialProviderRequest(
        workspace_id=WORKSPACE_ID,
        subject_type="parcel",
        subject_id=SUBJECT_ID,
        purpose="due_diligence",
        as_of=NOW,
        layer_key=layer_key,
    )


def test_fixture_is_unambiguously_synthetic_and_covers_required_scenarios() -> None:
    assert FIXTURE["fixture_environment"] == "test"
    assert FIXTURE["source_id"] == "vnext-test"
    assert FIXTURE["source_type"] == "test"
    assert FIXTURE["authority"] == "synthetic"
    disclaimer = FIXTURE["disclaimer"].lower()
    assert "synthetic test data only" in disclaimer
    assert "not official" in disclaimer
    assert "nlsc" in disclaimer
    assert set(FIXTURE["observation_scenarios"]) == {
        "present",
        "absent",
        "no_match",
        "partial_coverage",
        "unknown",
        "provider_unavailable",
        "provider_error",
        "stale",
        "not_assessed",
    }


def test_crs_contract_rejects_ambiguous_axis_order_and_requires_projected_distance_crs() -> (
    None
):
    with pytest.raises(SpatialContractError, match="invalid_coordinate_order"):
        CRSDefinition("EPSG:4326", CoordinateOrder.X_Y)
    with pytest.raises(SpatialContractError, match="projected_crs_required"):
        projected_crs("EPSG:4326")


def test_transformation_preserves_source_geometry_crs_and_lineage() -> None:
    source_crs = projected_crs("EPSG:3826")
    source = operand("parcel_alpha_twd97_tm2_121", crs=source_crs)
    transformed = transform_geometry(source, API_INTERCHANGE_CRS)

    assert transformed.source_crs.identifier == "EPSG:3826"
    assert transformed.target_crs.identifier == "EPSG:4326"
    assert dict(transformed.source_geometry) == GEOMETRIES["parcel_alpha_twd97_tm2_121"]
    point = transformed.transformed_geometry["coordinates"][0][0]
    assert point == pytest.approx((121.55, 25.03), abs=1e-6)
    assert transformed.lineage.operation == "crs_transform"
    assert transformed.lineage.coordinate_order is CoordinateOrder.EASTING_NORTHING


def test_parcel_geometry_is_versioned_evidence_linked_and_source_preserving() -> None:
    parcel = parcel_geometry_from_source(
        geometry_id=UUID("50000000-0000-0000-0000-000000000001"),
        parcel_identity_reference_id=SUBJECT_ID,
        source_operand=operand(
            "parcel_alpha_twd97_tm2_121",
            crs=projected_crs("EPSG:3826"),
        ),
        precision=SpatialPrecision(0.25, "meters", "provider_reported"),
        tolerance=0.5,
        tolerance_unit="meters",
        geometry_source="provider_observation",
        coverage=coverage(),
        provenance=provenance(),
        effective_at=NOW,
        valid_from=NOW,
    )

    assert isinstance(parcel, ParcelGeometry)
    assert parcel.geometry_type is GeometryType.POLYGON
    assert parcel.source_crs.identifier == "EPSG:3826"
    assert parcel.normalized_crs.identifier == "EPSG:4326"
    assert parcel.evidence_id == EVIDENCE_ID
    assert parcel.version == 1
    assert parcel.supersedes_geometry_id is None
    assert parcel.provenance.processing_lineage[-1].source_crs == "EPSG:3826"


@pytest.mark.parametrize(
    ("fixture_name", "expected_code"),
    (("malformed_polygon", "malformed_geometry"), ("empty_polygon", "empty_geometry")),
)
def test_invalid_and_empty_geometry_fail_safely(
    fixture_name: str, expected_code: str
) -> None:
    with pytest.raises(SpatialContractError, match=expected_code):
        operand(fixture_name)


def test_parcel_geometry_adapts_to_existing_stage_1_evidence() -> None:
    parcel = parcel_geometry_from_source(
        geometry_id=UUID("50000000-0000-0000-0000-000000000011"),
        parcel_identity_reference_id=SUBJECT_ID,
        source_operand=operand("parcel_alpha"),
        precision=SpatialPrecision(0.25, "meters", "provider_reported"),
        tolerance=0.5,
        tolerance_unit="meters",
        geometry_source="provider_observation",
        coverage=coverage(),
        provenance=provenance(),
        effective_at=NOW,
        valid_from=NOW,
    )

    draft = parcel_geometry_evidence_draft(parcel, license_metadata())

    assert draft.fact_type == "spatial.parcel_geometry.v1"
    assert draft.value is None
    assert draft.value_ref == f"parcel-geometry:{parcel.geometry_id}"
    assert draft.evidence_status is EvidenceStatus.UNVERIFIED
    assert draft.coverage["status"] == "complete"
    assert draft.license["attribution"] == "Synthetic Stage 2A test fixture"


def test_epsg4326_rejects_swapped_latitude_longitude_bounds() -> None:
    with pytest.raises(
        SpatialContractError, match="coordinate_order_or_bounds_invalid"
    ):
        SpatialOperand(
            feature_id="swapped-point",
            geometry={"type": "Point", "coordinates": [25.03, 121.55]},
            crs=API_INTERCHANGE_CRS,
        )


def test_point_in_polygon_inside_and_outside_are_deterministic() -> None:
    inside = execute_spatial_operation(
        SpatialOperationRequest(
            operation=SpatialOperation.POINT_IN_POLYGON,
            left=operand("inside_point"),
            right=operand("parcel_alpha"),
            processing_crs=API_INTERCHANGE_CRS,
            units=OperationUnit.BOOLEAN,
        )
    )
    outside = execute_spatial_operation(
        SpatialOperationRequest(
            operation=SpatialOperation.POINT_IN_POLYGON,
            left=operand("outside_point"),
            right=operand("parcel_alpha"),
            processing_crs=API_INTERCHANGE_CRS,
            units=OperationUnit.BOOLEAN,
        )
    )

    assert inside.result == {"matches": True}
    assert outside.result == {"matches": False}
    assert inside.units is OperationUnit.BOOLEAN
    assert inside.input_crs == ("EPSG:4326", "EPSG:4326")


def test_intersection_and_contains_cover_overlapping_candidates() -> None:
    intersects = execute_spatial_operation(
        SpatialOperationRequest(
            operation=SpatialOperation.INTERSECTS,
            left=operand("parcel_alpha"),
            right=operand("parcel_beta_overlap"),
            processing_crs=API_INTERCHANGE_CRS,
            units=OperationUnit.BOOLEAN,
        )
    )
    contains = execute_spatial_operation(
        SpatialOperationRequest(
            operation=SpatialOperation.CONTAINS,
            left=operand("parcel_alpha"),
            right=operand("inside_point"),
            processing_crs=API_INTERCHANGE_CRS,
            units=OperationUnit.BOOLEAN,
        )
    )
    assert intersects.result["matches"] is True
    assert contains.result["matches"] is True


def test_distance_nearest_and_bounding_box_declare_deterministic_units() -> None:
    processing = projected_crs("EPSG:3826")
    distance = execute_spatial_operation(
        SpatialOperationRequest(
            operation=SpatialOperation.DISTANCE,
            left=operand("outside_point"),
            right=operand("parcel_alpha"),
            processing_crs=processing,
            units=OperationUnit.METERS,
            tolerance=10,
            tolerance_unit=OperationUnit.METERS,
        )
    )
    nearest = execute_spatial_operation(
        SpatialOperationRequest(
            operation=SpatialOperation.NEAREST,
            left=operand("outside_point"),
            candidates=(operand("parcel_alpha"), operand("parcel_gamma_separate")),
            processing_crs=processing,
            units=OperationUnit.METERS,
        )
    )
    bounds = execute_spatial_operation(
        SpatialOperationRequest(
            operation=SpatialOperation.BOUNDING_BOX,
            left=operand("parcel_alpha"),
            candidates=(
                operand("parcel_beta_overlap"),
                operand("parcel_gamma_separate"),
            ),
            processing_crs=API_INTERCHANGE_CRS,
            units=OperationUnit.CRS_UNITS,
        )
    )

    assert distance.units is OperationUnit.METERS
    assert distance.tolerance_unit is OperationUnit.METERS
    assert distance.result["distance"] > 10
    assert distance.result["within_tolerance"] is False
    assert nearest.result["feature_id"] == "parcel_gamma_separate"
    assert nearest.result["distance"] >= 0
    assert bounds.result["bounds"] == pytest.approx((121.55, 25.03, 121.551, 25.031))
    assert bounds.result["feature_ids"] == ["parcel_beta_overlap"]


def test_unknown_is_not_absence_or_safety() -> None:
    result = SpatialProviderResult[dict[str, object]](
        status=ProviderResultStatus.UNKNOWN,
        data=None,
        coverage=coverage(SpatialCoverageStatus.UNKNOWN, gaps=("coverage_not_proven",)),
        license=license_metadata(),
        provenance=provenance(),
    )
    observation = normalize_provider_observation(
        observation_id=UUID("60000000-0000-0000-0000-000000000001"),
        request=request(),
        layer=layer(),
        result=result,
    )

    assert observation.status is SpatialObservationStatus.UNKNOWN
    assert observation.status is not SpatialObservationStatus.ABSENT
    assert observation.evidence_status is EvidenceStatus.UNKNOWN
    assert observation.supports_safe_conclusion is False
    assert observation.value is None


def test_provider_error_remains_distinct_and_maps_to_unavailable_evidence() -> None:
    result = SpatialProviderResult[dict[str, object]](
        status=ProviderResultStatus.PROVIDER_ERROR,
        data=None,
        coverage=coverage(SpatialCoverageStatus.UNAVAILABLE, gaps=("provider_failed",)),
        license=license_metadata(),
        provenance=provenance(),
        errors=(ProviderError("transport_error", True),),
    )
    observation = normalize_provider_observation(
        observation_id=UUID("60000000-0000-0000-0000-000000000002"),
        request=request(),
        layer=layer(),
        result=result,
    )

    assert observation.status is SpatialObservationStatus.PROVIDER_ERROR
    assert observation.evidence_status is EvidenceStatus.UNAVAILABLE
    assert observation.value is None


def test_absence_requires_complete_coverage_and_no_match_stays_distinct() -> None:
    with pytest.raises(
        SpatialContractError, match="absence_requires_complete_coverage"
    ):
        SpatialProviderResult[dict[str, object]](
            status=ProviderResultStatus.ABSENT,
            data=None,
            coverage=coverage(SpatialCoverageStatus.UNKNOWN, gaps=("unknown_extent",)),
            license=license_metadata(),
            provenance=provenance(),
        )

    no_match = SpatialProviderResult[dict[str, object]](
        status=ProviderResultStatus.NO_MATCH,
        data=None,
        coverage=coverage(
            SpatialCoverageStatus.UNKNOWN, gaps=("query_semantics_unknown",)
        ),
        license=license_metadata(),
        provenance=provenance(),
    )
    observation = normalize_provider_observation(
        observation_id=UUID("60000000-0000-0000-0000-000000000003"),
        request=request(),
        layer=layer(),
        result=no_match,
    )
    assert observation.status is SpatialObservationStatus.NO_MATCH
    assert observation.evidence_status is EvidenceStatus.UNKNOWN


@pytest.mark.parametrize(
    (
        "provider_status",
        "coverage_status",
        "data",
        "observation_status",
        "evidence_status",
    ),
    (
        (
            ProviderResultStatus.ABSENT,
            SpatialCoverageStatus.COMPLETE,
            None,
            SpatialObservationStatus.ABSENT,
            EvidenceStatus.AVAILABLE,
        ),
        (
            ProviderResultStatus.LIMITED,
            SpatialCoverageStatus.PARTIAL,
            {"feature_count": 1},
            SpatialObservationStatus.PARTIAL_COVERAGE,
            EvidenceStatus.LIMITED,
        ),
        (
            ProviderResultStatus.UNAVAILABLE,
            SpatialCoverageStatus.UNAVAILABLE,
            None,
            SpatialObservationStatus.UNAVAILABLE,
            EvidenceStatus.UNAVAILABLE,
        ),
        (
            ProviderResultStatus.STALE,
            SpatialCoverageStatus.COMPLETE,
            {"feature_count": 1},
            SpatialObservationStatus.STALE,
            EvidenceStatus.STALE,
        ),
        (
            ProviderResultStatus.NOT_ASSESSED,
            SpatialCoverageStatus.UNKNOWN,
            None,
            SpatialObservationStatus.NOT_ASSESSED,
            EvidenceStatus.UNKNOWN,
        ),
    ),
)
def test_provider_statuses_remain_distinct_through_normalization(
    provider_status: ProviderResultStatus,
    coverage_status: SpatialCoverageStatus,
    data: dict[str, object] | None,
    observation_status: SpatialObservationStatus,
    evidence_status: EvidenceStatus,
) -> None:
    gaps = () if coverage_status is SpatialCoverageStatus.COMPLETE else ("bounded_gap",)
    result = SpatialProviderResult[dict[str, object]](
        status=provider_status,
        data=data,
        coverage=coverage(coverage_status, gaps=gaps),
        license=license_metadata(),
        provenance=provenance(),
    )
    observation = normalize_provider_observation(
        observation_id=UUID("60000000-0000-0000-0000-000000000005"),
        request=request(),
        layer=layer(),
        result=result,
    )
    assert observation.status is observation_status
    assert observation.evidence_status is evidence_status
    assert observation.supports_safe_conclusion is False


def test_nonzero_tolerance_requires_an_explicit_projected_meter_crs() -> None:
    with pytest.raises(
        SpatialContractError, match="projected_meter_tolerance_required"
    ):
        SpatialOperationRequest(
            operation=SpatialOperation.INTERSECTS,
            left=operand("parcel_alpha"),
            right=operand("parcel_beta_overlap"),
            processing_crs=API_INTERCHANGE_CRS,
            units=OperationUnit.BOOLEAN,
            tolerance=0.0001,
            tolerance_unit=OperationUnit.CRS_UNITS,
        )


def test_evidence_adapter_preserves_coverage_license_and_processing_lineage() -> None:
    result = SpatialProviderResult[dict[str, object]](
        status=ProviderResultStatus.PRESENT,
        data={"feature_count": 1, "classification": "synthetic_overlap"},
        coverage=coverage(),
        license=license_metadata(),
        provenance=provenance(),
    )
    observation = normalize_provider_observation(
        observation_id=UUID("60000000-0000-0000-0000-000000000004"),
        request=request(),
        layer=layer(),
        result=result,
    )
    draft = observation_evidence_draft(observation)

    assert draft.fact_type == "spatial.layer_observation.v1"
    assert draft.source_id == "vnext-test"
    assert draft.source_environment is SourceEnvironment.TEST
    assert draft.retrieved_at == NOW
    assert draft.effective_from == NOW
    assert draft.coverage["status"] == "complete"
    assert draft.license["attribution"] == "Synthetic Stage 2A test fixture"
    assert draft.lineage["source_ref"] == "fixture:vnext-spatial-synthetic-v1"
    assert draft.value["result"]["feature_count"] == 1


def test_synthetic_source_cannot_claim_production_authority() -> None:
    with pytest.raises(
        SpatialContractError, match="synthetic_production_authority_forbidden"
    ):
        provenance(environment=SourceEnvironment.PRODUCTION)


def test_layer_registry_is_versioned_and_rejects_duplicate_versions() -> None:
    selected = layer()
    registry = SpatialLayerRegistry((selected,))
    assert registry.get("synthetic.parcel-context") is selected
    assert registry.all() == (selected,)
    with pytest.raises(SpatialContractError, match="duplicate_layer_version"):
        registry.register(selected)


def test_property_parcel_relationship_is_only_proposed_even_at_full_confidence() -> (
    None
):
    relation = proposed_property_parcel_relation(
        property_node_id=UUID("70000000-0000-0000-0000-000000000001"),
        parcel_node_id=UUID("70000000-0000-0000-0000-000000000002"),
        evidence_id=EVIDENCE_ID,
        source_id="vnext-test",
        source_environment=SourceEnvironment.TEST,
        confidence=1.0,
        confidence_method="synthetic-overlap-v1",
    )
    assert relation.relation_type is PropertyRelationType.PROPERTY_PARCEL
    assert relation.relation_status is PropertyRelationStatus.PROPOSED
    assert relation.confidence == 1.0


def test_map_workspace_is_case_scoped_and_requires_visible_layer_metadata() -> None:
    selected_layer = layer()
    selected_feature = MapFeatureSelection(
        feature_id="parcel-alpha",
        feature_type="parcel_candidate",
        layer_key=selected_layer.layer_key,
        evidence_id=EVIDENCE_ID,
    )
    workspace = MapWorkspaceContract(
        workspace_id=WORKSPACE_ID,
        case_id=UUID("80000000-0000-0000-0000-000000000001"),
        selected_property_entity_id=None,
        candidate_parcel_geometry_ids=(UUID("50000000-0000-0000-0000-000000000001"),),
        confirmed_parcel_geometry_ids=(),
        selected_layer_keys=(selected_layer.layer_key,),
        legend=(
            MapLegendItem(
                layer_key=selected_layer.layer_key,
                title=selected_layer.title,
                authority=selected_layer.authority,
                observation_status=SpatialObservationStatus.PARTIAL_COVERAGE,
                attribution=selected_layer.attribution,
            ),
        ),
        observation_ids=(UUID("60000000-0000-0000-0000-000000000004"),),
        viewport=MapViewport(121.5505, 25.0305, 18),
        selected_feature=selected_feature,
        limitations=("Parcel candidate remains unconfirmed.",),
    )
    assert workspace.case_id == UUID("80000000-0000-0000-0000-000000000001")
    assert workspace.selected_property_entity_id is None
    assert workspace.confirmed_parcel_geometry_ids == ()
