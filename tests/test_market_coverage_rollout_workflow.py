"""Static tests for the market coverage rollout workflow registration."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/reconcile-market-coverage.yml"
WORKFLOW = WORKFLOW_PATH.read_text(encoding="utf-8")


def test_reconcile_market_coverage_workflow_is_registered_in_workflows_dir() -> None:
    assert WORKFLOW_PATH.exists()
    assert WORKFLOW_PATH.parent.name == "workflows"
    assert WORKFLOW.splitlines()[0] == "name: Reconcile Nationwide Market Coverage"
    assert "reconcile-market-coverage:" in WORKFLOW


def test_reconcile_market_coverage_workflow_yaml_shape_is_parseable_when_available() -> None:
    try:
        import yaml  # type: ignore[import-not-found]
    except Exception:
        yaml = None

    if yaml is not None:
        parsed = yaml.safe_load(WORKFLOW)
        assert parsed["name"] == "Reconcile Nationwide Market Coverage"
        trigger = parsed.get("on", parsed.get(True))
        assert trigger == {"workflow_dispatch": None}
        assert parsed["permissions"] == {}
        assert "reconcile-market-coverage" in parsed["jobs"]

    lines = WORKFLOW.splitlines()
    assert lines[0] == "name: Reconcile Nationwide Market Coverage"
    assert lines[2] == "on:"
    assert lines[3] == "  workflow_dispatch:"
    assert lines[5] == "permissions: {}"


def test_reconcile_market_coverage_workflow_is_manual_only() -> None:
    assert "workflow_dispatch" in WORKFLOW
    assert "schedule" not in WORKFLOW
    assert "push:" not in WORKFLOW
    assert "pull_request" not in WORKFLOW
    assert "workflow_run" not in WORKFLOW
    assert "repository_dispatch" not in WORKFLOW


def test_reconcile_market_coverage_workflow_uses_only_expected_secrets() -> None:
    assert "secrets.RENDER_API_BASE_URL" in WORKFLOW
    assert "secrets.MARKET_READ_MODEL_REFRESH_TOKEN" in WORKFLOW
    assert "secrets.TDX" not in WORKFLOW
    assert "secrets.GOOGLE" not in WORKFLOW
    assert "secrets.TGOS" not in WORKFLOW
    assert "X-Market-Read-Model-Refresh-Token" in WORKFLOW


def test_reconcile_market_coverage_workflow_calls_rollout_routes_only() -> None:
    assert WORKFLOW.count("/market-insights/coverage/bootstrap") == 1
    assert WORKFLOW.count("/market-insights/coverage/reconcile") == 1
    assert WORKFLOW.count("/market-insights/coverage/audit") == 1
    assert "/market-insights/refresh" not in WORKFLOW
    assert "Refresh Market Read Model" not in WORKFLOW


def test_reconcile_market_coverage_workflow_has_safe_http_and_logs() -> None:
    assert "set -euo pipefail" in WORKFLOW
    assert "--connect-timeout 20" in WORKFLOW
    assert "--max-time 120" in WORKFLOW
    assert "--verbose" not in WORKFLOW
    assert "curl -v" not in WORKFLOW
    assert "--retry" not in WORKFLOW
    assert "set -x" not in WORKFLOW
    assert 'cat "$body' not in WORKFLOW
    assert 'echo "$body' not in WORKFLOW
    assert "echo \"${base_url}" not in WORKFLOW
    assert "echo \"${MARKET_READ_MODEL_REFRESH_TOKEN}" not in WORKFLOW
    for forbidden in ("database_url", "sql", "raw exception", "stack trace", "response body"):
        assert forbidden not in WORKFLOW.lower()


def test_reconcile_market_coverage_workflow_outputs_safe_status_lines() -> None:
    for line in (
        "MARKET_COVERAGE_BOOTSTRAP=success",
        "MARKET_COVERAGE_BOOTSTRAP=failed",
        "MARKET_COVERAGE_RECONCILED_COUNT=",
        "MARKET_COVERAGE_AUDIT=",
        "EXPECTED_REGION_COUNT=",
        "COVERED_REGION_COUNT=",
        "MISSING_REGION_COUNT=",
        "UNKNOWN_REGION_COUNT=",
    ):
        assert line in WORKFLOW
    assert "0 if status == 'FULL' else 1" in WORKFLOW
