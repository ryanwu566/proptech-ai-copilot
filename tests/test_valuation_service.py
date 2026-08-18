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
    provider = get_valuation_provider(database_url="", sqlite_path=Path("missing.sqlite"), demo_mode=True)
    assert isinstance(provider, SampleValuationProvider)
    status = provider.data_status()
    assert status["active_source"] == "real_price_sample"
    assert status["coverage"]["records_count"] >= 60
    assert status["is_demo_data"] is True


def test_postgres_placeholder_falls_back_without_crashing(monkeypatch) -> None:
    PostgresValuationProvider._availability_cache.clear()
    monkeypatch.setattr(PostgresValuationProvider, "_connect", lambda self: (_ for _ in ()).throw(ConnectionError("offline")))
    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://configured-but-not-enabled")
    provider = get_valuation_provider(sqlite_path=Path("missing.sqlite"))
    assert provider.__class__.__name__ == "UnavailableValuationProvider"


def test_missing_sqlite_and_sample_are_unavailable() -> None:
    provider = get_valuation_provider(database_url="", sqlite_path=Path("missing.sqlite"), sample_path=Path("missing.csv"))
    assert provider.__class__.__name__ == "UnavailableValuationProvider"
    assert provider.load_transactions() == ()


def test_explicit_demo_estimate_returns_demo_status(monkeypatch) -> None:
    monkeypatch.setenv("VALUATION_DEMO_MODE", "true")
    result = estimate_property({**PAYLOAD, "address_text": "和平綠境"})
    assert result["estimate_total_price"] > 0
    assert result["price_range"]["low"] <= result["price_range"]["mid"] <= result["price_range"]["high"]
    assert result["estimate_level"] == "community"
    assert result["matched_community"]["community_name"] == "和平綠境"
    assert result["data_status"]["active_source"] == "real_price_sample"
    assert result["valuation_status"] == "demo"
    assert result["is_actionable"] is False
    assert result["confidence_reason"]


def test_explicit_demo_unknown_community_falls_back_to_road_or_district(monkeypatch) -> None:
    monkeypatch.setenv("VALUATION_DEMO_MODE", "true")
    result = estimate_property({**PAYLOAD, "road": "和平東路二段", "address_text": "不明社區"})
    assert result["estimate_level"] == "road"
    assert result["matched_community"] is None
    assert result["comparables"]


def test_sample_has_three_demo_regions_with_at_least_twenty_rows_each() -> None:
    rows = get_valuation_provider(demo_mode=True).load_transactions()
    counts = Counter((row["city"], row["district"], row["road"]) for row in rows)
    assert len(rows) >= 60
    assert counts[("台北市", "大安區", "和平東路二段")] >= 20
    assert counts[("台北市", "信義區", "松仁路")] >= 20
    assert counts[("新北市", "板橋區", "文化路二段")] >= 20


# ---------------------------------------------------------------------------
# Regression: price_range ordering invariant (mid below P25 / above P75)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch
from services.valuation_providers.postgres_provider import PostgresValuationProvider
from services.valuation_result_contract import validate_official_result


def _fake_postgres_provider(rows, monkeypatch):
    """Create a FakePostgres provider wired into valuation_service."""
    provider = MagicMock(spec=PostgresValuationProvider)
    provider.source = "postgres"
    provider.is_demo_data = False
    provider.is_full_taiwan = False
    provider.available.return_value = True
    provider.data_status.return_value = {
        "active_source": "postgres", "is_demo_data": False, "is_full_taiwan": False,
        "data_composition": "official", "coverage": {"cities": ["屏東縣"], "districts": ["屏東市"], "roads_count": 1, "records_count": len(rows)},
        "last_updated": None, "source_note": "", "user_message": "",
        "freshness_status": "current", "freshness_reason_code": "data_current",
        "freshness_as_of": "2026-08-17", "latest_import_at": "2026-08-01T00:00:00+00:00",
        "latest_import_age_days": 16, "newest_effective_period_lag_months": 1,
        "operator_attention_required": False, "freshness_user_message": "資料為最新狀態。",
        "official_records_count": len(rows), "sample_records_count": 0,
    }
    provider.match_community.return_value = None
    provider.last_query_metadata = {
        "provider_active": "postgres", "candidate_pool_size": len(rows),
        "query_scope": "district_pool", "requested_city": "屏東縣",
        "requested_district": "屏東市", "requested_road": "自由路",
        "db_rows_returned": len(rows), "query_status": "ok",
    }
    provider.query_comparables.return_value = rows
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)
    # Disable GREEN routing for this unit test
    monkeypatch.setenv("PLVR_DATA_BACKEND", "blue")
    return provider


