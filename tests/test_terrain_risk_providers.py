"""Terrain risk provider contract tests."""

import json
import threading
import time
from urllib.parse import parse_qs, urlsplit

import pytest

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


def liquefaction_geojson(*, contains_point: bool = False, geometry_type: str = "Polygon") -> bytes:
    features = []
    if contains_point:
        polygon = [[[120.999, 24.999], [121.001, 24.999], [121.001, 25.001], [120.999, 25.001], [120.999, 24.999]]]
        coordinates = polygon if geometry_type == "Polygon" else [polygon]
        features.append({
            "type": "Feature",
            "properties": {"分級": "測試潛勢", "classify": "fixture", "area": "fixture"},
            "geometry": {"type": geometry_type, "coordinates": coordinates},
        })
    return json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False).encode("utf-8")


def query_params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


@pytest.mark.parametrize(
    ("area_hint", "expected_area"),
    [
        ("臺北市", "臺北"),
        ("新北市", "臺北"),
        ("新竹縣", "新竹"),
    ],
)
def test_liquefaction_routes_only_catalog_documented_city_areas(area_hint: str, expected_area: str) -> None:
    calls: list[str] = []

    def fake_get(url: str, timeout: float) -> bytes:
        calls.append(url)
        return liquefaction_geojson()

    result = GeologyCloudProvider(http_get=fake_get).analyze(
        25.0,
        121.0,
        500,
        area_hint=area_hint,
        include_layers=["liquefaction"],
    )

    assert result["liquefaction"]["status"] == "available"
    assert [query_params(url)["area"] for url in calls] == [[expected_area]] * 3


def test_liquefaction_queries_only_documented_bounded_parameters() -> None:
    calls: list[tuple[str, float]] = []

    def fake_get(url: str, timeout: float) -> bytes:
        calls.append((url, timeout))
        return liquefaction_geojson()

    GeologyCloudProvider(http_get=fake_get).analyze(
        25.0,
        121.0,
        500,
        area_hint="臺北市",
        include_layers=["liquefaction"],
    )

    assert len(calls) == 3
    assert all(timeout <= 5 for _, timeout in calls)
    assert {query_params(url)["classify"][0] for url, _ in calls} == {"低潛勢", "中潛勢", "高潛勢"}
    assert all(set(query_params(url)) == {"area", "classify", "bbox"} for url, _ in calls)
    assert all(len(query_params(url)["bbox"][0].split(",")) == 4 for url, _ in calls)


@pytest.mark.parametrize("area_hint", ["基隆市", "嘉義市", "恆春鎮", ""])
def test_liquefaction_without_unambiguous_catalog_city_fails_closed(area_hint: str) -> None:
    calls: list[str] = []
    provider = GeologyCloudProvider(http_get=lambda url, timeout: calls.append(url) or liquefaction_geojson())

    result = provider.analyze(25.0, 121.0, 500, area_hint=area_hint or None, include_layers=["liquefaction"])

    assert calls == []
    assert result["liquefaction"]["status"] == "unavailable"
    assert result["liquefaction"]["level"] == "unknown"


@pytest.mark.parametrize(
    ("official_classification", "expected_level"),
    [("高潛勢", "high"), ("中潛勢", "medium"), ("低潛勢", "low")],
)
def test_liquefaction_polygon_hit_maps_official_classification(
    official_classification: str,
    expected_level: str,
) -> None:
    def fake_get(url: str, timeout: float) -> bytes:
        return liquefaction_geojson(contains_point=query_params(url)["classify"] == [official_classification])

    result = GeologyCloudProvider(http_get=fake_get).analyze(
        25.0,
        121.0,
        500,
        area_hint="臺北市",
        include_layers=["liquefaction"],
    )["liquefaction"]

    assert result["status"] == "available"
    assert result["matched"] is True
    assert result["level"] == expected_level
    assert result["value"]["official_classification"] == official_classification


def test_liquefaction_multipolygon_hit_is_supported() -> None:
    def fake_get(url: str, timeout: float) -> bytes:
        return liquefaction_geojson(
            contains_point=query_params(url)["classify"] == ["高潛勢"],
            geometry_type="MultiPolygon",
        )

    result = GeologyCloudProvider(http_get=fake_get).analyze(
        25.0,
        121.0,
        500,
        area_hint="臺北市",
        include_layers=["liquefaction"],
    )["liquefaction"]

    assert result["matched"] is True
    assert result["level"] == "high"


def test_liquefaction_complete_three_class_no_hit_is_unknown_not_low() -> None:
    result = GeologyCloudProvider(http_get=lambda url, timeout: liquefaction_geojson()).analyze(
        25.0,
        121.0,
        500,
        area_hint="臺北市",
        include_layers=["liquefaction"],
    )["liquefaction"]

    assert result["status"] == "available"
    assert result["matched"] is False
    assert result["level"] == "unknown"
    assert "不代表" in result["explanation"]


def test_liquefaction_one_class_failure_is_limited_and_never_low() -> None:
    def fake_get(url: str, timeout: float) -> bytes:
        if query_params(url)["classify"] == ["中潛勢"]:
            raise TimeoutError("official API timed out")
        return liquefaction_geojson()

    result = GeologyCloudProvider(http_get=fake_get).analyze(
        25.0,
        121.0,
        500,
        area_hint="臺北市",
        include_layers=["liquefaction"],
    )["liquefaction"]

    assert result["status"] == "limited"
    assert result["matched"] is False
    assert result["level"] == "unknown"
    assert result["source"]["official_classification"] == "查詢不完整"


