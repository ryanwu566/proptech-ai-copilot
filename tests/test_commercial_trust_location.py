from services.location_insight_service import analyze_location


class NoVillage:
    def resolve(self, **kwargs):
        return {"location": {"status": "unavailable"}, "demographics": {"status": "no_data"}}


def test_missing_risk_source_is_unknown_and_cannot_support_score_or_suitability():
    def nearby(*args):
        categories = ["transport", "school", "park", "medical", "shopping", "food"]
        return {"source": "google_places", "categories": [{"category": key, "count": 3} for key in categories],
                "category_score_map": {key: 90 for key in categories}, "nearest_places": []}
    result = analyze_location(latitude=25, longitude=121, nearby_fetcher=nearby, village_resolver=NoVillage())
    assert result["category_scores"]["risk_score"] is None
    assert result["location_score"] is None
    assert result["poi_summary"]["risk_facility_count"] is None
    assert set(result["buyer_fit"].values()) == {"資料不足"}
    assert "中性 50" not in str(result)
    assert result["poi_summary"]["transit_count"] == 3


def test_unresolved_location_does_not_invent_risk_score():
    result = analyze_location(address="missing", searcher=lambda _: {"matched": False})
    assert result["category_scores"]["risk_score"] is None
