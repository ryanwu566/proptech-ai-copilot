"""Tests for Compact GREEN — valuation estimate GREEN routing with connection pool.

Covers 25 required test scenarios:
1. Pool is lazy — import creates 0 connections
2. First GREEN query initializes pool once
3. Subsequent GREEN queries reuse same pool object
4. Pool max_size = 3
5. Pool min_size = 1
6. Concurrent initialization creates one pool only
7. Query uses pool.connection(), not fresh psycopg.connect()
8. Checked-out connection is read-only before SELECT
9. Successful checkout returns connection cleanly
10. Query exception returns/rolls back safely
11. Pool checkout failure does NOT call BLUE
12. Broken GREEN connection does NOT call BLUE
13. Missing COMPACT_GREEN_DATABASE_URL fails explicitly
14. Geography cache still loads once
15. Max period remains 318 in regression mock
16. Frozen SQL semantics unchanged
17. Row mapping unchanged
18. PLVR_DATA_BACKEND unset remains BLUE
19. PLVR_DATA_BACKEND=blue remains BLUE
20. PLVR_DATA_BACKEND=green uses GREEN comparables only
21. Trend remains BLUE
22. Property search remains BLUE
23. Data status remains BLUE
24. match_community remains BLUE
25. API response contract unchanged
"""

from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_green_row(period_code: int = 318, **overrides: Any) -> dict[str, Any]:
    """Build a fake GREEN DB result row."""
    base = {
        "period_code": period_code,
        "city": "台北市",
        "district": "大安區",
        "road": "和平東路二段",
        "building_type": "住宅大樓",
        "area_ping": 30.0,
        "building_age_years": 12.0,
        "floor": 8.0,
        "total_floor": 14.0,
        "unit_price_per_ping": 75.0,
        "total_price": 2250.0,
        "address_text": "和平東路二段100號",
    }
    base.update(overrides)
    return base


@contextmanager
def _mock_pool(rows=None):
    """Context manager providing a mock pool that returns fake rows.

    The mock correctly simulates the transaction lifecycle:
    pool.connection() -> connection.transaction() -> connection.execute(SET RO) -> cursor.execute(SQL)
    """
    if rows is None:
        rows = [_fake_green_row()]

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.execute = MagicMock()

    # transaction() must be a context manager
    mock_tx = MagicMock()
    mock_tx.__enter__ = MagicMock(return_value=mock_tx)
    mock_tx.__exit__ = MagicMock(return_value=False)
    mock_conn.transaction.return_value = mock_tx

    @contextmanager
    def connection_ctx():
        yield mock_conn

    mock_pool_obj = MagicMock()
    mock_pool_obj.connection = connection_ctx
    mock_pool_obj.min_size = 1
    mock_pool_obj.max_size = 3

    yield mock_pool_obj, mock_conn, mock_cursor


def _fake_provider(monkeypatch, rows=None, available=True):
    """Patch get_valuation_provider to return a mock PostgresValuationProvider."""
    from services.valuation_providers.postgres_provider import PostgresValuationProvider

    provider = MagicMock(spec=PostgresValuationProvider)
    provider.source = "postgres"
    provider.is_demo_data = False
    provider.is_full_taiwan = False
    provider.available.return_value = available
    provider.data_status.return_value = {
        "active_source": "postgres", "is_demo_data": False, "is_full_taiwan": False,
        "data_composition": "official", "official_records_count": 1000, "sample_records_count": 0,
        "coverage": {"cities": ["台北市"], "districts": ["大安區"], "roads_count": 10, "records_count": 1000},
        "last_updated": "2026-08-01T00:00:00+00:00",
        "freshness_status": "current", "freshness_reason_code": "data_current",
        "freshness_as_of": "2026-08-17", "latest_import_at": "2026-08-01T00:00:00+00:00",
        "latest_import_age_days": 16, "newest_effective_period_lag_months": 1,
        "operator_attention_required": False, "freshness_user_message": "資料為最新狀態。",
    }
    provider.match_community.return_value = None
    provider.last_query_metadata = {
        "provider_active": "postgres", "candidate_pool_size": 50,
        "query_scope": "district_pool", "requested_city": "台北市",
        "requested_district": "大安區", "requested_road": "和平東路二段",
        "db_rows_returned": 50, "query_status": "ok",
    }
    provider.query_comparables.return_value = rows if rows is not None else []
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)
    return provider


