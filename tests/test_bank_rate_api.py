from fastapi.testclient import TestClient
from backend.api_main import app

client = TestClient(app)


def test_bank_rate_api_contract() -> None:
    institutions = client.get("/bank-rates/institutions")
    assert institutions.status_code == 200 and institutions.json()["institutions"]
    code = institutions.json()["institutions"][0]["bank_code"]
    result = client.get("/bank-rates/mortgage", params={"bank_code": code})
    assert result.status_code == 200
    assert {"items", "summary_rate", "notes"} <= set(result.json())
