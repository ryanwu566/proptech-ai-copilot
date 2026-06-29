"""Static checks for the protected commute snapshot refresh workflow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "refresh-commute-snapshot.yml"
DOC_PATH = ROOT / "docs" / "commute-snapshot-operations-v1.md"
WORKFLOW = WORKFLOW_PATH.read_text(encoding="utf-8")
DOCS = DOC_PATH.read_text(encoding="utf-8")


def test_workflow_exists_and_is_manual_only() -> None:
    assert WORKFLOW_PATH.exists()
    assert "name: Refresh Commute Snapshot" in WORKFLOW
    assert "workflow_dispatch:" in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "cron:" not in WORKFLOW
    assert "pull_request:" not in WORKFLOW
    assert "push:" not in WORKFLOW
    assert "permissions: {}" in WORKFLOW


def test_workflow_uses_only_required_github_secrets() -> None:
    assert "${{ secrets.RENDER_API_BASE_URL }}" in WORKFLOW
    assert "${{ secrets.COMMUTE_REFRESH_TOKEN }}" in WORKFLOW
    assert "vars." not in WORKFLOW
    for forbidden in ("TDX_CLIENT_ID", "TDX_CLIENT_SECRET", "GOOGLE_MAPS_API_KEY", "TGOS_API_KEY", "CORS_ALLOWED_ORIGINS"):
        assert forbidden not in WORKFLOW


def test_workflow_calls_only_commute_refresh_once_with_protected_header() -> None:
    assert WORKFLOW.count("/commute/refresh") == 1
    assert "/commute/status" not in WORKFLOW
    assert "/commute/nearest" not in WORKFLOW
    assert "/location/resolve" not in WORKFLOW
    assert WORKFLOW.count("curl \\") == 1
    assert "X-Commute-Refresh-Token" in WORKFLOW


def test_workflow_curl_is_non_verbose_timed_and_discards_body() -> None:
    assert "set -euo pipefail" in WORKFLOW
    assert "--connect-timeout 20" in WORKFLOW
    assert "--max-time 120" in WORKFLOW
    assert "--output /dev/null" in WORKFLOW
    assert "--write-out \"%{http_code}\"" in WORKFLOW
    assert "--verbose" not in WORKFLOW
    assert "--retry" not in WORKFLOW


def test_workflow_logs_only_safe_result_and_status() -> None:
    assert "REFRESH_RESULT=success" in WORKFLOW
    assert "REFRESH_RESULT=failed" in WORKFLOW
    assert "REFRESH_HTTP_STATUS=" in WORKFLOW
    for forbidden in ("cat ", "response body", "station_name", "latitude", "longitude", "address", "raw payload", "provider raw"):
        assert forbidden not in WORKFLOW.lower()
    assert "echo \"${RENDER_API_BASE_URL}" not in WORKFLOW
    assert "echo \"${COMMUTE_REFRESH_TOKEN}" not in WORKFLOW


def test_operations_doc_covers_secrets_manual_flow_and_memory_limits() -> None:
    for text in (
        "RENDER_API_BASE_URL",
        "COMMUTE_REFRESH_TOKEN",
        "Actions",
        "Refresh Commute Snapshot",
        "Run workflow",
        "REFRESH_RESULT=success",
        "REFRESH_HTTP_STATUS=200",
        "only in Render backend memory",
        "not a durable snapshot persistence mechanism",
        "frontend must not call `/commute/refresh`",
    ):
        assert text in DOCS


def test_workflow_scope_does_not_touch_app_or_deployment_configs() -> None:
    changed_paths = {
        ".github/workflows/refresh-commute-snapshot.yml",
        "docs/commute-snapshot-operations-v1.md",
        "tests/test_commute_refresh_workflow_config.py",
    }
    for forbidden in ("backend/", "services/", "frontend_next/", "render.yaml", ".env", ".env.example"):
        assert all(not path.startswith(forbidden) for path in changed_paths)
