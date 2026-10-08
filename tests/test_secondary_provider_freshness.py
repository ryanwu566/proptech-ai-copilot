"""Offline freshness and missing-data boundaries for secondary providers."""

from datetime import UTC, date, datetime

import pytest

from services.ris_demographics_insight import build_demographics_insight
from services.tdx_mrt_snapshot import build_tdx_mrt_snapshot


def _station(updated="2026-10-01T00:00:00Z"):
    return {"StationUID": "ST-A", "StationName": "Station A", "StationPosition": {"PositionLat": 25, "PositionLon": 121}, "SrcUpdateTime": updated}


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 8, tzinfo=UTC)


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 8)


@pytest.mark.parametrize("updated,status,age", [("2026-10-01T00:00:00Z", "current", 7), ("2026-01-01T00:00:00Z", "stale", 280), ("malformed", "unknown", None), ("2099-01-01T00:00:00Z", "unknown", None)])
def test_tdx_freshness_uses_source_time_instead_of_new_generation(monkeypatch, updated, status, age):
    import services.tdx_mrt_snapshot as mod
    monkeypatch.setattr(mod, "datetime", FixedDatetime, raising=False)
    snapshot = build_tdx_mrt_snapshot([_station(updated)], [], "2026-10-08T00:00:00Z")
    result = snapshot.to_status_dict()
    assert result["freshness_status"] == status
    assert result["source_age_days"] == age
    assert result["stale_after_days"] == 30


def test_tdx_version_identifies_content_without_changing_on_refresh_time():
    first = build_tdx_mrt_snapshot([_station()], [], "2026-10-08T00:00:00Z").to_status_dict()
    refresh = build_tdx_mrt_snapshot([_station()], [], "2026-10-09T00:00:00Z").to_status_dict()
    changed = build_tdx_mrt_snapshot([_station("2026-10-02T00:00:00Z")], [], "2026-10-09T00:00:00Z").to_status_dict()
    assert first["snapshot_version"] == refresh["snapshot_version"]
    assert first["snapshot_version"] != changed["snapshot_version"]


def test_nearest_station_and_public_status_preserve_snapshot_provenance(monkeypatch):
    import services.tdx_mrt_snapshot as mod
    from services.commute_service import find_nearest_station, get_commute_status, set_commute_snapshot_for_testing
    from backend.api.routes_commute import CommuteLookupResponse, CommuteStatusResponse
    from backend.api_main import app
    from fastapi.testclient import TestClient
    monkeypatch.setattr(mod, "datetime", FixedDatetime)
    snapshot = build_tdx_mrt_snapshot([_station("2026-01-01T00:00:00Z")], [], "2026-10-08T00:00:00Z")
    set_commute_snapshot_for_testing(snapshot)
    try:
        result = CommuteLookupResponse(**find_nearest_station(25, 121)).model_dump()
        status = CommuteStatusResponse(**get_commute_status()).model_dump()
        assert result["freshness_status"] == "stale"
        assert result["snapshot_version"] == status["snapshot_version"]
        assert status["available"] is True
        assert status["source_updated_at"] == "2026-01-01T00:00:00+00:00"
        assert result["source_updated_at"] == "2026-01-01T00:00:00Z"
        client = TestClient(app)
        public_status = client.get("/commute/status").json()
        public_nearest = client.post("/commute/nearest", json={"latitude": 25, "longitude": 121}).json()
        assert public_status["snapshot_version"] == public_nearest["snapshot_version"] == result["snapshot_version"]
        assert public_nearest["freshness_status"] == "stale"
        assert public_nearest["snapshot_source_updated_at"] == "2026-01-01T00:00:00+00:00"
    finally:
        set_commute_snapshot_for_testing(None)


def test_missing_tdx_snapshot_is_unavailable_freshness():
    from services.commute_service import get_commute_status, set_commute_snapshot_for_testing
    set_commute_snapshot_for_testing(None)
    status = get_commute_status()
    assert status["freshness_status"] == "unavailable"
    assert status["snapshot_version"] is None


def _observation(month="11509", **values):
    return {"statistic_yyymm": month, "statistic_month": date(1911 + int(month[:-2]), int(month[-2:]), 1), "total_population": 20, "household_count": 8, **values}


@pytest.mark.parametrize("key,value", [("total_population", None), ("household_count", "invalid"), ("total_population", float("inf")), ("total_population", 1.5), ("total_population", -1)])
def test_invalid_latest_demographics_is_no_data_instead_of_zero(key, value):
    result = build_demographics_insight(_observation(**{key: value}), [_observation("11508")])
    assert result["status"] == "no_data"
    assert result["reason"] == "demographics_observation_invalid"
    assert "total_population" not in result


def test_invalid_history_is_excluded_and_valid_zero_remains_zero():
    latest = _observation("11509", total_population=0)
    result = build_demographics_insight(latest, [_observation("11507", total_population=None), _observation("11508", total_population=10), latest])
    assert result["total_population"] == 0
    assert result["first_month"] == "11508"
    assert result["population_change"] == -10
    assert result["observed_month_count"] == 2


def test_latest_counts_are_preserved_when_history_read_has_older_months():
    result = build_demographics_insight(_observation("11509", total_population=25, household_count=10), [_observation("11508")])
    assert result["statistic_yyymm"] == "11509"
    assert result["total_population"] == 25
    assert result["household_count"] == 10


@pytest.mark.parametrize("month,status,lag", [("11509", "current", 1), ("11508", "current", 2), ("11507", "stale", 3), ("11601", "unknown", -3)])
def test_ris_freshness_tracks_statistical_month_separately_from_success(monkeypatch, month, status, lag):
    import services.ris_demographics_insight as mod
    monkeypatch.setattr(mod, "date", FixedDate)
    latest = _observation(month)
    result = build_demographics_insight(latest, [latest])
    assert result["status"] == "available"
    assert result["freshness_status"] == status
    assert result["latest_statistic_yyymm"] == month
    assert result["statistical_month_lag"] == lag
    assert result["stale_after_months"] == 2
