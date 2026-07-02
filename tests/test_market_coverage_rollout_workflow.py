"""Static tests for the protected market coverage rollout workflow."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/reconcile-market-coverage.yml"
WORKFLOW = WORKFLOW_PATH.read_text(encoding="utf-8")
REGISTRY_HELPER = ROOT / "scripts/list_market_coverage_counties.py"


def _reconcile_metrics_parser() -> str:
    marker = 'reconcile_metrics="$(python - "$reconcile_body" <<\'PY\''
    start = WORKFLOW.index(marker) + len(marker)
    end = WORKFLOW.index("\nPY\n", start)
    return WORKFLOW[start:end].lstrip()


def _run_reconcile_metrics_parser(payload: dict[str, object], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    payload_file = tmp_path / "reconcile.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-", str(payload_file)],
        input=_reconcile_metrics_parser(),
        check=False,
        text=True,
        capture_output=True,
    )


def test_market_coverage_rollout_workflow_is_manual_only() -> None:
    assert WORKFLOW_PATH.exists()
    assert "name: Reconcile Nationwide Market Coverage" in WORKFLOW
    assert "workflow_dispatch" in WORKFLOW
    assert "schedule" not in WORKFLOW
    assert "push:" not in WORKFLOW
    assert "pull_request" not in WORKFLOW
    assert "workflow_run" not in WORKFLOW
    assert "permissions: {}" in WORKFLOW


def test_market_coverage_rollout_uses_existing_secrets_and_safe_curl() -> None:
    assert "secrets.RENDER_API_BASE_URL" in WORKFLOW
    assert "secrets.MARKET_READ_MODEL_REFRESH_TOKEN" in WORKFLOW
    assert "X-Market-Read-Model-Refresh-Token" in WORKFLOW
    assert "set -euo pipefail" in WORKFLOW
    assert "--connect-timeout 20" in WORKFLOW
    assert "--max-time 120" in WORKFLOW
    assert "--verbose" not in WORKFLOW
    assert "--retry" not in WORKFLOW
    assert "set -x" not in WORKFLOW


def test_market_coverage_rollout_calls_only_coverage_routes() -> None:
    assert WORKFLOW.count("/market-insights/coverage/bootstrap") == 1
    assert WORKFLOW.count("/market-insights/coverage/reconcile") == 1
    assert WORKFLOW.count("/market-insights/coverage/audit") == 1
    assert "/market-insights/refresh" not in WORKFLOW


def test_market_coverage_rollout_outputs_only_safe_lines() -> None:
    for line in (
        "MARKET_COVERAGE_BOOTSTRAP=success",
        "MARKET_COVERAGE_BOOTSTRAP=failed",
        "MARKET_COVERAGE_BOOTSTRAP_HTTP_STATUS=",
        "MARKET_COVERAGE_BOOTSTRAP_REASON=",
        "MARKET_COVERAGE_REGISTRY=success",
        "MARKET_COVERAGE_REGISTRY=failed",
        "MARKET_COVERAGE_REGISTRY_REASON=",
        "MARKET_COVERAGE_RECONCILE_STATUS=",
        "MARKET_COVERAGE_RECONCILE_HTTP_STATUS=",
        "MARKET_COVERAGE_RECONCILE_REASON=",
        "MARKET_COVERAGE_RECONCILE_COUNTY=",
        "MARKET_COVERAGE_RECONCILED_COUNT=",
        "MARKET_COVERAGE_RECONCILE_COVERED_COUNT=",
        "MARKET_COVERAGE_RECONCILE_NOT_COVERED_COUNT=",
        "MARKET_COVERAGE_RECONCILE_UNKNOWN_COUNT=",
        "MARKET_COVERAGE_AUDIT=",
        "EXPECTED_REGION_COUNT=",
        "COVERED_REGION_COUNT=",
        "MISSING_REGION_COUNT=",
        "UNKNOWN_REGION_COUNT=",
    ):
        assert line in WORKFLOW
    assert 'cat "$bootstrap_status_file"' in WORKFLOW
    assert 'cat "$body_file"' not in WORKFLOW
    assert 'echo "$body_file"' not in WORKFLOW
    assert 'echo "MARKET_COVERAGE_RECONCILED_COUNT=0"' not in WORKFLOW
    assert 'echo "MARKET_COVERAGE_AUDIT=UNKNOWN"' not in WORKFLOW.split('if [ "$bootstrap_status" != "200" ]; then', 1)[1].split("exit 1", 1)[0]
    assert "response body" not in WORKFLOW.lower()
    assert "database_url" not in WORKFLOW
    assert "raw exception" not in WORKFLOW.lower()
    assert "real_price_transactions" not in WORKFLOW
    assert "FileNotFoundError" not in WORKFLOW
    assert "traceback" not in WORKFLOW.lower()


def test_market_coverage_rollout_full_only_exits_zero() -> None:
    assert "raise SystemExit(0 if status == 'FULL' else 1)" in WORKFLOW
    assert "'FULL','PARTIAL','UNKNOWN'" in WORKFLOW


def test_market_coverage_rollout_skips_later_stages_after_bootstrap_failure() -> None:
    bootstrap_failure_block = WORKFLOW.split('if [ "$bootstrap_status" != "200" ]; then', 1)[1].split("exit 1", 1)[0]

    assert "MARKET_COVERAGE_RECONCILE_STATUS=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_RECONCILE_HTTP_STATUS=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_RECONCILE_REASON=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_RECONCILE_COUNTY=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_RECONCILED_COUNT=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_RECONCILE_COVERED_COUNT=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_RECONCILE_NOT_COVERED_COUNT=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_RECONCILE_UNKNOWN_COUNT=not_run" in bootstrap_failure_block
    assert "MARKET_COVERAGE_AUDIT=NOT_RUN" in bootstrap_failure_block
    assert "EXPECTED_REGION_COUNT=not_run" in bootstrap_failure_block
    assert "COVERED_REGION_COUNT=not_run" in bootstrap_failure_block
    assert "MISSING_REGION_COUNT=not_run" in bootstrap_failure_block
    assert "UNKNOWN_REGION_COUNT=not_run" in bootstrap_failure_block
    assert "/market-insights/coverage/reconcile" not in bootstrap_failure_block
    assert "/market-insights/coverage/audit" not in bootstrap_failure_block


def test_market_coverage_rollout_skips_later_stages_after_registry_failure() -> None:
    registry_failure_block = WORKFLOW.split('if [ ! -f "$registry_helper" ]; then', 1)[1].split("exit 1", 1)[0]

    assert "MARKET_COVERAGE_REGISTRY=failed" in registry_failure_block
    assert "MARKET_COVERAGE_REGISTRY_REASON=canonical_registry_unavailable" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILE_STATUS=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILE_HTTP_STATUS=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILE_REASON=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILE_COUNTY=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILED_COUNT=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILE_COVERED_COUNT=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILE_NOT_COVERED_COUNT=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_RECONCILE_UNKNOWN_COUNT=not_run" in registry_failure_block
    assert "MARKET_COVERAGE_AUDIT=NOT_RUN" in registry_failure_block
    assert "EXPECTED_REGION_COUNT=not_run" in registry_failure_block
    assert "COVERED_REGION_COUNT=not_run" in registry_failure_block
    assert "MISSING_REGION_COUNT=not_run" in registry_failure_block
    assert "UNKNOWN_REGION_COUNT=not_run" in registry_failure_block
    assert "/market-insights/coverage/reconcile" not in registry_failure_block
    assert "/market-insights/coverage/audit" not in registry_failure_block


def test_market_coverage_rollout_skips_audit_after_reconcile_failure() -> None:
    reconcile_failure_block = WORKFLOW.split('if [ "$reconcile_status" != "200" ]; then', 1)[1].split("exit 1", 1)[0]

    assert "MARKET_COVERAGE_RECONCILE_STATUS=failed" in reconcile_failure_block
    assert "MARKET_COVERAGE_RECONCILE_HTTP_STATUS=${reconcile_status:-0}" in reconcile_failure_block
    assert 'MARKET_COVERAGE_RECONCILE_REASON=$(safe_reconcile_reason "$reconcile_body")' in reconcile_failure_block
    assert "MARKET_COVERAGE_RECONCILE_COUNTY=${county}" in reconcile_failure_block
    assert "MARKET_COVERAGE_RECONCILE_COVERED_COUNT=not_run" in reconcile_failure_block
    assert "MARKET_COVERAGE_RECONCILE_NOT_COVERED_COUNT=not_run" in reconcile_failure_block
    assert "MARKET_COVERAGE_RECONCILE_UNKNOWN_COUNT=not_run" in reconcile_failure_block
    assert "MARKET_COVERAGE_AUDIT=NOT_RUN" in reconcile_failure_block
    assert "EXPECTED_REGION_COUNT=not_run" in reconcile_failure_block
    assert "COVERED_REGION_COUNT=not_run" in reconcile_failure_block
    assert "MISSING_REGION_COUNT=not_run" in reconcile_failure_block
    assert "UNKNOWN_REGION_COUNT=not_run" in reconcile_failure_block
    assert "/market-insights/coverage/audit" not in reconcile_failure_block


def test_market_coverage_rollout_outputs_reconcile_success_metadata_before_audit() -> None:
    success_block = WORKFLOW.split('echo "MARKET_COVERAGE_RECONCILE_STATUS=success"', 1)[1].split('audit_body=', 1)[0]

    assert "MARKET_COVERAGE_RECONCILE_HTTP_STATUS=200" in success_block
    assert "MARKET_COVERAGE_RECONCILE_REASON=none" in success_block
    assert "MARKET_COVERAGE_RECONCILE_COUNTY=none" in success_block
    assert "MARKET_COVERAGE_RECONCILED_COUNT=${reconciled_count}" in success_block
    assert "MARKET_COVERAGE_RECONCILE_COVERED_COUNT=${reconcile_covered_count}" in success_block
    assert "MARKET_COVERAGE_RECONCILE_NOT_COVERED_COUNT=${reconcile_not_covered_count}" in success_block
    assert "MARKET_COVERAGE_RECONCILE_UNKNOWN_COUNT=${reconcile_unknown_count}" in success_block


def test_market_coverage_rollout_accumulates_reconcile_coverage_counts() -> None:
    assert "reconcile_covered_count=0" in WORKFLOW
    assert "reconcile_not_covered_count=0" in WORKFLOW
    assert "reconcile_unknown_count=0" in WORKFLOW
    assert "coverage_status" in WORKFLOW
    assert "covered_region_count" in WORKFLOW
    assert "not_covered_region_count" in WORKFLOW
    assert "unknown_region_count" in WORKFLOW
    assert "reconcile_covered_count=$((reconcile_covered_count + county_covered))" in WORKFLOW
    assert "reconcile_not_covered_count=$((reconcile_not_covered_count + county_not_covered))" in WORKFLOW
    assert "reconcile_unknown_count=$((reconcile_unknown_count + county_unknown))" in WORKFLOW


def test_market_coverage_reconcile_parser_accepts_legal_statuses(tmp_path) -> None:
    expected_outputs = {
        "covered": "2 0 0",
        "not_covered": "0 3 0",
        "coverage_unknown": "0 0 4",
    }

    for coverage_status, expected_stdout in expected_outputs.items():
        result = _run_reconcile_metrics_parser(
            {
                "coverage_status": coverage_status,
                "covered_region_count": 2 if coverage_status == "covered" else 0,
                "not_covered_region_count": 3 if coverage_status == "not_covered" else 0,
                "unknown_region_count": 4 if coverage_status == "coverage_unknown" else 0,
            },
            tmp_path,
        )

        assert result.returncode == 0
        assert result.stdout.strip() == expected_stdout
        assert "Traceback" not in result.stderr
        assert "exceptions must derive from BaseException" not in result.stderr


def test_market_coverage_reconcile_parser_fails_safely_for_invalid_payloads(tmp_path) -> None:
    invalid_payloads = [
        {"coverage_status": "unexpected"},
        {"coverage_status": "covered", "covered_region_count": "not-a-count"},
    ]

    for payload in invalid_payloads:
        result = _run_reconcile_metrics_parser(payload, tmp_path)

        assert result.returncode == 2
        assert result.stdout == ""
        assert "Traceback" not in result.stderr
        assert "exceptions must derive from BaseException" not in result.stderr


def test_market_coverage_reconcile_parser_fails_safely_for_invalid_json(tmp_path) -> None:
    payload_file = tmp_path / "reconcile.json"
    payload_file.write_text("{invalid json", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-", str(payload_file)],
        input=_reconcile_metrics_parser(),
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "exceptions must derive from BaseException" not in result.stderr


def test_market_coverage_reconcile_parser_has_no_raise_none_pattern() -> None:
    parser = _reconcile_metrics_parser()

    assert "raise SystemExit(2) if" not in WORKFLOW
    assert "raise None" not in WORKFLOW
    assert "exceptions must derive from BaseException" not in WORKFLOW
    assert "sys.exit(2)" in parser
    assert "allowed = {\"covered\", \"not_covered\", \"coverage_unknown\"}" in parser


def test_market_coverage_rollout_allowlists_bootstrap_reason_codes() -> None:
    for reason in (
        "coverage_bootstrap_route_unavailable",
        "coverage_bootstrap_migration_unavailable",
        "coverage_bootstrap_runtime_unavailable",
        "coverage_bootstrap_unknown_safe_failure",
    ):
        assert reason in WORKFLOW
    assert "reason_code" in WORKFLOW


def test_market_coverage_rollout_allowlists_reconcile_reason_codes() -> None:
    for reason in (
        "coverage_reconcile_route_unavailable",
        "coverage_reconcile_request_invalid",
        "coverage_reconcile_metadata_unavailable",
        "coverage_reconcile_runtime_unavailable",
        "coverage_reconcile_unknown_safe_failure",
    ):
        assert reason in WORKFLOW
    assert "safe_reconcile_reason" in WORKFLOW


def test_market_coverage_rollout_uses_workspace_registry_helper() -> None:
    assert "$GITHUB_WORKSPACE/scripts/list_market_coverage_counties.py" in WORKFLOW
    assert "data/taiwan-admin-areas.json" not in WORKFLOW
    assert "frontend_next/lib/taiwan-admin-areas.ts" not in WORKFLOW
    assert "canonical_registry_unavailable" in WORKFLOW
    assert "CANONICAL_REGISTRY_UNAVAILABLE" not in WORKFLOW


def test_market_coverage_county_helper_reads_shared_json_registry() -> None:
    helper = REGISTRY_HELPER.read_text(encoding="utf-8")

    assert 'frontend_next" / "lib" / "taiwan-admin-areas.json"' in helper
    assert "taiwan-admin-areas.ts" not in helper
    assert "COUNTY_PATTERN" not in helper
    assert "traceback" not in helper.lower()
    assert "FileNotFoundError" not in helper


def test_market_coverage_county_helper_outputs_tracked_counties_safely() -> None:
    result = subprocess.run(
        [sys.executable, str(REGISTRY_HELPER)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    counties = [line for line in result.stdout.splitlines() if line.strip()]
    assert result.returncode == 0
    assert len(counties) >= 1
    assert "CANONICAL_REGISTRY_UNAVAILABLE" not in result.stdout
    assert "Traceback" not in result.stderr
    assert "FileNotFoundError" not in result.stderr
