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

from unittest.mock import MagicMock
from services.valuation_providers.postgres_provider import PostgresValuationProvider
from services.valuation_result_contract import validate_official_result
import services.valuation_service as _vs


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
    """When weighted mid < p25, price_range low must equal estimate and ordering holds.

    Regression: shadow case pingtung-pingtung-ziyou had low > mid because
    the weighted average fell below the unweighted P25.

    We patch _weighted_mean/_weighted_median to force mid < P25, which accurately
    simulates the real-world condition where the full scoring system produces
    a weighted central estimate below the unweighted 25th percentile.
    """
    # 10 same-road rows with evenly-spaced prices 30..48
    rows = [_official_row(30.0 + i * 2, area=28.0, age=10.0) for i in range(10)]
    _fake_postgres_provider(rows, monkeypatch)

    # Patch weighted functions to return values below P25 of [30,32,...,48]
    # P25 = sorted[2.25] = 34 + 0.25*(36-34) = 34.5
    monkeypatch.setattr(_vs, "_weighted_mean", lambda rows: 28.0)
    monkeypatch.setattr(_vs, "_weighted_median", lambda rows: 29.0)

    result = estimate_property(_PAYLOAD_PINGTUNG)

    # Must produce an available result
    assert result["valuation_status"] == "available"

    # Prove the edge condition is exercised: mid < p25
    dist = result["unit_price_distribution"]
    mid = result["estimate_unit_price_per_ping"]
    assert mid < dist["p25"], (
        f"Edge condition NOT exercised: mid={mid} must be < p25={dist['p25']}"
    )

    # Public price_range must be ordered
    pr = result["price_range"]
    assert pr["low"] <= pr["mid"] <= pr["high"], (
        f"price_range ordering violated: low={pr['low']} mid={pr['mid']} high={pr['high']}"
    )

    # When mid < p25, range_low = mid * area (not p25 * area)
    area = 28.0
    assert pr["low"] == round(mid * area, 1), (
        f"range low should be mid*area={round(mid * area, 1)}, got {pr['low']}"
    )
    assert pr["mid"] == result["estimate_total_price"]


def test_price_range_ordered_when_mid_above_p75(monkeypatch) -> None:
    """When weighted mid > p75, price_range high must equal estimate and ordering holds.

    Symmetric case: high-similarity comparables have high prices pulling
    weighted mid above P75 of the unweighted distribution.
    """
    # 10 same-road rows with evenly-spaced prices 15..42
    rows = [_official_row(15.0 + i * 3, area=28.0, age=10.0) for i in range(10)]
    _fake_postgres_provider(rows, monkeypatch)

    # Patch weighted functions to return values above P75 of [15,18,...,42]
    # P75 = sorted[6.75] = 36 + 0.75*(39-36) = 38.25... let me verify
    # sorted = [15,18,21,24,27,30,33,36,39,42], position=(9)*0.75=6.75
    # sorted[6]=33, sorted[7]=36, P75 = 33 + 0.75*(36-33) = 35.25
    monkeypatch.setattr(_vs, "_weighted_mean", lambda rows: 40.0)
    monkeypatch.setattr(_vs, "_weighted_median", lambda rows: 42.0)

    result = estimate_property(_PAYLOAD_PINGTUNG)

    # Must produce an available result
    assert result["valuation_status"] == "available"

    # Prove the edge condition is exercised: mid > p75
    dist = result["unit_price_distribution"]
    mid = result["estimate_unit_price_per_ping"]
    assert mid > dist["p75"], (
        f"Edge condition NOT exercised: mid={mid} must be > p75={dist['p75']}"
    )

    # Public price_range must be ordered
    pr = result["price_range"]
    assert pr["low"] <= pr["mid"] <= pr["high"], (
        f"price_range ordering violated: low={pr['low']} mid={pr['mid']} high={pr['high']}"
    )

    # When mid > p75, range_high = mid * area (not p75 * area)
    area = 28.0
    assert pr["high"] == round(mid * area, 1), (
        f"range high should be mid*area={round(mid * area, 1)}, got {pr['high']}"
    )
    assert pr["mid"] == result["estimate_total_price"]


