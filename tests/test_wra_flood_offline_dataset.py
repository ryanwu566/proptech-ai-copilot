"""Unit tests for the pure WRA flood offline dataset/normalization logic.

These tests use only tiny synthetic geometries.  No official WRA SHP/ZIP is
committed or read.  A synthetic polygon covering a coordinate near Beitou is
used purely as regression metadata; because it is NOT the official WRA Beitou
polygon, these tests do not claim to reproduce a real WRA flood hit.  A live
official-SHP smoke test is deferred to a later phase.
"""

from __future__ import annotations

import math

import pytest
from shapely.geometry import MultiPolygon, Point, Polygon

from services.wra_flood_offline_dataset import (
    CLASS_TO_CANONICAL_DEPTH,
    DatasetExpectation,
    FloodFeature,
    canonical_depth_for_class,
    is_flood_dept_malformed,
    match_point,
    normalize_feature,
    normalize_geometry,
    project_3826_to_4326,
    transform_geometry_3826_to_4326,
    validate_dataset,
)


def _square(cx: float, cy: float, half: float = 0.001) -> Polygon:
    return Polygon(
        [
            (cx - half, cy - half),
            (cx + half, cy - half),
            (cx + half, cy + half),
            (cx - half, cy + half),
            (cx - half, cy - half),
        ]
    )


def _feature(class_value: int, geometry, flood_dept_raw=None) -> FloodFeature:
    feature, reason = normalize_feature(
        {"Class": class_value, "flood_dept": flood_dept_raw, "geometry": geometry}
    )
    assert reason is None, reason
    assert feature is not None
    return feature


# 1. Class 1-5 canonical mapping ------------------------------------------------

@pytest.mark.parametrize(
    "class_value,expected",
    [
        (1, "0.3-0.5 m"),
        (2, "0.5-1.0 m"),
        (3, "1.0-2.0 m"),
        (4, "2.0-3.0 m"),
        (5, ">3.0 m"),
    ],
)
def test_canonical_depth_mapping(class_value: int, expected: str) -> None:
    assert canonical_depth_for_class(class_value) == expected
    assert CLASS_TO_CANONICAL_DEPTH[class_value] == expected


def test_canonical_depth_accepts_numeric_string_class() -> None:
    assert canonical_depth_for_class("3") == "1.0-2.0 m"


# 2. malformed flood_dept does not affect canonical mapping ---------------------

@pytest.mark.parametrize("raw", ["0.3-0.>3.0", "0.>3.0-1.0", "", None, "garbage"])
def test_malformed_flood_dept_detected(raw) -> None:
    assert is_flood_dept_malformed(raw) is True


@pytest.mark.parametrize("raw", ["0.3-0.5", ">3.0", "1.0-2.0"])
def test_wellformed_flood_dept_not_flagged(raw) -> None:
    assert is_flood_dept_malformed(raw) is False


def test_malformed_flood_dept_preserved_but_canonical_from_class() -> None:
    feature = _feature(1, _square(121.5, 25.1), flood_dept_raw="0.3-0.>3.0")
    assert feature.flood_dept_malformed is True
    assert feature.flood_dept_raw == "0.3-0.>3.0"
    # Canonical depth is driven solely by Class, not by the malformed string.
    assert feature.canonical_depth == "0.3-0.5 m"


# 3. self-intersecting polygon -> make_valid -> valid ---------------------------

def test_self_intersecting_polygon_repaired() -> None:
    # Classic bowtie / figure-eight ring that is invalid until repaired.
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    assert bowtie.is_valid is False
    result = normalize_geometry(bowtie)
    assert result.valid is True
    assert result.geometry is not None
    assert result.geometry.is_valid is True
    assert result.geometry.geom_type in {"Polygon", "MultiPolygon"}
    assert result.geometry.is_empty is False


# 4. null / empty rejection -----------------------------------------------------

def test_null_geometry_rejected() -> None:
    result = normalize_geometry(None)
    assert result.valid is False
    assert result.error == "null_geometry"


def test_empty_geometry_rejected() -> None:
    result = normalize_geometry(Polygon())
    assert result.valid is False
    assert result.error == "empty_geometry"


# 5. unexpected geometry type rejection -----------------------------------------

def test_non_polygon_input_rejected() -> None:
    from shapely.geometry import LineString

    result = normalize_geometry(LineString([(0, 0), (1, 1)]))
    assert result.valid is False
    assert result.error == "unexpected_input_geometry_type"


def test_geometry_collapsing_to_non_polygon_rejected() -> None:
    # A degenerate zero-width polygon repairs to a line/empty, never a polygon.
    degenerate = Polygon([(0, 0), (1, 1), (2, 2), (0, 0)])
    result = normalize_geometry(degenerate)
    assert result.valid is False
    assert result.error in {
        "unexpected_geometry_type_after_make_valid",
        "empty_after_make_valid",
    }


# 6. EPSG:3826 -> EPSG:4326 transformation --------------------------------------

def test_point_reprojection_lands_in_taiwan() -> None:
    # A TWD97 / EPSG:3826 easting-northing roughly in northern Taiwan.
    lon, lat = project_3826_to_4326(305000.0, 2780000.0)
    assert 119.0 < lon < 122.5
    assert 21.5 < lat < 25.5


def test_geometry_reprojection_preserves_type_and_uses_lonlat_order() -> None:
    square_3826 = _square(305000.0, 2780000.0, half=100.0)
    reprojected = transform_geometry_3826_to_4326(square_3826)
    assert reprojected.geom_type == "Polygon"
    assert reprojected.is_valid
    minx, miny, maxx, maxy = reprojected.bounds
    # always_xy=True => x is longitude, y is latitude.
    assert 119.0 < minx < 122.5
    assert 21.5 < miny < 25.5