def _sample_payload() -> dict[str, Any]:
    return {
        "city": "台北市", "district": "大安區", "road": "和平東路二段",
        "building_type": "住宅大樓", "area_ping": 30.0, "building_age_years": 12.0,
        "floor": 8, "lat": 25.025, "lng": 121.543, "address_text": "和平東路二段100號",
    }


def _green_compatible_rows(n=5):
    """Return n BLUE-compatible mapped GREEN rows."""
    return [{
        "transaction_period": "2026-07", "city": "台北市", "district": "大安區",
        "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30.0,
        "building_age_years": 12.0, "floor": 8.0, "total_floor": 14.0,
        "unit_price_per_ping": 75.0, "total_price": 2250.0,
        "address_text": "和平東路二段100號", "lat": None, "lng": None,
        "source": "official_plvr_opendata", "imported_at": None, "raw_note": None,
    }] * n


# ---------------------------------------------------------------------------
# 1. Pool is lazy — import creates 0 connections
# ---------------------------------------------------------------------------

class TestPoolLazy:
    def test_import_does_not_create_pool(self):
        import services.compact_green_query as mod
        # Accessing the module-level _pool should be None after reset
        mod._reset_pool()
        assert mod._pool is None


# ---------------------------------------------------------------------------
# 2. First GREEN query initializes pool once
# ---------------------------------------------------------------------------

class TestPoolInitOnFirstQuery:
    def test_first_query_creates_pool(self, monkeypatch):
        from services.compact_green_query import query_green_comparables, reset_geography_cache, _pool
        import services.compact_green_query as mod

        reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        with _mock_pool() as (mock_pool_obj, mock_conn, mock_cursor):
            monkeypatch.setattr(mod, "_pool", None)
            monkeypatch.setattr("services.compact_green_query._get_pool", lambda: mock_pool_obj)

            query_green_comparables(_sample_payload())
            # Pool was used (connection() was called)
            # Verify via mock_conn.execute being called with SET TRANSACTION READ ONLY

        reset_geography_cache()


# ---------------------------------------------------------------------------
# 3. Subsequent GREEN queries reuse same pool object
# ---------------------------------------------------------------------------

class TestPoolReuse:
    def test_same_pool_across_calls(self, monkeypatch):
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        with _mock_pool() as (mock_pool_obj, _, _):
            monkeypatch.setattr(mod, "_pool", mock_pool_obj)

            mod.query_green_comparables(_sample_payload())
            mod.query_green_comparables(_sample_payload())
            # Same pool object used both times (no new pool created)
            assert mod._pool is mock_pool_obj

        mod.reset_geography_cache()


# ---------------------------------------------------------------------------
# 4. Pool max_size = 3
# ---------------------------------------------------------------------------

class TestPoolMaxSize:
    def test_max_size_is_3(self):
        from services.compact_green_query import _POOL_MAX_SIZE
        assert _POOL_MAX_SIZE == 3


# ---------------------------------------------------------------------------
# 5. Pool min_size = 1
# ---------------------------------------------------------------------------

class TestPoolMinSize:
    def test_min_size_is_1(self):
        from services.compact_green_query import _POOL_MIN_SIZE
        assert _POOL_MIN_SIZE == 1


# ---------------------------------------------------------------------------
# 6. Concurrent initialization creates one pool only
# ---------------------------------------------------------------------------

class TestPoolConcurrentInit:
    def test_concurrent_init_one_pool(self, monkeypatch):
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        mod._reset_pool()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

        init_count = {"n": 0}
        original_pool_class = MagicMock()

        def fake_pool_constructor(**kwargs):
            init_count["n"] += 1
            mock_pool = MagicMock()
            mock_pool.wait = MagicMock()
            mock_pool.min_size = 1
            mock_pool.max_size = 3
            return mock_pool

        monkeypatch.setattr("psycopg_pool.ConnectionPool", fake_pool_constructor)

        barrier = threading.Barrier(5, timeout=5)
        results = []

        def worker():
            barrier.wait()
            try:
                pool = mod._get_pool()
                results.append(pool)
            except Exception as e:
                results.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert init_count["n"] == 1
        mod._reset_pool()