def test_price_range_normal_mid_between_p25_p75(monkeypatch) -> None:
    """Normal case: mid between P25/P75, standard range semantics preserved."""
    rows = [_official_row(30.0 + i, area=28.0 + i * 0.5, age=10.0) for i in range(10)]
    _fake_postgres_provider(rows, monkeypatch)
    result = estimate_property(_PAYLOAD_PINGTUNG)

    assert result["valuation_status"] == "available"

    # Prove normal condition holds: p25 <= mid <= p75
    dist = result["unit_price_distribution"]
    mid = result["estimate_unit_price_per_ping"]
    assert dist["p25"] <= mid <= dist["p75"], (
        f"Normal condition NOT met: p25={dist['p25']} mid={mid} p75={dist['p75']}"
    )

    # Standard semantics: low ≈ p25*area, mid = estimate, high ≈ p75*area
    # (tolerance of 2.0 accounts for intermediate rounding of p25/p75)
    pr = result["price_range"]
    area = float(_PAYLOAD_PINGTUNG["area_ping"])
    assert abs(pr["low"] - dist["p25"] * area) < 2.0, (
        f"low={pr['low']} should be ~p25*area={dist['p25'] * area}"
    )
    assert pr["mid"] == result["estimate_total_price"]
    assert abs(pr["high"] - dist["p75"] * area) < 2.0, (
        f"high={pr['high']} should be ~p75*area={dist['p75'] * area}"
    )
    assert pr["low"] <= pr["mid"] <= pr["high"]


def test_validate_official_result_accepts_ordered_range(monkeypatch) -> None:
    """validate_official_result must accept a result with mid < p25 after fix."""
    rows = [_official_row(30.0 + i * 2, area=28.0, age=10.0) for i in range(10)]
    _fake_postgres_provider(rows, monkeypatch)

    # Force mid below P25
    monkeypatch.setattr(_vs, "_weighted_mean", lambda rows: 28.0)
    monkeypatch.setattr(_vs, "_weighted_median", lambda rows: 29.0)

    result = estimate_property(_PAYLOAD_PINGTUNG)

    # Must be available (not rejected)
    assert result["valuation_status"] == "available", (
        f"Expected available, got {result['valuation_status']} "
        f"reason={result.get('valuation_reason_code')}"
    )
    assert validate_official_result(result), (
        f"validate_official_result rejected result with price_range={result['price_range']}"
    )


def test_estimator_mid_not_clamped(monkeypatch) -> None:
    """The estimator's mid value must NOT be clamped to P25/P75 bounds."""
    rows = [_official_row(30.0 + i * 2, area=28.0, age=10.0) for i in range(10)]
    _fake_postgres_provider(rows, monkeypatch)

    # Force mid well below P25 — verifies mid reflects actual weighted estimate
    monkeypatch.setattr(_vs, "_weighted_mean", lambda rows: 28.0)
    monkeypatch.setattr(_vs, "_weighted_median", lambda rows: 29.0)

    result = estimate_property(_PAYLOAD_PINGTUNG)

    assert result["valuation_status"] == "available"

    # mid should reflect the actual weighted estimate (average of patched values)
    dist = result["unit_price_distribution"]
    mid_per_ping = result["estimate_unit_price_per_ping"]
    expected_mid = round((dist["weighted_mean"] + dist["weighted_median"]) / 2, 1)
    assert mid_per_ping == expected_mid, (
        f"mid was clamped: got {mid_per_ping}, expected {expected_mid} "
        f"(weighted_mean={dist['weighted_mean']}, weighted_median={dist['weighted_median']})"
    )
    # Confirm mid is actually below P25 (not clamped up)
    assert mid_per_ping < dist["p25"], (
        f"mid should be below p25 (unclamped): mid={mid_per_ping}, p25={dist['p25']}"
    )
