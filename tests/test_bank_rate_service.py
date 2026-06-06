import httpx

from services.bank_rate_service import get_bank_mortgage_rates, list_institutions, normalize_bank_rates


def test_bank_rate_fallback_has_broad_institution_list() -> None:
    def fail():
        raise httpx.TimeoutException("timeout")

    result = list_institutions(fail)
    assert result["source"] == "mock"
    assert result["institution_count"] >= 10
    assert get_bank_mortgage_rates("0040000", fail)["items"]


def test_bank_rate_normalization_from_plain_record() -> None:
    rows = normalize_bank_rates(
        [
            {
                "金融機構代號": "0040000",
                "金融機構名稱": "臺灣銀行",
                "牌告利率名稱": "指數型房貸參考利率",
                "機動利率": "1.73",
                "生效日期": "2026-05-01",
            }
        ]
    )
    assert rows[0]["variable_rate"] == 1.73


def test_bank_rate_normalization_from_data_value_string() -> None:
    payload = {
        "Data": [
            {
                "value": (
                    "0資料日期,2026-05-01,1金融機構代號,0040000,"
                    "2金融機構名稱,臺灣銀行,3牌告利率名稱,房屋貸款基準利率,"
                    "12固定利率,2.10,13機動利率,1.73"
                )
            }
        ]
    }
    rows = normalize_bank_rates(payload)
    assert rows == [
        {
            "bank_code": "0040000",
            "bank_name": "臺灣銀行",
            "rate_name": "房屋貸款基準利率",
            "fixed_rate": 2.1,
            "variable_rate": 1.73,
            "effective_date": "2026-05-01",
        }
    ]