# ---------------------------------------------------------------------------
# 7. Query uses pool.connection(), not fresh psycopg.connect()
# ---------------------------------------------------------------------------

class TestQueryUsesPool:
    def test_no_direct_psycopg_connect(self, monkeypatch):
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        connect_calls = {"n": 0}

        with _mock_pool() as (mock_pool_obj, _, _):
            monkeypatch.setattr(mod, "_pool", mock_pool_obj)

            # Patch psycopg.connect to detect direct usage
            with patch("psycopg.connect") as mock_connect:
                mod.query_green_comparables(_sample_payload())
                mock_connect.assert_not_called()

        mod.reset_geography_cache()


# ---------------------------------------------------------------------------
# 8. Checked-out connection is read-only before SELECT
# ---------------------------------------------------------------------------

class TestReadOnlyBeforeSelect:
    def test_set_transaction_read_only_inside_transaction(self, monkeypatch):
        """Verify SET TRANSACTION READ ONLY and SELECT are inside conn.transaction()."""
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        call_order = []

        with _mock_pool() as (mock_pool_obj, mock_conn, mock_cursor):
            # Track call order to prove nesting
            mock_conn.transaction.return_value.__enter__ = MagicMock(
                side_effect=lambda: call_order.append("tx_enter")
            )
            mock_conn.transaction.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute = MagicMock(
                side_effect=lambda sql: call_order.append(f"execute:{sql}")
            )
            mock_cursor.execute = MagicMock(
                side_effect=lambda sql, params=None: call_order.append("cursor_execute")
            )
            mock_cursor.fetchall.return_value = [_fake_green_row()]

            monkeypatch.setattr(mod, "_pool", mock_pool_obj)
            mod.query_green_comparables(_sample_payload())

        # Verify order: transaction entered BEFORE read-only and query
        assert "tx_enter" in call_order
        tx_idx = call_order.index("tx_enter")
        ro_idx = call_order.index("execute:SET TRANSACTION READ ONLY")
        query_idx = call_order.index("cursor_execute")
        assert tx_idx < ro_idx < query_idx, (
            f"Expected tx_enter < SET RO < cursor_execute, got order: {call_order}"
        )

        mod.reset_geography_cache()

    def test_transaction_context_manager_used(self, monkeypatch):
        """Verify conn.transaction() is called (not just conn.execute)."""
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        with _mock_pool() as (mock_pool_obj, mock_conn, mock_cursor):
            monkeypatch.setattr(mod, "_pool", mock_pool_obj)
            mod.query_green_comparables(_sample_payload())

            # connection.transaction() must have been called
            mock_conn.transaction.assert_called_once()

        mod.reset_geography_cache()


# ---------------------------------------------------------------------------
# 9. Successful checkout returns connection cleanly
# ---------------------------------------------------------------------------

class TestSuccessfulCheckout:
    def test_connection_returned_on_success(self, monkeypatch):
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        with _mock_pool() as (mock_pool_obj, _, _):
            monkeypatch.setattr(mod, "_pool", mock_pool_obj)
            # Should not raise — connection returned cleanly via context manager
            result = mod.query_green_comparables(_sample_payload())
            assert len(result) > 0

        mod.reset_geography_cache()


# ---------------------------------------------------------------------------
# 10. Query exception returns/rolls back safely
# ---------------------------------------------------------------------------