# 7-9. point-in-polygon matching ------------------------------------------------

def test_point_inside_polygon_hits() -> None:
    feature = _feature(2, _square(121.5, 25.1))
    result = match_point(121.5, 25.1, [feature])
    assert result.matched is True
    assert result.matched_feature is not None
    assert result.matched_feature["class"] == 2
    assert result.matched_feature["canonical_depth"] == "0.5-1.0 m"
    assert result.matched_count == 1


def test_point_outside_polygon_misses() -> None:
    feature = _feature(2, _square(121.5, 25.1))
    result = match_point(121.9, 25.9, [feature])
    assert result.matched is False
    assert result.matched_feature is None
    assert result.matched_count == 0


def test_point_on_boundary_hits_via_intersects() -> None:
    feature = _feature(1, _square(121.5, 25.1, half=0.001))
    # A vertex on the polygon boundary; strict contains would exclude it.
    result = match_point(121.499, 25.099, [feature])
    assert result.matched is True


def test_overlapping_features_report_deepest_class() -> None:
    shallow = _feature(1, _square(121.5, 25.1, half=0.002))
    deep = _feature(4, _square(121.5, 25.1, half=0.001))
    result = match_point(121.5, 25.1, [shallow, deep])
    assert result.matched is True
    assert result.matched_count == 2
    assert result.matched_feature is not None
    assert result.matched_feature["class"] == 4


def test_multipolygon_feature_matches() -> None:
    multi = MultiPolygon([_square(121.5, 25.1), _square(121.6, 25.2)])
    feature = _feature(3, multi)
    assert match_point(121.6, 25.2, [feature]).matched is True
    assert match_point(121.55, 25.15, [feature]).matched is False


# 10. invalid Class rejection ---------------------------------------------------

@pytest.mark.parametrize("bad_class", [0, 6, -1, "x", None, 2.5, True])
def test_invalid_class_rejected(bad_class) -> None:
    feature, reason = normalize_feature({"Class": bad_class, "geometry": _square(121.5, 25.1)})
    assert feature is None
    assert reason in {"invalid_class", "missing_field:Class"}


def test_invalid_class_raises_in_canonical_helper() -> None:
    with pytest.raises(ValueError):
        canonical_depth_for_class(9)


# 11. validation summary statistics ---------------------------------------------

def test_validation_summary_counts() -> None:
    records = [
        {"Class": 1, "flood_dept": "0.3-0.5", "geometry": _square(121.50, 25.10)},
        {"Class": 1, "flood_dept": "0.3-0.>3.0", "geometry": _square(121.51, 25.10)},  # malformed
        {"Class": 2, "flood_dept": "0.5-1.0", "geometry": _square(121.52, 25.10)},
        {"Class": 3, "flood_dept": ">3.0", "geometry": Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])},  # self-int -> repaired
        {"Class": 9, "flood_dept": "x", "geometry": _square(121.53, 25.10)},  # invalid class
        {"Class": 2, "flood_dept": "0.5-1.0", "geometry": None},  # null geometry
        {"flood_dept": "0.3-0.5", "geometry": _square(121.54, 25.10)},  # missing Class
    ]
    features, summary = validate_dataset(records)

    assert summary.feature_count == 7
    assert summary.accepted_count == 4  # two class-1, one class-2, one repaired class-3
    assert summary.rejected_count == 3
    assert summary.class_distribution == {1: 2, 2: 1, 3: 1}
    assert summary.malformed_flood_dept_count == 1
    assert summary.invalid_class_count == 1
    assert summary.null_or_empty_geometry_count == 1
    assert summary.missing_field_count == 1
    assert summary.valid is True
    assert len(features) == 4


def test_validation_expectation_pass_and_fail() -> None:
    records = [
        {"Class": 1, "flood_dept": "0.3-0.5", "geometry": _square(121.50, 25.10)},
        {"Class": 5, "flood_dept": "0.>3.0-1.0", "geometry": _square(121.51, 25.10)},  # malformed
    ]
    ok = DatasetExpectation(feature_count=2, class_distribution={1: 1, 5: 1}, malformed_flood_dept_count=1)
    _, summary_ok = validate_dataset(records, expected=ok)
    assert summary_ok.valid is True

    bad = DatasetExpectation(feature_count=99)
    _, summary_bad = validate_dataset(records, expected=bad)
    assert summary_bad.valid is False
    assert any("feature_count_mismatch" in error for error in summary_bad.errors)


def test_empty_dataset_is_invalid() -> None:
    _, summary = validate_dataset([])
    assert summary.valid is False
    assert "no_valid_features" in summary.errors


# Regression metadata (synthetic, NOT an official WRA polygon) ------------------

def test_synthetic_beitou_regression_metadata() -> None:
    # Regression coordinate from the manual WRA verification (24h/350mm).
    # This synthetic square is a placeholder, so a hit here only exercises the
    # matcher wiring; it does not reproduce the official WRA Beitou result.
    beitou_lon = 121.4648045853475
    beitou_lat = 25.128805040872507
    synthetic = _feature(1, _square(beitou_lon, beitou_lat, half=0.0005))
    result = match_point(beitou_lon, beitou_lat, [synthetic])
    assert result.matched is True
    assert result.matched_feature is not None
    assert result.matched_feature["class"] == 1
    assert result.matched_feature["canonical_depth"] == "0.3-0.5 m"
    assert not math.isnan(beitou_lat)
