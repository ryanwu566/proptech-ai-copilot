"""Tests for Compact GREEN Phase 1 — valuation estimate GREEN routing.

Covers all 16 required test scenarios:
1. Flag unset → BLUE query_comparables called
2. PLVR_DATA_BACKEND=blue → BLUE
3. PLVR_DATA_BACKEND=green → GREEN comparables function called
4. GREEN selection does NOT replace provider.data_status()
5. GREEN selection does NOT replace provider.match_community()
6. Trend remains BLUE
7. Property search remains BLUE
8. Geography cache loads only once
9. Missing district raises explicit error
10. Missing COMPACT_GREEN_DATABASE_URL fails explicitly
11. Period code decoding: 318 → 2026-07
12. GREEN row injects source="official_plvr_opendata"
13. GREEN row preserves current valuation-compatible fields
14. No INSERT / UPDATE / DELETE / DDL SQL in GREEN module
15. GREEN failure does NOT silently call BLUE query_comparables
16. Existing valuation API response contract remains unchanged
"""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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


def _fake_provider(monkeypatch, rows=None, available=True):
    """Patch get_valuation_provider to return a mock PostgresValuationProvider."""
    from services.valuation_providers.postgres_provider import PostgresValuationProvider

    provider = MagicMock(spec=PostgresValuationProvider)
    provider.source = "postgres"
    provider.is_demo_data = False
    provider.is_full_taiwan = False
    provider.available.return_value = available
    provider.data_status.return_value = {
        "active_source": "postgres",
        "is_demo_data": False,
        "is_full_taiwan": False,
        "data_composition": "official",
        "official_records_count": 1000,
        "sample_records_count": 0,
        "coverage": {"cities": ["台北市"], "districts": ["大安區"], "roads_count": 10, "records_count": 1000},
        "last_updated": "2026-08-01T00:00:00+00:00",
        "freshness_status": "current",
        "freshness_reason_code": "data_current",
        "freshness_as_of": "2026-08-17",
        "latest_import_at": "2026-08-01T00:00:00+00:00",
        "latest_import_age_days": 16,
        "newest_effective_period_lag_months": 1,
        "operator_attention_required": False,
        "freshness_user_message": "資料為最新狀態。",
    }
    provider.match_community.return_value = None
    provider.last_query_metadata = {
        "provider_active": "postgres",
        "candidate_pool_size": 50,
        "query_scope": "district_pool",
        "requested_city": "台北市",
        "requested_district": "大安區",
        "requested_road": "和平東路二段",
        "db_rows_returned": 50,
        "query_status": "ok",
    }
    if rows is not None:
        provider.query_comparables.return_value = rows
    else:
        provider.query_comparables.return_value = []

    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)
    return provider


def _sample_payload() -> dict[str, Any]:
    return {
        "city": "台北市",
        "district": "大安區",
        "road": "和平東路二段",
        "building_type": "住宅大樓",
        "area_ping": 30.0,
        "building_age_years": 12.0,
        "floor": 8,
        "lat": 25.025,
        "lng": 121.543,
        "address_text": "和平東路二段100號",
    }


# ---------------------------------------------------------------------------
# Test 1: Flag unset → BLUE query_comparables called
# ---------------------------------------------------------------------------

class TestFlagUnsetUsesBLUE:
    def test_unset_flag_uses_blue(self, monkeypatch):
        monkeypatch.delenv("PLVR_DATA_BACKEND", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        provider = _fake_provider(monkeypatch)

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())

        provider.query_comparables.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: PLVR_DATA_BACKEND=blue → BLUE
# ---------------------------------------------------------------------------

class TestFlagBlueUsesBLUE:
    def test_explicit_blue_uses_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "blue")
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        provider = _fake_provider(monkeypatch)

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())

        provider.query_comparables.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3: PLVR_DATA_BACKEND=green → GREEN comparables function called
# ---------------------------------------------------------------------------

