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


def test_market_insight_query(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda city, district="", period=None: {
            "city": city,
            "county": city,
            "district": district,
            "period": "2025-02",
            "average_unit_price": 70.0,
            "avg_price_per_ping": 70.0,
            "transaction_count": 4,
            "transaction_volume": 4,
            "record_count": 4,
            "history": [{"period": "2025-02", "average_unit_price": 70.0, "transaction_count": 4}],
            "summary": "direct aggregate ready",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "coverage_status": "partial",
            "data_status": "available",
            "caveat": "market caveat",
            "disclaimer": "market caveat",
        },
    )

    response = client.post("/market-insights/query", json={"city": "Demo County", "district": "Demo District"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "available"
    assert payload["avg_price_per_ping"] == 70.0
    assert payload["transaction_volume"] == 4
    assert "raw_error" not in payload
