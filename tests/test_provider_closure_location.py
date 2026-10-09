"""Exercise Places-to-Location evidence semantics without external requests."""

from services.location_insight_service import POI_CATEGORIES, analyze_location
from services.map_service import get_nearby_places


class Places:
    available = True

    def __init__(self, failed=(), empty=()):
        self.failed = set(failed)
        self.empty = set(empty)

    def nearby(self, lat, lng, radius_m, category, language_code):
        if category in self.failed:
            raise TimeoutError("private-provider-detail")
        if category in self.empty:
            return []
        types = {"transport": "subway_station", "school": "school", "park": "park", "medical": "hospital", "shopping": "shopping_mall", "food": "restaurant"}
        return [{"place_id": category, "name": category, "category": category, "types": [types[category]], "distance_m": 100, "lat": lat, "lng": lng, "source": "google_places"}]


def location(adapter):
    return analyze_location(latitude=25.03, longitude=121.56, nearby_fetcher=lambda lat, lng, radius, categories: get_nearby_places(lat, lng, radius, categories, adapter=adapter))


def test_partial_places_preserves_successes_and_does_not_score_failed_categories():
    result = location(Places(failed=("school", "medical")))
    assert result["data_quality"]["status"] == "limited"
    assert result["data_quality"]["partial"] is True
    assert result["data_quality"]["coverage"] == {"requested": 6, "successful": 4, "failed": 2}
    assert result["data_quality"]["failed_categories"] == ["school", "medical"]
    assert result["poi_summary"]["school_count"] is None
    assert result["poi_summary"]["medical_count"] is None
    assert result["poi_summary"]["transit_count"] == 1
    assert result["category_scores"]["education_score"] is None
    assert result["location_score"] is None
    assert {item["category"] for item in result["nearest_pois"]} >= {"transport", "park", "shopping"}
    assert "private-provider-detail" not in str(result)


def test_successful_zero_is_evidence_not_category_failure():
    result = location(Places(empty=("school",)))
    assert result["data_quality"]["status"] == "good"
    assert result["poi_summary"]["school_count"] == 0
    assert result["data_quality"]["category_status"]["school"]["status"] == "available"
    assert result["data_quality"]["coverage"]["successful"] == 6


def test_all_successful_zero_queries_remain_covered():
    result = location(Places(empty=POI_CATEGORIES))
    assert result["data_quality"]["status"] == "good"
    assert result["data_quality"]["partial"] is False
    assert result["poi_summary"]["school_count"] == 0
    assert result["location_score"] is None


def test_six_successes_preserve_google_source_and_query_time():
    result = location(Places())
    assert result["data_quality"]["status"] == "good"
    assert result["data_quality"]["source"] == "google_places"
    assert result["data_quality"]["checked_at"]
    assert result["location_score"] is None
    assert result["category_scores"]["risk_score"] is None


def test_total_failure_retains_failure_categories_when_demo_fallback_exists():
    result = location(Places(failed=POI_CATEGORIES))
    assert result["data_quality"]["status"] == "limited"
    assert result["data_quality"]["source"] == "mock"
    assert result["data_quality"]["coverage"]["successful"] == 0
    assert result["data_quality"]["failed_categories"] == POI_CATEGORIES
    assert all(item["source"] == "mock" for item in result["nearest_pois"])
    assert all(value["status"] == "error" for value in result["data_quality"]["category_status"].values())


def test_no_provider_result_has_unknown_counts():
    result = analyze_location(latitude=25.03, longitude=121.56, nearby_fetcher=lambda *args: {"source": "unavailable", "categories": []})
    assert result["data_quality"]["status"] == "unavailable"
    assert result["poi_summary"]["transit_count"] is None
    assert result["category_scores"]["transit_score"] is None