@pytest.mark.parametrize(
    "bad_payload",
    [b'{"type":"FeatureCollection","features":', b"x" * 2_000_001],
    ids=["malformed-geojson", "oversized-response"],
)
def test_liquefaction_invalid_official_response_fails_safely(bad_payload: bytes) -> None:
    def fake_get(url: str, timeout: float) -> bytes:
        if query_params(url)["classify"] == ["高潛勢"]:
            return bad_payload
        return liquefaction_geojson()

    result = GeologyCloudProvider(http_get=fake_get).analyze(
        25.0,
        121.0,
        500,
        area_hint="臺北市",
        include_layers=["liquefaction"],
    )["liquefaction"]

    assert result["status"] == "limited"
    assert result["matched"] is False
    assert result["level"] == "unknown"


def test_liquefaction_excessive_feature_count_fails_safely() -> None:
    feature = {
        "type": "Feature",
        "properties": {"classify": "fixture"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[120.0, 24.0], [120.001, 24.0], [120.001, 24.001], [120.0, 24.0]]],
        },
    }
    excessive = json.dumps({"type": "FeatureCollection", "features": [feature] * 1001}).encode("utf-8")

    def fake_get(url: str, timeout: float) -> bytes:
        return excessive if query_params(url)["classify"] == ["高潛勢"] else liquefaction_geojson()

    result = GeologyCloudProvider(http_get=fake_get).analyze(
        25.0,
        121.0,
        500,
        area_hint="臺北市",
        include_layers=["liquefaction"],
    )["liquefaction"]

    assert result["status"] == "limited"
    assert result["matched"] is False
    assert result["level"] == "unknown"


def test_geology_provider_skips_http_when_liquefaction_not_requested() -> None:
    calls: list[str] = []
    result = GeologyCloudProvider(
        http_get=lambda url, timeout: calls.append(url) or liquefaction_geojson(),
    ).analyze(25.0, 121.0, 500, area_hint="臺北市", include_layers=["geological_sensitivity"])

    assert calls == []
    assert result["geological_sensitivity"]["status"] == "unavailable"
    assert result["active_fault"]["status"] == "unavailable"
    assert result["liquefaction"]["status"] == "unavailable"
    assert result["geological_sensitivity"]["source"]["name"] == "地質雲與地質敏感圖資"
    assert result["active_fault"]["source"]["source_url"] == "https://www.geologycloud.tw/"
    assert "official_classifications" not in result["active_fault"]["source"]


def test_geology_provider_empty_include_layers_skips_all_http() -> None:
    calls: list[str] = []

    GeologyCloudProvider(
        http_get=lambda url, timeout: calls.append(url) or liquefaction_geojson(),
    ).analyze(25.0, 121.0, 500, area_hint="臺北市", include_layers=[])

    assert calls == []


def test_non_mvt_providers_return_unavailable_source_metadata_without_external_calls(monkeypatch) -> None:
    monkeypatch.delenv("NLSC_GATEWAY_BASE_URL", raising=False)
    monkeypatch.delenv("NLSC_GATEWAY_CLIENT_TOKEN", raising=False)
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


def test_nine_tiles_are_fetched_with_bounded_parallelism() -> None:
    probe = {"active": 0, "max_active": 0}
    probe_lock = threading.Lock()

    def tracked_get(url: str, timeout: float) -> bytes:
        with probe_lock:
            probe["active"] += 1
            probe["max_active"] = max(probe["max_active"], probe["active"])
        try:
            time.sleep(0.15)
            return b"tile"
        finally:
            with probe_lock:
                probe["active"] -= 1

    provider = ArdswcSlopeHazardProvider(
        http_get=tracked_get,
        decoder=lambda payload, tile: [],
        tile_workers=99,
        use_cache=False,
    )
    tiles = [TileCoord(14, index, 0) for index in range(15)]
    started = time.perf_counter()
    result = provider._query_mvt_layer("debris_flow", tiles, 25.026, 121.543, 100)
    elapsed = time.perf_counter() - started

    assert elapsed < 0.8
    assert result["status"] == "available"
    assert probe["max_active"] == 6
    assert probe["active"] == 0


def test_tile_cache_hit_avoids_duplicate_fetch() -> None:
    calls = {"count": 0}

    def fake_get(url: str, timeout: float) -> bytes:
        calls["count"] += 1
        return b"tile"

    provider = ArdswcSlopeHazardProvider(http_get=fake_get, decoder=lambda payload, tile: [], use_cache=True)
    tiles = [TileCoord(14, 4242, 2424)]
    first = provider._query_mvt_layer("debris_flow", tiles, 25.026, 121.543, 100)
    second = provider._query_mvt_layer("debris_flow", tiles, 25.026, 121.543, 100)

    assert first["status"] == second["status"] == "available"
    assert first["matched"] is second["matched"] is False
    assert calls["count"] == 1


def test_parallel_tile_completion_preserves_tile_order_and_deduplication() -> None:
    def fake_get(url: str, timeout: float) -> bytes:
        x = int(url.rsplit("/", 1)[-1].split(".", 1)[0])
        time.sleep((3 - x) * 0.03)
        return str(x).encode()

    def decoder(payload: bytes, tile: TileCoord) -> list[dict]:
        feature_id = int(payload.decode())
        return [{
            "properties": {"OBJECTID": feature_id},
            "geometry": [[[121.542, 25.025], [121.544, 25.025], [121.544, 25.027], [121.542, 25.027], [121.542, 25.025]]],
        }]

    provider = ArdswcSlopeHazardProvider(http_get=fake_get, decoder=decoder, use_cache=False)
    tiles = [TileCoord(14, index, 0) for index in range(4)]
    result = provider._query_mvt_layer("debris_affect", tiles, 25.026, 121.543, 100)

    assert result["value"]["feature_ids"] == ["OBJECTID:0", "OBJECTID:1", "OBJECTID:2", "OBJECTID:3"]
