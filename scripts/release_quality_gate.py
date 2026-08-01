"""Hermetic release-candidate contract checks.

This command reads tracked source and configuration only. It never loads
environment files, contacts a provider, or writes inside the repository.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REASON_CODES = (
    "required_file_missing",
    "registry_invalid",
    "registry_count_mismatch",
    "legacy_market_refresh_reachable",
    "mock_valuation_fallback_reachable",
    "demo_mode_unsafe_default",
    "production_localhost_fallback",
    "market_contract_invalid",
    "valuation_contract_invalid",
    "case_contract_invalid",
    "privacy_contract_invalid",
    "deployment_contract_invalid",
    "error_recovery_missing",
    "accessibility_contract_invalid",
    "python_tests_failed",
    "frontend_build_failed",
    "quality_gate_internal_failure",
)
OUTPUT_KEYS = (
    "RELEASE_CANDIDATE",
    "RELEASE_REASON",
    "PYTHON_TESTS",
    "FRONTEND_BUILD",
    "CANONICAL_REGISTRY",
    "MARKET_COVERAGE_CONTRACT",
    "MARKET_INSIGHT_CONTRACT",
    "VALUATION_TRUST_BOUNDARY",
    "PROPERTY_CASE_TRUST_BOUNDARY",
    "PRIVACY_BOUNDARY",
    "DEPLOYMENT_CONTRACT",
    "ERROR_RECOVERY",
    "ACCESSIBILITY_CONTRACT",
)

REQUIRED_FILES = (
    ".github/workflows/release-quality.yml",
    "scripts/release_quality_gate.py",
    "frontend_next/app/error.tsx",
    "frontend_next/app/global-error.tsx",
    "frontend_next/app/not-found.tsx",
    "frontend_next/lib/release-readiness.ts",
    "frontend_next/components/release-readiness-notice.tsx",
    "docs/release_candidate_operations.md",
    "docs/production_acceptance_checklist.md",
    "docs/privacy_and_storage_inventory.md",
    "tests/test_release_quality_gate.py",
    "tests/test_release_quality_workflow.py",
    "tests/test_frontend_release_recovery.py",
    "tests/test_frontend_accessibility_contract.py",
    "tests/test_frontend_privacy_boundary.py",
    "tests/test_deployment_configuration_contract.py",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _has_all(text: str, *needles: str) -> bool:
    return all(needle in text for needle in needles)


def _result(value: str = "pass", reason: str | None = None) -> dict[str, Any]:
    return {"value": value, "reason": reason}


def _required_files() -> tuple[str, str | None]:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    return ("pass", None) if not missing else ("fail", "required_file_missing")


def _registry() -> tuple[str, str | None]:
    try:
        payload = json.loads(_read("frontend_next/lib/taiwan-admin-areas.json"))
        areas = payload.get("areas")
        region_count = sum(len(area.get("districts", [])) for area in areas if isinstance(area, dict))
    except (OSError, TypeError, ValueError, AttributeError):
        return "fail", "registry_invalid"
    if not isinstance(areas, list) or len(areas) != 22 or region_count != 368:
        return "fail", "registry_count_mismatch"
    return "pass", None


def _market_contract() -> tuple[str, str | None]:
    routes = _read("backend/api/routes_market.py")
    service = _read("services/market_data_foundation.py")
    page = _read("frontend_next/app/page.tsx")
    if not _has_all(
        routes,
        "@router.post(\"/market-insights/query\")",
        "coverage_status",
        "data_status",
        "_safe_market_unavailable",
    ):
        return "fail", "market_contract_invalid"
    if not _has_all(service, "average_unit_price", "transaction_count", "source_name", "source_updated_at", "trend"):
        return "fail", "market_contract_invalid"
    if not _has_all(page, "availableResult", 'copy("common.noData")', 'copy("common.dataLimit")'):
        return "fail", "market_contract_invalid"
    return "pass", None


def _market_insight_contract() -> tuple[str, str | None]:
    page = _read("frontend_next/app/page.tsx")
    api = _read("frontend_next/lib/api.ts")
    if not _has_all(page, "Market Insight", "coverage_status", "data_status", "source_updated_at"):
        return "fail", "market_contract_invalid"
    if "/market-insights/query" not in api or "marketInsight" not in api:
        return "fail", "market_contract_invalid"
    # A protected operator refresh may remain in the backend, but no product
    # client may call the legacy refresh route.
    if "/market-insights/refresh" in api or "market-insights/refresh" in page:
        return "fail", "legacy_market_refresh_reachable"
    return "pass", None


def _load_names(source: str, name: str) -> list[ast.Name]:
    tree = ast.parse(source)
    return [node for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load)]


def _valuation_contract() -> tuple[str, str | None]:
    service = _read("services/valuation_service.py")
    contract = _read("services/valuation_result_contract.py")
    route = _read("backend/api/routes_valuation.py")
    try:
        mock_loads = _load_names(service, "MockFallbackProvider")
    except SyntaxError:
        return "fail", "valuation_contract_invalid"
    if mock_loads or not _has_all(service, "return UnavailableValuationProvider()", "explicit_demo", "VALUATION_DEMO_MODE"):
        return "fail", "mock_valuation_fallback_reachable"
    if not _has_all(contract, '"estimate_total_price": None', '"price_range": {"low": None, "mid": None, "high": None}', "result_origin"):
        return "fail", "valuation_contract_invalid"
    if not _has_all(route, "empty_estimate_result", "valuation_status", "result_origin"):
        return "fail", "valuation_contract_invalid"
    return "pass", None


def _case_contract() -> tuple[str, str | None]:
    evidence = _read("frontend_next/lib/property-case-evidence.ts")
    model = _read("frontend_next/lib/property-case.ts")
    comparison = _read("frontend_next/lib/case-comparison.ts")
    workspace = _read("frontend_next/components/immersive-viewing-workspace.tsx")
    report = _read("frontend_next/components/property-comparison-report.tsx")
    if not _has_all(evidence, "getTrustedValuationEvidence", "result_origin !== \"official\"", "is_actionable !== true", "comparables.length < 3"):
        return "fail", "case_contract_invalid"
    if not _has_all(model, "print_ready", "PARTIAL_CASE_PRINT_NOTICE", "hasBasicCaseInfo"):
        return "fail", "case_contract_invalid"
    if not _has_all(workspace, "getTrustedValuationEvidence", "transferable", "buildValuationSummaryHtml"):
        return "fail", "case_contract_invalid"
    if not _has_all(report, "comparisonStatus === \"ready\"", "PrintComparisonReport"):
        return "fail", "case_contract_invalid"
    if any(token in comparison for token in ("commute", "market-insights", "station_name")):
        return "fail", "case_contract_invalid"
    return "pass", None


def _privacy_contract() -> tuple[str, str | None]:
    storage = _read("frontend_next/lib/case-storage.ts")
    comparison = _read("frontend_next/lib/case-comparison.ts")
    inventory = _read("docs/privacy_and_storage_inventory.md")
    if storage.count("localStorage.setItem") != 1 or "SAVED_CASES_STORAGE_KEY" not in storage:
        return "fail", "privacy_contract_invalid"
    if not _has_all(storage, "resolved_location: null", "nearest_pois: []"):
        return "fail", "privacy_contract_invalid"
    if not _has_all(inventory, "localStorage", "sessionStorage", "coordinates", "provider payload", "share"):
        return "fail", "privacy_contract_invalid"
    if "localStorage" in comparison or "sessionStorage" in comparison:
        return "fail", "privacy_contract_invalid"
    return "pass", None


def _deployment_contract() -> tuple[str, str | None]:
    render = _read("render.yaml")
    api = _read("frontend_next/lib/api.ts")
    origin = _read("frontend_next/lib/api-origin.ts")
    package = json.loads(_read("frontend_next/package.json"))
    scripts = package.get("scripts", {})
    if not _has_all(render, "runtime: python", "uvicorn backend.api_main:app", "healthCheckPath: /health", "VALUATION_DATABASE_URL"):
        return "fail", "deployment_contract_invalid"
    if not _has_all(api, "NEXT_PUBLIC_API_BASE_URL", "resolveApiOrigin", "allowRelativeProxy") or not _has_all(origin, "Production API origin must use HTTPS", "A localhost API origin is not allowed"):
        return "fail", "production_localhost_fallback"
    if "build" not in scripts:
        return "fail", "deployment_contract_invalid"
    return "pass", None


def _error_recovery() -> tuple[str, str | None]:
    files = (_read("frontend_next/app/error.tsx"), _read("frontend_next/app/global-error.tsx"), _read("frontend_next/app/not-found.tsx"))
    joined = "\n".join(files)
    if not _has_all(joined, "role=\"alert\"", "type=\"button\"", "href=\"/\""):
        return "fail", "error_recovery_missing"
    if any(token in joined for token in ("error.message", "error.stack", "digest", "localStorage", "sessionStorage", "fetch(", "fetch (")):
        return "fail", "error_recovery_missing"
    return "pass", None


def _accessibility() -> tuple[str, str | None]:
    notice = _read("frontend_next/components/release-readiness-notice.tsx")
    files = "\n".join((_read("frontend_next/app/error.tsx"), notice))
    if not _has_all(files, "type=\"button\"", "role=\"status\"", "aria-live"):
        return "fail", "accessibility_contract_invalid"
    if not _has_all(files, "bg-emerald", "bg-amber", "bg-rose", "summary.label"):
        return "fail", "accessibility_contract_invalid"
    return "pass", None


def _run_command(command: list[str], *, cwd: Path, timeout: int) -> bool:
    try:
        completed = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _pytest_command(temp_path: Path) -> list[str]:
    """Build a platform-neutral pytest command for local gate execution."""

    return [sys.executable, "-m", "pytest", "-q", "--basetemp", str(temp_path)]


def _npm_executable(platform_name: str | None = None) -> str:
    """Resolve npm without embedding a Windows-only executable in CI."""

    return "npm.cmd" if (platform_name or os.name) == "nt" else "npm"


def _frontend_build_command(platform_name: str | None = None) -> list[str]:
    return [_npm_executable(platform_name), "--prefix", "frontend_next", "run", "build"]


def _run_tests() -> bool:
    temp_path = Path(tempfile.mkdtemp(prefix="release-quality-pytest-"))
    try:
        return _run_command(_pytest_command(temp_path), cwd=ROOT, timeout=900)
    finally:
        # The temporary directory is outside the repository and is safe to remove.
        import shutil

        shutil.rmtree(temp_path, ignore_errors=True)


def _run_frontend_build() -> bool:
    return _run_command(_frontend_build_command(), cwd=ROOT, timeout=900)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    os.replace(temp, path)


def evaluate(*, skip_tests: bool, skip_frontend_build: bool) -> tuple[dict[str, str], list[str], int]:
    checks: dict[str, str] = {key: "not_run" for key in OUTPUT_KEYS}
    failures: list[str] = []

    required_value, reason = _required_files()
    if required_value == "fail":
        return ({**checks, "RELEASE_CANDIDATE": "fail", "RELEASE_REASON": reason or "required_file_missing"}, [reason or "required_file_missing"], 2)

    contract_checks = (
        ("CANONICAL_REGISTRY", _registry),
        ("MARKET_COVERAGE_CONTRACT", _market_contract),
        ("MARKET_INSIGHT_CONTRACT", _market_insight_contract),
        ("VALUATION_TRUST_BOUNDARY", _valuation_contract),
        ("PROPERTY_CASE_TRUST_BOUNDARY", _case_contract),
        ("PRIVACY_BOUNDARY", _privacy_contract),
        ("DEPLOYMENT_CONTRACT", _deployment_contract),
        ("ERROR_RECOVERY", _error_recovery),
        ("ACCESSIBILITY_CONTRACT", _accessibility),
    )
    for key, checker in contract_checks:
        try:
            value, reason = checker()
        except (OSError, TypeError, ValueError, SyntaxError, json.JSONDecodeError):
            value, reason = "fail", "quality_gate_internal_failure"
        checks[key] = value
        if value == "fail":
            failures.append(reason or "quality_gate_internal_failure")

    checks["PYTHON_TESTS"] = "not_run" if skip_tests else ("pass" if _run_tests() else "fail")
    if checks["PYTHON_TESTS"] == "fail":
        failures.append("python_tests_failed")
    checks["FRONTEND_BUILD"] = "not_run" if skip_frontend_build else ("pass" if _run_frontend_build() else "fail")
    if checks["FRONTEND_BUILD"] == "fail":
        failures.append("frontend_build_failed")

    if failures:
        technical_failure = any(reason in {"python_tests_failed", "frontend_build_failed"} for reason in failures)
        return ({**checks, "RELEASE_CANDIDATE": "fail", "RELEASE_REASON": failures[0]}, failures, 1 if technical_failure else 2)
    return ({**checks, "RELEASE_CANDIDATE": "pass", "RELEASE_REASON": "none"}, [], 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the hermetic release candidate quality gate.")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-frontend-build", action="store_true")
    args = parser.parse_args(argv)
    try:
        checks, failures, exit_code = evaluate(skip_tests=args.skip_tests, skip_frontend_build=args.skip_frontend_build)
        if args.json_output:
            _write_json(args.json_output, {
                "schema_version": "release-quality-v1",
                "release_candidate": checks["RELEASE_CANDIDATE"],
                "checks": {key.lower(): value for key, value in checks.items() if key not in {"RELEASE_CANDIDATE", "RELEASE_REASON"}},
                "failed_reason_codes": failures,
                "generated_at": datetime.now(UTC).isoformat(),
            })
        for key in OUTPUT_KEYS:
            print(f"{key}={checks.get(key, 'not_run')}")
        return exit_code
    except Exception:
        for key in OUTPUT_KEYS:
            if key == "RELEASE_CANDIDATE":
                print(f"{key}=fail")
            elif key == "RELEASE_REASON":
                print(f"{key}=quality_gate_internal_failure")
            else:
                print(f"{key}=not_run")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