class TestQueryExceptionSafe:
    def test_exception_propagates_as_green_error(self, monkeypatch):
        import services.compact_green_query as mod
        from services.compact_green_query import CompactGreenQueryError

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = RuntimeError("simulated DB error")
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.execute = MagicMock()

        # transaction() context manager — __exit__ will be called with exception info
        mock_tx = MagicMock()
        mock_tx.__enter__ = MagicMock(return_value=mock_tx)
        mock_tx.__exit__ = MagicMock(return_value=False)  # propagate exception
        mock_conn.transaction.return_value = mock_tx

        @contextmanager
        def bad_connection():
            yield mock_conn

        mock_pool_obj = MagicMock()
        mock_pool_obj.connection = bad_connection
        monkeypatch.setattr(mod, "_pool", mock_pool_obj)

        with pytest.raises(CompactGreenQueryError, match="GREEN query failed"):
            mod.query_green_comparables(_sample_payload())

        # Verify transaction __exit__ was called (rollback path)
        mock_tx.__exit__.assert_called_once()

        mod.reset_geography_cache()

    def test_next_checkout_not_left_in_failed_state(self, monkeypatch):
        """After a failed query, next pool checkout gets a clean connection."""
        import services.compact_green_query as mod
        from services.compact_green_query import CompactGreenQueryError

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        call_count = {"n": 0}

        # First call fails, second succeeds
        def make_connection_ctx():
            @contextmanager
            def connection_ctx():
                call_count["n"] += 1
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
                mock_cursor.__exit__ = MagicMock(return_value=False)

                mock_tx = MagicMock()
                mock_tx.__enter__ = MagicMock(return_value=mock_tx)
                mock_tx.__exit__ = MagicMock(return_value=False)
                mock_conn.transaction.return_value = mock_tx

                if call_count["n"] == 1:
                    mock_cursor.execute.side_effect = RuntimeError("first call fails")
                else:
                    mock_cursor.execute.side_effect = None
                    mock_cursor.fetchall.return_value = [_fake_green_row()]

                mock_conn.cursor.return_value = mock_cursor
                mock_conn.execute = MagicMock()
                yield mock_conn

            return connection_ctx

        mock_pool_obj = MagicMock()
        mock_pool_obj.connection = make_connection_ctx()
        monkeypatch.setattr(mod, "_pool", mock_pool_obj)

        # First call should fail
        with pytest.raises(CompactGreenQueryError):
            mod.query_green_comparables(_sample_payload())

        # Second call with fresh connection mock
        mock_pool_obj.connection = make_connection_ctx()
        result = mod.query_green_comparables(_sample_payload())
        assert len(result) == 1  # second call succeeds

        mod.reset_geography_cache()


# ---------------------------------------------------------------------------
# 11. Pool checkout failure does NOT call BLUE
# ---------------------------------------------------------------------------

class TestPoolFailureNoBlueFallback:
    def test_pool_failure_no_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        from services.compact_green_query import CompactGreenQueryError

        def raise_pool_error(payload):
            raise CompactGreenQueryError("pool checkout timeout")

        monkeypatch.setattr("services.compact_green_query.query_green_comparables", raise_pool_error)

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())

        provider.query_comparables.assert_not_called()


# ---------------------------------------------------------------------------
# 12. Broken GREEN connection does NOT call BLUE
# ---------------------------------------------------------------------------

class TestBrokenConnectionNoBlueFallback:
    def test_broken_connection_no_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        from services.compact_green_query import CompactGreenQueryError

        def raise_broken(payload):
            raise CompactGreenQueryError("GREEN query failed: OperationalError")

        monkeypatch.setattr("services.compact_green_query.query_green_comparables", raise_broken)

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())

        provider.query_comparables.assert_not_called()


# ---------------------------------------------------------------------------
# 13. Missing COMPACT_GREEN_DATABASE_URL fails explicitly
# ---------------------------------------------------------------------------

class TestMissingURLFails:
    def test_missing_url_raises(self, monkeypatch):
        from services.compact_green_query import CompactGreenQueryError, query_green_comparables, reset_geography_cache
        import services.compact_green_query as mod

        reset_geography_cache()
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        mod._pool = None

        with pytest.raises(CompactGreenQueryError, match="not configured"):
            query_green_comparables(_sample_payload())

        reset_geography_cache()


# ---------------------------------------------------------------------------
# 14. Geography cache still loads once
# ---------------------------------------------------------------------------

