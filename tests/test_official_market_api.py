"""API-level safety checks for the official market read surface."""

from fastapi.testclient import TestClient

from backend.api_main import app


def test_methodology_is_safe_and_not_an_appraisal() -> None:
    response = TestClient(app).get("/market-insights/methodology")
    assert response.status_code == 200
    payload = response.json()
    assert payload["methodology_version"] == "median-quartiles-v1"
    assert "appraisal" in payload["disclaimer"]
    assert "database_url" not in payload


def test_comparables_fail_closed_without_runtime_database(monkeypatch) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
    response = TestClient(app).post("/market-insights/comparables", json={"county": "synthetic", "district": "synthetic"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "unavailable"
    assert payload["comparables"] == []
    assert "raw" not in response.text.lower()
