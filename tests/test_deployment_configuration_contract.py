"""Release-specific deployment contract checks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_does_not_use_deployment_secrets_or_providers() -> None:
    workflow = (ROOT / ".github/workflows/release-quality.yml").read_text(encoding="utf-8")
    assert "secrets." not in workflow
    assert "production" not in workflow.lower()
    assert "database" not in workflow.lower()
    assert "refresh" not in workflow.lower()


def test_render_and_frontend_contracts_remain_declared() -> None:
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    api = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")
    assert "uvicorn backend.api_main:app" in render
    assert "healthCheckPath: /health" in render
    assert "VALUATION_DATABASE_URL" in render
    assert "NEXT_PUBLIC_API_BASE_URL" in api
    assert "productionLocalhostConfigured" in api