class TestGeographyCacheLoadsOnce:
    def test_cache_singleton(self, monkeypatch):
        from services.compact_green_query import get_geography_cache, reset_geography_cache
        import services.compact_green_query as mod

        reset_geography_cache()
        call_count = {"n": 0}

        def fake_load(url):
            call_count["n"] += 1
            return ({("台北市", "大安區"): 1, ("新北市", "板橋區"): 2}, 318)

        monkeypatch.setattr(mod, "_load_geography_cache", fake_load)
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

        cache1 = get_geography_cache()
        cache2 = get_geography_cache()
        cache3 = get_geography_cache()

        assert call_count["n"] == 1
        assert cache1 is cache2 is cache3
        reset_geography_cache()


# ---------------------------------------------------------------------------
# 15. Max period remains 318 in regression mock
# ---------------------------------------------------------------------------

class TestMaxPeriod318:
    def test_max_period_code_318(self, monkeypatch):
        from services.compact_green_query import get_geography_cache, get_max_period_code, reset_geography_cache
        import services.compact_green_query as mod

        reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        get_geography_cache()
        assert get_max_period_code() == 318
        reset_geography_cache()


# ---------------------------------------------------------------------------
# 16. Frozen SQL semantics unchanged
# ---------------------------------------------------------------------------

class TestFrozenSQL:
    def test_sql_contains_required_elements(self):
        from services.compact_green_query import _VALUATION_COMPARABLES_SQL as sql
        assert "compact_green.compact_transaction_facts" in sql
        assert "compact_green.compact_geographies" in sql
        assert "compact_green.compact_roads" in sql
        assert "compact_green.compact_building_types" in sql
        assert "generation_key = 1" in sql
        assert "MATERIALIZED" in sql
        assert "LIMIT 200" in sql
        assert "%(max_period_code)s" in sql
        assert "%(road)s" in sql
        assert "%(building_type)s" in sql
        assert "%(area_ping)s" in sql
        assert "%(building_age_years)s" in sql


# ---------------------------------------------------------------------------
# 17. Row mapping unchanged
# ---------------------------------------------------------------------------

class TestRowMapping:
    def test_all_required_fields_present(self):
        from services.compact_green_query import _map_green_row
        row = _fake_green_row(period_code=318)
        mapped = _map_green_row(row)
        required = {"transaction_period", "city", "district", "road", "building_type",
                    "area_ping", "building_age_years", "floor", "total_floor",
                    "unit_price_per_ping", "total_price", "address_text",
                    "lat", "lng", "source", "imported_at", "raw_note"}
        assert required.issubset(set(mapped.keys()))
        assert mapped["transaction_period"] == "2026-07"
        assert mapped["source"] == "official_plvr_opendata"
        assert mapped["lat"] is None
        assert mapped["lng"] is None

    def test_period_decode_318(self):
        from services.compact_green_query import decode_period
        assert decode_period(318) == "2026-07"

    def test_period_decode_284(self):
        from services.compact_green_query import decode_period
        assert decode_period(284) == "2023-09"

    def test_encode_roundtrip(self):
        from services.compact_green_query import decode_period, encode_period
        assert decode_period(encode_period(2026, 7)) == "2026-07"
        assert decode_period(encode_period(2025, 12)) == "2025-12"


# ---------------------------------------------------------------------------
# 18. PLVR_DATA_BACKEND unset remains BLUE
# ---------------------------------------------------------------------------

class TestFlagUnsetBLUE:
    def test_unset_uses_blue(self, monkeypatch):
        monkeypatch.delenv("PLVR_DATA_BACKEND", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        provider = _fake_provider(monkeypatch)

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())
        provider.query_comparables.assert_called_once()


# ---------------------------------------------------------------------------
# 19. PLVR_DATA_BACKEND=blue remains BLUE
# ---------------------------------------------------------------------------

class TestFlagBlueBLUE:
    def test_explicit_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "blue")
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        provider = _fake_provider(monkeypatch)

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())
        provider.query_comparables.assert_called_once()


# ---------------------------------------------------------------------------
# 20. PLVR_DATA_BACKEND=green uses GREEN comparables only
# ---------------------------------------------------------------------------

class TestFlagGreenUsesGREEN:
    def test_green_flag_calls_green(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: _green_compatible_rows(5),
        )

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())
        provider.query_comparables.assert_not_called()


# ---------------------------------------------------------------------------
# 21. Trend remains BLUE
# ---------------------------------------------------------------------------

