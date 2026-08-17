"""Tests for the BLUE vs GREEN valuation shadow A/B harness."""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any
import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"

def _import_harness():
    import importlib.util
    spec = importlib.util.spec_from_file_location("harness", SCRIPT_DIR / "bench_valuation_blue_green_shadow.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@pytest.fixture
def harness():
    return _import_harness()

# ============================================================
# Case file / schema
# ============================================================

class TestCaseFile:
    def test_exists(self):
        assert (SCRIPT_DIR / "valuation_shadow_cases.json").is_file()

    def test_valid_json(self):
        cases = json.loads((SCRIPT_DIR / "valuation_shadow_cases.json").read_text(encoding="utf-8"))
        assert isinstance(cases, list) and len(cases) >= 30

    def test_unique_ids(self):
        cases = json.loads((SCRIPT_DIR / "valuation_shadow_cases.json").read_text(encoding="utf-8"))
        ids = [c["case_id"] for c in cases]
        assert len(ids) == len(set(ids))

    def test_schema_valid_all(self, harness):
        cases = json.loads((SCRIPT_DIR / "valuation_shadow_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            valid, errs = harness.validate_case_schema(case)
            assert valid, f"{case['case_id']}: {errs}"

    def test_deterministic_order(self):
        c1 = json.loads((SCRIPT_DIR / "valuation_shadow_cases.json").read_text(encoding="utf-8"))
        c2 = json.loads((SCRIPT_DIR / "valuation_shadow_cases.json").read_text(encoding="utf-8"))
        assert c1 == c2

# ============================================================
# Non-finite guards
# ============================================================

class TestNonFiniteGuard:
    def test_nan_estimate_fails_contract(self, harness):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "medium",
                "confidence_score": 50, "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_total_price": float("nan"), "estimate_unit_price_per_ping": 75.0}
        valid, errs = harness.validate_response_contract(resp)
        assert not valid
        assert any("non-finite" in e for e in errs)

    def test_inf_estimate_fails_contract(self, harness):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "medium",
                "confidence_score": 50, "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_total_price": float("inf"), "estimate_unit_price_per_ping": 75.0}
        valid, errs = harness.validate_response_contract(resp)
        assert not valid

    def test_neg_inf_estimate_fails_contract(self, harness):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "medium",
                "confidence_score": 50, "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_total_price": float("-inf"), "estimate_unit_price_per_ping": 75.0}
        valid, errs = harness.validate_response_contract(resp)
        assert not valid

    def test_negative_estimate_fails_contract(self, harness):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "medium",
                "confidence_score": 50, "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_total_price": -100.0, "estimate_unit_price_per_ping": 75.0}
        valid, errs = harness.validate_response_contract(resp)
        assert not valid
        assert any("negative" in e for e in errs)

    def test_nan_confidence_fails(self, harness):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "medium",
                "confidence_score": float("nan"), "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_total_price": 1000.0, "estimate_unit_price_per_ping": 75.0}
        valid, errs = harness.validate_response_contract(resp)
        assert not valid

# ============================================================
# Response contract validation
# ============================================================

class TestResponseContract:
    def test_missing_field_fails(self, harness):
        resp = {"source": "x"}  # Missing most required fields
        valid, errs = harness.validate_response_contract(resp)
        assert not valid
        assert any("missing" in e for e in errs)

    def test_malformed_comparables_fails(self, harness):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "medium",
                "confidence_score": 50, "comparables": "not_a_list", "methodology": [], "disclaimer": ""}
        valid, errs = harness.validate_response_contract(resp)
        assert not valid
        assert any("not a list" in e for e in errs)

    def test_valid_response_passes(self, harness):
        resp = {"source": "postgres", "data_status": {}, "estimate_level": "road", "confidence": "medium",
                "confidence_score": 50, "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_total_price": 1000.0, "estimate_unit_price_per_ping": 75.0}
        valid, errs = harness.validate_response_contract(resp)
        assert valid

# ============================================================
# Classification
# ============================================================

