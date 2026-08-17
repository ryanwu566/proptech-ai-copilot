"""Tests for the BLUE vs GREEN valuation shadow A/B harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# Import harness functions
sys_path_added = False

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _import_harness():
    """Import the harness module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bench_valuation_blue_green_shadow",
        SCRIPT_DIR / "bench_valuation_blue_green_shadow.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def harness():
    return _import_harness()


# ============================================================
# Case file validation
# ============================================================

class TestCaseFile:
    def test_cases_file_exists(self):
        cases_file = SCRIPT_DIR / "valuation_shadow_cases.json"
        assert cases_file.is_file()

    def test_cases_file_valid_json(self):
        cases_file = SCRIPT_DIR / "valuation_shadow_cases.json"
        cases = json.loads(cases_file.read_text(encoding="utf-8"))
        assert isinstance(cases, list)
        assert len(cases) >= 30

    def test_cases_have_required_fields(self):
        cases_file = SCRIPT_DIR / "valuation_shadow_cases.json"
        cases = json.loads(cases_file.read_text(encoding="utf-8"))
        required = {"case_id", "city", "district", "road", "building_type", "area_ping", "building_age_years", "floor"}
        for case in cases:
            assert required.issubset(set(case.keys())), f"Case {case.get('case_id')} missing fields"

    def test_cases_valid_values(self):
        cases_file = SCRIPT_DIR / "valuation_shadow_cases.json"
        cases = json.loads(cases_file.read_text(encoding="utf-8"))
        for case in cases:
            assert case["area_ping"] > 0, f"Case {case['case_id']}: area_ping <= 0"
            assert case["building_age_years"] >= 0, f"Case {case['case_id']}: age < 0"
            assert case["floor"] >= 0, f"Case {case['case_id']}: floor < 0"

    def test_case_ids_unique(self):
        cases_file = SCRIPT_DIR / "valuation_shadow_cases.json"
        cases = json.loads(cases_file.read_text(encoding="utf-8"))
        ids = [c["case_id"] for c in cases]
        assert len(ids) == len(set(ids)), "Duplicate case_id found"


# ============================================================
# Deterministic ordering
# ============================================================

class TestDeterministicOrdering:
    def test_cases_same_order_on_reload(self):
        cases_file = SCRIPT_DIR / "valuation_shadow_cases.json"
        cases1 = json.loads(cases_file.read_text(encoding="utf-8"))
        cases2 = json.loads(cases_file.read_text(encoding="utf-8"))
        assert cases1 == cases2


# ============================================================
# Metrics math
# ============================================================

class TestMetricsMath:
    def test_compute_diff_normal(self, harness):
        blue = {"estimate_total_price": 1000, "confidence_score": 70, "comparable_count": 10, "latency_ms": 200}
        green = {"estimate_total_price": 1050, "confidence_score": 65, "comparable_count": 8, "latency_ms": 150}
        diff = harness._compute_diff(blue, green)
        assert diff["estimate_abs_delta"] == 50.0
        assert diff["estimate_pct_delta"] == 5.0
        assert diff["confidence_delta"] == -5
        assert diff["comparable_count_delta"] == -2
        assert diff["latency_delta_ms"] == -50.0
        assert diff["latency_ratio"] == 0.75

    def test_compute_diff_zero_denominator(self, harness):
        blue = {"estimate_total_price": 0, "confidence_score": 70, "comparable_count": 0, "latency_ms": 0}
        green = {"estimate_total_price": 100, "confidence_score": 65, "comparable_count": 5, "latency_ms": 100}
        diff = harness._compute_diff(blue, green)
        # Zero blue estimate — pct delta should be None (avoid divide by zero)
        assert diff["estimate_pct_delta"] is None
        # Zero latency — ratio should be None
        assert diff["latency_ratio"] is None

    def test_compute_diff_missing_fields(self, harness):
        blue = {"status": "error"}
        green = {"status": "error"}
        diff = harness._compute_diff(blue, green)
        assert diff["estimate_abs_delta"] is None
        assert diff["estimate_pct_delta"] is None
        assert diff["confidence_delta"] is None

    def test_compute_diff_none_values(self, harness):
        blue = {"estimate_total_price": None, "confidence_score": None, "comparable_count": 0, "latency_ms": None}
        green = {"estimate_total_price": None, "confidence_score": None, "comparable_count": 0, "latency_ms": None}
        diff = harness._compute_diff(blue, green)
        assert diff["estimate_abs_delta"] is None
        assert diff["confidence_delta"] is None


# ============================================================
# Classification
# ============================================================

