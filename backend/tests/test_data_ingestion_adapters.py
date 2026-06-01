from app.data_ingestion.bank_rates import MockBankRatesAdapter
from app.data_ingestion.cbc_policy import MockCbcPolicyAdapter
from app.data_ingestion.judicial import MockJudicialAdapter
from app.data_ingestion.legal import MockLegalAdapter
from app.data_ingestion.real_price import MockRealPriceAdapter


def test_real_price_mock_adapter_returns_source_log() -> None:
    result = MockRealPriceAdapter().fetch_transactions(city="Taipei", district="Da-an")

    assert result.records
    assert result.source_log.source_name == "real_price_registry"
    assert result.source_log.retrieval_mode == "mock"
    assert result.source_log.record_count == len(result.records)


def test_judicial_mock_adapter_returns_source_log() -> None:
    result = MockJudicialAdapter().search_cases(
        property_address="Taipei",
        owner_name="Owner",
        keywords=["occupation"],
    )

    assert result.records
    assert result.source_log.source_type == "judicial_case"
    assert result.source_log.retrieval_mode == "mock"
    assert result.source_log.query["keywords"] == ["occupation"]


def test_legal_mock_adapter_returns_source_log() -> None:
    result = MockLegalAdapter().fetch_legal_references(topic="title_dispute")

    assert result.records
    assert result.source_log.source_type == "legal_reference"
    assert result.source_log.retrieval_mode == "mock"


def test_cbc_policy_mock_adapter_returns_source_log() -> None:
    result = MockCbcPolicyAdapter().fetch_credit_controls(region="Taipei")

    assert result.records
    assert result.source_log.source_type == "credit_policy"
    assert result.source_log.retrieval_mode == "mock"


def test_bank_rates_mock_adapter_returns_source_log() -> None:
    result = MockBankRatesAdapter().fetch_mortgage_rates(bank_code="BANK")

    assert result.records
    assert result.source_log.source_type == "bank_rate"
    assert result.source_log.retrieval_mode == "mock"
    assert result.to_dict()["source_log"]["requested_at"]
