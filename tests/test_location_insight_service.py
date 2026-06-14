"""Location insight service tests using mocked map capabilities."""

from services.location_insight_service import analyze_location


def nearby(*args):
    del args
    scores = {"transport": 80, "shopping": 70, "food": 60, "school": 50, "park": 40, "medical": 30}
    return {
        "source": "google_places",
        "categories": [{"category": key, "count": index + 1} for index, key in enumerate(scores)],
        "category_score_map": scores,
        "nearest_places": [{"category": "transport", "name": "捷運站", "distance_m": 250, "source": "google_places"}],
    }


def test_coordinates_take_priority_and_produce_explainable_score() -> None:
    result = analyze_location(latitude=25.03, longitude=121.56, nearby_fetcher=nearby)
    assert result["resolved_location"]["geocoding_confidence"] == "provided_coordinates"
    assert 0 <= result["location_score"] <= 100
    assert result["category_scores"]["transit_score"] == 80
    assert result["category_scores"]["convenience_score"] == 65
    assert result["data_quality"]["status"] == "good"


def test_road_query_can_resolve_location() -> None:
    searcher = lambda query: {"matched": True, "center": {"lat": 25.0, "lng": 121.5}, "formatted_address": query, "confidence": "mock"}
    result = analyze_location(city="台北市", district="大安區", road="和平東路二段", searcher=searcher, nearby_fetcher=nearby)
    assert result["resolved_location"]["address_label"] == "台北市大安區和平東路二段"
    assert result["poi_summary"]["transit_count"] == 1


def test_failed_location_is_friendly_and_stable() -> None:
    result = analyze_location(address="不存在", searcher=lambda query: {"matched": False, "center": None})
    assert result["location_score"] is None
    assert result["data_quality"]["status"] == "unavailable"
    assert result["weaknesses"]


def test_unavailable_poi_source_does_not_crash() -> None:
    empty = lambda *args: {"source": "unavailable", "categories": [], "category_score_map": {}, "nearest_places": []}
    result = analyze_location(latitude=25, longitude=121, nearby_fetcher=empty)
    assert result["location_score"] is None
    assert result["data_quality"]["status"] == "unavailable"
    assert set(result["poi_summary"]) == {"transit_count", "convenience_count", "school_count", "park_count", "medical_count", "risk_facility_count"}


def test_failing_poi_source_does_not_crash() -> None:
    def fail(*args):
        raise RuntimeError("source unavailable")

    result = analyze_location(latitude=25, longitude=121, nearby_fetcher=fail)
    assert result["data_quality"]["status"] == "unavailable"


def test_mock_fallback_is_marked_limited() -> None:
    mock = lambda *args: {**nearby(), "source": "mock"}
    result = analyze_location(latitude=25, longitude=121, nearby_fetcher=mock)
    assert result["data_quality"]["status"] == "limited"
    assert any("展示資料" in warning for warning in result["data_quality"]["warnings"])
