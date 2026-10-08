"""Offline regressions for evidence trust and source coverage contracts."""

import pytest

from services.terrain_risk_service import DEFAULT_LAYERS, _data_quality, _overall, _source_layer_row
from services.terrain_risk_providers.ardswc_slope_hazard_provider import ArdswcSlopeHazardProvider, TileCoord, match_feature
from services.terrain_risk_providers.wra_flood_provider import WraFloodProvider


def test_limited_evidence_is_never_fully_available():
    quality = _data_quality({}, {"flood": {"status": "limited", "matched": True}}, ["flood"], ["flood"])
    assert quality["status"] == "limited"


def test_successful_no_matches_cannot_produce_low_risk():
    assert _overall([], {"status": "good"}, DEFAULT_LAYERS)["level"] == "unknown"


def test_positive_partial_evidence_survives_without_high_confidence():
    summary = _overall([{"key": "flood", "level": "high"}], {"status": "limited"}, ["flood"])
    assert summary["level"] == "high"
    assert summary["confidence"] != "high"
    row = _source_layer_row("flood", "flood", {"status": "limited", "matched": True})
    assert row["assessment_status"] == "matched"
    assert row["coverage_status"] == "partial"


def test_closed_stream_is_proximity_not_polygon_containment():
    ring = [[121.54, 25.02], [121.56, 25.02], [121.56, 25.04], [121.54, 25.04], [121.54, 25.02]]
    feature = {"geometry": [ring], "_stable_id": "closed-stream"}
    assert match_feature(feature, 25.03, 121.55, 100, "line") is None
    assert match_feature(feature, 25.03, 121.55, 100, "polygon")["distance_m"] == 0


@pytest.mark.parametrize("geometry_type", ["Polygon", "MultiPolygon"])
@pytest.mark.parametrize("geojson", [False, True])
def test_ardswc_polygon_hole_is_not_containment_or_radius_overlap(geometry_type, geojson):
    outer = [[121.50, 25.0], [121.60, 25.0], [121.60, 25.10], [121.50, 25.10], [121.50, 25.0]]
    hole = [[121.52, 25.02], [121.58, 25.02], [121.58, 25.08], [121.52, 25.08], [121.52, 25.02]]
    rings = [outer, hole]
    coordinates = rings if geometry_type == "Polygon" else [rings, [[[122.0, 26.0], [122.1, 26.0], [122.1, 26.1], [122.0, 26.1], [122.0, 26.0]]]]
    geometry = {"type": geometry_type, "coordinates": coordinates} if geojson else coordinates
    feature = {"geometry": geometry, "_stable_id": "hole-polygon"}
    assert match_feature(feature, 25.05, 121.55, 100, "polygon") is None
    assert match_feature(feature, 25.01, 121.51, 100, "polygon")["distance_m"] == 0
    assert match_feature(feature, 25.05, 121.5201, 100, "polygon") is not None


def test_ardswc_partial_positive_keeps_layer_semantics_and_tile_counts():
    provider = ArdswcSlopeHazardProvider(decoder=lambda payload, tile: [], use_cache=False)
    tiles = [TileCoord(14, 0, 0), TileCoord(14, 1, 0)]
    feature = {"id": "stream", "geometry": [[121.54, 25.026], [121.55, 25.026]]}
    row = provider._build_mvt_result("debris_flow", tiles, {
        ("debris_flow", tiles[0]): ([feature], None),
        ("debris_flow", tiles[1]): ([], "TimeoutError"),
    }, 25.026, 121.543, 100)
    assert row["status"] == "limited" and row["matched"] is True
    assert row["source"]["layer_id"] == "debris_flow"
    assert row["source"]["match_semantics"] == "stream_proximity_within_radius"
    assert row["value"]["successful_tiles"] == 1
    assert row["value"]["failed_tiles"] == 1


@pytest.mark.parametrize("kwargs", [{"max_tiles_per_layer": 999}, {"timeout_seconds": 0}, {"query_budget_seconds": 0}])
def test_ardswc_constructor_cannot_disable_request_bounds(kwargs):
    with pytest.raises(ValueError):
        ArdswcSlopeHazardProvider(**kwargs)


@pytest.mark.parametrize("matched", [True, False])
def test_wra_keeps_configured_scenario_and_runtime_provenance(matched):
    result = {"scenario": "6h-150mm", "matched": matched, "class": 3,
              "canonical_depth": "1.0-2.0 m", "dataset_version": "v1",
              "artifact_sha256": "a" * 64, "source_vintage": "official-fixture-2024"}
    layer = WraFloodProvider(query_point=lambda *args: result, scenario="6h-150mm").analyze(25, 121, 2000)
    assert layer["source"]["scenario_label"] == "6 小時 / 150mm 淹水潛勢情境"
    assert layer["source"]["artifact_sha256"] == "a" * 64
    assert layer["source"]["data_vintage"] == "official-fixture-2024"
    assert layer["source"]["match_semantics"] == "point_intersects_scenario_polygon"
    assert "整筆土地" in layer["source"]["limitation"]


def test_wra_scenario_mismatch_is_error_not_successful_no_match():
    layer = WraFloodProvider(query_point=lambda *args: {"scenario": "6h-150mm", "matched": False}).analyze(25, 121, 500)
    assert layer["status"] == "error"