class TestClassification:
    def test_blue_exception_is_fail(self, harness):
        blue = {"service_status": "error", "comparable_count": 0}
        green = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "source": "postgres", "estimate_total_price": 100}
        cls, reasons = harness.classify_case(blue, green, {}, "GREEN")
        assert cls == "FAIL"
        assert any("BLUE" in r for r in reasons)

    def test_green_exception_is_fail(self, harness):
        blue = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available"}
        green = {"service_status": "error", "comparable_count": 0}
        cls, reasons = harness.classify_case(blue, green, {}, "GREEN")
        assert cls == "FAIL"
        assert any("GREEN" in r for r in reasons)

    def test_both_exception_is_fail(self, harness):
        blue = {"service_status": "error"}
        green = {"service_status": "error"}
        cls, reasons = harness.classify_case(blue, green, {}, "GREEN")
        assert cls == "FAIL"

    def test_green_mock_fallback_is_fail(self, harness):
        blue = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available"}
        green = {"service_status": "ok", "source": "mock_fallback", "comparable_count": 3, "valuation_status": "available", "estimate_total_price": 100, "green_comparables_calls": 1, "blue_comparables_calls": 0}
        cls, reasons = harness.classify_case(blue, green, {"estimate_pct_delta": 5}, "GREEN")
        assert cls == "FAIL"

    def test_small_delta_expected(self, harness):
        blue = {"service_status": "ok", "comparable_count": 10, "valuation_status": "available", "green_comparables_calls": 0, "blue_comparables_calls": 1}
        green = {"service_status": "ok", "comparable_count": 10, "valuation_status": "available", "source": "postgres", "estimate_total_price": 1000, "green_comparables_calls": 1, "blue_comparables_calls": 0}
        cls, reasons = harness.classify_case(blue, green, {"estimate_pct_delta": 5.0, "confidence_delta": -3}, "GREEN")
        assert cls == "EXPECTED"

    def test_large_delta_is_review(self, harness):
        blue = {"service_status": "ok", "comparable_count": 10, "valuation_status": "available", "green_comparables_calls": 0, "blue_comparables_calls": 1}
        green = {"service_status": "ok", "comparable_count": 10, "valuation_status": "available", "source": "postgres", "estimate_total_price": 1000, "green_comparables_calls": 1, "blue_comparables_calls": 0}
        cls, reasons = harness.classify_case(blue, green, {"estimate_pct_delta": 25.0, "confidence_delta": -5}, "GREEN")
        assert cls == "REVIEW"

    def test_nonfinite_estimate_in_classification_is_fail(self, harness):
        blue = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "green_comparables_calls": 0, "blue_comparables_calls": 1}
        green = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "source": "postgres", "estimate_total_price": float("inf"), "green_comparables_calls": 1, "blue_comparables_calls": 0}
        cls, reasons = harness.classify_case(blue, green, {}, "GREEN")
        assert cls == "FAIL"

    def test_negative_estimate_in_classification_is_fail(self, harness):
        blue = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "green_comparables_calls": 0, "blue_comparables_calls": 1}
        green = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "source": "postgres", "estimate_total_price": -500, "green_comparables_calls": 1, "blue_comparables_calls": 0}
        cls, reasons = harness.classify_case(blue, green, {}, "GREEN")
        assert cls == "FAIL"

# ============================================================
# Provenance
# ============================================================

class TestProvenance:
    def test_blue_side_accidental_green_is_fail(self, harness):
        blue = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "green_comparables_calls": 1, "blue_comparables_calls": 1}
        green = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "source": "postgres", "estimate_total_price": 100, "green_comparables_calls": 1, "blue_comparables_calls": 0}
        cls, reasons = harness.classify_case(blue, green, {"estimate_pct_delta": 5}, "BLUE")
        assert cls == "FAIL"
        assert any("GREEN comparables" in r for r in reasons)

    def test_green_side_no_green_call_is_fail(self, harness):
        blue = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "green_comparables_calls": 0, "blue_comparables_calls": 1}
        green = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "source": "postgres", "estimate_total_price": 100, "green_comparables_calls": 0, "blue_comparables_calls": 0}
        cls, reasons = harness.classify_case(blue, green, {"estimate_pct_delta": 5}, "GREEN")
        assert cls == "FAIL"
        assert any("did not call GREEN" in r for r in reasons)

    def test_green_side_accidental_blue_comparables_is_fail(self, harness):
        blue = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "green_comparables_calls": 0, "blue_comparables_calls": 1}
        green = {"service_status": "ok", "comparable_count": 5, "valuation_status": "available", "source": "postgres", "estimate_total_price": 100, "green_comparables_calls": 1, "blue_comparables_calls": 1}
        cls, reasons = harness.classify_case(blue, green, {"estimate_pct_delta": 5}, "GREEN")
        assert cls == "FAIL"
        assert any("BLUE comparables" in r for r in reasons)