def _official_row(unit_price: float, area: float = 28.0, age: float = 10.0, period: str = "2026-05") -> dict:
    return {
        "transaction_period": period, "city": "屏東縣", "district": "屏東市",
        "road": "自由路", "building_type": "住宅大樓",
        "area_ping": area, "unit_price_per_ping": unit_price,
        "total_price": unit_price * area,
        "building_age_years": age, "floor": 5, "total_floor": 12,
        "source": "official_plvr_opendata",
    }


_PAYLOAD_PINGTUNG = {
    "city": "屏東縣", "district": "屏東市", "road": "自由路",
    "building_type": "住宅大樓", "area_ping": 28.0,
    "building_age_years": 10, "floor": 5,
}


def test_price_range_ordered_when_mid_below_p25(monkeypatch) -> None:
    """When weighted mid < p25, price_range low must still be <= mid <= high.

    Regression: shadow case pingtung-pingtung-ziyou had low > mid because
    the weighted average fell below the unweighted P25.
    """
    # Construct comparables where weighted mid will be pulled below unweighted P25.
    # A few low-scoring rows with very low prices (high weight) + many higher-priced rows
    # will create a weighted mean below P25.
    rows = [
        # High-similarity row (same road, close area/age) with LOW price
        _official_row(22.0, area=28.0, age=10.0),
        _official_row(23.0, area=28.5, age=10.0),
        _official_row(24.0, area=27.5, age=11.0),
        # Lower-similarity rows with HIGHER prices that form the P25-P75 band
        _official_row(30.0, area=35.0, age=5.0),
        _official_row(31.0, area=36.0, age=5.0),
        _official_row(32.0, area=37.0, age=4.0),
        _official_row(33.0, area=38.0, age=6.0),
        _official_row(34.0, area=34.0, age=7.0),
        _official_row(35.0, area=40.0, age=3.0),
        _official_row(36.0, area=42.0, age=2.0),
    ]
    _fake_postgres_provider(rows, monkeypatch)
    result = estimate_property(_PAYLOAD_PINGTUNG)

    assert result["valuation_status"] in ("available", "demo")
    pr = result["price_range"]
    assert pr["low"] <= pr["mid"] <= pr["high"], (
        f"price_range ordering violated: low={pr['low']} mid={pr['mid']} high={pr['high']}"
    )
    # Estimator mid must be the actual estimate (not clamped)
    assert result["estimate_total_price"] == pr["mid"]


def test_price_range_ordered_when_mid_above_p75(monkeypatch) -> None:
    """When weighted mid > p75, price_range high must still be >= mid.

    Symmetric case: high-similarity rows have HIGH prices pulling weighted mid above P75.
    """
    rows = [
        # High-similarity row (same road, close area/age) with HIGH price
        _official_row(50.0, area=28.0, age=10.0),
        _official_row(52.0, area=28.5, age=10.0),
        _official_row(53.0, area=27.5, age=11.0),
        # Lower-similarity rows with LOWER prices that form the P25-P75 band
        _official_row(30.0, area=40.0, age=2.0),
        _official_row(31.0, area=42.0, age=3.0),
        _official_row(32.0, area=38.0, age=4.0),
        _official_row(33.0, area=36.0, age=5.0),
        _official_row(34.0, area=35.0, age=6.0),
        _official_row(28.0, area=44.0, age=1.0),
        _official_row(29.0, area=45.0, age=2.0),
    ]
    _fake_postgres_provider(rows, monkeypatch)
    result = estimate_property(_PAYLOAD_PINGTUNG)

    assert result["valuation_status"] in ("available", "demo")
    pr = result["price_range"]
    assert pr["low"] <= pr["mid"] <= pr["high"], (
        f"price_range ordering violated: low={pr['low']} mid={pr['mid']} high={pr['high']}"
    )
    assert result["estimate_total_price"] == pr["mid"]


