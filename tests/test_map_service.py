"""Map Insight Lite mock service tests."""

from services.map_service import get_map_insight, list_poi_categories, list_regions, search_location


def test_map_regions_and_categories_load() -> None:
    assert len(list_regions()) >= 3
    assert {item["category"] for item in list_poi_categories()} == {"transport", "school", "park", "medical", "commerce"}


def test_mock_address_search_matches_road() -> None:
    result = search_location("台北市大安區和平東路二段")
    assert result["matched"] is True
    assert result["district"] == "大安區"
    assert result["source"] == "mock"


def test_map_insight_has_stable_layers_and_score() -> None:
    result = get_map_insight("新北市板橋區文化路二段")
    assert result is not None
    assert 0 <= result["livability_score"] <= 100
    assert len(result["poi_layers"]) == 5


def test_unknown_map_query_is_friendly() -> None:
    assert search_location("不存在的地址")["matched"] is False
    assert get_map_insight("不存在的地址") is None