# ============================================================
# Metrics math
# ============================================================

class TestMetricsMath:
    def test_normal_diff(self, harness):
        blue = {"estimate_total_price": 1000, "confidence_score": 70, "comparable_count": 10, "service_latency_ms": 200, "api_latency_ms": 250}
        green = {"estimate_total_price": 1050, "confidence_score": 65, "comparable_count": 8, "service_latency_ms": 150, "api_latency_ms": 180}
        diff = harness._compute_diff(blue, green)
        assert diff["estimate_abs_delta"] == 50.0
        assert diff["estimate_pct_delta"] == 5.0
        assert diff["confidence_delta"] == -5
        assert diff["comparable_count_delta"] == -2
        assert diff["service_latency_delta"] == -50.0
        assert diff["api_latency_delta"] == -70.0

    def test_zero_denominator(self, harness):
        blue = {"estimate_total_price": 0, "confidence_score": 70, "comparable_count": 0, "service_latency_ms": 0, "api_latency_ms": 0}
        green = {"estimate_total_price": 100, "confidence_score": 65, "comparable_count": 5, "service_latency_ms": 100, "api_latency_ms": 100}
        diff = harness._compute_diff(blue, green)
        assert diff["estimate_pct_delta"] is None

    def test_none_values(self, harness):
        diff = harness._compute_diff({}, {})
        assert diff["estimate_abs_delta"] is None
        assert diff["confidence_delta"] is None

    def test_distribution(self, harness):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        dist = harness._distribution(vals)
        assert dist["min"] == 1.0
        assert dist["max"] == 10.0
        assert dist["median"] >= 5.0

    def test_empty_distribution(self, harness):
        dist = harness._distribution([])
        assert dist["min"] == 0
        assert dist["max"] == 0

# ============================================================
# Dry-run
# ============================================================

class TestDryRun:
    def test_no_network(self, harness, monkeypatch):
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        monkeypatch.setattr("sys.argv", ["bench", "--dry-run"])
        assert harness.main() == 0

    def test_no_subprocess(self, harness, monkeypatch):
        """Dry-run must not call _run_side."""
        monkeypatch.setattr("sys.argv", ["bench", "--dry-run"])
        calls = []
        monkeypatch.setattr(harness, "_run_side", lambda *a, **kw: calls.append(1) or [])
        harness.main()
        assert calls == []

# ============================================================
# Configuration
# ============================================================

class TestConfig:
    def test_missing_blue_fails(self, harness, monkeypatch):
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        assert harness._check_configuration(dry_run=False) == {}

    def test_missing_green_fails(self, harness, monkeypatch):
        monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://fake")
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        assert harness._check_configuration(dry_run=False) == {}

    def test_both_present(self, harness, monkeypatch):
        monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://fake")
        monkeypatch.setenv("COMPACT_GREEN_DATABASE_URL", "postgresql://fake")
        assert harness._check_configuration(dry_run=False).get("status") == "configured"

    def test_dry_run_skips(self, harness, monkeypatch):
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        assert harness._check_configuration(dry_run=True).get("status") == "configured"

# ============================================================
# Secret-safe
# ============================================================

class TestSecretSafe:
    def test_no_real_dsn(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        assert not re.findall(r"postgresql://[a-zA-Z0-9_]+[:@]", src)

    def test_no_supabase_host(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        assert not re.findall(r"[a-z]+\.supabase\.co", src, re.IGNORECASE)

    def test_no_write_sql_in_execute(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        assert not re.findall(r"(?:cursor|conn)\.execute.*?\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE)\b", src, re.IGNORECASE)