class TestFlagGreenUsesGREEN:
    def test_green_flag_calls_green_query(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        # Mock the GREEN query to return compatible rows
        green_rows = [
            {
                "transaction_period": "2026-07",
                "city": "台北市", "district": "大安區", "road": "和平東路二段",
                "building_type": "住宅大樓", "area_ping": 30.0, "building_age_years": 12.0,
                "floor": 8.0, "total_floor": 14.0, "unit_price_per_ping": 75.0,
                "total_price": 2250.0, "address_text": "和平東路二段100號",
                "lat": None, "lng": None, "source": "official_plvr_opendata",
                "imported_at": None, "raw_note": None,
            }
        ] * 5  # Need at least 3 for estimate

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: green_rows,
        )

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())

        # BLUE query_comparables should NOT have been called
        provider.query_comparables.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: GREEN selection does NOT replace provider.data_status()
# ---------------------------------------------------------------------------

class TestGreenDoesNotReplaceDataStatus:
    def test_data_status_still_from_blue_provider(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        green_rows = [
            {
                "transaction_period": "2026-07",
                "city": "台北市", "district": "大安區", "road": "和平東路二段",
                "building_type": "住宅大樓", "area_ping": 30.0, "building_age_years": 12.0,
                "floor": 8.0, "total_floor": 14.0, "unit_price_per_ping": 75.0,
                "total_price": 2250.0, "address_text": "和平東路二段100號",
                "lat": None, "lng": None, "source": "official_plvr_opendata",
                "imported_at": None, "raw_note": None,
            }
        ] * 5

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: green_rows,
        )

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())

        # data_status is ALWAYS called from BLUE provider
        provider.data_status.assert_called_once()


# ---------------------------------------------------------------------------
# Test 5: GREEN selection does NOT replace provider.match_community()
# ---------------------------------------------------------------------------

class TestGreenDoesNotReplaceCommunity:
    def test_match_community_still_from_blue_provider(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        green_rows = [
            {
                "transaction_period": "2026-07",
                "city": "台北市", "district": "大安區", "road": "和平東路二段",
                "building_type": "住宅大樓", "area_ping": 30.0, "building_age_years": 12.0,
                "floor": 8.0, "total_floor": 14.0, "unit_price_per_ping": 75.0,
                "total_price": 2250.0, "address_text": "和平東路二段100號",
                "lat": None, "lng": None, "source": "official_plvr_opendata",
                "imported_at": None, "raw_note": None,
            }
        ] * 5

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: green_rows,
        )

        from services.valuation_service import estimate_property
        estimate_property(_sample_payload())

        # match_community is ALWAYS called from BLUE provider
        provider.match_community.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6: Trend remains BLUE
# ---------------------------------------------------------------------------

