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
