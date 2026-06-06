"""Map Insight Lite mock service tests."""

from services.adapters.geocoding_adapter import GoogleGeocodingAdapter
from services.adapters.google_places_adapter import GooglePlacesAdapter
from services.map_service import (
    build_livability_scoring,
    get_map_insight,
    get_nearby_places,
    get_google_health,
    list_poi_categories,
    list_regions,
    load_map_data,
    search_location,
)


def test_map_regions_and_categories_load() -> None:
    assert len(list_regions()) >= 3
    assert {item["category"] for item in list_poi_categories()} == {"transport", "school", "park", "medical", "shopping", "food"}


def test_mock_address_search_matches_road() -> None:
    result = search_location("台北市大安區和平東路二段")
    assert result["matched"] is True
    assert result["district"] == "大安區"
    assert result["source"] == "mock"
    assert result["confidence"] == "mock"
    assert result["formatted_address"]


def test_map_insight_has_stable_layers_and_score() -> None:
    result = get_map_insight("新北市板橋區文化路二段")
    assert result is not None
    assert 0 <= result["livability_score"] <= 100
    assert len(result["poi_layers"]) == 5


def test_unknown_map_query_is_friendly() -> None:
    assert search_location("不存在的地址")["matched"] is False
    assert get_map_insight("不存在的地址") is None


def test_nearby_without_google_key_uses_mock_fallback() -> None:
    result = get_nearby_places(
        25.0254,
        121.5434,
        800,
        ["transport", "food", "shopping"],
        adapter=GooglePlacesAdapter(api_key=""),
    )
    assert result["source"] == "mock"
    assert 0 <= result["livability_score"] <= 100
    assert {row["category"] for row in result["categories"]} == {"transport", "food", "shopping"}
    assert result["categories"][0]["places"][0]["source"] == "mock"
    assert {item["category"] for item in result["category_scores"]} == {"transport", "school", "park", "medical", "shopping", "food"}
    assert result["livability_level"] in {"極佳", "良好", "普通", "偏弱", "不足"}
    assert all({"level", "poi_count", "nearest_distance_m", "explanation"} <= set(item) for item in result["category_scores"])
    assert len(result["nearest_places"]) == 3
    assert result["recommendation_text"]
    assert result["score_explanation"]
    assert result["scoring_criteria"]["category_weights"]["transport"] == 25
    assert result["scoring_criteria"]["distance_bands"][0] == {"range": "0-300m", "weight": "high"}


def test_nearby_google_error_uses_mock_fallback() -> None:
    class FailingGoogleAdapter:
        available = True

        def nearby(self, *args, **kwargs):
            import httpx

            raise httpx.TimeoutException("timeout")

    result = get_nearby_places(25.0254, 121.5434, 800, ["transport"], adapter=FailingGoogleAdapter())
    assert result["source"] == "mock"


def test_each_mock_region_has_complete_nearby_places() -> None:
    required = {"name", "category", "lat", "lng", "address", "rating", "user_rating_count", "business_status", "distance_m", "source"}
    for region in load_map_data()["regions"]:
        assert len(region["nearby_places"]) >= 20
        assert all(required <= set(place) for place in region["nearby_places"])


def test_distance_tiers_affect_category_score() -> None:
    scoring = build_livability_scoring(
        [
            {
                "category": "transport",
                "places": [
                    {"name": "近站", "distance_m": 200, "category": "transport"},
                    {"name": "中距離站", "distance_m": 500, "category": "transport"},
                    {"name": "範圍外", "distance_m": 900, "category": "transport"},
                ],
            }
        ],
        1000,
    )
    assert scoring["category_score_map"]["transport"] == 39
    assert scoring["nearest_places"][0]["name"] == "近站"


def test_google_geocoding_is_used_first_when_available(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"results": [{"place_id": "google-101", "formatted_address": "台北市信義區台北101", "geometry": {"location": {"lat": 25.033, "lng": 121.5654}}}]}

    monkeypatch.setattr("services.adapters.geocoding_adapter.httpx.get", lambda *args, **kwargs: Response())
    result = search_location("台北101", adapter=GoogleGeocodingAdapter(api_key="configured-for-test"))
    assert result["source"] == "google_geocoding"
    assert result["confidence"] == "high"
    assert result["place_id"] == "google-101"


def test_google_health_without_key_is_safe_mock(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.setattr("services.map_service.GOOGLE_HEALTH_CACHE", None)
    result = get_google_health()
    assert result["google_key_configured"] is False
    assert result["mode"] == "mock"
    assert result["safe_message"] == "目前使用展示資料"
