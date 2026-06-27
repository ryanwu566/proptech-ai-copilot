"""Terrain risk provider contract tests."""

from services.terrain_risk_providers import (
    ArdswcSlopeHazardProvider,
    GeologyCloudProvider,
    NlscTerrainProvider,
    WraFloodProvider,
)
from services.terrain_risk_providers.ardswc_slope_hazard_provider import (
    TileCoord,
    dedupe_features,
    match_feature,
    tiles_for_radius,
)


def test_non_mvt_providers_return_unavailable_source_metadata_without_external_calls() -> None:
    terrain = NlscTerrainProvider().analyze(25, 121, 500)
    assert terrain["status"] == "unavailable"

    flood = WraFloodProvider().analyze(25, 121, 500)
    assert flood["status"] == "unavailable"

    geology = GeologyCloudProvider().analyze(25, 121, 500)
    assert {"geological_sensitivity", "liquefaction", "active_fault"} <= set(geology)


def test_tile_range_expands_across_radius_boundary() -> None:
    small = tiles_for_radius(25.026, 121.543, 100, zoom=14)
    large = tiles_for_radius(25.026, 121.543, 2000, zoom=14)
    assert len(small) >= 1
    assert len(large) > len(small)
    assert all(isinstance(tile, TileCoord) for tile in large)


def test_line_distance_and_polygon_buffer_intersection() -> None:
    line = {"geometry": [[121.540, 25.026], [121.546, 25.026]], "_stable_id": "line-1"}
    polygon = {"geometry": [[[121.542, 25.025], [121.544, 25.025], [121.544, 25.027], [121.542, 25.027], [121.542, 25.025]]], "_stable_id": "poly-1"}
    assert match_feature(line, 25.026, 121.543, 50, "line")
    assert match_feature(polygon, 25.026, 121.543, 50, "polygon")


def test_feature_dedup_prefers_stable_official_fields() -> None:
    rows = [
        {"properties": {"OBJECTID": "A1"}, "geometry": [[121.54, 25.02]], "id": None},
        {"properties": {"OBJECTID": "A1"}, "geometry": [[121.55, 25.03]], "id": None},
        {"properties": {"OBJECTID": "A2"}, "geometry": [[121.56, 25.04]], "id": None},
    ]
    assert len(dedupe_features(rows)) == 2


def test_successful_no_hit_is_available_and_not_low_level() -> None:
    provider = ArdswcSlopeHazardProvider(
        http_get=lambda url, timeout: b"tile",
        decoder=lambda payload, tile: [],
        use_cache=False,
    )
    result = provider.analyze(25.026, 121.543, 100, include_layers=["debris_flow"])
    assert result["debris_flow"]["status"] == "available"
    assert result["debris_flow"]["matched"] is False
    assert result["debris_flow"]["level"] == "unknown"
    assert result["landslide"]["status"] == "skipped"
    assert result["debris_flow"]["source"]["data_vintage"] == "113年度（官方公開 MVT）"
    assert "limitation" in result["debris_flow"]["source"]


def test_partial_tile_failure_is_limited_and_not_no_hit() -> None:
    calls = {"count": 0}

    def flaky_get(url: str, timeout: float) -> bytes:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("slow tile")
        return b"tile"

    provider = ArdswcSlopeHazardProvider(http_get=flaky_get, decoder=lambda payload, tile: [], use_cache=False)
    result = provider.analyze(25.026, 121.543, 2000, include_layers=["debris_flow"])
    assert result["debris_flow"]["status"] == "limited"
    assert result["debris_flow"]["value"]["sublayers"][0]["status"] in {"limited", "error"}


def test_all_tile_failure_is_error() -> None:
    provider = ArdswcSlopeHazardProvider(
        http_get=lambda url, timeout: (_ for _ in ()).throw(TimeoutError("down")),
        decoder=lambda payload, tile: [],
        use_cache=False,
    )
    result = provider.analyze(25.026, 121.543, 100, include_layers=["landslide"])
    assert result["landslide"]["status"] == "error"
    assert result["landslide"]["matched"] is False


def test_invalid_pbf_is_error_not_no_hit() -> None:
    provider = ArdswcSlopeHazardProvider(
        http_get=lambda url, timeout: b"not-pbf",
        decoder=lambda payload, tile: (_ for _ in ()).throw(ValueError("bad pbf")),
        use_cache=False,
    )
    result = provider.analyze(25.026, 121.543, 100, include_layers=["debris_flow"])
    assert result["debris_flow"]["status"] == "error"
    assert result["debris_flow"]["matched"] is False


def test_debris_affect_overlap_returns_high() -> None:
    def decoder(payload: bytes, tile: TileCoord) -> list[dict]:
        return [{"properties": {"OBJECTID": "hit"}, "geometry": [[[121.542, 25.025], [121.544, 25.025], [121.544, 25.027], [121.542, 25.027], [121.542, 25.025]]]}]

    provider = ArdswcSlopeHazardProvider(http_get=lambda url, timeout: b"tile", decoder=decoder, use_cache=False)
    result = provider.analyze(25.026, 121.543, 100, include_layers=["debris_flow"])
    assert result["debris_flow"]["matched"] is True
    assert result["debris_flow"]["level"] == "high"
