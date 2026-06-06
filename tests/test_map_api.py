"""Map Insight Lite FastAPI endpoint tests."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_map_metadata_endpoints() -> None:
    assert client.get("/map/regions").status_code == 200
    assert client.get("/map/poi-categories").status_code == 200


def test_map_search_and_insight_endpoints() -> None:
    payload = {"query": "台北市大安區和平東路二段"}
    search = client.post("/map/search", json=payload)
    insight = client.post("/map/insight", json=payload)
    assert search.status_code == 200
    assert search.json()["matched"] is True
    assert insight.status_code == 200
    assert insight.json()["source"] == "mock"


def test_map_search_can_feed_nearby_mock_fallback(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    search = client.post("/map/search", json={"query": "台北市大安區和平東路二段"})
    center = search.json()["center"]
    nearby = client.post(
        "/map/nearby",
        json={
            "lat": center["lat"],
            "lng": center["lng"],
            "radius_m": 800,
            "categories": ["transport", "school", "park", "medical", "shopping", "food"],
            "language_code": "zh-TW",
        },
    )
    assert nearby.status_code == 200
    payload = nearby.json()
    assert payload["source"] == "mock"
    assert len(payload["categories"]) == 6
    assert 0 <= payload["livability_score"] <= 100
