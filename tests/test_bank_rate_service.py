import httpx

from services.bank_rate_service import get_bank_mortgage_rates, list_institutions, normalize_bank_rates


def test_bank_rate_fallback() -> None:
    def fail():
        raise httpx.TimeoutException("timeout")
    assert list_institutions(fail)["source"] == "mock"
    assert get_bank_mortgage_rates("0040000", fail)["items"]


def test_bank_rate_normalization() -> None:
    rows = normalize_bank_rates([{"金融機構代號": "0040000", "金融機構名稱": "臺灣銀行", "牌告利率名稱": "指數房貸指標利率", "機動利率": "1.73", "生效日期": "2026-05-01"}])
    assert rows[0]["variable_rate"] == 1.73
