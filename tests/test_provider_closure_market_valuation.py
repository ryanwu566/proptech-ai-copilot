"""Offline production-boundary regressions for Finder, Trend and valuation."""

from datetime import UTC, datetime
import re
import sqlite3

import pytest

from services.property_search_service import search_properties
from services.valuation_providers.postgres_provider import PostgresValuationProvider, _comparable_query
from services.valuation_service import _prepare_candidate_pool, _shift_month, estimate_property
from services.valuation_trend_service import analyze_valuation_trend


PAYLOAD = {"city": "Taipei City", "district": "Central District", "road": "Example Road", "building_type": "Apartment", "area_ping": 30, "building_age_years": 10, "floor": 5}


def _row(period):
    return {**PAYLOAD, "transaction_period": period, "source": "official_plvr_opendata", "unit_price_per_ping": 60, "total_price": 1800}


@pytest.mark.parametrize("capability", ["finder", "trend"])
def test_sql_failure_is_unavailable_and_recovery_can_return_true_empty(monkeypatch, capability):
    provider = PostgresValuationProvider("postgresql://offline-fixture")
    def fail_connect():
        raise RuntimeError("secret-database-detail")
    monkeypatch.setattr(provider, "_connect", fail_connect)
    if capability == "finder":
        monkeypatch.setattr("services.property_search_service.get_valuation_provider", lambda: provider)
        result = search_properties({"budget_max": 3000})
        assert result["search_status"] == "unavailable"
        assert result["search_reason_code"] == "provider_query_failed"
        assert result["summary"]["matched_count"] is None
    else:
        monkeypatch.setattr("services.valuation_trend_service.get_valuation_provider", lambda: provider)
        result = analyze_valuation_trend(PAYLOAD)
        assert result["trend_status"] == "unavailable"
        assert result["trend_reason_code"] == "provider_query_failed"
    assert "secret-database-detail" not in str(result)
    assert provider.last_query_metadata["query_status"] == "failed"
    monkeypatch.setattr(provider, "_connect", _EmptyConnection)
    if capability == "finder":
        recovered = search_properties({"budget_max": 3000})
        assert recovered["search_status"] == "no_data"
    else:
        recovered = analyze_valuation_trend(PAYLOAD)
        assert recovered["trend_status"] == "no_data"
    assert provider.last_query_metadata["query_status"] == "ok"


class _EmptyConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self

    def execute(self, *args):
        pass

    def fetchall(self):
        return []


@pytest.mark.parametrize("capability", ["finder", "trend"])
def test_blue_empty_capability_reports_source_even_with_green_estimate_enabled(monkeypatch, capability):
    from backend.api.routes_valuation import _safe_property_search_response, _safe_trend_response
    provider = PostgresValuationProvider("postgresql://offline-fixture")
    monkeypatch.setattr(provider, "_connect", _EmptyConnection)
    monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
    if capability == "finder":
        monkeypatch.setattr("services.property_search_service.get_valuation_provider", lambda: provider)
        result = _safe_property_search_response(search_properties({"budget_max": 3000}))
    else:
        monkeypatch.setattr("services.valuation_trend_service.get_valuation_provider", lambda: provider)
        result = _safe_trend_response(analyze_valuation_trend(PAYLOAD))
    assert result["source_details"]["provider_active"] == "postgres"
    assert result["source_details"]["backend"] == "blue"
    assert result["source_details"]["capability"] == capability


def test_official_candidate_window_includes_current_and_35_prior_months_only():
    current = datetime.now(UTC).strftime("%Y-%m")
    cutoff = _shift_month(current, -35)
    rows = [_row(period) for period in [cutoff, current, current, _shift_month(current, -36), _shift_month(current, 1), "2026-00", "2026-13", "2026-01-extra"]]
    selected, _ = _prepare_candidate_pool(rows, PAYLOAD)
    assert [row["transaction_period"] for row in selected] == [cutoff, current, current]


def test_blue_query_enforces_window_before_candidate_limit():
    sql, params = _comparable_query(PAYLOAD, "district", 200)
    current = datetime.now(UTC).strftime("%Y-%m")
    where = sql.split("order by")[0]
    assert "transaction_period >= %s" in where
    assert "transaction_period <= %s" in where
    assert params[:2] == [_shift_month(current, -35), current]
    assert "transaction_period ~" in where


def test_estimate_remains_available_when_same_provider_trend_query_fails(monkeypatch):
    provider = PostgresValuationProvider("postgresql://offline-fixture")
    monkeypatch.setattr(provider, "data_status", lambda: {"active_source": "postgres", "coverage": {}, "data_composition": "official"})
    monkeypatch.setattr(provider, "query_comparables", lambda payload: [_row(datetime.now(UTC).strftime("%Y-%m")) for _ in range(3)])
    monkeypatch.setattr(provider, "match_community", lambda payload: None)
    monkeypatch.setattr(provider, "_connect", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)
    monkeypatch.setattr("services.valuation_trend_service.get_valuation_provider", lambda: provider)
    monkeypatch.setenv("PLVR_DATA_BACKEND", "blue")
    estimate = estimate_property(PAYLOAD)
    trend = analyze_valuation_trend(PAYLOAD)
    assert estimate["valuation_status"] == "available"
    assert estimate["estimate_total_price"] == 1800
    assert trend["trend_status"] == "unavailable"
    assert trend["trend_reason_code"] == "provider_query_failed"


