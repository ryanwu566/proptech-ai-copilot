"""FastAPI smoke tests for the productized demo backend."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_case_can_be_analyzed_and_reported() -> None:
    case = client.get("/demo-cases").json()[0]
    result = client.post("/taxoracle/analyze", json=case)
    report = client.post("/taxoracle/report", json=case)
    assert result.status_code == 200
    assert result.json()["eligibility_status"] == "eligible"
    assert report.status_code == 200
    assert "TaxOracle" in report.text


def test_market_insight_query() -> None:
    response = client.post("/market-insights/query", json={"city": "台北市", "district": "信義區"})
    assert response.status_code == 200
    assert len(response.json()["trend"]) == 6