class TestClassification:
    def test_green_error_is_fail(self, harness):
        blue = {"status": "ok", "comparable_count": 5, "valuation_status": "available"}
        green = {"status": "error"}
        diff = {}
        assert harness._classify_case(blue, green, diff) == "FAIL"

    def test_green_unavailable_when_blue_ok_is_fail(self, harness):
        blue = {"status": "ok", "comparable_count": 5, "valuation_status": "available"}
        green = {"status": "ok", "valuation_status": "unavailable", "comparable_count": 0, "source": "postgres"}
        diff = {"estimate_pct_delta": None}
        assert harness._classify_case(blue, green, diff) == "FAIL"

    def test_green_zero_comparables_when_blue_has_them_is_fail(self, harness):
        blue = {"status": "ok", "comparable_count": 10, "valuation_status": "available"}
        green = {"status": "ok", "comparable_count": 0, "valuation_status": "available", "source": "postgres", "estimate_total_price": 0}
        diff = {"estimate_pct_delta": None}
        assert harness._classify_case(blue, green, diff) == "FAIL"

    def test_mock_fallback_source_is_fail(self, harness):
        blue = {"status": "ok", "comparable_count": 5, "valuation_status": "available"}
        green = {"status": "ok", "source": "mock_fallback", "comparable_count": 3, "valuation_status": "available", "estimate_total_price": 100}
        diff = {"estimate_pct_delta": 5}
        assert harness._classify_case(blue, green, diff) == "FAIL"

    def test_both_error_is_expected(self, harness):
        blue = {"status": "error"}
        green = {"status": "ok", "comparable_count": 0, "valuation_status": "available", "source": "postgres", "estimate_total_price": 0}
        diff = {"estimate_pct_delta": None}
        assert harness._classify_case(blue, green, diff) == "EXPECTED"

    def test_small_delta_is_expected(self, harness):
        blue = {"status": "ok", "comparable_count": 10, "valuation_status": "available"}
        green = {"status": "ok", "comparable_count": 10, "valuation_status": "available", "source": "postgres", "estimate_total_price": 1000}
        diff = {"estimate_pct_delta": 5.0, "confidence_delta": -3}
        assert harness._classify_case(blue, green, diff) == "EXPECTED"

    def test_large_delta_is_review(self, harness):
        blue = {"status": "ok", "comparable_count": 10, "valuation_status": "available"}
        green = {"status": "ok", "comparable_count": 10, "valuation_status": "available", "source": "postgres", "estimate_total_price": 1000}
        diff = {"estimate_pct_delta": 25.0, "confidence_delta": -5}
        assert harness._classify_case(blue, green, diff) == "REVIEW"

    def test_large_confidence_drop_is_review(self, harness):
        blue = {"status": "ok", "comparable_count": 10, "valuation_status": "available"}
        green = {"status": "ok", "comparable_count": 10, "valuation_status": "available", "source": "postgres", "estimate_total_price": 1000}
        diff = {"estimate_pct_delta": 5.0, "confidence_delta": -25}
        assert harness._classify_case(blue, green, diff) == "REVIEW"

    def test_negative_estimate_is_fail(self, harness):
        blue = {"status": "ok", "comparable_count": 5, "valuation_status": "available"}
        green = {"status": "ok", "comparable_count": 5, "valuation_status": "available", "source": "postgres", "estimate_total_price": -100}
        diff = {"estimate_pct_delta": -110}
        assert harness._classify_case(blue, green, diff) == "FAIL"


# ============================================================
# Secret-safe reporting
# ============================================================

class TestSecretSafe:
    def test_no_connection_strings_in_script(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        # Match real connection strings (with host/user), not pattern literals used for filtering
        real_dsns = re.findall(r"postgresql://[a-zA-Z0-9_]+[:@]", src)
        assert real_dsns == [], f"Real DSN found: {real_dsns}"

    def test_no_supabase_urls(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        # Match actual supabase hostnames, not string-pattern references
        supabase = re.findall(r"[a-z]+\.supabase\.co", src, re.IGNORECASE)
        assert supabase == []

    def test_no_write_sql(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        # Check for actual SQL write statements (cursor.execute with write keywords)
        # Exclude Python method calls like sys.path.insert or dict.update
        sql_writes = re.findall(r"(?:cursor|connection|conn)\.execute\(['\"].*?\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE)\b", src, re.IGNORECASE)
        assert sql_writes == [], f"Write SQL in execute call: {sql_writes}"


# ============================================================
# Dry-run
# ============================================================

class TestDryRun:
    def test_dry_run_no_network(self, harness, monkeypatch):
        """Dry-run must not attempt any network/DB calls."""
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        monkeypatch.setattr("sys.argv", ["bench", "--dry-run"])
        # Should succeed without any DB configured
        result = harness.main()
        assert result == 0

    def test_dry_run_loads_cases(self, harness, monkeypatch):
        """Dry-run validates case file."""
        monkeypatch.setattr("sys.argv", ["bench", "--dry-run"])
        result = harness.main()
        assert result == 0


# ============================================================
# Configuration missing fails safely
# ============================================================

class TestConfigMissing:
    def test_missing_blue_url_fails(self, harness, monkeypatch):
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        config = harness._check_configuration(dry_run=False)
        assert config == {}

    def test_missing_green_url_fails(self, harness, monkeypatch):
        monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://fake")
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        config = harness._check_configuration(dry_run=False)
        assert config == {}

    def test_both_present_passes(self, harness, monkeypatch):
        monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://fake")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        config = harness._check_configuration(dry_run=False)
        assert config.get("status") == "configured"

    def test_dry_run_skips_config_check(self, harness, monkeypatch):
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        config = harness._check_configuration(dry_run=True)
        # dry_run=True skips env validation, issues stays empty, returns configured
        assert config.get("status") == "configured"
