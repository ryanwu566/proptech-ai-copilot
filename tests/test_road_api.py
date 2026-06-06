"""Road selection API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_road_selection_endpoints() -> None:
    assert "台北市" in client.get("/roads/cities").json()["cities"]
    assert "大安區" in client.get("/roads/districts", params={"city": "台北市"}).json()["districts"]
    assert "和平東路二段" in client.get("/roads/roads", params={"city": "台北市", "district": "大安區"}).json()["roads"]


def test_unknown_road_selection_is_friendly() -> None:
    districts = client.get("/roads/districts", params={"city": "不存在城市"}).json()
    roads = client.get("/roads/roads", params={"city": "台北市", "district": "不存在區域"}).json()
    assert districts["districts"] == [] and districts["message"]
    assert roads["roads"] == [] and roads["message"]
