"""Tests for the hermetic release quality gate."""

from pathlib import Path

from scripts import release_quality_gate as gate


ROOT = Path(__file__).resolve().parents[1]


def test_contract_only_quality_gate_passes_without_running_tests_or_build() -> None:
    checks, failures, exit_code = gate.evaluate(skip_tests=True, skip_frontend_build=True)
    assert exit_code == 0
    assert not failures
    assert checks["RELEASE_CANDIDATE"] == "pass"
    assert all(checks[key] == "pass" for key in gate.OUTPUT_KEYS[4:])


def test_output_keys_are_allowlisted() -> None:
    assert tuple(gate.OUTPUT_KEYS) == (
        "RELEASE_CANDIDATE", "RELEASE_REASON", "PYTHON_TESTS", "FRONTEND_BUILD",
        "CANONICAL_REGISTRY", "MARKET_COVERAGE_CONTRACT", "MARKET_INSIGHT_CONTRACT",
        "VALUATION_TRUST_BOUNDARY", "PROPERTY_CASE_TRUST_BOUNDARY", "PRIVACY_BOUNDARY",
        "DEPLOYMENT_CONTRACT", "ERROR_RECOVERY", "ACCESSIBILITY_CONTRACT",
    )


def test_registry_contract_is_22_areas_and_368_regions() -> None:
    assert gate._registry() == ("pass", None)


def test_gate_does_not_read_environment_files() -> None:
    source = (ROOT / "scripts/release_quality_gate.py").read_text(encoding="utf-8")
    assert ".env" not in source
    assert "os.getenv" not in source
    assert "printenv" not in source