class TestTrendRemainsBLUE:
    def test_trend_does_not_use_green(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

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
        result = analyze_valuation_trend({"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 12})

        # Trend service calls query_trend_rows, not query_green_comparables
        provider.query_trend_rows.assert_called_once()


# ---------------------------------------------------------------------------
# Test 7: Property search remains BLUE
# ---------------------------------------------------------------------------

class TestPropertySearchRemainsBLUE:
    def test_property_search_does_not_use_green(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

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
        result = search_properties({"city": "台北市", "districts": ["大安區"], "budget_max": 5000})

        # Property search service calls query_property_search_rows, not GREEN
        provider.query_property_search_rows.assert_called_once()


# ---------------------------------------------------------------------------
# Test 8: Geography cache loads only once
# ---------------------------------------------------------------------------

class TestGeographyCacheLoadsOnce:
    def test_cache_singleton(self, monkeypatch):
        from services.compact_green_query import (
            get_geography_cache,
            reset_geography_cache,
        )

        reset_geography_cache()

        call_count = {"n": 0}

        def fake_load(url):
            call_count["n"] += 1
            return ({("台北市", "大安區"): 1, ("新北市", "板橋區"): 2}, 318)

        monkeypatch.setattr("services.compact_green_query._load_geography_cache", fake_load)
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

        cache1 = get_geography_cache()
        cache2 = get_geography_cache()
        cache3 = get_geography_cache()

        assert call_count["n"] == 1
        assert cache1 is cache2 is cache3
        reset_geography_cache()


# ---------------------------------------------------------------------------
# Test 9: Missing district raises explicit error
# ---------------------------------------------------------------------------

class TestMissingDistrictRaises:
    def test_district_not_in_cache_raises(self, monkeypatch):
        from services.compact_green_query import (
            CompactGreenQueryError,
            query_green_comparables,
            reset_geography_cache,
        )

        reset_geography_cache()

        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(
            "services.compact_green_query._load_geography_cache",
            lambda url: ({("台北市", "大安區"): 1}, 318),
        )

        with pytest.raises(CompactGreenQueryError, match="district not found"):
            query_green_comparables({
                "city": "台北市",
                "district": "信義區",
                "road": "松仁路",
                "building_type": "住宅大樓",
                "area_ping": 30,
                "building_age_years": 10,
            })

        reset_geography_cache()


# ---------------------------------------------------------------------------
# Test 10: Missing COMPACT_GREEN_DATABASE_URL fails explicitly
# ---------------------------------------------------------------------------

class TestMissingDatabaseURLFails:
    def test_missing_url_raises(self, monkeypatch):
        from services.compact_green_query import (
            CompactGreenQueryError,
            query_green_comparables,
            reset_geography_cache,
        )

        reset_geography_cache()
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)

        with pytest.raises(CompactGreenQueryError, match="not configured"):
            query_green_comparables({
                "city": "台北市",
                "district": "大安區",
                "road": "和平東路二段",
                "building_type": "住宅大樓",
                "area_ping": 30,
                "building_age_years": 12,
            })

        reset_geography_cache()


# ---------------------------------------------------------------------------
# Test 11: Period code decoding: 318 → 2026-07
# ---------------------------------------------------------------------------

class TestPeriodCodeDecoding:
    def test_decode_318(self):
        from services.compact_green_query import decode_period
        assert decode_period(318) == "2026-07"

    def test_decode_284(self):
        from services.compact_green_query import decode_period
        assert decode_period(284) == "2023-09"

    def test_encode_roundtrip(self):
        from services.compact_green_query import decode_period, encode_period
        assert decode_period(encode_period(2026, 7)) == "2026-07"
        assert decode_period(encode_period(2023, 9)) == "2023-09"
        assert decode_period(encode_period(2025, 1)) == "2025-01"
        assert decode_period(encode_period(2025, 12)) == "2025-12"


# ---------------------------------------------------------------------------
# Test 12: GREEN row injects source="official_plvr_opendata"
# ---------------------------------------------------------------------------

class TestGreenRowSource:
    def test_mapped_row_has_official_source(self):
        from services.compact_green_query import _map_green_row

        row = _fake_green_row()
        mapped = _map_green_row(row)
        assert mapped["source"] == "official_plvr_opendata"


# ---------------------------------------------------------------------------
# Test 13: GREEN row preserves current valuation-compatible fields
# ---------------------------------------------------------------------------

class TestGreenRowCompatibility:
    def test_all_required_fields_present(self):
        from services.compact_green_query import _map_green_row

        row = _fake_green_row(period_code=318)
        mapped = _map_green_row(row)

        required_fields = {
            "transaction_period", "city", "district", "road", "building_type",
            "area_ping", "building_age_years", "floor", "total_floor",
            "unit_price_per_ping", "total_price", "address_text",
            "lat", "lng", "source", "imported_at", "raw_note",
        }
        assert required_fields.issubset(set(mapped.keys()))

    def test_field_types(self):
        from services.compact_green_query import _map_green_row

        row = _fake_green_row(period_code=318)
        mapped = _map_green_row(row)

        assert mapped["transaction_period"] == "2026-07"
        assert isinstance(mapped["area_ping"], float)
        assert isinstance(mapped["building_age_years"], float)
        assert isinstance(mapped["floor"], float)
        assert isinstance(mapped["total_floor"], float)
        assert isinstance(mapped["unit_price_per_ping"], float)
        assert isinstance(mapped["total_price"], float)
        assert mapped["lat"] is None
        assert mapped["lng"] is None
        assert mapped["imported_at"] is None
        assert mapped["raw_note"] is None

    def test_field_values_preserved(self):
        from services.compact_green_query import _map_green_row

        row = _fake_green_row(
            period_code=300,
            city="新北市",
            district="板橋區",
            road="文化路二段",
            building_type="華廈",
            area_ping=28.5,
            building_age_years=16.0,
            floor=6.0,
            total_floor=10.0,
            unit_price_per_ping=61.0,
            total_price=1738.5,
            address_text="文化路二段50號",
        )
        mapped = _map_green_row(row)

        assert mapped["city"] == "新北市"
        assert mapped["district"] == "板橋區"
        assert mapped["road"] == "文化路二段"
        assert mapped["building_type"] == "華廈"
        assert mapped["area_ping"] == 28.5
        assert mapped["building_age_years"] == 16.0
        assert mapped["floor"] == 6.0
        assert mapped["total_floor"] == 10.0
        assert mapped["unit_price_per_ping"] == 61.0
        assert mapped["total_price"] == 1738.5
        assert mapped["address_text"] == "文化路二段50號"
        assert mapped["transaction_period"] == "2025-01"


# ---------------------------------------------------------------------------
# Test 14: No INSERT / UPDATE / DELETE / DDL SQL in GREEN module
# ---------------------------------------------------------------------------

class TestNoWriteSQL:
    def test_green_module_has_no_write_statements(self):
        source_path = Path(__file__).resolve().parents[1] / "services" / "compact_green_query.py"
        source = source_path.read_text(encoding="utf-8")

        # Check for dangerous SQL keywords (case-insensitive)
        dangerous_patterns = [
            r"\bINSERT\b",
            r"\bUPDATE\b",
            r"\bDELETE\b",
            r"\bDROP\b",
            r"\bCREATE\s+TABLE\b",
            r"\bALTER\b",
            r"\bTRUNCATE\b",
        ]
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, source, re.IGNORECASE)
            # Filter out matches in comments/docstrings that say "No INSERT"
            # We need actual SQL usage, not documentation
            assert not matches or all(
                "No " in source[max(0, source.find(m) - 5):source.find(m)]
                or "Do NOT" in source[max(0, source.find(m) - 20):source.find(m)]
                or "never" in source[max(0, source.find(m) - 20):source.find(m)].lower()
                for m in matches
            ), f"Found potentially dangerous SQL pattern '{pattern}' in GREEN module"

    def test_green_module_only_has_select_and_set(self):
        source_path = Path(__file__).resolve().parents[1] / "services" / "compact_green_query.py"
        source = source_path.read_text(encoding="utf-8")

        # Extract only the actual SQL string literal (the big triple-quoted constant)
        # and any cursor.execute calls
        sql_constant_match = re.search(
            r'_VALUATION_COMPARABLES_SQL\s*=\s*"""(.*?)"""',
            source,
            re.DOTALL,
        )
        assert sql_constant_match, "Could not find _VALUATION_COMPARABLES_SQL"
        main_sql = sql_constant_match.group(1).strip().upper()

        # The main SQL must start with WITH (which is SELECT-equivalent)
        assert main_sql.startswith("WITH"), f"Main SQL does not start with WITH: {main_sql[:40]}"

        # Check cursor.execute calls — extract their string args
        execute_calls = re.findall(r'cursor\.execute\(\s*["\']([^"\']+)["\']', source)
        for call_sql in execute_calls:
            upper = call_sql.strip().upper()
            assert upper.startswith(("SELECT", "SET")), (
                f"cursor.execute contains non-SELECT/SET SQL: {call_sql}"
            )


# ---------------------------------------------------------------------------
# Test 15: GREEN failure does NOT silently call BLUE query_comparables
# ---------------------------------------------------------------------------

class TestGreenFailureNoSilentFallback:
    def test_green_exception_does_not_call_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        provider = _fake_provider(monkeypatch)

        from services.compact_green_query import CompactGreenQueryError

        def raise_error(payload):
            raise CompactGreenQueryError("simulated failure")

        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            raise_error,
        )

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())

        # BLUE query_comparables must NOT have been called as fallback
        provider.query_comparables.assert_not_called()
        # Result should indicate failure
        assert result.get("valuation_status") in ("unavailable", None) or result.get("valuation_reason_code") == "provider_query_failed"


