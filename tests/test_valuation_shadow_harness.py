"""Tests for BLUE vs GREEN valuation shadow A/B harness — all 20 scenarios."""
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
def h():
    return _import_harness()

def _good_prov(blue=True):
    if blue:
        return {"blue_calls": 1, "green_calls": 0}
    return {"blue_calls": 0, "green_calls": 1}

# ============================================================
# 1-4: Provenance failures
# ============================================================

class TestProvenance:
    def test_1_blue_blue_calls_zero_fail(self, h):
        valid, reasons = h.validate_backend_provenance(
            {"blue_calls": 0, "green_calls": 0}, _good_prov(True),
            _good_prov(False), _good_prov(False))
        assert not valid
        assert any("BLUE service: blue_calls=0" in r for r in reasons)

    def test_2_blue_green_calls_nonzero_fail(self, h):
        valid, reasons = h.validate_backend_provenance(
            {"blue_calls": 1, "green_calls": 1}, _good_prov(True),
            _good_prov(False), _good_prov(False))
        assert not valid
        assert any("green_calls" in r for r in reasons)

    def test_3_green_green_calls_zero_fail(self, h):
        valid, reasons = h.validate_backend_provenance(
            _good_prov(True), _good_prov(True),
            {"blue_calls": 0, "green_calls": 0}, _good_prov(False))
        assert not valid
        assert any("GREEN service: green_calls=0" in r for r in reasons)

    def test_4_green_blue_calls_nonzero_fail(self, h):
        valid, reasons = h.validate_backend_provenance(
            _good_prov(True), _good_prov(True),
            {"blue_calls": 1, "green_calls": 1}, _good_prov(False))
        assert not valid

# ============================================================
# 5-8: Layer-specific provenance
# ============================================================

    def test_5_blue_service_correct(self, h):
        valid, _ = h.validate_backend_provenance(
            _good_prov(True), _good_prov(True),
            _good_prov(False), _good_prov(False))
        assert valid

    def test_6_blue_api_provenance_wrong(self, h):
        valid, reasons = h.validate_backend_provenance(
            _good_prov(True), {"blue_calls": 0, "green_calls": 0},
            _good_prov(False), _good_prov(False))
        assert not valid
        assert any("BLUE API" in r for r in reasons)

    def test_7_green_service_correct(self, h):
        valid, _ = h.validate_backend_provenance(
            _good_prov(True), _good_prov(True),
            _good_prov(False), _good_prov(False))
        assert valid

    def test_8_green_api_provenance_wrong(self, h):
        valid, reasons = h.validate_backend_provenance(
            _good_prov(True), _good_prov(True),
            _good_prov(False), {"blue_calls": 0, "green_calls": 0})
        assert not valid
        assert any("GREEN API" in r for r in reasons)

# ============================================================
# 9-10: Contract validation failures
# ============================================================

class TestContractGating:
    def test_9_blue_contract_invalid_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                     "service_contract_valid": False, "service_contract_errors": ["missing: source"],
                     "api_contract_valid": True, "api_contract_errors": [],
                     "svc_api_consistent": True, "svc_api_reasons": []},
            "green": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                      "service_contract_valid": True, "service_contract_errors": [],
                      "api_contract_valid": True, "api_contract_errors": [],
                      "svc_api_consistent": True, "svc_api_reasons": [],
                      "source": "postgres", "estimate_total_price": 100, "comparable_count": 5, "valuation_status": "available"},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, reasons = h.classify_case(case_data)
        assert cls == "FAIL"
        assert any("BLUE service contract" in r for r in reasons)

    def test_10_green_contract_invalid_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                     "service_contract_valid": True, "service_contract_errors": [],
                     "api_contract_valid": True, "api_contract_errors": [],
                     "svc_api_consistent": True, "svc_api_reasons": []},
            "green": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                      "service_contract_valid": False, "service_contract_errors": ["non-finite"],
                      "api_contract_valid": True, "api_contract_errors": [],
                      "svc_api_consistent": True, "svc_api_reasons": []},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, reasons = h.classify_case(case_data)
        assert cls == "FAIL"

# ============================================================
# 11-14: API-level failures
# ============================================================

