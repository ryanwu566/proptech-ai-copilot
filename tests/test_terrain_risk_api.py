"""Terrain risk API tests."""

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def layer(key: str, label: str, status: str = "available", level: str = "unknown", matched: bool = False) -> dict:
    return {
        "key": key,
        "label": label,
        "status": status,
        "level": level,
        "matched": matched,
        "distance_m": 150 if matched else None,
        "value": None,
        "explanation": f"{label} API fixture result",
        "source": {"name": label, "agency": "fixture", "source_url": "https://example.test", "status": status},
    }


class ApiTerrainProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return {
            "status": "available",
            "slope_value": 7,
            "slope_class": "gentle",
            "elevation_m": 20,
            "explanation": "Terrain API fixture.",
            "source": {"name": "fixture terrain", "agency": "fixture", "source_url": "https://example.test", "status": "available"},
        }


class ApiSlopeHazardProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int, include_layers=None) -> dict:
        rows = {
            "landslide": layer("landslide", "fixture landslide", "available", "unknown", False),
            "debris_flow": layer("debris_flow", "fixture debris flow", "available", "unknown", False),
        }
        if include_layers is None:
            return rows
        return {key: rows[key] for key in include_layers}


class ApiFloodProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return layer("flood", "fixture flood", "available", "unknown", False)


class ApiGeologyProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return {
            "geological_sensitivity": layer("geological_sensitivity", "fixture geological sensitivity", "available", "unknown", False),
            "liquefaction": layer("liquefaction", "fixture liquefaction", "available", "unknown", False),
            "active_fault": layer("active_fault", "fixture active fault", "available", "unknown", False),
        }


@pytest.fixture(autouse=True)
def isolate_terrain_risk_providers(monkeypatch):
    monkeypatch.setattr(
        "services.terrain_risk_service._default_providers",
        lambda: {
            "terrain": ApiTerrainProvider(),
            "slope_hazard": ApiSlopeHazardProvider(),
            "flood": ApiFloodProvider(),
            "geology": ApiGeologyProvider(),
        },
    )


def test_terrain_risk_endpoint_exists_and_returns_stable_contract() -> None:
    response = client.post("/terrain-risk/analyze", json={"latitude": 25.026, "longitude": 121.543})
    assert response.status_code == 200
    payload = response.json()
    assert {"input", "resolved_location", "overall", "terrain", "hazards", "risk_factors", "missing_sources", "recommended_checks", "map_layers", "data_quality", "disclaimer"} <= set(payload)
    assert payload["overall"]["level"] in {"low", "medium", "high", "unknown"}
    assert "不代表建築結構鑑定" in payload["disclaimer"]


def test_terrain_risk_default_radius_and_include_layer_filter() -> None:
    payload = client.post("/terrain-risk/analyze", json={"latitude": 25.026, "longitude": 121.543, "include_layers": ["debris_flow"]}).json()
    assert payload["input"]["radius_m"] == 500
    assert payload["input"]["include_layers"] == ["debris_flow"]
    assert payload["hazards"]["landslide"]["status"] == "skipped"


def test_terrain_risk_rejects_partial_coordinates() -> None:
    assert client.post("/terrain-risk/analyze", json={"latitude": 25.026}).status_code == 422


def test_terrain_risk_rejects_radius_outside_limits() -> None:
    assert client.post("/terrain-risk/analyze", json={"latitude": 25.026, "longitude": 121.543, "radius_m": 99}).status_code == 422
    assert client.post("/terrain-risk/analyze", json={"latitude": 25.026, "longitude": 121.543, "radius_m": 2001}).status_code == 422


def test_terrain_risk_geocoding_failure_returns_422(monkeypatch) -> None:
    monkeypatch.setattr("services.terrain_risk_service.search_location", lambda query: {"matched": False, "center": None})
    response = client.post("/terrain-risk/analyze", json={"address": "不存在"})
    assert response.status_code == 422
    assert "無法定位" in response.json()["detail"]