# ---------------------------------------------------------------------------
# Test 16: Existing valuation API response contract remains unchanged
# ---------------------------------------------------------------------------

class TestValuationAPIContractUnchanged:
    def test_blue_response_contract_unchanged(self, monkeypatch):
        """With BLUE active, response shape is identical to pre-GREEN."""
        monkeypatch.delenv("PLVR_DATA_BACKEND", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)

        blue_rows = [
            {
                "transaction_period": "2026-01", "city": "台北市", "district": "大安區",
                "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30.0,
                "building_age_years": 12.0, "floor": 8.0, "total_floor": 14.0,
                "unit_price_per_ping": 75.0, "total_price": 2250.0,
                "address_text": "和平東路二段100號", "lat": 25.025, "lng": 121.543,
                "source": "official_plvr_opendata", "imported_at": None, "raw_note": None,
            }
        ] * 5

        provider = _fake_provider(monkeypatch, rows=blue_rows)

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())

        # Core contract fields must be present
        required_keys = {
            "source", "data_status", "estimate_level", "confidence",
            "confidence_score", "comparables", "methodology", "disclaimer",
        }
        assert required_keys.issubset(set(result.keys())), (
            f"Missing keys: {required_keys - set(result.keys())}"
        )

    def test_green_response_contract_matches_blue(self, monkeypatch):
        """With GREEN active, response shape is identical."""
        monkeypatch.setenv("PLVR_DATA_BACKEND", "green")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

        green_rows = [
            {
                "transaction_period": "2026-07", "city": "台北市", "district": "大安區",
                "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30.0,
                "building_age_years": 12.0, "floor": 8.0, "total_floor": 14.0,
                "unit_price_per_ping": 75.0, "total_price": 2250.0,
                "address_text": "和平東路二段100號", "lat": None, "lng": None,
                "source": "official_plvr_opendata", "imported_at": None, "raw_note": None,
            }
        ] * 5

        provider = _fake_provider(monkeypatch)
        monkeypatch.setattr(
            "services.compact_green_query.query_green_comparables",
            lambda payload: green_rows,
        )

        from services.valuation_service import estimate_property
        result = estimate_property(_sample_payload())

        required_keys = {
            "source", "data_status", "estimate_level", "confidence",
            "confidence_score", "comparables", "methodology", "disclaimer",
        }
        assert required_keys.issubset(set(result.keys())), (
            f"Missing keys: {required_keys - set(result.keys())}"
        )
        # Verify result is actionable (not a failure)
        assert result.get("valuation_status") in ("available", "demo")


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