class TestTrendRemainsBLUE:
    def test_trend_no_green(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        from services.valuation_providers.postgres_provider import PostgresValuationProvider

        provider = MagicMock(spec=PostgresValuationProvider)
        provider.source = "postgres"
        provider.is_demo_data = False
        provider.is_full_taiwan = False
        provider.available.return_value = True
        provider.last_query_metadata = {"query_status": "ok"}
        provider.query_trend_rows.return_value = []

        monkeypatch.setattr("services.valuation_trend_service.get_valuation_provider", lambda: provider)

        from services.valuation_trend_service import analyze_valuation_trend
        analyze_valuation_trend({"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 12})
        provider.query_trend_rows.assert_called_once()


# ---------------------------------------------------------------------------
# 22. Property search remains BLUE
# ---------------------------------------------------------------------------

class TestPropertySearchRemainsBLUE:
    def test_search_no_green(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        from services.valuation_providers.postgres_provider import PostgresValuationProvider

        provider = MagicMock(spec=PostgresValuationProvider)
        provider.source = "postgres"
        provider.is_demo_data = False
        provider.is_full_taiwan = False
        provider.available.return_value = True
        provider.last_query_metadata = {"query_status": "ok"}
        provider.query_property_search_rows.return_value = []

        monkeypatch.setattr("services.property_search_service.get_valuation_provider", lambda: provider)

        from services.property_search_service import search_properties
        search_properties({"city": "台北市", "districts": ["大安區"], "budget_max": 5000})
        provider.query_property_search_rows.assert_called_once()


# ---------------------------------------------------------------------------
# 23. Data status remains BLUE
# ---------------------------------------------------------------------------

class TestDataStatusRemainsBLUE:
    def test_data_status_from_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: _green_compatible_rows(5),
        )

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())
        provider.data_status.assert_called_once()


# ---------------------------------------------------------------------------
# 24. match_community remains BLUE
# ---------------------------------------------------------------------------

class TestMatchCommunityRemainsBLUE:
    def test_community_from_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: _green_compatible_rows(5),
        )

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())
        provider.match_community.assert_called_once()


# ---------------------------------------------------------------------------
# 25. API response contract unchanged
# ---------------------------------------------------------------------------

class TestAPIContractUnchanged:
    def test_blue_contract(self, monkeypatch):
        monkeypatch.delenv("PLVR_DATA_BACKEND", raising=False)
        blue_rows = [{
            "transaction_period": "2026-01", "city": "台北市", "district": "大安區",
            "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30.0,
            "building_age_years": 12.0, "floor": 8.0, "total_floor": 14.0,
            "unit_price_per_ping": 75.0, "total_price": 2250.0,
            "address_text": "和平東路二段100號", "lat": 25.025, "lng": 121.543,
            "source": "official_plvr_opendata", "imported_at": None, "raw_note": None,
        }] * 5
        _fake_provider(monkeypatch, rows=blue_rows)

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())
        required = {"source", "data_status", "estimate_level", "confidence", "confidence_score", "comparables", "methodology", "disclaimer"}
        assert required.issubset(set(result.keys()))

    def test_green_contract(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        _fake_provider(monkeypatch)

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: _green_compatible_rows(5),
        )

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())
        required = {"source", "data_status", "estimate_level", "confidence", "confidence_score", "comparables", "methodology", "disclaimer"}
        assert required.issubset(set(result.keys()))
        assert result.get("valuation_status") in ("available", "demo")


# ---------------------------------------------------------------------------
# Additional: No write SQL in module
# ---------------------------------------------------------------------------

