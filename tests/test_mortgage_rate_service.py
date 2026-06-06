"""Mortgage-rate reference service tests."""

import httpx

from services.mortgage_rate_service import get_latest_mortgage_rate, parse_latest_rate


def test_parse_latest_central_bank_rate() -> None:
    result = parse_latest_rate({"data": [{"年月": "2025-01", "指數房貸利率": "2.10"}, {"年月": "2025-02", "指數房貸利率": "2.20"}]})
    assert result["source"] == "central_bank_opendata"
    assert result["period"] == "2025-02"
    assert result["reference_rate"] == 2.2
    assert "指數房貸利率" in result["available_fields"]


def test_api_failure_returns_mock_fallback() -> None:
    def fail():
        raise httpx.TimeoutException("timeout")

    result = get_latest_mortgage_rate(fetcher=fail)
    assert result["source"] == "mock"
    assert result["reference_rate"] > 0
    assert len(result["notes"]) == 2