@pytest.mark.parametrize("request_bounds", [{}, {"window_start": "1900-01", "current_period": "2099-01"}])
def test_trend_database_window_precedes_limit_so_future_rows_cannot_starve_valid_evidence(monkeypatch, request_bounds):
    current = datetime.now(UTC).strftime("%Y-%m")
    cutoff = _shift_month(current, -35)
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.create_function("regexp", 2, lambda pattern, value: bool(re.fullmatch(pattern, value)))
    db.execute("create table real_price_transactions(transaction_period text, city text, district text, road text, building_type text, area_ping real, building_age_years real, unit_price_per_ping real, total_price real, source text)")
    columns = ("transaction_period", "city", "district", "road", "building_type", "area_ping", "building_age_years", "unit_price_per_ping", "total_price", "source")
    rows = [_row(_shift_month(current, 1)) for _ in range(10_001)]
    rows += [_row(cutoff) for _ in range(20)] + [_row(current) for _ in range(20)]
    rows += [_row(_shift_month(current, -36)), _row("2026-13"), _row("2026-01-extra")]
    db.executemany("insert into real_price_transactions values (?,?,?,?,?,?,?,?,?,?)", [tuple(row[column] for column in columns) for row in rows])

    class OfflineConnection:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def cursor(self):
            return self
        def execute(self, sql, params):
            # Adapt only PostgreSQL parameter/regex syntax; SQLite executes the
            # production WHERE/ORDER/LIMIT semantics against the fixture table.
            sql = re.sub(r"transaction_period ~ '([^']+)'", r"regexp('\1', transaction_period)", sql)
            sql = sql.replace("'Infinity'::numeric", "1e999")
            self.rows = db.execute(sql.replace("%s", "?"), params).fetchall()
        def fetchall(self):
            return self.rows

    provider = PostgresValuationProvider("postgresql://offline-fixture")
    monkeypatch.setattr(provider, "_connect", OfflineConnection)
    try:
        selected = provider.query_trend_rows({**PAYLOAD, **request_bounds})
        assert len(selected) == 40
        assert {row["transaction_period"] for row in selected} == {cutoff, current}
        result = analyze_valuation_trend(PAYLOAD, selected)
        assert result["trend_status"] == "available"
        assert result["sample_count"] == 40
    finally:
        db.close()


@pytest.mark.parametrize("key,value", [("unit_price_per_ping", float("nan")), ("area_ping", float("nan")), ("area_ping", float("inf")), ("unit_price_per_ping", "invalid")])
def test_trend_invalid_numeric_evidence_cannot_erase_valid_rows_or_create_json_nan(key, value):
    current = datetime.now(UTC).strftime("%Y-%m")
    valid = [_row(current), _row(_shift_month(current, -1))]
    invalid = {**_row(current), key: value}
    result = analyze_valuation_trend(PAYLOAD, [*valid, invalid])
    assert result["trend_status"] == "available"
    assert result["sample_count"] == 2
    assert result["recent_median_unit_price"] == 60
    unavailable = analyze_valuation_trend(PAYLOAD, [invalid, {**invalid, "transaction_period": _shift_month(current, -1)}])
    assert unavailable["trend_status"] == "no_data"
    assert unavailable["recent_median_unit_price"] is None


@pytest.mark.parametrize("competing", [{"source": "real_price_sample"}, {"total_price": 0}, {"total_price": float("inf")}, {"unit_price_per_ping": 0}, {"unit_price_per_ping": float("inf")}])
def test_blue_query_filters_ineligible_rows_before_limit_to_preserve_official_estimate(monkeypatch, competing):
    current = datetime.now(UTC).strftime("%Y-%m")
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.create_function("regexp", 2, lambda pattern, value: bool(re.fullmatch(pattern, value)))
    db.create_function("power", 2, lambda left, right: left ** right)
    db.execute("create table real_price_transactions(id integer, transaction_period text, city text, district text, road text, address_text text, building_type text, area_ping real, building_age_years real, floor real, total_floor real, unit_price_per_ping real, total_price real, lat real, lng real, source text, imported_at text, raw_note text)")
    columns = ("id", "transaction_period", "city", "district", "road", "address_text", "building_type", "area_ping", "building_age_years", "floor", "total_floor", "unit_price_per_ping", "total_price", "lat", "lng", "source", "imported_at", "raw_note")
    rows = [{**_row(current), "id": index, **competing} for index in range(200)]
    rows += [{**_row(current), "id": index + 200, "area_ping": 40, "total_price": 2400} for index in range(3)]
    db.executemany("insert into real_price_transactions values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [tuple(row.get(column) for column in columns) for row in rows])

    class OfflineConnection:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def cursor(self):
            return self
        def execute(self, sql, params):
            sql = re.sub(r"transaction_period ~ '([^']+)'", r"regexp('\1', transaction_period)", sql)
            sql = sql.replace("::double precision", "").replace("'Infinity'::numeric", "1e999")
            self.rows = db.execute(sql.replace("%s", "?"), params).fetchall()
        def fetchall(self):
            return self.rows

    provider = PostgresValuationProvider("postgresql://offline-fixture")
    monkeypatch.setattr(provider, "_connect", OfflineConnection)
    monkeypatch.setattr(provider, "match_community", lambda payload: None)
    monkeypatch.setattr(provider, "data_status", lambda: {"active_source": "postgres", "coverage": {}, "data_composition": "official"})
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)
    monkeypatch.setenv("PLVR_DATA_BACKEND", "blue")
    try:
        result = estimate_property(PAYLOAD)
        assert result["valuation_status"] == "available"
        assert result["candidate_pool_size"] == 3
        assert len(result["comparables"]) == 3
        assert {row["source"] for row in result["comparables"]} == {"official_plvr_opendata"}
    finally:
        db.close()
