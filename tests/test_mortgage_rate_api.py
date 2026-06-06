"""Mortgage-rate API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_mortgage_rate_endpoint_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.mortgage_rate_service.get_latest_mortgage_rate",
        lambda: {
            "source": "mock", "source_name": "中央銀行 OpenData：五大銀行存放款利率歷史月資料",
            "period": "2025-02", "reference_rate": 2.185, "rate_type": "五大銀行房貸相關月資料",
            "available_fields": [], "notes": ["本資料為月資料，非即時核貸利率", "實際房貸利率仍依銀行、信用條件、擔保品與方案而定"],
            "fetched_at": "2025-02-01T00:00:00+00:00",
        },
    )
    response = client.get("/mortgage-rates/latest")
    assert response.status_code == 200
    assert set(response.json()) == {"source", "source_name", "period", "reference_rate", "rate_type", "available_fields", "notes", "fetched_at"}