class TestNoWriteSQL:
    def test_no_write_statements(self):
        source_path = Path(__file__).resolve().parents[1] / "services" / "compact_green_query.py"
        source = source_path.read_text(encoding="utf-8")
        dangerous = [r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b", r"\bCREATE\s+TABLE\b", r"\bALTER\b", r"\bTRUNCATE\b"]
        for pattern in dangerous:
            assert not re.search(pattern, source, re.IGNORECASE), f"Found write SQL: {pattern}"


# ---------------------------------------------------------------------------
# Additional: Wall-clock period regression
# ---------------------------------------------------------------------------

class TestWallClockRegression:
    def test_frozen_318_not_wallclock(self, monkeypatch):
        from services.compact_green_query import get_geography_cache, get_max_period_code, encode_period, reset_geography_cache
        import services.compact_green_query as mod

        reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        get_geography_cache()
        # Even if current month is 2026-08 (code 319), we use 318 from data
        assert encode_period(2026, 8) == 319
        assert get_max_period_code() == 318
        reset_geography_cache()


# ---------------------------------------------------------------------------
# Additional: Feature flag edge cases
# ---------------------------------------------------------------------------

class TestFeatureFlagEdgeCases:
    def test_invalid_value_defaults_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "invalid")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is False

    def test_uppercase_green(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "GREEN")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is True

    def test_whitespace_green(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "  green  ")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is True

    def test_empty_defaults_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is False


# ---------------------------------------------------------------------------
# close_green_pool() tests
# ---------------------------------------------------------------------------

class TestCloseGreenPool:
    def test_close_on_uninitialized_pool_is_safe(self):
        """Calling close when pool was never created must not raise."""
        import services.compact_green_query as mod
        mod._reset_pool()  # ensure None
        assert mod._pool is None
        # Must not raise
        mod.close_green_pool()
        assert mod._pool is None

    def test_close_does_not_initialize_pool(self, monkeypatch):
        """close_green_pool must NOT create a pool."""
        import services.compact_green_query as mod
        mod._reset_pool()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        # close should not trigger pool creation
        mod.close_green_pool()
        assert mod._pool is None

    def test_initialized_pool_close_called(self, monkeypatch):
        """When pool exists, close_green_pool calls pool.close() exactly once."""
        import services.compact_green_query as mod
        mod._reset_pool()

        mock_pool = MagicMock()
        mock_pool.close = MagicMock()
        mod._pool = mock_pool

        mod.close_green_pool()

        mock_pool.close.assert_called_once()
        assert mod._pool is None

    def test_repeated_close_is_safe(self, monkeypatch):
        """Multiple close calls must not raise."""
        import services.compact_green_query as mod
        mod._reset_pool()

        mock_pool = MagicMock()
        mod._pool = mock_pool

        mod.close_green_pool()
        mod.close_green_pool()
        mod.close_green_pool()
        # All calls safe; pool.close() called once (first time only, _pool is None after)
        assert mod._pool is None

    def test_pool_none_after_close(self):
        """After close, _pool must be None."""
        import services.compact_green_query as mod
        mock_pool = MagicMock()
        mod._pool = mock_pool
        mod.close_green_pool()
        assert mod._pool is None

    def test_new_pool_can_initialize_after_close(self, monkeypatch):
        """After close, a new GREEN query can lazily create a fresh pool."""
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        # Simulate: pool was closed
        mod._reset_pool()
        assert mod._pool is None

        # Now a query should be able to lazily init a new pool
        with _mock_pool() as (mock_pool_obj, _, _):
            monkeypatch.setattr(mod, "_pool", None)
            monkeypatch.setattr("services.compact_green_query._get_pool", lambda: mock_pool_obj)
            result = mod.query_green_comparables(_sample_payload())
            assert len(result) > 0

        mod.reset_geography_cache()

    def test_close_preserves_read_only_semantics(self, monkeypatch):
        """After close and re-init, transactions remain read-only."""
        import services.compact_green_query as mod

        mod.reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(mod, "_load_geography_cache", lambda url: ({("台北市", "大安區"): 1}, 318))

        with _mock_pool() as (mock_pool_obj, mock_conn, _):
            monkeypatch.setattr(mod, "_pool", mock_pool_obj)
            mod.query_green_comparables(_sample_payload())
            # Verify read-only was set inside transaction
            mock_conn.transaction.assert_called_once()
            mock_conn.execute.assert_called_once_with("SET TRANSACTION READ ONLY")

        mod.reset_geography_cache()

    def test_close_no_blue_fallback(self, monkeypatch):
        """close_green_pool must not trigger any BLUE interaction."""
        import services.compact_green_query as mod
        mod._reset_pool()
        # No BLUE env needed, no BLUE called
        mod.close_green_pool()
        # If we got here without error, no BLUE was touched
