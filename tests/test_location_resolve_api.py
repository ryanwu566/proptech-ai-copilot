"""Trusted address resolve API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


SAFE_KEYS = {
    "status",
    "source",
    "formatted_address",
    "latitude",
    "longitude",
    "confidence",
    "message",
}


def test_location_resolve_rejects_blank_address() -> None:
    response = client.post("/location/resolve", json={"address": " \n\t "})

    assert response.status_code == 422


def test_location_resolve_returns_only_safe_fields(monkeypatch) -> None:
    def fake_resolve_address(address: str) -> dict[str, object]:
        assert address == "臺北市信義區市府路1號"
        return {
            "status": "resolved",
            "source": "google",
            "formatted_address": "測試格式化地址",
            "latitude": 25.03,
            "longitude": 121.56,
            "confidence": "high",
            "message": "已取得可信位置（Google）。",
            "raw_payload": {"token": "must not leak"},
            "api_key": "must not leak",
            "provider_raw_error": "must not leak",
        }

    monkeypatch.setattr("services.location_resolver.resolve_address", fake_resolve_address)

    response = client.post("/location/resolve", json={"address": "臺北市信義區市府路1號"})

    assert response.status_code == 200
    result = response.json()
    assert set(result) == SAFE_KEYS
    assert result["status"] == "resolved"
    assert result["source"] == "google"
    serialized = str(result)
    assert "raw_payload" not in serialized
    assert "api_key" not in serialized
    assert "provider_raw_error" not in serialized
    assert "must not leak" not in serialized
