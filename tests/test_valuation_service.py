from collections import Counter
from pathlib import Path

from services.valuation_service import (
    MockFallbackProvider,
    SampleValuationProvider,
    estimate_property,
    get_valuation_data_status,
    get_valuation_provider,
    load_transactions,
)
from services.valuation_providers.postgres_provider import PostgresValuationProvider


PAYLOAD = {
    "city": "台北市",
    "district": "大安區",
    "road": "和平東路二段",
    "building_type": "住宅大樓",
    "area_ping": 30,
    "building_age_years": 15,
    "floor": 8,
    "lat": 25.0254,
    "lng": 121.5434,
}


def test_sample_provider_and_data_status() -> None:
    provider = get_valuation_provider(database_url="", sqlite_path=Path("missing.sqlite"))
    assert isinstance(provider, SampleValuationProvider)
    status = get_valuation_data_status()
    assert status["active_source"] == "real_price_sample"
    assert status["coverage"]["records_count"] >= 60
    assert status["is_demo_data"] is True


def test_postgres_placeholder_falls_back_without_crashing(monkeypatch) -> None:
    PostgresValuationProvider._availability_cache.clear()
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: (_ for _ in ()).throw(ConnectionError("offline")))
    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://configured-but-not-enabled")
    provider = get_valuation_provider(sqlite_path=Path("missing.sqlite"))
    assert isinstance(provider, SampleValuationProvider)


def test_missing_sqlite_and_sample_use_mock_fallback() -> None:
    provider = get_valuation_provider(database_url="", sqlite_path=Path("missing.sqlite"), sample_path=Path("missing.csv"))
    assert isinstance(provider, MockFallbackProvider)
    assert provider.load_transactions()


def test_estimate_returns_level_status_and_comparables() -> None:
    result = estimate_property({**PAYLOAD, "address_text": "和平綠境"})
    assert result["estimate_total_price"] > 0
    assert result["price_range"]["low"] <= result["price_range"]["mid"] <= result["price_range"]["high"]
    assert result["estimate_level"] == "community"
    assert result["matched_community"]["community_name"] == "和平綠境"
    assert result["data_status"]["active_source"] == "real_price_sample"
    assert result["confidence_reason"]


def test_unknown_community_falls_back_to_road_or_district() -> None:
    result = estimate_property({**PAYLOAD, "road": "和平東路二段", "address_text": "不明社區"})
    assert result["estimate_level"] == "road"
    assert result["matched_community"] is None
    assert result["comparables"]


def test_sample_has_three_demo_regions_with_at_least_twenty_rows_each() -> None:
    rows = load_transactions()
    counts = Counter((row["city"], row["district"], row["road"]) for row in rows)
    assert len(rows) >= 60
    assert counts[("台北市", "大安區", "和平東路二段")] >= 20
    assert counts[("台北市", "信義區", "松仁路")] >= 20
    assert counts[("新北市", "板橋區", "文化路二段")] >= 20