class TestAPIFailures:
    def test_11_blue_api_non200_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "http_error", "api_http_status": 500,
                     "service_contract_valid": True, "service_contract_errors": [],
                     "api_contract_valid": True, "api_contract_errors": [],
                     "svc_api_consistent": True, "svc_api_reasons": []},
            "green": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                      "service_contract_valid": True, "service_contract_errors": [],
                      "api_contract_valid": True, "api_contract_errors": [],
                      "svc_api_consistent": True, "svc_api_reasons": [],
                      "source": "postgres", "estimate_total_price": 100, "comparable_count": 5, "valuation_status": "available"},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, _ = h.classify_case(case_data)
        assert cls == "FAIL"

    def test_12_green_api_non200_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                     "service_contract_valid": True, "service_contract_errors": [],
                     "api_contract_valid": True, "api_contract_errors": [],
                     "svc_api_consistent": True, "svc_api_reasons": []},
            "green": {"service_status": "ok", "api_status": "http_error", "api_http_status": 422,
                      "service_contract_valid": True, "service_contract_errors": [],
                      "api_contract_valid": True, "api_contract_errors": [],
                      "svc_api_consistent": True, "svc_api_reasons": []},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, _ = h.classify_case(case_data)
        assert cls == "FAIL"

    def test_13_blue_api_contract_invalid_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                     "service_contract_valid": True, "service_contract_errors": [],
                     "api_contract_valid": False, "api_contract_errors": ["missing fields"],
                     "svc_api_consistent": True, "svc_api_reasons": []},
            "green": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                      "service_contract_valid": True, "service_contract_errors": [],
                      "api_contract_valid": True, "api_contract_errors": [],
                      "svc_api_consistent": True, "svc_api_reasons": [],
                      "source": "postgres", "estimate_total_price": 100, "comparable_count": 5, "valuation_status": "available"},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, _ = h.classify_case(case_data)
        assert cls == "FAIL"

    def test_14_green_api_contract_invalid_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                     "service_contract_valid": True, "service_contract_errors": [],
                     "api_contract_valid": True, "api_contract_errors": [],
                     "svc_api_consistent": True, "svc_api_reasons": []},
            "green": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                      "service_contract_valid": True, "service_contract_errors": [],
                      "api_contract_valid": False, "api_contract_errors": ["malformed"],
                      "svc_api_consistent": True, "svc_api_reasons": []},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, _ = h.classify_case(case_data)
        assert cls == "FAIL"

# ============================================================
# 15-16: Service/API consistency
# ============================================================

class TestConsistency:
    def test_15_blue_svc_api_mismatch_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                     "service_contract_valid": True, "service_contract_errors": [],
                     "api_contract_valid": True, "api_contract_errors": [],
                     "svc_api_consistent": False, "svc_api_reasons": ["estimate_total_price differs"]},
            "green": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                      "service_contract_valid": True, "service_contract_errors": [],
                      "api_contract_valid": True, "api_contract_errors": [],
                      "svc_api_consistent": True, "svc_api_reasons": [],
                      "source": "postgres", "estimate_total_price": 100, "comparable_count": 5, "valuation_status": "available"},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, reasons = h.classify_case(case_data)
        assert cls == "FAIL"
        assert any("mismatch" in r for r in reasons)

    def test_16_green_svc_api_mismatch_fail(self, h):
        case_data = {
            "blue": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                     "service_contract_valid": True, "service_contract_errors": [],
                     "api_contract_valid": True, "api_contract_errors": [],
                     "svc_api_consistent": True, "svc_api_reasons": []},
            "green": {"service_status": "ok", "api_status": "ok", "api_http_status": 200,
                      "service_contract_valid": True, "service_contract_errors": [],
                      "api_contract_valid": True, "api_contract_errors": [],
                      "svc_api_consistent": False, "svc_api_reasons": ["confidence_score differs"],
                      "source": "postgres", "estimate_total_price": 100, "comparable_count": 5, "valuation_status": "available"},
            "diff": {}, "provenance_valid": True, "provenance_reasons": [],
        }
        cls, _ = h.classify_case(case_data)
        assert cls == "FAIL"

# ============================================================
# 17: Canonical request model validation
# ============================================================