def test_price_range_normal_mid_between_p25_p75(monkeypatch) -> None:
    """Normal case: mid is between P25 and P75, existing semantics unchanged."""
    rows = [_official_row(30.0 + i, area=28.0 + i * 0.5, age=10.0) for i in range(10)]
    _fake_postgres_provider(rows, monkeypatch)
    result = estimate_property(_PAYLOAD_PINGTUNG)

    assert result["valuation_status"] in ("available", "demo")
    pr = result["price_range"]
    assert pr["low"] <= pr["mid"] <= pr["high"]
    assert result["estimate_total_price"] == pr["mid"]
    # unit_price_distribution preserves raw P25/P75 regardless of mid position
    dist = result["unit_price_distribution"]
    assert "p25" in dist and "p75" in dist
    assert dist["p25"] <= dist["p75"]


def test_validate_official_result_accepts_ordered_range(monkeypatch) -> None:
    """validate_official_result must accept a result with properly ordered price_range."""
    rows = [
        _official_row(22.0, area=28.0, age=10.0),
        _official_row(23.0, area=28.5, age=10.0),
        _official_row(24.0, area=27.5, age=11.0),
        _official_row(30.0, area=35.0, age=5.0),
        _official_row(31.0, area=36.0, age=5.0),
        _official_row(32.0, area=37.0, age=4.0),
        _official_row(33.0, area=38.0, age=6.0),
        _official_row(34.0, area=34.0, age=7.0),
        _official_row(35.0, area=40.0, age=3.0),
        _official_row(36.0, area=42.0, age=2.0),
    ]
    _fake_postgres_provider(rows, monkeypatch)
    result = estimate_property(_PAYLOAD_PINGTUNG)

    # The result should pass validation (not be rejected as invalid)
    if result["valuation_status"] == "available":
        assert validate_official_result(result), (
            f"validate_official_result rejected ordered result: {result['price_range']}"
        )


def test_estimator_mid_not_clamped(monkeypatch) -> None:
    """The estimator's mid value must NOT be clamped to P25/P75 bounds."""
    rows = [
        _official_row(22.0, area=28.0, age=10.0),
        _official_row(23.0, area=28.5, age=10.0),
        _official_row(24.0, area=27.5, age=11.0),
        _official_row(30.0, area=35.0, age=5.0),
        _official_row(31.0, area=36.0, age=5.0),
        _official_row(32.0, area=37.0, age=4.0),
        _official_row(33.0, area=38.0, age=6.0),
        _official_row(34.0, area=34.0, age=7.0),
        _official_row(35.0, area=40.0, age=3.0),
        _official_row(36.0, area=42.0, age=2.0),
    ]
    _fake_postgres_provider(rows, monkeypatch)
    result = estimate_property(_PAYLOAD_PINGTUNG)

    if result["valuation_status"] == "available":
        # mid should reflect the actual weighted estimate, which may differ from p25/p75
        dist = result["unit_price_distribution"]
        mid_per_ping = result["estimate_unit_price_per_ping"]
        # The mid is the average of weighted_mean and weighted_median
        expected_mid = round((dist["weighted_mean"] + dist["weighted_median"]) / 2, 1)
        assert mid_per_ping == expected_mid, (
            f"mid was clamped: got {mid_per_ping}, expected {expected_mid}"
        )
