"""Tests for the hermetic release quality gate."""

from pathlib import Path
import json
import tempfile

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


def test_pytest_command_uses_current_interpreter_and_supplied_temp_path() -> None:
    temp_path = Path("system") / "temp" / "release-quality-pytest"
    command = gate._pytest_command(temp_path)
    assert command[:4] == [gate.sys.executable, "-m", "pytest", "-q"]
    assert command[-2:] == ["--basetemp", str(temp_path)]


def test_npm_command_is_portable_between_windows_and_linux() -> None:
    assert gate._npm_executable("nt") == "npm.cmd"
    assert gate._npm_executable("posix") == "npm"
    assert gate._frontend_build_command("posix")[0] == "npm"
    assert gate._frontend_build_command("nt")[0] == "npm.cmd"


def test_gate_does_not_depend_on_git_branch_or_history() -> None:
    source = (ROOT / "scripts/release_quality_gate.py").read_text(encoding="utf-8")
    assert "git " not in source
    assert "subprocess.run" in source


def test_gate_uses_system_temp_for_internal_pytest_runs() -> None:
    source = (ROOT / "scripts/release_quality_gate.py").read_text(encoding="utf-8")
    assert "tempfile.mkdtemp" in source
    assert "release-quality-pytest-" in source


def test_json_report_has_safe_schema_and_is_written_atomically() -> None:
    with tempfile.TemporaryDirectory(prefix="codex-release-report-") as directory:
        output = Path(directory) / "report.json"
        assert gate.main(["--skip-tests", "--skip-frontend-build", "--json-output", str(output)]) == 0
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "release-quality-v1"
        assert payload["release_candidate"] == "pass"
        assert isinstance(payload["checks"], dict)
        assert isinstance(payload["failed_reason_codes"], list)
        assert not output.with_name(".report.json.tmp").exists()


def test_contract_failure_and_test_failure_have_distinct_exit_codes(monkeypatch) -> None:
    monkeypatch.setattr(gate, "_registry", lambda: ("fail", "registry_count_mismatch"))
    _, failures, contract_exit = gate.evaluate(skip_tests=True, skip_frontend_build=True)
    assert contract_exit == 2
    assert failures == ["registry_count_mismatch"]

    monkeypatch.setattr(gate, "_registry", lambda: ("pass", None))
    monkeypatch.setattr(gate, "_run_tests", lambda: False)
    _, failures, test_exit = gate.evaluate(skip_tests=False, skip_frontend_build=True)
    assert test_exit == 1
    assert "python_tests_failed" in failures