class TestCanonicalSchema:
    def test_17_uses_real_pydantic_model(self, h):
        valid, errs = h.validate_case_schema({"city": "台北市", "district": "大安區", "road": "x", "building_type": "住宅大樓", "area_ping": 30.0, "building_age_years": 12.0, "floor": 8})
        assert valid

    def test_invalid_area_rejected(self, h):
        valid, errs = h.validate_case_schema({"city": "x", "district": "y", "road": "z", "building_type": "w", "area_ping": -1, "building_age_years": 0, "floor": 0})
        assert not valid

    def test_missing_field_rejected(self, h):
        valid, errs = h.validate_case_schema({"city": "x"})
        assert not valid

    def test_all_36_cases_valid(self, h):
        cases = json.loads((SCRIPT_DIR / "valuation_shadow_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            valid, errs = h.validate_case_schema(case)
            assert valid, f"{case['case_id']}: {errs}"

# ============================================================
# 18: TestClient lifespan context
# ============================================================

class TestClientLifespan:
    def test_18_worker_uses_context_manager(self):
        """Worker script must use 'with TestClient(app) as client:'"""
        from scripts.bench_valuation_blue_green_shadow import _WORKER_SCRIPT
        assert "with TestClient(app) as client:" in _WORKER_SCRIPT

# ============================================================
# 19: NaN/inf guards
# ============================================================

class TestNonFinite:
    def test_19_nan_fails_contract(self, h):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "m",
                "confidence_score": 50, "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_total_price": float("nan")}
        valid, _ = h.validate_response_contract(resp)
        assert not valid

    def test_inf_fails(self, h):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "m",
                "confidence_score": float("inf"), "comparables": [], "methodology": [], "disclaimer": ""}
        valid, _ = h.validate_response_contract(resp)
        assert not valid

    def test_neg_inf_fails(self, h):
        resp = {"source": "x", "data_status": {}, "estimate_level": "road", "confidence": "m",
                "confidence_score": 50, "comparables": [], "methodology": [], "disclaimer": "",
                "estimate_unit_price_per_ping": float("-inf")}
        valid, _ = h.validate_response_contract(resp)
        assert not valid

# ============================================================
# 20: Dry-run safety
# ============================================================

class TestDryRunSafety:
    def test_20_no_subprocess_or_db(self, h, monkeypatch):
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        monkeypatch.setattr("sys.argv", ["bench", "--dry-run"])
        calls = []
        monkeypatch.setattr(h, "_run_side", lambda *a, **kw: calls.append(1) or [])
        result = h.main()
        assert result == 0
        assert calls == []

# ============================================================
# Additional: service/API consistency helper
# ============================================================

class TestConsistencyHelper:
    def test_matching_results(self, h):
        svc = {"valuation_status": "available", "estimate_total_price": 1000.0, "estimate_unit_price_per_ping": 50.0, "confidence_score": 70, "estimate_level": "road"}
        api = {"valuation_status": "available", "estimate_total_price": 1000.0, "estimate_unit_price_per_ping": 50.0, "confidence_score": 70, "estimate_level": "road"}
        valid, reasons = h.check_service_api_consistency(svc, api)
        assert valid

    def test_mismatched_estimate(self, h):
        svc = {"valuation_status": "available", "estimate_total_price": 1000.0, "estimate_unit_price_per_ping": 50.0, "confidence_score": 70, "estimate_level": "road"}
        api = {"valuation_status": "available", "estimate_total_price": 999.0, "estimate_unit_price_per_ping": 50.0, "confidence_score": 70, "estimate_level": "road"}
        valid, reasons = h.check_service_api_consistency(svc, api)
        assert not valid

# ============================================================
# Config / security
# ============================================================

class TestConfig:
    def test_missing_both_fails(self, h, monkeypatch):
        monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("COMPACT_GREEN_DATABASE_URL", raising=False)
        assert h._check_configuration(dry_run=False) == {}

    def test_dry_run_skips(self, h):
        assert h._check_configuration(dry_run=True).get("status") == "configured"

class TestSecretSafe:
    def test_no_real_dsn(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        assert not re.findall(r"postgresql://[a-zA-Z0-9_]+[:@]", src)

    def test_no_write_sql(self):
        import re
        src = (SCRIPT_DIR / "bench_valuation_blue_green_shadow.py").read_text(encoding="utf-8")
        assert not re.findall(r"(?:cursor|conn)\.execute.*?\b(INSERT|UPDATE|DELETE|DROP)\b", src, re.IGNORECASE)