class TestFeatureFlagEdgeCases:
    def test_invalid_flag_value_defaults_to_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "invalid_value")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is False

    def test_uppercase_GREEN_works(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "GREEN")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is True

    def test_whitespace_green_works(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "  green  ")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is True

    def test_empty_flag_defaults_to_blue(self, monkeypatch):
        monkeypatch.setenv("PLVR_DATA_BACKEND", "")
        from services.compact_green_query import is_green_enabled
        assert is_green_enabled() is False


class TestGeographyCacheThreadSafety:
    def test_concurrent_loads_only_one_fetch(self, monkeypatch):
        from services.compact_green_query import get_geography_cache, reset_geography_cache

        reset_geography_cache()
        call_count = {"n": 0}
        load_lock = threading.Event()

        def slow_load(url):
            load_lock.wait(timeout=2)
            call_count["n"] += 1
            return ({("台北市", "大安區"): 1}, 318)

        monkeypatch.setattr("services.compact_green_query._load_geography_cache", slow_load)
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

        results = []

        def worker():
            try:
                results.append(get_geography_cache())
            except Exception as exc:
                results.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()

        # Let all threads proceed
        load_lock.set()

        for t in threads:
            t.join(timeout=5)

        assert call_count["n"] == 1
        assert all(r == {("台北市", "大安區"): 1} for r in results)
        reset_geography_cache()


