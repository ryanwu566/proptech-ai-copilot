from fastapi.testclient import TestClient
from backend.api_main import app

client = TestClient(app)


def test_bank_rate_api_contract(monkeypatch) -> None:
    from services import bank_rate_service

    # Contract tests must not contact CBC or depend on a previous test's cache.
    monkeypatch.setattr(bank_rate_service, "_CACHE", None)
    monkeypatch.setattr(bank_rate_service, "_fetch", lambda: [{
        "bank_code": "0040000", "bank_name": "臺灣銀行", "rate_name": "指數房貸",
        "variable_rate": 1.72, "effective_date": "2026-05-01",
    }])
    institutions = client.get("/bank-rates/institutions")
    assert institutions.status_code == 200 and institutions.json()["institutions"]
    assert institutions.json()["source"] == "central_bank_opendata"
    code = institutions.json()["institutions"][0]["bank_code"]
    result = client.get("/bank-rates/mortgage", params={"bank_code": code})
    assert result.status_code == 200
    assert {"items", "summary_rate", "notes"} <= set(result.json())
    assert result.json()["source"] == "central_bank_opendata"
    assert result.json()["bank_code"] == "0040000"
    assert result.json()["summary_rate"] == 1.72
