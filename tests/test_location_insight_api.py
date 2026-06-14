"""Location insight API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_location_insight_api_with_coordinates(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.location_insight_service.get_nearby_places",
        lambda *args: {"source": "unavailable", "categories": [], "category_score_map": {}, "nearest_places": []},
    )
    response = client.post("/location/insight", json={"latitude": 25.03, "longitude": 121.56})
    assert response.status_code == 200
    result = response.json()
    assert {"resolved_location", "location_score", "category_scores", "poi_summary", "strengths", "weaknesses", "buyer_fit", "valuation_context", "data_quality", "disclaimer"} <= set(result)


def test_location_insight_api_rejects_partial_coordinates() -> None:
    assert client.post("/location/insight", json={"latitude": 25.03}).status_code == 422


def test_location_insight_api_returns_unavailable_for_unknown_query(monkeypatch) -> None:
    monkeypatch.setattr("services.location_insight_service.search_location", lambda query: {"matched": False, "center": None})
    result = client.post("/location/insight", json={"address": "不存在"}).json()
    assert result["data_quality"]["status"] == "unavailable"
    assert result["location_score"] is None