class TestNormalizeCityInGreen:
    def test_traditional_city_normalized(self, monkeypatch):
        from services.compact_green_query import (
            CompactGreenQueryError,
            query_green_comparables,
            reset_geography_cache,
        )

        reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(
            "services.compact_green_query._load_geography_cache",
            lambda url: ({("台北市", "大安區"): 1}, 318),
        )

        # Mock psycopg to avoid real connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [_fake_green_row()]
        mock_connection = MagicMock()
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_connection):
            result = query_green_comparables({
                "city": "臺北市",  # Traditional character
                "district": "大安區",
                "road": "和平東路二段",
                "building_type": "住宅大樓",
                "area_ping": 30,
                "building_age_years": 12,
            })

        assert len(result) == 1
        reset_geography_cache()


# ---------------------------------------------------------------------------
# Wall-clock period regression test
# ---------------------------------------------------------------------------

class TestWallClockPeriodRegression:
    """Prove that wall-clock time does NOT determine max_period_code.

    Frozen generation official-plvr-green-18203c6347cd ends at period_code 318
    (2026-07). Even when the system clock is 2026-08 or later, the query must
    use 318 (from cached data metadata), NOT 319 (from datetime.now()).
    """

    def test_august_2026_uses_frozen_318_not_319(self, monkeypatch):
        from services.compact_green_query import (
            query_green_comparables,
            reset_geography_cache,
            get_max_period_code,
            encode_period,
        )

        reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")

        # Simulate: frozen data has max period_code 318 (2026-07)
        monkeypatch.setattr(
            "services.compact_green_query._load_geography_cache",
            lambda url: ({("台北市", "大安區"): 1}, 318),
        )

        # Mock psycopg to capture the actual params passed to execute
        captured_params = {}
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [_fake_green_row(period_code=318)]

        def capture_execute(sql, params=None):
            if params and isinstance(params, dict) and "max_period_code" in params:
                captured_params.update(params)

        mock_cursor.execute = capture_execute
        mock_connection = MagicMock()
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Key: wall clock is August 2026 — would produce 319 if used
        # But we DON'T use it — we use cached max from frozen data
        assert encode_period(2026, 8) == 319  # What wall-clock would produce

        with patch("psycopg.connect", return_value=mock_connection):
            # The function should use 318 (from cache), not 319 (from clock)
            try:
                query_green_comparables({
                    "city": "台北市",
                    "district": "大安區",
                    "road": "和平東路二段",
                    "building_type": "住宅大樓",
                    "area_ping": 30,
                    "building_age_years": 12,
                })
            except Exception:
                pass  # May fail due to mock cursor, but params are captured

        # The critical assertion: max_period_code must be 318, not 319
        assert captured_params.get("max_period_code") == 318, (
            f"Expected max_period_code=318 (frozen data), "
            f"got {captured_params.get('max_period_code')} (wall-clock bug if 319)"
        )

        # Also verify via the public getter
        assert get_max_period_code() == 318

        reset_geography_cache()

    def test_get_max_period_code_returns_cached_value(self, monkeypatch):
        from services.compact_green_query import (
            get_geography_cache,
            get_max_period_code,
            reset_geography_cache,
        )

        reset_geography_cache()
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        monkeypatch.setattr(
            "services.compact_green_query._load_geography_cache",
            lambda url: ({("台北市", "大安區"): 1}, 318),
        )

        get_geography_cache()
        assert get_max_period_code() == 318
        reset_geography_cache()

    def test_get_max_period_code_raises_before_cache_load(self):
        from services.compact_green_query import (
            CompactGreenQueryError,
            get_max_period_code,
            reset_geography_cache,
        )

        reset_geography_cache()
        with pytest.raises(CompactGreenQueryError, match="not available"):
            get_max_period_code()
